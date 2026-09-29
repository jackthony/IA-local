"""Patrón 6: Magentic-One. Un manager planifica (task ledger), delega paso a paso
(progress ledger: ¿terminado? ¿en loop? ¿quién sigue?) y replanifica si se atasca.

Costoso: ~5 llamadas largas del manager por tarea (hechos, plan, 1 ledger por ronda, respuesta final).
En esta CPU: ~18 min con qwen3:4b-instruct, ~20 min con MANAGER_MODEL=qwen3:8b. Itera contra GPU/cloud.
"""
import asyncio
import os
import time

from agent_framework.orchestrations import MagenticBuilder, MagenticOrchestratorEventType

from common import agent, show
from empresa import ventas_por_region

TAREA = "Prepara un resumen ejecutivo de las ventas Q3 vs Q2 por región con una recomendación accionable."

async def main() -> None:
    analista = agent("analista", "Analista de datos. Obtén cifras SOLO con la tool ventas_por_region y reporta "
                                 "hallazgos con números exactos. Nunca calcules tú.",
                     description="Consulta y analiza datos de ventas", tools=[ventas_por_region])
    redactor = agent("redactor", "Redactas resúmenes ejecutivos claros (máx. 120 palabras) usando SOLO las cifras "
                                 "que ya aportó el analista.", description="Redacta el resumen ejecutivo final")
    manager = agent("manager", "Coordinas un equipo para completar tareas de negocio.",
                    model=os.getenv("MANAGER_MODEL"),  # None -> LLM_MODEL
                    default_options={"reasoning_effort": "none"})  # modelos híbridos (qwen3:8b) razonan por defecto

    wf = MagenticBuilder(participants=[analista, redactor], manager_agent=manager,
                         max_round_count=8, max_stall_count=2, max_reset_count=1).build()

    t, final = time.time(), None
    async for ev in wf.run(TAREA, stream=True):
        if ev.type == "magentic_orchestrator":
            d = ev.data
            if d.event_type == MagenticOrchestratorEventType.PROGRESS_LEDGER_UPDATED:
                pl = d.content
                print(f"[{time.time() - t:4.0f}s ledger] satisfecho={pl.is_request_satisfied.answer} "
                      f"-> {pl.next_speaker.answer}: {pl.instruction_or_question.answer}\n")
            else:
                print(f"[{time.time() - t:4.0f}s {d.event_type.value}]\n{d.content.text}\n")
        elif ev.type == "output":
            final = ev.data
    print("===== RESPUESTA FINAL =====")
    show([final])
    print(f"({time.time() - t:.0f}s)")


if __name__ == "__main__":
    asyncio.run(main())
