"""Jev local: decisiones tipadas con probabilidad calibrada sobre modelos locales ("System One").

En vez de generar texto, cada pregunta tiene un tipo (Choice / Score / Noul). Se pide 1 token y se lee
la distribución del modelo (logprobs) sobre el primer token del nombre de cada opción:
- la salida siempre está en el dominio (cero errores estructurales),
- la confianza sale de probabilidades reales, calibrables con temperature scaling,
- ~1-2 s por decisión en CPU, frente a decenas de segundos de un agente.

Uso:
    jev = Jev()
    d = await jev.preguntar(ticket, "¿Qué área lo atiende?", Choice(("facturacion", "tecnico")))
    d.valor, d.confianza, ruta(d.confianza)
"""
import asyncio
import math
import os
import unicodedata
from dataclasses import dataclass

from openai import AsyncOpenAI

MAX_OPCIONES = 26  # ponytail: tope práctico para el prompt. Jev admite 255.


@dataclass(frozen=True)
class Choice:
    opciones: tuple[str, ...]
    descripciones: tuple[str, ...] | None = None  # una por opción: qué entra en cada una

    def __post_init__(self) -> None:
        if not 2 <= len(self.opciones) <= MAX_OPCIONES:
            raise ValueError(f"Choice requiere entre 2 y {MAX_OPCIONES} opciones")
        if self.descripciones is not None and len(self.descripciones) != len(self.opciones):
            raise ValueError("descripciones debe tener una entrada por opción")


@dataclass(frozen=True)
class Score:
    niveles: int  # escala 1..niveles

    def __post_init__(self) -> None:
        if not 2 <= self.niveles <= 9:  # dígitos 1..9 = 1 token
            raise ValueError("Score requiere entre 2 y 9 niveles")


@dataclass(frozen=True)
class Noul:
    """Pregunta sí/no. Valor = P(sí)."""


Tipo = Choice | Score | Noul


@dataclass(frozen=True)
class Decision:
    valor: str | float
    probs: dict
    confianza: float


def etiquetas(tipo: Tipo) -> list[str]:
    """Las opciones son su propio nombre: se puntúa el primer token con que el modelo las escribiría."""
    if isinstance(tipo, Score):
        return [str(i) for i in range(1, tipo.niveles + 1)]
    return ["Sí", "No"] if isinstance(tipo, Noul) else list(tipo.opciones)


def prompt(estado: str, pregunta: str, tipo: Tipo, rotulo: str = "Texto") -> list[dict]:
    """Un mensaje: instrucción + opciones + regla + '<rotulo>: estado'.

    Medido (40 tickets, qwen3:4b): esta forma 37/40; pregunta interrogativa sin rótulo 31/40. El prompt
    es un hiperparámetro: redacta `pregunta` como instrucción ("Clasifica el ticket en una de estas áreas")
    y valida con tu dataset.
    """
    if isinstance(tipo, Score):
        texto = f"{pregunta} Responde SOLO con un número del 1 (mínimo) al {tipo.niveles} (máximo)."
    elif isinstance(tipo, Noul):
        texto = f"{pregunta} Responde SOLO Sí o No, sin explicar."
    elif tipo.descripciones:
        lineas = "\n".join(f"- {o}: {d}" for o, d in zip(tipo.opciones, tipo.descripciones))
        texto = f"{pregunta}:\n{lineas}\nResponde SOLO con el nombre exacto de la opción, sin explicar."
    else:
        texto = f"{pregunta}: {', '.join(tipo.opciones)}. Responde SOLO con el nombre exacto, sin explicar."
    return [{"role": "user", "content": f"{texto}\n{rotulo}: {estado}"}]


def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.strip().lower()) if unicodedata.category(c) != "Mn")


def distribucion(top: list[tuple[str, float]], opciones: list[str], t: float = 1.0) -> dict[str, float]:
    """Masa por opción (tokens que son prefijo inequívoco del nombre) y luego p ∝ masa^(1/t).

    La temperatura va sobre la masa agregada: escalar por token favorecía opciones con más variantes
    tokenizadas ("fact", " fact", "Fact") y cambiaba el argmax. Sin masa válida -> uniforme.
    """
    nombres = {o: _norm(o) for o in opciones}
    masa = dict.fromkeys(opciones, 0.0)
    for token, lp in top:
        k = _norm(token)
        hits = [o for o, n in nombres.items() if k and n.startswith(k)]
        if len(hits) == 1:
            masa[hits[0]] += math.exp(lp)
    if not any(masa.values()):
        return {o: 1 / len(opciones) for o in opciones}
    escalada = {o: m ** (1 / t) for o, m in masa.items()}
    total = sum(escalada.values())
    return {o: m / total for o, m in escalada.items()}


def decidir(tipo: Tipo, dist: dict[str, float]) -> Decision:
    if isinstance(tipo, Noul):
        p = dist["Sí"]
        return Decision(p, {"si": p, "no": 1 - p}, max(p, 1 - p))
    if isinstance(tipo, Score):
        probs = {int(e): p for e, p in dist.items()}
        return Decision(sum(n * p for n, p in probs.items()), probs, max(probs.values()))
    valor = max(dist, key=dist.get)
    return Decision(valor, dict(dist), dist[valor])


def calibrar(ejemplos: list[tuple[list[tuple[str, float]], list[str], str]]) -> float:
    """Temperature scaling: T de la grilla 0.25..20 que minimiza NLL. ejemplos: (top_logprobs, etiquetas, correcta)."""
    def nll(t: float) -> float:
        return -sum(math.log(max(distribucion(top, etqs, t)[ok], 1e-12)) for top, etqs, ok in ejemplos)
    return min((i / 4 for i in range(1, 81)), key=nll)


def ece(confianzas: list[float], aciertos: list[bool], bins: int = 10) -> float:
    """Expected Calibration Error: |exactitud - confianza| promedio ponderado por bin."""
    total = 0.0
    for b in range(bins):
        idx = [i for i, c in enumerate(confianzas) if b / bins < c <= (b + 1) / bins or (b == 0 and c == 0)]
        if idx:
            acc = sum(aciertos[i] for i in idx) / len(idx)
            conf = sum(confianzas[i] for i in idx) / len(idx)
            total += len(idx) / len(confianzas) * abs(acc - conf)
    return total


def brier(confianzas: list[float], aciertos: list[bool]) -> float:
    """Brier top-label: media de (confianza - acierto)². 0 = perfecto."""
    return sum((c - a) ** 2 for c, a in zip(confianzas, aciertos)) / len(confianzas)


def ruta(confianza: float, auto: float = 0.9, humano: float = 0.6) -> str:
    return "auto" if confianza >= auto else "escalar" if confianza >= humano else "humano"


def umbral_auto(confianzas: list[float], aciertos: list[bool], error_max: float = 0.05) -> float:
    """Menor umbral observado cuyo tramo >= umbral cumple exactitud >= 1 - error_max. > 1 = nunca auto."""
    mejor = 1.01
    for c in sorted(set(confianzas), reverse=True):
        tramo = [a for x, a in zip(confianzas, aciertos) if x >= c]
        if sum(tramo) / len(tramo) >= 1 - error_max:
            mejor = c
    return mejor


class Jev:
    def __init__(self, model: str | None = None, t: float = 1.0, base_url: str | None = None,
                 extra: dict | None = None, rotulo: str = "Texto") -> None:
        self.model = model or os.getenv("LLM_MODEL", "qwen3:4b-instruct")
        self.t = t
        self.extra = extra  # extra_body del servidor, p. ej. {"reasoning_effort": "none"} para qwen3:8b
        self.rotulo = rotulo  # cómo se presenta el estado: "Ticket", "Correo", "Factura"...
        self._c = AsyncOpenAI(base_url=base_url or os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
                              api_key=os.getenv("LLM_API_KEY", "ollama"))

    async def logprobs(self, estado: str, pregunta: str, tipo: Tipo) -> list[tuple[str, float]]:
        r = await self._c.chat.completions.create(
            model=self.model, messages=prompt(estado, pregunta, tipo, self.rotulo),
            max_tokens=1, temperature=0, logprobs=True, top_logprobs=20, extra_body=self.extra)
        lp = r.choices[0].logprobs
        return [(x.token, x.logprob) for x in lp.content[0].top_logprobs] if lp and lp.content else []

    async def preguntar(self, estado: str, pregunta: str, tipo: Tipo) -> Decision:
        return decidir(tipo, distribucion(await self.logprobs(estado, pregunta, tipo), etiquetas(tipo), self.t))

    async def lote(self, estado: str, preguntas: dict[str, tuple[str, Tipo]]) -> dict[str, Decision]:
        """Todas las preguntas en paralelo (en GPU/vLLM; Ollama en CPU las serializa)."""
        ds = await asyncio.gather(*(self.preguntar(estado, p, t) for p, t in preguntas.values()))
        return dict(zip(preguntas, ds))


async def cascada(jevs: list[Jev], estado: str, pregunta: str, tipo: Tipo,
                  auto: float = 0.9) -> tuple[Decision, str]:
    """Modelo chico -> grande -> humano. Devuelve (decisión, 'auto:<modelo>' | 'humano')."""
    for j in jevs:
        d = await j.preguntar(estado, pregunta, tipo)
        if d.confianza >= auto:
            return d, f"auto:{j.model}"
    return d, "humano"
