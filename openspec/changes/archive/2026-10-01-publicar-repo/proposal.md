## Why

El repo pasa a ser público (portafolio y LinkedIn). La auditoría de todo el historial (295 blobs y los mensajes
de commit) no encontró secretos, rutas personales ni datos reales: solo datos ficticios de tests (`acme.pe`).
El único dato propio es el dominio del empleador, que el escáner de secretos tenía escrito en el código, el test
y la spec para bloquear correos corporativos. Un repo personal público no debe nombrar al empleador, y un repo
público sin licencia no permite reutilizar el código.

## What Changes

- `scripts/escanear_secretos.py`: los dominios corporativos salen de configuración local fuera de git
  (`IA_DOMINIOS_CORPORATIVOS` o `~/.ia-local/dominios-corporativos`), no del código. Sin dominios configurados
  la categoría `correo_corporativo` queda inactiva y el escáner lo avisa (en CI no hay dominios: los logs de un
  repo público son públicos).
- Test y spec del escáner con un dominio de ejemplo; el del empleador desaparece del árbol. El historial se
  conserva intacto (no se reescribe).
- `LICENSE` (MIT) para el código; los datasets mantienen sus licencias (`data/LICENCIAS.md`).
- README: el repo deja de describirse como privado.

## Impact

- Sin dependencias nuevas. Cada máquina configura su dominio una vez en `~/.ia-local/dominios-corporativos`.
- El dominio sigue visible en commits anteriores (decisión: no reescribir historial).
