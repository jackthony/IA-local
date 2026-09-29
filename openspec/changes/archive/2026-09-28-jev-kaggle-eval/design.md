## Decisiones

- **Fuente**: `huggingface.co/datasets/Tobi-Bueck/customer-support-tickets` commit `ddf1c81…`, archivo
  `dataset-tickets-multi-lang-4-20k.csv` (18.8 MB, único con ES). Mismo autor que Kaggle; HF no requiere
  credenciales (Kaggle sí, y no se manejan tokens del usuario). URL fijada al commit, no a `main`.
- **Verificar antes de escribir**: los bytes viven en memoria hasta que tamaño ≤ 25 MB y SHA-256 ==
  `9be3bf81…0635` (hash LFS publicado). Si no, se aborta sin tocar disco.
- **Sin librería `datasets`**: puede ejecutar scripts de carga del repo. Solo `urllib` + `csv`.
- **Escaneo de contenido**: fórmulas (celdas que empiezan con `= + - @` o tab/CR, OWASP CSV injection)
  se reportan (riesgo si alguien abre el CSV en Excel); marcadores de prompt injection y Unicode
  bidi/zero-width se reportan. No se modifica el dataset: se documenta.
- **Jev es estructuralmente resistente a prompt injection**: su salida es 1 token mapeado a una opción
  cerrada; un ticket hostil puede, como mucho, sesgar la clasificación, nunca ejecutar acciones.
- **Muestra estratificada determinista** (semilla fija) para que las cifras sean reproducibles.
- **Cuerpo truncado a 1200 caracteres**: acota latencia en CPU; se documenta.
