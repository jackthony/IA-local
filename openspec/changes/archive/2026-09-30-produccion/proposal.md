## Why

Los labs corren como scripts en un equipo. Para producción: servicios en contenedores endurecidos,
autenticación entre servicios (zero trust también dentro de la red), trazas para ver cada decisión
sin exponer datos, y el mismo despliegue en Windows o en la MacBook (Ollama nativo con Metal).

## What Changes

- `servicios/`: `mcp_http.py` (MCP empresa por HTTP), `a2a_divisas.py` (agente A2A que usa el MCP
  por HTTP), `router_api.py` (Jev como servicio de decisión), `seguridad.py` (middleware Bearer
  fail-closed), `telemetria.py` (OpenTelemetry sin datos sensibles), `cliente_demo.py` (host).
- Tokens por servicio desde `.env` (fuera de git), generados por `scripts/generar_env.py` sin imprimirlos.
- Datasets públicos versionados con licencia y manifiesto (para clases sin descarga).
- Docker: no se pudo probar en el equipo Windows (Docker Desktop sin permisos); se valida en la MacBook.
- `Dockerfile` (base y uv fijadas por digest, usuario sin privilegios, dependencias exactas del lock) y
  `compose.yaml` (FS de solo lectura, sin capabilities, `no-new-privileges`, puertos solo en 127.0.0.1,
  Ollama en el host vía `host.docker.internal`, Jaeger fijado por digest).
- Extra `prod`: opentelemetry-sdk y exportador OTLP HTTP 1.45.0 (aprobadas; sin attestation PEP 740, sin CVEs).
- CI: tests de servicios y runner fijado (`ubuntu-24.04`).

## Impact

- Nuevas dependencias solo en el extra `prod`. Imágenes: python:3.12-slim, ghcr.io/astral-sh/uv:0.9.26,
  jaegertracing/jaeger:2.21.0 (todas por digest).
