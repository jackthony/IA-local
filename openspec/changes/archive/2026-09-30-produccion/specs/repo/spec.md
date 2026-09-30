## MODIFIED Requirements

### Requirement: Nada sensible en el repo
El repo SHALL versionar los datasets públicos descargados (Bitext y tickets de Kaggle) junto con su
manifiesto SHA-256 y `data/LICENCIAS.md` (atribución y términos), para usarlos en clases sin descargar.
`.gitignore` SHALL seguir excluyendo `.env` (cada entorno genera sus tokens con `scripts/generar_env.py`),
`.venv/`, el estado de ejecución (`data/hitl/`, `data/correcciones.jsonl`, `data/router-log.jsonl`),
`*.bak`, `__pycache__/` y `.DS_Store`.

#### Scenario: Qué se publica
- **WHEN** se consulta `git check-ignore` para el CSV de Bitext, `.env`, `data/hitl/pendientes.json` y `data/correcciones.jsonl`
- **THEN** el CSV NO está ignorado; `.env` y los dos archivos de estado sí
