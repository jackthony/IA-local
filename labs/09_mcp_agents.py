"""Patrón 7: tools compartidos vía MCP con mínimo privilegio.

Un servidor MCP (08) = sistemas de la empresa. Cada agente se conecta y SOLO ve los tools de su rol.
Los datos vienen del sistema, no del modelo: grounding contra la fabricación de cifras.
"""
import asyncio
import sys
import time
from pathlib import Path

from agent_framework import MCPStdioTool
from agent_framework.orchestrations import SequentialBuilder

from common import ExigeTool, agent, show

SERVER = [str(Path(__file__).parent / "08_mcp_server.py")]


def empresa(*tools: str) -> MCPStdioTool:
    # ponytail: stdio = un subproceso por agente. En prod: un solo servidor HTTP (MCPStreamableHTTPTool).
    return MCPStdioTool("empresa", sys.executable, args=SERVER, allowed_tools=list(tools))


async def main() -> None:
    async with empresa("ventas_por_region") as ventas, empresa("convertir") as cambio:
        analista = agent("analista", "Obtén las cifras SOLO con la tool ventas_por_region (montos en PEN). "
                                     "Reporta el dato en PEN con el número exacto. NUNCA conviertas monedas: "
                                     "eso lo hace finanzas.", tools=[ventas])
        # Medido: finanzas copió la conversión inventada del analista y Ollama ignora tool_choice -> guardia en código.
        finanzas = agent("finanzas", "Convierte a USD la cifra en PEN que reportó el analista usando la tool "
                                     "convertir. Responde con ambos montos.", tools=[cambio],
                         middleware=[ExigeTool("convertir")])
        t = time.time()
        wf = SequentialBuilder(participants=[analista, finanzas], intermediate_output_from=[analista]).build()
        r = await wf.run("¿Cuánto vendió la región Lima en Q3? Dámelo en soles y en dólares.")
        show(r.get_intermediate_outputs())
        show(r.get_outputs())
        print(f"({time.time() - t:.0f}s)")


if __name__ == "__main__":
    asyncio.run(main())
