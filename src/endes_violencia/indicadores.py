"""Construcción de los indicadores de violencia de pareja de la ENDES.

Cada definición está anotada con el cuadro del informe del INEI que reproduce
(``referencias/cuadros_inei/Cap. 12``). Las definiciones marcadas como
VALIDADO reproducen el valor publicado con dos decimales exactos para 2021-2025;
consulta ``docs/validacion.md``.

Categorías de respuesta del módulo de violencia (D103*, D105*)
--------------------------------------------------------------
============== ==========================================================
Etiqueta       Significado
============== ==========================================================
"No"           Nunca ocurrió  →  no cuenta como violencia
"Nunca"        Ocurrió, pero **no** en los últimos 12 meses
"Algunas veces" Ocurrió algunas veces en los últimos 12 meses
"Frecuentemente" Ocurrió frecuentemente en los últimos 12 meses
============== ==========================================================

De ahí que "alguna vez" incluya la etiqueta ``"Nunca"`` (contraintuitivo pero
correcto: es el "sí, pero no en el último año") y "últimos 12 meses" no la incluya.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import categorias
from .config import COL_ELEGIBLE, COL_PESO, ESCALA_PESO, VAR_PESO
from .etiquetas import alguna, es, preguntada

# --------------------------------------------------------------------------
# Categorías de respuesta
# --------------------------------------------------------------------------
SI_ALGUNA_VEZ = ("Frecuentemente", "Algunas veces", "Nunca")
SI_ULTIMOS_12M = ("Frecuentemente", "Algunas veces", "Mucha frecuencia")
AFIRMATIVO = ("Si", "Sí")

# --------------------------------------------------------------------------
# Componentes de cada forma de violencia (cuadros 12.1, 12.2 y 12.22 del INEI)
# --------------------------------------------------------------------------
VIOLENCIA_FISICA = (
    "D105A",  # la empujó, sacudió o le tiró algo
    "D105B",  # la abofeteó o le retorció el brazo
    "D105C",  # la golpeó con el puño o algo que pudo dañarla
    "D105D",  # la pateó o arrastró
    "D105E",  # trató de estrangularla o quemarla
    "D105F",  # la amenazó con cuchillo, pistola u otra arma
    "D105G",  # la atacó/agredió con cuchillo, pistola u otra arma
)

VIOLENCIA_SEXUAL = (
    "D105H",  # la obligó a tener relaciones sexuales sin que ella quisiera
    "D105I",  # la obligó a realizar actos sexuales que ella no aprueba
)

# Situaciones de control (cuadro 12.2). Los seis ítems entran en el indicador de
# violencia psicológica, aunque el cuadro publicado detalla solo cinco.
CONTROL = {
    "D101A": "Es celoso o molesto si conversa con otro hombre",
    "D101B": "La acusa frecuentemente de ser infiel",
    "D101C": "Le impide que visite o la visiten sus amistades",
    "D101D": "Trata de limitar las visitas o el contacto con su familia",
    "D101E": "Insiste siempre en saber a dónde va",
    "D101F": "Desconfía con el dinero",
}

# Situaciones humillantes y amenazas (cuadro 12.2)
HUMILLACION = {"D103A": "La ha humillado delante de los demás"}
AMENAZAS = {
    "D103B": "La amenazó con hacerle daño a ella o a alguien cercano",
    "D103D": "La amenazó con irse de casa / quitarle las hijas e hijos o la ayuda económica",
}

# Equivalente de las situaciones de control referidas a los últimos 12 meses.
# Son preguntas propias del cuestionario peruano (no forman parte del recode DHS).
CONTROL_12M = ("QI1003AN", "QI1003BN", "QI1003CN", "QI1003DN", "QI1003EN", "QI1003FN")

# --------------------------------------------------------------------------
# Empoderamiento y actitudes
# --------------------------------------------------------------------------
# "Sola o con su esposo o compañero tiene la última palabra" (cuadro 2.15).
# ENDES 2021 etiqueta la decisión conjunta como "Ambos" y desde 2022 como
# "Entrevistada y esposo/compañero": se aceptan ambas familias de etiquetas.
DECIDE_SOLA_O_CON_PAREJA = (
    "Entrevistada",
    "Ambos",
    "Entrevistada y compañero",
    "Entrevistada y esposo/compañero",
)

DECISIONES = {
    "V739": "Gasto del propio dinero",
    "V743A": "Cuidado de su propia salud",
    "V743B": "Grandes compras del hogar",
    "V743C": "Compras para necesidades diarias",
    "V743D": "Visitas a familiares o amigos",
    "V743E": "Qué alimentos cocinar cada día",
}

JUSTIFICACION = {
    "V744A": "Si sale sin decirle",
    "V744B": "Si descuida a los niños",
    "V744C": "Si ella discute con él",
    "V744D": "Si se niega a tener relaciones sexuales",
    "V744E": "Si ella quema la comida",
}

# --------------------------------------------------------------------------
# Búsqueda de ayuda (cuadros 12.10, 12.11 y 12.12)
# --------------------------------------------------------------------------
FUENTES_AYUDA_CERCANAS = {
    "Madre": ("D119B",),
    "Padre": ("D119C",),
    "Hermana": ("D119F",),
    "Hermano": ("D119G",),
    "Actual/último esposo o compañero": ("D119A",),
    "Suegros": ("D119O", "D119P"),
    "Otro pariente del esposo": ("D119Q", "D119R"),
    # D119XI = "otro pariente femenino", D119XJ = "otro pariente masculino":
    # ambos son parientes de la mujer, no "otra persona".
    "Otro pariente de la mujer": ("D119XI", "D119XJ"),
    "Amiga(o) / Vecina(o)": ("D119S", "D119U"),
    "Otra persona": ("D119X",),
}

INSTITUCIONES = {
    "Comisaría": ("S1023AA",),
    "Juzgado": ("S1023AB",),
    "Fiscalía": ("S1023AC",),
    "Defensoría Municipal (DEMUNA)": ("S1023AD",),
    "Ministerio de la Mujer y Poblaciones Vulnerables": ("S1023AE",),
    "Defensoría del Pueblo": ("S1023AF",),
    "Establecimiento de salud": ("S1023AG",),
    "Organización privada": ("S1023AH",),
    "Otra institución": ("S1023AX",),
}

# --------------------------------------------------------------------------
# Universos
# --------------------------------------------------------------------------
COL_UNIVERSO_AYUDA = "universo_ayuda"


def marcar_universo(df: pd.DataFrame, copiar: bool = True) -> pd.DataFrame:
    """Agrega el ponderador y la marca de elegibilidad al módulo de violencia.

    El universo de los cuadros 12.1 a 12.4 son las **mujeres de 15 a 49 años alguna
    vez unidas seleccionadas y entrevistadas** para el módulo de violencia:

    * ``V044`` = "Mujer seleccionada y entrevistada"
    * ``V502`` ≠ "Nunca casada"

    VALIDADO: reproduce exactamente el número de casos ponderado y sin ponderar
    publicado por el INEI para 2022, 2023 y 2024.
    """
    df = _preparar(df, copiar)
    df[COL_PESO] = pd.to_numeric(df[VAR_PESO], errors="coerce") / ESCALA_PESO

    seleccionada = es(df["V044"], ["Mujer seleccionada y entrevistada"])
    alguna_vez_unida = preguntada(df["V502"]) & ~es(df["V502"], ["Nunca casada"])
    df[COL_ELEGIBLE] = seleccionada & alguna_vez_unida

    # Universo de las preguntas de búsqueda de ayuda: mujeres a las que se les
    # preguntó si buscaron ayuda tras haber sido maltratadas físicamente.
    df[COL_UNIVERSO_AYUDA] = preguntada(df["D119Y"])
    return df


# --------------------------------------------------------------------------
# Indicadores de violencia
# --------------------------------------------------------------------------
def _binaria(condicion: np.ndarray, elegible: np.ndarray) -> np.ndarray:
    """Devuelve 1/0 dentro del universo y NaN fuera de él."""
    salida = np.full(len(condicion), np.nan)
    salida[elegible] = condicion[elegible].astype(float)
    return salida


def _preparar(df: pd.DataFrame, copiar: bool) -> pd.DataFrame:
    """Copia el DataFrame salvo que quien llama ya se haya encargado de ello.

    Las etapas de construcción agregan decenas de columnas. Copiar en cada una multiplica
    el uso de memoria por el número de etapas, así que :func:`construir_todo` copia una
    sola vez y encadena el resto con ``copiar=False``.
    """
    return df.copy() if copiar else df


def construir_violencia(df: pd.DataFrame, copiar: bool = True) -> pd.DataFrame:
    """Construye los indicadores de violencia de pareja para ambas ventanas temporales.

    Se generan pares de columnas con sufijo ``_alguna_vez`` y ``_12m``:
    física, sexual, psicológica, total, física y/o sexual y las combinaciones
    excluyentes de polivictimización.

    VALIDADO contra los cuadros 12.1, 12.1.1, 12.4.1 y 12.4.2 del INEI.
    """
    df = _preparar(df, copiar)
    elegible = df[COL_ELEGIBLE].to_numpy(dtype=bool)

    # Cada ventana temporal define qué categorías cuentan y de qué familia de
    # variables se toman las situaciones de control.
    ventanas = (
        # sufijo,        categorías,       columnas de control,  categorías de control
        ("alguna_vez", SI_ALGUNA_VEZ, tuple(CONTROL), AFIRMATIVO),
        ("12m", SI_ULTIMOS_12M, CONTROL_12M, SI_ULTIMOS_12M),
    )

    for sufijo, categorias, columnas_control, categorias_control in ventanas:
        fisica = alguna(df, VIOLENCIA_FISICA, categorias)
        sexual = alguna(df, VIOLENCIA_SEXUAL, categorias)
        control_mask = alguna(df, columnas_control, categorias_control)
        humillacion = alguna(df, HUMILLACION, categorias)
        amenazas = alguna(df, AMENAZAS, categorias)
        psicologica = control_mask | humillacion | amenazas

        df[f"violencia_fisica_{sufijo}"] = _binaria(fisica, elegible)
        df[f"violencia_sexual_{sufijo}"] = _binaria(sexual, elegible)
        df[f"violencia_psicologica_{sufijo}"] = _binaria(psicologica, elegible)
        df[f"violencia_total_{sufijo}"] = _binaria(fisica | sexual | psicologica, elegible)
        df[f"violencia_fisica_o_sexual_{sufijo}"] = _binaria(fisica | sexual, elegible)

        # Componentes de la violencia psicológica (cuadro 12.2)
        df[f"control_{sufijo}"] = _binaria(control_mask, elegible)
        df[f"humillacion_{sufijo}"] = _binaria(humillacion, elegible)
        df[f"amenazas_{sufijo}"] = _binaria(amenazas, elegible)

        # Polivictimización: categorías mutuamente excluyentes
        df[f"poli_fisica_psicologica_{sufijo}"] = _binaria(
            fisica & psicologica & ~sexual, elegible)
        df[f"poli_sexual_psicologica_{sufijo}"] = _binaria(
            sexual & psicologica & ~fisica, elegible)
        df[f"poli_fisica_sexual_{sufijo}"] = _binaria(
            fisica & sexual & ~psicologica, elegible)
        df[f"poli_triple_{sufijo}"] = _binaria(fisica & sexual & psicologica, elegible)

    return df


def construir_componentes(df: pd.DataFrame, copiar: bool = True) -> pd.DataFrame:
    """Construye los componentes de control, humillación y amenaza (cuadro 12.2)."""
    df = _preparar(df, copiar)
    elegible = df[COL_ELEGIBLE].to_numpy(dtype=bool)
    for col in list(CONTROL) + list(HUMILLACION) + list(AMENAZAS):
        if col not in df.columns:
            continue
        categorias = AFIRMATIVO if col.startswith("D101") else SI_ALGUNA_VEZ
        df[f"comp_{col}"] = _binaria(es(df[col], categorias), elegible)
    return df


# --------------------------------------------------------------------------
# Dinámicas y factores asociados
# --------------------------------------------------------------------------
def construir_factores(df: pd.DataFrame, copiar: bool = True) -> pd.DataFrame:
    """Indicadores de consumo de alcohol de la pareja, decisiones y actitudes."""
    df = _preparar(df, copiar)
    elegible = df[COL_ELEGIBLE].to_numpy(dtype=bool)

    # Consumo de alcohol de la pareja (D113) y frecuencia (D114)
    toma = es(df["D113"], AFIRMATIVO)
    df["pareja_consume_alcohol"] = _binaria(toma, elegible)
    df["pareja_consume_frecuente"] = _binaria(
        toma & es(df["D114"], ["Algunas veces", "Mucha frecuencia"]), elegible)

    # Participación en decisiones del hogar: sola o junto con su pareja.
    # Universo: mujeres a las que se les formuló la pregunta (unidas actualmente).
    for col, etiqueta in DECISIONES.items():
        if col not in df.columns:
            continue
        universo = preguntada(df[col])
        df[f"decide_{col}"] = _binaria(es(df[col], DECIDE_SOLA_O_CON_PAREJA), universo)

    # Justificación de la violencia física. Universo: todas las mujeres entrevistadas.
    for col in JUSTIFICACION:
        if col not in df.columns:
            continue
        df[f"justifica_{col}"] = _binaria(es(df[col], AFIRMATIVO), preguntada(df[col]))

    return df


def construir_busqueda_ayuda(df: pd.DataFrame, copiar: bool = True) -> pd.DataFrame:
    """Indicadores de búsqueda de ayuda (cuadros 12.10, 12.11 y 12.12).

    VALIDADO: ``ayuda_personas_cercanas`` y ``ayuda_institucion`` reproducen
    exactamente el cuadro 12.10 del INEI para 2021-2025.
    """
    df = _preparar(df, copiar)
    universo = df[COL_UNIVERSO_AYUDA].to_numpy(dtype=bool)

    df["ayuda_personas_cercanas"] = _binaria(
        es(df["D119Y"], ["Buscó ayuda de alguien"]), universo)
    # S1023AZ = "No, nunca ha buscado ayuda": la respuesta "No" identifica a las
    # mujeres que sí acudieron a alguna institución.
    df["ayuda_institucion"] = _binaria(es(df["S1023AZ"], ["No"]), universo)
    df["ayuda_alguna"] = _binaria(
        (df["ayuda_personas_cercanas"] == 1).to_numpy()
        | (df["ayuda_institucion"] == 1).to_numpy(), universo)

    # Universos condicionales para el detalle por fuente / institución
    busco_cercanas = (df["ayuda_personas_cercanas"] == 1).to_numpy()
    busco_institucion = (df["ayuda_institucion"] == 1).to_numpy()

    for etiqueta, columnas in FUENTES_AYUDA_CERCANAS.items():
        clave = slug(etiqueta)
        df[f"fuente_{clave}"] = _binaria(alguna(df, columnas, AFIRMATIVO), busco_cercanas)

    for etiqueta, columnas in INSTITUCIONES.items():
        clave = slug(etiqueta)
        df[f"institucion_{clave}"] = _binaria(alguna(df, columnas, AFIRMATIVO), busco_institucion)

    return df


def slug(texto: str) -> str:
    """Convierte una etiqueta legible en un nombre de columna válido."""
    reemplazos = str.maketrans("áéíóúÁÉÍÓÚñÑ ", "aeiouAEIOUnN_")
    limpio = texto.translate(reemplazos)
    return "".join(c for c in limpio if c.isalnum() or c == "_").lower().strip("_")


def construir_todo(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica en orden todas las etapas de construcción de indicadores.

    Copia el DataFrame una sola vez; el resto de las etapas escriben sobre esa copia.
    """
    df = marcar_universo(df, copiar=True)
    df = categorias.normalizar(df, copiar=False)
    df = construir_violencia(df, copiar=False)
    df = construir_componentes(df, copiar=False)
    df = construir_factores(df, copiar=False)
    df = construir_busqueda_ayuda(df, copiar=False)
    return df
