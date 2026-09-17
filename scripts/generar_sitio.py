"""Genera los datos que consume el dashboard de `site/`.

Produce:
    site/data/indicadores.json    indicadores por año y característica
    site/data/directorio.json     servicios de atención del MIMP
    site/data/departamentos.geojson  geometría departamental para los mapas

Uso:
    python scripts/generar_sitio.py
    python scripts/generar_sitio.py --sin-descarga   # usa lo ya descargado en data/raw
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from endes_violencia import carga, config, directorio, indicadores, mapas, sitio  # noqa: E402

DIR_SITIO = config.RAIZ / "site" / "data"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sin-descarga", action="store_true",
                        help="usa el directorio del MIMP ya descargado en data/raw")
    parser.add_argument("--indent", type=int, default=None,
                        help="indentación del JSON (por omisión, compacto)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    DIR_SITIO.mkdir(parents=True, exist_ok=True)

    # ── indicadores ────────────────────────────────────────────────────────
    df = indicadores.construir_todo(carga.cargar_base())
    datos = sitio.construir_datos(df)
    sitio.escribir(datos, DIR_SITIO / "indicadores.json", indent=args.indent)

    hojas = sum(len(v) for k, v in datos.items() if k != "meta")
    print(f"\nIndicadores: {hojas} hojas, años {datos['meta']['anios']}")
    general = {r["Año"]: r["violencia_total"] for r in datos["alguna_vez"]["General_Anual"]}
    print("Violencia total alguna vez:", general)

    # ── geometría: jerarquía y capas ───────────────────────────────────────
    if not args.sin_descarga:
        mapas.descargar_todo()

    indice = mapas.construir_indice()
    sitio.escribir(indice, DIR_SITIO / "ubigeos.json", indent=args.indent)

    capa = mapas.construir()
    sitio.escribir(capa, DIR_SITIO / "departamentos.geojson", indent=args.indent)

    en_endes = {r["V024"] for r in datos["alguna_vez"]["Departamento"]}
    huerfanos = mapas.verificar_cruce(capa, en_endes)
    if huerfanos:
        print(f"\n(!) Departamentos del mapa sin equivalente en la ENDES: {huerfanos}")
    else:
        print(f"\nGeometría: {len(capa['features'])} departamentos, cruzan todos con la ENDES")

    # Provincias y distritos, en un paquete por departamento que el navegador
    # descarga solo cuando alguien elige ese departamento.
    paquetes = mapas.construir_geo_por_departamento()
    dir_geo = DIR_SITIO / "geo"
    dir_geo.mkdir(parents=True, exist_ok=True)
    for codigo, paquete in sorted(paquetes.items()):
        sitio.escribir(paquete, dir_geo / f"{codigo}.json", indent=args.indent)

    pesos = sorted((f.stat().st_size, f.name) for f in dir_geo.glob("*.json"))
    provincias = sum(len(p["provincias"]) for p in paquetes.values())
    distritos = sum(len(p["distritos"]) for p in paquetes.values())
    print(f"  {len(paquetes)} paquetes: {provincias} provincias, {distritos} distritos")
    print(f"  peso: menor {pesos[0][0]/1024:.0f} KB ({pesos[0][1]}), "
          f"mayor {pesos[-1][0]/1024:.0f} KB ({pesos[-1][1]})")

    # ── directorio de servicios ────────────────────────────────────────────
    if not args.sin_descarga:
        directorio.descargar()
    dir_datos = directorio.construir(indice=indice)
    sitio.escribir(dir_datos, DIR_SITIO / "directorio.json", indent=args.indent)

    print(f"\nDirectorio: {dir_datos['meta']['total']} servicios")
    for tipo, n in sorted(dir_datos["meta"]["por_tipo"].items(), key=lambda x: -x[1]):
        print(f"  {tipo:5} {n:4}")
    con_ubigeo = sum(1 for s in dir_datos["servicios"] if s["ubigeo"])
    print(f"  con ubigeo cruzado: {con_ubigeo}/{dir_datos['meta']['total']}")

    # ── índice de archivos publicados ──────────────────────────────────────
    manifiesto = {
        "indicadores": {
            "archivo": "indicadores.json",
            "anios": datos["meta"]["anios"],
            "generado": datos["meta"]["generado"],
        },
        "directorio": {
            "archivo": "directorio.json",
            "total": dir_datos["meta"]["total"],
            "fuente": dir_datos["meta"]["url"],
        },
        "geometria": {
            "archivos": ["departamentos.geojson", "ubigeos.json", "geo/<ubigeo>.json"],
            "departamentos": len(capa["features"]),
            "provincias": provincias,
            "distritos": distritos,
            "fuente": capa["meta"]["url"],
        },
    }
    (DIR_SITIO / "manifiesto.json").write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nArchivos en {DIR_SITIO}")


if __name__ == "__main__":
    main()
