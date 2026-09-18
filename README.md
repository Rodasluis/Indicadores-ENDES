# Indicadores de violencia de pareja — ENDES (Perú)

### 📊 [Ver el dashboard →](https://rodasluis.github.io/Indicadores-ENDES/)

Cálculo reproducible de los indicadores de **violencia familiar contra la mujer de 15 a 49 años
ejercida por el esposo o compañero**, a partir de los microdatos de la Encuesta Demográfica y de
Salud Familiar (ENDES) del INEI.

El repositorio descarga los microdatos del portal del INEI, construye los indicadores, estima su
precisión muestral y **contrasta cada resultado contra la cifra publicada en el informe oficial**.

> **55 de 55 valores de referencia coinciden con la cifra oficial del INEI** —estimación puntual
> y desviación estándar, cuadros 12.1, 12.1.1, 12.2, 12.4.1, 12.4.2 y 12.10, años 2021-2025.
> Detalle en [`docs/validacion.md`](docs/validacion.md).

Los mismos resultados alimentan un **dashboard público**, descrito en
[El dashboard](#el-dashboard).

## Resultados

Porcentaje de mujeres de 15 a 49 años alguna vez unidas que declara haber sufrido violencia de
su esposo o compañero:

| Forma de violencia | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|--:|--:|--:|--:|--:|
| **Alguna vez** | | | | | |
| Total | 54,86 | 55,66 | 53,76 | 51,96 | **49,09** |
| Psicológica y/o verbal | 50,83 | 51,89 | 49,34 | 48,42 | **45,60** |
| Física | 26,69 | 27,76 | 27,19 | 25,46 | **23,24** |
| Sexual | 5,86 | 6,70 | 6,46 | 5,60 | **5,64** |
| **En los últimos 12 meses** | | | | | |
| Total | 33,61 | 35,63 | 34,46 | 33,89 | **30,99** |
| Psicológica y/o verbal | 32,49 | 34,81 | 33,51 | 33,13 | **30,33** |
| Física | 6,95 | 8,12 | 7,64 | 7,00 | **6,53** |
| Sexual | 1,75 | 2,17 | 1,87 | 1,71 | **1,56** |

La violencia total alguna vez lleva tres años consecutivos de descenso desde su máximo de 2022:
**6,6 puntos porcentuales menos** (5,8 menos que en 2021). En 2025 bajan el total y las formas
psicológica y física; la sexual se mantiene (5,60 % → 5,64 %).

Cada estimación se acompaña de su desviación estándar, intervalo de confianza al 95 % y
coeficiente de variación, calculados según el diseño muestral complejo de la encuesta.

## Instalación

Requiere Python 3.10 o superior.

```bash
git clone <url-del-repositorio>
cd "Indicadores ENDES"

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
pip install -e .                 # instala el paquete endes_violencia en modo editable
```

El proyecto usa *src layout*: el código vive en `src/endes_violencia/` y no es importable hasta
instalarlo. `pip install -e .` lo deja disponible desde cualquier directorio y refleja los
cambios que hagas en `src/` sin reinstalar.

El notebook, los scripts de `scripts/` y `pytest` funcionan **sin** ese paso: agregan `src/` al
`sys.path` por su cuenta. Solo hace falta instalar para importar `endes_violencia` desde tu
propio código (Opción 3).

## Uso

### Opción 1 — el notebook

```bash
jupyter lab notebooks/01_indicadores_violencia_pareja.ipynb
```

[`notebooks/01_indicadores_violencia_pareja.ipynb`](notebooks/01_indicadores_violencia_pareja.ipynb)
recorre todo el flujo con explicaciones: descarga, construcción de indicadores, validación contra
el INEI, series nacionales, desagregaciones, factores asociados y búsqueda de ayuda.

### Opción 2 — los scripts

```bash
python scripts/construir_base.py        # descarga (~130 MB/año) y consolida en parquet
python scripts/generar_reportes.py      # calcula, valida y exporta a outputs/
python scripts/generar_sitio.py         # genera los datos del dashboard en site/data/
pytest tests -q                         # comprueba la validación contra el INEI
```

### Opción 3 — como paquete

Requiere `pip install -e .` (ver Instalación).

```python
from endes_violencia import carga, indicadores, tabulacion, reportes

df = indicadores.construir_todo(carga.cargar_base())

tabla = tabulacion.tabular(df, reportes.INDICADORES_ALGUNA_VEZ)
print(tabulacion.a_formato_ancho(tabla))

# desagregado por área de residencia
tabulacion.tabular(df, reportes.INDICADORES_ALGUNA_VEZ, por="V025")
```

### Agregar un año

Los identificadores de encuesta del portal del INEI están en
[`src/endes_violencia/config.py`](src/endes_violencia/config.py):

```python
ENCUESTAS = {2021: "760", 2022: "786", 2023: "910", 2024: "968", 2025: "1038"}
```

Añade la entrada del año nuevo y vuelve a ejecutar. Conviene revisar antes que las etiquetas de
valor no hayan cambiado: ya ocurrió una vez (las decisiones del hogar entre 2021 y 2022) y es la
causa más probable de un salto artificial en una serie.

## Salidas

`outputs/` (no versionado):

| Archivo | Contenido |
|---|---|
| `tablas/indicadores_violencia_endes.xlsx` | 25 hojas: series nacionales, componentes, desagregaciones y la hoja de validación |
| `tablas/validacion_inei.csv` | Comparación indicador por indicador contra la cifra oficial |
| `csv/*.csv` | Las mismas tablas en formato largo, para BI o para volver a leer |
| `csv/microdatos_violencia.csv` | Microdatos del universo con los indicadores construidos y las variables de diseño, para modelar |

## El dashboard

**https://rodasluis.github.io/Indicadores-ENDES/**

Cinco paneles que llevan al lector de la magnitud del problema a dónde pedir ayuda:

| # | Panel | Qué muestra |
|---|---|---|
| 1 | El problema existe y es grande | Prevalencia nacional y por departamento de la violencia total, psicológica y/o verbal, física y sexual, en mapa y en serie 2021-2025, más la polivictimización |
| 2 | No afecta igual a todas | La prevalencia desagregada por edad, área de residencia, educación, nivel de riqueza, situación de pareja, condición laboral, grupo étnico y antecedentes de violencia en la infancia |
| 3 | Hay dinámicas que lo sostienen | Situaciones de control, consumo de alcohol de la pareja, participación de la mujer en las decisiones del hogar y justificación de la violencia física |
| 4 | La respuesta no llega donde más se necesita | Búsqueda de ayuda en personas cercanas y en instituciones, a qué institución se acudió y las razones para no buscarla |
| 5 | ¿Dónde buscar ayuda? | Los canales nacionales de atención y un buscador de las 548 sedes del MIMP (CEM, SAR, SAU, HRT y CAI) por departamento, provincia y distrito |

Las cifras del tablero son las mismas que `pytest tests` contrasta contra los cuadros del INEI:
la prevalencia total alguna vez de 2025 que encabeza el panel 1 (49,09 %) es la del cuadro 12.1.

Cómo está construido —contrato de datos, decisiones de diseño, mapas en SVG y privacidad del
buscador— está en [`site/README.md`](site/README.md).

## Estructura

```
├── notebooks/01_indicadores_violencia_pareja.ipynb   análisis narrado
├── site/                        dashboard publicado con GitHub Pages
│   ├── index.html · assets/     frontend estático
│   └── data/*.json              generados por scripts/generar_sitio.py
├── src/endes_violencia/
│   ├── config.py         años, identificadores de encuesta, rutas, variables de diseño
│   ├── descarga.py       descarga y descompresión desde el portal del INEI
│   ├── carga.py          lectura de .dta, unión por CASEID, consolidación en parquet
│   ├── etiquetas.py      comparación segura de etiquetas de valor de Stata
│   ├── categorias.py     etiquetas de corte homogéneas entre años y grupos derivados
│   ├── indicadores.py    definición de cada indicador, anotada con su cuadro del INEI
│   ├── tabulacion.py     estimación ponderada + error estándar de muestreo complejo
│   ├── reportes.py       composición de las tablas del reporte
│   ├── sitio.py          serialización al formato que consume el dashboard
│   ├── directorio.py     servicios de atención del MIMP, cruzados por ubigeo
│   ├── mapas.py          geometría de Perú-maps en sus tres niveles
│   └── validacion.py     contraste contra los valores publicados
├── scripts/
│   ├── construir_base.py        descarga y consolida
│   ├── generar_reportes.py      calcula, valida y exporta
│   ├── generar_sitio.py         genera los datos del dashboard
│   └── extraer_valores_inei.py  regenera la tabla de referencia desde los cuadros del INEI
├── tests/                       validación contra el INEI y contrato de datos del sitio
├── validacion/valores_referencia_inei.csv   valores oficiales (versionado)
├── docs/
│   ├── metodologia.md           universo, definiciones, estimador de varianza
│   └── validacion.md            resultados de la validación
├── referencias/                 documentación del INEI (no versionada)
├── data/                        microdatos descargados (no versionados)
└── outputs/                     tablas generadas (no versionadas)
```

## Diseño

**Las etiquetas se comparan completas, nunca por subcadena.** Los indicadores se definen sobre
etiquetas de texto (`"Si"`, `"Nunca"`, `"Entrevistada y esposo/compañero"`), y esas etiquetas
cambian entre años. `etiquetas.es()` compara valores exactos contra una lista explícita, de modo
que un cambio de etiqueta produce un cero visible en lugar de una coincidencia parcial silenciosa.
La función además copia la columna antes de comparar: sobre dtype `string`,
`Serie.astype(str)` puede convertir los `NA` en la cadena `"<NA>"` mutando el original, tras lo
cual `notna()` devuelve `True` para todo y los denominadores calculados después quedan mal sin
lanzar ningún error.

**El universo va en los datos, no en el filtro.** Cada indicador es `1`, `0` o `NaN`, siendo
`NaN` "fuera de universo". El denominador queda determinado por la propia variable, así que no
hay que arrastrar máscaras de filtrado a través del código ni recordar cuál aplica a cuál.

**Ventanas temporales en columnas separadas.** Los indicadores llevan sufijo `_alguna_vez` o
`_12m` y coexisten en un mismo `DataFrame`; ninguna etapa sobrescribe el resultado de otra, así
que el orden de ejecución no cambia el resultado.

**La validación es una prueba, no un informe.** `pytest tests` falla si algún indicador se
separa de la cifra oficial. Los valores de referencia están versionados en
`validacion/valores_referencia_inei.csv` y se regeneran desde los libros del INEI con
`scripts/extraer_valores_inei.py`.

## Fuentes y licencia

Datos y cuadros de referencia: **Instituto Nacional de Estadística e Informática (INEI)**,
*Encuesta Demográfica y de Salud Familiar (ENDES)*, 2021-2025.
[Portal de microdatos](https://proyectos.inei.gob.pe/microdatos/) ·
[Publicaciones ENDES](https://www.gob.pe/inei).

Servicios de atención: **Ministerio de la Mujer y Poblaciones Vulnerables (MIMP)**,
*Consolidado Directorio Nacional*.

Geometría departamental: **[Perú-maps](https://github.com/Rodasluis/Peru-maps)** — límites
administrativos del Perú en GeoJSON. No son oficiales y son solo para uso estadístico.

El código de este repositorio se distribuye bajo licencia [MIT](LICENSE). Los microdatos, los
cuadros del informe, los diccionarios de variables y los manuales son propiedad del INEI y se
rigen por sus condiciones de uso; no se redistribuyen aquí (`referencias/` y `data/` no están
versionados).

### Cómo citar

> Rodas Palomino, L. (2026). *Indicadores de violencia de pareja — ENDES (Perú)* (v1.0.0)
> [software]. Zenodo. https://doi.org/10.5281/zenodo.22823100

Ese DOI es el de concepto: resuelve siempre a la última versión publicada. Si necesitas
referirte exactamente a la v1.0.0, usa https://doi.org/10.5281/zenodo.22823101
