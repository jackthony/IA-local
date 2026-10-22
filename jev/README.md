# Jev local — decisiones tipadas con probabilidad calibrada

Versión propia del concepto "System One" de [Jev (TypeSafe AI)](https://www.eigent.ai/es/blog/typesafe-ai-jev-system-one-models)
sobre modelos locales. En vez de generar texto, cada pregunta es tipada y devuelve **valor + probabilidades**:

```python
from jev import Jev, Choice, Score, Noul, ruta

jev = Jev(rotulo="Ticket")
d = await jev.preguntar(texto, "Clasifica el ticket en una de estas áreas", Choice(("facturacion", "tecnico", "ventas", "cuenta")))
d.valor, d.confianza           # 'facturacion', 0.97
r = await jev.lote(texto, {"area": (..., Choice(...)), "urgencia": ("Califica la urgencia del ticket.", Score(5)),
                           "molesto": ("¿El cliente está molesto?", Noul())})
```

Cómo funciona: 1 token con `logprobs`; la masa de cada token va a la opción de la que es prefijo
(sin tildes/mayúsculas). Salida siempre dentro del dominio. Calibración por temperature scaling sobre la
masa agregada (no cambia la opción ganadora). Umbral de automatización derivado de un error objetivo.

```bash
uv run python jev/test_jev.py        # tests deterministas (sin LLM)
uv run python jev/demo_triage.py     # demo de valor (~5 min en CPU)
uv run python jev/auditar_deps.py    # uv.lock -> OSV (CVEs + paquetes maliciosos)
```

## Resultados medidos (CPU laptop, 20 tickets de calibración + 20 de evaluación)

| | Exactitud | Confianza útil | Latencia |
|---|---|---|---|
| LLM generativo (4B, "responde solo el área") | 19/20 | no | 0.85 s |
| Jev 4B | 17/20 | sí, ECE 0.088 calibrado (0.135 crudo) | **0.48 s** |
| Jev cascada 4B→8B→humano, error objetivo 5 % | **12/13 en automático (92 %)** | 65 % del tráfico automatizado, 35 % a humano | — |

Lecciones:
- **El prompt es un hiperparámetro.** Misma tarea, mismo modelo: 31/40 → 37/40 solo cambiando la redacción
  (instrucción + lista de opciones + rótulo "Ticket:"). Elegirlo midiendo con el dataset, nunca a ojo.
- **Etiquetas A/B/C/D empeoran** a modelos chicos (16/20 vs 19/20): puntuar el nombre de la opción.
- **Calibrar es obligatorio**: sin calibrar el modelo reporta ~0.99 de confianza acertando 85 %.
- **Umbral fijo (0.9) no sirve**: derivarlo del error tolerado (`umbral_auto`) pasó de 10 % a 65 % automatizado.
- **Honestidad**: con 20 tickets fáciles, el LLM generativo acierta más en bruto. El valor de Jev no es
  exactitud sino **saber cuáles decisiones son seguras**: automatizas el tramo confiable con error acotado y
  mandas el resto a humano. Con datos reales (cientos de tickets, más ambiguos) esa diferencia es la que paga.

## Dónde entrega valor (escenarios en la empresa)

| Escenario | Tipo | Por qué Jev y no un agente LLM |
|---|---|---|
| Triage de tickets / correos a área | Choice | Latencia <1 s, % automatizable con error acotado, auditoría de probabilidades |
| Router de agentes (reemplaza el triage LLM del handoff, lab 03) | Choice | La ruta la decide código con umbral; el agente solo contesta |
| Urgencia / prioridad de casos | Score | Valor continuo (3.4/5) para ordenar colas |
| "¿Requiere humano?", "¿Es fraude?", "¿Cumple política?" | Noul | P(sí) calibrada → umbral según costo del error |
| Clasificación de facturas / documentos | Choice | Salida tipada, nunca texto que parsear |
| Moderación de contenido interno | Noul/Choice | Alto volumen, decisiones repetitivas, bajo costo |

No sirve para: redactar respuestas, razonamiento multi-paso, tareas abiertas (ahí van los agentes).

## Seguridad (zero trust)

- Código propio; ningún repo de terceros clonado. Única dependencia: SDK oficial `openai` (en `uv.lock` con hashes).
- `auditar_deps.py`: los paquetes del lock contra OSV → sin CVEs ni paquetes maliciosos (verificado que detecta
  casos conocidos: torch 2.0.0 → 28 avisos).
- Los datos no salen de la máquina (Ollama local). En prod: mismo código contra vLLM on-prem (`LLM_BASE_URL`).
- Alternativas open source auditadas en remoto (Kev, AnyJev): ver resumen en el [README raíz](../README.md#auditoría-zero-trust-de-alternativas-open-source-a-jev).

## Evaluación con dataset de Kaggle (zero trust)

**Qué se aprendió, en una línea:** en este dataset ningún método (Jev 4B/8B, Naive Bayes, LLM generativo) pasa de
~27 % porque las **etiquetas son ruido**, no porque el modelo sea malo; y precisamente por eso sirve como prueba de
que Jev, con umbral derivado del error tolerado, **no rutea mal en silencio**: automatiza ~0 % y manda todo a humano.
Para medir valor hace falta un dataset con etiquetas consistentes (ver Bitext más abajo).

Fuente: "Customer IT Support - Ticket Dataset" (Tobias Bueck), espejo del autor en Hugging Face, archivo
`dataset-tickets-multi-lang-4-20k.csv` fijado al commit `ddf1c81`. **Sintético**, CC BY-NC 4.0 (solo evaluación).

Ingesta (`jev/ingesta.py`): bytes en memoria → tope 25 MB → SHA-256 contra el hash LFS publicado → recién
entonces a `data/` (solo lectura) + `data/MANIFEST.json`. Sin librería `datasets` (ejecuta scripts). Escaneo:
15 celdas que empiezan con `-` (riesgo solo en Excel), 1 falso positivo de prompt injection (`<user>` =
marcador de anonimización, regla corregida), 0 Unicode invisible. El archivo **no trae español** (en/de).

Diagnóstico (inglés, 10 colas, misma muestra: 80 calibración / 120 evaluación):

| Configuración | Exactitud | Colas agrupadas | ECE | Automatizable a ≤10 % error | s/decisión |
|---|---|---|---|---|---|
| Naive Bayes stdlib (11.7k ejemplos supervisados) | 27 % | 45 % | — | — | — |
| Jev 4B sin descripciones | 18 % | 41 % | 0.265 | 4 % (100 % correctas) | 4.1 |
| Jev 4B con descripciones | 20 % | 39 % | 0.412 | 0 % | 4.3 |
| Jev 8B con descripciones | 26 % | 43 % | 0.138 | 0 % | 7.4 |
| LLM generativo 4B (corrida previa, 150 tickets) | 27 % | — | sin confianza | — | 3.7 |

Conclusión (con la evidencia):
- **El cuello de botella son las etiquetas, no el modelo.**
- Un clasificador supervisado con 11.7k ejemplos no supera a los LLM zero-shot (27 %); en la mezcla natural
  NB llega a 41.9 % contra 28 % de "responder siempre Technical Support".
- 36 asuntos **idénticos** aparecen con colas distintas: ruido de etiqueta directo del generador sintético.
- El 8B alcanza el techo de NB y calibra mejor (ECE 0.138); las descripciones no mueven la aguja (±2 tickets,
  dentro del ruido: con 120 ejemplos el intervalo de confianza es de ~±8 puntos).
- T tocó el tope de la grilla (20) en todas: señal de "no hay señal" (la T óptima tiende a infinito).
- **Lo valioso**: con umbral derivado del error, Jev automatiza ~0 % → manda todo a humano en vez de rutear
  mal en silencio. Un LLM generativo habría ruteado solo y fallado ~73 % sin avisar.

**Qué cambió en el proyecto por esto:** (1) se buscó Bitext, con etiquetas limpias; (2) las descripciones por clase
no se dan por buenas sin medirlas en cada dataset; (3) T=20 (tope de la grilla) se trata como alarma de "no hay señal".

Para demostrar valor hacen falta etiquetas consistentes: tickets reales de la empresa (ruteo histórico
auditado) o un dataset con etiquetas humanas. Scripts: `jev/eval_kaggle.py`, `jev/diagnostico_kaggle.py`.

## Evaluación con etiquetas limpias: Bitext Customer Support (zero trust)

Fuente: `bitext/Bitext-customer-support-llm-chatbot-training-dataset` (Hugging Face), commit `430d1a8`,
un CSV de 19.2 MB, SHA-256 verificado en memoria; **CDLA-Sharing-1.0** (permite uso comercial). Híbrido
sintético curado por lingüistas, inglés. 26,872 mensajes, 11 categorías. Escaneo: 13 falsos positivos
de prompt injection en la columna `response` (no usada como entrada). BANKING77 y MASSIVE descartados:
en HF solo tienen scripts de carga `.py` que descargan de URLs externas.

Ruteo por categoría, misma muestra (165 calibración / 220 evaluación). Descripciones **derivadas de los
datos** (intents de cada categoría), no inventadas:

| Configuración | Exactitud | ECE | Automatiza a ≤5 % error (exactitud) | a ≤10 % | s/decisión (CPU) |
|---|---|---|---|---|---|
| Naive Bayes stdlib (26.5k ejemplos supervisados) | 100 % | — | — | — | ~0 |
| Jev 4B sin descripciones | 75 % | 0.059 | 0 % | 62 % (93 %) | 0.52 |
| **Jev 4B con descripciones** | **94 %** | **0.036** | **89 % (99 %)** | 99 % (94 %) | **0.53** |
| Jev 8B con descripciones | 93 % | 0.033 | 100 % (93 %) ⚠️ | 100 % (93 %) | ~3 (suspensión del equipo invalidó la medición) |
| LLM generativo 4B con descripciones | 93 % | sin confianza | — | — | 1.62 |

Lecciones:
- **Aquí sí se ve el valor de Jev**: misma exactitud que el LLM generativo (94 % vs 93 %), 3x más rápido, y
  sabe **cuáles** decisiones son seguras: automatiza el 89 % del tráfico con 1 % de error y manda el 11 % a
  humano. El generativo acierta 93 % pero no distingue su 7 % de errores: se rutean mal en silencio.
- **Descripciones derivadas de los datos: +19 puntos** (75 → 94 %). Aclaran fronteras que el nombre no dice
  (`cancel order` es ORDER; CANCEL es solo la tarifa de cancelación). En Kaggle no ayudaron porque el
  problema eran las etiquetas.
- **8B no mejora al 4B** y su umbral a 5 % se sobreajustó (93 % en evaluación): con 165 ejemplos de
  calibración el umbral es frágil. En prod: cientos de ejemplos y validación separada.
- **Honestidad**: con 26k ejemplos etiquetados, un Naive Bayes de 30 líneas llega a 100 % en este dataset
  (plantillas muy léxicas). Si la empresa tiene miles de tickets bien etiquetados, un clasificador
  supervisado barato puede ganar. Jev/LLM zero-shot conviene con **pocas o ninguna etiqueta**, categorías
  que cambian, arranque en frío, o como segunda opinión con confianza calibrada.
- Muestra de 220: intervalo de confianza de ~±3 puntos alrededor de 94 %.

Script: `jev/eval_bitext.py`. Ingesta: `uv run python jev/ingesta.py bitext`.

## Con tickets de la empresa (`jev/evaluar_empresa.py`)

1. Exporta unos cientos de tickets (ideal 50+ por área) a CSV UTF-8 con dos columnas: texto y área real
   (la que finalmente lo resolvió, no la asignada al inicio). Guárdalo en `data/` — nunca lo compartas ni subas.
2. Opcional: `areas.json` con `{"Facturación": "cobros, comprobantes, notas de crédito", ...}` redactado por
   soporte (en Bitext las descripciones subieron la exactitud de 75 % a 94 %).
3. Ejecuta:

```bash
uv run python jev/evaluar_empresa.py data/tickets_empresa.csv --texto texto --area area --descripciones data/areas.json
```

Guardas zero trust: aborta si `LLM_BASE_URL` no es local (salvo `--permitir-remoto`); anonimiza email,
tarjeta (Luhn), RUC, celular y DNI antes del modelo (sobre-anonimiza números de 8 dígitos, a propósito);
reporta posibles prompt injection; la salida solo muestra métricas agregadas, nunca textos de tickets; el
artefacto `data/calibracion-<nombre>.json` guarda T, umbrales y el SHA-256 del CSV de origen.

Prueba con Bitext como sustituto: 95 % de exactitud, ECE 0.017, automatiza 97 % con 96 % a error objetivo 5 %.

## Jev alojado de TypeSafe y segundo juez (`jev/typesafe.py`)

Cliente mínimo (solo `httpx`) del servicio alojado `POST /v1/systemone`, con el mismo contrato que `Jev.preguntar`
(solo `Choice`). Usa las `probabilities` del servicio, no su `confidence` (una medida de dispersión), y el umbral local
se aplica sin recalibrar. La clave sale de `TYPESAFE_API_KEY` y nunca se imprime. Se usa de dos formas:

- **Medición:** `uv run python evals/evaluar.py --perfil typesafe --grabar` (ver [evals/README.md](../evals/README.md)).
- **Segundo juez del router:** `JEV_SEGUNDO=typesafe` en `router-api`; solo desempata dudas, con el mensaje anonimizado y
  cupo de consultas (`DECISIONES.md` §9 y §13).

## Qué cambió desde estas mediciones

Los números de Kaggle y Bitext de arriba son de 2026-09 con 11 clases. Después se añadió la clase `OTRO` (fuera de dominio),
se recalibró con 40 ejemplos por clase y se midió fuera del golden propio:

- **El 95 % de Bitext no transfiere.** Sobre un hold-out independiente (240 casos) y sobre consultas de otro rubro
  (Banking77, 300 casos) la exactitud dentro de lo automatizado queda en 87-92 %, no en el 95 % de error objetivo
  (`DECISIONES.md` §10, §12 y §14). Calibra con tickets de tu canal antes de confiar en el umbral.
- **Calibración vigente:** `data/calibracion-bitext-otro.json` (T = 6.5, umbral al 5 % de error = 0.88).
- **Datos propios:** `evals/csv_a_golden.py` convierte tickets reales en un golden privado (ignorado por git).

## Límites conocidos

- Opciones que son prefijo una de otra ("cuenta"/"cuentas") pierden masa en tokens ambiguos.
- `urgencia`/`molesto` salen sin calibrar (conf 1.00): cada pregunta necesita su propia T y dataset.
- T y umbral ajustados con pocos ejemplos: en prod usar cientos + set de validación separado.
- Grilla de T acotada a 20: si la calibración llega al tope, el modelo no tiene señal para esa pregunta.
- En CPU: 2–4 s/decisión (4B) y ~7 s (8B) con emails de ~600 caracteres; en GPU/vLLM, decenas de ms.
