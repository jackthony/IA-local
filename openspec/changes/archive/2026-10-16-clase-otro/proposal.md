## Why

Mensajes fuera de dominio salían a un especialista con confianza 0.97 (Ollama y TypeSafe) porque el catálogo no tenía una
opción "otro". Al recalibrar con más muestra se vio además que el umbral anterior (0.70, de 15 ejemplos por clase) era optimista.

## What Changes

- Clase `OTRO` sin especialista (va a humano por "sin especialista"); `data/ood-otro-v1.csv` y `evaluar_empresa.py --extra`.
- `data/calibracion-bitext-otro.json` (40 por clase, T 6.0, umbral 5 % = 0.83); router, Dockerfile y docs apuntan a ella.
- `evals/golden/golden-v3.jsonl` (v2 inmutable), limitaciones y umbrales ajustados con su razón (DECISIONES §8).

## Impact

Más tráfico a humanos (automatización ~68 % sobre el golden vs 82.6 % con el umbral optimista). TypeSafe por regrabar.
