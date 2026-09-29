## Why

El usuario quiere el proyecto en GitHub (repo privado `jackthony/IA-local`) para clonarlo en su
MacBook. Publicar exige zero trust sobre lo que sale: sin datasets ni datos de revisión humana, sin
secretos, sin correo corporativo en el historial, y CI que verifique cada push.

## What Changes

- `.gitignore` estricto: fuera `.venv/`, `data/` (salvo artefactos de calibración y manifiestos de
  procedencia, sin PII), `data/hitl/`, logs, `.env`, respaldos.
- `scripts/escanear_secretos.py` (stdlib): bloquea tokens (GitHub, OpenAI, AWS, Slack), claves privadas,
  `.env` con valores y el correo corporativo en los archivos a publicar. Se ejecuta antes del push y en CI.
- `.github/workflows/tests.yml`: permisos mínimos, Actions fijadas por SHA, `uv sync --locked`,
  escáner de secretos y tests deterministas (sin LLM).
- Identidad de commits solo en este repo: `43307950+jackthony@users.noreply.github.com`.
- README: guía rápida para macOS (Apple Silicon usa GPU Metal en Ollama).

## Impact

- Nuevo repo git local + remoto privado. Sin dependencias nuevas.
