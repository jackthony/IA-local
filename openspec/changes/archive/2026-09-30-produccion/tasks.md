## 1. Tests
- [x] 1.1 servicios/test_servicios.py: BearerAuth (4 escenarios), token débil, router 400/401 (fallaron antes)

## 2. Servicios
- [x] 2.1 seguridad.py, telemetria.py
- [x] 2.2 mcp_http.py, a2a_divisas.py, router_api.py
- [x] 2.3 scripts/generar_env.py + .env.example; extra prod (OTel)

## 3. Contenedores
- [x] 3.1 Dockerfile + compose.yaml endurecidos (digests); `docker compose config` válido
- [x] 3.2a Prueba sin Docker en Windows: 401 x3, 421 Host falso, router ok, A2A->MCP 937.5
- [x] 3.2b MacBook (M5 Pro, Docker Desktop 29.7.2, Ollama Metal): build + up; cliente_demo en 3.4 s: 401 sin token
      (router y A2A), router PAYMENT 0.93 auto / ORDER 0.61 humano / injection -> humano, A2A->MCP 937.5;
      dentro de la red: MCP 401 sin token, 421 Host falso; uid 10001, FS solo lectura, sin capabilities,
      puertos solo 127.0.0.1. Trazas en Jaeger (router-api, a2a-divisas con tools/call al MCP) sin contenido
      de mensajes. Jaeger pasó a `read_only` + tmpfs (el requisito "todos los servicios" no lo cumplía)

## 4. Cierre
- [x] 4.1 CI (tests servicios, runner ubuntu-24.04), README producción, datasets con LICENCIAS.md
- [x] 4.2 Commit + push (identidad noreply) y CI verde (run 36690885256 en main, 26 s)
