# jev-typesafe Specification

## Purpose
Usar el Jev alojado de TypeSafe como backend medible con el mismo golden set.
## Requirements

### Requirement: Cliente del Jev alojado
`jev/typesafe.py` SHALL enviar `POST {url}` con `state`, `model` y una pregunta `choice` cuyo `criteria` sean las opciones
y sus descripciones, con `Authorization: Bearer` tomado de `TYPESAFE_API_KEY` (aborta si falta). SHALL usar las
`probabilities` de la respuesta, validar que sus claves sean opciones conocidas y sumen 1, y reintentar solo 429 y 529
con backoff exponencial. Los errores SHALL NOT incluir la clave ni el cuerpo de la respuesta.

#### Scenario: Error de autenticación
- **WHEN** el servicio responde 401
- **THEN** se lanza `TypeSafeError` sin reintentar y el mensaje no contiene la clave ni el estado enviado

#### Scenario: Sobrecarga transitoria
- **WHEN** el servicio responde 429 y 529 antes de 200
- **THEN** la decisión se obtiene tras tres solicitudes

### Requirement: Perfil typesafe en la evaluación
`evaluar.py --perfil typesafe --grabar` SHALL anonimizar cada mensaje antes de enviarlo, guardar las probabilidades por caso
con sus tokens de uso, respetar los topes de `Presupuesto` y registrar la grabación en `reportes/uso.jsonl`.

#### Scenario: Grabación completa
- **WHEN** se graban los 69 casos contra el servicio
- **THEN** se hacen 70 llamadas, ninguna lleva un correo y las predicciones pasan la verificación de frescura
