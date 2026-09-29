# jev Specification

## Purpose
TBD - created by archiving change jev-local. Update Purpose after archive.
## Requirements
### Requirement: Distribución sobre opciones por nombre
`distribucion(top_logprobs, opciones, T=1.0)` SHALL asignar la masa exp(logprob) de cada token a la
opción de la que es prefijo inequívoco (comparando sin espacios, en minúsculas y sin tildes), ignorar
tokens ambiguos o ajenos, y luego aplicar temperatura sobre la masa agregada: p_i ∝ masa_i^(1/T), de
modo que T nunca cambia la opción ganadora. Sin masa válida SHALL devolver distribución uniforme.
Medido: nombres + prompt natural 19/20 (ECE 0.075) vs etiquetas A-D 16/20 (ECE 0.188) con qwen3:4b.

#### Scenario: Agrega variantes y normaliza
- **WHEN** tokens `[("A",0.0),("B",-2.0),(" a",-3.0),("X",-1.0)]` y opciones `A,B,C`
- **THEN** devuelve `A≈0.8858`, `B≈0.1142`, `C=0.0`

#### Scenario: Prefijos y tildes
- **WHEN** tokens `[("fact",-0.1),(" Si",-5.0)]` y opciones `facturacion,Sí`
- **THEN** `facturacion` recibe la masa de `fact` y `Sí` la de ` Si`

#### Scenario: Sin masa válida
- **WHEN** tokens `[("X",0.0)]` y opciones `A,B,C`
- **THEN** devuelve `1/3` para cada opción

#### Scenario: Temperatura aplana
- **WHEN** tokens `[("A",0.0),("B",-2.0)]`, opciones `A,B` y `T=2`
- **THEN** `A≈0.7311` (con `T=1` sería `≈0.8808`)

#### Scenario: T no cambia el argmax
- **WHEN** tokens `[("cuenta",-0.1),("fact",-2.0),("Fact",-2.5),(" fact",-3.0)]`, opciones `facturacion,cuenta`, `T=8`
- **THEN** gana `cuenta` (igual que con `T=1`)

### Requirement: Prompt natural
`prompt(estado, pregunta, tipo, rotulo="Texto")` SHALL ser un único mensaje de usuario: la pregunta
como instrucción imperativa seguida de las opciones por nombre (o escala 1..n, o Sí/No), la regla de
responder solo con la opción, y el estado precedido por `rotulo:`. Medido sobre 40 tickets (qwen3:4b):
instrucción + lista + rótulo 37/40 (ECE 0.085); pregunta interrogativa sin rótulo 31/40 (ECE 0.165);
encuadre system + "Estado/Pregunta" 16/20. El prompt es un hiperparámetro: se elige con el dataset.

#### Scenario: Un solo mensaje de usuario con las opciones
- **WHEN** `prompt("Me cobraron doble", "Clasifica el ticket en una de estas áreas", Choice(("facturacion","tecnico")), rotulo="Ticket")`
- **THEN** devuelve 1 mensaje `role="user"` que contiene `áreas: facturacion, tecnico` y `Ticket: Me cobraron doble`

### Requirement: Decisiones tipadas
`decidir(tipo, dist)` SHALL devolver `Decision(valor, probs, confianza)` según el tipo.

#### Scenario: Choice
- **WHEN** `Choice(("facturacion","tecnico","ventas"))` y dist `{facturacion:0.7,tecnico:0.2,ventas:0.1}`
- **THEN** valor `"facturacion"`, confianza `0.7`, probs indexadas por opción

#### Scenario: Score
- **WHEN** `Score(3)` y dist `{1:0.0, 2:0.5, 3:0.5}`
- **THEN** valor `2.5`, confianza `0.5`

#### Scenario: Noul
- **WHEN** `Noul()` y dist `{Sí:0.8, No:0.2}`
- **THEN** valor `0.8`, confianza `0.8`

### Requirement: Calibración y métricas
`calibrar(ejemplos)` SHALL devolver la T de la grilla que minimiza NLL; `ece` y `brier` SHALL medir
calibración.

#### Scenario: Corrige sobreconfianza
- **WHEN** 10 ejemplos con logprobs `A:0, B:-4` y opción correcta A en 7 y B en 3
- **THEN** `calibrar` devuelve `4.0 ≤ T ≤ 5.5` (óptimo teórico ≈ 4.72)

#### Scenario: ECE de un bin
- **WHEN** confianzas `[0.9, 0.9]` y aciertos `[True, False]`
- **THEN** `ece ≈ 0.4`

#### Scenario: Brier
- **WHEN** confianzas `[1.0, 0.0]` y aciertos `[True, True]`
- **THEN** `brier = 0.5`

### Requirement: Ruteo por confianza
`ruta(confianza, auto=0.9, humano=0.6)` SHALL devolver `"auto"` si confianza ≥ auto, `"escalar"`
si ≥ humano, y `"humano"` en otro caso.

#### Scenario: Tres zonas
- **WHEN** confianzas `0.95`, `0.7`, `0.4`
- **THEN** `"auto"`, `"escalar"`, `"humano"`

### Requirement: Triage end-to-end
`jev/demo_triage.py` SHALL clasificar los tickets de evaluación con cascada 4B -> 8B -> humano y
reportar exactitud, ECE sin/con calibración, latencia media por decisión y conteo por ruta.

#### Scenario: Reporte
- **WHEN** se ejecuta la demo
- **THEN** imprime las métricas, el umbral elegido por error objetivo en calibración, el % de tráfico
  automatizado en evaluación y su exactitud (objetivo ≥ 90 %), y una comparación justa contra un LLM
  generativo instruido a responder solo el área

### Requirement: Auditoría de dependencias contra OSV
`jev/auditar_deps.py` SHALL extraer `(nombre, versión)` de cada paquete de `uv.lock` (excluyendo el
proyecto raíz) y consultar OSV en lote, reportando IDs de vulnerabilidades y paquetes maliciosos.

#### Scenario: Parseo del lock
- **WHEN** el lock contiene `[[package]] name="openai" version="3.20.0"` y el proyecto `ia-local` (source virtual)
- **THEN** `paquetes(lock)` devuelve `[("openai", "3.20.0")]`

### Requirement: Umbral de automatización por error objetivo
`umbral_auto(confianzas, aciertos, error_max=0.05)` SHALL devolver el menor umbral c (entre las
confianzas observadas) tal que las decisiones con confianza ≥ c tengan exactitud ≥ 1 - error_max; si
ninguno cumple, SHALL devolver un valor > 1 (nunca automatizar). Medido: con umbral fijo 0.9 tras
calibrar, solo 10 % del tráfico se automatizaba pese a aciertos con confianza 0.74-0.82.

#### Scenario: Elige el menor umbral seguro
- **WHEN** confianzas `[0.95, 0.9, 0.8, 0.7]`, aciertos `[T, T, T, F]`, `error_max=0.05`
- **THEN** devuelve `0.8`

#### Scenario: Ninguno cumple
- **WHEN** confianzas `[0.9]`, aciertos `[F]`
- **THEN** devuelve un valor `> 1`

### Requirement: Descripciones de opciones
`Choice(opciones, descripciones=None)` SHALL aceptar una descripción por opción (misma longitud, o
`ValueError`). Con descripciones, `prompt` SHALL listar cada opción en su propia línea como
`- <opción>: <descripción>`; la puntuación sigue siendo por el nombre de la opción.

#### Scenario: Prompt con descripciones
- **WHEN** `prompt("x", "Classify the ticket into one of these queues", Choice(("IT Support", "Billing"), ("Internal IT, laptops", "Invoices, refunds")))`
- **THEN** el mensaje contiene `- IT Support: Internal IT, laptops` y `- Billing: Invoices, refunds`

#### Scenario: Longitud distinta
- **WHEN** `Choice(("A", "B"), ("solo una",))`
- **THEN** lanza `ValueError`

