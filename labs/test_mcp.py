"""Test determinista del servidor MCP empresa por protocolo real (spec: openspec/specs/mcp-empresa). Sin LLM.

uv run python labs/test_mcp.py
"""
import asyncio
import json
import sys
from pathlib import Path

from agent_framework import AgentResponse, Content, MCPStdioTool, Message
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

sys.path.insert(0, str(Path(__file__).parent))
from common import llamo_tool  # noqa: E402

SERVER = [str(Path(__file__).parent / "08_mcp_server.py")]


def _valor(result):
    """Valor del tool: structuredContent si existe, si no el texto."""
    if result.structuredContent is not None:
        return result.structuredContent.get("result", result.structuredContent)
    return result.content[0].text


async def test_protocolo() -> None:
    async with stdio_client(StdioServerParameters(command=sys.executable, args=SERVER)) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            assert {t.name for t in (await s.list_tools()).tools} == {"ventas_por_region", "convertir"}
            assert float(_valor(await s.call_tool("convertir", {"monto": 250, "de": "USD", "a": "PEN"}))) == 937.5
            assert json.loads(_valor(await s.call_tool("ventas_por_region", {})))["total"]["q3"] == 564000


async def test_minimo_privilegio() -> None:
    async with MCPStdioTool("empresa", sys.executable, args=SERVER, allowed_tools=["convertir"]) as t:
        assert [f.name for f in t.functions] == ["convertir"]


def test_llamo_tool() -> None:
    def resp(*contents):
        return AgentResponse(messages=[Message("assistant", list(contents))])
    llamada = Content.from_function_call(call_id="1", name="convertir", arguments={"monto": 1})
    otra = Content.from_function_call(call_id="2", name="ventas_por_region", arguments={})
    assert llamo_tool(resp(llamada), "convertir")
    assert not llamo_tool(resp("solo texto"), "convertir")
    assert not llamo_tool(resp(otra), "convertir")


if __name__ == "__main__":
    asyncio.run(test_protocolo())
    asyncio.run(test_minimo_privilegio())
    test_llamo_tool()
    print("ok")
