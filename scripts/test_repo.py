"""Test determinista de lo que el repo público debe tener (spec: openspec/specs/repo).

uv run python scripts/test_repo.py
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def test_licencia_mit_y_readme() -> None:
    licencia = (RAIZ / "LICENSE").read_text(encoding="utf-8")
    assert licencia.startswith("MIT License") and "Permission is hereby granted, free of charge" in licencia
    readme = (RAIZ / "README.md").read_text(encoding="utf-8")
    assert "(LICENSE)" in readme and "(data/LICENCIAS.md)" in readme


if __name__ == "__main__":
    test_licencia_mit_y_readme()
    print("ok")
