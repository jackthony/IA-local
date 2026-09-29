## 1. Tests
- [x] 1.1 servicios/test_servicios.py: BearerAuth (4 escenarios), token débil, router 400/401 (fallaron antes)

## 2. Servicios
- [x] 2.1 seguridad.py, telemetria.py
- [x] 2.2 mcp_http.py, a2a_divisas.py, router_api.py
- [x] 2.3 scripts/generar_env.py + .env.example; extra prod (OTel)

## 3. Contenedores
- [x] 3.1 Dockerfile + compose.yaml endurecidos (digests); `docker compose config` válido
- [x] 3.2a Prueba sin Docker en Windows: 401 x3, 421 Host falso, router ok, A2A->MCP 937.5
- [ ] 3.2b Build + up + cliente_demo + trazas en Jaeger — PENDIENTE en la MacBook (Docker sin permisos en Windows)

## 4. Cierre
- [x] 4.1 CI (tests servicios, runner ubuntu-24.04), README producción, datasets con LICENCIAS.md
- [ ] 4.2 Commit + push (identidad noreply) y CI verde
