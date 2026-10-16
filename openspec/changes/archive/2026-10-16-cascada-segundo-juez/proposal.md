## Why

TypeSafe iguala o supera al modelo local en exactitud pero es más lento, cuesta y recibe datos. Una cascada usa al local
siempre y al remoto solo cuando el local duda, para combinar exactitud y costo.

## What Changes

- `servicios/router_api.py`: segundo juez opcional (`JEV_SEGUNDO=typesafe`), `Cupo` por proceso (`JEV_SEGUNDO_MAX`), campo `juez`.
- `evals/evaluar.py --cascada` (medición offline con predicciones grabadas) y `fusionar_cascada`.

## Impact

Sin dependencias nuevas; apagado por defecto. Medido offline: 13 % consultas, 98.6 % exactitud, 74.0 % automatizado,
~USD 0.003 por 1,000. Falta medirlo con tráfico real.
