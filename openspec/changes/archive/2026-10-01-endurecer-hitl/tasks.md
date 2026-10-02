## 1. Tests (fallaron antes)
- [x] 1.1 jev/test_datos.py: evasiones de `hallazgos` (zero-width, salto de línea, espacios múltiples, "earlier")
- [x] 1.2 labs/test_router.py: `es_sospechoso`
- [x] 1.3 labs/test_hitl.py: sellar uno a la vez (plantado sin sello), `AlmacenSellado` (plantado con fecha
  futura invisible para `get_latest` y rechazado en `load`), cola firmada, reembolso idempotente, la tool no paga

## 2. Implementación
- [x] 2.1 `normalizar` + patrón en jev/ingesta.py; `es_sospechoso` en lab 10, lab 11 y router_api
- [x] 2.2 `AlmacenSellado`, `firmar_entrada` / `verificar_entrada`, `ejecutar_reembolso` idempotente

## 3. Verificación
- [x] 3.1 Suite determinista completa + escáner de secretos
- [x] 3.2 Lab 11 extremo a extremo contra un LLM falso OpenAI-compatible: cola editada rechazada en `revisar` y
  `responder`; checkpoint plantado nunca sellado; caída simulada tras pagar -> "ya emitido antes", 1 línea en el
  ledger; supervisor-demo (ORDER, S/ 900 bloqueado, ataque descartado); email ausente en data/
- [x] 3.3 Sin falsos positivos nuevos en los datasets versionados (Bitext 13 -> 13, tickets 0 -> 0)
- [x] 3.4 Labs 10 y 11 con Ollama real en la MacBook (Metal): Jev mediana 76 ms; injection -> humano; lab 11 iniciar -> revisar -> supervisor-demo (S/ 50 emitido, S/ 900 bloqueado por política, ataque descartado); ningún correo en data/
