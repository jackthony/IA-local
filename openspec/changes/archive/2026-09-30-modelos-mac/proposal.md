## Why

La MacBook M5 Pro del usuario tiene memoria de sobra para modelos grandes. En lugar de "candidatos",
el manifiesto debe declarar el set por rol (router, agentes, manager, código, embeddings) para que el
inventario verifique en la Mac exactamente esos modelos por digest.

## What Changes

- `modelos.json`: `qwen3:30b-a3b` (agentes), `gpt-oss:20b` y `qwen3:32b` (manager/razonamiento),
  `qwen3-coder:30b` (código) y `qwen3-embedding:0.6b` (RAG) pasan a `modelos` como opcionales con `rol`;
  digests re-consultados en el registro. `qwen3:14b` queda como candidato.
- `validar_manifiesto(doc)` y columna `Rol` en `INVENTARIO.md`.

## Impact

- Sin dependencias nuevas. En máquinas sin esos modelos el inventario los marca `falta` sin fallar (opcionales).
