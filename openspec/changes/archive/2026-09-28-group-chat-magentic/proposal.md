## Why

Faltan en el lab los dos patrones de orquestación "con director": group chat (conversación
multi-agente con selección de turno) y Magentic-One (manager que planifica, delega y replanifica).
Son la base de casos empresariales como comités de revisión y análisis multi-paso.

## What Changes

- `labs/06_group_chat.py`: debate optimista/escéptico/moderador en dos modos:
  (A) selector determinista round-robin (función pura), (B) orquestador LLM que elige el turno.
  Termina cuando el moderador emite `VEREDICTO:` o al llegar a `max_rounds`.
- `labs/07_magentic.py`: manager Magentic (qwen3:8b, `reasoning_effort=none`) con participantes
  `analista` (tool `ventas_por_region`, datos fijos) y `redactor`. Límites: rondas, stalls, resets.
  Muestra el plan (task ledger) y cada progress ledger por streaming.
- Tests deterministas sin LLM: selector, condición de término y tool de ventas.

## Impact

- labs/06_group_chat.py, labs/07_magentic.py, labs/test_orquestacion.py, README.md
- ponytail: datos de ventas estáticos; en prod el tool consulta el DWH/API real.
