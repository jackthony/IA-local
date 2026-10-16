# Comparación por perfil (generado por `evals/evaluar.py --comparar`)

Golden `golden-v2.jsonl` sha256 `b48b2bfae01a`, 77 casos.

| Métrica | ollama | deepseek | typesafe |
|---|---|---|---|
| Modelo | qwen3:4b-instruct | deepseek-chat | jev-1.13.0 |
| Exactitud global | 100.0% | 91.2% | 100.0% |
| Logprobs degenerados (sin distribución real) | 0% | 100% | 0% |
| ECE | 0.026 | 0.008 | 0.002 |
| % automatizado | 82.6% | 76.8% | 85.5% |
| Críticos a automático | 0 | 0 | 0 |
| Latencia mediana / p95 (ms) | 69 / 73 | 1021 / 1160 | 342 / 445 |
| Tokens por decisión (ent/sal) | 210 / 1 | 214 / 1 | 544 / 111 |
| Costo USD por 1,000 decisiones | 0 (local, sin contar energía) | sin precios (define PRECIO_*_USD_1M) | sin precios (define PRECIO_*_USD_1M) |
