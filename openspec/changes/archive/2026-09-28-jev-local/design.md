## Decisiones

- **Logprobs de 1 token en vez de JSON**: se puntúa el primer token del NOMBRE de cada opción
  (prefijo inequívoco; Noul = Sí/No; Score = dígitos 1..9). Etiquetas A..Z se descartaron: medido
  16/20 vs 19/20. Se pide `max_tokens=1, logprobs, top_logprobs=20`. Ventajas: salida
  siempre dentro del dominio (se toma la masa de probabilidad solo de etiquetas válidas), latencia
  ~1-2 s en CPU, y una distribución real en vez de una "confianza" verbalizada por el LLM.
  ponytail: máximo 26 opciones (Jev admite 255); ampliar con etiquetas de 2 caracteres si hace falta.
- **Sin masa válida -> distribución uniforme**: nunca excepción estructural; confianza = 1/n, que cae
  bajo el umbral humano. Esto cumple "cero errores estructurales" y degrada a revisión humana.
- **Temperature scaling** (Guo et al. 2017): p_i ∝ exp(logprob_i / T). T se ajusta por búsqueda en
  grilla minimizando NLL sobre ejemplos etiquetados. Medido: el modelo instruct da p≈1.0 aun cuando
  duda (gaps de ~30 en logprob), por lo que la calibración es obligatoria.
- **Score** = valor esperado Σ nivel·p (decimal entre niveles, como Jev). Confianza = max p.
- **Noul** = Choice binaria (A=Sí, B=No); valor = P(Sí).
- **Cascada**: confianza ≥ `auto` -> actuar; si no, reintentar con modelo grande; si sigue bajo
  -> humano. Umbrales por defecto 0.9 / 0.6, ajustables con el dataset.
- **Paralelismo**: `lote` lanza todas las preguntas con `asyncio.gather`; Ollama en CPU las serializa
  (OLLAMA_NUM_PARALLEL), en GPU/vLLM corren en paralelo real.
- **Independiente de labs/**: usa el SDK `openai` directo (mismo contrato LLM_BASE_URL/LLM_MODEL),
  así se puede extraer como paquete sin arrastrar el framework de agentes.
- **`Jev(extra=...)`** se envía como `extra_body` (p. ej. `{"reasoning_effort": "none"}` para qwen3:8b,
  que si no emite `<think>` como primer token). Medido en labs: sin esto ~100 s/llamada en CPU.
- **Auditoría de dependencias sin herramientas nuevas (zero trust)**: `jev/auditar_deps.py` lee
  `uv.lock` con `tomllib` (stdlib) y consulta la API de OSV (incluye la base de paquetes maliciosos
  de OpenSSF). No se descarga ni ejecuta `pip-audit`.
- **Temperatura sobre masa agregada** (no por token): escalar por token favorecía opciones con más
  variantes tokenizadas y cambiaba el argmax (19 -> 17/20 medido).
- ponytail: opciones que son prefijo una de otra ("cuenta"/"cuentas") pierden masa en tokens ambiguos;
  si aparece, volver a etiquetas cortas únicas para ese Choice.
