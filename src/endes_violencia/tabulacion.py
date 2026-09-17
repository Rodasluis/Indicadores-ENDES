"""Estimación ponderada con errores estándar de muestreo complejo.

La ENDES es una muestra bietápica, estratificada e independiente por departamento.
El INEI publica para cada estimación su desviación estándar, intervalo de confianza
al 95 % y coeficiente de variación. Este módulo los reproduce mediante linealización
de Taylor sobre la razón ponderada, tomando ``V022`` como estrato y ``V001`` como
conglomerado.

VALIDADO: los errores estándar y coeficientes de variación obtenidos coinciden con
los publicados en los cuadros 12.1.1, 12.4.1, 12.4.2 y 12.10 con dos decimales.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import COL_ANIO, COL_PESO, VAR_CONGLOMERADO, VAR_ESTRATO

# Cuantil normal al 95 %; se define aquí para no arrastrar una dependencia de scipy.
Z_95 = 1.959963984540054


def _var_razon(y: np.ndarray, w: np.ndarray,
               estrato: np.ndarray, conglomerado: np.ndarray, razon: float) -> float:
    """Varianza de una razón ponderada por linealización de Taylor."""
    varianza = 0.0
    for h in np.unique(estrato):
        en_estrato = estrato == h
        conglomerados = conglomerado[en_estrato]
        unicos = np.unique(conglomerados)
        n_h = len(unicos)
        if n_h < 2:  # estrato con un solo conglomerado: no aporta varianza estimable
            continue
        w_h, y_h = w[en_estrato], y[en_estrato]
        residuos = np.array([
            (w_h[conglomerados == c] * y_h[conglomerados == c]).sum()
            - razon * w_h[conglomerados == c].sum()
            for c in unicos
        ])
        varianza += n_h / (n_h - 1) * (np.sum(residuos ** 2) - residuos.sum() ** 2 / n_h)
    return varianza


def estimar_proporcion(df: pd.DataFrame, indicador: str,
                       con_error: bool = True) -> dict[str, float]:
    """Estima una proporción ponderada (en porcentaje) y su precisión.

    Los casos con ``indicador`` missing quedan fuera del denominador: así se
    respeta el universo definido al construir cada indicador.
    """
    hay_disenio = VAR_ESTRATO in df.columns and VAR_CONGLOMERADO in df.columns
    columnas = [indicador, COL_PESO] + ([VAR_ESTRATO, VAR_CONGLOMERADO] if hay_disenio else [])

    datos = df.loc[df[indicador].notna(), columnas]
    datos = datos.loc[datos[COL_PESO].notna()]

    if datos.empty or datos[COL_PESO].sum() <= 0:
        return {"estimacion": np.nan, "ee": np.nan, "ic_inf": np.nan,
                "ic_sup": np.nan, "cv": np.nan, "n": 0, "n_ponderado": 0.0}

    y = datos[indicador].to_numpy(dtype=float)
    w = datos[COL_PESO].to_numpy(dtype=float)
    razon = float((w * y).sum() / w.sum())

    resultado = {
        "estimacion": 100 * razon,
        "n": int(len(datos)),
        "n_ponderado": float(w.sum()),
    }

    if not con_error or not hay_disenio:
        resultado.update({"ee": np.nan, "ic_inf": np.nan, "ic_sup": np.nan, "cv": np.nan})
        return resultado

    estrato = datos[VAR_ESTRATO].to_numpy()
    conglomerado = datos[VAR_CONGLOMERADO].to_numpy()
    ee = 100 * np.sqrt(_var_razon(y, w, estrato, conglomerado, razon)) / w.sum()

    resultado.update({
        "ee": ee,
        "ic_inf": resultado["estimacion"] - Z_95 * ee,
        "ic_sup": resultado["estimacion"] + Z_95 * ee,
        "cv": 100 * ee / resultado["estimacion"] if resultado["estimacion"] else np.nan,
    })
    return resultado


def tabular(df: pd.DataFrame, indicadores: dict[str, str] | list[str],
            por: str | None = None, con_error: bool = True,
            col_anio: str = COL_ANIO) -> pd.DataFrame:
    """Tabula uno o varios indicadores por año y, opcionalmente, por una variable de corte.

    Parameters
    ----------
    indicadores
        Nombres de columna, o un diccionario ``{columna: etiqueta legible}``.
    por
        Variable de desagregación (por ejemplo ``"V025"`` para área de residencia).
    con_error
        Calcula desviación estándar, IC 95 % y coeficiente de variación.

    Returns
    -------
    DataFrame en formato largo con una fila por (año, categoría, indicador).
    """
    if not isinstance(indicadores, dict):
        indicadores = {c: c for c in indicadores}
    indicadores = {c: e for c, e in indicadores.items() if c in df.columns}

    # Se trabaja solo con las columnas necesarias: agrupar el DataFrame completo
    # (varios cientos de columnas) copia cada grupo entero y es innecesariamente caro.
    necesarias = [col_anio, COL_PESO, *indicadores]
    necesarias += [c for c in (VAR_ESTRATO, VAR_CONGLOMERADO, por) if c and c in df.columns]
    df = df[list(dict.fromkeys(necesarias))]

    filas = []
    for anio, grupo_anio in df.groupby(col_anio, sort=True, observed=True):
        if por is None:
            grupos = [(None, grupo_anio)]
        else:
            valido = grupo_anio.loc[grupo_anio[por].notna()]
            grupos = list(valido.groupby(por, sort=True, observed=True))

        for categoria, grupo in grupos:
            for columna, etiqueta in indicadores.items():
                fila = {"anio": anio, "indicador": etiqueta, "variable": columna}
                if por is not None:
                    fila[por] = categoria
                fila.update(estimar_proporcion(grupo, columna, con_error=con_error))
                filas.append(fila)

    columnas = ["anio"] + ([por] if por else []) + [
        "indicador", "variable", "estimacion", "ee", "ic_inf", "ic_sup",
        "cv", "n", "n_ponderado",
    ]
    return pd.DataFrame(filas)[columnas]


def a_formato_ancho(tabla: pd.DataFrame, valor: str = "estimacion",
                    decimales: int = 2) -> pd.DataFrame:
    """Convierte la salida de :func:`tabular` a una tabla año × indicador."""
    indice = [c for c in tabla.columns if c not in
              {"indicador", "variable", "estimacion", "ee", "ic_inf", "ic_sup",
               "cv", "n", "n_ponderado"}]
    ancha = tabla.pivot_table(index=indice, columns="indicador", values=valor,
                              sort=False, observed=True)
    ancha = ancha[[i for i in tabla["indicador"].unique() if i in ancha.columns]]
    return ancha.round(decimales).reset_index()


def distribucion(df: pd.DataFrame, variable: str, universo: str | None = None,
                 col_anio: str = COL_ANIO, decimales: int = 2) -> pd.DataFrame:
    """Distribución porcentual ponderada de una variable categórica, por año.

    ``universo`` es el nombre de una columna booleana que restringe el denominador.
    """
    columnas = list(dict.fromkeys([col_anio, COL_PESO, variable] +
                                  ([universo] if universo else [])))
    datos = df[columnas]
    if universo is not None:
        datos = datos.loc[datos[universo].fillna(0).astype(bool)]
    datos = datos.loc[datos[variable].notna() & datos[COL_PESO].notna()]

    tabla = (
        datos.groupby([col_anio, variable], observed=True)[COL_PESO].sum()
        .unstack(fill_value=0.0)
    )
    tabla = 100 * tabla.div(tabla.sum(axis=1), axis=0)
    return tabla.round(decimales).reset_index()
