## Why

Jev existe como servicio alojado (TypeSafe, `POST /v1/systemone`) y el proyecto solo tenía la versión local. Medirlo con el
mismo golden permite decidir con datos si el servicio sustituye o complementa al modelo local.

## What Changes

- `jev/typesafe.py`: cliente mínimo (`httpx`) con `solicitud`, `leer_respuesta` (valida) y `TypeSafeJev` (backoff 429/529).
- `evals/evaluar.py`: perfil `typesafe`; las predicciones guardan `probabilidades` (sin logprobs) y la huella de frescura
  usa el cuerpo de la solicitud en lugar del prompt local.
- `perfiles/typesafe.env.example`; `evals/test_typesafe.py` (servicio falso, sin clave) en CI.

## Impact

Sin dependencias nuevas. La grabación contra el servicio real la ejecuta el usuario con su clave (nunca en el chat ni en git);
hasta entonces la columna queda "no ejecutado". El umbral local se aplica sin recalibrar (ver DECISIONES §7).
