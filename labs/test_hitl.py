"""Tests deterministas del router con aprobación humana (spec: openspec/specs/hitl). Sin LLM.

uv run python labs/test_hitl.py
"""
import importlib
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
h = importlib.import_module("11_hitl_router")
CLAVE = b"clave-de-prueba-32-bytes-exactos!"


def falla(fn, texto: str = "") -> None:
    try:
        fn()
    except ValueError as e:
        assert texto in str(e), e
        return
    raise AssertionError("debió lanzar ValueError")


def test_sello() -> None:
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "abc.json").write_text('{"estado": 1}', encoding="utf-8")
        h.sellar(d, CLAVE)
        h.verificar_checkpoint(d, "abc", CLAVE)
        (d / "abc.json").write_text('{"estado": 2}', encoding="utf-8")
        h.sellar(d, CLAVE)  # re-sellar NO debe legitimar el archivo manipulado
        falla(lambda: h.verificar_checkpoint(d, "abc", CLAVE), "sello")
        (d / "nuevo.json").write_text("{}", encoding="utf-8")
        falla(lambda: h.verificar_checkpoint(d, "nuevo", CLAVE))


def test_acuerdo() -> None:
    cs = [{"jev": "ORDER", "humano": "ORDER"}, {"jev": "CANCEL", "humano": "ORDER"}, {"jev": "REFUND", "humano": "REFUND"}]
    assert h.acuerdo(cs) == 2 / 3
    assert h.acuerdo(cs + [{"jev": "ACCOUNT", "humano": "DESCARTADO"}]) == 2 / 3
    assert h.acuerdo([]) is None and h.acuerdo([{"jev": "ACCOUNT", "humano": "DESCARTADO"}]) is None


def test_validar_reembolso() -> None:
    assert h.validar_reembolso({"monto": 900, "motivo": "x"})[0] is False
    assert h.validar_reembolso({"monto": -5, "motivo": "x"})[0] is False
    assert h.validar_reembolso({"monto": "mucho", "motivo": "x"})[0] is False
    assert h.validar_reembolso({"monto": 50, "motivo": "x"}) == (True, "")


def test_limpiar_marcadores() -> None:
    assert h.limpiar_marcadores("escríbanos a [EMAIL_1] hoy") == ("escríbanos a (dato no disponible) hoy", 1)
    assert h.limpiar_marcadores("sin marcadores") == ("sin marcadores", 0)


if __name__ == "__main__":
    test_limpiar_marcadores()
    test_sello()
    test_acuerdo()
    test_validar_reembolso()
    print("ok")
