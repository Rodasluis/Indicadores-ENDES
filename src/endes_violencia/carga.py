"""Lectura de los archivos .dta del INEI y construcción de la base consolidada."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pandas as pd

from .config import (
    ARCHIVO_BASE,
    ARCHIVO_BASE_MAESTRA,
    COL_ANIO,
    DIR_CRUDO,
    ENCUESTAS,
    LLAVE,
    MODULOS,
)

log = logging.getLogger(__name__)

# Variables conservadas al leer cada .dta. Se filtra en la lectura para no cargar
# más de mil columnas por año (la base completa no cabe cómodamente en memoria).
VARIABLES_BASE = {
    # identificación y diseño muestral
    "CASEID", "V000", "V001", "V002", "V003", "V004", "V005", "V007",
    "V021", "V022", "V023",
    # características sociodemográficas usadas como variables de corte
    "V012", "V013", "V024", "V025", "V044", "V101", "V106", "V149", "V150",
    "V151", "V190", "V191",
    # nupcialidad, actividad y empoderamiento
    "V501", "V502", "V503", "V504", "V505", "V701", "V704", "V714", "V715",
    "V716", "V717", "V729", "V730", "V731", "V739",
    "V743A", "V743B", "V743C", "V743D", "V743E", "V743F",
    "V744A", "V744B", "V744C", "V744D", "V744E",
    "V745A", "V745B", "V746",
}

# Familias completas que se conservan por prefijo.
PREFIJOS = ("D1", "S1023", "S119", "QI1003")


def _variables_a_leer(ruta: Path) -> list[str]:
    with pd.io.stata.StataReader(ruta) as lector:
        disponibles = list(lector.variable_labels())
    return [
        v for v in disponibles
        if v.upper() in VARIABLES_BASE or v.upper().startswith(PREFIJOS)
    ]


def buscar_dta(carpeta: Path, nombre: str) -> Path:
    """Localiza un .dta ignorando sufijos de año y mayúsculas.

    El INEI publica ``REC0111.dta`` en unos años y ``REC0111_2023.dta`` en otros.
    """
    patron = re.compile(rf"^{re.escape(nombre)}(_\d{{4}})?\.dta$", re.IGNORECASE)
    coincidencias = sorted(p for p in carpeta.rglob("*") if patron.match(p.name))
    if not coincidencias:
        raise FileNotFoundError(f"No se encontró {nombre}.dta bajo {carpeta}")
    if len(coincidencias) > 1:
        log.warning("varias coincidencias para %s, se usa %s", nombre, coincidencias[0].name)
    return coincidencias[0]


def leer_dta(ruta: Path) -> pd.DataFrame:
    """Lee un .dta conservando las etiquetas de valor como categorías."""
    df = pd.read_stata(ruta, columns=_variables_a_leer(ruta), convert_categoricals=True)
    df.columns = [c.upper() for c in df.columns]
    if LLAVE in df.columns:
        df[LLAVE] = df[LLAVE].astype(str).str.strip()
    return df


def _unir(izquierda: pd.DataFrame, derecha: pd.DataFrame) -> pd.DataFrame:
    """Une por CASEID descartando las columnas duplicadas del lado derecho."""
    duplicadas = [c for c in derecha.columns if c in izquierda.columns and c != LLAVE]
    return izquierda.merge(
        derecha.drop(columns=duplicadas), on=LLAVE, how="left", validate="one_to_one"
    )


def cargar_anio(anio: int, dir_crudo: Path = DIR_CRUDO) -> pd.DataFrame:
    """Lee y une todos los módulos de un año en un único DataFrame por mujer."""
    carpeta = dir_crudo / str(anio)
    if not carpeta.exists():
        raise FileNotFoundError(
            f"No hay datos para {anio} en {carpeta}. Ejecuta primero descarga.descargar()."
        )

    base = None
    for modulo, archivos in MODULOS.items():
        for nombre in archivos:
            df = leer_dta(buscar_dta(carpeta / f"modulo{modulo}", nombre))
            log.info("  %s/%s: %s filas, %s columnas", modulo, nombre, *df.shape)
            if nombre == ARCHIVO_BASE_MAESTRA:
                base = df
            elif base is None:
                raise RuntimeError(f"{ARCHIVO_BASE_MAESTRA} debe leerse antes que {nombre}")
            else:
                base = _unir(base, df)

    base[COL_ANIO] = anio
    return base


def _homogeneizar(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte categóricas a objeto para poder concatenar años con distintas etiquetas."""
    categoricas = [c for c in df.columns if isinstance(df[c].dtype, pd.CategoricalDtype)]
    if categoricas:
        df = df.assign(**{c: df[c].astype(object) for c in categoricas})
    return df


def _normalizar_tipos(df: pd.DataFrame) -> pd.DataFrame:
    """Uniformiza las columnas de objeto con tipos mezclados entre años.

    Algunas variables (p. ej. V704, ocupación de la pareja) llegan etiquetadas en unos
    años y como código numérico en otros; al concatenar quedan columnas con ``str`` y
    ``float`` a la vez, que parquet no puede serializar.
    """
    for columna in df.columns[df.dtypes == object]:
        valores = df[columna].dropna()
        if valores.map(type).nunique() > 1:
            df[columna] = df[columna].map(lambda v: v if pd.isna(v) else str(v))
            log.info("columna %s con tipos mixtos: convertida a texto", columna)
    return df


# Por encima de este número de valores distintos una columna no se guarda como
# categórica (deja de compensar; p. ej. CASEID, que es única por fila).
MAX_CATEGORIAS = 1000


def _comprimir(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte las columnas de etiquetas a ``category``.

    Las etiquetas de valor de Stata son texto repetido: guardarlas como objeto cuesta
    un puntero de 8 bytes por celda más el propio objeto, frente a 1-2 bytes por celda
    en categórica. En la base consolidada eso reduce el uso de memoria de ~1,5 GB a
    ~200 MB, lo que permite trabajar con ella en equipos modestos.
    """
    antes = df.memory_usage(deep=True).sum()
    for columna in df.columns[df.dtypes == object]:
        if df[columna].nunique(dropna=True) <= MAX_CATEGORIAS:
            df[columna] = df[columna].astype("category")
    despues = df.memory_usage(deep=True).sum()
    log.info("memoria: %.0f MB → %.0f MB", antes / 1e6, despues / 1e6)
    return df


def construir_base(anios: list[int] | tuple[int, ...] | None = None,
                   dir_crudo: Path = DIR_CRUDO,
                   guardar_en: Path | None = ARCHIVO_BASE) -> pd.DataFrame:
    """Consolida todos los años en una sola base (equivalente al ``append`` de Stata)."""
    anios = tuple(anios or ENCUESTAS)
    marcos = []
    for anio in anios:
        log.info("=== cargando ENDES %s ===", anio)
        marcos.append(_homogeneizar(cargar_anio(anio, dir_crudo)))

    base = pd.concat(marcos, axis=0, ignore_index=True)
    marcos.clear()
    base = _comprimir(_normalizar_tipos(base))
    log.info("base consolidada: %s filas, %s columnas", *base.shape)

    if guardar_en is not None:
        guardar_en.parent.mkdir(parents=True, exist_ok=True)
        base.to_parquet(guardar_en, index=False)
        log.info("guardada en %s", guardar_en)

    return base


def cargar_base(ruta: Path = ARCHIVO_BASE) -> pd.DataFrame:
    """Lee la base consolidada previamente guardada en parquet."""
    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe {ruta}. Ejecuta construir_base() o scripts/construir_base.py."
        )
    return pd.read_parquet(ruta)
