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

## 4. Si el modelo no responde, el router manda el caso a una persona

- **Contexto.** Al correr el golden set contra el servicio real, un modelo caído daba 500 y un modelo colgado retenía
  la petición hasta 10 min (el cliente OpenAI espera eso y reintenta 2 veces).
- **Decisión.** Sin distribución de Jev no hay decisión: el endpoint responde **503** con
  `{"destino": "humano", "motivo": "jev no disponible"}`. Plazo de 10 s (`JEV_TIMEOUT_S`) y cero reintentos ocultos;
  si reintentar conviene, lo decide el cliente. También cubre al modelo que responde 200 sin logprobs.
- **Por qué.** Es el mismo principio que el umbral: abstenerse cuando no se sabe. Un 503 deja la caída visible en
  monitoreo (un 200 con "humano" la escondería) y el cuerpo le dice al cliente qué hacer.
- **Cuesta.** El cliente debe tratar 503 como "a humano"; una caída prolongada del modelo manda todo a la cola humana.
- **Verificación.** `servicios/test_escenarios.py` (caído, lento, sin logprobs).

## 5. Divergencias aceptadas como limitaciones conocidas, no como umbral laxo

- **Contexto.** Al pasar los 69 casos de ruteo por HTTP, 5 terminaron en un destino distinto al esperado y la puerta
  de evals no lo veía: solo medía exactitud de clase, ECE, automatización y críticos. Dos son conservadores (a humano
  con 0.68 y 0.63 de confianza); tres son mensajes fuera de dominio ("hello", el clima) que salen a un especialista,
  dos con 0.97: el 4B es sobreconfiado fuera de dominio y la temperatura no lo corrige.
- **Decisión.** No se relajó el escenario ni se añadió una regla por mensaje. Cada divergencia consta en
  `evals/golden/limitaciones-v2-ollama.json` con su impacto, y la puerta funciona como trinquete: una divergencia nueva
  falla, una que cambia de destino falla, y una resuelta obliga a retirarla del archivo.
- **Por qué.** Una regla por mensaje sobreajusta al golden y no generaliza; un umbral laxo (p. ej. 92 % de destino)
  deja entrar un empeoramiento hasta ese piso. El trinquete mantiene la deuda visible y solo permite mejorarla.
- **Cuesta.** Mantener el archivo al regrabar. **No se atacó la causa** (falta una clase fuera-de-dominio calibrada con
  ejemplos); queda como mitigación pendiente.
- **Verificación.** `evals/test_evals.py` y `servicios/test_escenarios.py` (la lista debe coincidir exacta).

## 6. Un modelo en la nube no sirve como Jev solo por ser compatible con OpenAI

- **Contexto.** Se grabó el golden con `deepseek-chat` (API compatible con OpenAI, el único proveedor en la nube con
  logprobs entre los disponibles; la API de Claude no los expone). Resultado: 91.2 % de exactitud, 1 s de latencia
  (15× la de Ollama local) y dos problemas de fondo, ambos medidos en `evals/golden/predicciones-v2-deepseek.jsonl`.
- **Logprobs degenerados.** El primer token trae 0.0 y todos los demás -9999: no hay distribución, la confianza es
  binaria. Con eso `umbral_auto`, la temperatura y el ECE pierden sentido (el ECE de 0.008 es una coincidencia de
  errores, no calibración). La tabla lo muestra en la fila "Logprobs degenerados".
- **Tokenización.** DeepSeek escribe `CANCEL` como `C`+`ANCEL`; `distribucion` descarta los tokens que son prefijo de
  más de una opción (`C` también lo es de `CONTACT`) y cae a uniforme: CANCEL queda 0/5. Es un límite del puntaje
  por primer token, no un error del modelo: depende de cómo el tokenizador parte los nombres de las opciones.
- **Decisión.** DeepSeek no entra como Jev del router; la comparación queda documentada tal cual, sin recalibrar para
  que salga bien. Las limitaciones conocidas pasan a ser **por perfil** (`limitaciones-v2-<perfil>.json`): antes la
  puerta aplicaba las de Ollama a otro modelo.
- **Cuesta / pendiente.** Un Jev en la nube exigiría etiquetas con primer token único (códigos en lugar de nombres) y
  un proveedor con logprobs reales; no se probó. Claude y DeepSeek sí caben como especialistas (System 2).
- **Verificación.** `evals/evaluar.py --comparar` y `evals/test_evals.py`.

## 7. El Jev alojado se mide con el mismo golden, con sus probabilidades y sin recalibrar

- **Contexto.** `jev/` es una versión propia del concepto "System One"; TypeSafe ofrece el original como servicio
  (`POST /v1/systemone`, Bearer, probabilidades calibradas por opción, tokens de uso en la respuesta).
- **Decisión.** Perfil `typesafe` en `evals/` con un cliente mínimo (`jev/typesafe.py`, solo `httpx`, sin SDK nuevo):
  se guardan sus `probabilidades` y se aplica el mismo `decidir_ruta` y el mismo golden. No se usa su `confidence`, que
  es `(p_max − 1/n)/(1 − 1/n)` y no la probabilidad de acierto que `umbral_auto` necesita.
- **Por qué sin recalibrar.** Calibrar con el propio golden sería fuga de datos. El umbral 0.7033 es de otro modelo, así
  que los números de ECE y automatización de este perfil se leen como indicativos hasta recalibrar con datos aparte.
- **Controles.** La clave solo por env (nunca en errores, bitácoras ni predicciones); errores sin cuerpo (un servicio
  puede repetir el estado enviado); reintento con backoff solo en 429/529; la respuesta se valida (opciones ajenas o
  masa ≠ 1 son error); PII anonimizada antes de salir; topes de llamadas/tokens/USD con corte previo (`Presupuesto`).
- **Resultado (golden-v2, 69 casos, 2026-10-16).** Exactitud 100 %, ECE 0.002, 85.5 % automatizado, 0 críticos a
  automático, destino 95.7 %, latencia mediana 342 ms (p95 445), 544 tokens de entrada y 111 de salida por decisión. Con el
  precio público de lista (entrada USD 0.042 por millón, salida gratis; verifica tu plan) son ~USD 0.023 por cada 1,000
  decisiones. Frente a Ollama (100 %, 82.6 %, 69 ms, costo 0): igual de exacto, 5× más lento y con costo, a cambio de
  probabilidades calibradas por el proveedor. Las 3 divergencias de destino son las mismas fuera de dominio de Ollama
  (`limitaciones-v2-typesafe.json`): no dependen del modelo sino de que el catálogo no tiene una opción "otro".
- **Lectura honesta.** Sobre 69 casos escritos por nosotros, la diferencia de 3 puntos de automatización no es
  concluyente; no hay evidencia aquí de que el servicio supere al modelo local, solo de que lo iguala con más latencia.
- **Verificación.** `evals/test_typesafe.py` contra un servicio falso, incluida la grabación completa.

## 8. Decisiones menores relacionadas

- **Reembolso: el LLM propone, el humano aprueba los argumentos exactos, el código ejecuta** (`proto_aprobacion.py`),
  con política de montos en código (`MAX_REEMBOLSO`) y operación idempotente. Aprobación humana no sustituye política.
- **Prompt injection → cola humana**, no solo filtrado: Jev está acotado a una categoría, pero el especialista
  sí leería el texto hostil.
- **Golden set con predicciones grabadas** (`evals/`): CI no depende de un LLM ni de red; recalcula ruteo con el
  código vigente. No detecta deriva del modelo: para eso se regraba (`--grabar`) o se corre
  `servicios/test_escenarios.py --vivo`, que repite los escenarios contra el modelo real.
- **Escenarios de producción contra un servidor falso compatible con OpenAI** (`evals/llm_falso.py`): el recorrido
  completo (HTTP, auth, PII, cliente de Jev, ruteo, workflow, checkpoints, ledger) corre en CI sin LLM. Cada prueba de
  seguridad se validó rompiendo el código a propósito (mutación) para comprobar que falla.
