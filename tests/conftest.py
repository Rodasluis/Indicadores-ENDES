from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from endes_violencia import carga, config, indicadores  # noqa: E402


@pytest.fixture(scope="session")
def base_disponible() -> bool:
    return config.ARCHIVO_BASE.exists()


@pytest.fixture(scope="session")
def df(base_disponible):
    """Base consolidada con todos los indicadores construidos.

    Requiere haber ejecutado ``scripts/construir_base.py``. Si la base no está
    disponible, las pruebas que dependen de los microdatos se omiten.
    """
    if not base_disponible:
        pytest.skip(
            "No hay base consolidada en data/interim. "
            "Ejecuta scripts/construir_base.py para correr las pruebas de validación."
        )
    return indicadores.construir_todo(carga.cargar_base())
