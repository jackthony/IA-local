## MODIFIED Requirements

### Requirement: Checkpoints sellados
`sellar(directorio, checkpoint_id, clave)` SHALL guardar en `SELLOS.hmac` (no `.json`: el framework intenta
leer todo `*.json` del directorio como checkpoint) el HMAC-SHA256 de UN checkpoint que este proceso acaba de
escribir; nunca SHALL sellar por glob (un archivo plantado quedaría legitimado) y un sello existente nunca se
reescribe. `verificar_checkpoint(directorio, checkpoint_id, clave)` SHALL lanzar `ValueError` si el archivo no
tiene sello o si su contenido no coincide. `AlmacenSellado(directorio, clave)` SHALL sellar en cada `save`,
verificar en cada `load` antes de deserializar, y listar (`get_latest`) solo checkpoints con sello válido.

#### Scenario: Íntegro
- **WHEN** se sella un checkpoint y se verifica sin cambios
- **THEN** no lanza error

#### Scenario: Manipulado
- **WHEN** se modifica un byte del checkpoint tras sellar, y se vuelve a llamar `sellar` con su id
- **THEN** `verificar_checkpoint` lanza `ValueError` que menciona `sello`

#### Scenario: Plantado
- **WHEN** un tercero escribe un checkpoint con fecha futura en el directorio y luego el almacén guarda otros
- **THEN** el plantado no tiene sello, `get_latest` no lo devuelve y `load` lanza `ValueError`

## ADDED Requirements

### Requirement: Cola humana firmada
Cada entrada de `data/hitl/pendientes.json` SHALL llevar un HMAC (`firmar_entrada`) sobre sus datos y su
`request_id`. `verificar_entrada` SHALL lanzar `ValueError` si la entrada fue editada, no tiene firma o se
presenta con otro `request_id`; `revisar` SHALL omitir (con aviso) y `responder` SHALL rechazar esas entradas:
lo que el supervisor ve es lo que se ejecuta.

#### Scenario: Monto editado en la cola
- **WHEN** se cambia `argumentos.monto` de una entrada firmada
- **THEN** `verificar_entrada` lanza `ValueError` que menciona `sello`

### Requirement: Reembolso idempotente
`ejecutar_reembolso(operacion, monto, motivo)` SHALL registrar `operacion` (caso + id de la tool call) en el
ledger y, si ya existe, SHALL devolver "ya emitido" sin volver a pagar. La tool que ve el LLM
(`emitir_reembolso`, `approval_mode="always_require"`) SHALL no pagar nunca por sí misma.

#### Scenario: Reintento tras una caída
- **WHEN** se ejecuta dos veces la misma `operacion`
- **THEN** el ledger tiene una sola línea para ella y la segunda llamada devuelve "ya emitido"
