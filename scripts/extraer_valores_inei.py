"""Extrae de los cuadros publicados por el INEI los valores usados para validar.

Los libros de Excel del informe de la ENDES tienen encabezados combinados, hojas
duplicadas y columnas rotuladas con años que no corresponden al dato que contienen,
por lo que no se pueden leer con ``pandas.read_excel``. Se usa un mapa explícito de
celdas de la fila "Total" de cada cuadro, verificado a mano contra el PDF del informe.

Genera ``validacion/valores_referencia_inei.csv``. Ese archivo está versionado en el
repositorio, de modo que la validación funciona sin necesidad de tener los libros
originales (``referencias/cuadros_inei/``, no versionados).

Uso:
    python scripts/extraer_valores_inei.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import openpyxl
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from endes_violencia.config import ARCHIVO_REFERENCIA_INEI, DIR_REFERENCIAS  # noqa: E402

LIBRO_CAP12 = DIR_REFERENCIAS / "cuadros_inei" / "Cap. 12" / "Cap. 12_2025.xlsx"

# Columnas (1-indexadas) de la fila "Total" en los cuadros con serie 2021-2025.
# Cada año trae: valor, desviación estándar, IC inferior, IC superior, CV.
# Para 2021 el INEI solo publica el valor puntual.
DISENIO_A = {  # cuadros 12.1.1 y 12.4.1
    2021: (26, None, None, None, None),
    2022: (28, 29, 30, 31, 32),
    2023: (40, 41, 42, 43, 44),
    2024: (52, 53, 54, 55, 56),
    2025: (64, 65, 66, 67, 68),
}
DISENIO_B = {  # cuadros 12.1, 12.4.2 y 12.10 (primer bloque)
    2021: (2, None, None, None, None),
    2022: (4, 5, 6, 7, 8),
    2023: (14, 15, 16, 17, 18),
    2024: (24, 25, 26, 27, 28),
    2025: (34, 35, 36, 37, 38),
}
DISENIO_C = {  # cuadros 12.4.2 y 12.10 (segundo bloque)
    2021: (44, None, None, None, None),
    2022: (46, 47, 48, 49, 50),
    2023: (56, 57, 58, 59, 60),
    2024: (66, 67, 68, 69, 70),
    2025: (76, 77, 78, 79, 80),
}

# (cuadro, hoja, fila, diseño de columnas, variable del proyecto, etiqueta)
MAPA = [
    ("12.1.1", "12.1.1", 9, DISENIO_A, "violencia_total_alguna_vez",
     "Violencia total alguna vez"),
    ("12.1.1", "12.1.1", 11, DISENIO_A, "violencia_psicologica_alguna_vez",
     "Violencia psicológica y/o verbal alguna vez"),
    ("12.1.1", "12.1.1", 12, DISENIO_A, "violencia_fisica_alguna_vez",
     "Violencia física alguna vez"),
    ("12.1.1", "12.1.1", 13, DISENIO_A, "violencia_sexual_alguna_vez",
     "Violencia sexual alguna vez"),
    ("12.4.1", "12.4.1", 9, DISENIO_A, "violencia_fisica_o_sexual_12m",
     "Violencia física y/o sexual, últimos 12 meses"),
    ("12.4.1", "12.4.1", 11, DISENIO_A, "violencia_fisica_12m",
     "Violencia física, últimos 12 meses"),
    ("12.4.1", "12.4.1", 12, DISENIO_A, "violencia_sexual_12m",
     "Violencia sexual, últimos 12 meses"),
    ("12.4.2", "12.4.2", 11, DISENIO_B, "violencia_total_12m",
     "Violencia total, últimos 12 meses"),
    ("12.4.2", "12.4.2", 11, DISENIO_C, "violencia_psicologica_12m",
     "Violencia psicológica y/o verbal, últimos 12 meses"),
    ("12.10", "12.10", 10, DISENIO_B, "ayuda_personas_cercanas",
     "Buscó ayuda en personas cercanas"),
    ("12.10", "12.10", 10, DISENIO_C, "ayuda_institucion",
     "Buscó ayuda en alguna institución"),
]

# Valores puntuales de 2021 con dos decimales, tomados de los cuadros donde el INEI
# sí los publica con esa precisión (12.1.1 los redondea a un decimal).
CORRECCIONES_2021 = {
    ("12.1", "violencia_total_alguna_vez"): ("12.1", 11, 2),
    ("12.2", "violencia_psicologica_alguna_vez"): ("12.2", 12, 20),
}


def _num(hoja, fila: int, columna: int | None) -> float | None:
    if columna is None:
        return None
    valor = hoja.cell(row=fila, column=columna).value
    return float(valor) if isinstance(valor, (int, float)) else None


def _decimales(valor: float | None) -> int:
    if valor is None:
        return 2
    texto = f"{valor:.10f}".rstrip("0")
    entero, _, decimal = texto.partition(".")
    return 2 if len(decimal.rstrip("0")) >= 2 else 1


def extraer(libro_path: Path = LIBRO_CAP12) -> pd.DataFrame:
    libro = openpyxl.load_workbook(libro_path, read_only=True, data_only=True)
    filas = []

    for cuadro, hoja_nombre, fila, disenio, variable, etiqueta in MAPA:
        hoja = libro[hoja_nombre]
        for anio, (c_val, c_ee, c_inf, c_sup, c_cv) in disenio.items():
            valor = _num(hoja, fila, c_val)
            if valor is None:
                continue
            filas.append({
                "cuadro": cuadro,
                "indicador_inei": etiqueta,
                "variable": variable,
                "anio": anio,
                "valor_inei": round(valor, 4),
                "ee_inei": _num(hoja, fila, c_ee),
                "ic_inf_inei": _num(hoja, fila, c_inf),
                "ic_sup_inei": _num(hoja, fila, c_sup),
                "cv_inei": _num(hoja, fila, c_cv),
                "tolerancia": 0.005 if _decimales(valor) == 2 else 0.05,
            })

    # Sustituye los valores de 2021 por su versión con dos decimales cuando existe.
    for (cuadro_origen, variable), (hoja_nombre, fila, columna) in CORRECCIONES_2021.items():
        valor = _num(libro[hoja_nombre], fila, columna)
        if valor is None:
            continue
        objetivo = [f for f in filas if f["variable"] == variable and f["anio"] == 2021]
        for f in objetivo:
            f["valor_inei"] = round(float(valor), 4)
            f["tolerancia"] = 0.005
            f["cuadro"] = f"{f['cuadro']} / {cuadro_origen}"

    libro.close()

    tabla = pd.DataFrame(filas).sort_values(["cuadro", "variable", "anio"])
    return tabla.reset_index(drop=True)


def main() -> None:
    if not LIBRO_CAP12.exists():
        raise SystemExit(
            f"No se encontró {LIBRO_CAP12}.\n"
            "Descarga los cuadros del informe ENDES desde el INEI y colócalos en "
            "referencias/cuadros_inei/."
        )
    tabla = extraer()
    ARCHIVO_REFERENCIA_INEI.parent.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(ARCHIVO_REFERENCIA_INEI, index=False, encoding="utf-8")
    print(f"{len(tabla)} valores de referencia escritos en {ARCHIVO_REFERENCIA_INEI}")
    print(tabla.to_string(index=False))


if __name__ == "__main__":
    main()
