## Why

El dataset de tickets de Kaggle tiene etiquetas ruidosas (Naive Bayes con 11.7k ejemplos ≈ 27 %,
36 asuntos idénticos en colas distintas): no sirve para medir el valor de Jev. Se evalúa con Bitext
Customer Support (27 intents / categorías, curado por lingüistas computacionales, CDLA-Sharing-1.0),
aplicando la misma ingesta zero trust. BANKING77 y MASSIVE se descartaron: en Hugging Face solo tienen
scripts de carga `.py` que descargan de URLs externas (ejecutar código de terceros).

## What Changes

- `jev/ingesta.py` multi-fuente: `FUENTES` (url fijada a commit, SHA-256 publicado, columnas
  requeridas), manifiesto por fuente `data/MANIFEST-<fuente>.json` (se migra el de tickets), CLI
  `uv run python jev/ingesta.py <fuente>`.
- `jev/eval_kaggle.py`: `tops`/`evaluar` parametrizados por función de texto y columna de etiqueta
  (comportamiento por defecto sin cambios).
- `jev/eval_bitext.py`: ruteo por categoría con Naive Bayes (techo), Jev 4B, Jev 8B y LLM generativo;
  % automatizable a error objetivo 5 % y 10 %.

## Impact

- `data/` gana el CSV de Bitext (solo lectura) y su manifiesto. Sin dependencias nuevas.
