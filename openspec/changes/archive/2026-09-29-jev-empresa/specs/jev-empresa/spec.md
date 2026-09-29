## ADDED Requirements

### Requirement: Anonimización de PII antes del modelo
`anonimizar(texto)` SHALL reemplazar emails por `[EMAIL]`, tarjetas de 13 a 19 dígitos que pasan Luhn
por `[TARJETA]`, RUC (11 dígitos que empiezan con 10, 15, 16, 17 o 20) por `[RUC]`, celulares
peruanos (9 dígitos que empiezan con 9, con o sin +51) por `[TELEFONO]` y DNI (8 dígitos aislados)
por `[DNI]`, en ese orden de prioridad.

#### Scenario: Email y celular
- **WHEN** `anonimizar("Escríbanme a juan.perez@acme.pe o al +51 987654321")`
- **THEN** devuelve `"Escríbanme a [EMAIL] o al [TELEFONO]"`

#### Scenario: DNI y RUC
- **WHEN** `anonimizar("DNI 45678912, RUC 20123456789")`
- **THEN** devuelve `"DNI [DNI], RUC [RUC]"`

#### Scenario: Tarjeta válida por Luhn
- **WHEN** `anonimizar("pagué con 4111 1111 1111 1111")`
- **THEN** devuelve `"pagué con [TARJETA]"`

#### Scenario: Número que no es PII
- **WHEN** `anonimizar("pedido 1234 por S/ 250")`
- **THEN** devuelve el texto sin cambios

### Requirement: Los datos de la empresa no salen de la máquina
`es_local(url)` SHALL ser verdadero solo para hosts `localhost`, `127.0.0.1`, `::1` o que terminan en
`.localhost`. `evaluar_empresa.py` SHALL abortar si `LLM_BASE_URL` no es local, salvo `--permitir-remoto`.

#### Scenario: Local
- **WHEN** `es_local("http://localhost:11434/v1")` y `es_local("http://127.0.0.1:8000/v1")`
- **THEN** ambos son `True`

#### Scenario: Remoto
- **WHEN** `es_local("https://api.openai.com/v1")` y `es_local("http://localhost.evil.com/v1")`
- **THEN** ambos son `False`

### Requirement: Artefacto de calibración
`evaluar_empresa.py` SHALL guardar `data/calibracion-<nombre>.json` con modelo, T, umbrales a 5 % y
10 %, opciones, descripciones, pregunta, rótulo, tamaños de calibración/evaluación, exactitud en
evaluación, fecha y SHA-256 del CSV de origen.

#### Scenario: Corrida con sustituto
- **WHEN** se ejecuta con el CSV verificado de Bitext (`--texto instruction --area category`)
- **THEN** imprime métricas (NB, Jev, automatización 5/10 %) y escribe el artefacto con esos campos
