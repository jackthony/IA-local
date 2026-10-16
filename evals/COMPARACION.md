# Comparación por perfil (generado por `evals/evaluar.py --comparar`)

Golden `golden-v2.jsonl` sha256 `b48b2bfae01a`, 77 casos.

| Métrica | ollama | deepseek |
|---|---|---|
| Modelo | qwen3:4b-instruct | deepseek-chat |
| Exactitud global | 100.0% | 91.2% |
| Logprobs degenerados (sin distribución real) | 0% | 100% |
| ECE | 0.026 | 0.008 |
| % automatizado | 82.6% | 76.8% |
| Críticos a automático | 0 | 0 |
| Latencia mediana / p95 (ms) | 69 / 73 | 1021 / 1160 |
| Tokens por decisión (ent/sal) | 210 / 1 | 214 / 1 |
| Costo USD por 1,000 decisiones | 0 (local, sin contar energía) | sin precios (define PRECIO_*_USD_1M) |
