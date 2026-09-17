"""Los indicadores calculados deben reproducir los cuadros publicados por el INEI."""

from __future__ import annotations

import pytest

from endes_violencia import tabulacion, validacion
from endes_violencia.reportes import AYUDA, INDICADORES_12M, INDICADORES_ALGUNA_VEZ

# Número de casos publicado por el INEI para el universo de mujeres alguna vez unidas
# seleccionadas y entrevistadas para el módulo de violencia (cuadro 12.1.1).
CASOS_INEI = {
    2022: (21321, 18397.60),
    2023: (21349, 18076.95),
    2024: (20398, 17435.53),
}


@pytest.fixture(scope="module")
def nacional(df):
    indicadores = {**INDICADORES_ALGUNA_VEZ, **INDICADORES_12M, **AYUDA}
    return tabulacion.tabular(df, indicadores)


@pytest.fixture(scope="module")
def comparacion(nacional):
    return validacion.comparar(nacional)


def test_referencia_no_esta_vacia():
    referencia = validacion.cargar_referencia()
    assert len(referencia) >= 40
    assert set(referencia.columns) >= {"cuadro", "variable", "anio", "valor_inei", "tolerancia"}


def test_todos_los_valores_de_referencia_se_calculan(comparacion):
    faltantes = comparacion.loc[comparacion["estado"] == "SIN DATO", "variable"].unique()
    assert not len(faltantes), f"Indicadores sin calcular: {sorted(faltantes)}"


def test_estimaciones_coinciden_con_el_inei(comparacion):
    fuera = comparacion.loc[comparacion["estado"] == "DIFIERE"]
    detalle = fuera[["cuadro", "variable", "anio", "valor_inei",
                     "estimacion", "diferencia"]].to_string(index=False)
    assert fuera.empty, f"Estimaciones fuera de tolerancia:\n{detalle}"


def test_errores_estandar_coinciden_con_el_inei(comparacion):
    """El estimador de linealización de Taylor debe reproducir la desviación estándar."""
    con_ee = comparacion.loc[comparacion["ee_inei"].notna()].copy()
    assert len(con_ee) >= 30
    fuera = con_ee.loc[con_ee["diferencia_ee"].abs() > 0.005]
    detalle = fuera[["variable", "anio", "ee_inei", "ee", "diferencia_ee"]].to_string(index=False)
    assert fuera.empty, f"Errores estándar fuera de tolerancia:\n{detalle}"


@pytest.mark.parametrize("anio", sorted(CASOS_INEI))
def test_universo_coincide_con_el_inei(df, anio):
    """El universo de mujeres alguna vez unidas debe cuadrar en casos y ponderación."""
    elegibles = df.loc[(df["anio"] == anio) & df["elegible"]]
    n_esperado, w_esperado = CASOS_INEI[anio]
    assert len(elegibles) == n_esperado
    assert elegibles["peso"].sum() == pytest.approx(w_esperado, abs=0.01)


def test_intervalos_de_confianza_coinciden(comparacion):
    con_ic = comparacion.loc[comparacion["ic_inf_inei"].notna()]
    assert len(con_ic) >= 30
    for _, fila in con_ic.iterrows():
        margen = 1.959963984540054 * fila["ee"]
        assert fila["estimacion"] - margen == pytest.approx(fila["ic_inf_inei"], abs=0.01)
        assert fila["estimacion"] + margen == pytest.approx(fila["ic_sup_inei"], abs=0.01)
