"""Evaluación de Jev con etiquetas limpias: Bitext Customer Support (spec: openspec/specs/jev-datos).

Ruteo por categoría (11) sobre la misma muestra: Naive Bayes (techo supervisado), Jev 4B sin/con
descripciones, Jev 8B con descripciones y LLM generativo 4B. Descripciones derivadas de los datos
(intents de cada categoría), no inventadas.
uv run python jev/eval_bitext.py
"""
import asyncio
import collections
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ingesta  # noqa: E402
from diagnostico_kaggle import NaiveBayes  # noqa: E402
from eval_kaggle import evaluar, tops  # noqa: E402
from jev import Choice, Jev, calibrar, ece, etiquetas, umbral_auto  # noqa: E402

N_CAL, N_EV = 15, 20  # por categoría
PREGUNTA = "Classify the customer message into one of these categories"


def texto(f: dict) -> str:
    return f["instruction"]


async def config(nombre: str, jev: Jev, tipo: Choice, cal: list, ev: list) -> dict:
    t0 = time.perf_counter()
    tp_cal, _ = await tops(jev, cal, tipo, texto, PREGUNTA)
    tp_ev, lat = await tops(jev, ev, tipo, texto, PREGUNTA)
    t = calibrar([(x, etiquetas(tipo), f["cat"]) for x, f in zip(tp_cal, cal)])
    _, ok, conf = evaluar(tp_ev, ev, tipo, t, "cat")
    _, ok_c, conf_c = evaluar(tp_cal, cal, tipo, t, "cat")
    fila = {"config": nombre, "exactitud": sum(ok) / len(ok), "ece": ece(conf, ok), "T": t, "s/dec": lat}
    for err in (0.05, 0.10):
        u = umbral_auto(conf_c, ok_c, err)
        auto = [a for c, a in zip(conf, ok) if c >= u]
        fila[f"auto@{err:.0%}"] = len(auto) / len(ev)
        fila[f"exact@{err:.0%}"] = sum(auto) / max(len(auto), 1)
    print(f"  {nombre}: {time.perf_counter() - t0:.0f}s -> {fila}", flush=True)
    return fila


async def generativo(ev: list, tipo: Choice) -> dict:
    from openai import AsyncOpenAI
    c = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    lineas = "\n".join(f"- {o}: {d}" for o, d in zip(tipo.opciones, tipo.descripciones))
    t, ok, fuera = time.perf_counter(), 0, 0
    for f in ev:
        r = await c.chat.completions.create(model="qwen3:4b-instruct", temperature=0, max_tokens=8, messages=[
            {"role": "user", "content": f"{PREGUNTA}:\n{lineas}\nReply ONLY with the exact category name.\n"
                                        f"Message: {texto(f)}"}])
        v = r.choices[0].message.content.strip().strip(".").lower()
        fuera += v not in tipo.opciones
        ok += v == f["cat"]
    return {"config": "LLM generativo 4B (con descripciones)", "exactitud": ok / len(ev),
            "s/dec": (time.perf_counter() - t) / len(ev), "fuera": fuera}


async def main() -> None:
    fs = ingesta.cargar("bitext")  # re-verifica SHA-256 contra data/MANIFEST-bitext.json
    for f in fs:
        f["cat"] = f["category"].lower()  # nombres legibles para el modelo; se puntúan por prefijo
    cats = [c for c, _ in collections.Counter(f["cat"] for f in fs).most_common()]
    cal = ingesta.muestra(fs, N_CAL, semilla=1, etiqueta="cat")
    usados = {id(f) for f in cal}
    ev = ingesta.muestra([f for f in fs if id(f) not in usados], N_EV, semilla=2, etiqueta="cat")
    usados |= {id(f) for f in ev}
    entren = [f for f in fs if id(f) not in usados]
    intents = collections.defaultdict(set)
    for f in entren:
        intents[f["cat"]].add(f["intent"].replace("_", " "))
    desc = tuple("intents: " + ", ".join(sorted(intents[c])) for c in cats)
    print(f"{len(fs)} mensajes | {len(cats)} categorías | calibración {len(cal)} | evaluación {len(ev)}", flush=True)
    for c, d in zip(cats, desc):
        print(f"  {c}: {d}")

    nb = NaiveBayes().fit([texto(f) for f in entren], [f["cat"] for f in entren])
    filas = [{"config": f"NaiveBayes ({len(entren)} ej.)",
              "exactitud": sum(nb.predecir(texto(f)) == f["cat"] for f in ev) / len(ev)}]
    print(f"  {filas[0]}", flush=True)

    sin, con = Choice(tuple(cats)), Choice(tuple(cats), desc)
    j4 = Jev("qwen3:4b-instruct", rotulo="Message")
    filas.append(await config("Jev 4B sin descripciones", j4, sin, cal, ev))
    filas.append(await config("Jev 4B con descripciones", j4, con, cal, ev))
    filas.append(await config("Jev 8B con descripciones",
                              Jev("qwen3:8b", extra={"reasoning_effort": "none"}, rotulo="Message"), con, cal, ev))
    filas.append(await generativo(ev, con))
    print(f"  {filas[-1]}", flush=True)

    print("\n| config | exactitud | ECE | T | auto @5% (exact.) | auto @10% (exact.) | s/decisión |")
    print("|---|---|---|---|---|---|---|")
    for r in filas:
        g = lambda k, f="{:.0%}": f.format(r[k]) if k in r else "-"
        a5 = f"{g('auto@5%')} ({g('exact@5%')})" if "auto@5%" in r else "-"
        a10 = f"{g('auto@10%')} ({g('exact@10%')})" if "auto@10%" in r else "-"
        print(f"| {r['config']} | {g('exactitud')} | {g('ece', '{:.3f}')} | {g('T', '{}')} | {a5} | {a10} | {g('s/dec', '{:.2f}')} |")


if __name__ == "__main__":
    asyncio.run(main())
