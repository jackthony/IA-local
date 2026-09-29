## Why

Muchas decisiones empresariales (clasificar tickets, enrutar intenciones, puntuar urgencia) no
necesitan un LLM generando texto: necesitan un "if inteligente" rápido, tipado y con confianza
confiable para decidir cuándo actuar solo, cuándo escalar y cuándo pedir un humano. Es la idea del
modelo "Jev" (TypeSafe AI, orquestado por Eigent). Se construye una versión propia sobre modelos
locales, sin clonar proyectos open source de terceros (riesgo de supply chain / malware).

## What Changes

- `jev/jev.py`: primitivas tipadas `Choice`, `Score`, `Noul`; `Jev.preguntar` y `Jev.lote`
  (preguntas en paralelo) con probabilidades desde logprobs del modelo (1 token, salida válida por
  construcción); calibración por temperature scaling; métricas ECE/Brier; ruteo por confianza con
  cascada modelo chico -> modelo grande -> humano.
- `jev/tickets.json`: dataset etiquetado de tickets de soporte (calibración + evaluación).
- `jev/demo_triage.py`: triage de tickets (área, urgencia, molestia) con reporte de exactitud,
  calibración antes/después, latencia y distribución auto/escalar/humano.
- `jev/test_jev.py`: tests deterministas de las funciones puras (sin LLM).
- Auditoría de dependencias (`uvx pip-audit`) documentada.

## Impact

- Nuevo directorio `jev/`. Dependencia directa `openai` (SDK oficial; ya estaba en el lock como
  transitiva). Sin repos de terceros.
