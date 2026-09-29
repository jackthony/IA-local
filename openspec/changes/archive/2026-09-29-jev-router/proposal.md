## Why

En el lab 03 el ruteo lo hacía un agente LLM de triage (~45 s por caso, sin confianza, con ping-pong).
Jev ya demostró en Bitext 94-95 % de exactitud con confianza calibrada. Patrón de producción: System 1
(Jev decide rápido y dice cuándo duda) + System 2 (agentes especialistas contestan) + humano para lo dudoso.
Sin tickets reales aún, se usa la calibración de Bitext (`data/calibracion-bitext-demo.json`).

## What Changes

- `labs/10_router_jev.py`: carga el artefacto de calibración, decide la categoría con Jev, rutea en
  código a 4 especialistas o a cola humana, registra cada decisión anonimizada en `data/router-log.jsonl`.
- Demo con mensajes nuevos: claros, ambiguos, uno en español y uno hostil (prompt injection).
- `labs/test_router.py`: tests deterministas de ruteo, validación del artefacto y log anonimizado.

## Impact

- Reutiliza `jev/jev.py` y `jev/evaluar_empresa.anonimizar`. Sin dependencias nuevas.
