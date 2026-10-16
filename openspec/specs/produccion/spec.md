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

### Requirement: El router falla cerrado si el modelo no decide
Si el servidor de modelos falla (caída, error HTTP, plazo vencido de `JEV_TIMEOUT_S`) o responde sin logprobs,
`POST /v1/decidir` SHALL responder 503 con `{"error": "modelo no disponible", "destino": "humano", "motivo":
"jev no disponible"}` y registrar el motivo en el span. SHALL NOT rutear sin una decisión de Jev ni responder 500.
`GET /salud` SHALL seguir respondiendo 200 (la salud del proceso no depende del modelo).

#### Scenario: Modelo caído
- **WHEN** el servidor de modelos responde 500
- **THEN** el router responde 503 con destino `humano`

#### Scenario: Modelo lento
- **WHEN** el modelo tarda más que `JEV_TIMEOUT_S`
- **THEN** el router responde 503 dentro del plazo, no cuando el modelo termine

#### Scenario: Respuesta sin logprobs
- **WHEN** el modelo responde 200 sin `top_logprobs`
- **THEN** el router responde 503 con destino `humano`

### Requirement: Escenarios de producción del router
`servicios/test_escenarios.py` SHALL ejercer el servicio ASGI completo contra un servidor falso compatible con
OpenAI que repite las predicciones grabadas del golden set, y con `--vivo` contra `LLM_BASE_URL`. SHALL cubrir cada
caso de ruteo del golden (destino HTTP igual al esperado salvo las limitaciones conocidas, exactas), que ningún
crítico esperado en humano salga a un especialista, el motivo de humano (inyección, riesgo legal), que la PII no
llegue al modelo ni a la respuesta, que una petición sin token no toque al modelo y que el span no lleve contenido.

#### Scenario: Regresión de seguridad
- **WHEN** se desactiva el detector de inyección o la anonimización en el servicio
- **THEN** al menos un escenario falla
