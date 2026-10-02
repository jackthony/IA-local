## 1. Tests (fallaron antes)
- [x] 1.1 scripts/test_escanear_secretos.py: dominio de ejemplo, sin dominios, configuración por variable y por archivo
- [x] 1.2 scripts/test_repo.py: `LICENSE` es MIT y el README enlaza `LICENSE` y `data/LICENCIAS.md`

## 2. Implementación
- [x] 2.1 `dominios_corporativos()` y `buscar_secretos(texto, dominios)`; aviso sin dominios; sin el dominio en el árbol
- [x] 2.2 `LICENSE` (MIT) y sección de licencias en el README; el README deja de decir "repo privado"

## 3. Verificación
- [ ] 3.1 Gate completo y CI verde
- [x] 3.2 Con el dominio real configurado localmente, el escáner bloquea un correo corporativo (sin commitearlo): con IA_DOMINIOS_CORPORATIVOS el escáner devuelve correo_corporativo
- [ ] 3.3 `git grep` del dominio real en el árbol: 0 resultados
