"""MCP 'empresa' por HTTP (streamable) con Bearer (spec: openspec/changes/produccion).

Protección DNS rebinding ACTIVA con hosts permitidos explícitos (no se desactiva para que funcione en Docker).
.venv/bin/python servicios/mcp_http.py
"""
import os
import sys
from pathlib import Path

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse

RAIZ = Path(__file__).resolve().parent.parent
for d in ("labs", "servicios"):
    sys.path.insert(0, str(RAIZ / d))
from empresa import convertir, ventas_por_region  # noqa: E402
from seguridad import BearerAuth, token_requerido  # noqa: E402
from telemetria import configurar  # noqa: E402

configurar("mcp-empresa")
TOKEN = token_requerido("MCP_TOKEN")
PUERTO = int(os.getenv("MCP_PORT", "8001"))
HOSTS = os.getenv("MCP_ALLOWED_HOSTS", f"localhost:{PUERTO},127.0.0.1:{PUERTO},mcp-empresa:{PUERTO}").split(",")

mcp = FastMCP("empresa", host="0.0.0.0", port=PUERTO, stateless_http=True,
              transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=True,
                                                           allowed_hosts=HOSTS, allowed_origins=[]))
mcp.tool()(convertir)
mcp.tool()(ventas_por_region)


@mcp.custom_route("/salud", methods=["GET"])
async def salud(request: Request) -> JSONResponse:
    return JSONResponse({"estado": "ok"})


app = BearerAuth(mcp.streamable_http_app(), TOKEN, publicas={"/salud"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PUERTO)
