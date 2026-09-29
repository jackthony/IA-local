"""Evaluación de Jev con tickets del dataset de Kaggle (verificado por jev/ingesta.py).

uv run python jev/eval_kaggle.py [idioma]      # idioma por defecto: en (el archivo solo trae en/de)
Muestra estratificada determinista (misma cantidad por cola): las tasas de automatización cambian con la
mezcla real de colas en producción.
"""
import asyncio
import collections
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ingesta  # noqa: E402
from ingesta import muestra  # noqa: E402
from jev import Choice, Jev, brier, calibrar, decidir, distribucion, ece, etiquetas, umbral_auto  # noqa: E402

IDIOMA = sys.argv[1] if len(sys.argv) > 1 else "en"
N_CAL, N_EV, MAX_CHARS = 12, 15, 600  # por cola; cuerpo truncado para acotar latencia en CPU
PREGUNTA = "Classify the ticket into one of these queues"


def cargar() -> list[dict]:
    """CSV verificado (SHA-256 contra su manifiesto) filtrado por idioma."""
    return [f for f in ingesta.cargar("tickets") if f["language"] == IDIOMA]


def texto(f: dict) -> str:
    return f"{f['subject']}\n{f['body'][:MAX_CHARS]}"


async def tops(jev: Jev, fs: list[dict], tipo: Choice, a_texto=texto, pregunta: str = PREGUNTA) -> tuple[list, float]:
    t, out = time.perf_counter(), []
    for f in fs:
        out.append(await jev.logprobs(a_texto(f), pregunta, tipo))
    return out, (time.perf_counter() - t) / len(fs)


def evaluar(tp: list, fs: list[dict], tipo: Choice, t: float, etiqueta: str = "queue") -> tuple[list, list, list]:
    ds = [decidir(tipo, distribucion(x, etiquetas(tipo), t)) for x in tp]
    return ds, [d.valor == f[etiqueta] for d, f in zip(ds, fs)], [d.confianza for d in ds]


async def generativo(fs: list[dict], colas: list[str]) -> tuple[float, int, int]:
    from openai import AsyncOpenAI
    c = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    t, ok, fuera, norm = time.perf_counter(), 0, 0, {q.lower(): q for q in colas}
    for f in fs:
        r = await c.chat.completions.create(model="qwen3:4b-instruct", temperature=0, max_tokens=12, messages=[
            {"role": "user", "content": f"{PREGUNTA}: {', '.join(colas)}. Reply ONLY with the exact queue name.\n"
                                        f"Ticket: {texto(f)}"}])
        v = norm.get(r.choices[0].message.content.strip().strip(".").lower())
        fuera += v is None
        ok += v == f["queue"]
    return (time.perf_counter() - t) / len(fs), ok, fuera


async def main() -> None:
    fs = cargar()
    colas = [q for q, _ in collections.Counter(f["queue"] for f in fs).most_common()]
    tipo = Choice(tuple(colas))
    cal = muestra(fs, N_CAL, semilla=1)
    usados = {id(f) for f in cal}
    ev = muestra([f for f in fs if id(f) not in usados], N_EV, semilla=2)
    print(f"idioma={IDIOMA} | {len(fs)} tickets | {len(colas)} colas | calibración {len(cal)} | evaluación {len(ev)}")

    jev = Jev("qwen3:4b-instruct", rotulo="Ticket")
    tp_cal, lat = await tops(jev, cal, tipo)
    tp_ev, _ = await tops(jev, ev, tipo)
    t = calibrar([(x, etiquetas(tipo), f["queue"]) for x, f in zip(tp_cal, cal)])

    _, ok, conf = evaluar(tp_ev, ev, tipo, 1.0)
    print(f"\nlatencia {lat:.2f} s/decisión | T = {t}")
    print(f"sin calibrar: exactitud {sum(ok) / len(ok):.1%} | ECE {ece(conf, ok):.3f} | Brier {brier(conf, ok):.3f}")
    ds, ok, conf = evaluar(tp_ev, ev, tipo, t)
    print(f"calibrado:    exactitud {sum(ok) / len(ok):.1%} | ECE {ece(conf, ok):.3f} | Brier {brier(conf, ok):.3f}")

    _, ok_c, conf_c = evaluar(tp_cal, cal, tipo, t)
    print("\nautomatización con umbral derivado del error objetivo (elegido en calibración):")
    for err in (0.05, 0.10, 0.20):
        u = umbral_auto(conf_c, ok_c, err)
        auto = [a for c, a in zip(conf, ok) if c >= u]
        print(f"  error objetivo {err:.0%}: umbral {u:.2f} -> automatiza {len(auto) / len(ev):.0%} "
              f"con exactitud {sum(auto) / max(len(auto), 1):.0%} ({sum(auto)}/{len(auto)}); resto a humano")

    print("\nexactitud por cola (evaluación):")
    por = collections.defaultdict(list)
    confus = collections.Counter()
    for d, f in zip(ds, ev):
        por[f["queue"]].append(d.valor == f["queue"])
        if d.valor != f["queue"]:
            confus[(f["queue"], d.valor)] += 1
    for q in colas:
        print(f"  {q:34} {sum(por[q])}/{len(por[q])}")
    print("confusiones más frecuentes:", [f"{a} -> {b} ({n})" for (a, b), n in confus.most_common(5)])

    lat_g, ok_g, fuera = await generativo(ev, colas)
    print(f"\nLLM generativo: {lat_g:.2f} s/ticket | exactitud {ok_g / len(ev):.1%} | fuera de formato {fuera}/{len(ev)} "
          f"| sin confianza")
    print(f"Jev 4B:         {lat:.2f} s/ticket | exactitud {sum(ok) / len(ok):.1%} | fuera de formato 0 | confianza calibrada")


if __name__ == "__main__":
    asyncio.run(main())
