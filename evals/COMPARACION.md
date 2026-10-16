# Comparación por perfil (generado por `evals/evaluar.py --comparar`)

Golden `golden-v3.jsonl` sha256 `ea84dcfaeb11`, 85 casos.

| Métrica | ollama | deepseek | typesafe |
|---|---|---|---|
| Modelo | qwen3:4b-instruct | no ejecutado | jev-1.13.0 |
| Exactitud global | 95.7% | no ejecutado | 100.0% |
| Logprobs degenerados (sin distribución real) | 0% | no ejecutado | 0% |
| ECE | 0.036 | no ejecutado | 0.004 |
| % automatizado | 67.5% | no ejecutado | 72.7% |
| Críticos a automático | 0 | no ejecutado | 0 |
| Latencia mediana / p95 (ms) | 70 / 72 | no ejecutado | 342 / 379 |
| Tokens por decisión (ent/sal) | 239 / 1 | no ejecutado | 579 / 119 |
| Costo USD por 1,000 decisiones | 0 (local, sin contar energía) | no ejecutado | sin precios (define PRECIO_*_USD_1M) |

`no ejecutado`: sin predicciones grabadas para deepseek. Carga el perfil (perfiles/*.env.example) y corre `evals/evaluar.py --perfil <perfil> --grabar`.
