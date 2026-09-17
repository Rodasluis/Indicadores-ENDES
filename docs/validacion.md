# Validación contra los cuadros publicados por el INEI

Los indicadores de este repositorio se contrastan automáticamente contra los valores
publicados en el **Capítulo 12 · Violencia contra las mujeres, niñas y niños** (y el
cuadro 2.15 del Capítulo 2) del informe principal de la ENDES.

* Valores de referencia: [`validacion/valores_referencia_inei.csv`](../validacion/valores_referencia_inei.csv)
* Extracción: [`scripts/extraer_valores_inei.py`](../scripts/extraer_valores_inei.py)
* Pruebas: [`tests/test_validacion_inei.py`](../tests/test_validacion_inei.py)

```bash
pytest tests -q
```

## Resultado

**55 de 55 valores de referencia coinciden con la cifra oficial**, en estimación puntual y en
desviación estándar, para los años 2021-2025. Tolerancia: 0,005 pp cuando el INEI publica dos
decimales y 0,05 pp cuando publica uno (los valores de 2021 en los cuadros de serie histórica
vienen redondeados a un decimal).

| Cuadro INEI | Indicadores | Valores | Estado |
|---|---|--:|:--:|
| 12.1.1 | Violencia total, psicológica y/o verbal, física y sexual **alguna vez** | 18 | ✅ |
| 12.1.1 / 12.1 | Violencia total alguna vez 2021 (dos decimales) | 1 | ✅ |
| 12.1.1 / 12.2 | Violencia psicológica y/o verbal 2021 (dos decimales) | 1 | ✅ |
| 12.4.1 | Violencia física, sexual y física y/o sexual, **últimos 12 meses** | 15 | ✅ |
| 12.4.2 | Violencia total y psicológica y/o verbal, **últimos 12 meses** | 10 | ✅ |
| 12.10 | Búsqueda de ayuda en personas cercanas y en instituciones | 10 | ✅ |

La diferencia máxima en la estimación puntual es de 0,048 pp, y se da únicamente en los valores
de 2021 que el cuadro 12.1.1 publica con un solo decimal. Donde el INEI publica dos decimales la
coincidencia llega al tercer decimal.

### Universo

El universo se reproduce exactamente, tanto en casos sin ponderar como en el total ponderado:

| Año | n INEI | n calculado | Ponderado INEI | Ponderado calculado |
|---|--:|--:|--:|--:|
| 2022 | 21 321 | 21 321 | 18 397,60 | 18 397,60 |
| 2023 | 21 349 | 21 349 | 18 076,95 | 18 076,95 |
| 2024 | 20 398 | 20 398 | 17 435,53 | 17 435,53 |
| 2025 | 19 271 | 19 271 | 16 120,83 | 16 120,83 |

(El informe no publica el número de casos de 2021; el universo calculado para ese año es de
21 797 mujeres, 18 705,23 ponderadas.)

### Prevalencia — violencia ejercida alguna vez

Porcentaje de mujeres de 15 a 49 años alguna vez unidas.

| Indicador | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|--:|--:|--:|--:|--:|
| Total | 54,86 | 55,66 | 53,76 | 51,96 | 49,09 |
| Psicológica y/o verbal | 50,83 | 51,89 | 49,34 | 48,42 | 45,60 |
| Física | 26,69 | 27,76 | 27,19 | 25,46 | 23,24 |
| Sexual | 5,86 | 6,70 | 6,46 | 5,60 | 5,64 |

### Prevalencia — violencia ejercida en los últimos 12 meses

| Indicador | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|--:|--:|--:|--:|--:|
| Total | 33,61 | 35,63 | 34,46 | 33,89 | 30,99 |
| Psicológica y/o verbal | 32,49 | 34,81 | 33,51 | 33,13 | 30,33 |
| Física | 6,95 | 8,12 | 7,64 | 7,00 | 6,53 |
| Sexual | 1,75 | 2,17 | 1,87 | 1,71 | 1,56 |
| Física y/o sexual | 7,57 | 8,57 | 8,26 | 7,51 | 6,82 |

### Búsqueda de ayuda (cuadro 12.10)

Porcentaje de mujeres que fueron maltratadas físicamente.

| Indicador | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|--:|--:|--:|--:|--:|
| En personas cercanas | 44,02 | 45,69 | 45,34 | 44,56 | 45,47 |
| En alguna institución | 29,27 | 29,08 | 29,66 | 29,46 | 31,36 |

### Errores estándar

El estimador de linealización de Taylor con estrato `V022` y conglomerado `V001` reproduce la
desviación estándar publicada con una diferencia máxima de **0,0002 pp** en los 44 valores para
los que el INEI la publica (no la publica para 2021). El intervalo de confianza al 95 % coincide
con `estimación ± 1,96 · D.E.` y el coeficiente de variación con `100 · D.E. / estimación`.

Ejemplo (violencia total alguna vez):

| Año | Est. | D.E. INEI | D.E. calc. | IC 95 % INEI | CV INEI | CV calc. |
|---|--:|--:|--:|---|--:|--:|
| 2022 | 55,66 | 0,750 | 0,750 | [54,19 – 57,13] | 1,35 | 1,35 |
| 2023 | 53,76 | 0,711 | 0,711 | [52,36 – 55,15] | 1,32 | 1,32 |
| 2024 | 51,96 | 0,749 | 0,749 | [50,49 – 53,43] | 1,44 | 1,44 |
| 2025 | 49,09 | 0,839 | 0,839 | [47,45 – 50,74] | 1,71 | 1,71 |

## Indicadores fuera del contraste automático

Algunos cuadros del informe publican la serie **solo para 2025**. El repositorio los calcula,
pero no forman parte de la tabla de referencia y por tanto no se contrastan:

| Cuadro | Indicador | Motivo |
|---|---|---|
| 12.2 | Componentes de control, humillación y amenaza | Serie publicada solo para 2025 (el agregado sí se valida vía 12.1.1) |
| 12.11 | Fuentes de ayuda en personas cercanas | Solo 2025 |
| 12.12 | Institución a la que acudió | Solo 2025 |
| 12.13 | Razones para no buscar ayuda | Solo 2025 |
| 12.8 | Consumo de alcohol de la pareja | Solo 2025; además el rótulo del cuadro no coincide con la distribución observada de `D114` |
| 2.15 | Toma de decisiones del hogar | Los componentes por decisión se publican solo para 2025 |

Incorporarlos es cuestión de ampliar el mapa de celdas de
[`scripts/extraer_valores_inei.py`](../scripts/extraer_valores_inei.py) y volver a generar
`validacion/valores_referencia_inei.csv`.
