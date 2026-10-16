# Comparación por perfil (generado por `evals/evaluar.py --comparar`)

Golden `golden-v3.jsonl` sha256 `ea84dcfaeb11`, 85 casos.

| Métrica | ollama | deepseek | typesafe |
|---|---|---|---|
| Modelo | qwen3:4b-instruct | no ejecutado | no ejecutado |
| Exactitud global | 95.7% | no ejecutado | no ejecutado |
| Logprobs degenerados (sin distribución real) | 0% | no ejecutado | no ejecutado |
| ECE | 0.036 | no ejecutado | no ejecutado |
| % automatizado | 67.5% | no ejecutado | no ejecutado |
| Críticos a automático | 0 | no ejecutado | no ejecutado |
| Latencia mediana / p95 (ms) | 70 / 72 | no ejecutado | no ejecutado |
| Tokens por decisión (ent/sal) | 239 / 1 | no ejecutado | no ejecutado |
| Costo USD por 1,000 decisiones | 0 (local, sin contar energía) | no ejecutado | no ejecutado |

`no ejecutado`: sin predicciones grabadas para deepseek, typesafe. Carga el perfil (perfiles/*.env.example) y corre `evals/evaluar.py --perfil <perfil> --grabar`.
