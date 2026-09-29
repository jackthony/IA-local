## 1. Tests
- [x] 1.1 jev/test_jev.py con todos los escenarios deterministas (falla antes de implementar)

## 2. Núcleo
- [x] 2.1 Tipos Choice/Score/Noul, etiquetas y prompt
- [x] 2.2 distribucion, decidir, calibrar, ece, brier, ruta
- [x] 2.3 Jev.preguntar / Jev.lote (openai SDK, logprobs) + cascada

## 3. Demo y datos
- [x] 3.1 jev/tickets.json (calibración + evaluación)
- [x] 3.2 jev/demo_triage.py con métricas
- [x] 3.3 Ejecutar demo y registrar resultados

## 4. Seguridad y docs
- [x] 4.1 `uv add openai` explícito; `jev/auditar_deps.py` (uv.lock -> OSV) con test; hallazgos documentados
- [x] 4.2 jev/README.md (uso, resultados, seguridad)
