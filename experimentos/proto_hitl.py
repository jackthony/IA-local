"""Prototipo HITL: pausa con request_info, checkpoint en disco, reanudación en otro proceso. Sin LLM."""
import asyncio
import sys
from pathlib import Path

from agent_framework import Executor, FileCheckpointStorage, WorkflowBuilder, WorkflowContext, handler, response_handler

DIR = Path(__file__).parent / "proto_ckpt"


class Revisor(Executor):
    @handler
    async def entrada(self, msg: dict, ctx: WorkflowContext[dict, dict]) -> None:
        if msg["confianza"] >= 0.7:
            await ctx.yield_output({"ruta": msg["categoria"], "por": "auto"})
        else:
            await ctx.request_info({"mensaje": msg["texto"], "sugerencias": msg["top2"]}, dict)

    @response_handler
    async def revisado(self, original: dict, respuesta: dict, ctx: WorkflowContext[dict, dict]) -> None:
        await ctx.yield_output({"ruta": respuesta["categoria"], "por": "humano", "pedido": original["mensaje"]})


def flujo(storage):
    return WorkflowBuilder(name="proto-hitl", start_executor=Revisor(id="revisor"), checkpoint_storage=storage).build()


async def main() -> None:
    storage = FileCheckpointStorage(DIR)
    if sys.argv[1] == "iniciar":
        r = await flujo(storage).run({"texto": "cancel my order", "confianza": 0.52, "categoria": "ORDER", "top2": ["ORDER", "CANCEL"]})
        reqs = r.get_request_info_events()
        print("salidas:", r.get_outputs(), "| pendientes:", [(e.request_id, e.data) for e in reqs])
        print("storage métodos:", [m for m in dir(storage) if not m.startswith("_")])
    else:
        ultimo = await storage.get_latest(workflow_name="proto-hitl")
        print("último checkpoint:", ultimo.checkpoint_id, "| archivos:", [p.name for p in DIR.iterdir()][:4])
        wf = flujo(storage)
        r = await wf.run(checkpoint_id=ultimo.checkpoint_id, checkpoint_storage=storage)
        reqs = r.get_request_info_events()
        print("pendientes tras restaurar:", [(e.request_id, e.data) for e in reqs])
        r2 = await wf.run(responses={reqs[0].request_id: {"categoria": "ORDER"}})
        print("salidas tras responder:", r2.get_outputs())


asyncio.run(main())
