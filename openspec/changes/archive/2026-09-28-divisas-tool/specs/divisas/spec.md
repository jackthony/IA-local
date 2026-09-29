## ADDED Requirements

### Requirement: Conversión determinista de monedas
El agente `divisas` SHALL obtener toda conversión del tool `convertir(monto, de, a)`, que usa una
tabla de tasas fija expresada en PEN por unidad (USD=3.75, EUR=4.10, PEN=1.0) y redondea a 2 decimales.

#### Scenario: USD a PEN
- **WHEN** se invoca `convertir(250, "USD", "PEN")`
- **THEN** devuelve `937.5`

#### Scenario: Cruce vía PEN
- **WHEN** se invoca `convertir(100, "EUR", "USD")`
- **THEN** devuelve `109.33`

#### Scenario: Códigos insensibles a mayúsculas
- **WHEN** se invoca `convertir(10, "usd", "pen")`
- **THEN** devuelve `37.5`

#### Scenario: Moneda no soportada
- **WHEN** se invoca `convertir(10, "JPY", "PEN")`
- **THEN** lanza `ValueError` indicando la moneda no soportada
