"""Escáner de secretos antes de publicar (spec: openspec/specs/repo). Solo stdlib.

Recorre los archivos que git publicaría (versionados + nuevos no ignorados) y sale con código 1 si
encuentra tokens, claves privadas o un correo corporativo. Nunca imprime el secreto: solo archivo:línea.
Los dominios corporativos NO están en el repo (es público): salen de IA_DOMINIOS_CORPORATIVOS o de
~/.ia-local/dominios-corporativos (uno por línea) en cada máquina.
uv run python scripts/escanear_secretos.py
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ARCHIVO_DOMINIOS = Path.home() / ".ia-local" / "dominios-corporativos"
PATRONES = {
    "github_token": re.compile(r"\b(?:gh[pous]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    "aws_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    "clave_privada": re.compile("-----BEGIN [A-Z ]*" + "PRIVATE KEY-----"),
}


def dominios_corporativos(entorno=os.environ, archivo: Path = ARCHIVO_DOMINIOS) -> list[str]:
    """Variable IA_DOMINIOS_CORPORATIVOS (comas) o, si no existe, el archivo local (`#` comenta)."""
    if "IA_DOMINIOS_CORPORATIVOS" in entorno:
        crudos = entorno["IA_DOMINIOS_CORPORATIVOS"].split(",")
    else:
        try:
            crudos = archivo.read_text(encoding="utf-8").splitlines()
        except OSError:
            crudos = []
    return [d.strip() for d in crudos if d.strip() and not d.strip().startswith("#")]


def buscar_secretos(texto: str, dominios: list[str] | None = None) -> list[str]:
    hallados = [nombre for nombre, patron in PATRONES.items() if patron.search(texto)]
    dominios = dominios_corporativos() if dominios is None else dominios
    if dominios:
        correo = re.compile(r"[\w.+-]+@(?:" + "|".join(re.escape(d) for d in dominios) + r")\b", re.IGNORECASE)
        if correo.search(texto):
            hallados.append("correo_corporativo")
    return hallados


def archivos_a_publicar(raiz: Path) -> list[Path]:
    salida = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                            cwd=raiz, capture_output=True, text=True, check=True).stdout
    return [raiz / linea for linea in salida.splitlines() if linea]


def main() -> int:
    raiz = Path(__file__).resolve().parent.parent
    dominios = dominios_corporativos()
    hallazgos = []
    archivos = archivos_a_publicar(raiz)
    for p in archivos:
        try:
            texto = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binario: no aplica
        for n, linea in enumerate(texto.splitlines(), 1):
            for cat in buscar_secretos(linea, dominios):
                hallazgos.append(f"{p.relative_to(raiz)}:{n} {cat}")
    print(f"{len(archivos)} archivos a publicar escaneados")
    if not dominios:
        print(f"  aviso: correo_corporativo inactivo (define IA_DOMINIOS_CORPORATIVOS o {ARCHIVO_DOMINIOS})")
    for h in hallazgos:
        print(f"  BLOQUEADO {h}")
    print("sin secretos" if not hallazgos else f"{len(hallazgos)} hallazgos: NO publicar")
    return 1 if hallazgos else 0


if __name__ == "__main__":
    sys.exit(main())
