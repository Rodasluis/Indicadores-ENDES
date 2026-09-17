"""Descarga los microdatos de la ENDES y construye la base consolidada.

Uso:
    python scripts/construir_base.py                 # todos los años configurados
    python scripts/construir_base.py 2023 2024       # solo algunos años
    python scripts/construir_base.py --sin-descarga   # usa lo que ya está en data/raw
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from endes_violencia import carga, config, descarga  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("anios", nargs="*", type=int, default=None,
                        help="años a procesar (por omisión, todos los configurados)")
    parser.add_argument("--sin-descarga", action="store_true",
                        help="no descargar; usar los archivos ya presentes en data/raw")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    config.crear_directorios()

    anios = tuple(args.anios) if args.anios else config.ANIOS
    if not args.sin_descarga:
        descarga.descargar(anios)

    base = carga.construir_base(anios)
    print(f"\nBase consolidada: {len(base):,} filas × {base.shape[1]} columnas")
    print(f"Guardada en {config.ARCHIVO_BASE}")
    print(base.groupby(config.COL_ANIO).size().to_string())


if __name__ == "__main__":
    main()
