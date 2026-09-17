"""Calcula todos los indicadores, valida contra el INEI y exporta los reportes.

Uso:
    python scripts/generar_reportes.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from endes_violencia import carga, config, indicadores, tabulacion, validacion  # noqa: E402
from endes_violencia.reportes import (  # noqa: E402
    AYUDA,
    CORTES,
    INDICADORES_12M,
    INDICADORES_ALGUNA_VEZ,
    construir_reportes,
)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    config.crear_directorios()

    base = carga.cargar_base()
    df = indicadores.construir_todo(base)

    # ---------------- validación contra los cuadros del INEI ----------------
    nacional = tabulacion.tabular(df, {**INDICADORES_ALGUNA_VEZ, **INDICADORES_12M, **AYUDA})
    comparacion = validacion.comparar(nacional)
    informe = validacion.informe(comparacion)

    print("\n=== VALIDACIÓN CONTRA LOS CUADROS DEL INEI ===")
    print(informe.to_string(index=False))
    print("\n" + validacion.resumen(comparacion).to_string(index=False))

    ruta_validacion = config.DIR_TABLAS / "validacion_inei.csv"
    informe.to_csv(ruta_validacion, index=False, encoding="utf-8-sig")
    print(f"\nInforme de validación → {ruta_validacion}")

    if not validacion.todo_valida(comparacion):
        print("\n*** Hay indicadores fuera de tolerancia: revisa el informe. ***")

    # ---------------- reportes ----------------
    hojas = construir_reportes(df)
    salida = config.DIR_TABLAS / "indicadores_violencia_endes.xlsx"
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        informe.to_excel(writer, sheet_name="Validacion_INEI", index=False)
        for nombre, tabla in hojas.items():
            tabla.to_excel(writer, sheet_name=nombre[:31], index=False)
    print(f"Reporte Excel ({len(hojas) + 1} hojas) → {salida}")

    for nombre, tabla in hojas.items():
        tabla.to_csv(config.DIR_CSV / f"{nombre}.csv", index=False, encoding="utf-8-sig")
    print(f"Tablas en CSV → {config.DIR_CSV}")

    # ---------------- microdatos analíticos ----------------
    ruta = config.DIR_CSV / "microdatos_violencia.csv"
    columnas = [config.COL_ANIO, "CASEID", config.COL_PESO, config.VAR_ESTRATO,
                config.VAR_CONGLOMERADO, config.COL_ELEGIBLE]
    columnas += [c for c in df.columns
                 if c.startswith(("violencia_", "poli_", "control_", "humillacion_",
                                  "amenazas_", "ayuda_", "decide_", "justifica_",
                                  "pareja_consume_"))]
    columnas += list(CORTES.values())
    columnas = [c for c in dict.fromkeys(columnas) if c in df.columns]
    df.loc[df[config.COL_ELEGIBLE], columnas].to_csv(ruta, index=False, encoding="utf-8-sig")
    print(f"Microdatos analíticos ({len(columnas)} columnas) → {ruta}")


if __name__ == "__main__":
    main()
