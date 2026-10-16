# Comparación por perfil (generado por `evals/evaluar.py --comparar`)

Golden `golden-v2.jsonl` sha256 `b48b2bfae01a`, 77 casos.

| Métrica | ollama | deepseek | typesafe |
|---|---|---|---|
| Modelo | qwen3:4b-instruct | deepseek-chat | no ejecutado |
| Exactitud global | 100.0% | 91.2% | no ejecutado |
| Logprobs degenerados (sin distribución real) | 0% | 100% | no ejecutado |
| ECE | 0.026 | 0.008 | no ejecutado |
| % automatizado | 82.6% | 76.8% | no ejecutado |
| Críticos a automático | 0 | 0 | no ejecutado |
| Latencia mediana / p95 (ms) | 69 / 73 | 1021 / 1160 | no ejecutado |
| Tokens por decisión (ent/sal) | 210 / 1 | 214 / 1 | no ejecutado |
| Costo USD por 1,000 decisiones | 0 (local, sin contar energía) | sin precios (define PRECIO_*_USD_1M) | no ejecutado |

`no ejecutado`: sin predicciones grabadas para typesafe. Carga el perfil (perfiles/*.env.example) y corre `evals/evaluar.py --perfil <perfil> --grabar`.
