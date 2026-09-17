# Dashboard — Violencia de pareja contra la mujer en el Perú

Sitio estático publicado con GitHub Pages. No tiene backend: son HTML, CSS, JavaScript
y los archivos de datos que genera el pipeline del repositorio.

**Nada se ejecuta al cargarlo.** El Python corre una sola vez, fuera de línea, y escribe
los JSON; el navegador solo los descarga. Una sesión completa —los cinco paneles, cambios
de año, el buscador— son **10 peticiones, todas a archivos de este mismo directorio y
ninguna a un tercero**. Tampoco hay sondeo periódico.

Que no haya recursos externos no es cuestión de rendimiento: cada uno enviaría la IP de
quien visita el tablero a otro dominio, y aquí puede ser una mujer buscando ayuda. Por eso
Chart.js y la tipografía están alojados en `assets/`, y hay una prueba
(`test_el_sitio_no_carga_recursos_de_terceros`) que falla si vuelve a colarse alguno.

```
site/
├── index.html                  cinco paneles
├── assets/
│   ├── styles.css
│   ├── app.js                  render con Chart.js; sin dependencias de red
│   ├── fonts/                  Inter variable (SIL OFL), 2 subconjuntos
│   └── vendor/                 Chart.js 4.4.0 + plugin datalabels (copia local)
└── data/
    ├── indicadores.json        prevalencias por año y característica
    ├── directorio.json         servicios de atención del MIMP
    ├── ubigeos.json            jerarquía dep → prov → dist (nombres, sin geometría)
    ├── departamentos.geojson   los 25 departamentos
    ├── geo/<ubigeo>.json       provincias y distritos de un departamento
    └── manifiesto.json         qué se publicó y cuándo
```

## Diseño

Una regla gobierna el resto: **el color pertenece a los datos**. Los cuatro tonos de
tipo de violencia y la rampa secuencial de la coropleta son los únicos colores
saturados; todo lo demás —cabecera, pestañas, tarjetas, botones, modal— vive en una
escala neutra. Cuando el cromo lleva color compite con la lectura del gráfico.

De ahí salen las reglas concretas:

| Regla | Motivo |
|---|---|
| Sin degradados | Decoración que no codifica nada |
| Un solo lienzo para los cinco paneles | El mismo gráfico debe leerse igual en cualquier pestaña |
| Navegación con subrayado, no con color | La navegación no es un dato |
| Tarjetas con borde de 1px | La sombra se reserva a lo que flota: modal y desplegables |
| Una serie, un color | Colorear por ranking repite lo que la longitud ya dice |
| Un único botón sólido, en tinta neutra | La acción se distingue por tener relleno, no por su tono |
| El hover cambia el borde, no la posición | Movimiento sin información |

Dos excepciones deliberadas: las píldoras de tipo de violencia llevan el color de su
serie —es la identidad que se verá en el gráfico— y el botón de la **Línea 100** va en
verde, porque es la acción más urgente del sitio.

La frecuencia de embriaguez es la única variable **ordinal** del tablero: se muestra en
su orden natural y el color recorre la rampa en ese mismo orden, no según el valor.

Escala de espaciado de 4 px (`--e1` … `--e7`), tipografía con cifras tabulares para que
las columnas de números no bailen, y `prefers-reduced-motion` respetado.

## Mapas

Se dibujan en **SVG puro**, sin librería de mapas ni servidor de teselas: el sitio no
hace ninguna petición a terceros. Con 25 polígonos y hasta 517 puntos, cada marca puede
ser un nodo del DOM con su `<title>`, y el tooltip y el foco de teclado salen gratis.

* **Coropleta de prevalencia** (panel 1) — magnitud en una escala secuencial de un solo
  tono, claro → oscuro, con cinco clases de igual amplitud y leyenda de rangos.
* **Mapa de sedes** (panel 5) — el tipo de servicio se codifica por **forma**, no por
  color. Cinco colores no superan la prueba de separación para daltonismo cuando
  cualquier par puede quedar contiguo, que es exactamente el caso de un mapa de puntos;
  la forma sí es un canal seguro.

### Los tres niveles administrativos

La geometría viene de [Perú-maps](https://github.com/Rodasluis/Peru-maps) y se reparte
para que el navegador descargue solo lo que mira:

| archivo | cuándo se pide | peso |
|---|---|---|
| `departamentos.geojson` | siempre | 57 KB |
| `ubigeos.json` | al abrir el buscador | 50 KB |
| `geo/<ubigeo>.json` | al elegir un departamento | 4-284 KB |

Los 1 892 distritos del país juntos pesan varios megabytes; repartidos por departamento,
una sesión típica descarga uno solo.

Los tres desplegables son dependientes y llevan el **conteo de sedes** entre paréntesis.
Un distrito con `(0)` es información útil, no un error: en ese caso el listado ofrece los
servicios más cercanos, calculados desde el centro de la unidad elegida. El mapa encuadra
el nivel seleccionado — sin selección, el país; con departamento, sus provincias; con
provincia, sus distritos.

### Botón «Usar mi ubicación»

Resuelve el distrito por punto-en-polígono en dos pasos: primero el departamento sobre la
capa que ya está en memoria, después el distrito dentro del paquete de ese departamento.
Así no hay que descargar los 1 892 polígonos solo para situar un punto.

**Las coordenadas no salen del navegador**: no hay servidor al que enviarlas. Si el
permiso se deniega, la ubicación falla o cae fuera del Perú, el buscador lo dice y sigue
funcionando con los desplegables.

El cruce entre el directorio del MIMP y la geometría es por **ubigeo** (548/548 sedes),
no por nombre: el MIMP escribe "Lima Metropolitana" donde el registro oficial dice "Lima".

## Ver el sitio en local

Los datos se cargan con `fetch()`, así que **no funciona abriendo `index.html` con doble
clic** (el navegador bloquea las peticiones desde `file://`). Sírvelo por HTTP:

```bash
cd site
python -m http.server 8000
# http://localhost:8000
```

## Regenerar los datos

```bash
python scripts/generar_sitio.py
```

Lee la base consolidada de `data/interim/` y el consolidado del MIMP, y reescribe
`site/data/*.json`. Requiere haber ejecutado antes `scripts/construir_base.py`.

Las cifras que publica el sitio son las mismas que valida `pytest tests` contra los
cuadros del INEI: la prevalencia total alguna vez de 2025 que aparece en el panel 1
(49,09 %) es la del cuadro 12.1.

## Paneles

| # | Panel | Contenido |
|---|---|---|
| 1 | El problema existe y es grande | Prevalencia nacional y departamental, polivictimización |
| 2 | No afecta igual a todas | Edad, residencia, educación, riqueza, situación de pareja, condición laboral, grupo étnico, antecedentes en la infancia |
| 3 | Hay dinámicas que lo sostienen | Situaciones de control, alcohol, decisiones del hogar, justificación |
| 4 | La respuesta no llega donde más se necesita | Búsqueda de ayuda, instituciones, barreras |
| 5 | ¿Dónde buscar ayuda? | Canales nacionales y buscador de servicios del MIMP |

## Contrato de datos

`site/assets/app.js` lee los JSON **por nombre de hoja y de columna**. Ese contrato está
fijado en [`tests/test_sitio.py`](../tests/test_sitio.py): renombrar un indicador en
`src/endes_violencia/sitio.py` rompe una prueba en vez de dejar una barra en cero.

Si agregas un indicador al dashboard, tócalo en los tres sitios: `sitio.py` (lo emite),
`test_sitio.py` (lo exige) y `app.js` (lo dibuja).

## Fuentes

* **Indicadores** — INEI, Encuesta Demográfica y de Salud Familiar (ENDES) 2021-2025.
* **Servicios de atención** — MIMP, [Consolidado Directorio Nacional](https://www.mimp.gob.pe/omep/Consolidado_Directorio_Nacional_2026.xlsx).
  Se publican solo los servicios de atención frente a la violencia (CEM, SAR, SAU, HRT, CAI),
  con sede, dirección y teléfono institucional.
* **Geometría administrativa** — [Perú-maps](https://github.com/Rodasluis/Peru-maps),
  en sus tres niveles. Cada capa se simplifica a la escala con que se mira: los
  departamentos pasan de 71 124 a 2 849 vértices, indistinguible en un tablero.
  **Los límites no son oficiales y son solo para uso estadístico.**
