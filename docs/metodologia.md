# Metodología

## Fuente

Microdatos de la **Encuesta Demográfica y de Salud Familiar (ENDES)** del Instituto Nacional de
Estadística e Informática (INEI) del Perú, disponibles en el
[portal de microdatos](https://proyectos.inei.gob.pe/microdatos/).

Cada año es una encuesta independiente con su propio identificador. Los archivos se descargan de:

```
https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/{id_encuesta}-Modulo{modulo}.zip
```

| Año | id_encuesta |
|---|---|
| 2021 | 760 |
| 2022 | 786 |
| 2023 | 910 |
| 2024 | 968 |
| 2025 | 1038 |

Los identificadores viven en `config.ENCUESTAS`; agregar un año es agregar una entrada.

## Módulos y archivos

Solo se descargan los módulos con variables de violencia:

| Módulo | Archivo | Contenido | Variables clave |
|---|---|---|---|
| 1631 | `REC0111` | Características de la mujer, ponderador, diseño muestral | `V005`, `V044`, `V001`, `V022`, `V013`, `V024`, `V025`, `V149`, `V190` |
| 1631 | `REC91` | Módulo Perú: etnicidad y ayuda institucional | `S119`, `S119D`, `S1023A*` |
| 1635 | `RE516171` | Nupcialidad, actividad y empoderamiento | `V501`, `V502`, `V731`, `V739`, `V743*`, `V744*` |
| 1637 | `REC84DV` | Módulo de violencia doméstica | `D101*`, `D103*`, `D105*`, `D113`, `D114`, `D119*`, `D120`, `D121`, `QI1003*N` |

La unión se hace por `CASEID` con `validate="one_to_one"` (una fila por mujer) y los años se
apilan agregando la columna `anio`.

El INEI publica los archivos con nombre variable entre años (`REC0111.dta` en unos,
`REC0111_2023.dta` en otros); `carga.buscar_dta()` resuelve ambos casos con un patrón anclado.

## Universo

Los cuadros 12.1 a 12.4 del informe se refieren a **mujeres de 15 a 49 años alguna vez unidas
que fueron seleccionadas y entrevistadas para el módulo de violencia**:

```python
V044 == "Mujer seleccionada y entrevistada"   and   V502 != "Nunca casada"
```

El módulo de violencia se aplica a una submuestra: de las ~38 000 mujeres entrevistadas cada
año, entre 19 000 y 22 000 forman el universo. Esta definición reproduce exactamente el número
de casos —ponderado y sin ponderar— que publica el INEI.

Los indicadores toman valor `NaN` fuera de su universo, de modo que el denominador queda
determinado por la propia variable y no hace falta arrastrar filtros.

## Ponderación

`peso = V005 / 1 000 000`. Todas las estimaciones son ponderadas.

## Categorías de respuesta del módulo de violencia

Las preguntas `D103*` y `D105*` no son dicotómicas. Sus cuatro etiquetas se leen así:

| Etiqueta | Significado | Alguna vez | Últimos 12 meses |
|---|---|:--:|:--:|
| `No` | Nunca ocurrió | — | — |
| `Nunca` | Ocurrió, pero **no** en los últimos 12 meses | ✔ | — |
| `Algunas veces` | Ocurrió algunas veces en los últimos 12 meses | ✔ | ✔ |
| `Frecuentemente` | Ocurrió frecuentemente en los últimos 12 meses | ✔ | ✔ |

Es contraintuitivo: `"Nunca"` **sí** cuenta como violencia en la ventana "alguna vez", porque es
el *"sí, pero no en el último año"*. El "no" verdadero es `"No"`.

Las situaciones de control se preguntan en dos formatos: `D101A`-`D101F` con respuesta
`Si`/`No`/`No sabe` (referida a alguna vez) y `QI1003AN`-`QI1003FN` con respuesta
`Nunca`/`Algunas veces`/`Mucha frecuencia` (referida a los últimos 12 meses).

## Definición de las formas de violencia

### Violencia física
`D105A` empujó, sacudió o le tiró algo · `D105B` abofeteó o retorció el brazo ·
`D105C` golpeó con el puño o algo que pudo dañarla · `D105D` pateó o arrastró ·
`D105E` trató de estrangularla o quemarla · `D105F` amenazó con cuchillo, pistola u otra arma ·
`D105G` atacó/agredió con cuchillo, pistola u otra arma.

(`D105J` figura en el recode DHS pero llega vacía en la ENDES peruana.)

### Violencia sexual
`D105H` la obligó a tener relaciones sexuales sin que ella quisiera ·
`D105I` la obligó a realizar actos sexuales que ella no aprueba.

### Violencia psicológica y/o verbal
Unión de tres bloques (cuadro 12.2):

* **Situaciones de control** — los seis ítems `D101A`-`D101F`. El cuadro 12.2 publica cinco de
  ellos, pero los seis entran en el agregado: excluir `D101D` ("trata de limitar las visitas o
  el contacto con su familia") deja la prevalencia unos 0,3 pp por debajo de la cifra oficial.
* **Situaciones humillantes** — `D103A`.
* **Amenazas** — `D103B` (hacerle daño a ella o a alguien cercano) y `D103D` (irse de casa,
  quitarle las hijas e hijos o la ayuda económica).

(`D103C`, `D103E` y `D103F` llegan vacías.)

### Violencia total
Unión de física, sexual y psicológica.

### Polivictimización
Cuatro categorías mutuamente excluyentes: física+psicológica sin sexual, sexual+psicológica sin
física, física+sexual sin psicológica, y las tres a la vez. No forman parte de los cuadros
publicados por el INEI.

## Búsqueda de ayuda

* **Universo** (cuadro 12.10): mujeres a las que se formuló la pregunta de búsqueda de ayuda tras
  haber sido maltratadas físicamente, es decir `D119Y` no vacío. Nótese que no equivale a
  "violencia física por la pareja": el módulo pregunta por el maltrato de cualquier agresor, de
  modo que el universo (~7 800 casos en 2024) es mayor que el de violencia física por la pareja
  (~4 900). Usar este último desplaza el indicador institucional unos 3 pp.
* **En personas cercanas**: `D119Y == "Buscó ayuda de alguien"`.
* **En alguna institución**: `S1023AZ == "No"`. La variable se rotula *"No, nunca ha buscado
  ayuda"*, así que responder `"No"` identifica a quienes **sí** acudieron a alguna institución.
* **Detalle por fuente** (cuadro 12.11) y **por institución** (cuadro 12.12): respuesta múltiple
  condicionada a haber buscado ayuda en ese canal; los porcentajes no suman 100.

## Empoderamiento y actitudes

* **Toma de decisiones** (cuadro 2.15): la mujer tiene la última palabra sola o junto con su
  esposo o compañero. Requiere aceptar las etiquetas de 2021 (`"Ambos"`,
  `"Entrevistada y compañero"`) y las de 2022 en adelante
  (`"Entrevistada y esposo/compañero"`), y **no** aceptar las decisiones tomadas con terceros
  (`"Entrevistada y otra persona"`). Universo: mujeres a las que se formuló la pregunta.
* **Justificación de la violencia física** (`V744A`-`V744E`): universo de todas las mujeres
  entrevistadas a las que se formuló la pregunta. La etiqueta afirmativa es `"Si"` en 2021 y
  `"Sí"` en 2022 en adelante.

## Estimación de la precisión

La ENDES es una muestra **bietápica, estratificada e independiente por departamento**. El INEI
publica para cada estimación la desviación estándar, el intervalo de confianza al 95 % y el
coeficiente de variación.

Se reproducen con un estimador de **linealización de Taylor** sobre la razón ponderada, con:

* **estrato** = `V022`
* **conglomerado** = `V001`

Para una proporción ponderada `r = Σwy / Σw`:

```
var(r) = (1 / (Σw)²) · Σ_h [ n_h/(n_h−1) · ( Σ_i d_hi² − (Σ_i d_hi)²/n_h ) ]

donde   d_hi = Σ_{j∈i} w_j y_j − r · Σ_{j∈i} w_j
```

`h` indexa estratos, `i` conglomerados dentro del estrato y `n_h` es el número de conglomerados
del estrato. Los estratos con un solo conglomerado no aportan varianza estimable y se omiten.

De ahí:

```
D.E.      = √var(r) · 100
IC 95 %   = estimación ± 1,95996 · D.E.
CV        = 100 · D.E. / estimación
```

Esta especificación reproduce la desviación estándar publicada con una diferencia máxima de
0,0001 pp (ver [`validacion.md`](validacion.md)). Usar `V023` o `V024` como estrato da valores
cercanos pero no idénticos.

### Interpretación del coeficiente de variación

Siguiendo la convención del INEI:

* CV ≤ 15 % — estimación confiable.
* 15 % < CV < 50 % — estimación referencial (el INEI la publica entre paréntesis).
* CV ≥ 50 % — no se publica.

## Limitaciones

* Los indicadores de violencia se basan en el autorreporte de la mujer entrevistada y están
  sujetos a subdeclaración.
* La ENDES 2020 se levantó con entrevista presencial interrumpida por la pandemia; el propio
  INEI marca ese año con una nota al pie. Este repositorio arranca en 2021.
* La comparabilidad entre años depende de que las etiquetas de valor no cambien. Ya se detectó
  un cambio (las decisiones del hogar entre 2021 y 2022); al incorporar un año nuevo conviene
  revisar las etiquetas antes de dar la serie por buena.
* Algunos cuadros del informe publican la serie solo para 2025. El repositorio los calcula, pero
  quedan fuera del contraste automático hasta que se amplíe el mapa de celdas de
  `scripts/extraer_valores_inei.py` (ver [`validacion.md`](validacion.md)).
