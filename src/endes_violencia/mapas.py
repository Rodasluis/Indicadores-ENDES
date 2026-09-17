"""Geometría administrativa para los mapas del dashboard.

Fuente: **Perú-maps** — límites administrativos del Perú en GeoJSON, con pipeline
reproducible y validado. https://github.com/Rodasluis/Peru-maps

Se publican los tres niveles, repartidos para que el navegador descargue solo lo que
mira:

===========================  ==========  ====================================
archivo                      cuándo      qué trae
===========================  ==========  ====================================
``departamentos.geojson``    siempre     los 25 departamentos
``ubigeos.json``             siempre     jerarquía de nombres (sin geometría)
``geo/<dd>.json``            al elegir   provincias y distritos de ese departamento
===========================  ==========  ====================================

Cada nivel se simplifica a la escala con que se mira: el departamento se ve entero
en la pantalla, la provincia dentro de su departamento y el distrito dentro de su
provincia, así que el detalle necesario aumenta al bajar de nivel.

> Los límites de Perú-maps no son oficiales y son solo para uso estadístico: sirven
> para agregar y mapear indicadores, no para deslindes ni fines legales.
"""

from __future__ import annotations

import json
import logging
import unicodedata
from pathlib import Path

import requests
from shapely.geometry import mapping, shape

from .config import DIR_CRUDO

log = logging.getLogger(__name__)

REPOSITORIO = "https://github.com/Rodasluis/Peru-maps"
BASE_RAW = "https://raw.githubusercontent.com/Rodasluis/Peru-maps/main/salida"

# nivel → (archivo remoto, tolerancia de simplificación en grados, decimales)
NIVELES = {
    "departamento": ("departamento_simplificado.geojson", 0.02, 3),
    "provincia": ("provincia_simplificado.geojson", 0.005, 4),
    "distrito": ("distrito_simplificado.geojson", 0.002, 4),
}

EXCEPCIONES = {"DE": "de", "LA": "La", "DEL": "del", "Y": "y"}


def _nombre_propio(nombre: str) -> str:
    """'MADRE DE DIOS' → 'Madre de Dios'; 'LA LIBERTAD' → 'La Libertad'."""
    palabras = nombre.strip().split()
    return " ".join(
        EXCEPCIONES[p.upper()] if i > 0 and p.upper() in EXCEPCIONES else p.capitalize()
        for i, p in enumerate(palabras)
    )


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def descargar(nivel: str = "departamento", destino: Path | None = None,
              forzar: bool = False) -> Path:
    """Descarga una capa de Perú-maps a ``data/raw`` (idempotente)."""
    if nivel not in NIVELES:
        raise KeyError(f"nivel desconocido: {nivel}. Usa uno de {sorted(NIVELES)}")

    archivo = NIVELES[nivel][0]
    destino = destino or (DIR_CRUDO / f"peru_{nivel}.geojson")
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and destino.stat().st_size > 0 and not forzar:
        log.info("%s ya descargado: %s", nivel, destino.name)
        return destino

    respuesta = requests.get(f"{BASE_RAW}/{archivo}", timeout=300)
    respuesta.raise_for_status()
    destino.write_bytes(respuesta.content)
    log.info("Perú-maps · %s descargado (%.1f MB)", nivel, len(respuesta.content) / 1e6)
    return destino


def descargar_todo(forzar: bool = False) -> dict[str, Path]:
    return {n: descargar(n, forzar=forzar) for n in NIVELES}


# --------------------------------------------------------------------------
# Simplificación
# --------------------------------------------------------------------------
def _redondear(geometria: dict, decimales: int) -> dict:
    def rec(coords):
        if isinstance(coords[0], (int, float)):
            return [round(float(c), decimales) for c in coords]
        return [rec(c) for c in coords]

    return {"type": geometria["type"], "coordinates": rec(geometria["coordinates"])}


def contar_vertices(geometria: dict) -> int:
    def rec(coords):
        return 1 if isinstance(coords[0], (int, float)) else sum(rec(c) for c in coords)

    return rec(geometria["coordinates"])


def _aligerar(feature: dict, tolerancia: float, decimales: int) -> dict:
    geometria = shape(feature["geometry"]).simplify(tolerancia, preserve_topology=True)
    if geometria.is_empty:
        geometria = shape(feature["geometry"])
    return _redondear(mapping(geometria), decimales)


def _leer(nivel: str) -> list[dict]:
    ruta = DIR_CRUDO / f"peru_{nivel}.geojson"
    if not ruta.exists():
        raise FileNotFoundError(f"No existe {ruta}. Ejecuta mapas.descargar('{nivel}').")
    return json.loads(ruta.read_text(encoding="utf-8"))["features"]


# --------------------------------------------------------------------------
# Capas publicadas
# --------------------------------------------------------------------------
def construir(ruta: Path | None = None, tolerancia: float | None = None) -> dict:
    """Capa de los 25 departamentos, con ``dep`` igual al ``V024`` de la ENDES."""
    _, tol_defecto, decimales = NIVELES["departamento"]
    tolerancia = tolerancia if tolerancia is not None else tol_defecto

    origen = (json.loads(ruta.read_text(encoding="utf-8"))["features"] if ruta
              else _leer("departamento"))

    features, antes, despues = [], 0, 0
    for f in origen:
        antes += contar_vertices(f["geometry"])
        geometria = _aligerar(f, tolerancia, decimales)
        despues += contar_vertices(geometria)
        features.append({
            "type": "Feature",
            "properties": {"dep": _nombre_propio(f["properties"]["nombre"]),
                           "u": f["properties"]["ubigeo"]},
            "geometry": geometria,
        })

    features.sort(key=lambda f: _sin_tildes(f["properties"]["dep"]))
    log.info("departamentos: %s → %s vértices", antes, despues)

    return {
        "type": "FeatureCollection",
        "meta": _meta(tolerancia),
        "features": features,
    }


def _meta(tolerancia: float) -> dict:
    return {
        "fuente": "Perú-maps · límites administrativos del Perú",
        "url": REPOSITORIO,
        "nota": ("Límites no oficiales, solo para uso estadístico. "
                 "Simplificados para visualización web."),
        "tolerancia_grados": tolerancia,
    }


def construir_indice() -> dict:
    """Jerarquía departamento → provincia → distrito, solo nombres y ubigeos.

    Alimenta los desplegables sin necesidad de descargar geometría. Se publica la
    jerarquía **completa**, no solo los lugares con servicios: quien use el botón de
    ubicación tiene que poder aterrizar en su distrito aunque allí no haya sede, y
    saberlo es justamente la información que necesita.
    """
    indice: dict[str, dict] = {}

    for f in _leer("departamento"):
        p = f["properties"]
        indice[p["ubigeo"]] = {"n": _nombre_propio(p["nombre"]), "p": {}}

    for f in _leer("provincia"):
        p = f["properties"]
        departamento = indice.get(p["ubigeo_departamento"])
        if departamento is not None:
            departamento["p"][p["ubigeo"]] = {"n": _nombre_propio(p["nombre"]), "d": {}}

    huerfanos = 0
    for f in _leer("distrito"):
        p = f["properties"]
        departamento = indice.get(p["ubigeo_departamento"])
        provincia = departamento["p"].get(p["ubigeo_provincia"]) if departamento else None
        if provincia is None:
            huerfanos += 1
            continue
        provincia["d"][p["ubigeo"]] = _nombre_propio(p["nombre"])

    if huerfanos:
        log.warning("%s distritos sin provincia en el índice", huerfanos)

    distritos = sum(len(pr["d"]) for de in indice.values() for pr in de["p"].values())
    provincias = sum(len(de["p"]) for de in indice.values())
    log.info("índice: %s departamentos, %s provincias, %s distritos",
             len(indice), provincias, distritos)
    return indice


def construir_geo_por_departamento() -> dict[str, dict]:
    """Un paquete por departamento con sus provincias y sus distritos.

    Se descarga solo cuando alguien elige ese departamento, así la carga inicial no
    arrastra los 1 892 distritos del país.
    """
    _, tol_prov, dec_prov = NIVELES["provincia"]
    _, tol_dist, dec_dist = NIVELES["distrito"]

    paquetes: dict[str, dict] = {}

    for f in _leer("provincia"):
        p = f["properties"]
        paquete = paquetes.setdefault(p["ubigeo_departamento"], {"provincias": [], "distritos": []})
        paquete["provincias"].append({
            "type": "Feature",
            "properties": {"u": p["ubigeo"], "n": _nombre_propio(p["nombre"])},
            "geometry": _aligerar(f, tol_prov, dec_prov),
        })

    for f in _leer("distrito"):
        p = f["properties"]
        paquete = paquetes.setdefault(p["ubigeo_departamento"], {"provincias": [], "distritos": []})
        paquete["distritos"].append({
            "type": "Feature",
            "properties": {"u": p["ubigeo"], "p": p["ubigeo_provincia"],
                           "n": _nombre_propio(p["nombre"])},
            "geometry": _aligerar(f, tol_dist, dec_dist),
        })

    for codigo, paquete in paquetes.items():
        paquete["meta"] = {"departamento": codigo, "fuente": REPOSITORIO}

    log.info("geometría por departamento: %s paquetes", len(paquetes))
    return paquetes


def verificar_cruce(capa: dict, departamentos_endes: set[str]) -> list[str]:
    """Devuelve los departamentos de la capa que no existen en la ENDES."""
    en_capa = {f["properties"]["dep"] for f in capa["features"]}
    return sorted(en_capa - departamentos_endes)
