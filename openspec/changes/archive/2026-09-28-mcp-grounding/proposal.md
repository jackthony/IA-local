## Why

Cada lab define sus propios tools (`convertir` en 04, `ventas_por_region` en 07): datos duplicados y
acoplados a un agente. En la empresa, los sistemas (ventas, tipo de cambio) deben exponerse UNA vez y
consumirse por cualquier agente con permisos acotados. MCP es el estándar para eso. Además, dar datos
reales vía tools es la mitigación a la fabricación de cifras vista en el lab 06.

## What Changes

- `labs/empresa.py`: fuente única de datos/funciones de negocio (`convertir`, `ventas_por_region`);
  04 y 07 la importan (sin cambio de comportamiento).
- `labs/08_mcp_server.py`: servidor MCP `empresa` (stdio) que expone ambos tools.
- `labs/09_mcp_agents.py`: dos agentes comparten el servidor con mínimo privilegio
  (`allowed_tools`): `analista` solo ve ventas, `finanzas` solo ve conversión; flujo secuencial.
- `labs/test_mcp.py`: test determinista por protocolo MCP real (sin LLM).

## Impact

- labs/empresa.py (nuevo), labs/04_a2a_server.py, labs/07_magentic.py, tests existentes (import).
- Nueva dependencia: `mcp` (SDK oficial modelcontextprotocol/python-sdk).
