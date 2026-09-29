"""Diagnóstico de la exactitud baja en tickets de Kaggle (spec: openspec/specs/jev-datos).

Sobre la MISMA muestra compara: Jev 4B sin/con descripciones, 8B con descripciones y un Naive Bayes
(techo de aprendibilidad desde el texto). Recalcula también con colas agrupadas.
uv run python jev/diagnostico_kaggle.py
"""
import asyncio
import collections
import math
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from eval_kaggle import PREGUNTA, cargar, evaluar, texto, tops  # noqa: E402
from ingesta import muestra  # noqa: E402
from jev import Choice, Jev, calibrar, ece, etiquetas, umbral_auto  # noqa: E402

N_CAL, N_EV = 8, 12  # por cola (80 + 120): acota el tiempo del 8B en CPU
# Redactadas por nosotros (el dataset no define las colas): es lo que haría el equipo de soporte real.
DESCRIPCIONES = {
    "Technical Support": "errors, bugs, crashes, integrations or configuration problems using our software/product",
    "Product Support": "how product features work, usage questions, compatibility, product recommendations",
    "Customer Service": "account or order help, complaints, feedback, subscription or delivery issues",
    "IT Support": "internal IT infrastructure: hardware, network, VPN, servers, security, employee access",
    "Billing and Payments": "invoices, charges, payments, refunds, billing errors",
    "Returns and Exchanges": "returning or exchanging purchased products, replacements, return shipping",
    "Service Outages and Maintenance": "service down or unavailable, outages, degraded performance, maintenance",
    "Sales and Pre-Sales": "quotes, pricing for new purchases, demos, information before buying",
    "Human Resources": "employment, payroll, benefits, leave, hiring, HR policies",
    "General Inquiry": "general questions that fit no other queue",
}
GRUPOS = {"Technical Support": "soporte_tecnico", "IT Support": "soporte_tecnico", "Product Support": "soporte_tecnico",
          "Customer Service": "atencion_general", "General Inquiry": "atencion_general"}


class NaiveBayes:
    """Multinomial con suavizado de Laplace. Solo stdlib."""

    def fit(self, textos: list[str], etiquetas_: list[str]) -> "NaiveBayes":
        self.docs = collections.Counter(etiquetas_)
        self.palabras = collections.defaultdict(collections.Counter)
        for t, e in zip(textos, etiquetas_):
            self.palabras[e].update(re.findall(r"\w+", t.lower()))
        self.vocab = {w for c in self.palabras.values() for w in c}
        self.totales = {e: sum(c.values()) for e, c in self.palabras.items()}
        return self

    def predecir(self, t: str) -> str:
        tokens = [w for w in re.findall(r"\w+", t.lower()) if w in self.vocab]
        n, v = sum(self.docs.values()), len(self.vocab)
        return max(self.docs, key=lambda e: math.log(self.docs[e] / n) + sum(
            math.log((self.palabras[e][w] + 1) / (self.totales[e] + v)) for w in tokens))


def agrupada(pred: list[str], real: list[str]) -> float:
    return sum(GRUPOS.get(p, p) == GRUPOS.get(r, r) for p, r in zip(pred, real)) / len(real)


async def config(nombre: str, jev: Jev, tipo: Choice, cal: list, ev: list) -> dict:
    t0 = time.perf_counter()
    tp_cal, _ = await tops(jev, cal, tipo)
    tp_ev, lat = await tops(jev, ev, tipo)
    t = calibrar([(x, etiquetas(tipo), f["queue"]) for x, f in zip(tp_cal, cal)])
    ds, ok, conf = evaluar(tp_ev, ev, tipo, t)
    _, ok_c, conf_c = evaluar(tp_cal, cal, tipo, t)
    u = umbral_auto(conf_c, ok_c, 0.10)
    auto = [a for c, a in zip(conf, ok) if c >= u]
    fila = {"config": nombre, "exactitud": sum(ok) / len(ok), "agrupada": agrupada([d.valor for d in ds], [f["queue"] for f in ev]),
            "ece": ece(conf, ok), "T": t, "auto@10%": len(auto) / len(ev),
            "exact_auto": sum(auto) / max(len(auto), 1), "s/dec": lat}
    print(f"  {nombre}: listo en {time.perf_counter() - t0:.0f}s -> {fila}", flush=True)
    return fila


async def main() -> None:
    fs = cargar()
    colas = [q for q, _ in collections.Counter(f["queue"] for f in fs).most_common()]
    cal = muestra(fs, N_CAL, semilla=1)
    usados = {id(f) for f in cal}
    ev = muestra([f for f in fs if id(f) not in usados], N_EV, semilla=2)
    usados |= {id(f) for f in ev}
    print(f"{len(fs)} tickets | {len(colas)} colas | calibración {len(cal)} | evaluación {len(ev)}", flush=True)

    entren = [f for f in fs if id(f) not in usados]
    nb = NaiveBayes().fit([texto(f) for f in entren], [f["queue"] for f in entren])
    pred_nb = [nb.predecir(texto(f)) for f in ev]
    real = [f["queue"] for f in ev]
    filas = [{"config": f"NaiveBayes ({len(entren)} ej. entrenamiento)", "exactitud": sum(p == r for p, r in zip(pred_nb, real)) / len(ev),
              "agrupada": agrupada(pred_nb, real)}]
    print(f"  NaiveBayes: {filas[0]}", flush=True)

    sin, con = Choice(tuple(colas)), Choice(tuple(colas), tuple(DESCRIPCIONES[q] for q in colas))
    filas.append(await config("Jev 4B sin descripciones", Jev("qwen3:4b-instruct", rotulo="Ticket"), sin, cal, ev))
    filas.append(await config("Jev 4B con descripciones", Jev("qwen3:4b-instruct", rotulo="Ticket"), con, cal, ev))
    filas.append(await config("Jev 8B con descripciones",
                              Jev("qwen3:8b", extra={"reasoning_effort": "none"}, rotulo="Ticket"), con, cal, ev))

    print("\n| config | exactitud | colas agrupadas | ECE cal. | T | auto @10% err | exact. en auto | s/decisión |")
    print("|---|---|---|---|---|---|---|---|")
    for r in filas:
        g = lambda k, f="{:.0%}": f.format(r[k]) if k in r else "-"
        print(f"| {r['config']} | {g('exactitud')} | {g('agrupada')} | {g('ece', '{:.3f}')} | {g('T', '{}')} | "
              f"{g('auto@10%')} | {g('exact_auto')} | {g('s/dec', '{:.2f}')} |")


if __name__ == "__main__":
    asyncio.run(main())
