"""Evalúa y calibra Jev con tickets de la empresa (spec: openspec/specs/jev-empresa).

Zero trust para datos internos:
- aborta si el LLM no es local (LLM_BASE_URL), salvo --permitir-remoto;
- anonimiza PII (email, tarjeta Luhn, RUC, celular, DNI) antes de enviar texto al modelo;
- registra el SHA-256 del CSV de origen en el artefacto de calibración;
- escanea marcadores de prompt injection en los tickets (clientes también son entrada no confiable).

Uso (CSV con una columna de texto y otra de área):
  uv run python jev/evaluar_empresa.py data/tickets_empresa.csv --texto texto --area area [--descripciones areas.json]
Salida: métricas + data/calibracion-<nombre>.json (lo consume el router en producción).
"""
import argparse
import asyncio
import collections
import datetime
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent))
from diagnostico_kaggle import NaiveBayes  # noqa: E402
from eval_kaggle import evaluar, tops  # noqa: E402
from ingesta import DATA, filas, hallazgos, muestra  # noqa: E402
from jev import Choice, Jev, calibrar, ece, etiquetas, umbral_auto  # noqa: E402

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
TARJETA = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
RUC = re.compile(r"(?<!\d)(?:10|15|16|17|20)\d{9}(?!\d)")
TELEFONO = re.compile(r"(?<![\d+])(?:\+?51[\s-]?)?9\d{2}[\s-]?\d{3}[\s-]?\d{3}(?!\d)")
DNI = re.compile(r"(?<!\d)\d{8}(?!\d)")  # ponytail: también tapa códigos de 8 dígitos; sobre-anonimizar es lo seguro


def _luhn(digitos: str) -> bool:
    total = 0
    for i, d in enumerate(reversed(digitos)):
        n = int(d) * (2 if i % 2 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def anonimizar(texto: str) -> str:
    texto = EMAIL.sub("[EMAIL]", texto)
    texto = TARJETA.sub(lambda m: "[TARJETA]" if _luhn(re.sub(r"\D", "", m.group())) else m.group(), texto)
    texto = RUC.sub("[RUC]", texto)
    texto = TELEFONO.sub("[TELEFONO]", texto)
    return DNI.sub("[DNI]", texto)


PATRONES_PII = (("EMAIL", EMAIL, None), ("TARJETA", TARJETA, lambda s: _luhn(re.sub(r"\D", "", s))),
                ("RUC", RUC, None), ("TELEFONO", TELEFONO, None), ("DNI", DNI, None))
MARCADOR = re.compile(r"\[(?:EMAIL|TARJETA|RUC|TELEFONO|DNI)_\d+\]")


def anonimizar_con_mapa(texto: str) -> tuple[str, dict[str, str]]:
    """Como `anonimizar`, pero con marcadores numerados y el mapa para rehidratar la respuesta final.

    El mapa es PII: nunca va al modelo, a checkpoints ni a logs (vive en la bóveda local del caso).
    """
    mapa, inverso = {}, {}

    def reemplazar(tipo, valida):
        def f(m):
            valor = m.group()
            if valida and not valida(valor):
                return valor
            if valor not in inverso:
                n = sum(k.startswith(f"[{tipo}_") for k in mapa) + 1
                inverso[valor] = f"[{tipo}_{n}]"
                mapa[inverso[valor]] = valor
            return inverso[valor]
        return f

    for tipo, patron, valida in PATRONES_PII:
        texto = patron.sub(reemplazar(tipo, valida), texto)
    return texto, mapa


def rehidratar(texto: str, mapa: dict[str, str]) -> str:
    """Reinserta PII solo en marcadores exactos del mapa (la salida final al cliente, en código)."""
    return MARCADOR.sub(lambda m: mapa.get(m.group(), m.group()), texto)


def es_local(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in ("localhost", "127.0.0.1", "::1") or host.endswith(".localhost")


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("csv", type=Path)
    ap.add_argument("--nombre", help="nombre del artefacto (por defecto: nombre del archivo)")
    ap.add_argument("--texto", default="texto", help="columna con el texto del ticket")
    ap.add_argument("--area", default="area", help="columna con el área real")
    ap.add_argument("--descripciones", type=Path, help='JSON {"area": "qué entra en ella"}')
    ap.add_argument("--desc-columna", help="columna de sub-etiqueta para derivar descripciones (p. ej. intent)")
    ap.add_argument("--pregunta", default="Clasifica el ticket en una de estas áreas")
    ap.add_argument("--rotulo", default="Ticket")
    ap.add_argument("--modelo", default="qwen3:4b-instruct")
    ap.add_argument("--n-cal", type=int, default=15, help="por área")
    ap.add_argument("--n-ev", type=int, default=20, help="por área")
    ap.add_argument("--extra", type=Path, help="CSV adicional con las mismas columnas (p. ej. mensajes fuera de dominio de una clase OTRO)")
    ap.add_argument("--permitir-remoto", action="store_true", help="permite un LLM no local (los datos salen)")
    a = ap.parse_args()

    base = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    if not es_local(base) and not a.permitir_remoto:
        raise SystemExit(f"LLM_BASE_URL={base} no es local: los tickets saldrían de la máquina. Usa --permitir-remoto si está autorizado.")

    crudo = a.csv.read_bytes()
    sha = hashlib.sha256(crudo).hexdigest()
    requeridas = {a.texto, a.area} | ({a.desc_columna} if a.desc_columna else set())
    fs = [f for f in filas(crudo.decode("utf-8-sig"), requeridas) if f[a.area].strip() and f[a.texto].strip()]
    sha_extra = None
    if a.extra:
        extra = a.extra.read_bytes()
        sha_extra = hashlib.sha256(extra).hexdigest()
        fs += [f for f in filas(extra.decode("utf-8-sig"), requeridas) if f[a.area].strip() and f[a.texto].strip()]
    redacciones, inyecciones = collections.Counter(), 0
    for f in fs:
        f["_t"] = anonimizar(f[a.texto])
        f["_a"] = f[a.area].strip()
        redacciones.update(re.findall(r"\[(EMAIL|TARJETA|RUC|TELEFONO|DNI)\]", f["_t"]))
        inyecciones += "prompt_injection" in hallazgos(f[a.texto])
    areas = [x for x, _ in collections.Counter(f["_a"] for f in fs).most_common()]
    print(f"{a.csv.name} sha256={sha[:16]}… | {len(fs)} tickets | {len(areas)} áreas | "
          f"PII anonimizada: {dict(redacciones) or 'ninguna'} | posibles prompt injection: {inyecciones}")

    cal = muestra(fs, a.n_cal, semilla=1, etiqueta="_a")
    usados = {id(f) for f in cal}
    ev = muestra([f for f in fs if id(f) not in usados], a.n_ev, semilla=2, etiqueta="_a")
    usados |= {id(f) for f in ev}
    resto = [f for f in fs if id(f) not in usados]

    if a.descripciones:
        mapa = json.loads(a.descripciones.read_text(encoding="utf-8"))
        desc = tuple(mapa.get(x, x) for x in areas)
    elif a.desc_columna:
        sub = collections.defaultdict(set)
        for f in resto:
            sub[f["_a"]].add(f[a.desc_columna].replace("_", " "))
        desc = tuple("incluye: " + ", ".join(sorted(sub[x])) for x in areas)
    else:
        desc = None
    tipo = Choice(tuple(areas), desc)

    if resto:
        nb = NaiveBayes().fit([f["_t"] for f in resto], [f["_a"] for f in resto])
        print(f"Naive Bayes ({len(resto)} ej.): {sum(nb.predecir(f['_t']) == f['_a'] for f in ev) / len(ev):.1%}")

    jev = Jev(a.modelo, rotulo=a.rotulo, base_url=base)
    t0 = time.perf_counter()
    tp_cal, _ = await tops(jev, cal, tipo, lambda f: f["_t"], a.pregunta)
    tp_ev, lat = await tops(jev, ev, tipo, lambda f: f["_t"], a.pregunta)
    t = calibrar([(x, etiquetas(tipo), f["_a"]) for x, f in zip(tp_cal, cal)])
    ds, ok, conf = evaluar(tp_ev, ev, tipo, t, "_a")
    _, ok_c, conf_c = evaluar(tp_cal, cal, tipo, t, "_a")
    print(f"Jev {a.modelo}: exactitud {sum(ok) / len(ok):.1%} | ECE {ece(conf, ok):.3f} | T {t} | "
          f"{lat:.2f} s/decisión | {time.perf_counter() - t0:.0f}s total")

    umbrales = {}
    for err in (0.05, 0.10):
        u = umbral_auto(conf_c, ok_c, err)
        umbrales[f"{err:.2f}"] = u
        auto = [x for c, x in zip(conf, ok) if c >= u]
        print(f"  error objetivo {err:.0%}: umbral {u:.2f} -> automatiza {len(auto) / len(ev):.0%} "
              f"con exactitud {sum(auto) / max(len(auto), 1):.0%}; resto a humano")
    por = collections.defaultdict(list)
    for d, f in zip(ds, ev):
        por[f["_a"]].append(d.valor == f["_a"])
    print("por área:", {x: f"{sum(v)}/{len(v)}" for x, v in por.items()})

    salida = DATA / f"calibracion-{a.nombre or a.csv.stem}.json"
    DATA.mkdir(exist_ok=True)
    salida.write_text(json.dumps({
        "modelo": a.modelo, "T": t, "umbrales": umbrales, "opciones": list(areas),
        "descripciones": list(desc) if desc else None, "pregunta": a.pregunta, "rotulo": a.rotulo,
        "n_cal": len(cal), "n_ev": len(ev), "exactitud_ev": sum(ok) / len(ok), "ece_ev": ece(conf, ok),
        "fecha": datetime.date.today().isoformat(), "origen": a.csv.name, "sha256_origen": sha,
        **({"extra": a.extra.name, "sha256_extra": sha_extra} if a.extra else {}),
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"artefacto: {salida}")


if __name__ == "__main__":
    asyncio.run(main())
