## ADDED Requirements

### Requirement: Clase residual OTRO
El catálogo del router SHALL incluir la clase `OTRO` (saludos, charla, fuera de tema, ininteligible, consulta vaga) sin
especialista, de modo que `decidir_ruta` la envíe a humano con motivo "sin especialista". Su calibración SHALL usar mensajes
fuera de dominio distintos de los del golden set.

#### Scenario: Saludo
- **WHEN** el mensaje es "hello"
- **THEN** el destino es `humano`
