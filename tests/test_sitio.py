"""El dashboard de `site/` depende del formato exacto que emite `sitio.py`.

Estas pruebas fijan ese contrato: si se renombra un indicador o una hoja, falla aquí
en vez de dejar una barra en cero en el tablero publicado.
"""

from __future__ import annotations

import json
import re

import pytest

from endes_violencia import config, sitio, validacion

DIR_SITIO = config.RAIZ / "site"
ARCHIVO_INDICADORES = DIR_SITIO / "data" / "indicadores.json"
ARCHIVO_DIRECTORIO = DIR_SITIO / "data" / "directorio.json"
ARCHIVO_GEOMETRIA = DIR_SITIO / "data" / "departamentos.geojson"

# Columnas que el frontend lee por nombre (site/assets/app.js).
COLUMNAS_FRONTEND = {
    "Control_Pareja": [
        "Es celoso o molesto si conversa con otro hombre",
        "La acusa frecuentemente de ser infiel",
        "Insiste siempre en saber a dónde va",
        "Le impide que visite o la visiten sus amistades",
        "Desconfía con el dinero",
        "Trata de limitar las visitas o el contacto con su familia",
    ],
    "Toma_Decisiones": [
        "Gasto del propio dinero", "Cuidado de su propia salud",
        "Grandes compras del hogar", "Compras para necesidades diarias",
        "Visitas a familiares o amigos", "Qué alimentos cocinar cada día",
    ],
    "Ayuda_Institucional": [
        "Comisaría", "Juzgado", "Fiscalía", "Defensoría Municipal (DEMUNA)",
        "Ministerio de la Mujer y Poblaciones Vulnerables", "Defensoría del Pueblo",
        "Establecimiento de salud", "Otra institución",
    ],
    "Ayuda_Informal": [
        "Madre", "Padre", "Hermana", "Hermano", "Suegros",
        "Actual/último esposo o compañero", "Amiga(o) / Vecina(o)",
        "Otro pariente de la mujer", "Otro pariente del esposo", "Otra persona",
    ],
    "Justificacion": [
        "Si sale sin decirle", "Si descuida a los niños", "Si ella discute con él",
        "Si se niega a tener relaciones sexuales", "Si ella quema la comida",
    ],
    "Alcohol": ["Nunca", "Algunas veces", "Mucha frecuencia"],
}

FORMAS_FRONTEND = ["violencia_total", "violencia_psicologica", "violencia_fisica",
                   "violencia_sexual", "violencia_fis_psic", "violencia_sex_psic",
                   "violencia_fis_sex", "violencia_triple"]

# Hojas de corte con su columna de categoría, tal como las pide app.js
CORTES_FRONTEND = {
    "Departamento": "V024", "Edad": "V013", "Lugar de Residencia": "V025",
    "Logro Académico": "V149", "Indice de Riqueza": "V190", "Estado Civil": "V501",
    "Autoidentificación étnica": "S119D", "Violencia por Madre": "D115B",
    "Violencia por Padre": "D115C", "Violencia Interparental": "D121",
    "Situación de pareja": "pareja_actual", "Condición laboral": "trabajo_12m",
    "Grupo étnico": "etnia",
}


@pytest.fixture(scope="module")
def datos():
    if not ARCHIVO_INDICADORES.exists():
        pytest.skip("Ejecuta scripts/generar_sitio.py para generar site/data/.")
    return json.loads(ARCHIVO_INDICADORES.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def dir_servicios():
    if not ARCHIVO_DIRECTORIO.exists():
        pytest.skip("Ejecuta scripts/generar_sitio.py para generar site/data/.")
    return json.loads(ARCHIVO_DIRECTORIO.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def geometria():
    if not ARCHIVO_GEOMETRIA.exists():
        pytest.skip("Ejecuta scripts/generar_sitio.py para generar site/data/.")
    return json.loads(ARCHIVO_GEOMETRIA.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# indicadores.json
# --------------------------------------------------------------------------
def test_bloques_principales(datos):
    assert set(datos) == {"alguna_vez", "doce_meses", "factores", "meta"}
    assert datos["meta"]["anios"] == list(config.ANIOS)


@pytest.mark.parametrize("bloque", ["alguna_vez", "doce_meses"])
def test_hojas_de_prevalencia(datos, bloque):
    hojas = datos[bloque]
    assert "General_Anual" in hojas
    for hoja, clave in CORTES_FRONTEND.items():
        assert hoja in hojas, f"falta la hoja {hoja!r} en {bloque}"
        assert hojas[hoja], f"la hoja {hoja!r} de {bloque} está vacía"
        assert clave in hojas[hoja][0], f"{hoja}: falta la columna de categoría {clave!r}"


@pytest.mark.parametrize("bloque", ["alguna_vez", "doce_meses"])
def test_formas_de_violencia_presentes(datos, bloque):
    fila = datos[bloque]["General_Anual"][0]
    faltan = [f for f in FORMAS_FRONTEND if f not in fila]
    assert not faltan, f"{bloque}/General_Anual: faltan {faltan}"


@pytest.mark.parametrize("hoja,columnas", COLUMNAS_FRONTEND.items())
def test_columnas_de_factores(datos, hoja, columnas):
    assert hoja in datos["factores"], f"falta la hoja de factores {hoja!r}"
    fila = datos["factores"][hoja][0]
    faltan = [c for c in columnas if c not in fila]
    assert not faltan, f"{hoja}: faltan columnas {faltan}"


def test_valores_numericos_y_en_rango(datos):
    for bloque in ("alguna_vez", "doce_meses", "factores"):
        for hoja, filas in datos[bloque].items():
            for fila in filas:
                for clave, valor in fila.items():
                    if clave in ("Año", "n") or isinstance(valor, str):
                        continue
                    assert valor is None or 0 <= valor <= 100, \
                        f"{bloque}/{hoja}/{clave} = {valor} fuera de [0, 100]"


def test_totales_coinciden_con_los_valores_validados(datos):
    """El sitio publica exactamente las cifras validadas contra el INEI.

    Los valores esperados salen de ``validacion/valores_referencia_inei.csv``, no de
    una lista escrita a mano: al incorporar un año nuevo la prueba lo exige sola.
    """
    referencia = validacion.cargar_referencia()
    esperados = {
        int(f.anio): round(float(f.valor_inei), 2)
        for f in referencia.itertuples()
        if f.variable == "violencia_total_alguna_vez"
    }
    publicados = {r["Año"]: r["violencia_total"] for r in datos["alguna_vez"]["General_Anual"]}

    assert set(publicados) == set(esperados), (
        f"años publicados {sorted(publicados)} vs validados {sorted(esperados)}")
    for anio, valor in esperados.items():
        assert abs(publicados[anio] - valor) < 0.01, f"{anio}: {publicados[anio]} ≠ {valor}"


def test_el_sitio_publica_todos_los_anios_del_pipeline(datos):
    assert datos["meta"]["anios"] == list(config.ANIOS)


def test_estado_civil_distingue_casada_y_conviviente(datos):
    """Casada y Conviviente son categorías distintas y deben publicarse por separado."""
    filas = [r for r in datos["alguna_vez"]["Estado Civil"] if r["Año"] == 2024]
    categorias = {r["V501"] for r in filas}
    assert {"Casada", "Conviviente"} <= categorias


def test_sin_categorias_nulas(datos):
    """Ninguna tabulación debe publicar una categoría vacía como si fuera un grupo."""
    for bloque in ("alguna_vez", "doce_meses"):
        for hoja, clave in CORTES_FRONTEND.items():
            valores = {str(r[clave]).strip().lower() for r in datos[bloque][hoja]}
            assert not (valores & {"nan", "none", "", "<na>"}), f"{bloque}/{hoja}"


def test_departamentos_sin_espacios(datos):
    """V024 llega del INEI con espacio inicial en 16 departamentos: debe normalizarse."""
    deps = {r["V024"] for r in datos["alguna_vez"]["Departamento"]}
    assert all(d == d.strip() for d in deps)
    assert len(deps) == 25


# --------------------------------------------------------------------------
# directorio.json
# --------------------------------------------------------------------------
def test_estructura_del_directorio(dir_servicios):
    assert set(dir_servicios) == {"meta", "tipos", "servicios"}
    assert dir_servicios["meta"]["total"] == len(dir_servicios["servicios"])
    assert set(dir_servicios["tipos"]) == {"CEM", "SAR", "SAU", "HRT", "CAI"}


def test_campos_de_cada_servicio(dir_servicios):
    esperados = {"tipo", "departamento", "provincia", "distrito", "nombre",
                 "direccion", "telefono", "lat", "lon"}
    for s in dir_servicios["servicios"]:
        assert set(s) >= esperados
        assert s["tipo"] in dir_servicios["tipos"]
        assert s["nombre"]


def test_coordenadas_dentro_del_peru(dir_servicios):
    """Una sede sin coordenada válida se publica sin enlace al mapa, no con basura."""
    georreferenciados = 0
    for s in dir_servicios["servicios"]:
        if s["lat"] is None or s["lon"] is None:
            continue
        georreferenciados += 1
        assert -18.5 <= s["lat"] <= 0.5, f"{s['nombre']}: lat {s['lat']}"
        assert -81.5 <= s["lon"] <= -68.5, f"{s['nombre']}: lon {s['lon']}"
    assert georreferenciados > 0.8 * len(dir_servicios["servicios"])


def test_departamentos_del_directorio_cruzan_con_la_endes(datos, dir_servicios):
    """El MIMP separa Lima en dos ámbitos; la ENDES no. Deben quedar alineados."""
    endes = {r["V024"] for r in datos["alguna_vez"]["Departamento"]}
    directorio = {s["departamento"] for s in dir_servicios["servicios"]}
    huerfanos = directorio - endes
    assert not huerfanos, f"departamentos sin equivalente en la ENDES: {sorted(huerfanos)}"


def test_el_directorio_no_publica_datos_de_contacto_personal(dir_servicios):
    """El buscador orienta hacia el servicio, no hacia una persona.

    El consolidado del MIMP trae el nombre y el correo de cada coordinador o
    coordinadora; el sitio publica solo la sede, su dirección y su teléfono.
    """
    prohibidos = {"coordinador", "coodinador", "correo", "email", "responsable"}
    for s in dir_servicios["servicios"]:
        assert not (set(s) & prohibidos)
        assert not any("@" in str(v) for v in s.values() if isinstance(v, str))


# --------------------------------------------------------------------------
# departamentos.geojson — geometría de Perú-maps
# --------------------------------------------------------------------------
def test_geometria_tiene_los_25_departamentos(geometria):
    assert geometria["type"] == "FeatureCollection"
    assert len(geometria["features"]) == 25
    assert "Peru-maps" in geometria["meta"]["url"]


def test_cada_poligono_declara_su_departamento(geometria):
    """Dos claves y no más: el nombre cruza con la ENDES y el ubigeo con Perú-maps.

    El nombre alimenta la coropleta de indicadores; el ubigeo alimenta el buscador de
    servicios, que baja a provincia y distrito.
    """
    for f in geometria["features"]:
        assert set(f["properties"]) == {"dep", "u"}
        assert f["geometry"]["type"] in ("Polygon", "MultiPolygon")


def test_los_nombres_del_mapa_son_los_de_la_endes(datos, geometria):
    """El cruce mapa ↔ indicadores es por nombre; si difieren, el mapa sale en blanco."""
    en_mapa = {f["properties"]["dep"] for f in geometria["features"]}
    en_endes = {r["V024"] for r in datos["alguna_vez"]["Departamento"]}
    assert en_mapa == en_endes, f"difieren: {en_mapa ^ en_endes}"


def test_geometria_es_liviana_para_web(geometria):
    """Un mapa de tablero no necesita resolución cartográfica completa."""
    def vertices(coords):
        return 1 if isinstance(coords[0], (int, float)) else sum(vertices(c) for c in coords)

    total = sum(vertices(f["geometry"]["coordinates"]) for f in geometria["features"])
    assert total < 12000, f"{total} vértices: simplifica más antes de publicar"
    assert ARCHIVO_GEOMETRIA.stat().st_size < 400_000


def test_coordenadas_dentro_del_peru_en_la_geometria(geometria):
    def revisar(coords):
        if isinstance(coords[0], (int, float)):
            lon, lat = coords[0], coords[1]
            assert -81.5 <= lon <= -68.5 and -18.5 <= lat <= 0.5, (lon, lat)
        else:
            for c in coords:
                revisar(c)

    for f in geometria["features"]:
        revisar(f["geometry"]["coordinates"])


def test_el_sitio_atribuye_la_fuente_de_la_geometria():
    html = (DIR_SITIO / "index.html").read_text(encoding="utf-8")
    assert html.count("github.com/Rodasluis/Peru-maps") >= 2
    assert "no oficiales" in html


# --------------------------------------------------------------------------
# Coherencia entre el sitio y el paquete
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# Geometría: los tres niveles administrativos
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def ubigeos():
    ruta = DIR_SITIO / "data" / "ubigeos.json"
    if not ruta.exists():
        pytest.skip("Ejecuta scripts/generar_sitio.py para generar site/data/.")
    return json.loads(ruta.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def departamentos():
    ruta = DIR_SITIO / "data" / "departamentos.geojson"
    if not ruta.exists():
        pytest.skip("Ejecuta scripts/generar_sitio.py para generar site/data/.")
    return json.loads(ruta.read_text(encoding="utf-8"))


def test_jerarquia_completa(ubigeos):
    """Los 25 departamentos, 196 provincias y 1892 distritos del registro del INEI."""
    assert len(ubigeos) == 25
    provincias = sum(len(d["p"]) for d in ubigeos.values())
    distritos = sum(len(p["d"]) for d in ubigeos.values() for p in d["p"].values())
    assert provincias == 196
    assert distritos == 1892


def test_los_ubigeos_son_consistentes(ubigeos):
    """El ubigeo de cada nivel prefija al del siguiente: 05 → 0501 → 050101."""
    for u_dep, departamento in ubigeos.items():
        assert len(u_dep) == 2
        for u_prov, provincia in departamento["p"].items():
            assert len(u_prov) == 4 and u_prov.startswith(u_dep)
            for u_dist in provincia["d"]:
                assert len(u_dist) == 6 and u_dist.startswith(u_prov)


def test_hay_un_paquete_de_geometria_por_departamento(ubigeos):
    dir_geo = DIR_SITIO / "data" / "geo"
    archivos = {p.stem for p in dir_geo.glob("*.json")}
    assert archivos == set(ubigeos), "falta o sobra algún paquete departamental"


def test_cada_paquete_cubre_su_departamento(ubigeos):
    """Provincias y distritos del paquete coinciden con los de la jerarquía."""
    for u_dep, departamento in ubigeos.items():
        paquete = json.loads((DIR_SITIO / "data" / "geo" / f"{u_dep}.json")
                             .read_text(encoding="utf-8"))
        provincias = {f["properties"]["u"] for f in paquete["provincias"]}
        distritos = {f["properties"]["u"] for f in paquete["distritos"]}
        esperadas = set(departamento["p"])
        esperados = {u for p in departamento["p"].values() for u in p["d"]}
        assert provincias == esperadas, f"provincias de {u_dep}"
        assert distritos == esperados, f"distritos de {u_dep}"
        # Cada distrito declara a qué provincia pertenece: el mapa filtra por eso.
        for f in paquete["distritos"]:
            assert f["properties"]["p"] in esperadas


def test_los_paquetes_pesan_lo_razonable():
    """Se descargan bajo demanda, pero uno solo no debe volverse una descarga pesada."""
    pesos = {p.stem: p.stat().st_size for p in (DIR_SITIO / "data" / "geo").glob("*.json")}
    mayor = max(pesos.items(), key=lambda kv: kv[1])
    assert mayor[1] < 400_000, f"el paquete {mayor[0]} pesa {mayor[1]/1024:.0f} KB"
    assert sum(pesos.values()) < 4_000_000


def test_los_servicios_cruzan_con_la_jerarquia(dir_servicios, ubigeos):
    """Sin este cruce el buscador y el mapa hablarían de unidades distintas."""
    distritos = {u for d in ubigeos.values() for p in d["p"].values() for u in p["d"]}
    sin_ubigeo = [s["nombre"] for s in dir_servicios["servicios"] if not s["ubigeo"]]
    assert not sin_ubigeo, f"servicios sin ubigeo: {sin_ubigeo[:5]}"

    huerfanos = [s["nombre"] for s in dir_servicios["servicios"]
                 if s["ubigeo"] not in distritos]
    assert not huerfanos, f"servicios cuyo distrito no existe: {huerfanos[:5]}"

    for s in dir_servicios["servicios"]:
        assert s["ubigeo"].startswith(s["ubigeo_prov"])
        assert s["ubigeo_prov"].startswith(s["ubigeo_dep"])


def test_los_nombres_del_directorio_son_los_oficiales(dir_servicios, ubigeos):
    """El MIMP escribe 'Lima Metropolitana'; el registro oficial, 'Lima'."""
    for s in dir_servicios["servicios"]:
        departamento = ubigeos[s["ubigeo_dep"]]
        provincia = departamento["p"][s["ubigeo_prov"]]
        assert s["departamento"] == departamento["n"]
        assert s["provincia"] == provincia["n"]
        assert s["distrito"] == provincia["d"][s["ubigeo"]]


def test_la_capa_departamental_trae_ubigeo_y_nombre_endes(departamentos, ubigeos):
    assert len(departamentos["features"]) == 25
    for f in departamentos["features"]:
        propiedades = f["properties"]
        assert set(propiedades) == {"dep", "u"}
        assert propiedades["u"] in ubigeos
        assert propiedades["dep"] == ubigeos[propiedades["u"]]["n"]


def test_el_sitio_no_carga_recursos_de_terceros():
    """Ningún recurso puede venir de otro dominio.

    No es una cuestión de rendimiento: cada recurso externo envía la IP de quien
    visita el tablero a un tercero, y aquí puede ser una mujer buscando ayuda.
    Los enlaces ``<a href>`` a gob.pe o GitHub sí son legítimos: los abre quien
    decide hacer clic, no se cargan solos.
    """
    patrones_de_carga = [
        re.compile(r"@import\s+url\(\s*['\"]?https?://", re.I),      # CSS
        re.compile(r"url\(\s*['\"]?https?://", re.I),                 # CSS: fuentes, imágenes
        re.compile(r"<script[^>]+src=[\"']https?://", re.I),          # HTML
        re.compile(r"<link[^>]+href=[\"']https?://", re.I),           # HTML
        re.compile(r"<img[^>]+src=[\"']https?://", re.I),             # HTML
        re.compile(r"fetch\(\s*['\"`]https?://", re.I),               # JS
    ]

    for archivo in ("index.html", "assets/styles.css", "assets/app.js"):
        texto = (DIR_SITIO / archivo).read_text(encoding="utf-8")
        for patron in patrones_de_carga:
            hallazgo = patron.search(texto)
            assert not hallazgo, (
                f"{archivo} carga un recurso externo: {hallazgo.group(0)!r}. "
                "Aloja el archivo en site/assets/."
            )


def test_la_tipografia_esta_alojada_localmente():
    fuentes = sorted((DIR_SITIO / "assets" / "fonts").glob("*.woff2"))
    assert fuentes, "no hay fuentes locales en site/assets/fonts/"
    css = (DIR_SITIO / "assets" / "styles.css").read_text(encoding="utf-8")
    for fuente in fuentes:
        assert f"fonts/{fuente.name}" in css, f"{fuente.name} no se referencia en el CSS"
    peso = sum(f.stat().st_size for f in fuentes)
    assert peso < 300_000, f"{peso/1024:.0f} KB de fuentes: usa la versión variable"


def test_html_declara_cinco_paneles():
    html = (DIR_SITIO / "index.html").read_text(encoding="utf-8")
    assert len(re.findall(r'<div class="panel[ "][^>]*id="panel-', html)) == 5


def test_las_hojas_declaradas_existen_en_el_modulo():
    """`sitio.py` y las pruebas deben declarar las mismas hojas de corte."""
    declaradas = set(sitio.HOJAS_PREVALENCIA) - {"General_Anual"}
    assert set(CORTES_FRONTEND) <= declaradas
