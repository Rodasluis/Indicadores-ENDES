# Documentación del INEI (no versionada)

Esta carpeta guarda material publicado por el INEI que **no se redistribuye** en el
repositorio (ver `.gitignore`). Para reproducir la validación desde cero, descárgalo del
portal del INEI y colócalo así:

```
referencias/
├── cuadros_inei/          cuadros del informe ENDES en Excel, una carpeta por capítulo
│   ├── Cap. 2/Cap. 2_2025.xlsx
│   └── Cap. 12/Cap. 12_2025.xlsx
├── diccionarios/          diccionarios de variables por cuestionario (PDF)
├── manuales/              manuales de la entrevistadora y de la antropometrista (PDF)
└── FICHA_TECNICA_ENDES_2025.pdf
```

`scripts/extraer_valores_inei.py` lee `cuadros_inei/Cap. 12/Cap. 12_2025.xlsx` para
regenerar `validacion/valores_referencia_inei.csv`. Ese CSV **sí** está versionado, de modo
que la validación funciona sin necesidad de tener los libros originales.
