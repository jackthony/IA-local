# magentic Specification

## Purpose
TBD - created by archiving change group-chat-magentic. Update Purpose after archive.
## Requirements
### Requirement: Datos de ventas por tool determinista
El analista SHALL obtener cifras solo del tool `ventas_por_region()`, que devuelve por región
ventas Q2, Q3 y crecimiento % (1 decimal), más un total, a partir de datos fijos:
norte 120000→138000, sur 90000→81000, lima 300000→345000.

#### Scenario: Crecimiento por región
- **WHEN** se invoca `ventas_por_region()`
- **THEN** lima tiene crecimiento `15.0`, sur `-10.0` y norte `15.0`

#### Scenario: Total consolidado
- **WHEN** se invoca `ventas_por_region()`
- **THEN** el total tiene Q3 `564000` y crecimiento `10.6`

### Requirement: Orquestación Magentic acotada
El workflow Magentic SHALL usar un manager (modelo por `MANAGER_MODEL`, default `LLM_MODEL`, con
`reasoning_effort=none`) con plan y progress ledger y límites
`max_round_count=8`, `max_stall_count=2`, `max_reset_count=1`, y entregar una respuesta final.

#### Scenario: Resumen ejecutivo
- **WHEN** se pide un resumen ejecutivo de ventas Q3 con recomendación
- **THEN** el manager publica un plan, delega en `analista` y `redactor`, y la respuesta final cita cifras del tool

