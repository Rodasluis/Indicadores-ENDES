"""Directorio de servicios de atención del MIMP.

Fuente pública: *Consolidado Directorio Nacional* del Observatorio Nacional de la
Violencia contra las Mujeres y los Integrantes del Grupo Familiar (MIMP).

Del consolidado se conservan únicamente los **servicios de atención frente a la
violencia**; el archivo incluye además servicios de adopciones, adulto mayor,
discapacidad y primera infancia que no corresponden a este dashboard.

Los nombres de departamento se alinean con los de la ENDES (``V024``) para poder
cruzar el directorio con los indicadores.
"""

from __future__ import annotations

import logging
import unicodedata
from pathlib import Path

import pandas as pd
import requests
import urllib3

from .config import DIR_CRUDO

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log = logging.getLogger(__name__)

URL_MIMP = "https://www.mimp.gob.pe/omep/Consolidado_Directorio_Nacional_2026.xlsx"
HOJA = "SERVICIOS MIMP"
ARCHIVO_LOCAL = "directorio_mimp.xlsx"

# --------------------------------------------------------------------------
# Servicios de atención frente a la violencia (clave → prefijo del campo CENTRO)
# --------------------------------------------------------------------------
SERVICIOS = {
    "CEM": {
        "centro": "Centro Emergencia Mujer y Familia",
        "nombre": "Centro Emergencia Mujer (CEM)",
        "descripcion": "Atención integral: orientación legal, defensa judicial, "
                       "consejería psicológica y asistencia social.",
    },
    "SAR": {
        "centro": "Servicio de Atención Rural - SAR",
        "nombre": "Servicio de Atención Rural (SAR)",
        "descripcion": "Atención itinerante en comunidades rurales y zonas de "
                       "difícil acceso donde no hay CEM.",
    },
    "SAU": {
        "centro": "Servicio de Atención Urgente - SAU",
        "nombre": "Servicio de Atención Urgente (SAU)",
        "descripcion": "Respuesta inmediata ante riesgo severo: traslado y "
                       "acompañamiento en situaciones de emergencia.",
    },
    "HRT": {
        "centro": "Hogares de Refugio Temporal - HRT",
        "nombre": "Hogar de Refugio Temporal (HRT)",
        "descripcion": "Acogida temporal para víctimas de violencia familiar, "
                       "sexual y/o de género.",
    },
    "CAI": {
        "centro": "Centro de Atencion Institucional - CAI",
        "nombre": "Centro de Atención Institucional (CAI)",
        "descripcion": "Reeducación de personas agresoras de violencia familiar.",
    },
}

# Servicios nacionales sin sede física; se muestran como canales, no en el buscador.
CANALES_NACIONALES = ("Linea 100", "Chat 100")

# MIMP → ENDES (V024). El MIMP separa Lima en dos ámbitos; la ENDES no.
DEPARTAMENTOS = {
    "Lima Metropolitana": "Lima",
    "Lima Provincias": "Lima",
    "Madre De Dios": "Madre de Dios",
}

# Columnas del consolidado que se publican. Se omite "Coodinador/a": el dashboard
# orienta a quien busca ayuda hacia el servicio, no hacia una persona concreta,
# y el nombre no aporta a esa tarea. Para incluirlo, agrégalo a esta tupla.
COLUMNAS = ("Departamento", "Provincia", "Distrito", "Centro de Atención",
            "Dirección", "Teléfono", "COORD_X", "COORD_Y", "Ubigeo")


def _ubigeo(valor) -> str:
    """Normaliza el ubigeo del consolidado a seis dígitos.

    Excel lo entrega como número y pierde el cero inicial: 70101 es 070101. Es la llave
    con la que cada sede se ata a su distrito en Perú-maps.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    try:
        return str(int(float(valor))).zfill(6)
    except (TypeError, ValueError):
        texto = _texto(valor)
        return texto.zfill(6) if texto.isdigit() else ""


def descargar(destino: Path | None = None, forzar: bool = False) -> Path:
    """Descarga el consolidado del MIMP a ``data/raw`` (idempotente)."""
    destino = destino or (DIR_CRUDO / ARCHIVO_LOCAL)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and destino.stat().st_size > 0 and not forzar:
        log.info("directorio MIMP ya descargado: %s", destino)
        return destino

    respuesta = requests.get(URL_MIMP, verify=False, timeout=180)
    respuesta.raise_for_status()
    destino.write_bytes(respuesta.content)
    log.info("directorio MIMP descargado (%.0f KB)", len(respuesta.content) / 1024)
    return destino


def _texto(valor) -> str:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    return " ".join(str(valor).split())


def _telefono(valor) -> str:
    texto = _texto(valor)
    if not texto:
        return ""
    if texto.replace(".", "").isdigit():
        texto = str(int(float(texto)))
    return texto


# Límites del territorio peruano; descarta coordenadas mal digitadas o vacías.
LIMITES = {"lon": (-81.5, -68.5), "lat": (-18.5, 0.5)}


def _coordenada(valor, eje: str) -> float | None:
    try:
        numero = float(str(valor).strip())
    except (TypeError, ValueError):
        return None
    if numero != numero:  # NaN
        return None
    minimo, maximo = LIMITES[eje]
    if not minimo <= numero <= maximo:
        log.debug("coordenada fuera de rango (%s=%s)", eje, numero)
        return None
    return round(numero, 6)


def _clave_servicio(centro: str) -> str | None:
    normal = _normalizar(centro)
    for clave, cfg in SERVICIOS.items():
        if _normalizar(cfg["centro"]) == normal:
            return clave
    return None


def _normalizar(texto: str) -> str:
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    return " ".join(sin_tildes.lower().split())


def _mapa_de_ubigeos(indice: dict) -> dict[str, dict]:
    """Aplana la jerarquía a ``ubigeo de distrito → nombres de los tres niveles``."""
    plano = {}
    for u_dep, departamento in indice.items():
        for u_prov, provincia in departamento["p"].items():
            for u_dist, nombre in provincia["d"].items():
                plano[u_dist] = {
                    "dep": departamento["n"], "prov": provincia["n"], "dist": nombre,
                    "u_dep": u_dep, "u_prov": u_prov,
                }
    return plano


def construir(ruta: Path | None = None, indice: dict | None = None) -> dict:
    """Lee el consolidado y devuelve el directorio listo para publicar.

    Si se pasa ``indice`` (la jerarquía de :func:`mapas.construir_indice`), cada sede
    se ata a su distrito por **ubigeo** y adopta los nombres oficiales del INEI, de modo
    que el buscador, el mapa y los indicadores se refieran a las mismas unidades: sin
    ese cruce, "Lima Metropolitana" del MIMP y "Lima" de la ENDES son lugares
    distintos.
    """
    ruta = ruta or (DIR_CRUDO / ARCHIVO_LOCAL)
    if not ruta.exists():
        raise FileNotFoundError(f"No existe {ruta}. Ejecuta directorio.descargar() primero.")

    bruto = pd.read_excel(ruta, sheet_name=HOJA)
    bruto.columns = [str(c).strip() for c in bruto.columns]

    faltantes = [c for c in COLUMNAS + ("CENTRO",) if c not in bruto.columns]
    if faltantes:
        raise ValueError(
            f"El consolidado del MIMP cambió de estructura; faltan columnas: {faltantes}"
        )

    oficial = _mapa_de_ubigeos(indice) if indice else {}
    servicios: list[dict] = []
    descartados: dict[str, int] = {}
    sin_cruce: list[str] = []

    for _, fila in bruto.iterrows():
        clave = _clave_servicio(_texto(fila["CENTRO"]))
        if clave is None:
            centro = _texto(fila["CENTRO"]) or "(sin centro)"
            descartados[centro] = descartados.get(centro, 0) + 1
            continue

        departamento = _texto(fila["Departamento"])
        ubigeo = _ubigeo(fila.get("Ubigeo"))
        lugar = oficial.get(ubigeo)
        if oficial and lugar is None:
            sin_cruce.append(ubigeo or "(vacío)")

        servicios.append({
            "tipo": clave,
            "ubigeo": ubigeo,
            # Nombres oficiales cuando el ubigeo cruza; si no, los del consolidado.
            "departamento": lugar["dep"] if lugar else DEPARTAMENTOS.get(departamento, departamento),
            "provincia": lugar["prov"] if lugar else _texto(fila["Provincia"]),
            "distrito": lugar["dist"] if lugar else _texto(fila["Distrito"]),
            "ubigeo_dep": lugar["u_dep"] if lugar else ubigeo[:2],
            "ubigeo_prov": lugar["u_prov"] if lugar else ubigeo[:4],
            "ambito": departamento,
            "nombre": _texto(fila["Centro de Atención"]),
            "direccion": _texto(fila["Dirección"]),
            "telefono": _telefono(fila["Teléfono"]),
            "lat": _coordenada(fila["COORD_Y"], "lat"),
            "lon": _coordenada(fila["COORD_X"], "lon"),
        })

    if sin_cruce:
        log.warning("%s sedes sin distrito en Perú-maps: %s",
                    len(sin_cruce), sorted(set(sin_cruce))[:10])

    servicios.sort(key=lambda s: (s["departamento"], s["provincia"], s["distrito"], s["nombre"]))
    log.info("directorio: %s servicios de violencia; %s registros de otros programas omitidos",
             len(servicios), sum(descartados.values()))

    conteo: dict[str, int] = {}
    for s in servicios:
        conteo[s["tipo"]] = conteo.get(s["tipo"], 0) + 1

    return {
        "meta": {
            "fuente": "MIMP · Consolidado Directorio Nacional",
            "url": URL_MIMP,
            "total": len(servicios),
            "por_tipo": conteo,
            "nota": ("Solo servicios de atención frente a la violencia. "
                     "Verifica siempre el horario y la vigencia del servicio antes de acudir."),
        },
        "tipos": {k: {"nombre": v["nombre"], "descripcion": v["descripcion"]}
                  for k, v in SERVICIOS.items()},
        "servicios": servicios,
    }
