# router Specification

## Purpose
TBD - created by archiving change jev-router. Update Purpose after archive.
## Requirements
### Requirement: Validación del artefacto de calibración
`cargar_calibracion(ruta)` SHALL leer el JSON y lanzar `ValueError` si falta alguna clave requerida
(`modelo`, `T`, `umbrales`, `opciones`, `pregunta`, `rotulo`), si `opciones` está vacía o si el umbral
a 5 % no está en [0, 1.01].

#### Scenario: Falta clave
- **WHEN** el JSON no tiene `umbrales`
- **THEN** lanza `ValueError` que menciona `umbrales`

### Requirement: Ruteo decidido en código
`decidir_ruta(categoria, confianza, umbral, especialistas, sospechoso=False)` SHALL devolver, en este
orden de prioridad: `("humano", "posible prompt injection")` si `sospechoso`; `("humano", "confianza baja")`
si `confianza < umbral`; `("humano", "sin especialista")` si la categoría no está mapeada; y
`(especialista, "auto")` en otro caso. `sospechoso` viene del detector de la ingesta: aunque la salida de
Jev está acotada, el agente especialista sí leería el texto hostil.

#### Scenario: Mensaje sospechoso
- **WHEN** `decidir_ruta("REFUND", 0.99, 0.70, {"REFUND": "pagos"}, sospechoso=True)`
- **THEN** devuelve `("humano", "posible prompt injection")`

#### Scenario: Confianza alta
- **WHEN** `decidir_ruta("REFUND", 0.93, 0.70, {"REFUND": "pagos"})`
- **THEN** devuelve `("pagos", "auto")`

#### Scenario: Confianza baja
- **WHEN** `decidir_ruta("REFUND", 0.55, 0.70, {"REFUND": "pagos"})`
- **THEN** devuelve `("humano", "confianza baja")`

#### Scenario: Categoría sin especialista
- **WHEN** `decidir_ruta("OTRA", 0.99, 0.70, {"REFUND": "pagos"})`
- **THEN** devuelve `("humano", "sin especialista")`

### Requirement: Log de auditoría anonimizado
`registro(mensaje, categoria, confianza, top2, destino, motivo, ms)` SHALL devolver un dict con el
mensaje anonimizado (sin PII), la decisión, la confianza redondeada a 3 decimales, las 2 categorías más
probables, destino, motivo, latencia y marca de tiempo ISO.

#### Scenario: PII fuera del log
- **WHEN** el mensaje contiene `ana@acme.pe`
- **THEN** el registro contiene `[EMAIL]` y no contiene `ana@acme.pe`

### Requirement: Demo de router
`labs/10_router_jev.py` SHALL procesar mensajes claros, ambiguos, uno en español y uno con prompt
injection; imprimir por mensaje categoría, confianza, destino y respuesta del especialista (o cola
humana con top-2), y la latencia de Jev vs la del especialista.

#### Scenario: Mensaje hostil
- **WHEN** el mensaje pide ignorar instrucciones y otorgar acceso de administrador
- **THEN** Jev solo devuelve una categoría del dominio, el detector lo marca y va a cola humana sin
  llegar a ningún agente

