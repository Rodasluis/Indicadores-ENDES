"""Serialización de los indicadores al formato que consume el dashboard.

El sitio de `site/` lee tres archivos JSON generados aquí. El contrato es deliberadamente explícito —una constante por bloque— para que
renombrar un indicador rompa una prueba en lugar de dejar un gráfico vacío.

Formato de ``indicadores.json``::

    {
      "meta":       {"anios": [...], "generado": "...", "fuente": "..."},
      "alguna_vez": {"<hoja>": [{"Año": 2024, "violencia_total": 51.96, ...}, ...]},
      "doce_meses": {...},
      "factores":   {"<hoja>": [{"Año": 2024, "<columna>": 41.3, ...}, ...]}
    }
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import tabulacion
from .config import COL_ANIO

log = logging.getLogger(__name__)

DECIMALES = 2

# --------------------------------------------------------------------------
# Bloques de prevalencia: una hoja por variable de corte
# --------------------------------------------------------------------------
# Nombres cortos con que el frontend identifica cada forma de violencia.
FORMAS = {
    "violencia_fisica": "violencia_fisica",
    "violencia_sexual": "violencia_sexual",
    "violencia_psicologica": "violencia_psicologica",
    "violencia_total": "violencia_total",
    "poli_fisica_psicologica": "violencia_fis_psic",
    "poli_sexual_psicologica": "violencia_sex_psic",
    "poli_fisica_sexual": "violencia_fis_sex",
    "poli_triple": "violencia_triple",
}

# hoja → variable de corte (None = total nacional)
HOJAS_PREVALENCIA: dict[str, str | None] = {
    "General_Anual": None,
    "Departamento": "V024",
    "Edad": "V013",
    "Lugar de Residencia": "V025",
    "Logro Académico": "V149",
    "Indice de Riqueza": "V190",
    "Trabajó últimos 12 meses": "V731",
    "Estado Civil": "V501",
    "Autoidentificación étnica": "S119D",
    "Violencia por Madre": "D115B",
    "Violencia por Padre": "D115C",
    "Violencia Interparental": "D121",
    # agrupaciones derivadas (ver categorias.DERIVADAS)
    "Situación de pareja": "pareja_actual",
    "Condición laboral": "trabajo_12m",
    "Grupo étnico": "etnia",
}

VENTANAS = {"alguna_vez": "alguna_vez", "doce_meses": "12m"}

# --------------------------------------------------------------------------
# Bloque de factores: cada hoja es una tabla de indicadores por año
# --------------------------------------------------------------------------
from .indicadores import CONTROL, DECISIONES, INSTITUCIONES, JUSTIFICACION  # noqa: E402
from .indicadores import FUENTES_AYUDA_CERCANAS, slug  # noqa: E402

HOJAS_FACTORES: dict[str, dict[str, str]] = {
    "Control_Pareja": {f"comp_{c}": e for c, e in CONTROL.items()},
    "Toma_Decisiones": {f"decide_{c}": e for c, e in DECISIONES.items()},
    "Justificacion": {f"justifica_{c}": e for c, e in JUSTIFICACION.items()},
    "Ayuda_Informal": {f"fuente_{slug(e)}": e for e in FUENTES_AYUDA_CERCANAS},
    "Ayuda_Institucional": {f"institucion_{slug(e)}": e for e in INSTITUCIONES},
    "Busqueda_Ayuda": {
        "ayuda_personas_cercanas": "En personas cercanas",
        "ayuda_institucion": "En alguna institución",
        "ayuda_alguna": "En cualquiera de los dos",
    },
}

# Hojas que son una distribución porcentual de una variable categórica
HOJAS_DISTRIBUCION: dict[str, tuple[str, str | None]] = {
    "Alcohol": ("D114", "pareja_consume_alcohol"),
    "Barreras": ("D120", None),
}


def _redondear(valor: float | None) -> float | None:
    return None if valor is None or pd.isna(valor) else round(float(valor), DECIMALES)


def _tabla_prevalencia(df: pd.DataFrame, sufijo: str, corte: str | None) -> list[dict]:
    """Una fila por (año, categoría) con las ocho formas de violencia."""
    indicadores = {f"{col}_{sufijo}": alias for col, alias in FORMAS.items()}
    tabla = tabulacion.tabular(df, indicadores, por=corte, con_error=False)
    if tabla.empty:
        return []

    filas: list[dict] = []
    claves = [COL_ANIO] + ([corte] if corte else [])
    for valores, grupo in tabla.groupby(claves, sort=False, observed=True):
        valores = valores if isinstance(valores, tuple) else (valores,)
        fila: dict = {"Año": int(valores[0])}
        if corte:
            fila[corte] = str(valores[1])
        for _, r in grupo.iterrows():
            fila[r["indicador"]] = _redondear(r["estimacion"])
        # n sin ponderar del grupo: sirve para marcar estimaciones poco fiables
        fila["n"] = int(grupo["n"].max())
        # Categorías declaradas pero sin casos en el universo (p. ej. el grupo de
        # edad 12-14, fuera del rango de la encuesta) se publicarían como 0 %.
        if fila["n"] == 0:
            continue
        filas.append(fila)
    return filas


def _tabla_factores(df: pd.DataFrame, indicadores: dict[str, str]) -> list[dict]:
    tabla = tabulacion.tabular(df, indicadores, con_error=False)
    if tabla.empty:
        return []
    filas = []
    for anio, grupo in tabla.groupby(COL_ANIO, sort=True, observed=True):
        fila = {"Año": int(anio)}
        for _, r in grupo.iterrows():
            fila[r["indicador"]] = _redondear(r["estimacion"])
        fila["n"] = int(grupo["n"].max())
        filas.append(fila)
    return filas


def _tabla_distribucion(df: pd.DataFrame, variable: str, universo: str | None) -> list[dict]:
    tabla = tabulacion.distribucion(df, variable, universo=universo, decimales=DECIMALES)
    if tabla.empty:
        return []
    filas = []
    for _, r in tabla.iterrows():
        fila = {"Año": int(r[COL_ANIO])}
        for col in tabla.columns:
            if col != COL_ANIO:
                fila[str(col)] = _redondear(r[col])
        filas.append(fila)
    return filas


def construir_datos(df: pd.DataFrame) -> dict:
    """Arma el diccionario completo de ``indicadores.json``."""
    datos: dict = {}

    for bloque, sufijo in VENTANAS.items():
        log.info("serializando bloque %s", bloque)
        datos[bloque] = {
            hoja: _tabla_prevalencia(df, sufijo, corte)
            for hoja, corte in HOJAS_PREVALENCIA.items()
        }

    log.info("serializando bloque factores")
    factores = {n: _tabla_factores(df, ind) for n, ind in HOJAS_FACTORES.items()}
    factores.update({
        n: _tabla_distribucion(df, var, uni)
        for n, (var, uni) in HOJAS_DISTRIBUCION.items()
    })
    datos["factores"] = factores

    anios = sorted(int(a) for a in df[COL_ANIO].dropna().unique())
    datos["meta"] = {
        "anios": anios,
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fuente": "INEI · Encuesta Demográfica y de Salud Familiar (ENDES)",
        "universo": ("Mujeres de 15 a 49 años alguna vez unidas, seleccionadas y "
                     "entrevistadas para el módulo de violencia"),
        "nota": ("Estimaciones ponderadas. Validadas contra los cuadros 12.1, 12.1.1, "
                 "12.2, 12.4.1, 12.4.2 y 12.10 del informe de la ENDES."),
    }
    return datos


def escribir(datos: dict, ruta: Path, indent: int | None = None) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        json.dumps(datos, ensure_ascii=False, indent=indent, allow_nan=False),
        encoding="utf-8",
    )
    log.info("%s (%.0f KB)", ruta, ruta.stat().st_size / 1024)
    return ruta
