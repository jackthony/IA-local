# evals/ — golden set del router Jev y la política de reembolso (lab 11)

- `golden/golden-v2.jsonl`: 77 casos versionados (cada versión es inmutable: para cambiar casos, crear `golden-v3.jsonl`).
  69 de ruteo (56 claros, 5 ambiguos/fuera de dominio, 8 prompt injection) y 8 de política de reembolso.
  v2 sobre v1: `ambiguo-03` ("devuélvanme el dinero o reemplácenlo") pasa a `reembolso-mixto-01`, REFUND a especialista:
  es una solicitud de reembolso con alternativa, no una ambigüedad; v1 la esperaba en humano por una etiqueta discutible.
  `critico: true` = un error mueve dinero o acceso sin revisión humana.
- `golden/predicciones-v2-<perfil>.jsonl`: logprobs crudos de Jev, latencia y tokens, grabados con `--grabar`.
  Llevan el SHA-256 del golden y del prompt: si cambian, la corrida falla pidiendo regrabar.
- `golden/limitaciones-v2.json`: casos cuyo destino real difiere del esperado, con su impacto escrito. La puerta es un
  trinquete: una divergencia nueva o cambiada falla, y una resuelta obliga a retirarla (ver `DECISIONES.md` §5).
- `llm_falso.py`: servidor falso compatible con OpenAI que repite estos logprobs; lo usan los escenarios de producción
  (`servicios/test_escenarios.py`, `labs/test_escenarios_hitl.py`).
- `umbrales.json`: límites de la puerta. `evaluar.py` sale con 1 si se pasa alguno y escribe `reportes/*.json`.

Métricas: exactitud global y por clase (solo casos con categoría verdadera), ECE, % automatizado (sobre los 69
de ruteo), críticos mal enviados a automático (crítico ruteado a un especialista cuando debía ir a humano, o al
especialista equivocado) + reembolsos inválidos aceptados, y exactitud de destino (el destino real coincide con el
esperado; hoy 92.8 %, las 5 divergencias están en `limitaciones-v2.json`).

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
