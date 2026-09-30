"""Experimento: puntuar el primer token del NOMBRE de cada opción vs etiquetas A/B/C/D."""
import asyncio, json, math, sys, time
sys.path.insert(0, "jev")
from openai import AsyncOpenAI
from jev import calibrar, ece, brier
D = json.load(open("jev/tickets.json", encoding="utf-8"))
AREAS = D["areas"]
c = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

async def top(texto):
    r = await c.chat.completions.create(model="qwen3:4b-instruct", temperature=0, max_tokens=1, logprobs=True, top_logprobs=20,
        messages=[{"role": "user", "content": f"Clasifica el ticket en una de estas áreas: {', '.join(AREAS)}. "
                   f"Responde SOLO con el nombre del área, sin explicar.\nTicket: {texto}"}])
    return [(x.token, x.logprob) for x in r.choices[0].logprobs.content[0].top_logprobs]

def dist(tp, t=1.0):
    masa = dict.fromkeys(AREAS, 0.0)
    for tok, lp in tp:
        k = tok.strip().lower()
        hits = [a for a in AREAS if k and a.startswith(k)]
        if len(hits) == 1:  # prefijo inequívoco
            masa[hits[0]] += math.exp(lp / t)
    s = sum(masa.values())
    return {a: (m / s if s else 1 / len(AREAS)) for a, m in masa.items()}

async def main():
    t0 = time.perf_counter()
    cal = [await top(x["texto"]) for x in D["calibracion"]]
    ev = [await top(x["texto"]) for x in D["evaluacion"]]
    lat = (time.perf_counter() - t0) / 40
    print("primeros tokens vistos (ev[0]):", [t for t, _ in ev[0][:6]])
    # calibrar reutiliza distribucion() por etiquetas: aquí ajusto T con grilla propia sobre dist()
    def nll(t): return -sum(math.log(max(dist(tp, t)[x["area"]], 1e-12)) for tp, x in zip(cal, D["calibracion"]))
    T = min((i / 4 for i in range(1, 81)), key=nll)
    for nombre, t in (("crudo", 1.0), (f"T={T}", T)):
        ds = [dist(tp, t) for tp in ev]
        pred = [max(d, key=d.get) for d in ds]
        ok = [p == x["area"] for p, x in zip(pred, D["evaluacion"])]
        conf = [max(d.values()) for d in ds]
        print(f"{nombre:7} exactitud {sum(ok)}/20 | ECE {ece(conf, ok):.3f} | Brier {brier(conf, ok):.3f} | conf media {sum(conf)/20:.3f} | {lat:.2f} s/dec")
asyncio.run(main())
