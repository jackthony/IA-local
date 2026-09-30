"""Prototipo: tool con approval_mode='always_require' -> ¿qué devuelve agent.run?"""
import asyncio
import sys
from typing import Annotated

sys.path.insert(0, "labs")
from agent_framework import tool  # noqa: E402

from common import agent  # noqa: E402

EJECUTADO = []


@tool(approval_mode="always_require", description="Emite un reembolso al cliente")
def emitir_reembolso(monto: Annotated[float, "Monto en soles"], motivo: Annotated[str, "Motivo breve"]) -> str:
    EJECUTADO.append((monto, motivo))
    return f"reembolso de S/ {monto} emitido"


async def main() -> None:
    a = agent("pagos", "Atiendes reembolsos. Si el cliente pide un reembolso con monto, usa la tool emitir_reembolso.",
              tools=[emitir_reembolso])
    r = await a.run("Me cobraron dos veces 50 soles por el pedido 881, devuélvanme 50 soles")
    print("user_input_requests:", [(c.type, c.function_call.name, c.function_call.arguments) for c in r.user_input_requests])
    print("ejecutado sin aprobación?:", EJECUTADO, "| texto:", repr(r.text[:80]))


asyncio.run(main())
