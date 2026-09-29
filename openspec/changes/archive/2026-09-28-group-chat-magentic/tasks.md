## 1. Tests deterministas

- [x] 1.1 labs/test_orquestacion.py con escenarios de group-chat y magentic (falla antes de implementar)
- [x] 1.2 Test de `otros_como_user` (preparer de historial multi-agente)

## 2. Group chat

- [x] 2.1 `turno` y `hay_veredicto` en labs/06_group_chat.py
- [x] 2.1b `otros_como_user` en labs/common.py aplicado a cada agente
- [x] 2.2 Modo A: GroupChatBuilder con selection_func + termination + max_rounds
- [x] 2.3 Modo B: orchestrator_agent LLM elige turno
- [x] 2.4 Ejecutar ambos modos y registrar tiempos

## 3. Magentic

- [x] 3.1 Tool `ventas_por_region` en labs/07_magentic.py
- [x] 3.2 MagenticBuilder con manager qwen3:8b, límites y streaming de plan/ledger
- [x] 3.3 Ejecutar y verificar que la respuesta final cita cifras del tool

## 4. Docs

- [x] 4.1 README: labs 06/07, tiempos y lecciones
