# Inventario — generado 2026-09-29

Regenerar: `uv run python scripts/inventario.py`. Rutas con `~`; credenciales solo por nombre (nunca valores).

## Máquina

- Sistema: Windows 11 (AMD64) · RAM 24 GB · CPUs 8
- Python del proyecto: 3.12.12

## Modelos (manifiesto `modelos.json`)

| Modelo | Obligatorio | Tamaño | Estado | Uso |
|---|---|---|---|---|
| qwen3:4b-instruct | sí | 2.50 GB | ok | Default LLM_MODEL: agentes de labs 01-11, Jev (router, triage, evaluación) y servicios. |
| qwen3:8b | no | 5.23 GB | ok | Opcional: manager de Magentic (MANAGER_MODEL), cascada y diagnóstico de Jev. Requiere reasoning_effort=none. |

Otros modelos locales (de otros proyectos): ninguno

### Almacenes de modelos detectados en esta máquina

| Almacén | Ruta | Tamaño |
|---|---|---|
| Ollama | ~/.ollama/models | 7.72 GB |
| Hugging Face | ~/.cache/huggingface | 2.00 GB |

### Candidatos que caben en 24 GB de RAM (medir con `jev/eval_bitext.py` antes de adoptar)

- `qwen3:14b` (9.28 GB, ≥24 GB RAM): Siguiente escalón para agentes y Jev: más exactitud que 4B/8B.
- `qwen3-embedding:0.6b` (0.64 GB, ≥8 GB RAM): Embeddings para RAG (siguiente tema: grounding con documentos).

## Datasets (verificados por SHA-256 contra su manifiesto)

| Fuente | Archivo | Tamaño | Estado | Licencia |
|---|---|---|---|---|
| tickets | dataset-tickets-multi-lang-4-20k.csv | 0.02 GB | ok | CC BY-NC 4.0 |
| bitext | Bitext_Sample_Customer_Support_Training_Dataset_ | 0.02 GB | ok | CDLA-Sharing-1.0 |

## Credenciales

| Credencial | Dónde vive | La usa | Presente | ≥32 bytes |
|---|---|---|---|---|
| API_TOKEN | .env (por máquina, fuera de git) | router-api | sí | sí |
| A2A_TOKEN | .env (por máquina, fuera de git) | a2a-divisas | sí | sí |
| MCP_TOKEN | .env (por máquina, fuera de git) | mcp-empresa | sí | sí |
| clave HMAC de checkpoints | ~/.ia-local/hitl.key | lab 11 (HITL) | sí | sí |

Generar/rotar tokens: borra `.env` y ejecuta `uv run python scripts/generar_env.py`. Rotar la clave HMAC invalida los checkpoints pendientes del lab 11 (por diseño).

## Imágenes de contenedor (fijadas por digest)

- `ghcr.io/astral-sh/uv:0.9.26` @ `sha256:9a23023be68b…`
- `python:3.12-slim` @ `sha256:f77ac9e44ae9…`
- `jaegertracing/jaeger:2.21.0` @ `sha256:3d0ac795ff98…`

## Herramientas

| Herramienta | Versión |
|---|---|
| uv | uv 0.9.26 (ee4f00362 2026-01-15) |
| ollama | ollama version is 0.34.4 |
| git | git version 2.49.0.windows.1 |
| gh | gh version 2.87.3 (2026-02-23) |
| docker | Docker version 29.1.3, build f52814d |
| openspec | instalado (versión no disponible) |

## Proyecto

- Labs: 11 · specs OpenSpec: 10 · changes archivados: 10 · suites de tests: 11
- Tamaños: .venv 0.08 GB · data 0.04 GB
- Paquetes Python en uv.lock: 68

## Estado

✅ Todo lo obligatorio está presente y verificado.
