"""Indicadores de violencia de pareja a partir de los microdatos de la ENDES (INEI, Perú).

Uso típico::

    from endes_violencia import carga, indicadores, tabulacion

    base = carga.cargar_base()
    df = indicadores.construir_todo(base)
    tabla = tabulacion.tabular(df, {"violencia_total_alguna_vez": "Total"})
"""

from . import (
    carga,
    categorias,
    config,
    descarga,
    directorio,
    etiquetas,
    indicadores,
    mapas,
    reportes,
    sitio,
    tabulacion,
    validacion,
)

__all__ = [
    "carga",
    "categorias",
    "config",
    "descarga",
    "directorio",
    "etiquetas",
    "indicadores",
    "mapas",
    "reportes",
    "sitio",
    "tabulacion",
    "validacion",
]

__version__ = "1.1.0"
