## ADDED Requirements

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
