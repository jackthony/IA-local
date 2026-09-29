"""Demo de valor de Jev local: triage de tickets con decisiones tipadas y calibradas.

uv run python jev/demo_triage.py
Mide: exactitud y calibración (antes/después), cascada 4B -> 8B -> humano, lote de preguntas,
y comparación contra un LLM generando texto para la misma tarea.
"""
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from jev import (Choice, Jev, Noul, Score, brier, calibrar, decidir, distribucion, ece,  # noqa: E402
                 etiquetas, umbral_auto)

DATOS = json.loads((Path(__file__).parent / "tickets.json").read_text(encoding="utf-8"))
AREA = Choice(tuple(DATOS["areas"]))
PREGUNTA = "Clasifica el ticket en una de estas áreas"
ERROR_MAX = 0.05  # error tolerado en decisiones automáticas; el umbral se deriva de esto


async def logprobs(jev: Jev, tickets: list[dict]) -> tuple[list, float]:
    t, out = time.perf_counter(), []
    for tk in tickets:  # secuencial: Ollama en CPU serializa igual; latencia por decisión honesta
        out.append(await jev.logprobs(tk["texto"], PREGUNTA, AREA))
    return out, (time.perf_counter() - t) / len(tickets)


def metricas(tops: list, tickets: list[dict], t: float) -> tuple[list, dict]:
    ds = [decidir(AREA, distribucion(top, etiquetas(AREA), t)) for top in tops]
    ok = [d.valor == tk["area"] for d, tk in zip(ds, tickets)]
    conf = [d.confianza for d in ds]
    return ds, {"exactitud": sum(ok) / len(ok), "ece": ece(conf, ok), "brier": brier(conf, ok),
                "conf_media": sum(conf) / len(conf)}


def ejemplos(tops: list, tickets: list[dict]) -> list:
    return [(top, etiquetas(AREA), tk["area"]) for top, tk in zip(tops, tickets)]


def fmt(m: dict) -> str:
    return " | ".join(f"{k} {v:.3f}" for k, v in m.items())


async def llm_generativo(tickets: list[dict]) -> tuple[float, int, int]:
    """Misma tarea con un LLM generando texto libre: latencia, aciertos y respuestas fuera de formato."""
    from openai import AsyncOpenAI
    c = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    t, ok, fuera = time.perf_counter(), 0, 0
    for tk in tickets:
        r = await c.chat.completions.create(model="qwen3:4b-instruct", messages=[{"role": "user", "content":
            f"Clasifica el ticket en una de estas áreas: {', '.join(AREA.opciones)}. "
            f"Responde SOLO con el nombre del área, sin explicar.\nTicket: {tk['texto']}"}], temperature=0)
        txt = r.choices[0].message.content.strip().strip(".").lower()
        fuera += txt not in AREA.opciones  # comparación justa: coincidencia exacta con el dominio
        ok += txt == tk["area"]
    return (time.perf_counter() - t) / len(tickets), ok, fuera


async def main() -> None:
    cal, ev = DATOS["calibracion"], DATOS["evaluacion"]
    j4 = Jev("qwen3:4b-instruct", rotulo="Ticket")
    j8 = Jev("qwen3:8b", extra={"reasoning_effort": "none"}, rotulo="Ticket")

    print("== 1. Jev 4B: calibración ==")
    cal4, lat4 = await logprobs(j4, cal)
    ev4, _ = await logprobs(j4, ev)
    t4 = calibrar(ejemplos(cal4, cal))
    _, crudo = metricas(ev4, ev, 1.0)
    ds4, calib = metricas(ev4, ev, t4)
    print(f"latencia media {lat4:.2f} s/decisión | T ajustada = {t4}")
    print(f"sin calibrar: {fmt(crudo)}\ncalibrado:    {fmt(calib)}")

    print(f"\n== 2. Cascada 4B -> 8B -> humano (umbral por error objetivo <= {ERROR_MAX:.0%}) ==")
    cal8, lat8 = await logprobs(j8, cal)
    t8 = calibrar(ejemplos(cal8, cal))
    umbrales = {}
    for nombre, tops, t in (("4B", cal4, t4), ("8B", cal8, t8)):
        ds_cal, _ = metricas(tops, cal, t)
        umbrales[nombre] = umbral_auto([d.confianza for d in ds_cal],
                                       [d.valor == tk["area"] for d, tk in zip(ds_cal, cal)], ERROR_MAX)
    print(f"8B: latencia {lat8:.2f} s/decisión | T = {t8} | umbrales elegidos en calibración: {umbrales}")
    rutas, aciertos = {"auto:4B": 0, "auto:8B": 0, "humano": 0}, {"auto:4B": 0, "auto:8B": 0, "humano": 0}
    for d4, tk in zip(ds4, ev):
        d, r = d4, "auto:4B"
        if d4.confianza < umbrales["4B"]:
            d = decidir(AREA, distribucion(await j8.logprobs(tk["texto"], PREGUNTA, AREA), etiquetas(AREA), t8))
            r = "auto:8B" if d.confianza >= umbrales["8B"] else "humano"
        rutas[r] += 1
        aciertos[r] += d.valor == tk["area"]
        marca = "OK " if d.valor == tk["area"] else "ERR"
        print(f"  {marca} [{r:7}] conf {d.confianza:.2f} -> {d.valor:12} (real {tk['area']:12}) | {tk['texto'][:46]}")
    auto = rutas["auto:4B"] + rutas["auto:8B"]
    ok_auto = aciertos["auto:4B"] + aciertos["auto:8B"]
    print(f"rutas: {rutas} | exactitud en auto: {ok_auto}/{auto} = {ok_auto / max(auto, 1):.0%} "
          f"| resuelto sin humano: {auto / len(ev):.0%}")
    print("  ojo: T y umbral se ajustan con 20 ejemplos; en prod usar cientos y un set de validación aparte.")

    print("\n== 3. Lote tipado (área + urgencia + molestia) ==")
    for tk in ev[:3]:
        t = time.perf_counter()
        r = await j4.lote(tk["texto"], {
            "area": (PREGUNTA, AREA),
            "urgencia": ("Califica la urgencia del ticket.", Score(5)),
            "molesto": ("¿El cliente está molesto?", Noul()),
        })
        print(f"  {time.perf_counter() - t:.1f}s | área={r['area'].valor} ({r['area'].confianza:.2f}) "
              f"urgencia={r['urgencia'].valor:.1f}/5 P(molesto)={r['molesto'].valor:.2f} | {tk['texto'][:50]}")

    print("\n== 4. Valor: mismo triage con LLM generando texto ==")
    lat_g, ok_g, fuera = await llm_generativo(ev)
    print(f"LLM generativo: {lat_g:.2f} s/ticket | exactitud {ok_g}/{len(ev)} | fuera de formato {fuera}/{len(ev)} | sin confianza")
    print(f"Jev 4B:         {lat4:.2f} s/ticket | exactitud {calib['exactitud']:.0%} | fuera de formato 0 (por construcción) "
          f"| confianza calibrada (ECE {calib['ece']:.3f})")


if __name__ == "__main__":
    asyncio.run(main())
