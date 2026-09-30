## Why

El proyecto creció (11 labs, Jev, servicios, datasets, modelos, tokens, imágenes) y el usuario lo
llevará a una MacBook M5 Pro donde ya tiene otros modelos descargados. Necesita orden: qué se usa,
dónde vive, cuánto ocupa, qué credenciales existen y cómo compartir modelos entre proyectos.

## What Changes

- `modelos.json`: manifiesto de modelos (tag, digest SHA-256 del manifiesto del registro, tamaño,
  uso). Los modelos no van a git; el digest permite verificar que otra máquina baje exactamente lo auditado.
- `scripts/inventario.py`: genera `INVENTARIO.md` en cualquier máquina (modelos vs manifiesto,
  almacenes de modelos detectados, datasets verificados por hash, credenciales SOLO por nombre y
  ubicación, herramientas, tamaños) y sale con código 1 si falta o cambió algo obligatorio.
- `ARQUITECTURA.md`: mapa del sistema para aprender (componentes, flujos, credenciales, orden de
  carpetas `~/IA/` compartido entre proyectos, siguiente nivel en la Mac con tamaños medidos).
- `experimentos/`: prototipos y experimentos de la sesión que llevaron a cada hallazgo.

## Impact

- Sin dependencias nuevas. `INVENTARIO.md` se regenera por máquina (rutas con `~`, sin valores secretos).
