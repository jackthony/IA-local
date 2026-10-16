"""Convierte tickets reales (CSV) en un golden privado para medir el router y la cascada con tráfico propio.

Zero trust para datos de clientes:
- anonimiza la PII ANTES de escribir nada (el golden nunca contiene correos, tarjetas, RUC, teléfonos ni DNI);
- escribe solo en evals/golden/privado/ (ignorado por git) y se niega a escribir en otro sitio;
- no adivina áreas: toda área del CSV debe estar en las del catálogo o en --mapa; si falta alguna, aborta y las lista;
- los mensajes con patrón de prompt injection pasan a casos críticos que deben ir a humano.

  uv run python evals/csv_a_golden.py tickets.csv --texto texto --area area [--mapa mapa.json] [--max 300] [--nombre mis-tickets]
  uv run python evals/evaluar.py --golden evals/golden/privado/golden-mis-tickets.jsonl --grabar          # Ollama (local)
  uv run python evals/evaluar.py --golden evals/golden/privado/golden-mis-tickets.jsonl --perfil typesafe --grabar
  uv run python evals/evaluar.py --golden evals/golden/privado/golden-mis-tickets.jsonl --cascada
"""
import argparse
import importlib
import json
import random
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PRIVADO = RAIZ / "evals" / "golden" / "privado"
sys.path.insert(0, str(RAIZ / "jev"))
sys.path.insert(0, str(RAIZ / "labs"))
from evaluar_empresa import anonimizar  # noqa: E402
from ingesta import filas  # noqa: E402

r10 = importlib.import_module("10_router_jev")


class AreasSinMapa(ValueError):
    pass


def convertir(texto_csv: str, col_texto: str, col_area: str, opciones: list[str], mapa: dict[str, str] | None = None,
              maximo: int = 300, semilla: int = 7) -> list[dict]:
    mapa = mapa or {}
    malos = [o for o in mapa.values() if o not in opciones]
    if malos:
        raise ValueError(f"el mapa apunta a categorías que no existen: {sorted(set(malos))}")
    filas_ok = [f for f in filas(texto_csv, {col_texto, col_area}) if f[col_texto].strip() and f[col_area].strip()]
    destino = lambda a: mapa.get(a.strip(), a.strip())  # noqa: E731
    sin_mapa = sorted({f[col_area].strip() for f in filas_ok if destino(f[col_area]) not in opciones})
    if sin_mapa:
        raise AreasSinMapa(f"áreas sin categoría: {sin_mapa}. Mapéalas con --mapa (categorías válidas: {opciones})")
    vistos, unicas = set(), []
    for f in filas_ok:  # duplicados fuera: un mismo texto repetido sesga la medición
        t = f[col_texto].strip()
        if t not in vistos:
            vistos.add(t)
            unicas.append({"texto": t, "area": destino(f[col_area])})
    random.Random(semilla).shuffle(unicas)
    casos = []
    for n, f in enumerate(unicas[:maximo], 1):
        limpio, hostil = anonimizar(f["texto"]), r10.es_sospechoso(f["texto"])
        if hostil:
            casos.append({"id": f"real-{n:04d}", "tipo": "ruteo", "mensaje": limpio, "esperado": None,
                          "destino_esperado": "humano", "critico": True, "etiquetas": ["real", "inyeccion"]})
        else:
            otro = f["area"] == "OTRO"
            casos.append({"id": f"real-{n:04d}", "tipo": "ruteo", "mensaje": limpio, "esperado": f["area"],
                          "destino_esperado": "humano" if otro else "auto", "critico": False, "etiquetas": ["real"]})
    return casos


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("csv", type=Path)
    ap.add_argument("--texto", default="texto")
    ap.add_argument("--area", default="area")
    ap.add_argument("--mapa", type=Path, help='JSON {"área del CSV": "CATEGORÍA del catálogo"}')
    ap.add_argument("--max", type=int, default=300)
    ap.add_argument("--nombre", default="mis-tickets")
    ap.add_argument("--salida", type=Path, help=f"debe estar dentro de {PRIVADO.relative_to(RAIZ)}")
    a = ap.parse_args()
    cal = r10.cargar_calibracion(r10.CALIBRACION)
    mapa = json.loads(a.mapa.read_text(encoding="utf-8")) if a.mapa else None
    try:
        casos = convertir(a.csv.read_text(encoding="utf-8-sig"), a.texto, a.area, cal["opciones"], mapa, a.max)
    except AreasSinMapa as e:
        print(f"ABORTADO: {e}", file=sys.stderr)
        return 2
    if len(casos) < 50:
        print(f"ABORTADO: {len(casos)} casos únicos; se necesitan al menos 50 para medir", file=sys.stderr)
        return 2
    salida = (a.salida or PRIVADO / f"golden-{a.nombre}.jsonl").resolve()
    if PRIVADO.resolve() not in salida.parents:
        print(f"ABORTADO: la salida debe estar dentro de {PRIVADO} (ignorado por git)", file=sys.stderr)
        return 2
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in casos) + "\n", encoding="utf-8")
    print(f"{len(casos)} casos anonimizados -> {salida.relative_to(RAIZ)} (no versionado)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
