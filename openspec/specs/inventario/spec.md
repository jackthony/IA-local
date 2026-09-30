# inventario Specification

## Purpose
TBD - created by archiving change inventario. Update Purpose after archive.
## Requirements
### Requirement: Manifiesto y verificación de modelos
`modelos.json` SHALL listar por modelo: `nombre`, `digest` (SHA-256 del manifiesto del registro de
Ollama, igual al digest local), `bytes`, `obligatorio` y `uso`. `comparar_modelos(esperados, locales)`
SHALL devolver por modelo esperado `ok`, `falta` o `distinto` (digest diferente: el tag cambió y hay que
re-evaluar), y listar como `no_inventariado` los modelos locales fuera del manifiesto.

#### Scenario: Estados
- **WHEN** esperados `a` (digest d1) y `b` (d2); locales `a`=d1, `b`=d9 y `c`=d3
- **THEN** devuelve `a: ok`, `b: distinto` y `no_inventariado: [c]`

#### Scenario: Falta
- **WHEN** un esperado no está en locales
- **THEN** su estado es `falta`

### Requirement: Credenciales solo por nombre y ubicación
`inventario_credenciales(env, clave_hmac)` SHALL devolver nombre, archivo, presencia y largo mínimo
cumplido para cada credencial, y NUNCA el valor.

#### Scenario: Sin valores
- **WHEN** `.env` contiene `API_TOKEN=<valor>` y se genera el inventario
- **THEN** la salida contiene `API_TOKEN` y no contiene `<valor>`

### Requirement: Rutas sin datos personales
`ruta_legible(ruta)` SHALL reemplazar el directorio home por `~` para que `INVENTARIO.md` no exponga
usuario ni estructura personal.

#### Scenario: Home
- **WHEN** `ruta_legible(Path.home() / ".ollama" / "models")`
- **THEN** devuelve `~/.ollama/models`

### Requirement: Recomendación por RAM
`recomendar(ram_gb, candidatos)` SHALL devolver, ordenados de mayor a menor `ram_min_gb`, los
candidatos de `modelos.json` cuyo `ram_min_gb` <= `ram_gb` (regla: ~1.5x el tamaño del modelo + margen
para sistema y apps; medir siempre con los scripts de evaluación antes de cambiar de modelo).

#### Scenario: Máquina de 36 GB
- **WHEN** candidatos con `ram_min_gb` 24, 36 y 48 y `ram_gb=36`
- **THEN** devuelve los de 36 y 24, en ese orden

### Requirement: Inventario reproducible
`scripts/inventario.py` SHALL escribir `INVENTARIO.md` con modelos (estado vs manifiesto y almacenes
detectados con tamaño), datasets (verificados por SHA-256), credenciales, herramientas y tamaños, y
salir con código 1 si falta o cambió un modelo obligatorio o un dataset no verifica.

#### Scenario: Máquina completa
- **WHEN** se ejecuta con los modelos del manifiesto instalados y los datasets presentes
- **THEN** escribe `INVENTARIO.md` y sale con código 0

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

