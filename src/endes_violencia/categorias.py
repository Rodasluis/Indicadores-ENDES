"""Normalización de las variables de corte.

Las etiquetas de valor de la ENDES **cambian entre años** y traen suciedad de
digitación. Sin normalizar, una serie por característica no es comparable:

* ``V501`` cambia por completo entre 2021 y 2022: ``"Casada"`` → ``"Casado"``,
  ``"Conviviente"`` → ``"Viviendo juntos"``, ``"No viviendo juntos"`` → ``"No viven juntos"``.
* ``V731`` alterna ``"Actualmente trabaja"`` y ``"Actualmente trabajando"``.
* ``V024`` trae espacio inicial en 16 de los 25 departamentos (``" Lima"``).
* ``V190`` trae ``"Pobrer"`` en lugar de ``"Pobre"``.

Cada variable declara un diccionario ``variante → etiqueta canónica`` y un orden de
presentación. Las variantes no declaradas se conservan tal cual y se registran en el
log, para que un cambio de rótulo en un año nuevo se detecte en lugar de aparecer
como una categoría duplicada.
"""

from __future__ import annotations

import logging

import pandas as pd

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Equivalencias: {variable: {etiqueta cruda: etiqueta canónica}}
# --------------------------------------------------------------------------
EQUIVALENCIAS: dict[str, dict[str, str]] = {
    "V013": {
        "De 12 a 14 años de edad": "12-14",
        "De 15 a 19 años de edad": "15-19",
        "De 20 a 24 años de edad": "20-24",
        "De 25 a 29 años de edad": "25-29",
        "De 30 a 34 años de edad": "30-34",
        "De 35 a 39 años de edad": "35-39",
        "De 40 a 44 años de edad": "40-44",
        "De 45 a 49 años de edad": "45-49",
    },
    "V190": {
        "El más pobre": "Más pobre",
        "Pobrer": "Pobre",           # errata en las etiquetas del INEI
        "Pobre": "Pobre",
        "Medio": "Medio",
        "Rico": "Rico",
        "Más rico": "Más rico",
    },
    "V501": {
        "Casada": "Casada",
        "Casado": "Casada",
        "Conviviente": "Conviviente",
        "Viviendo juntos": "Conviviente",
        "No viven juntos": "Separada",
        "No viviendo juntos": "Separada",
        "Divorciada": "Divorciada",
        "Viuda": "Viuda",
        "Nunca casada": "Nunca unida",
        "Nunca se caso": "Nunca unida",
    },
    "V731": {
        "Actualmente trabaja": "Trabaja actualmente",
        "Actualmente trabajando": "Trabaja actualmente",
        "En el año pasado": "Trabajó en el último año",
        "Tiene un trabajo, pero con licencia hace 7 días": "Con trabajo, de licencia",
        "Tener un trabajo, pero en licencia los últimos 7 días": "Con trabajo, de licencia",
        "No": "No trabajó",
    },
    "S119D": {
        "Negro/ Moreno/ Zambo/ Mulato/Pueblo Afroperuano o afrodescendiente": "Afroperuano",
        "Nativo o indigena de la Amazonía": "Nativo/indígena amazónico",
        "Parte de otro pueblo indigena u originario": "Otro pueblo originario",
    },
    "D115B": {"Sí": "Sí", "No": "No", "No respondio": "No respondió"},
    "D115C": {"Sí": "Sí", "No": "No", "No respondio": "No respondió"},
    "D121": {"Sí": "Sí", "No": "No", "No sabe": "No sabe", "No respondio": "No respondió"},
}

# --------------------------------------------------------------------------
# Orden de presentación (las categorías ausentes de la lista van al final)
# --------------------------------------------------------------------------
ORDEN: dict[str, tuple[str, ...]] = {
    "V013": ("15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49"),
    "V025": ("Urbano", "Rural"),
    "V149": ("Sin educación", "Primaria incompleta", "Primaria completa",
             "Secundaria incompleta", "Secundaria completa", "Superior"),
    "V190": ("Más pobre", "Pobre", "Medio", "Rico", "Más rico"),
    "V501": ("Casada", "Conviviente", "Separada", "Divorciada", "Viuda", "Nunca unida"),
    "V731": ("Trabaja actualmente", "Trabajó en el último año",
             "Con trabajo, de licencia", "No trabajó"),
    "S119D": ("Quechua", "Aimara", "Nativo/indígena amazónico", "Otro pueblo originario",
              "Afroperuano", "Blanco", "Mestizo", "Otro", "No sabe"),
    "D115B": ("Sí", "No"),
    "D115C": ("Sí", "No"),
    "D121": ("Sí", "No", "No sabe"),
}

# Categorías que no deben aparecer en los reportes (no informativas o de n mínimo).
EXCLUIR: dict[str, tuple[str, ...]] = {
    "D115B": ("No respondió",),
    "D115C": ("No respondió",),
    "D121": ("No respondió",),
}

# Variables a las que solo se les recorta el espacio en blanco.
SOLO_LIMPIAR = ("V024", "V025", "V149", "V101", "V151", "S119")

# Variables cuya tabla de equivalencias debe cubrir *todas* las etiquetas posibles.
# Son aquellas donde el INEI cambió el rótulo entre años: si aparece una etiqueta no
# declarada, es señal de que un año nuevo trae otra variante y hay que revisarla.
# En el resto, la tabla solo renombra algunas etiquetas y el resto pasa tal cual.
EXHAUSTIVAS = frozenset({"V013", "V190", "V501", "V731", "D115B", "D115C", "D121"})


def _canonizar(serie: pd.Series, variable: str) -> pd.Series:
    """Recorta espacios y aplica la tabla de equivalencias de la variable."""
    limpia = serie.astype(object).where(serie.notna())
    limpia = limpia.map(lambda v: v.strip() if isinstance(v, str) else v)

    tabla = EQUIVALENCIAS.get(variable)
    if not tabla:
        return limpia

    if variable in EXHAUSTIVAS:
        desconocidas = {v for v in limpia.dropna().unique()} - set(tabla)
        if desconocidas:
            log.warning(
                "%s: etiquetas sin equivalencia declarada %s. "
                "Revisa si un año nuevo cambió el rótulo antes de usar la serie.",
                variable, sorted(desconocidas))

    return limpia.map(lambda v: tabla.get(v, v) if isinstance(v, str) else v)


# --------------------------------------------------------------------------
# Agrupaciones derivadas
#
# Agregados que el dashboard presenta como una sola categoría. Se calculan sobre el
# microdato y no sobre los porcentajes ya tabulados: promediar porcentajes trata igual
# a un grupo de 4 200 casos y a uno de 12 800, y el resultado no corresponde a ninguna
# población. Como columna del microdato, el agregado usa el ponderador de la encuesta.
# --------------------------------------------------------------------------
DERIVADAS: dict[str, tuple[str, dict[str, str]]] = {
    "pareja_actual": ("V501", {
        "Casada": "Con pareja",
        "Conviviente": "Con pareja",
        "Separada": "Sin pareja",
        "Divorciada": "Sin pareja",
        "Viuda": "Sin pareja",
    }),
    "trabajo_12m": ("V731", {
        "Trabaja actualmente": "Trabajó",
        "Trabajó en el último año": "Trabajó",
        "Con trabajo, de licencia": "Trabajó",
        "No trabajó": "No trabajó",
    }),
    "etnia": ("S119D", {
        "Quechua": "Origen nativo",
        "Aimara": "Origen nativo",
        "Nativo/indígena amazónico": "Origen nativo",
        "Otro pueblo originario": "Origen nativo",
        "Afroperuano": "Afroperuano",
        "Blanco": "Blanco",
        "Mestizo": "Mestizo",
    }),
}

ORDEN_DERIVADAS = {
    "pareja_actual": ("Con pareja", "Sin pareja"),
    "trabajo_12m": ("Trabajó", "No trabajó"),
    "etnia": ("Origen nativo", "Afroperuano", "Mestizo", "Blanco"),
}


def _derivar(df: pd.DataFrame) -> pd.DataFrame:
    for destino, (origen, mapa) in DERIVADAS.items():
        if origen not in df.columns:
            continue
        valores = df[origen].astype(object).map(lambda v: mapa.get(v) if isinstance(v, str) else None)
        orden = ORDEN_DERIVADAS[destino]
        categorias_obs = [c for c in valores.dropna().unique()]
        df[destino] = pd.Categorical(
            valores,
            categories=list(orden) + sorted(c for c in categorias_obs if c not in orden),
            ordered=True,
        )
    return df


def normalizar(df: pd.DataFrame, copiar: bool = True) -> pd.DataFrame:
    """Normaliza las variables de corte y las convierte en categóricas ordenadas."""
    if copiar:
        df = df.copy()

    variables = set(EQUIVALENCIAS) | set(SOLO_LIMPIAR) | set(ORDEN)
    for variable in sorted(variables):
        if variable not in df.columns:
            continue

        limpia = _canonizar(df[variable], variable)

        for excluida in EXCLUIR.get(variable, ()):
            limpia = limpia.where(limpia != excluida)

        orden = ORDEN.get(variable)
        if orden:
            observadas = [c for c in limpia.dropna().unique()]
            categorias = list(orden) + sorted(c for c in observadas if c not in orden)
            limpia = pd.Categorical(limpia, categories=categorias, ordered=True)

        df[variable] = limpia

    return _derivar(df)
