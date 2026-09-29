## Why

El demo de Jev usó 40 tickets escritos a mano: muy pocos y fáciles para probar valor. Se evalúa con un
dataset público etiquetado de Kaggle (Tobias Bueck, "Customer IT Support - Ticket Dataset", espejo del
mismo autor en Hugging Face), aplicando zero trust a los DATOS: procedencia verificada por hash, solo
texto plano, escaneo de contenido hostil y trato de los tickets como entrada no confiable al modelo.

## What Changes

- `jev/ingesta.py`: descarga en memoria con tope de tamaño, verificación SHA-256 contra el hash LFS
  publicado, parseo con `csv` (stdlib) y chequeo de esquema, escaneo de celdas (inyección de fórmulas,
  marcadores de prompt injection, Unicode bidi/invisible), escritura en `data/` solo si todo pasa, y
  `data/MANIFEST.json` con procedencia.
- `jev/eval_kaggle.py`: subconjunto por idioma (en por defecto; el archivo no trae español), muestra estratificada determinista (calibración /
  evaluación), triage de cola (queue) con Jev: exactitud, ECE, Brier, % automatizable a error objetivo
  5 % y 10 %, exactitud por cola y comparación con LLM generativo.
- Tests deterministas sin red ni LLM.

## Impact

- Nuevo `data/` (dataset CC BY-NC 4.0: solo evaluación/aprendizaje, NO producción).
- Sin dependencias nuevas.
