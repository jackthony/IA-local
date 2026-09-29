"""Patrón 2: pipeline secuencial (redactor -> revisor) y fan-out concurrente."""
import asyncio

from agent_framework.orchestrations import ConcurrentBuilder, SequentialBuilder

from common import agent, show


def agente(nombre: str, rol: str):
    return agent(nombre, rol + " Responde en español, máximo 80 palabras.")


async def main() -> None:
    tema = "Adoptar agentes de IA en soporte al cliente"

    seq = SequentialBuilder(participants=[
        agente("redactor", "Escribe un párrafo persuasivo sobre el tema."),
        agente("revisor", "Critica el texto anterior y entrega una versión mejorada."),
    ]).build()
    print("== SECUENCIAL ==")
    show((await seq.run(tema)).get_outputs())

    con = ConcurrentBuilder(participants=[
        agente("legal", "Analiza riesgos legales."),
        agente("finanzas", "Analiza costos y ROI."),
        agente("tecnico", "Analiza la viabilidad técnica."),
    ]).build()
    print("\n== CONCURRENTE ==")
    show((await con.run(tema)).get_outputs())


if __name__ == "__main__":
    asyncio.run(main())
