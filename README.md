# IA-local — Lab de agentes, A2A y orquestación con modelos locales

📐 **Empieza por [ARQUITECTURA.md](ARQUITECTURA.md)** (mapa, credenciales, orden de carpetas y siguiente
nivel en Mac) · 📋 [INVENTARIO.md](INVENTARIO.md) (se regenera por máquina) · 🧭 [DECISIONES.md](DECISIONES.md) (el porqué de cada decisión) · 🧠 [modelos.json](modelos.json)
(modelos por digest) · 🧪 [experimentos/](experimentos/) (cómo se descubrió cada decisión)

Stack: **Ollama** (CPU) + **Microsoft Agent Framework** (Python) + **A2A SDK**.
El cliente es OpenAI-compatible (`labs/common.py`): el mismo código corre contra Ollama local,
vLLM on-prem o DeepSeek/OpenAI con solo cambiar variables de entorno.

## Setup en macOS (MacBook)

```bash
# 1. Herramientas (instaladores oficiales; en Apple Silicon Ollama usa la GPU vía Metal: mucho más rápido que CPU)
brew install uv              # o: https://docs.astral.sh/uv/
brew install --cask ollama    # o la app oficial de https://ollama.com/download
# 2. Repo (público)
git clone https://github.com/jackthony/IA-local.git && cd IA-local
# 3. Dependencias EXACTAS del lock (hashes verificados) y modelos
uv sync --locked
ollama pull qwen3:4b-instruct
ollama pull qwen3:8b          # opcional (manager de Magentic / cascada)
# 4. Verificar: tests deterministas (sin LLM) + escáner de secretos
uv run python scripts/escanear_secretos.py
uv run python jev/test_jev.py
# 5. Inventario de TU máquina: modelos vs modelos.json (digest), otros almacenes (tus otros proyectos),
#    candidatos que caben en tu RAM, credenciales (solo nombres) -> INVENTARIO.md
uv run python scripts/inventario.py
```

Datos: el repo **sí trae** los dos datasets en `data/` (~38 MB, versionados, cada uno con su manifiesto SHA-256
y su licencia en [data/LICENCIAS.md](data/LICENCIAS.md)), más la calibración `data/calibracion-bitext-demo.json`
(sin PII). Los labs 10 y 11 funcionan tras clonar, sin descargar nada. `uv run python jev/ingesta.py bitext`
(y `tickets`) descarga de nuevo desde la fuente fijada a commit y verifica el SHA-256: sirve para regenerarlos o
auditarlos, no es un paso obligatorio. El dataset de tickets es CC BY-NC 4.0 (solo no comercial); Bitext es CDLA-Sharing-1.0.

## Evaluación continua (golden set)

`evals/` mide el router Jev (lab 10) y la política de reembolso (lab 11) contra 77 casos versionados
(`evals/golden/golden-v2.jsonl`): exactitud por clase, ECE, % automatizado y casos críticos mal enviados a
automático. `evals/umbrales.json` fija los límites; CI falla si se pasa alguno y deja un reporte JSON por corrida
en `evals/reportes/`. Perfiles de modelo (Ollama / DeepSeek) y comparación: [evals/README.md](evals/README.md).

```bash
uv run python evals/evaluar.py             # repite predicciones grabadas, sin LLM (lo que corre CI)
uv run python evals/evaluar.py --grabar    # mide en vivo con el modelo de LLM_BASE_URL / LLM_MODEL
```

**Escenarios de producción.** Los mismos casos recorren el servicio real, de extremo a extremo, contra un servidor falso
compatible con OpenAI (sin LLM, corre en CI): `servicios/test_escenarios.py` (HTTP, auth, PII, modelo caído o lento,
telemetría sin contenido) y `labs/test_escenarios_hitl.py` (reembolsos, checkpoints, cola y ledger del lab 11).
`servicios/test_escenarios.py --vivo` repite los escenarios del router contra el modelo real para detectar deriva.
Las divergencias de destino que se aceptan están listadas con su impacto en `evals/golden/limitaciones-v2-ollama.json`.

## Producción local con Docker (MacBook)

Tres servicios endurecidos + Jaeger, con Ollama nativo en el host (GPU Metal):

| Servicio | Qué hace | Puerto (solo 127.0.0.1) | Auth |
|---|---|---|---|
| `router-api` | Jev como servicio de decisión (`POST /v1/decidir`) | 8000 | `API_TOKEN` |
| `a2a-divisas` | Agente A2A; usa el MCP por HTTP con su propio token | 5001 | `A2A_TOKEN` (card pública) |
| `mcp-empresa` | MCP de sistemas de negocio (streamable HTTP, DNS rebinding activo) | interno | `MCP_TOKEN` |
| `jaeger` | Trazas OpenTelemetry (sin contenido de mensajes) | 16686 | — |

```bash
ollama serve                                  # si la app de Ollama no está abierta
uv sync --locked --extra prod
uv run python scripts/generar_env.py          # .env con tokens nuevos (no se imprimen, no va a git)
docker compose up -d --build                  # imágenes fijadas por digest, contenedores sin root ni capabilities
uv run python servicios/cliente_demo.py       # decisión del router, A2A→MCP con token, y 401 sin token
open http://127.0.0.1:16686                   # trazas en Jaeger
docker compose down
```

Sin Docker (mismo código, útil para depurar): exporta los tokens de `.env` y corre
`uv run python servicios/mcp_http.py`, `uv run uvicorn --app-dir servicios a2a_divisas:app --port 5001` y
`uv run uvicorn --app-dir servicios router_api:app --port 8000` con `LLM_BASE_URL=http://localhost:11434/v1`.
Probado así en Windows: 401 sin token en los tres, 421 con Host falso en el MCP, A2A→MCP → 937.5 soles.

## Setup en Windows (equipo original)

```powershell
uv sync --locked
ollama pull qwen3:4b-instruct
```

| Variable       | Default                      | Prod (ejemplo)                    |
|----------------|------------------------------|-----------------------------------|
| `LLM_BASE_URL` | `http://localhost:11434/v1`  | `http://vllm.interno:8000/v1`     |
| `LLM_MODEL`    | `qwen3:4b-instruct`          | `Qwen/Qwen3-32B`                  |
| `LLM_API_KEY`  | `ollama`                     | secreto del gateway               |
| `A2A_URL`      | `http://localhost:5001/`     | URL pública del agente            |

Modelos: `qwen3:4b-instruct` (rápido, default) · `qwen3:8b` (mejor razonamiento, ~2x más lento).
Evita `qwen3:4b` (variante *thinking-only*: razona siempre, ~5x más lento en CPU).

## Labs

| # | Patrón | Comando | Tiempo CPU |
|---|--------|---------|-----------|
| 01 | Agente + tools | `uv run python labs/01_agent_tools.py` | ~10 s |
| 02 | Secuencial + concurrente (fan-out) | `uv run python labs/02_sequential_concurrent.py` | ~80 s |
| 03 | Handoff (triage → especialistas) | `uv run python labs/03_handoff.py` | ~45 s |
| 04 | Servidor A2A (Agent Card + JSON-RPC) | `uv run uvicorn --app-dir labs 04_a2a_server:app --port 5001` | — |
| 05 | Orquestador → agente remoto vía A2A | `uv run python labs/05_a2a_orchestrator.py` (con 04 corriendo) | ~40 s |
| 06 | Group chat: selector round-robin vs director LLM | `uv run python labs/06_group_chat.py` | ~5 min (A ~100 s, B ~190 s) |
| 07 | Magentic-One: manager planifica, delega, replanifica | `uv run python labs/07_magentic.py` | ~18 min ⚠️ |
| 08 | Servidor MCP `empresa` (sistemas de negocio, stdio) | lo lanza el lab 09 como subproceso | — |
| 09 | Agentes comparten MCP con mínimo privilegio + `ExigeTool` | `uv run python labs/09_mcp_agents.py` | ~45 s |
| 10 | Router Jev (System 1) + especialistas (System 2) + cola humana | `uv run python labs/10_router_jev.py` | ~1 min |
| 11 | Aprobación humana reanudable: revisión de ruteo + aprobación de reembolsos, checkpoints sellados | `uv run python labs/11_hitl_router.py iniciar` → `revisar` → `responder <id> '<json>'` (o `supervisor-demo`) | ~1 min + humano |

Agent Card: http://localhost:5001/.well-known/agent-card.json

Tests deterministas (sin LLM): `uv run python labs/test_divisas.py` · `uv run python labs/test_orquestacion.py` ·
`uv run python labs/test_mcp.py` (protocolo MCP real) · `uv run python labs/test_router.py` · `uv run python labs/test_hitl.py` ·
`uv run python labs/test_escenarios_hitl.py` · `uv run python servicios/test_escenarios.py`

Datos de negocio: fuente única en `labs/empresa.py` (la usan el servidor MCP y los labs 04/07).

## Lecciones ya encontradas

- **LLM pequeño + aritmética = alucinación.** El agente `divisas` dijo 250 USD ≈ 39,000 PEN. Fix: tool
  determinista `convertir` (ver `openspec/specs/divisas`). Regla: datos y cálculos, siempre en tools.
- **Handoff en malla hace ping-pong** con modelos chicos. Usa estrella (`add_handoff(triage, [...])`),
  `turn_limits` y `termination_condition`.
- **Group chat rompe backends estrictos**: el historial compartido trae varios `assistant` seguidos y
  Ollama responde 400 "Cannot have 2 or more assistant messages at the end of the list". Fix:
  `otros_como_user` en `common.py` envía los mensajes de otros agentes como `user` `[autor]: texto`.
- **Condiciones de término frágiles**: el modelo escribe `**Veredicto:**`, no `VEREDICTO:`. Normaliza
  (mayúsculas, sin markdown) y deja siempre `max_rounds` como red de seguridad.
- **Modelos híbridos (qwen3:8b) razonan por defecto**: `default_options={"reasoning_effort": "none"}`
  baja de ~100 s a ~5 s por llamada en CPU.
- **Estructura en código, contenido en el LLM.** Un 4B no respeta reglas de estado en el prompt
  ("si ya hablaste, cierra") y el director LLM de group chat devolvía `terminate=true` en la ronda 0.
  El selector fija el orden y la condición de término decide el final; el LLM solo aporta contenido.
  También deriva de rol (el "optimista" abrió con "No"): refuerza la postura en el prompt.
- **Debate adversarial fabrica evidencia.** Con roles fijos, los agentes inventan estadísticas y fuentes
  ("30 % según Gartner", "CO₂ de 1000 autos") para ganar. En prod: darles datos vía tools/MCP/RAG y un
  verificador; el prompt "no inventes" no basta en modelos chicos.
- **Magentic es el patrón más caro**: ~5 llamadas largas del manager por tarea. En esta CPU ~18 min
  (4B) / ~20 min (8B), mismo resultado correcto. Úsalo para tareas abiertas multi-paso; si el flujo es
  conocido, secuencial/handoff cuesta 10–20x menos. Para iterar sobre él, apunta `LLM_BASE_URL` a GPU/cloud.
- **Restringir tools no restringe al modelo.** El `analista` no tenía `convertir` y aun así convirtió
  en texto con una tasa inventada; `finanzas` copió esa cifra en vez de usar su tool. Los agentes
  confían en lo que dice el agente anterior.
- **Ollama ignora `tool_choice`** (auto/required/función: mismo resultado, medido). La obligación va en
  código: middleware `ExigeTool` en `common.py` verifica el `function_call` y reintenta.
- **Router Jev (lab 10)**: Jev decide en ~1.3 s (mediana) con confianza calibrada y el código rutea;
  el especialista tarda ~8 s. De 8 mensajes: 5 auto (todos correctos), 3 a humano: "cancel my order"
  (ORDER 0.52 vs CANCEL: la frontera ambigua conocida), uno ambiguo, y el prompt injection. Jev le dio
  ACCOUNT 0.97 al ataque: **sin el detector habría llegado a un agente**. Defensa en profundidad: salida
  acotada de Jev + detector + agentes sin tools sensibles + humano.
- **La anonimización tiene costo**: el especialista respondió "envíe el detalle a [EMAIL]". En prod,
  guarda el mapa marcador → valor fuera del modelo y rehidrata la respuesta en código, o instruye al
  agente a no repetir marcadores.
- **HITL reanudable (lab 11)**: `request_info` pausa el workflow, el checkpoint queda en disco y otro
  proceso lo reanuda con la decisión humana (probado: iniciar → revisar → responder en 3 procesos).
- **Los checkpoints del framework llevan pickle** (restringido) incluso si solo pasas dicts: se sellan con
  HMAC-SHA256 (clave en `~/.ia-local/hitl.key`, fuera del repo) y un sello nunca se reescribe. Probado:
  un byte alterado → "sello inválido, no se reanuda", sin ejecutar nada.
- **El LLM propone, el humano aprueba, el código ejecuta**: `emitir_reembolso` tiene
  `approval_mode="always_require"`; el framework no lo ejecuta, devuelve los argumentos exactos para
  aprobar; tras aprobar, el código lo ejecuta con esos argumentos y aplica política (S/ 900 → rechazado).
- **Un prompt puede inducir la fuga que intentas evitar**: decir "si ves [EMAIL_1], úsalo" hizo que el
  modelo inventara "[EMAIL_1]" en un caso sin PII. Fix: no mencionar marcadores + `limpiar_marcadores`
  como última barrera. PII solo en una bóveda por caso, borrada al entregar (verificado: 0 apariciones
  del email en checkpoints, cola, correcciones).
- **Sellar por glob legitima lo ajeno; firmar el checkpoint no firma lo que ve el humano.** Revisión del
  2026-09-30 (`openspec/changes/endurecer-hitl`): un checkpoint plantado quedaba sellado en la siguiente
  corrida, la cola sin firma mostraba S/ 45 mientras se pagaban S/ 450, una caída tras pagar permitía pagar
  dos veces, y un zero-width o un salto de línea evadía el detector de prompt injection. Fix: se sella cada
  checkpoint al guardarlo, la cola va firmada, el reembolso es idempotente y el detector normaliza el texto.
- `agent-framework-ollama` (beta) falla en handoff (`allow_multiple_tool_calls`); por eso se usa el
  endpoint OpenAI-compatible de Ollama.

## Roadmap

1. ~~Agente+tools, secuencial, concurrente, handoff, A2A~~ ✅
2. ~~Group chat / Magentic~~ ✅
3. ~~MCP server como tool compartido entre agentes~~ ✅
3b. ~~Proyecto "Jev local": decisiones tipadas con probabilidad calibrada~~ ✅ (ver `jev/README.md`)
4. ~~Human-in-the-loop (aprobación de tools) + checkpointing~~ ✅ (lab 11)
5. ~~Producción: Docker Compose, auth entre servicios, OpenTelemetry → Jaeger~~ ✅ (`servicios/`, validado en la MacBook)
6. CI/CD para trunk-based development (gate único local = CI, stack en CI, despliegue local) y evals con umbrales

## Auditoría zero trust de alternativas open source a Jev (2026-09-28, solo remota)

Método: metadatos y búsquedas del lado del servidor (GitHub API/code search, PyPI Integrity, OSV, HF API).
Ningún código de terceros se ejecutó ni quedó en disco.

| | Kev (jaredpalmer) | AnyJev ("nokia-applied-research") |
|---|---|---|
| Identidad | ✅ cuenta 2013, 10.6k seguidores | 🚩 org creada 2026-08-03, no verificada, 2 contribuidores |
| Commits firmados | ✅ 30/30 | 🚩 0/30 |
| PyPI | 🚩 `kev` en PyPI es OTRO paquete (2016): instalar solo desde git + commit fijo | ✅ attestation PEP 740 desde el repo |
| Deserialización | ⚠️ `head.pt` (pickle) con `torch.load` sin `weights_only` (mitigado por torch>=2.6) | ✅ heads en JSON |
| CPU/Ollama | ❌ torch+transformers | ❌ HF/vLLM (`allowed_token_ids`) |

Veredicto: ninguno listo para la empresa hoy (repos de <2 semanas, sin OpenSSF Scorecard). Siguiente paso
si se quiere adoptar uno: prueba en sandbox desechable sin red (nivel 2), nunca en equipos de trabajo.

## Licencia

Código bajo [MIT](LICENSE). Los datasets de `data/` mantienen sus propias licencias (CDLA-Sharing-1.0 y
CC BY-NC 4.0, solo uso no comercial): ver [data/LICENCIAS.md](data/LICENCIAS.md).
