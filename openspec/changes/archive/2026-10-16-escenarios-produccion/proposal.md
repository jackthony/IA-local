## Why

El golden set (`evals/`) mide al router con logprobs grabados, pero no recorre el camino que usa un cliente real. Al
convertir sus casos en escenarios de producción de extremo a extremo (HTTP -> auth -> PII -> Jev -> ruteo) aparecieron:

1. **El servicio caía con 500 si el modelo fallaba** (caído, lento, o con respuesta sin logprobs). Sin Jev no hay
   decisión: lo correcto es fallar cerrado hacia una persona, no un 500 opaco ni rutear a ciegas.
2. **Sin plazo para el modelo.** El cliente OpenAI espera 10 min y reintenta 2 veces por defecto: un modelo colgado
   retiene la petición ~30 min.
3. **La puerta de evals no veía divergencias de destino no críticas.** 5 de 69 casos terminan en un destino distinto
   al esperado (2 conservadores a humano; 3 fuera de dominio que salen a un especialista, dos con confianza 0.97:
   el 4B es sobreconfiado fuera de dominio y la temperatura no lo corrige). Nada lo registraba ni lo vigilaba.

## What Changes

- `servicios/router_api.py`: `consultar_jev` traduce fallos del modelo (`OpenAIError`, respuesta sin logprobs) en
  `JevNoDisponible`; el endpoint responde **503** `{error, destino: "humano", motivo: "jev no disponible"}`. Plazo por
  `JEV_TIMEOUT_S` (10 s) y sin reintentos ocultos.
- `jev/jev.py`: `Jev(timeout=, reintentos=)` opcionales (por defecto, el comportamiento del cliente OpenAI).
- `evals/`: `exactitud_destino` y `divergencias_destino` en el reporte; `golden/limitaciones-v2-ollama.json` registra cada
  divergencia aceptada con su impacto y la puerta actúa como **trinquete**: una divergencia nueva o cambiada falla, y
  una resuelta obliga a retirarla del archivo. `llm_falso.py`: servidor falso compatible con OpenAI.
- `servicios/test_escenarios.py` (69 escenarios del golden + propiedades de producción; `--vivo` contra el modelo real)
  y `labs/test_escenarios_hitl.py` (8 historias completas del lab 11). `labs/11_hitl_router.py`: `ingresar()` extraído
  de `iniciar()` para poder manejar el flujo desde pruebas.

## Impact

- Sin dependencias nuevas. Clientes de `/v1/decidir` deben tratar 503 como "enviar a humano" (el cuerpo lo dice).
- No se añadió ninguna regla específica por mensaje: las 3 divergencias fuera de dominio quedan como limitación
  conocida. Mitigación no hecha: clase explícita fuera-de-dominio calibrada con ejemplos.
