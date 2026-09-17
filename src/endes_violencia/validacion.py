"""Contraste de los indicadores calculados contra los valores publicados por el INEI."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .config import ARCHIVO_REFERENCIA_INEI

# Tolerancias por defecto según el número de decimales con que el INEI publica el valor.
TOLERANCIA_2_DECIMALES = 0.005
TOLERANCIA_1_DECIMAL = 0.05


def cargar_referencia(ruta: Path = ARCHIVO_REFERENCIA_INEI) -> pd.DataFrame:
    """Lee la tabla de valores oficiales extraídos de los cuadros del INEI."""
    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe {ruta}. Genérala con scripts/extraer_valores_inei.py."
        )
    return pd.read_csv(ruta)


def comparar(calculado: pd.DataFrame,
             referencia: pd.DataFrame | None = None,
             columna_valor: str = "estimacion") -> pd.DataFrame:
    """Compara una tabla de :func:`tabulacion.tabular` contra los valores del INEI.

    ``calculado`` debe traer las columnas ``anio`` y ``variable``; el cruce se hace
    contra ``variable`` y ``anio`` de la tabla de referencia.
    """
    referencia = cargar_referencia() if referencia is None else referencia

    cruce = referencia.merge(
        calculado[["anio", "variable", columna_valor, "ee", "n", "n_ponderado"]],
        on=["anio", "variable"], how="left", suffixes=("_inei", "_calc"),
    )

    cruce["diferencia"] = cruce[columna_valor] - cruce["valor_inei"]
    cruce["dentro_tolerancia"] = cruce["diferencia"].abs() <= cruce["tolerancia"]

    cruce["diferencia_ee"] = np.where(
        cruce["ee_inei"].notna(), cruce["ee"] - cruce["ee_inei"], np.nan)

    cruce["estado"] = np.select(
        [cruce[columna_valor].isna(), cruce["dentro_tolerancia"]],
        ["SIN DATO", "OK"], default="DIFIERE",
    )
    return cruce


def resumen(comparacion: pd.DataFrame) -> pd.DataFrame:
    """Resume el resultado de la validación por cuadro del INEI."""
    return (
        comparacion.groupby(["cuadro", "estado"], observed=True)
        .size().unstack(fill_value=0)
        .reset_index()
    )


def informe(comparacion: pd.DataFrame, columna_valor: str = "estimacion") -> pd.DataFrame:
    """Tabla legible con el valor calculado, el publicado y la diferencia."""
    columnas = ["cuadro", "indicador_inei", "anio", "valor_inei",
                columna_valor, "diferencia", "ee_inei", "ee", "estado"]
    salida = comparacion[columnas].copy()
    salida = salida.rename(columns={
        columna_valor: "valor_calculado",
        "indicador_inei": "indicador",
        "ee_inei": "ee_inei",
        "ee": "ee_calculado",
    })
    for c in ("valor_inei", "valor_calculado", "diferencia", "ee_inei", "ee_calculado"):
        salida[c] = salida[c].astype(float).round(3)
    return salida.sort_values(["cuadro", "indicador", "anio"]).reset_index(drop=True)


def todo_valida(comparacion: pd.DataFrame) -> bool:
    """True si todas las filas comparables quedaron dentro de la tolerancia."""
    return bool((comparacion["estado"] == "OK").all())
