"""Evaluación del router Jev (lab 10) y de la política de reembolso del lab 11 contra un golden set versionado.

  uv run python evals/evaluar.py                      # repite predicciones grabadas (sin LLM) -> puerta de CI
  uv run python evals/evaluar.py --grabar             # llama a Jev en vivo con LLM_BASE_URL/LLM_MODEL/LLM_API_KEY
  uv run python evals/evaluar.py --comparar           # tabla Ollama vs Azure desde las predicciones grabadas

Las predicciones guardan los logprobs crudos de Jev: la repetición recalcula confianza, ruteo y detector con el
código y la calibración ACTUALES, así que un cambio en umbral, T, detector o política rompe la puerta sin LLM.
No detecta deriva del modelo: para eso se vuelve a grabar. Sale con código 1 si algún umbral falla.
"""
import argparse
import asyncio
import datetime
import hashlib
import importlib
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).parent.parent
sys.path.insert(0, str(RAIZ / "jev"))
sys.path.insert(0, str(RAIZ / "labs"))
from evaluar_empresa import anonimizar, es_local  # noqa: E402
from jev import Jev, Choice, decidir, distribucion, ece, etiquetas, prompt  # noqa: E402

r10 = importlib.import_module("10_router_jev")
h11 = importlib.import_module("11_hitl_router")

GOLDEN = RAIZ / "evals" / "golden" / "golden-v1.jsonl"
UMBRALES = RAIZ / "evals" / "umbrales.json"
REPORTES = RAIZ / "evals" / "reportes"
PERFILES = ("ollama", "azure")
CLAVES_UMBRAL = ("min_exactitud_global", "min_exactitud_clase", "max_ece", "min_pct_automatizado",
                 "max_criticos_automaticos", "min_exactitud_reembolso")


def sha256(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def ruta_predicciones(perfil: str, golden: Path = GOLDEN) -> Path:
    return golden.with_name(f"predicciones-{golden.stem.removeprefix('golden-')}-{perfil}.jsonl")


# ---------- carga y validación ----------
def cargar_golden(ruta: Path, opciones: list[str]) -> list[dict]:
    casos, vistos = [], set()
    for n, linea in enumerate(Path(ruta).read_text(encoding="utf-8").splitlines(), 1):
        if not linea.strip():
            continue
        c = json.loads(linea)
        if c.get("id") in vistos or not c.get("id"):
            raise ValueError(f"línea {n}: id ausente o repetido ({c.get('id')})")
        vistos.add(c["id"])
        if c.get("tipo") == "ruteo":
            if not isinstance(c.get("mensaje"), str) or c.get("destino_esperado") not in ("auto", "humano"):
                raise ValueError(f"{c['id']}: ruteo requiere mensaje y destino_esperado auto|humano")
            if c.get("esperado") is not None and c["esperado"] not in opciones:
                raise ValueError(f"{c['id']}: categoría esperada fuera de las opciones: {c['esperado']}")
            if c["destino_esperado"] == "auto" and c.get("esperado") is None:
                raise ValueError(f"{c['id']}: destino auto exige categoría esperada")
        elif c.get("tipo") == "reembolso":
            if "monto" not in c or not isinstance(c.get("valido"), bool):
                raise ValueError(f"{c['id']}: reembolso requiere monto y valido (bool)")
        else:
            raise ValueError(f"{c['id']}: tipo desconocido {c.get('tipo')!r}")
        if not isinstance(c.get("critico"), bool):
            raise ValueError(f"{c['id']}: critico debe ser bool")
        casos.append(c)
    if len(casos) < 50:
        raise ValueError(f"golden set con {len(casos)} casos: se exigen al menos 50")
    return casos


def cargar_umbrales(ruta: Path) -> dict:
    u = json.loads(Path(ruta).read_text(encoding="utf-8"))
    faltan = [k for k in CLAVES_UMBRAL if k not in u]
    if faltan:
        raise ValueError(f"umbrales incompletos, faltan: {faltan}")
    return u


def huella_prompt(cal: dict) -> str:
    """Hash del prompt real de Jev para esta calibración: si cambia, los logprobs grabados ya no aplican."""
    tipo = Choice(tuple(cal["opciones"]), tuple(cal["descripciones"]) if cal.get("descripciones") else None)
    return hashlib.sha256(json.dumps(prompt("<mensaje>", cal["pregunta"], tipo, cal["rotulo"]),
                                     sort_keys=True).encode()).hexdigest()


def cargar_predicciones(ruta: Path) -> tuple[dict, dict[str, dict]]:
    lineas = [json.loads(x) for x in Path(ruta).read_text(encoding="utf-8").splitlines() if x.strip()]
    if not lineas or "meta" not in lineas[0]:
        raise ValueError(f"{Path(ruta).name}: falta la línea meta")
    return lineas[0]["meta"], {p["id"]: p for p in lineas[1:]}


def verificar_frescura(meta: dict, golden_sha: str, cal: dict, casos: list[dict], preds: dict) -> None:
    if meta["golden_sha256"] != golden_sha:
        raise ValueError("el golden set cambió desde que se grabaron las predicciones: regrábalas con --grabar")
    if meta["prompt_sha256"] != huella_prompt(cal):
        raise ValueError("el prompt de Jev o sus opciones cambiaron: regraba las predicciones con --grabar")
    faltan = [c["id"] for c in casos if c["tipo"] == "ruteo" and c["id"] not in preds]
    if faltan:
        raise ValueError(f"predicciones sin cubrir {len(faltan)} casos: {faltan[:5]}")


# ---------- métricas ----------
def pct(valores: list[float], q: float) -> float:
    s = sorted(valores)
    return s[min(len(s) - 1, math.ceil(q * len(s)) - 1)]


def evaluar(casos: list[dict], preds: dict[str, dict], cal: dict, meta: dict, precios: dict | None = None) -> dict:
    tipo = Choice(tuple(cal["opciones"]), tuple(cal["descripciones"]) if cal.get("descripciones") else None)
    umbral = cal["umbrales"]["0.05"]
    ruteo = [c for c in casos if c["tipo"] == "ruteo"]
    filas = []
    for c in ruteo:
        p = preds[c["id"]]
        d = decidir(tipo, distribucion([(t, lp) for t, lp in p["logprobs"]], etiquetas(tipo), cal["T"]))
        destino, motivo = r10.decidir_ruta(d.valor, d.confianza, umbral, r10.ESPECIALISTAS, r10.es_sospechoso(c["mensaje"]))
        filas.append({"caso": c, "pred": d.valor, "conf": d.confianza, "destino": destino, "motivo": motivo, "ms": p["ms"]})

    con_verdad = [f for f in filas if f["caso"]["esperado"] is not None]
    aciertos = [f["pred"] == f["caso"]["esperado"] for f in con_verdad]
    por_clase = {}
    for clase in cal["opciones"]:
        fs = [a for f, a in zip(con_verdad, aciertos) if f["caso"]["esperado"] == clase]
        por_clase[clase] = {"n": len(fs), "exactitud": round(sum(fs) / len(fs), 4) if fs else None}

    def mal_automatico(f: dict) -> bool:
        c = f["caso"]
        if not c["critico"] or f["destino"] == "humano":
            return False
        return c["destino_esperado"] == "humano" or f["destino"] != r10.ESPECIALISTAS[c["esperado"]]

    criticos_mal = [f["caso"]["id"] for f in filas if mal_automatico(f)]
    reembolsos = [c for c in casos if c["tipo"] == "reembolso"]
    ok_reembolso = [h11.validar_reembolso({"monto": c["monto"]})[0] == c["valido"] for c in reembolsos]
    aceptados = [c["id"] for c in reembolsos if not c["valido"] and h11.validar_reembolso({"monto": c["monto"]})[0]]
    auto = [f for f in filas if f["destino"] != "humano"]
    ms = [f["ms"] for f in filas]
    t_in = statistics.fmean(preds[f["caso"]["id"]].get("tokens_in", 0) for f in filas)
    t_out = statistics.fmean(preds[f["caso"]["id"]].get("tokens_out", 0) for f in filas)
    return {
        "exactitud_global": round(sum(aciertos) / len(aciertos), 4),
        "exactitud_por_clase": por_clase,
        "ece": round(ece([f["conf"] for f in con_verdad], aciertos), 4),
        "pct_automatizado": round(len(auto) / len(filas), 4),
        "automatizado_exactitud": round(sum(f["pred"] == f["caso"]["esperado"] for f in auto if f["caso"]["esperado"]) /
                                        max(1, sum(1 for f in auto if f["caso"]["esperado"])), 4),
        "criticos": {"n_ruteo": sum(f["caso"]["critico"] for f in filas), "n_reembolso": sum(c["critico"] for c in reembolsos),
                     "mal_a_automatico": criticos_mal, "reembolsos_invalidos_aceptados": aceptados},
        "exactitud_reembolso": round(sum(ok_reembolso) / len(ok_reembolso), 4) if ok_reembolso else None,
        "latencia_ms": {"mediana": round(statistics.median(ms)), "p95": round(pct(ms, 0.95))},
        "tokens_por_decision": {"entrada": round(t_in, 1), "salida": round(t_out, 1)},
        "costo_por_1000_usd": costo_1000(t_in, t_out, meta, precios),
        "errores": [{"id": f["caso"]["id"], "esperado": f["caso"]["esperado"], "pred": f["pred"],
                     "conf": round(f["conf"], 3), "destino": f["destino"], "motivo": f["motivo"]}
                    for f in filas if f["caso"]["esperado"] and f["pred"] != f["caso"]["esperado"]],
        "n": {"ruteo": len(filas), "con_verdad": len(con_verdad), "reembolso": len(reembolsos)},
    }


def costo_1000(t_in: float, t_out: float, meta: dict, precios: dict | None) -> float | None:
    """USD por 1,000 decisiones. Local = 0 (sin contar hardware ni energía). Nube: exige precios del usuario."""
    if meta.get("local"):
        return 0.0
    if not precios or precios.get("entrada_1m") is None or precios.get("salida_1m") is None:
        return None  # los precios cambian y dependen del contrato: nunca se asumen
    return round((t_in * precios["entrada_1m"] + t_out * precios["salida_1m"]) * 1000 / 1e6, 4)


def precios_env() -> dict:
    def f(k: str) -> float | None:
        v = os.getenv(k)
        return float(v) if v else None
    return {"entrada_1m": f("PRECIO_ENTRADA_USD_1M"), "salida_1m": f("PRECIO_SALIDA_USD_1M")}


def compuerta(m: dict, u: dict) -> list[str]:
    """Violaciones de umbral; lista vacía = aprueba."""
    v = []
    if m["exactitud_global"] < u["min_exactitud_global"]:
        v.append(f"exactitud global {m['exactitud_global']:.3f} < {u['min_exactitud_global']}")
    for clase, x in m["exactitud_por_clase"].items():
        if x["exactitud"] is not None and x["exactitud"] < u["min_exactitud_clase"]:
            v.append(f"exactitud de {clase} {x['exactitud']:.2f} < {u['min_exactitud_clase']}")
    if m["ece"] > u["max_ece"]:
        v.append(f"ECE {m['ece']:.3f} > {u['max_ece']}")
    if m["pct_automatizado"] < u["min_pct_automatizado"]:
        v.append(f"automatizado {m['pct_automatizado']:.1%} < {u['min_pct_automatizado']:.1%}")
    malos = m["criticos"]["mal_a_automatico"] + m["criticos"]["reembolsos_invalidos_aceptados"]
    if len(malos) > u["max_criticos_automaticos"]:
        v.append(f"{len(malos)} casos críticos a automático (máx. {u['max_criticos_automaticos']}): {malos}")
    if m["exactitud_reembolso"] is not None and m["exactitud_reembolso"] < u["min_exactitud_reembolso"]:
        v.append(f"política de reembolso {m['exactitud_reembolso']:.2f} < {u['min_exactitud_reembolso']}")
    return v


# ---------- grabación en vivo ----------
class JevMedido(Jev):
    """Jev que además conserva los tokens de la última llamada (para el costo). Misma petición que Jev.logprobs."""
    uso: tuple[int, int] = (0, 0)

    async def logprobs(self, estado, pregunta, tipo):
        r = await self._c.chat.completions.create(
            model=self.model, messages=prompt(estado, pregunta, tipo, self.rotulo),
            max_tokens=1, temperature=0, logprobs=True, top_logprobs=20, extra_body=self.extra)
        self.uso = (r.usage.prompt_tokens, r.usage.completion_tokens) if r.usage else (0, 0)
        lp = r.choices[0].logprobs
        return [(x.token, x.logprob) for x in lp.content[0].top_logprobs] if lp and lp.content else []


def origen_publico(url: str) -> str:
    u = urlparse(url)
    return f"{u.scheme}://{u.hostname}"  # sin credenciales, ruta ni query


async def grabar(casos: list[dict], cal: dict, perfil: str, golden: Path) -> Path:
    base = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    local = es_local(base)
    if (perfil == "ollama") != local:
        raise ValueError(f"perfil {perfil!r} no coincide con LLM_BASE_URL ({origen_publico(base)}): "
                         "no se graban datos bajo el perfil equivocado")
    modelo = os.getenv("LLM_MODEL") or cal["modelo"]
    jev = JevMedido(modelo, t=cal["T"], base_url=base, rotulo=cal["rotulo"])
    tipo = Choice(tuple(cal["opciones"]), tuple(cal["descripciones"]) if cal.get("descripciones") else None)
    await jev.logprobs("warm-up", cal["pregunta"], tipo)  # carga en frío del modelo fuera de la medición
    salida = []
    for c in (c for c in casos if c["tipo"] == "ruteo"):
        t0 = time.perf_counter()
        top = await jev.logprobs(anonimizar(c["mensaje"]), cal["pregunta"], tipo)  # PII fuera antes del modelo
        ms = int((time.perf_counter() - t0) * 1000)
        salida.append({"id": c["id"], "logprobs": [[t, round(lp, 6)] for t, lp in top], "ms": ms,
                       "tokens_in": jev.uso[0], "tokens_out": jev.uso[1]})
        print(f"  {c['id']:<14} {ms:>5} ms")
    meta = {"perfil": perfil, "modelo": modelo, "origen": origen_publico(base), "local": local,
            "golden_sha256": sha256(golden), "prompt_sha256": huella_prompt(cal), "T_grabada": cal["T"],
            "fecha": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "n": len(salida)}
    destino = ruta_predicciones(perfil, golden)
    destino.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in [{"meta": meta}, *salida]) + "\n", encoding="utf-8")
    return destino


# ---------- reporte y comparación ----------
def tabla(filas: dict[str, dict | None]) -> str:
    def f(m, k, fmt):
        return fmt(m) if m else "no ejecutado"
    cab = "| Métrica | " + " | ".join(filas) + " |\n|---|" + "---|" * len(filas)
    defs = [("Modelo", lambda m: m["_meta"]["modelo"]),
            ("Exactitud global", lambda m: f"{m['exactitud_global']:.1%}"),
            ("ECE", lambda m: f"{m['ece']:.3f}"),
            ("% automatizado", lambda m: f"{m['pct_automatizado']:.1%}"),
            ("Críticos a automático", lambda m: str(len(m["criticos"]["mal_a_automatico"]))),
            ("Latencia mediana / p95 (ms)", lambda m: f"{m['latencia_ms']['mediana']} / {m['latencia_ms']['p95']}"),
            ("Tokens por decisión (ent/sal)", lambda m: f"{m['tokens_por_decision']['entrada']:.0f} / {m['tokens_por_decision']['salida']:.0f}"),
            ("Costo USD por 1,000 decisiones",
             lambda m: "0 (local, sin contar energía)" if m["costo_por_1000_usd"] == 0.0 else
             "sin precios (define PRECIO_*_USD_1M)" if m["costo_por_1000_usd"] is None else f"{m['costo_por_1000_usd']:.4f}")]
    return cab + "\n" + "\n".join(f"| {n} | " + " | ".join(fn(m) if m else "no ejecutado" for m in filas.values()) + " |"
                                  for n, fn in defs)


def calcular_perfil(perfil: str, casos, golden_sha, cal, golden: Path, precios) -> dict | None:
    ruta = ruta_predicciones(perfil, golden)
    if not ruta.exists():
        return None
    meta, preds = cargar_predicciones(ruta)
    verificar_frescura(meta, golden_sha, cal, casos, preds)
    return {**evaluar(casos, preds, cal, meta, precios if perfil != "ollama" else None), "_meta": meta}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--perfil", choices=PERFILES, default="ollama")
    ap.add_argument("--grabar", action="store_true", help="llama a Jev en vivo y guarda las predicciones")
    ap.add_argument("--comparar", action="store_true", help="tabla entre perfiles con predicciones grabadas")
    ap.add_argument("--golden", type=Path, default=GOLDEN)
    ap.add_argument("--umbrales", type=Path, default=UMBRALES)
    a = ap.parse_args()
    cal = r10.cargar_calibracion(r10.CALIBRACION)
    casos = cargar_golden(a.golden, cal["opciones"])
    if a.grabar:
        print(f"grabando {a.perfil} ({sum(c['tipo'] == 'ruteo' for c in casos)} casos de ruteo)")
        print("guardado:", asyncio.run(grabar(casos, cal, a.perfil, a.golden)))
    golden_sha, precios = sha256(a.golden), precios_env()
    if a.comparar:
        res = {p: calcular_perfil(p, casos, golden_sha, cal, a.golden, precios) for p in PERFILES}
        md = tabla(res)
        faltan = [p for p, m in res.items() if m is None]
        if faltan:
            md += (f"\n\n`no ejecutado`: sin predicciones grabadas para {', '.join(faltan)}. Carga el perfil "
                   "(perfiles/*.env.example) y corre `evals/evaluar.py --perfil <perfil> --grabar`.")
        print(md)
        (a.golden.parent.parent / "COMPARACION.md").write_text(
            "# Comparación por perfil (generado por `evals/evaluar.py --comparar`)\n\n"
            f"Golden `{a.golden.name}` sha256 `{golden_sha[:12]}`, {len(casos)} casos.\n\n{md}\n", encoding="utf-8")
        return 0
    m = calcular_perfil(a.perfil, casos, golden_sha, cal, a.golden, precios)
    if m is None:
        print(f"sin predicciones para {a.perfil}: corre con --grabar", file=sys.stderr)
        return 2
    u = cargar_umbrales(a.umbrales)
    violaciones = compuerta(m, u)
    informe = {"fecha": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
               "perfil": a.perfil, "modo": "vivo" if a.grabar else "repeticion",
               "golden": {"archivo": a.golden.name, "sha256": golden_sha, "casos": len(casos)},
               "calibracion": {"T": cal["T"], "umbral_5pct": cal["umbrales"]["0.05"]},
               "umbrales": u, "metricas": {k: v for k, v in m.items() if k != "_meta"}, "predicciones": m["_meta"],
               "violaciones": violaciones, "aprobado": not violaciones}
    REPORTES.mkdir(parents=True, exist_ok=True)
    salida = REPORTES / f"{datetime.datetime.now().strftime('%Y%m%dT%H%M%S')}-{a.perfil}.json"
    salida.write_text(json.dumps(informe, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"exactitud {m['exactitud_global']:.1%} | ECE {m['ece']:.3f} | automatizado {m['pct_automatizado']:.1%} | "
          f"críticos a automático {len(m['criticos']['mal_a_automatico']) + len(m['criticos']['reembolsos_invalidos_aceptados'])} | "
          f"reembolso {m['exactitud_reembolso']:.0%} | reporte: {salida.relative_to(RAIZ)}")
    for x in m["errores"]:
        print(f"  ✗ {x['id']}: esperado {x['esperado']}, Jev {x['pred']} ({x['conf']}) -> {x['destino']} [{x['motivo']}]")
    for x in violaciones:
        print(f"FALLA: {x}", file=sys.stderr)
    return 1 if violaciones else 0


if __name__ == "__main__":
    sys.exit(main())
