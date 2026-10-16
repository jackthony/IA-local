# evals Specification

## Purpose
Medir el router Jev y la política de reembolso contra un golden set versionado, con una puerta de CI.
## Requirements

### Requirement: Golden set versionado y puerta de CI
`evals/golden/golden-vN.jsonl` SHALL ser inmutable por versión (cambiar casos exige crear `golden-vN+1`), con al menos
50 casos válidos. `evals/evaluar.py` SHALL repetir las predicciones grabadas (logprobs crudos) con la calibración, el
detector y la política vigentes, medir exactitud por clase, ECE, % automatizado, críticos a automático y exactitud de
destino, escribir un reporte JSON por corrida y salir con 1 si algún umbral de `umbrales.json` se pasa. SHALL negarse
a correr si el golden o el prompt de Jev cambiaron desde la grabación.

#### Scenario: Umbral violado
- **WHEN** el umbral de automatización se fija en 1.01
- **THEN** el % automatizado cae a 0 y la puerta devuelve violación

### Requirement: Limitaciones conocidas como trinquete
Todo caso cuyo destino real difiera del esperado SHALL constar en `golden/limitaciones-vN-<perfil>.json` con el destino
observado y un impacto escrito. La puerta SHALL fallar ante una divergencia nueva, ante un cambio de destino de una
conocida, y ante una limitación ya resuelta que siga listada.

#### Scenario: Limitación resuelta
- **WHEN** un caso listado como limitación deja de divergir
- **THEN** la puerta falla pidiendo retirarlo del archivo
