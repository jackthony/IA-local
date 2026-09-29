## 1. Tests
- [x] 1.1 test_empresa.py: anonimizar_con_mapa y rehidratar (fallaron antes)
- [x] 1.2 labs/test_hitl.py: sellar/verificar (íntegro, manipulado+re-sellado, sin sello), acuerdo, validar_reembolso, limpiar_marcadores

## 2. Implementación
- [x] 2.1 anonimizar_con_mapa / rehidratar en jev/evaluar_empresa.py
- [x] 2.2 sellar / verificar_checkpoint / acuerdo / validar_reembolso / limpiar_marcadores
- [x] 2.3 Workflow: Entrada (Jev + revisión) -> Especialista (aprobación de reembolso)
- [x] 2.4 Cola persistente + bóveda PII + CLI iniciar|revisar|responder|supervisor-demo

## 3. Verificación
- [x] 3.1 3 procesos: iniciar (1 auto, 4 a cola) -> revisar -> supervisor-demo (ORDER, S/50 emitido, S/900 bloqueado, ataque descartado)
- [x] 3.2 Email ausente en data/, bóveda vacía; checkpoint manipulado rechazado sin ejecutar nada
- [x] 3.3 README (lab 11 + lecciones)
