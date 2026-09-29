"""Auditoría zero-trust de dependencias: uv.lock -> OSV (CVEs + paquetes maliciosos de OpenSSF).

Solo stdlib: no se descarga ni ejecuta ninguna herramienta de terceros.
uv run python jev/auditar_deps.py [ruta/uv.lock]
"""
import json
import sys
import tomllib
import urllib.request
from pathlib import Path


def paquetes(lock: dict) -> list[tuple[str, str]]:
    """(nombre, versión) de cada paquete del registro; excluye el proyecto propio (virtual/editable)."""
    return [(p["name"], p["version"]) for p in lock.get("package", [])
            if "version" in p and not {"virtual", "editable"} & set(p.get("source", {}))]


def consultar_osv(pkgs: list[tuple[str, str]]) -> dict[str, list[str]]:
    """IDs de vulnerabilidades por paquete (querybatch de OSV, lotes de 500)."""
    hallazgos = {}
    for i in range(0, len(pkgs), 500):
        lote = pkgs[i:i + 500]
        body = {"queries": [{"package": {"name": n, "ecosystem": "PyPI"}, "version": v} for n, v in lote]}
        req = urllib.request.Request("https://api.osv.dev/v1/querybatch", json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            for (n, v), res in zip(lote, json.load(r)["results"]):
                if res.get("vulns"):
                    hallazgos[f"{n}=={v}"] = [x["id"] for x in res["vulns"]]
    return hallazgos


if __name__ == "__main__":
    ruta = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent / "uv.lock")
    pkgs = paquetes(tomllib.loads(ruta.read_text(encoding="utf-8")))
    hallazgos = consultar_osv(pkgs)
    print(f"{len(pkgs)} paquetes auditados contra OSV")
    for pkg, ids in sorted(hallazgos.items()):
        mal = [i for i in ids if i.startswith("MAL-")]
        print(f"  {'🚨 MALICIOSO' if mal else '⚠️'} {pkg}: {', '.join(ids)}")
    print("sin hallazgos" if not hallazgos else f"{len(hallazgos)} paquetes con avisos")
    sys.exit(1 if any(i.startswith("MAL-") for ids in hallazgos.values() for i in ids) else 0)
