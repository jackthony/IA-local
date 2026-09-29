## 1. Tests
- [x] 1.1 test_datos.py: filas con requeridas por fuente; FUENTES registradas (fallan antes)

## 2. Ingesta
- [x] 2.1 ingesta.py multi-fuente + manifiesto por fuente; migrar MANIFEST.json de tickets
- [x] 2.2 Ingestar bitext y revisar hallazgos (13 falsos positivos en `response`, documentados en el manifiesto)

## 3. Evaluación
- [x] 3.1 eval_kaggle.py: tops/evaluar parametrizados (sin cambio de comportamiento)
- [x] 3.2 eval_bitext.py (NB, 4B, 8B, generativo, auto 5/10 %)
- [x] 3.3 Ejecutar y documentar en jev/README.md (4B + descripciones: 94 %, automatiza 89 % con 99 %)
