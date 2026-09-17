"""Descarga y descompresión de los microdatos de la ENDES desde el portal del INEI."""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path

import requests
import urllib3

from .config import DIR_CRUDO, ENCUESTAS, MODULOS, URL_PLANTILLA

# El certificado TLS del portal del INEI suele estar mal encadenado; se desactiva
# la verificación solo para ese host y se silencia la advertencia asociada.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log = logging.getLogger(__name__)

TIEMPO_ESPERA = 300
INTENTOS = 3


def _descargar_zip(url: str, destino: Path) -> bool:
    """Descarga un zip con reintentos. Devuelve True si el archivo quedó disponible."""
    if destino.exists() and destino.stat().st_size > 0:
        log.info("ya existe: %s", destino.name)
        return True

    for intento in range(1, INTENTOS + 1):
        try:
            respuesta = requests.get(url, verify=False, timeout=TIEMPO_ESPERA)
            respuesta.raise_for_status()
            destino.write_bytes(respuesta.content)
            log.info("descargado %s (%.1f MB)", destino.name, len(respuesta.content) / 1e6)
            return True
        except requests.RequestException as exc:
            log.warning("intento %d/%d falló para %s: %s", intento, INTENTOS, url, exc)

    log.error("no se pudo descargar %s", url)
    return False


def _descomprimir(zip_path: Path, destino: Path) -> None:
    if destino.exists() and any(destino.iterdir()):
        return
    destino.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(destino)
    log.info("descomprimido %s", zip_path.name)


def descargar_anio(anio: int, dir_crudo: Path = DIR_CRUDO) -> Path:
    """Descarga y descomprime todos los módulos requeridos de un año.

    Returns
    -------
    Path
        Carpeta del año, con una subcarpeta por módulo.
    """
    if anio not in ENCUESTAS:
        raise KeyError(
            f"El año {anio} no está en config.ENCUESTAS. "
            "Agrega su identificador de encuesta del portal del INEI."
        )

    id_encuesta = ENCUESTAS[anio]
    carpeta_anio = dir_crudo / str(anio)
    carpeta_anio.mkdir(parents=True, exist_ok=True)

    for modulo in MODULOS:
        url = URL_PLANTILLA.format(id_encuesta=id_encuesta, modulo=modulo)
        zip_path = carpeta_anio / f"modulo{modulo}.zip"
        if _descargar_zip(url, zip_path):
            _descomprimir(zip_path, carpeta_anio / f"modulo{modulo}")

    return carpeta_anio


def descargar(anios: list[int] | tuple[int, ...] | None = None,
              dir_crudo: Path = DIR_CRUDO) -> None:
    """Descarga los microdatos de todos los años solicitados."""
    for anio in anios or ENCUESTAS:
        log.info("=== ENDES %s (id %s) ===", anio, ENCUESTAS[anio])
        descargar_anio(anio, dir_crudo)
