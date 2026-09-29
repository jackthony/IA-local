## 1. Tests
- [x] 1.1 jev/test_datos.py: verificar, hallazgos, filas, muestra (falla antes de implementar)
- [x] 1.2 Guarda Trojan Source `test_sin_invisibles()` (detectó 3 archivos propios; corregidos)
- [x] 1.3 Tests de descripciones (test_jev.py) y NaiveBayes (test_datos.py)

## 2. Ingesta zero trust
- [x] 2.1 jev/ingesta.py (verificar, hallazgos, filas, descarga en memoria, MANIFEST)
- [x] 2.2 Ejecutar ingesta y revisar reporte de hallazgos (15 fórmulas '-', 1 falso positivo '<user>' corregido; sin ES)

## 3. Evaluación y diagnóstico
- [x] 3.1 jev/eval_kaggle.py (muestra, métricas, umbrales 5/10 %, por cola, baseline generativo)
- [x] 3.2 Choice con descripciones; jev/diagnostico_kaggle.py (4B sin/con desc, 8B, NB, colas agrupadas)
- [x] 3.3 Ejecutar y documentar en jev/README.md (cuello de botella: etiquetas; Jev automatiza ~0 %)
