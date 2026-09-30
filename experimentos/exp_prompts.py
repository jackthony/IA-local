"""Plantillas de prompt como hiperparámetro: exactitud/ECE sobre los 40 tickets."""
import asyncio, json, sys
sys.path.insert(0, "jev")
from openai import AsyncOpenAI
from jev import distribucion, ece
D = json.load(open("jev/tickets.json", encoding="utf-8"))
A = D["areas"]; OPC = ", ".join(A)
T = D["calibracion"] + D["evaluacion"]
c = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
PLANTILLAS = {
    "actual": lambda x: f"¿Qué área debe atender este ticket? Opciones: {OPC}. Responde SOLO con la opción exacta, sin explicar.\n{x}",
    "rotulo": lambda x: f"¿Qué área debe atender este ticket? Opciones: {OPC}. Responde SOLO con la opción exacta, sin explicar.\nTicket: {x}",
    "experimento": lambda x: f"Clasifica el ticket en una de estas áreas: {OPC}. Responde SOLO con el nombre del área, sin explicar.\nTicket: {x}",
    "texto_primero": lambda x: f"Ticket: {x}\n¿Qué área debe atenderlo? Opciones: {OPC}. Responde SOLO con la opción exacta.",
}
async def main():
    for nombre, p in PLANTILLAS.items():
        ok, conf = [], []
        for tk in T:
            r = await c.chat.completions.create(model="qwen3:4b-instruct", temperature=0, max_tokens=1, logprobs=True,
                                                top_logprobs=20, messages=[{"role": "user", "content": p(tk["texto"])}])
            d = distribucion([(x.token, x.logprob) for x in r.choices[0].logprobs.content[0].top_logprobs], A)
            v = max(d, key=d.get); ok.append(v == tk["area"]); conf.append(d[v])
        print(f"{nombre:14} exactitud {sum(ok)}/40 | ECE {ece(conf, ok):.3f}")
asyncio.run(main())
