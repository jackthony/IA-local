# evals/ — golden set del router Jev y la política de reembolso (lab 11)

- `golden/golden-v1.jsonl`: 77 casos versionados (v1 es inmutable: para cambiar casos, crear `golden-v2.jsonl`).
  69 de ruteo (55 claros en 11 clases, 6 ambiguos/fuera de dominio, 8 prompt injection) y 8 de política de reembolso.
  `critico: true` = un error mueve dinero o acceso sin revisión humana.
- `golden/predicciones-v1-<perfil>.jsonl`: logprobs crudos de Jev, latencia y tokens, grabados con `--grabar`.
  Llevan el SHA-256 del golden y del prompt: si cambian, la corrida falla pidiendo regrabar.
- `umbrales.json`: límites de la puerta. `evaluar.py` sale con 1 si se pasa alguno y escribe `reportes/*.json`.

Métricas: exactitud global y por clase (solo casos con categoría verdadera), ECE, % automatizado (sobre los 69
de ruteo), críticos mal enviados a automático (crítico ruteado a un especialista cuando debía ir a humano, o al
especialista equivocado) + reembolsos inválidos aceptados.

## Perfiles de modelo (solo variables de entorno)

El cliente es OpenAI-compatible, así que cambiar de Ollama a Azure OpenAI no toca código:

```bash
set -a; source perfiles/ollama.env.example; set +a
uv run python evals/evaluar.py --perfil ollama --grabar

cp perfiles/azure.env.example ~/mi-azure.env   # fuera del repo; rellena endpoint, despliegue, clave y precios
set -a; source ~/mi-azure.env; set +a
uv run python evals/evaluar.py --perfil azure --grabar
uv run python evals/evaluar.py --comparar        # escribe evals/COMPARACION.md
```

`--grabar` se niega si el perfil no coincide con `LLM_BASE_URL` (no guarda datos de nube bajo "ollama").
El costo por 1,000 decisiones usa los tokens medidos y los precios de TU contrato (`PRECIO_*_USD_1M`); no se asumen.
Local = 0 sin contar hardware ni energía.

**Calibración:** `T` y el umbral están calibrados para `qwen3:4b-instruct`. Con otro modelo la confianza no se
transfiere (ECE y % automatizado de Azure salen con la calibración de Ollama). Para una comparación justa de
ECE/automatización, recalibra con `jev/evaluar_empresa.py` y usa un `data/calibracion-*.json` propio.
