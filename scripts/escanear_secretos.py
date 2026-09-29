"""Escáner de secretos antes de publicar (spec: openspec/changes/repo-github). Solo stdlib.

Recorre los archivos que git publicaría (versionados + nuevos no ignorados) y sale con código 1 si
encuentra tokens, claves privadas o el correo corporativo. Nunca imprime el secreto: solo archivo:línea.
uv run python scripts/escanear_secretos.py
"""
import re
import subprocess
import sys
from pathlib import Path

DOMINIO = "acity" + ".com.pe"  # armado por concatenación: este archivo no contiene el patrón literal
PATRONES = {
    "github_token": re.compile(r"\b(?:gh[pous]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    "aws_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    "clave_privada": re.compile("-----BEGIN [A-Z ]*" + "PRIVATE KEY-----"),
    "correo_corporativo": re.compile(r"[\w.+-]+@" + re.escape(DOMINIO), re.IGNORECASE),
}


def buscar_secretos(texto: str) -> list[str]:
    return [nombre for nombre, patron in PATRONES.items() if patron.search(texto)]


def archivos_a_publicar(raiz: Path) -> list[Path]:
    salida = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                            cwd=raiz, capture_output=True, text=True, check=True).stdout
    return [raiz / linea for linea in salida.splitlines() if linea]


def main() -> int:
    raiz = Path(__file__).resolve().parent.parent
    hallazgos = []
    archivos = archivos_a_publicar(raiz)
    for p in archivos:
        try:
            texto = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binario: no aplica
        for n, linea in enumerate(texto.splitlines(), 1):
            for cat in buscar_secretos(linea):
                hallazgos.append(f"{p.relative_to(raiz)}:{n} {cat}")
    print(f"{len(archivos)} archivos a publicar escaneados")
    for h in hallazgos:
        print(f"  BLOQUEADO {h}")
    print("sin secretos" if not hallazgos else f"{len(hallazgos)} hallazgos: NO publicar")
    return 1 if hallazgos else 0


if __name__ == "__main__":
    sys.exit(main())
