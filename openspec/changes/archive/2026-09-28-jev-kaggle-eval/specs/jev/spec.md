## ADDED Requirements

### Requirement: Descripciones de opciones
`Choice(opciones, descripciones=None)` SHALL aceptar una descripción por opción (misma longitud, o
`ValueError`). Con descripciones, `prompt` SHALL listar cada opción en su propia línea como
`- <opción>: <descripción>`; la puntuación sigue siendo por el nombre de la opción.

#### Scenario: Prompt con descripciones
- **WHEN** `prompt("x", "Classify the ticket into one of these queues", Choice(("IT Support", "Billing"), ("Internal IT, laptops", "Invoices, refunds")))`
- **THEN** el mensaje contiene `- IT Support: Internal IT, laptops` y `- Billing: Invoices, refunds`

#### Scenario: Longitud distinta
- **WHEN** `Choice(("A", "B"), ("solo una",))`
- **THEN** lanza `ValueError`
