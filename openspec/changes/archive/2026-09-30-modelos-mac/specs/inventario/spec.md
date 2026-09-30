## ADDED Requirements

### Requirement: Rol por modelo y manifiesto válido
Cada entrada de `modelos` en `modelos.json` SHALL tener `nombre`, `digest` (64 hex), `bytes` > 0,
`obligatorio` (booleano) y `rol` no vacío; los nombres y digests SHALL ser únicos. `validar_manifiesto(doc)`
SHALL devolver la lista de errores (vacía si es válido) y el inventario SHALL mostrar el rol de cada modelo.
Los opcionales ausentes se reportan `falta` sin que el inventario falle.

#### Scenario: Manifiesto del repo
- **WHEN** se valida el `modelos.json` versionado
- **THEN** no hay errores e incluye los roles router, agentes, manager, código y embeddings

#### Scenario: Entrada inválida
- **WHEN** un modelo tiene digest de 10 caracteres y otro repite nombre
- **THEN** `validar_manifiesto` devuelve un error por cada problema
