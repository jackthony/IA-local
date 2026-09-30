# Inventario — generado 2026-09-30

Regenerar: `uv run python scripts/inventario.py`. Rutas con `~`; credenciales solo por nombre (nunca valores).

## Máquina

- Sistema: Darwin 25.6.0 (arm64) · RAM 24 GB · CPUs 15
- Python del proyecto: 3.14.7

## Modelos (manifiesto `modelos.json`)

| Modelo | Rol | Obligatorio | Tamaño | Estado | Uso |
|---|---|---|---|---|---|
| qwen3:4b-instruct | router (Jev) y agentes por defecto | sí | 2.50 GB | ok | Default LLM_MODEL: agentes de labs 01-11, Jev (router, triage, evaluación) y servicios. |
| qwen3:8b | manager Magentic / cascada Jev (equipos con poca RAM) | no | 5.23 GB | falta | Opcional: manager de Magentic (MANAGER_MODEL), cascada y diagnóstico de Jev. Requiere reasoning_effort=none. |
| qwen3:30b-a3b | agentes especialistas (Mac) | no | 18.56 GB | falta | LLM_MODEL para agentes: MoE (3B activos), calidad ~30B a velocidad cercana a 4B. |
| gpt-oss:20b | manager / razonamiento (Mac) | no | 13.79 GB | falta | MANAGER_MODEL del lab 07 (Magentic) y tareas de razonamiento. |
| qwen3:32b | manager / razonamiento de máxima calidad (Mac) | no | 20.20 GB | falta | Alternativa densa a gpt-oss:20b; más lento, mejor calidad. |
| qwen3-coder:30b | código (Mac) | no | 18.56 GB | ok | Agentes que programan (MoE). |
| qwen3-embedding:0.6b | embeddings / RAG | no | 0.64 GB | falta | Siguiente tema: grounding con documentos. |

Otros modelos locales (de otros proyectos): ninguno

### Almacenes de modelos detectados en esta máquina

| Almacén | Ruta | Tamaño |
|---|---|---|
| Ollama | ~/.ollama/models | 21.05 GB |
| Hugging Face | ~/.cache/huggingface | 15.24 GB |

### Candidatos que caben en 24 GB de RAM (medir con `jev/eval_bitext.py` antes de adoptar)

- `qwen3:14b` (9.28 GB, ≥24 GB RAM): Siguiente escalón para agentes y Jev: más exactitud que 4B/8B.

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
| clave HMAC de checkpoints | ~/.ia-local/hitl.key | lab 11 (HITL) | no | no |

Generar/rotar tokens: borra `.env` y ejecuta `uv run python scripts/generar_env.py`. Rotar la clave HMAC invalida los checkpoints pendientes del lab 11 (por diseño).

## Imágenes de contenedor (fijadas por digest)

- `ghcr.io/astral-sh/uv:0.9.26` @ `sha256:9a23023be68b…`
- `python:3.12-slim` @ `sha256:f77ac9e44ae9…`
- `jaegertracing/jaeger:2.21.0` @ `sha256:3d0ac795ff98…`

## Herramientas

| Herramienta | Versión |
|---|---|
| uv | uv 0.12.19 (Homebrew 2026-09-24 aarch64-apple-darwin) |
| ollama | ollama version is 0.34.2 |
| git | git version 2.55.0 |
| gh | gh version 2.97.0 (2026-07-31) |
| docker | Docker version 29.7.2, build a7dcaa6 |
| openspec | no instalado |

## Proyecto

- Labs: 11 · specs OpenSpec: 12 · changes archivados: 13 · suites de tests: 11
- Tamaños: .venv 0.06 GB · data 0.04 GB
- Paquetes Python en uv.lock: 68

## Estado

✅ Todo lo obligatorio está presente y verificado.
