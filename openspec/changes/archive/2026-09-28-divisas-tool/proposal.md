## Why

El agente A2A `divisas` (labs/04_a2a_server.py) calcula conversiones "de memoria". Con qwen3:4b
respondió que 250 USD ≈ 39,000 PEN (real ≈ 940). Un LLM pequeño no debe hacer aritmética ni
inventar tasas: la conversión debe venir de un tool determinista.

## What Changes

- Nuevo tool `convertir(monto, de, a)` con tabla de tasas fija (USD/PEN/EUR), expuesto al agente `divisas`.
- Instrucciones del agente: usar siempre el tool, nunca calcular.
- Test determinista del tool (sin LLM).

## Impact

- labs/04_a2a_server.py, labs/test_divisas.py
- ponytail: tasas estáticas; en prod reemplazar por API de tipo de cambio (BCRP/SBS) en el mismo tool.
