"""Pruebas de la lógica de construcción de indicadores (sin depender de los microdatos)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from endes_violencia import etiquetas, indicadores, tabulacion


# --------------------------------------------------------------------------
# etiquetas.py
# --------------------------------------------------------------------------
def test_es_compara_etiqueta_completa_no_subcadena():
    serie = pd.Series(["Entrevistada", "Entrevistada y otra persona", "Esposo/compañero"])
    assert etiquetas.es(serie, ["Entrevistada"]).tolist() == [True, False, False]


def test_es_no_muta_la_columna_original():
    """El bug clásico: astype(str) sobre dtype string convierte los NA en '<NA>' in situ."""
    df = pd.DataFrame({"x": pd.array(["Si", None, "No"], dtype="string")})
    etiquetas.es(df["x"], ["Si"])
    assert df["x"].isna().sum() == 1
    assert etiquetas.preguntada(df["x"]).tolist() == [True, False, True]


def test_alguna_ignora_columnas_ausentes_y_vacias():
    df = pd.DataFrame({"A": ["Si", "No"], "B": [None, None]})
    assert etiquetas.alguna(df, ["A", "B", "NO_EXISTE"], ["Si"]).tolist() == [True, False]


# --------------------------------------------------------------------------
# indicadores.py
# --------------------------------------------------------------------------
def test_nunca_cuenta_como_violencia_alguna_vez_pero_no_en_12_meses():
    """"Nunca" significa "ocurrió, pero no en los últimos 12 meses"."""
    assert "Nunca" in indicadores.SI_ALGUNA_VEZ
    assert "Nunca" not in indicadores.SI_ULTIMOS_12M
    assert "No" not in indicadores.SI_ALGUNA_VEZ


def test_decide_acepta_las_etiquetas_de_2021_y_las_posteriores():
    """ENDES 2021 usa "Ambos" donde 2022+ usa "Entrevistada y esposo/compañero"."""
    assert "Ambos" in indicadores.DECIDE_SOLA_O_CON_PAREJA
    assert "Entrevistada y esposo/compañero" in indicadores.DECIDE_SOLA_O_CON_PAREJA
    # y no debe incluir las decisiones tomadas con terceros
    assert "Entrevistada y otra persona" not in indicadores.DECIDE_SOLA_O_CON_PAREJA


def test_otro_pariente_masculino_no_es_otra_persona():
    """D119XJ es "otro pariente masculino": pertenece a los parientes de la mujer."""
    assert "D119XJ" in indicadores.FUENTES_AYUDA_CERCANAS["Otro pariente de la mujer"]
    assert "D119XJ" not in indicadores.FUENTES_AYUDA_CERCANAS["Otra persona"]


def _base_sintetica() -> pd.DataFrame:
    """Cuatro mujeres: elegible con violencia reciente, elegible con violencia antigua,
    elegible sin violencia y no elegible."""
    return pd.DataFrame({
        "V005": [1_000_000] * 4,
        "V001": [1, 1, 2, 2],
        "V022": [1, 1, 2, 2],
        "V044": ["Mujer seleccionada y entrevistada"] * 3 + ["Mujer No sabeleccionada"],
        "V502": ["Actualmente casada", "Anteriormente casada", "Actualmente casada", "Nunca casada"],
        "D105A": ["Algunas veces", "Nunca", "No", None],
        "D105H": ["No", "No", "No", None],
        "D101A": ["Si", "No", "No", None],
        "D103A": ["No", "No", "No", None],
        "D103B": ["No", "No", "No", None],
        "D103D": ["No", "No", "No", None],
        "QI1003AN": ["Algunas veces", None, None, None],
        "D119Y": ["Buscó ayuda de alguien", "No buscó ayuda", None, None],
        "S1023AZ": ["No", "Si", None, None],
        "D113": ["Si", "No", "No", None],
        "D114": ["Mucha frecuencia", None, None, None],
        "anio": [2024] * 4,
    })


@pytest.fixture
def sintetica():
    df = indicadores.marcar_universo(_base_sintetica())
    df = indicadores.construir_violencia(df)
    return indicadores.construir_busqueda_ayuda(df)


def test_universo_excluye_no_seleccionadas_y_nunca_casadas(sintetica):
    assert sintetica["elegible"].tolist() == [True, True, True, False]


def test_violencia_fisica_por_ventana_temporal(sintetica):
    # "Algunas veces" cuenta en ambas ventanas; "Nunca" solo en "alguna vez"
    assert sintetica["violencia_fisica_alguna_vez"].tolist()[:3] == [1.0, 1.0, 0.0]
    assert sintetica["violencia_fisica_12m"].tolist()[:3] == [1.0, 0.0, 0.0]


def test_indicadores_son_nan_fuera_del_universo(sintetica):
    assert np.isnan(sintetica["violencia_total_alguna_vez"].iloc[3])


def test_polivictimizacion_es_excluyente(sintetica):
    fila = sintetica.iloc[0]
    assert fila["poli_fisica_psicologica_alguna_vez"] == 1.0
    assert fila["poli_triple_alguna_vez"] == 0.0


def test_ayuda_institucion_usa_la_negativa_de_s1023az(sintetica):
    # S1023AZ = "No, nunca ha buscado ayuda": responder "No" implica que sí acudió
    assert sintetica["ayuda_institucion"].tolist()[:2] == [1.0, 0.0]
    assert np.isnan(sintetica["ayuda_institucion"].iloc[2])


# --------------------------------------------------------------------------
# tabulacion.py
# --------------------------------------------------------------------------
def test_denominador_excluye_los_missing(sintetica):
    resultado = tabulacion.estimar_proporcion(sintetica, "violencia_fisica_alguna_vez")
    assert resultado["n"] == 3          # la no elegible queda fuera
    assert resultado["estimacion"] == pytest.approx(200 / 3)


def test_estimacion_ponderada_usa_el_peso():
    df = pd.DataFrame({
        "y": [1.0, 0.0],
        "peso": [3.0, 1.0],
        "V022": [1, 1],
        "V001": [1, 2],
        "anio": [2024, 2024],
    })
    assert tabulacion.estimar_proporcion(df, "y")["estimacion"] == pytest.approx(75.0)


def test_estrato_con_un_solo_conglomerado_no_rompe():
    df = pd.DataFrame({
        "y": [1.0, 0.0, 1.0],
        "peso": [1.0, 1.0, 1.0],
        "V022": [1, 1, 9],   # el estrato 9 tiene un único conglomerado
        "V001": [1, 2, 3],
        "anio": [2024] * 3,
    })
    resultado = tabulacion.estimar_proporcion(df, "y")
    assert np.isfinite(resultado["ee"])


def test_tabular_devuelve_una_fila_por_anio_e_indicador(sintetica):
    tabla = tabulacion.tabular(
        sintetica,
        {"violencia_fisica_alguna_vez": "Física", "violencia_sexual_alguna_vez": "Sexual"},
    )
    assert len(tabla) == 2
    assert list(tabla["indicador"]) == ["Física", "Sexual"]
