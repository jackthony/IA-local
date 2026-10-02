# repo Specification

## Purpose
TBD - created by archiving change repo-github. Update Purpose after archive.
## Requirements
### Requirement: Escáner de secretos antes de publicar
`buscar_secretos(texto, dominios=None)` SHALL devolver las categorías encontradas entre: `github_token`
(`ghp_`, `gho_`, `ghs_`, `ghu_`, `github_pat_` seguidos de 20+ caracteres), `openai_key` (`sk-` + 20+),
`aws_key` (`AKIA` + 16 mayúsculas/dígitos), `slack_token` (`xox[baprs]-`), `clave_privada`
(`-----BEGIN ... PRIVATE KEY-----`) y `correo_corporativo` (una dirección `@<dominio>` de alguno de los
dominios corporativos). Sin `dominios`, SHALL usar `dominios_corporativos()`: la variable
`IA_DOMINIOS_CORPORATIVOS` (separada por comas) o, si no existe, el archivo `~/.ia-local/dominios-corporativos`
(uno por línea; `#` comenta). Ningún dominio corporativo real SHALL estar en el repo. `escanear_secretos.py`
SHALL recorrer los archivos que git publicaría, avisar si no hay dominios configurados y salir con código 1 si
hay hallazgos.

#### Scenario: Token de GitHub
- **WHEN** `buscar_secretos("token=" + "gh" + "p_" + "a" * 36)`
- **THEN** contiene `github_token`

#### Scenario: Clave privada y correo corporativo
- **WHEN** el texto contiene una cabecera de clave privada RSA y `alguien@ejemplo-corp.pe`, con
  `dominios=["ejemplo-corp.pe"]`
- **THEN** contiene `clave_privada` y `correo_corporativo`

#### Scenario: Sin dominios configurados
- **WHEN** `buscar_secretos("alguien@ejemplo-corp.pe", dominios=[])`
- **THEN** devuelve lista vacía

#### Scenario: Configuración local
- **WHEN** `IA_DOMINIOS_CORPORATIVOS=" a.pe , b.com "`, o no existe la variable y el archivo tiene `# x`, una
  línea vacía y `c.org`
- **THEN** `dominios_corporativos` devuelve `["a.pe", "b.com"]` en el primer caso y `["c.org"]` en el segundo

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

### Requirement: Licencia del código
El repo SHALL tener `LICENSE` (MIT) en la raíz y el README SHALL aclarar que los datasets de `data/` mantienen
sus propias licencias (`data/LICENCIAS.md`: CDLA-Sharing-1.0 y CC BY-NC 4.0).

#### Scenario: Licencia presente
- **WHEN** se lee `LICENSE`
- **THEN** es el texto MIT y el README enlaza `LICENSE` y `data/LICENCIAS.md`
