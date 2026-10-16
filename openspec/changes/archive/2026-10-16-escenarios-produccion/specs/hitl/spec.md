## ADDED Requirements

### Requirement: Escenarios de producción del lab 11
`labs/test_escenarios_hitl.py` SHALL ejecutar historias completas (mensaje -> cola humana -> decisión -> efecto) con
el workflow, los checkpoints sellados, la cola firmada, la bóveda y el ledger reales en un directorio temporal, y un
servidor falso compatible con OpenAI. SHALL cubrir: reembolso dentro de política, monto fuera de política bloqueado
aunque el supervisor apruebe, rechazo del supervisor, inyección que no llega a ningún agente, cola o checkpoint
manipulados que no se reanudan, reintento tras caída sin doble pago y PII que no se persiste.

#### Scenario: Aprobación humana no sustituye la política
- **WHEN** el supervisor aprueba un reembolso de S/ 900 (MAX_REEMBOLSO = 500)
- **THEN** el estado es "reembolso NO emitido" y el ledger queda vacío

#### Scenario: Reintento tras caída
- **WHEN** se responde dos veces la misma solicitud porque la cola no llegó a guardarse
- **THEN** el ledger tiene una sola línea y la segunda respuesta dice "ya emitido"
