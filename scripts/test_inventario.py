"""Tests deterministas del inventario (spec: openspec/specs/inventario). Sin red ni LLM.

uv run python scripts/test_inventario.py
"""
import secrets
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from inventario import (comparar_modelos, inventario_credenciales, recomendar, render_credenciales,  # noqa: E402
                        ruta_legible)


def test_comparar_modelos() -> None:
    esperados = [{"nombre": "a", "digest": "d1"}, {"nombre": "b", "digest": "d2"}]
    r = comparar_modelos(esperados, {"a": "d1", "b": "d9", "c": "d3"})
    assert r["estados"] == {"a": "ok", "b": "distinto"} and r["no_inventariado"] == ["c"]
    assert comparar_modelos(esperados, {"a": "d1"})["estados"]["b"] == "falta"


def test_credenciales_sin_valores() -> None:
    valor = secrets.token_urlsafe(32)
    with tempfile.TemporaryDirectory() as d:
        env = Path(d) / ".env"
        env.write_text(f"API_TOKEN={valor}\nLLM_MODEL=qwen3:4b-instruct\n", encoding="utf-8")
        filas = inventario_credenciales(env, Path(d) / "no-existe.key")
        texto = render_credenciales(filas)
    assert "API_TOKEN" in texto and valor not in texto and str(filas).find(valor) == -1


def test_ruta_legible() -> None:
    assert ruta_legible(Path.home() / ".ollama" / "models") == "~/.ollama/models"


def test_recomendar() -> None:
    cs = [{"nombre": "m24", "ram_min_gb": 24}, {"nombre": "m48", "ram_min_gb": 48}, {"nombre": "m36", "ram_min_gb": 36}]
    assert [c["nombre"] for c in recomendar(36, cs)] == ["m36", "m24"]


if __name__ == "__main__":
    test_recomendar()
    test_comparar_modelos()
    test_credenciales_sin_valores()
    test_ruta_legible()
    print("ok")
