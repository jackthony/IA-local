## ADDED Requirements

### Requirement: Servidor MCP de sistemas de empresa
El servidor MCP `empresa` SHALL exponer por stdio exactamente los tools `ventas_por_region` y
`convertir`, delegando en `labs/empresa.py` (fuente única).

#### Scenario: Descubrimiento de tools
- **WHEN** un cliente MCP lista los tools del servidor
- **THEN** obtiene exactamente `{"ventas_por_region", "convertir"}`

#### Scenario: Llamada a conversión
- **WHEN** un cliente MCP llama `convertir` con `{"monto": 250, "de": "USD", "a": "PEN"}`
- **THEN** el resultado es `937.5`

#### Scenario: Llamada a ventas
- **WHEN** un cliente MCP llama `ventas_por_region` sin argumentos
- **THEN** el total Q3 del resultado es `564000`

### Requirement: Mínimo privilegio por agente
Cada agente SHALL ver solo los tools MCP de su rol vía `allowed_tools`.

#### Scenario: Finanzas no ve ventas
- **WHEN** se conecta un `MCPStdioTool` con `allowed_tools=["convertir"]`
- **THEN** sus funciones disponibles son exactamente `["convertir"]`

### Requirement: Agentes comparten el servidor
El lab 09 SHALL ejecutar `analista` (ventas) y luego `finanzas` (conversión) sobre el mismo servidor
MCP, y la respuesta final SHALL expresar las ventas Q3 de Lima (345000 PEN) en USD (92000.0).

#### Scenario: Flujo compartido
- **WHEN** se ejecuta `labs/09_mcp_agents.py`
- **THEN** la salida de `finanzas` contiene `92000` (345000 / 3.75)

### Requirement: Uso de tool exigido en código
Un agente cuyo rol exige un tool SHALL llevar el middleware `ExigeTool(nombre, intentos=2)`: si la
respuesta no contiene un `function_call` a `nombre`, reintenta añadiendo la instrucción de usarlo.
Motivo medido: Ollama ignora `tool_choice` (auto/required/función) y `finanzas` copió una conversión
inventada por otro agente en 1 de 2 corridas.

#### Scenario: Respuesta con la tool exigida
- **WHEN** `llamo_tool(respuesta, "convertir")` y la respuesta contiene un `function_call` `convertir`
- **THEN** devuelve `True`

#### Scenario: Respuesta solo texto
- **WHEN** la respuesta solo contiene texto
- **THEN** `llamo_tool` devuelve `False`

#### Scenario: Otra tool
- **WHEN** la respuesta contiene un `function_call` a `ventas_por_region`
- **THEN** `llamo_tool(respuesta, "convertir")` devuelve `False`
