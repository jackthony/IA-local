## Decisiones

- **stdio** para el lab: el agente lanza el servidor como subproceso; cero puertos. En prod el mismo
  servidor corre con transporte streamable HTTP detrás de auth (cambio de 1 línea en `mcp.run`).
- **Mínimo privilegio por agente** con `allowed_tools` del lado cliente. Nota: no es control de
  seguridad del servidor; en prod el servidor MCP debe autorizar por identidad (OAuth) también.
- **Fuente única** `empresa.py`: los tests de negocio se prueban ahí; el test MCP prueba el contrato
  del protocolo (descubrimiento de tools + llamada), que es lo que consumen los agentes.
