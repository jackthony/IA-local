"""Servidor MCP 'empresa': expone los sistemas de negocio a cualquier agente (stdio).

Lo lanza el cliente como subproceso: MCPStdioTool("empresa", sys.executable, args=[este_archivo]).
En prod: mcp.run("streamable-http") detrás de auth; mismo código de tools.
"""
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).parent))
from empresa import convertir, ventas_por_region  # noqa: E402

mcp = FastMCP("empresa")
mcp.tool()(convertir)
mcp.tool()(ventas_por_region)

if __name__ == "__main__":
    mcp.run()
