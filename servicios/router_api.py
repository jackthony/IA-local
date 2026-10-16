"""Jev como servicio de decisión (System 1): POST /v1/decidir (spec: openspec/changes/produccion).

.venv/bin/uvicorn --app-dir servicios router_api:app --host 0.0.0.0 --port 8000
"""
import importlib
import os
import sys
from pathlib import Path

from opentelemetry import trace
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

RAIZ = Path(__file__).resolve().parent.parent
for d in ("jev", "labs", "servicios"):
    sys.path.insert(0, str(RAIZ / d))
from seguridad import BearerAuth, token_requerido  # noqa: E402
from telemetria import configurar  # noqa: E402

configurar("router-api")
from evaluar_empresa import anonimizar  # noqa: E402
from jev import Choice, Jev, decidir as decidir_jev, distribucion, etiquetas  # noqa: E402
from openai import OpenAIError  # noqa: E402
from typesafe import TypeSafeError, TypeSafeJev  # noqa: E402

r10 = importlib.import_module("10_router_jev")
TOKEN = token_requerido("API_TOKEN")
MAX_CHARS = 4000
CAL = r10.cargar_calibracion(r10.CALIBRACION)
TIPO = Choice(tuple(CAL["opciones"]), tuple(CAL["descripciones"]) if CAL.get("descripciones") else None)
# Una decisión tarda ~1 s: esperar más es una caída. Sin reintentos ocultos; el cliente decide si reintenta.
JEV = Jev(CAL["modelo"], t=CAL["T"], rotulo=CAL["rotulo"], timeout=float(os.getenv("JEV_TIMEOUT_S", "10")), reintentos=0)
tracer = trace.get_tracer("router-api")


class Cupo:
    """Tope de consultas al juez remoto por proceso (se reinicia al reiniciar). Es un freno de gasto, no un límite de
    facturación: el tope real se fija también en la consola del proveedor."""

    def __init__(self, maximo: int) -> None:
        self.maximo, self.usadas = maximo, 0

    def tomar(self) -> bool:
        if self.usadas >= self.maximo:
            return False
        self.usadas += 1
        return True


# Segundo juez opcional (JEV_SEGUNDO=typesafe + TYPESAFE_API_KEY): solo cuando el modelo local daría "confianza baja".
# Nunca para inyección ni riesgo legal: esos mensajes ya van a humano y no deben salir de la máquina.
SEGUNDO = TypeSafeJev(timeout=float(os.getenv("JEV_TIMEOUT_S", "10")), reintentos=1) if os.getenv("JEV_SEGUNDO") == "typesafe" else None
CUPO = Cupo(int(os.getenv("JEV_SEGUNDO_MAX", "200")))


class JevNoDisponible(Exception):
    """Sin una distribución del modelo no hay decisión que rutear."""


async def consultar_jev(estado: str):
    try:
        top = await JEV.logprobs(estado, CAL["pregunta"], TIPO)
    except OpenAIError as e:  # caída, timeout, 4xx/5xx del servidor de modelos
        raise JevNoDisponible(type(e).__name__) from e
    if not top:  # p. ej. un despliegue de razonamiento que no devuelve logprobs
        raise JevNoDisponible("sin logprobs")
    return decidir_jev(TIPO, distribucion(top, etiquetas(TIPO), JEV.t))


async def decidir(request: Request) -> JSONResponse:
    try:
        cuerpo = await request.json()
    except ValueError:
        return JSONResponse({"error": "JSON inválido"}, status_code=400)
    msg = cuerpo.get("mensaje") if isinstance(cuerpo, dict) else None
    if not isinstance(msg, str) or not msg.strip() or len(msg) > MAX_CHARS:
        return JSONResponse({"error": f"'mensaje' debe ser texto de 1 a {MAX_CHARS} caracteres"}, status_code=400)
    with tracer.start_as_current_span("jev.decidir") as span:  # atributos de decisión, nunca el texto
        try:
            d = await consultar_jev(anonimizar(msg))
        except JevNoDisponible as e:
            # Falla cerrado: no se rutea a ciegas ni se oculta la caída; el cliente manda el caso a una persona.
            span.set_attributes({"ruta.destino": "humano", "ruta.motivo": "jev no disponible", "jev.error": str(e)})
            return JSONResponse({"error": "modelo no disponible", "destino": "humano", "motivo": "jev no disponible"},
                                status_code=503)
        top2 = sorted(d.probs, key=d.probs.get, reverse=True)[:2]
        destino, motivo = r10.decidir_ruta(d.valor, d.confianza, CAL["umbrales"]["0.05"], r10.ESPECIALISTAS,
                                           sospechoso=r10.es_sospechoso(msg), riesgoso=r10.es_riesgoso(msg))
        juez = "local"
        if motivo == "confianza baja" and SEGUNDO is not None and CUPO.tomar():
            try:
                d = await SEGUNDO.preguntar(anonimizar(msg), CAL["pregunta"], TIPO)
                top2 = sorted(d.probs, key=d.probs.get, reverse=True)[:2]
                destino, motivo = r10.decidir_ruta(d.valor, d.confianza, CAL["umbrales"]["0.05"], r10.ESPECIALISTAS)
                juez = "typesafe"
            except TypeSafeError as e:  # el segundo juez es un refuerzo: si falla, queda la decisión local (a humano)
                span.set_attribute("segundo.error", str(e))
        span.set_attributes({"jev.juez": juez, "jev.categoria": d.valor, "jev.confianza": round(d.confianza, 3),
                             "ruta.destino": destino, "ruta.motivo": motivo})
    return JSONResponse({"categoria": d.valor, "confianza": round(d.confianza, 3), "top2": top2,
                         "destino": destino, "motivo": motivo, "juez": juez})


async def salud(request: Request) -> JSONResponse:
    return JSONResponse({"estado": "ok", "modelo": CAL["modelo"]})


app = BearerAuth(Starlette(routes=[Route("/v1/decidir", decidir, methods=["POST"]), Route("/salud", salud)]),
                 TOKEN, publicas={"/salud"})
