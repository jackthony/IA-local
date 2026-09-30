# produccion Specification

## Purpose
TBD - created by archiving change produccion. Update Purpose after archive.
## Requirements
### Requirement: Autenticación Bearer fail-closed entre servicios
`token_requerido(nombre)` SHALL leer la variable de entorno y abortar (`SystemExit`) si falta o tiene
menos de 32 caracteres. `BearerAuth(app, token, publicas)` SHALL responder 401 sin tocar la app si el
encabezado `Authorization: Bearer <token>` falta o no coincide (comparación en tiempo constante), salvo
en las rutas de `publicas`.

#### Scenario: Sin token
- **WHEN** se pide una ruta protegida sin `Authorization`
- **THEN** responde 401

#### Scenario: Token incorrecto
- **WHEN** se envía `Bearer otro-token`
- **THEN** responde 401

#### Scenario: Token correcto
- **WHEN** se envía el token configurado
- **THEN** la app responde (200)

#### Scenario: Ruta pública
- **WHEN** se pide `/salud` sin token
- **THEN** responde 200

#### Scenario: Token débil al arrancar
- **WHEN** la variable tiene 10 caracteres
- **THEN** `token_requerido` aborta con `SystemExit`

### Requirement: Router como servicio de decisión
`POST /v1/decidir` con `{"mensaje": str}` SHALL anonimizar, detectar prompt injection, pedir la decisión
a Jev y responder `{categoria, confianza, top2, destino, motivo}`. SHALL rechazar cuerpos sin `mensaje`
de tipo texto o de más de 4000 caracteres (400). `GET /salud` es público.

#### Scenario: Cuerpo inválido
- **WHEN** se envía `{"mensaje": 123}` con token válido
- **THEN** responde 400

### Requirement: Servicios endurecidos
Todos los servicios SHALL correr en contenedores con usuario no root, sistema de archivos de solo lectura,
sin capabilities, `no-new-privileges`, imágenes fijadas por digest y puertos publicados solo en
`127.0.0.1`. El servidor MCP SHALL mantener la protección contra DNS rebinding con hosts permitidos
explícitos. La telemetría SHALL exportarse sin contenido de mensajes (`enable_sensitive_data=False`).

#### Scenario: Stack en Docker
- **WHEN** se levanta `docker compose up` con `.env` generado
- **THEN** `cliente_demo.py` obtiene una decisión del router, una respuesta del agente A2A (que usa el MCP
  por HTTP con su token), una llamada sin token recibe 401, y las trazas aparecen en Jaeger
