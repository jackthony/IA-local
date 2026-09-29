## Why

El router (lab 10) manda a "cola humana" pero solo imprime: no hay forma de que una persona decida y
el flujo continúe, las acciones sensibles no piden aprobación, y la anonimización deja marcadores como
`[EMAIL]` en la respuesta al cliente. Producción necesita human-in-the-loop real y reanudable.

## What Changes

- `labs/11_hitl_router.py`: workflow con dos puntos de aprobación humana vía `request_info` y
  checkpoints en disco (el proceso puede cerrarse mientras espera):
  1. revisión de ruteo cuando Jev duda o el mensaje es sospechoso;
  2. aprobación de `emitir_reembolso` (tool con `approval_mode="always_require"`): el LLM propone,
     el humano aprueba los argumentos exactos, el código ejecuta.
- Cola humana persistente `data/hitl/pendientes.json` + CLI `iniciar | revisar | responder | demo`.
- Checkpoints sellados con HMAC-SHA256 (clave local fuera del repo): el framework usa pickle
  restringido en checkpoints, así que no se reanuda un checkpoint cuyo sello no verifica.
- Anonimización reversible: marcadores numerados (`[EMAIL_1]`); el mapa vive en una bóveda local por
  caso (nunca en checkpoints ni logs) y se borra tras entregar; la respuesta final se rehidrata en código.
- Cada decisión humana de ruteo queda en `data/correcciones.jsonl` (ejemplo etiquetado para recalibrar)
  y se mide el acuerdo Jev-humano.

## Impact

- Reutiliza lab 10 (`decidir_ruta`, calibración) y `jev/`. Sin dependencias nuevas.
