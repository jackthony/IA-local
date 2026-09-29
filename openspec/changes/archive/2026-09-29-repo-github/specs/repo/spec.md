## ADDED Requirements

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
`.gitignore` SHALL excluir `.venv/`, `data/**` salvo `data/calibracion-*.json` y `data/MANIFEST-*.json`,
`.env`, `*.bak`, `__pycache__/` y `.DS_Store`.

#### Scenario: Cola humana y datasets fuera
- **WHEN** se consulta `git check-ignore` para `data/hitl/pendientes.json`, `data/correcciones.jsonl` y el CSV de Bitext
- **THEN** los tres están ignorados y `data/calibracion-bitext-demo.json` no

### Requirement: CI verificable
El workflow SHALL correr en push y pull request con `permissions: contents: read`, Actions fijadas por
SHA de commit, `uv sync --locked`, el escáner de secretos y todas las suites deterministas.

#### Scenario: Push al repo
- **WHEN** se hace push a `main`
- **THEN** el workflow pasa (secretos: ninguno; tests: ok)
