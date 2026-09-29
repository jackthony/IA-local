"""Patrón 4b: orquestador local que delega a un agente remoto vía A2A (agente-como-tool)."""
import asyncio
import os

from agent_framework.a2a import A2AAgent

from common import agent


async def main() -> None:
    async with A2AAgent(url=os.getenv("A2A_URL", "http://localhost:5001/"), name="divisas",
                        description="Agente remoto experto en divisas") as remoto:
        orquestador = agent("orquestador", "Coordinas. Para cualquier tema de monedas delega en la tool 'divisas'.",
                            tools=[remoto.as_tool()])
        print(await orquestador.run("Voy a gastar 250 USD en Lima, ¿cuánto es en soles aprox?"))


if __name__ == "__main__":
    asyncio.run(main())
