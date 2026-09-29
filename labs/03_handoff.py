"""Patrón 3: handoff. Triage decide a qué especialista pasa el control.

Topología estrella (triage -> especialistas). La malla por defecto (todos con todos)
hace que modelos pequeños se reboten el caso en vez de resolverlo.
"""
import asyncio

from agent_framework.orchestrations import HandoffBuilder

from common import agent, show

# Handoff corta llamadas a tools: el framework exige persistir historial por llamada.
H = {"require_per_service_call_history_persistence": True}


async def main() -> None:
    triage = agent("triage", "Clasifica la consulta y transfiere al especialista correcto. No la resuelvas tú.", **H)
    facturacion = agent("facturacion", "Resuelves dudas de facturación y pagos, breve.",
                        description="Cobros, facturas, pagos, reembolsos", **H)
    tecnico = agent("tecnico", "Resuelves problemas técnicos, breve.",
                    description="Errores, caídas, acceso, configuración", **H)

    wf = (HandoffBuilder(participants=[triage, facturacion, tecnico])
          .with_start_agent(triage)
          .add_handoff(triage, [facturacion, tecnico])
          .with_autonomous_mode(turn_limits={"triage": 2})  # sin input humano; tope anti-loop
          .with_termination_condition(  # termina cuando un especialista responde con texto
              lambda msgs: any(m.author_name in ("facturacion", "tecnico") and m.text for m in msgs))
          .build())
    show((await wf.run("Me cobraron dos veces la factura de septiembre")).get_outputs())


if __name__ == "__main__":
    asyncio.run(main())
