"""Patrón 1: agente único + tools (loop ReAct gestionado por el framework)."""
import asyncio
from typing import Annotated

from agent_framework import tool

from common import agent

PEDIDOS = {"A100": "enviado", "A200": "pendiente de pago"}


@tool(description="Consulta el estado de un pedido por su código")
def estado_pedido(codigo: Annotated[str, "Código del pedido, ej. A100"]) -> str:
    return PEDIDOS.get(codigo.upper(), "no existe")


async def main() -> None:
    soporte = agent("soporte", "Eres soporte. Usa las tools; responde breve en español.",
                    tools=[estado_pedido])
    print(await soporte.run("¿Cómo va mi pedido a200?"))


if __name__ == "__main__":
    asyncio.run(main())
