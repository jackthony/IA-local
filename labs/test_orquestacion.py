"""Tests deterministas de group chat y magentic (spec: openspec/specs/group-chat, openspec/specs/magentic). Sin LLM.

uv run python labs/test_orquestacion.py
"""
import importlib
import json
import sys
from collections import OrderedDict
from pathlib import Path

from agent_framework import Message
from agent_framework.orchestrations import GroupChatState

sys.path.insert(0, str(Path(__file__).parent))
from common import otros_como_user  # noqa: E402
from empresa import ventas_por_region  # noqa: E402
gc = importlib.import_module("06_group_chat")

PARTICIPANTES = OrderedDict(optimista="", esceptico="", moderador="")


def test_turno() -> None:
    assert gc.turno(GroupChatState(0, PARTICIPANTES, [])) == "optimista"
    assert gc.turno(GroupChatState(3, PARTICIPANTES, [])) == "esceptico"
    assert gc.turno(GroupChatState(4, PARTICIPANTES, [])) == "moderador"


def test_hay_veredicto() -> None:
    assert gc.hay_veredicto([Message("assistant", ["VEREDICTO: adoptar"], author_name="moderador")])
    assert gc.hay_veredicto([Message("assistant", ["**Veredicto:** adoptar por fases"], author_name="moderador")])
    assert not gc.hay_veredicto([Message("assistant", ["VEREDICTO: sí"], author_name="optimista")])


def test_otros_como_user() -> None:
    prep = otros_como_user("esceptico")
    ajeno = Message("assistant", ["hola"], author_name="optimista")
    assert prep(ajeno, [{"role": "assistant", "content": "hola"}]) == [{"role": "user", "content": "[optimista]: hola"}]
    propio = Message("assistant", ["yo"], author_name="esceptico")
    assert prep(propio, [{"role": "assistant", "content": "yo"}]) == [{"role": "assistant", "content": "yo"}]
    tc = [{"role": "assistant", "content": None, "tool_calls": [{"id": "1"}]}]
    assert prep(Message("assistant", [], author_name="optimista"), tc) == tc


def test_ventas_por_region() -> None:
    d = json.loads(ventas_por_region())
    assert d["lima"]["crecimiento_pct"] == 15.0
    assert d["sur"]["crecimiento_pct"] == -10.0
    assert d["norte"]["crecimiento_pct"] == 15.0
    assert d["total"]["q3"] == 564000
    assert d["total"]["crecimiento_pct"] == 10.6


if __name__ == "__main__":
    test_turno()
    test_hay_veredicto()
    test_otros_como_user()
    test_ventas_por_region()
    print("ok")
