"""Genera .env con tokens aleatorios por servicio (nunca los imprime). No sobrescribe un .env existente.

uv run python scripts/generar_env.py
"""
import os
import secrets
import stat
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PLANTILLA = RAIZ / ".env.example"
DESTINO = RAIZ / ".env"


def main() -> int:
    if DESTINO.exists():
        print(".env ya existe: no se sobrescribe (bórralo a mano para rotar tokens)")
        return 0
    lineas = []
    for linea in PLANTILLA.read_text(encoding="utf-8").splitlines():
        clave, _, valor = linea.partition("=")
        lineas.append(f"{clave}={secrets.token_urlsafe(32)}" if valor == "<generar>" else linea)
    DESTINO.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    os.chmod(DESTINO, stat.S_IREAD | stat.S_IWRITE)  # solo el dueño
    print(f".env creado con tokens nuevos ({sum('<generar>' in x for x in PLANTILLA.read_text().splitlines())}); no se muestran")
    return 0


if __name__ == "__main__":
    sys.exit(main())
