"""Patrón 4a: expone un agente como servicio A2A (Agent Card + JSON-RPC).

uv run uvicorn --app-dir labs 04_a2a_server:app --port 5001  (ver README)
"""
import os

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from agent_framework.a2a import A2AExecutor
from starlette.applications import Starlette

from common import agent
from empresa import convertir

URL = os.getenv("A2A_URL", "http://localhost:5001/")

divisas = agent("divisas", "Eres experto en divisas. Para CUALQUIER conversión usa la tool convertir; "
                "nunca calcules tú. Responde breve con el resultado de la tool.", tools=[convertir])

card = AgentCard(
    name="divisas",
    description="Convierte montos entre monedas y explica tipos de cambio.",
    version="0.1.0",
    supported_interfaces=[AgentInterface(url=URL, protocol_binding="JSONRPC")],
    capabilities=AgentCapabilities(streaming=False),
    default_input_modes=["text"],
    default_output_modes=["text"],
    skills=[AgentSkill(id="convertir", name="Convertir moneda", description="PEN/USD/EUR",
                       tags=["finanzas"], examples=["¿Cuánto son 100 USD en PEN?"])],
)

handler = DefaultRequestHandler(agent_executor=A2AExecutor(divisas), task_store=InMemoryTaskStore(),
                                agent_card=card)
app = Starlette(routes=[*create_agent_card_routes(card), *create_jsonrpc_routes(handler, "/")])
