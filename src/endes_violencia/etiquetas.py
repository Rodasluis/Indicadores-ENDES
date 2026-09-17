"""Comparación segura de etiquetas de valor de Stata.

Los microdatos del INEI llegan como variables categóricas cuyas *etiquetas de texto*
son las que definen los indicadores (``"Si"``, ``"Nunca"``, ``"Algunas veces"``…).
Todas las comparaciones del proyecto pasan por estas funciones para garantizar que:

1. Se comparan etiquetas completas y no subcadenas: ``str.contains("Entrevistada")``
   captura también ``"Entrevistada y otra persona"`` y altera el indicador.
2. Nunca se muta la columna original. En pandas, ``Serie.astype(str)`` sobre una
   columna de dtype ``string`` puede convertir los ``NA`` en la cadena literal
   ``"<NA>"`` *in situ*; a partir de ahí ``notna()`` devuelve ``True`` para todo y
   corrompe en silencio cualquier denominador calculado después.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


def _a_objeto(serie: pd.Series) -> np.ndarray:
    """Copia la serie a un arreglo de objetos sin tocar la columna original."""
    return serie.to_numpy(dtype=object, copy=True)


def es(serie: pd.Series, valores: Iterable[str]) -> np.ndarray:
    """Máscara booleana: la etiqueta de ``serie`` es exactamente una de ``valores``."""
    valores = {str(v) for v in valores}
    arreglo = _a_objeto(serie)
    return np.array([v in valores for v in arreglo], dtype=bool)


def alguna(df: pd.DataFrame, columnas: Iterable[str], valores: Iterable[str]) -> np.ndarray:
    """Máscara booleana: al menos una de ``columnas`` toma alguna de ``valores``.

    Las columnas ausentes en ``df`` se ignoran; las presentes pero totalmente
    vacías simplemente no aportan casos.
    """
    mascara = np.zeros(len(df), dtype=bool)
    for col in columnas:
        if col in df.columns:
            mascara |= es(df[col], valores)
    return mascara


def preguntada(serie: pd.Series) -> np.ndarray:
    """Máscara booleana: la pregunta fue formulada (el valor no es missing)."""
    return serie.notna().to_numpy(dtype=bool)


def columnas_presentes(df: pd.DataFrame, columnas: Iterable[str]) -> list[str]:
    """Subconjunto de ``columnas`` que existe en ``df`` y tiene al menos un dato."""
    return [c for c in columnas if c in df.columns and df[c].notna().any()]
