# IA-local

**Lab de agentes, A2A y orquestación con modelos locales**, más un router de decisiones tipadas (Jev) listo para
producción local con Docker.

[![tests](https://github.com/jackthony/IA-local/actions/workflows/tests.yml/badge.svg)](https://github.com/jackthony/IA-local/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-%E2%89%A53.12-blue)
![Licencia](https://img.shields.io/badge/licencia-MIT-green)

**Stack:** Ollama (CPU o GPU Metal) · Microsoft Agent Framework (Python) · A2A SDK · MCP.
El cliente es OpenAI-compatible (`labs/common.py`): el mismo código corre contra Ollama local, vLLM on-prem o
DeepSeek/OpenAI con solo cambiar variables de entorno.

## Contenido

- [Documentación](#documentación)
- [Inicio rápido](#inicio-rápido)
- [Labs](#labs)
- [Evaluación continua](#evaluación-continua)
- [Producción local con Docker](#producción-local-con-docker)
- [Configuración](#configuración)
- [Lecciones encontradas](#lecciones-encontradas)
- [Roadmap](#roadmap)
- [Auditoría de alternativas a Jev](#auditoría-zero-trust-de-alternativas-open-source-a-jev)
- [Licencia](#licencia)

## Documentación

| Documento | Para qué sirve |
|---|---|
| [ARQUITECTURA.md](ARQUITECTURA.md) | **Empieza aquí**: mapa del repo, flujo del sistema, credenciales y orden de carpetas |
| [DECISIONES.md](DECISIONES.md) | El porqué de cada decisión, con su medición |
| [INVENTARIO.md](INVENTARIO.md) | Estado de cada máquina (se regenera con `scripts/inventario.py`) |
| [jev/README.md](jev/README.md) | Jev local: decisiones tipadas con probabilidad calibrada |
| [evals/README.md](evals/README.md) | Golden sets, umbrales, perfiles de modelo y cascada |
| [experimentos/](experimentos/README.md) | Cómo se descubrió cada decisión |
| [modelos.json](modelos.json) | Modelos fijados por digest |
| [data/LICENCIAS.md](data/LICENCIAS.md) | Licencias y manifiestos de los datasets |
| [openspec/specs/](openspec/specs) | Specs vigentes (el historial está en `openspec/changes/archive`) |

## Inicio rápido

```bash
# 1. Herramientas (en Apple Silicon Ollama usa la GPU vía Metal)
brew install uv
brew install --cask ollama

# 2. Repo público y dependencias EXACTAS del lock (hashes verificados)
git clone https://github.com/jackthony/IA-local.git && cd IA-local
uv sync --locked

# 3. Modelos
ollama pull qwen3:4b-instruct
ollama pull qwen3:8b          # opcional (manager de Magentic / cascada)

# 4. Verificar: escáner de secretos + tests deterministas (sin LLM)
uv run python scripts/escanear_secretos.py
uv run python jev/test_jev.py

# 5. Inventario de tu máquina -> INVENTARIO.md
uv run python scripts/inventario.py
```

En Windows el flujo es igual: `uv sync --locked` y `ollama pull qwen3:4b-instruct`.

**Datos.** El repo trae los dos datasets en `data/` (~38 MB, cada uno con manifiesto SHA-256 y licencia) y la
calibración `data/calibracion-bitext-otro.json` (sin PII). Los labs 10 y 11 funcionan tras clonar, sin descargar
nada. `uv run python jev/ingesta.py bitext` (o `tickets`) regenera o audita desde la fuente fijada a commit; no es
un paso obligatorio.

| Dataset | Licencia |
|---|---|
| Bitext | CDLA-Sharing-1.0 |
| Tickets multi-idioma | CC BY-NC 4.0 (solo no comercial) |

## Labs

| # | Patrón | Comando | Tiempo (CPU) |
|---|---|---|---|
| 01 | Agente + tools | `uv run python labs/01_agent_tools.py` | ~10 s |
| 02 | Secuencial + concurrente (fan-out) | `uv run python labs/02_sequential_concurrent.py` | ~80 s |
| 03 | Handoff (triage → especialistas) | `uv run python labs/03_handoff.py` | ~45 s |
| 04 | Servidor A2A (Agent Card + JSON-RPC) | `uv run uvicorn --app-dir labs 04_a2a_server:app --port 5001` | — |
| 05 | Orquestador → agente remoto vía A2A | `uv run python labs/05_a2a_orchestrator.py` (con el 04 corriendo) | ~40 s |
| 06 | Group chat: round-robin vs director LLM | `uv run python labs/06_group_chat.py` | ~5 min |
| 07 | Magentic-One: manager planifica, delega, replanifica | `uv run python labs/07_magentic.py` | ~18 min ⚠️ |
| 08 | Servidor MCP `empresa` (stdio) | lo lanza el lab 09 como subproceso | — |
| 09 | Agentes comparten MCP con mínimo privilegio + `ExigeTool` | `uv run python labs/09_mcp_agents.py` | ~45 s |
| 10 | Router Jev (System 1) + especialistas (System 2) + cola humana | `uv run python labs/10_router_jev.py` | ~1 min |
| 11 | Aprobación humana reanudable: revisión de ruteo y reembolsos con checkpoints sellados | `uv run python labs/11_hitl_router.py iniciar` → `revisar` → `responder <id> '<json>'` (o `supervisor-demo`) | ~1 min + humano |

- Agent Card (lab 04): <http://localhost:5001/.well-known/agent-card.json>
- Datos de negocio: fuente única en `labs/empresa.py` (la usan el servidor MCP y los labs 04/07).

**Tests deterministas (sin LLM):**

```bash
uv run python labs/test_divisas.py
uv run python labs/test_orquestacion.py
uv run python labs/test_mcp.py                  # protocolo MCP real
uv run python labs/test_router.py
uv run python labs/test_hitl.py
uv run python labs/test_escenarios_hitl.py
uv run python servicios/test_servicios.py
uv run python servicios/test_escenarios.py
```

## Evaluación continua

`evals/` mide el router Jev (lab 10) y la política de reembolso (lab 11) contra **85 casos versionados**
(`evals/golden/golden-v3.jsonl`: 77 de ruteo, incluida la clase `OTRO` y 8 de prompt injection, y 8 de reembolso).
Mide exactitud por clase, ECE, % automatizado y casos críticos enviados por error a automático.

| Métrica (golden-v3, `qwen3:4b-instruct`) | Medido | Límite en `evals/umbrales.json` |
|---|---|---|
| Exactitud global | 92.8 % | ≥ 90 % |
| ECE | 0.049 | ≤ 0.08 |
| Automatizado | 59.7 % | ≥ 55 % |
| Críticos a automático | 0 | 0 |

CI falla si se pasa algún umbral y deja un reporte JSON por corrida en `evals/reportes/`.

```bash
uv run python evals/evaluar.py             # repite predicciones grabadas, sin LLM (lo que corre CI)
uv run python evals/evaluar.py --grabar    # mide en vivo con el modelo de LLM_BASE_URL / LLM_MODEL
```

> **Ojo con el golden propio.** El hold-out independiente (240 casos) y la medición con consultas de otro rubro
> (Banking77) muestran que la meta del 5 % de error **no transfiere** fuera del golden propio
> ([DECISIONES §10, §12 y §14](DECISIONES.md)). Para uso real, calibra con tus propios tickets
> (`evals/csv_a_golden.py`).

Más opciones, todas en [evals/README.md](evals/README.md):

- **Perfiles de modelo:** Ollama, DeepSeek y el Jev alojado de TypeSafe, sin tocar código.
- **Cascada** (`--cascada`): Ollama decide y un segundo juez remoto solo desempata dudas, con cupo de consultas.
- **Golden privado** a partir de tickets reales, con PII anonimizada.

**Escenarios de producción.** Los mismos casos recorren el servicio real de extremo a extremo contra un servidor
falso compatible con OpenAI (sin LLM, corre en CI): `servicios/test_escenarios.py` cubre HTTP, auth, PII, modelo
caído o lento y telemetría sin contenido. `labs/test_escenarios_hitl.py` cubre reembolsos, checkpoints, cola y
ledger. Con `--vivo` se repiten contra el modelo real para detectar deriva. Las divergencias de destino aceptadas
están en `evals/golden/limitaciones-v3-ollama.json`.

## Producción local con Docker

Tres servicios endurecidos más Jaeger, con Ollama nativo en el host (GPU Metal):

| Servicio | Qué hace | Puerto (solo 127.0.0.1) | Auth |
|---|---|---|---|
| `router-api` | Jev como servicio de decisión (`POST /v1/decidir`) | 8000 | `API_TOKEN` |
| `a2a-divisas` | Agente A2A; usa el MCP por HTTP con su propio token | 5001 | `A2A_TOKEN` (card pública) |
| `mcp-empresa` | MCP de sistemas de negocio (streamable HTTP, protección DNS rebinding) | interno | `MCP_TOKEN` |
| `jaeger` | Trazas OpenTelemetry (sin contenido de mensajes) | 16686 | — |

```bash
ollama serve                                  # si la app de Ollama no está abierta
uv sync --locked --extra prod
uv run python scripts/generar_env.py          # .env con tokens nuevos (no se imprimen ni van a git)
docker compose up -d --build                  # imágenes fijadas por digest, sin root ni capabilities
uv run python servicios/cliente_demo.py       # decisión del router, A2A→MCP con token y 401 sin token
open http://127.0.0.1:16686                   # trazas en Jaeger
docker compose down
```

Sin Docker (mismo código, útil para depurar): exporta los tokens de `.env` y corre
`servicios/mcp_http.py`, `uvicorn --app-dir servicios a2a_divisas:app --port 5001` y
`uvicorn --app-dir servicios router_api:app --port 8000` con `LLM_BASE_URL=http://localhost:11434/v1`.
Probado así en Windows: 401 sin token en los tres, 421 con Host falso en el MCP, A2A→MCP → 937.5 soles.

## Configuración

| Variable | Default | Producción (ejemplo) |
|---|---|---|
| `LLM_BASE_URL` | `http://localhost:11434/v1` | `http://vllm.interno:8000/v1` |
| `LLM_MODEL` | `qwen3:4b-instruct` | `Qwen/Qwen3-32B` |
| `LLM_API_KEY` | `ollama` | secreto del gateway |
| `A2A_URL` | `http://localhost:5001/` | URL pública del agente |

Perfiles listos en `perfiles/` (`ollama`, `deepseek`, `typesafe`; copia el `.env.example` fuera del repo).

**Modelos:** `qwen3:4b-instruct` (rápido, default) · `qwen3:8b` (mejor razonamiento, ~2x más lento). Evita
`qwen3:4b` (variante *thinking-only*: razona siempre, ~5x más lento en CPU).

## Lecciones encontradas

### Modelos pequeños

- **LLM pequeño + aritmética = alucinación.** El agente `divisas` dijo 250 USD ≈ 39,000 PEN. Fix: tool
  determinista `convertir` (ver `openspec/specs/divisas`). Datos y cálculos, siempre en tools.
- **Estructura en código, contenido en el LLM.** Un 4B no respeta reglas de estado en el prompt ("si ya hablaste,
  cierra"), y el director LLM del group chat devolvía `terminate=true` en la ronda 0. El selector fija el orden y la
  condición de término decide el final.
- **El debate adversarial fabrica evidencia.** Con roles fijos, los agentes inventan estadísticas y fuentes para
  ganar. Dales datos vía tools/MCP/RAG y un verificador; "no inventes" no basta.
- **Restringir tools no restringe al modelo.** El `analista` no tenía `convertir` y aun así convirtió con una tasa
  inventada; `finanzas` copió esa cifra. Los agentes confían en lo que dice el agente anterior.
- **Ollama ignora `tool_choice`** (auto/required/función: mismo resultado, medido). La obligación va en código:
  middleware `ExigeTool` en `common.py` verifica el `function_call` y reintenta.
- **Los modelos híbridos (`qwen3:8b`) razonan por defecto.** `default_options={"reasoning_effort": "none"}` baja de
  ~100 s a ~5 s por llamada en CPU.

### Orquestación

- **El handoff en malla hace ping-pong** con modelos chicos. Usa estrella (`add_handoff(triage, [...])`),
  `turn_limits` y `termination_condition`.
- **El group chat rompe backends estrictos.** El historial compartido trae varios `assistant` seguidos y Ollama
  responde 400. Fix: `otros_como_user` en `common.py` envía los mensajes de otros agentes como `user` `[autor]: texto`.
- **Las condiciones de término son frágiles.** El modelo escribe `**Veredicto:**`, no `VEREDICTO:`. Normaliza y deja
  siempre `max_rounds` como red de seguridad.
- **Magentic es el patrón más caro:** ~5 llamadas largas del manager por tarea (~18 min con 4B, ~20 min con 8B).
  Úsalo para tareas abiertas; si el flujo es conocido, secuencial o handoff cuesta 10–20x menos.
- `agent-framework-ollama` (beta) falla en handoff (`allow_multiple_tool_calls`); por eso se usa el endpoint
  OpenAI-compatible de Ollama.

### Router Jev y seguridad

- **Router Jev (lab 10).** Jev decide en ~1.3 s (mediana) con confianza calibrada y el código rutea; el especialista
  tarda ~8 s. De 8 mensajes: 5 auto (todos correctos) y 3 a humano (frontera ambigua "cancel my order", un mensaje
  ambiguo y el prompt injection). Jev le dio ACCOUNT 0.97 al ataque: **sin el detector habría llegado a un agente**.
  Defensa en profundidad: salida acotada + detector + agentes sin tools sensibles + humano.
- **La anonimización tiene costo.** El especialista respondió "envíe el detalle a [EMAIL]". Guarda el mapa
  marcador → valor fuera del modelo y rehidrata en código.
- **Un prompt puede inducir la fuga que intentas evitar.** Decir "si ves [EMAIL_1], úsalo" hizo que el modelo
  inventara el marcador en un caso sin PII. Fix: no mencionar marcadores + `limpiar_marcadores` como última barrera;
  PII solo en una bóveda por caso, borrada al entregar.
- **HITL reanudable (lab 11).** `request_info` pausa el workflow, el checkpoint queda en disco y otro proceso lo
  reanuda con la decisión humana (iniciar → revisar → responder en 3 procesos).
- **Los checkpoints del framework llevan pickle** (restringido) incluso con dicts: se sellan con HMAC-SHA256 (clave
  en `~/.ia-local/hitl.key`, fuera del repo) y un sello nunca se reescribe. Un byte alterado → "sello inválido".
- **El LLM propone, el humano aprueba, el código ejecuta.** `emitir_reembolso` usa `approval_mode="always_require"`;
  tras aprobar, el código lo ejecuta con esos argumentos y aplica política (S/ 900 → rechazado).
- **Sellar por glob legitima lo ajeno; firmar el checkpoint no firma lo que ve el humano.** La revisión del
  2026-09-30 (`openspec/changes/endurecer-hitl`) encontró un checkpoint plantado sellado en la siguiente corrida, una
  cola sin firma que mostraba S/ 45 mientras se pagaban S/ 450, doble pago tras una caída, y un zero-width que
  evadía el detector. Fix: sello al guardar, cola firmada, reembolso idempotente y detector que normaliza el texto.

## Roadmap

- [x] Agente + tools, secuencial, concurrente, handoff, A2A
- [x] Group chat y Magentic
- [x] Servidor MCP como tool compartido entre agentes
- [x] Jev local: decisiones tipadas con probabilidad calibrada ([jev/README.md](jev/README.md))
- [x] Human-in-the-loop (aprobación de tools) y checkpointing (lab 11)
- [x] Producción: Docker Compose, auth entre servicios, OpenTelemetry → Jaeger (validado en la MacBook)
- [x] CI/CD trunk-based: gate local = CI, evals con umbrales, auditoría OSV
- [x] Evals fuera del golden propio: hold-out de 240 casos, otro rubro (Banking77), cascada con segundo juez
- [ ] Calibrar con tickets reales de la empresa (la meta del 5 % no transfiere desde Bitext)

## Auditoría zero trust de alternativas open source a Jev

Hecha el 2026-09-28, solo remota: metadatos y búsquedas del lado del servidor (GitHub API/code search, PyPI
Integrity, OSV, HF API). Ningún código de terceros se ejecutó ni quedó en disco.

| | Kev (jaredpalmer) | AnyJev ("nokia-applied-research") |
|---|---|---|
| Identidad | ✅ cuenta 2013, 10.6k seguidores | 🚩 org creada 2026-08-03, no verificada, 2 contribuidores |
| Commits firmados | ✅ 30/30 | 🚩 0/30 |
| PyPI | 🚩 `kev` en PyPI es OTRO paquete (2016): instalar solo desde git + commit fijo | ✅ attestation PEP 740 desde el repo |
| Deserialización | ⚠️ `head.pt` (pickle) con `torch.load` sin `weights_only` (mitigado por torch>=2.6) | ✅ heads en JSON |
| CPU/Ollama | ❌ torch + transformers | ❌ HF/vLLM (`allowed_token_ids`) |

**Veredicto:** ninguno listo para la empresa hoy (repos de menos de 2 semanas, sin OpenSSF Scorecard). Si se quiere
adoptar uno: prueba en sandbox desechable sin red, nunca en equipos de trabajo.

## Licencia

Código bajo [MIT](LICENSE). Los datasets de `data/` mantienen sus propias licencias (CDLA-Sharing-1.0 y
CC BY-NC 4.0, solo uso no comercial): ver [data/LICENCIAS.md](data/LICENCIAS.md).
