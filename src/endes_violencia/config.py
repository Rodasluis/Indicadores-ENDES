"""Configuración central del proyecto: rutas, años y variables de diseño muestral."""

from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------
# Rutas
# --------------------------------------------------------------------------
RAIZ = Path(__file__).resolve().parents[2]

DIR_DATOS = Path(os.environ.get("ENDES_DATA_DIR", RAIZ / "data"))
DIR_CRUDO = DIR_DATOS / "raw"          # zips y .dta descargados del INEI
DIR_INTERMEDIO = DIR_DATOS / "interim"  # base consolidada en parquet
DIR_SALIDAS = Path(os.environ.get("ENDES_OUTPUT_DIR", RAIZ / "outputs"))
DIR_TABLAS = DIR_SALIDAS / "tablas"
DIR_CSV = DIR_SALIDAS / "csv"
DIR_VALIDACION = RAIZ / "validacion"
DIR_REFERENCIAS = RAIZ / "referencias"

ARCHIVO_REFERENCIA_INEI = DIR_VALIDACION / "valores_referencia_inei.csv"
ARCHIVO_BASE = DIR_INTERMEDIO / "endes_violencia.parquet"


def crear_directorios() -> None:
    """Crea las carpetas de trabajo si no existen."""
    for d in (DIR_CRUDO, DIR_INTERMEDIO, DIR_TABLAS, DIR_CSV):
        d.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------
# Años disponibles y su identificador de encuesta en el portal del INEI
#
# El identificador es el número que aparece en la URL de descarga:
#   https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/{ID}-Modulo{MOD}.zip
# Para incorporar un año nuevo basta con agregar su ID a este diccionario.
# --------------------------------------------------------------------------
ENCUESTAS: dict[int, str] = {
    2021: "760",
    2022: "786",
    2023: "910",
    2024: "968",
    2025: "1038",
}

ANIOS = tuple(sorted(ENCUESTAS))

# --------------------------------------------------------------------------
# Módulos y archivos requeridos
#
# Solo se descargan los módulos que contienen las variables de violencia:
#   1631 · REC0111   Características generales de la mujer (incluye V005, V044, diseño)
#   1631 · REC91     Módulo Perú: etnicidad y búsqueda de ayuda institucional (S1023*)
#   1635 · RE516171  Nupcialidad, actividad y empoderamiento (V501, V502, V731, V739, V743*, V744*)
#   1637 · REC84DV   Módulo de violencia doméstica (D101*, D103*, D105*, D113-D121, QI1003*)
# --------------------------------------------------------------------------
MODULOS: dict[str, tuple[str, ...]] = {
    "1631": ("REC0111", "REC91"),
    "1635": ("RE516171",),
    "1637": ("REC84DV",),
}

ARCHIVO_BASE_MAESTRA = "REC0111"  # archivo que define el universo de mujeres entrevistadas
LLAVE = "CASEID"

URL_PLANTILLA = (
    "https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/{id_encuesta}-Modulo{modulo}.zip"
)

# --------------------------------------------------------------------------
# Variables de diseño muestral
#
# Reproducen exactamente los errores estándar publicados por el INEI:
# estimador de linealización de Taylor con estrato = V022 y conglomerado = V001.
# --------------------------------------------------------------------------
VAR_PESO = "V005"          # factor de ponderación (se divide entre 1 000 000)
VAR_ESTRATO = "V022"       # estrato de muestreo
VAR_CONGLOMERADO = "V001"  # conglomerado / UPM
ESCALA_PESO = 1_000_000

COL_ANIO = "anio"
COL_PESO = "peso"
COL_ELEGIBLE = "elegible"
