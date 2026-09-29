"""Test determinista del tool convertir (spec: openspec/specs/divisas). Sin LLM.

uv run python labs/test_divisas.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from empresa import convertir  # noqa: E402


def test_convertir() -> None:
    assert convertir(250, "USD", "PEN") == 937.5
    assert convertir(100, "EUR", "USD") == 109.33
    assert convertir(10, "usd", "pen") == 37.5
    try:
        convertir(10, "JPY", "PEN")
        raise AssertionError("JPY debió fallar")
    except ValueError as e:
        assert "JPY" in str(e)


if __name__ == "__main__":
    test_convertir()
    print("ok")
