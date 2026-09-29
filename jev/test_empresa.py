"""Tests deterministas del pipeline para tickets de la empresa (spec: openspec/specs/jev-empresa). Sin red ni LLM.

uv run python jev/test_empresa.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from evaluar_empresa import anonimizar, anonimizar_con_mapa, es_local, rehidratar  # noqa: E402


def test_anonimizar() -> None:
    assert anonimizar("Escríbanme a juan.perez@acme.pe o al +51 987654321") == "Escríbanme a [EMAIL] o al [TELEFONO]"
    assert anonimizar("DNI 45678912, RUC 20123456789") == "DNI [DNI], RUC [RUC]"
    assert anonimizar("pagué con 4111 1111 1111 1111") == "pagué con [TARJETA]"
    assert anonimizar("pedido 1234 por S/ 250") == "pedido 1234 por S/ 250"


def test_anonimizacion_reversible() -> None:
    original = "de ana@acme.pe para luis@x.pe"
    anon, mapa = anonimizar_con_mapa(original)
    assert anon == "de [EMAIL_1] para [EMAIL_2]"
    assert mapa == {"[EMAIL_1]": "ana@acme.pe", "[EMAIL_2]": "luis@x.pe"}
    assert rehidratar(anon, mapa) == original
    assert rehidratar("escriba a [EMAIL_9]", mapa) == "escriba a [EMAIL_9]"  # solo marcadores del mapa


def test_es_local() -> None:
    assert es_local("http://localhost:11434/v1") and es_local("http://127.0.0.1:8000/v1")
    assert not es_local("https://api.openai.com/v1") and not es_local("http://localhost.evil.com/v1")


if __name__ == "__main__":
    test_anonimizar()
    test_anonimizacion_reversible()
    test_es_local()
    print("ok")
