# Comparación por perfil (generado por `evals/evaluar.py --comparar`)

Golden `golden-v1.jsonl` sha256 `72ccc257ab5e`, 77 casos.

| Métrica | ollama | azure |
|---|---|---|
| Modelo | qwen3:4b-instruct | no ejecutado |
| Exactitud global | 100.0% | no ejecutado |
| ECE | 0.026 | no ejecutado |
| % automatizado | 82.6% | no ejecutado |
| Críticos a automático | 1 | no ejecutado |
| Latencia mediana / p95 (ms) | 69 / 73 | no ejecutado |
| Tokens por decisión (ent/sal) | 210 / 1 | no ejecutado |
| Costo USD por 1,000 decisiones | 0 (local, sin contar energía) | no ejecutado |

`no ejecutado`: sin predicciones grabadas para azure. Carga el perfil (perfiles/*.env.example) y corre `evals/evaluar.py --perfil <perfil> --grabar`.
