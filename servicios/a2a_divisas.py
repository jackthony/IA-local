"""Agente A2A 'divisas' con Bearer, que usa el MCP 'empresa' por HTTP con su propio token.

Service-to-service zero trust: el cliente A2A presenta A2A_TOKEN; este agente presenta MCP_TOKEN al MCP.
La Agent Card (pública) declara el esquema Bearer; el JSON-RPC exige token.
.venv/bin/uvicorn --app-dir servicios a2a_divisas:app --host 0.0.0.0 --port 5001
"""
import contextlib
import os
import sys
from pathlib import Path

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (AgentCapabilities, AgentCard, AgentInterface, AgentSkill, HTTPAuthSecurityScheme,
                       SecurityScheme)
from agent_framework import MCPStreamableHTTPTool
from agent_framework.a2a import A2AExecutor
from starlette.applications import Starlette

RAIZ = Path(__file__).resolve().parent.parent
for d in ("labs", "servicios"):
    sys.path.insert(0, str(RAIZ / d))
from seguridad import BearerAuth, token_requerido  # noqa: E402
from telemetria import configurar  # noqa: E402

configurar("a2a-divisas")
from common import ExigeTool, agent  # noqa: E402

A2A_TOKEN, MCP_TOKEN = token_requerido("A2A_TOKEN"), token_requerido("MCP_TOKEN")
URL = os.getenv("A2A_URL", "http://localhost:5001/")
MCP_URL = os.getenv("MCP_URL", "http://localhost:8001/mcp")
TARJETA = "/.well-known/agent-card.json"

empresa = MCPStreamableHTTPTool("empresa", MCP_URL, allowed_tools=["convertir"],
                                static_headers={"Authorization": f"Bearer {MCP_TOKEN}"})
divisas = agent("divisas", "Eres experto en divisas. Para CUALQUIER conversión usa la tool convertir; nunca "
                "calcules tú. Responde breve con el resultado de la tool.", tools=[empresa],
                middleware=[ExigeTool("convertir")])

card = AgentCard(
    name="divisas", description="Convierte montos entre monedas (PEN/USD/EUR) con tasas del sistema.",
    version="1.0.0", supported_interfaces=[AgentInterface(url=URL, protocol_binding="JSONRPC")],
    capabilities=AgentCapabilities(streaming=False), default_input_modes=["text"], default_output_modes=["text"],
    security_schemes={"bearer": SecurityScheme(http_auth_security_scheme=HTTPAuthSecurityScheme(
        scheme="Bearer", description="Token de servicio (A2A_TOKEN)"))},
    skills=[AgentSkill(id="convertir", name="Convertir moneda", description="PEN/USD/EUR", tags=["finanzas"],
                       examples=["¿Cuánto son 250 USD en PEN?"])],
)
handler = DefaultRequestHandler(agent_executor=A2AExecutor(divisas), task_store=InMemoryTaskStore(), agent_card=card)


@contextlib.asynccontextmanager
async def ciclo(_app):
    async with empresa:  # conexión MCP autenticada durante la vida del servicio
        yield


app = BearerAuth(Starlette(routes=[*create_agent_card_routes(card, card_url=TARJETA),
                                   *create_jsonrpc_routes(handler, "/")], lifespan=ciclo),
                 A2A_TOKEN, publicas={TARJETA})
