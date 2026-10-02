# hitl Specification

## Purpose
TBD - created by archiving change router-hitl. Update Purpose after archive.
## Requirements
### Requirement: Anonimización reversible
`anonimizar_con_mapa(texto)` SHALL devolver `(texto_anon, mapa)` con marcadores numerados por tipo
(`[EMAIL_1]`, `[EMAIL_2]`, `[DNI_1]`…) y `mapa` marcador -> valor original. `rehidratar(texto, mapa)`
SHALL reemplazar solo marcadores exactos presentes en el mapa.

#### Scenario: Dos emails
- **WHEN** `anonimizar_con_mapa("de ana@acme.pe para luis@x.pe")`
- **THEN** devuelve `("de [EMAIL_1] para [EMAIL_2]", {"[EMAIL_1]": "ana@acme.pe", "[EMAIL_2]": "luis@x.pe"})`

#### Scenario: Ida y vuelta
- **WHEN** se rehidrata el texto anonimizado con su mapa
- **THEN** se obtiene el texto original

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

### Requirement: Revisión humana de ruteo reanudable
Si `decidir_ruta` devuelve `humano`, el workflow SHALL pedir revisión con `request_info` enviando solo
datos anonimizados (caso, mensaje anonimizado, top-2, motivo), guardar checkpoint sellado y registrar
la solicitud en `data/hitl/pendientes.json`. La respuesta `{"categoria": X}` SHALL continuar el caso con
esa categoría; `{"descartar": true}` SHALL cerrarlo. Cada decisión SHALL agregarse a
`data/correcciones.jsonl` con categoría y confianza de Jev y categoría humana.

#### Scenario: Caso dudoso
- **WHEN** "I want to cancel my order" llega con confianza bajo el umbral
- **THEN** queda pendiente en la cola; al responder `{"categoria": "ORDER"}` desde otro proceso, el caso lo
  atiende el especialista de pedidos y la corrección queda registrada

### Requirement: Aprobación de acciones sensibles
`emitir_reembolso` SHALL registrarse con `approval_mode="always_require"`. Si el especialista propone
llamarlo, el workflow SHALL pedir aprobación mostrando tool y argumentos exactos. Con `{"aprobado": true}`
el código SHALL ejecutar el tool con esos argumentos; con `{"aprobado": false}` SHALL no ejecutarse.

Aun aprobado, `validar_reembolso(argumentos)` SHALL rechazar en código montos no numéricos, ≤ 0 o
> `MAX_REEMBOLSO` (500): los argumentos los propone un LLM y son entrada no confiable. Solo
`aprobado` estrictamente `true` (booleano) cuenta como aprobación.

#### Scenario: Reembolso rechazado
- **WHEN** el supervisor responde `{"aprobado": false}`
- **THEN** el reembolso no se ejecuta y el caso cierra con mensaje de rechazo

#### Scenario: Política en código
- **WHEN** `validar_reembolso({"monto": 900, "motivo": "x"})` y `validar_reembolso({"monto": -5, "motivo": "x"})`
- **THEN** ambos devuelven `(False, motivo)`; `validar_reembolso({"monto": 50, "motivo": "x"})` devuelve `(True, "")`

### Requirement: Marcadores sin resolver no llegan al cliente
`limpiar_marcadores(texto)` SHALL reemplazar cualquier marcador (`[EMAIL_n]`, `[DNI_n]`…) que quede tras
rehidratar por `(dato no disponible)` y devolver cuántos reemplazó. Medido: un especialista inventó
"contact us at [EMAIL_1]" en un caso sin PII porque el prompt mencionaba el marcador; el prompt ya no los
menciona y el código es la última barrera.

#### Scenario: Marcador inventado
- **WHEN** `limpiar_marcadores("escríbanos a [EMAIL_1] hoy")`
- **THEN** devuelve `("escríbanos a (dato no disponible) hoy", 1)`

### Requirement: PII fuera de checkpoints y logs
El mapa de PII SHALL guardarse solo en `data/hitl/boveda/<caso>.json` y borrarse al entregar la
respuesta final rehidratada.

#### Scenario: Demo con email
- **WHEN** termina la demo con un mensaje que contiene un email
- **THEN** el email no aparece en checkpoints, pendientes ni correcciones, y la bóveda del caso ya no existe

### Requirement: Acuerdo Jev-humano
`acuerdo(correcciones)` SHALL devolver la fracción de revisiones donde la categoría humana coincide con la
de Jev, excluyendo las descartadas (`DESCARTADO` no es una categoría, p. ej. prompt injection); `None`
si no quedan revisiones.

#### Scenario: Acuerdo parcial
- **WHEN** 3 correcciones y 2 coinciden
- **THEN** devuelve `2/3`

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
