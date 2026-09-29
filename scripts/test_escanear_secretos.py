"""Test determinista del escáner de secretos (spec: openspec/changes/repo-github).

Los secretos de prueba se arman por concatenación: el repo nunca contiene uno literal.
uv run python scripts/test_escanear_secretos.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from escanear_secretos import buscar_secretos  # noqa: E402


def test_buscar_secretos() -> None:
    assert "github_token" in buscar_secretos("token=" + "gh" + "p_" + "a" * 36)
    cabecera = "-----BEGIN " + "RSA PRIVATE KEY-----"
    correo = "alguien" + "@" + "acity.com.pe"
    h = buscar_secretos(f"{cabecera}\nMIIE...\n{correo}")
    assert "clave_privada" in h and "correo_corporativo" in h
    assert "openai_key" in buscar_secretos("OPENAI=" + "s" + "k-" + "x" * 30)
    assert buscar_secretos("api_key = os.getenv('LLM_API_KEY', 'ollama')") == []


if __name__ == "__main__":
    test_buscar_secretos()
    print("ok")
