# Datasets incluidos: procedencia y licencias

Ambos se descargaron con `jev/ingesta.py` (zero trust): URL fijada a commit, SHA-256 verificado en
memoria antes de escribir. Verifica en cualquier momento: `uv run python -c "import sys; sys.path.insert(0,'jev'); import ingesta; print(len(ingesta.cargar('bitext')))"`
(re-verifica el hash contra `MANIFEST-<fuente>.json`).

## Bitext — Customer Support LLM Chatbot Training Dataset

- Archivo: `Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv`
- Fuente: https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset (commit `430d1a8`)
- Autor: Bitext Innovations — https://www.bitext.com
- Licencia: **CDLA-Sharing-1.0** (Community Data License Agreement – Sharing). Permite usar, modificar y
  redistribuir, incluso comercialmente; los datos redistribuidos o derivados deben compartirse bajo la
  misma licencia e incluir este aviso. Texto: https://cdla.dev/sharing-1-0/

## Customer IT Support – Ticket Dataset (Tobias Bueck)

- Archivo: `dataset-tickets-multi-lang-4-20k.csv`
- Fuente: https://huggingface.co/datasets/Tobi-Bueck/customer-support-tickets (commit `ddf1c81`),
  espejo del autor de https://www.kaggle.com/datasets/tobiasbueck/multilingual-customer-support-tickets
- Autor: Tobias Bück
- Licencia: **CC BY-NC 4.0** — atribución obligatoria y **solo uso no comercial** (apto para clases y
  aprendizaje; no para producción ni productos). Texto: https://creativecommons.org/licenses/by-nc/4.0/
- Nota: sintético con etiquetas ruidosas (ver `jev/README.md`); útil para enseñar diagnóstico, no para medir valor.
