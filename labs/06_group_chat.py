"""Patrón 5: group chat. Varios agentes conversan; un director decide quién habla.

Modo A: selector determinista (función pura). Barato y predecible.
Modo B: orquestador LLM elige el turno leyendo la conversación. Flexible, cuesta 1 llamada extra por turno.

Principio: la estructura (cuántas réplicas, cuándo cerrar) vive en código; el LLM solo aporta contenido.
"""
import asyncio
import time

from agent_framework import Message
from agent_framework.orchestrations import GroupChatBuilder, GroupChatState

from common import agent, show

TEMA = "¿Debe la empresa reemplazar el primer nivel de soporte con agentes de IA este año?"
RONDAS_DEBATE = 4  # 2 réplicas por lado; luego cierra el último participante (moderador)


def turno(state: GroupChatState) -> str:
    """Round-robin entre los debatientes; tras RONDAS_DEBATE, el último participante cierra."""
    *debatientes, cierre = list(state.participants)
    return debatientes[state.current_round % len(debatientes)] if state.current_round < RONDAS_DEBATE else cierre


def hay_veredicto(msgs: list[Message]) -> bool:
    # tolerante a markdown/mayúsculas: los modelos escriben "**Veredicto:**"
    return any(m.author_name == "moderador" and "VEREDICTO:" in (m.text or "").replace("*", "").upper()
               for m in msgs)


def participantes() -> list:
    return [
        agent("optimista", "Estás SIEMPRE a favor de adoptar; nunca cambies de postura. Argumentos concretos "
                           "de negocio, rebatiendo al escéptico. Máximo 60 palabras.",
              description="Argumenta a favor"),
        agent("esceptico", "Estás SIEMPRE en contra; nunca cambies de postura. Señalas riesgos y costos "
                           "ocultos, rebatiendo al optimista. Máximo 60 palabras.",
              description="Argumenta en contra"),
        agent("moderador", "Cierras el debate sopesando ambos lados. Responde con "
                           "'VEREDICTO: <decisión y condición clave>'. Máximo 60 palabras.",
              description="Cierra el debate con el veredicto final"),
    ]


async def correr(nombre: str, builder: GroupChatBuilder) -> None:
    print(f"\n===== {nombre} =====")
    t = time.time()
    r = await builder.build().run(TEMA)
    show(r.get_intermediate_outputs())  # cada turno del debate
    show(r.get_outputs())
    print(f"({time.time() - t:.0f}s)")


async def main() -> None:
    await correr("A: selector round-robin", GroupChatBuilder(
        participants=participantes(), selection_func=turno,
        termination_condition=hay_veredicto, max_rounds=8, intermediate_output_from="all"))

    await correr("B: orquestador LLM", GroupChatBuilder(
        participants=participantes(),
        orchestrator_agent=agent("director", "Diriges un debate. Elige quién habla para que haya réplica entre "
                                             "optimista y esceptico; tras 2 réplicas de cada uno, da la palabra al "
                                             "moderador. NUNCA pongas terminate=true: el sistema termina solo."),
        termination_condition=hay_veredicto, max_rounds=8, intermediate_output_from="all"))


if __name__ == "__main__":
    asyncio.run(main())
