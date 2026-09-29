## ADDED Requirements

### Requirement: Selector determinista con estructura fija
El group chat SHALL poder elegir el siguiente orador con `turno(state)`: durante las primeras
`RONDAS_DEBATE=4` rondas alterna entre los participantes salvo el último (round-robin); desde la
ronda 4 devuelve el último participante (el moderador, que emite el veredicto). La estructura del
debate vive en código, no en el prompt (medido: qwen3:4b no respeta "si ya hablaste, cierra").

#### Scenario: Primera ronda
- **WHEN** `current_round=0` y participantes `[optimista, esceptico, moderador]`
- **THEN** `turno` devuelve `"optimista"`

#### Scenario: Réplica
- **WHEN** `current_round=3` con los mismos participantes
- **THEN** `turno` devuelve `"esceptico"`

#### Scenario: Cierre
- **WHEN** `current_round=4` con los mismos participantes
- **THEN** `turno` devuelve `"moderador"`

### Requirement: Director LLM sin poder de término
En modo orquestador LLM, el director SHALL elegir solo el siguiente orador; el término lo decide
`hay_veredicto` (código). Medido: qwen3:4b como director devolvía `terminate=true` en la ronda 0.

#### Scenario: Debate dirigido por LLM
- **WHEN** se ejecuta el modo B
- **THEN** al menos un participante habla antes del cierre y el debate termina con veredicto del moderador

### Requirement: Término por veredicto
El group chat SHALL terminar cuando `hay_veredicto(msgs)` sea verdadero: algún mensaje con
`author_name == "moderador"` contiene `VEREDICTO:` sin distinguir mayúsculas e ignorando `*`
(los modelos suelen formatear en markdown).

#### Scenario: Moderador emite veredicto
- **WHEN** la conversación incluye un mensaje de `moderador` con texto `"VEREDICTO: adoptar"`
- **THEN** `hay_veredicto` devuelve `True`

#### Scenario: Veredicto con markdown
- **WHEN** el `moderador` escribe `"**Veredicto:** adoptar por fases"`
- **THEN** `hay_veredicto` devuelve `True`

#### Scenario: Otro agente menciona veredicto
- **WHEN** solo `optimista` escribe `"VEREDICTO: sí"`
- **THEN** `hay_veredicto` devuelve `False`

### Requirement: Historial multi-agente compatible con backends estrictos
Cada agente SHALL enviar los mensajes `assistant` de OTROS agentes (texto, sin tool calls) como rol
`user` con prefijo `[autor]: `, porque backends como Ollama/llama.cpp rechazan 2+ mensajes
`assistant` consecutivos al final ("Cannot have 2 or more assistant messages at the end of the list").

#### Scenario: Mensaje de otro agente
- **WHEN** el agente `esceptico` prepara un mensaje assistant de `optimista` con texto `"hola"`
- **THEN** se envía `{"role": "user", "content": "[optimista]: hola"}`

#### Scenario: Mensaje propio
- **WHEN** el agente `esceptico` prepara su propio mensaje assistant
- **THEN** se envía sin cambios con rol `assistant`

#### Scenario: Tool calls intactos
- **WHEN** un mensaje de otro agente contiene `tool_calls`
- **THEN** se envía sin cambios
