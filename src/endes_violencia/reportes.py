"""Definición de las tablas del reporte y de las variables de desagregación."""

from __future__ import annotations

import pandas as pd

from . import indicadores, tabulacion
from .indicadores import CONTROL, DECISIONES, HUMILLACION, JUSTIFICACION

# --------------------------------------------------------------------------
# Indicadores principales
# --------------------------------------------------------------------------
INDICADORES_ALGUNA_VEZ = {
    "violencia_total_alguna_vez": "Violencia total alguna vez",
    "violencia_psicologica_alguna_vez": "Violencia psicológica y/o verbal alguna vez",
    "violencia_fisica_alguna_vez": "Violencia física alguna vez",
    "violencia_sexual_alguna_vez": "Violencia sexual alguna vez",
    "violencia_fisica_o_sexual_alguna_vez": "Violencia física y/o sexual alguna vez",
}

INDICADORES_12M = {
    "violencia_total_12m": "Violencia total, últimos 12 meses",
    "violencia_psicologica_12m": "Violencia psicológica y/o verbal, últimos 12 meses",
    "violencia_fisica_12m": "Violencia física, últimos 12 meses",
    "violencia_sexual_12m": "Violencia sexual, últimos 12 meses",
    "violencia_fisica_o_sexual_12m": "Violencia física y/o sexual, últimos 12 meses",
}

POLIVICTIMIZACION = {
    "poli_fisica_psicologica_alguna_vez": "Física y psicológica (no sexual)",
    "poli_sexual_psicologica_alguna_vez": "Sexual y psicológica (no física)",
    "poli_fisica_sexual_alguna_vez": "Física y sexual (no psicológica)",
    "poli_triple_alguna_vez": "Física, sexual y psicológica",
}

COMPONENTES_PSICOLOGICA = {
    **{f"comp_{c}": e for c, e in CONTROL.items()},
    "control_alguna_vez": "Algún control",
    **{f"comp_{c}": e for c, e in HUMILLACION.items()},
    "amenazas_alguna_vez": "Alguna amenaza",
}

FACTORES = {
    "pareja_consume_alcohol": "La pareja consume bebidas alcohólicas",
    "pareja_consume_frecuente": "La pareja consume algunas veces o con frecuencia",
}

TOMA_DECISIONES = {f"decide_{c}": e for c, e in DECISIONES.items()}
JUSTIFICA_VIOLENCIA = {f"justifica_{c}": e for c, e in JUSTIFICACION.items()}

AYUDA = {
    "ayuda_personas_cercanas": "Buscó ayuda en personas cercanas",
    "ayuda_institucion": "Buscó ayuda en alguna institución",
    "ayuda_alguna": "Buscó ayuda en personas cercanas y/o en alguna institución",
}

FUENTES_AYUDA = {
    f"fuente_{indicadores.slug(e)}": e for e in indicadores.FUENTES_AYUDA_CERCANAS
}
INSTITUCIONES_AYUDA = {
    f"institucion_{indicadores.slug(e)}": e for e in indicadores.INSTITUCIONES
}

# --------------------------------------------------------------------------
# Variables de desagregación (cuadros 12.1 a 12.4 del INEI)
# --------------------------------------------------------------------------
CORTES = {
    "Grupo de edad": "V013",
    "Área de residencia": "V025",
    "Región natural": "V101",
    "Departamento": "V024",
    "Nivel educativo": "V149",
    "Quintil de riqueza": "V190",
    "Estado conyugal": "V501",
    "Sexo del jefe del hogar": "V151",
    "Trabajó en los últimos 12 meses": "V731",
    "Lengua materna": "S119",
    "Autoidentificación étnica": "S119D",
    "El padre golpeaba a la madre": "D121",
}


def construir_reportes(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Construye todas las tablas del reporte en formato ancho, listas para exportar."""
    hojas: dict[str, pd.DataFrame] = {}

    def agregar(nombre: str, indicadores_dict: dict[str, str], por: str | None = None,
                con_error: bool = True) -> None:
        tabla = tabulacion.tabular(df, indicadores_dict, por=por, con_error=con_error)
        if tabla.empty:
            return
        hojas[nombre] = tabla

    # --- series nacionales con precisión muestral
    agregar("Nacional_alguna_vez", INDICADORES_ALGUNA_VEZ)
    agregar("Nacional_12_meses", INDICADORES_12M)
    agregar("Polivictimizacion", POLIVICTIMIZACION)
    agregar("Componentes_psicologica", COMPONENTES_PSICOLOGICA)
    agregar("Busqueda_de_ayuda", AYUDA)
    agregar("Fuentes_ayuda_cercanas", FUENTES_AYUDA)
    agregar("Instituciones_ayuda", INSTITUCIONES_AYUDA)
    agregar("Factores_alcohol", FACTORES)
    agregar("Toma_de_decisiones", TOMA_DECISIONES)
    agregar("Justifica_violencia", JUSTIFICA_VIOLENCIA)

    # --- desagregaciones (sin error estándar: son muchas celdas)
    principales = {**INDICADORES_ALGUNA_VEZ, **INDICADORES_12M}
    for etiqueta, variable in CORTES.items():
        if variable not in df.columns:
            continue
        tabla = tabulacion.tabular(df, principales, por=variable, con_error=False)
        if not tabla.empty:
            hojas[f"Por_{_nombre_hoja(etiqueta)}"] = tabla

    # --- distribuciones porcentuales
    distribuciones = {
        "Dist_razones_no_ayuda": ("D120", None),
        "Dist_frecuencia_alcohol": ("D114", "pareja_consume_alcohol"),
    }
    for nombre, (variable, universo) in distribuciones.items():
        if variable in df.columns:
            hojas[nombre] = tabulacion.distribucion(df, variable, universo=universo)

    return hojas


def _nombre_hoja(etiqueta: str) -> str:
    reemplazos = str.maketrans("áéíóúÁÉÍÓÚñÑ ", "aeiouAEIOUnN_")
    return etiqueta.translate(reemplazos)[:26]
