"""Cliente LLM compartido. Cambia de modelo/servidor por env, no por código.

Usa la API OpenAI-compatible: el mismo código apunta a Ollama (local), vLLM (GPU on-prem)
o Azure/OpenAI (cloud) cambiando LLM_BASE_URL / LLM_API_KEY / LLM_MODEL.
"""
import os

from agent_framework import Agent, AgentContext, AgentMiddleware, Message
from agent_framework.openai import OpenAIChatCompletionClient


def otros_como_user(nombre: str):
    """Envía los mensajes de OTROS agentes como user '[autor]: texto'.

    En group chat/magentic el historial compartido trae varios 'assistant' seguidos y
    Ollama/llama.cpp los rechaza. Mensajes propios y tool calls pasan intactos.
    """
    def prep(msg, out: list[dict]) -> list[dict]:
        if msg.role != "assistant" or not msg.author_name or msg.author_name == nombre:
            return out
        return [{"role": "user", "content": f"[{msg.author_name}]: {_texto(d['content'])}"}
                if d.get("role") == "assistant" and d.get("content") and not d.get("tool_calls") else d
                for d in out]
    return prep


def _texto(content) -> str:
    return content if isinstance(content, str) else "".join(p.get("text", "") for p in content)


def client(model: str | None = None, nombre: str | None = None) -> OpenAIChatCompletionClient:
    return OpenAIChatCompletionClient(
        model=model or os.getenv("LLM_MODEL", "qwen3:4b-instruct"),
        base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.getenv("LLM_API_KEY", "ollama"),  # Ollama ignora la key; vLLM/Azure no.
        message_preparer=otros_como_user(nombre) if nombre else None,
    )


def agent(name: str, instructions: str, model: str | None = None, **kwargs) -> Agent:
    return Agent(client(model, name), instructions, name=name, **kwargs)


def llamo_tool(respuesta, nombre: str) -> bool:
    """¿La respuesta del agente incluye una llamada al tool `nombre`?"""
    return any(c.type == "function_call" and c.name == nombre
               for m in respuesta.messages for c in m.contents)


class ExigeTool(AgentMiddleware):
    """Obliga en código a que el agente use un tool (Ollama ignora `tool_choice`).

    Si la respuesta no llamó `nombre`, reintenta con una instrucción explícita. Tras `intentos`,
    deja la última respuesta: quien la consuma debe tratarla como no verificada.
    """

    def __init__(self, nombre: str, intentos: int = 2) -> None:
        self.nombre, self.intentos = nombre, intentos

    async def process(self, context: AgentContext, call_next) -> None:
        for intento in range(1, self.intentos + 1):
            await call_next()
            if context.stream or llamo_tool(context.result, self.nombre):
                return
            print(f"  [ExigeTool: intento {intento}/{self.intentos} sin {self.nombre}]")
            context.messages = [*context.messages, Message(
                "user", [f"No usaste la tool {self.nombre}. Úsala ahora; no respondas cifras sin ella."])]


def show(outputs) -> None:
    """Imprime salidas de un workflow mensaje a mensaje, con su autor."""
    for out in outputs:
        msgs = getattr(out, "messages", None) or (out if isinstance(out, list) else [out])
        for m in msgs:
            if getattr(m, "role", None) == "user":
                continue
            quien = getattr(m, "author_name", None) or getattr(m, "role", "?")
            for c in getattr(m, "contents", []):  # tool calls visibles: qué dato vino de un sistema
                if c.type == "function_call":
                    print(f"  [{quien} -> {c.name}({c.arguments})]")
                elif c.type == "function_result":
                    print(f"  [= {str(c.result)[:120]}]")
            if getattr(m, "text", m):
                print(f"[{quien}] {getattr(m, 'text', m)}\n")
