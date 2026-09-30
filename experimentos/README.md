# Experimentos de la sesión (cómo se descubrió cada decisión)

Scripts de exploración que precedieron al código definitivo. Se conservan para enseñar el método:
**pregunta → experimento mínimo → dato medido → decisión en spec (OpenSpec) → código → test**.
Ejecutar desde la raíz del repo con Ollama activo (salvo los que dicen "sin LLM").

| Script | Pregunta | Hallazgo medido | Adónde llevó |
|---|---|---|---|
| `exp_nombres.py` | ¿Puntuar etiquetas A/B/C/D o el nombre de la opción? ¿Importa el prompt? | Letras + encuadre "Estado/Pregunta": 16/20. Nombres + prompt natural: **19/20**, ECE 0.075. Temperatura por token cambiaba el argmax (19→17) | `jev.distribucion` puntúa prefijos del nombre y aplica T sobre la masa agregada |
| `exp_prompts.py` | ¿Cuánto pesa la redacción del prompt? | Misma tarea, mismo modelo: **31/40 → 37/40** solo cambiando la plantilla | `jev.prompt`: instrucción + lista + rótulo; "el prompt es un hiperparámetro" |
| `nb_uniforme.py` (sin LLM) | ¿El 24 % en Kaggle es culpa del modelo o de las etiquetas? | Naive Bayes con 9.5k ejemplos: 41.9 % vs 28 % de la clase mayoritaria; 36 asuntos idénticos con colas distintas | Diagnóstico: etiquetas ruidosas → se buscó Bitext (etiquetas limpias) |
| `proto_hitl.py iniciar` / `reanudar` (sin LLM) | ¿`request_info` + checkpoint permiten pausar y reanudar en OTRO proceso? | Sí, mismo `request_id`; pero el checkpoint lleva **pickle** del framework aunque pases dicts | Lab 11: checkpoints sellados con HMAC |
| `proto_aprobacion.py` | ¿Qué hace el framework con un tool `approval_mode="always_require"`? | No lo ejecuta: devuelve `function_approval_request` con los argumentos exactos | Lab 11: "el LLM propone, el humano aprueba, el código ejecuta" |
