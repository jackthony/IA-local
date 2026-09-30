# repo Specification

## Purpose
TBD - created by archiving change repo-github. Update Purpose after archive.
## Requirements
### Requirement: Escáner de secretos antes de publicar
`buscar_secretos(texto)` SHALL devolver las categorías encontradas entre: `github_token`
(`ghp_`, `gho_`, `ghs_`, `ghu_`, `github_pat_` seguidos de 20+ caracteres), `openai_key` (`sk-` + 20+),
`aws_key` (`AKIA` + 16 mayúsculas/dígitos), `slack_token` (`xox[baprs]-`), `clave_privada`
(`-----BEGIN ... PRIVATE KEY-----`) y `correo_corporativo` (dominio `acity.com.pe` precedido de arroba;
el patrón se arma por concatenación para que ni el escáner ni esta spec lo contengan). `escanear_secretos.py`
SHALL recorrer los archivos que git publicaría y salir con código 1 si hay hallazgos.

#### Scenario: Token de GitHub
- **WHEN** `buscar_secretos("token=" + "gh" + "p_" + "a" * 36)`
- **THEN** contiene `github_token`

#### Scenario: Clave privada y correo corporativo
- **WHEN** el texto contiene una cabecera de clave privada RSA y un correo del dominio corporativo
- **THEN** contiene `clave_privada` y `correo_corporativo`

#### Scenario: Texto limpio
- **WHEN** `buscar_secretos("api_key = os.getenv('LLM_API_KEY', 'ollama')")`
- **THEN** devuelve lista vacía

### Requirement: Nada sensible en el repo
El repo SHALL versionar los datasets públicos descargados (Bitext y tickets de Kaggle) junto con su
manifiesto SHA-256 y `data/LICENCIAS.md` (atribución y términos), para usarlos en clases sin descargar.
`.gitignore` SHALL seguir excluyendo `.env` (cada entorno genera sus tokens con `scripts/generar_env.py`),
`.venv/`, el estado de ejecución (`data/hitl/`, `data/correcciones.jsonl`, `data/router-log.jsonl`),
`*.bak`, `__pycache__/` y `.DS_Store`.

#### Scenario: Qué se publica
- **WHEN** se consulta `git check-ignore` para el CSV de Bitext, `.env`, `data/hitl/pendientes.json` y `data/correcciones.jsonl`
- **THEN** el CSV NO está ignorado; `.env` y los dos archivos de estado sí

### Requirement: CI verificable
El workflow SHALL correr en push y pull request con `permissions: contents: read`, Actions fijadas por
SHA de commit, `uv sync --locked`, el escáner de secretos y todas las suites deterministas.

#### Scenario: Push al repo
- **WHEN** se hace push a `main`
- **THEN** el workflow pasa (secretos: ninguno; tests: ok)

