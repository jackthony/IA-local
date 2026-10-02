"""Test determinista del escáner de secretos (spec: openspec/specs/repo).

Los secretos de prueba se arman por concatenación: el repo nunca contiene uno literal. El dominio corporativo
de prueba es ficticio (`ejemplo-corp.pe`): el real vive solo en la configuración local de cada máquina.
uv run python scripts/test_escanear_secretos.py
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from escanear_secretos import buscar_secretos, dominios_corporativos  # noqa: E402

DOMINIO = "ejemplo-corp.pe"


def test_buscar_secretos() -> None:
    assert "github_token" in buscar_secretos("token=" + "gh" + "p_" + "a" * 36, dominios=[])
    cabecera = "-----BEGIN " + "RSA PRIVATE KEY-----"
    correo = "alguien" + "@" + DOMINIO
    h = buscar_secretos(f"{cabecera}\nMIIE...\n{correo}", dominios=[DOMINIO])
    assert "clave_privada" in h and "correo_corporativo" in h
    assert "openai_key" in buscar_secretos("OPENAI=" + "s" + "k-" + "x" * 30, dominios=[])
    assert buscar_secretos("api_key = os.getenv('LLM_API_KEY', 'ollama')", dominios=[DOMINIO]) == []


def test_sin_dominios_no_hay_correo_corporativo() -> None:
    assert buscar_secretos("alguien" + "@" + DOMINIO, dominios=[]) == []


def test_dominios_corporativos_por_variable_y_archivo() -> None:
    with tempfile.TemporaryDirectory() as d:
        archivo = Path(d) / "dominios-corporativos"
        archivo.write_text("# comentario\n\nc.org\n", encoding="utf-8")
        assert dominios_corporativos({"IA_DOMINIOS_CORPORATIVOS": " a.pe , b.com "}, archivo) == ["a.pe", "b.com"]
        assert dominios_corporativos({}, archivo) == ["c.org"]
        assert dominios_corporativos({}, Path(d) / "no-existe") == []


if __name__ == "__main__":
    test_buscar_secretos()
    test_sin_dominios_no_hay_correo_corporativo()
    test_dominios_corporativos_por_variable_y_archivo()
    print("ok")
