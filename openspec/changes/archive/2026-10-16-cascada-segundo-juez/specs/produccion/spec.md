## ADDED Requirements

### Requirement: Segundo juez opcional del router
Con `JEV_SEGUNDO=typesafe`, `POST /v1/decidir` SHALL consultar al Jev alojado solo cuando el ruteo local sería "confianza baja",
con el mensaje anonimizado y el mismo umbral, y SHALL NOT consultarlo para prompt injection ni riesgo legal. SHALL limitar las
consultas por proceso a `JEV_SEGUNDO_MAX` y, si el servicio falla o el cupo se agota, conservar la decisión local. La
respuesta SHALL incluir `juez` (`local` o `typesafe`).

#### Scenario: Duda del local
- **WHEN** el modelo local da "confianza baja" y el segundo juez responde con confianza suficiente
- **THEN** el destino sale del segundo juez y `juez` es `typesafe`

#### Scenario: Cupo agotado
- **WHEN** ya se usaron `JEV_SEGUNDO_MAX` consultas
- **THEN** el caso dudoso va a humano con `juez` `local` y el servicio remoto no recibe más llamadas
