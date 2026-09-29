## ADDED Requirements

### Requirement: Ingesta multi-fuente
`FUENTES` SHALL definir por fuente: repo, commit, archivo, SHA-256 publicado, licencia y columnas
requeridas. `filas(texto, requeridas)` SHALL validar las columnas de esa fuente. Cada fuente SHALL
escribir su manifiesto `data/MANIFEST-<fuente>.json`.

#### Scenario: Columnas de Bitext
- **WHEN** `filas("flags,instruction,intent\nB,hola,x\n", {"instruction", "category", "intent"})`
- **THEN** lanza `ValueError` que menciona `category`

#### Scenario: Fuentes registradas
- **WHEN** se consulta `FUENTES`
- **THEN** contiene `tickets` y `bitext`, cada una con `sha256` de 64 caracteres hexadecimales y `url` fijada a su commit

### Requirement: Evaluación Bitext
`jev/eval_bitext.py` SHALL, sobre la misma muestra estratificada por categoría, reportar exactitud de
Naive Bayes (entrenado con el resto), Jev 4B, Jev 8B (reasoning_effort none) y LLM generativo 4B; ECE
calibrado y % automatizable con exactitud en automático a error objetivo 5 % y 10 % para Jev. SHALL
verificar el SHA-256 del CSV contra su manifiesto antes de usarlo.

#### Scenario: Reporte
- **WHEN** se ejecuta con el CSV verificado
- **THEN** imprime la tabla comparativa y, por cada configuración Jev, la automatización a 5 % y 10 %
