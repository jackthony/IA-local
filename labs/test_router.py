"""Tests deterministas del router Jev (spec: openspec/specs/router). Sin LLM.

uv run python labs/test_router.py
"""
import importlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
r = importlib.import_module("10_router_jev")

VALIDA = {"modelo": "m", "T": 4.5, "umbrales": {"0.05": 0.7}, "opciones": ["REFUND"], "pregunta": "p", "rotulo": "M"}


def test_cargar_calibracion() -> None:
    with tempfile.TemporaryDirectory() as d:
        ok = Path(d) / "ok.json"
        ok.write_text(json.dumps(VALIDA), encoding="utf-8")
        assert r.cargar_calibracion(ok)["T"] == 4.5
        mala = Path(d) / "mala.json"
        mala.write_text(json.dumps({k: v for k, v in VALIDA.items() if k != "umbrales"}), encoding="utf-8")
        try:
            r.cargar_calibracion(mala)
            raise AssertionError("debió lanzar ValueError")
        except ValueError as e:
            assert "umbrales" in str(e)


def test_decidir_ruta() -> None:
    esp = {"REFUND": "pagos"}
    assert r.decidir_ruta("REFUND", 0.93, 0.70, esp) == ("pagos", "auto")
    assert r.decidir_ruta("REFUND", 0.55, 0.70, esp) == ("humano", "confianza baja")
    assert r.decidir_ruta("OTRA", 0.99, 0.70, esp) == ("humano", "sin especialista")
    assert r.decidir_ruta("REFUND", 0.99, 0.70, esp, sospechoso=True) == ("humano", "posible prompt injection")


def test_registro() -> None:
    reg = r.registro("soy ana@acme.pe y quiero mi reembolso", "REFUND", 0.93456, ["REFUND", "PAYMENT"], "pagos", "auto", 812)
    texto = json.dumps(reg)
    assert "[EMAIL]" in texto and "ana@acme.pe" not in texto
    assert reg["confianza"] == 0.935 and reg["top2"] == ["REFUND", "PAYMENT"] and "ts" in reg


if __name__ == "__main__":
    test_cargar_calibracion()
    test_decidir_ruta()
    test_registro()
    print("ok")
