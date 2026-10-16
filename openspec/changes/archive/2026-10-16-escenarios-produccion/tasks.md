## 1. Tests (fallaron antes)
- [x] 1.1 servicios/test_escenarios.py: caso de modelo caído -> 500 (rojo), luego 503 con destino humano
- [x] 1.2 evals/test_evals.py: divergencia nueva, limitación resuelta, cambio de destino y limitación sin impacto
- [x] 1.3 labs/test_escenarios_hitl.py: 8 historias del lab 11 con workflow, checkpoints y ledger reales

## 2. Implementación
- [x] 2.1 router_api: `consultar_jev`, `JevNoDisponible`, 503, `JEV_TIMEOUT_S`; `Jev(timeout, reintentos)`
- [x] 2.2 evals: `exactitud_destino`, `divergencias_destino`, `contrastar_limitaciones`, `limitaciones-v2.json`
- [x] 2.3 evals/llm_falso.py compartido; `ingresar()` extraído en el lab 11
- [x] 2.4 CI: ambos archivos de escenarios en el paso de tests

## 3. Verificación
- [x] 3.1 Mutaciones (cada una debe fallar): detector de inyección apagado, sin anonimizar, umbral permisivo
  (servicio); política de monto, idempotencia, firma de la cola y bóveda de PII (lab 11)
- [x] 3.2 `test_escenarios.py --vivo` contra Ollama real (qwen3:4b-instruct): 69 escenarios con las mismas 5
  limitaciones conocidas, sin deriva respecto de las predicciones grabadas
- [x] 3.3 Suite determinista completa + escáner de secretos + puerta de evals
