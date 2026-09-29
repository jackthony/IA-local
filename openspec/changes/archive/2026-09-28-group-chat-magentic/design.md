## Decisiones

- **Selector como función pura** `turno(state: GroupChatState) -> str`: round-robin por
  `state.current_round` sobre `state.participants`. Testeable sin LLM; el modo LLM (orchestrator_agent)
  se compara contra él para ver costo/beneficio de un director inteligente.
- **Término explícito** `hay_veredicto(msgs)`: evita depender solo de `max_rounds`.
- **Manager Magentic configurable (`MANAGER_MODEL`), default qwen3:4b-instruct**: se midieron ambos.
  8B: 1207 s; 4B: 1077 s; ambos con ledgers JSON válidos y cifras exactas del tool. El costo está en el
  patrón (prompts largos de ledger en CPU a ~2 tok/s), no en el tamaño del modelo.
  `reasoning_effort=none` es obligatorio con qwen3:8b (de ~100 s a ~5 s por llamada, medido).
- **Estructura en código, contenido en el LLM**: qwen3:4b no respetó reglas de estado en prompt
  ("si ya hablaste, cierra") ni el director LLM se abstuvo de `terminate=true`. El selector fija la
  estructura y `hay_veredicto` decide el término.
- **Historial multi-agente**: `otros_como_user` convierte mensajes de otros agentes a rol `user`
  porque Ollama rechaza 2+ `assistant` consecutivos.
- **Números vía tool** (lección de `divisas-tool`): el analista no calcula, el tool entrega crecimiento
  ya calculado.
- Límites Magentic: `max_round_count=8`, `max_stall_count=2`, `max_reset_count=1` (tope de costo).
