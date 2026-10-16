# Decisiones y su porqué

Formato: contexto → decisión → por qué → qué cuesta → cómo se verifica. Lo medido remite a `jev/README.md`,
`experimentos/` o `evals/`; lo que no se midió se dice.

## 1. Checkpoints del lab 11 sellados con HMAC

- **Contexto.** El HITL reanudable guarda el estado del workflow en disco para poder cerrar el proceso y retomar
  días después. `proto_hitl.py` mostró que el checkpoint del framework contiene **pickle** aunque se le pasen dicts.
- **Decisión.** Cada checkpoint se sella con HMAC-SHA256 al guardarlo (`SELLOS.hmac`) y se verifica **antes** de
  deserializar. La cola de revisión humana también se firma, ligada a su `request_id`. La clave vive fuera del repo
  (`~/.ia-local/hitl.key`, solo lectura).
- **Por qué.** Deserializar un pickle manipulado ejecuta código. Un archivo plantado en el directorio de
  checkpoints sería ejecución de código en la reanudación. Y si la cola se puede editar, lo que el supervisor ve
  deja de ser lo que se ejecuta (p. ej. un monto cambiado entre la aprobación y el pago).
- **Detalles que importan.** Se sella UN checkpoint que este proceso acaba de escribir, nunca por glob (sellar
  todo `*.json` legitimaba un archivo plantado). Un sello existente no se reescribe. `get_latest` no deserializa
  archivos sin sello válido. El sello va en `.hmac`, no `.json`, porque el framework intenta leer todo `*.json`.
- **Cuesta.** Gestionar una clave: borrarla invalida los checkpoints pendientes. HMAC prueba integridad y origen
  local, no confidencialidad (los checkpoints no llevan PII: va a una bóveda local por caso).
- **Verificación.** `labs/test_hitl.py` (sin LLM): sello íntegro, manipulado, ausente, plantado y entrada de cola editada.

## 2. Umbral de automatización derivado del error tolerado

- **Contexto.** Jev devuelve una confianza por decisión. Hay que decidir desde qué confianza se rutea solo.
- **Decisión.** No se fija un número a ojo (0.9). Se fija el **error que el negocio tolera** (5 %) y
  `umbral_auto` busca el menor umbral cuyo tramo de decisiones por encima acierta ≥ 95 % en datos de calibración.
  La confianza se calibra antes con temperatura (`calibrar`, T de una grilla por NLL); se mide con ECE y Brier.
  El umbral queda en `data/calibracion-*.json` y el código de ruteo (`decidir_ruta`) lo aplica.
- **Por qué.** "0.9" no significa lo mismo en cada modelo ni dataset: un 4B sin calibrar da 1.00 de confianza en
  preguntas sin señal. Hablar en "error tolerado" convierte una decisión técnica en una de negocio, y hace que el
  sistema **se abstenga cuando no sabe**: con las etiquetas ruidosas de Kaggle automatiza ~0 % (todo a humano) en
  lugar de rutear mal en silencio como el LLM generativo (~73 % de fallo sin aviso). Con Bitext, el 4B con
  descripciones automatiza el 89 % del tráfico con 1 % de error.
- **Cuesta.** Necesita datos etiquetados de calibración y recalibrar al cambiar de modelo, prompt o dominio.
  Es frágil con pocas muestras: el 8B "ganó" 100 % automático con 93 % de exactitud real (sobreajuste con 165
  ejemplos). Por eso se pide cientos de ejemplos y validación separada, y `evals/` replica la decisión con el
  umbral vigente.
- **Verificación.** `jev/test_jev.py` (umbral, ECE), `labs/test_router.py` (ruteo) y `evals/` (puerta de CI).

## 3. Topología en estrella en vez de malla (handoff)

- **Contexto.** `HandoffBuilder` por defecto conecta a todos con todos.
- **Decisión.** Un agente de triage que deriva a especialistas que **no** se derivan entre sí
  (`add_handoff(triage, [facturacion, tecnico])`), con tope de turnos del triage y condición de término explícita.
  En producción el mismo principio se movió a código: Jev elige, `decidir_ruta` rutea (lab 10).
- **Por qué.** Observado con modelos chicos: en malla se rebotan el caso (ping-pong) en vez de resolverlo.
  La estrella da un único punto de decisión, un recorrido auditable y un tope natural de saltos. Es la misma
  idea que recorre el proyecto: la estructura y las decisiones de riesgo viven en código; el LLM aporta contenido.
- **Cuesta.** Triage es punto único de fallo y cuello de botella; un caso que necesita dos especialistas obliga a
  volver al centro. Qué tan frecuente es el ping-pong con modelos grandes **no se midió**: la regla se adoptó con
  modelos de 4-8B.
- **Verificación.** `labs/03_handoff.py` (demo); no hay test automatizado de la topología.

## 4. Decisiones menores relacionadas

- **Reembolso: el LLM propone, el humano aprueba los argumentos exactos, el código ejecuta** (`proto_aprobacion.py`),
  con política de montos en código (`MAX_REEMBOLSO`) y operación idempotente. Aprobación humana no sustituye política.
- **Prompt injection → cola humana**, no solo filtrado: Jev está acotado a una categoría, pero el especialista
  sí leería el texto hostil.
- **Golden set con predicciones grabadas** (`evals/`): CI no depende de un LLM ni de red; recalcula ruteo con el
  código vigente. No detecta deriva del modelo: para eso se regraba (`--grabar`).
