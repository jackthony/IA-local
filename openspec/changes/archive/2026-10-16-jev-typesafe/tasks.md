## 1. Tests
- [x] 1.1 evals/test_typesafe.py: solicitud, auth, reintentos 429/529, 401 sin filtrar nada, respuesta inválida, sin clave
- [x] 1.2 Grabación y evaluación completas contra el servicio falso (70 llamadas, sin PII, clave ausente de lo guardado)

## 2. Implementación
- [x] 2.1 jev/typesafe.py; perfil `typesafe` en evals/evaluar.py; perfiles/typesafe.env.example; CI

## 3. Verificación
- [x] 3.1 Suite determinista + puerta de evals sin cambios para Ollama
- [ ] 3.2 Grabación contra el servicio real (la corre el usuario con su clave)
