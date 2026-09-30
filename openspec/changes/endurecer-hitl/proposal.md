## Why

Revisión de seguridad del router y del lab 11 (2026-09-30), con prueba de concepto de cada hallazgo:

1. **Detector de prompt injection evadible.** `"Ignore<U+200B> all previous instructions"` solo daba
   `unicode_invisible` (el router lo ignoraba y ruteaba en automático); un salto de línea o espacios
   múltiples entre palabras, o "earlier" en vez de "previous", no daban nada.
2. **`sellar()` legitimaba archivos ajenos.** Sellaba todo `*.json` sin sello del directorio: un checkpoint
   plantado por un tercero (sin la clave) quedaba sellado en el siguiente `procesar()`, y `get_latest`
   deserializaba cualquier archivo, incluso uno con fecha futura que se volvía "el último".
3. **Lo que el supervisor ve no era lo que se ejecuta.** `revisar` mostraba `pendientes.json` (sin firma) y
   `aprobado` ejecuta los argumentos del checkpoint: editar la cola mostraba S/ 45 y se pagaban S/ 450.
4. **Reembolso no idempotente.** Si el proceso caía tras pagar y antes de guardar la cola, responder de nuevo
   reanudaba el mismo checkpoint y pagaba dos veces.

## What Changes

- `jev/ingesta.py`: `normalizar()` (quita caracteres de formato Cf, NFKC, colapsa espacios) antes del patrón;
  el patrón acepta "earlier".
- `labs/10_router_jev.py`: `es_sospechoso(mensaje)` = `prompt_injection` o `unicode_invisible`; lo usan el
  lab 10, el lab 11 y `servicios/router_api.py`.
- `labs/11_hitl_router.py`:
  - `AlmacenSellado(FileCheckpointStorage)`: sella cada checkpoint al guardarlo (`sellar(dir, id, clave)`,
    uno a la vez, nunca por glob) y verifica al cargar y al listar (un archivo sin sello nunca se deserializa).
  - Cola firmada: `firmar_entrada` / `verificar_entrada` (HMAC ligado al `request_id`); `revisar` no muestra
    y `responder` no reanuda una entrada manipulada.
  - `ejecutar_reembolso(operacion, monto, motivo)` idempotente por `operacion` (caso + id de la tool call);
    la tool que ve el LLM (`proponer_reembolso`) nunca paga por sí misma.

## Impact

- Sin dependencias nuevas. Checkpoints y colas de corridas anteriores no se reanudan (`iniciar` ya borra
  `data/hitl/`).
- Límite conocido: el detector sigue siendo una lista de patrones; una paráfrasis nueva lo evade. La defensa
  sigue en capas (salida acotada de Jev, especialistas sin tools sensibles, aprobación humana, política en código).
