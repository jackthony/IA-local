"""Jev como servicio de decisión (System 1): POST /v1/decidir (spec: openspec/changes/produccion).

.venv/bin/uvicorn --app-dir servicios router_api:app --host 0.0.0.0 --port 8000
"""
import importlib
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
from jev import Choice, Jev  # noqa: E402

r10 = importlib.import_module("10_router_jev")
TOKEN = token_requerido("API_TOKEN")
MAX_CHARS = 4000
CAL = r10.cargar_calibracion(r10.CALIBRACION)
TIPO = Choice(tuple(CAL["opciones"]), tuple(CAL["descripciones"]) if CAL.get("descripciones") else None)
JEV = Jev(CAL["modelo"], t=CAL["T"], rotulo=CAL["rotulo"])
tracer = trace.get_tracer("router-api")


async def decidir(request: Request) -> JSONResponse:
    try:
        cuerpo = await request.json()
    except ValueError:
        return JSONResponse({"error": "JSON inválido"}, status_code=400)
    msg = cuerpo.get("mensaje") if isinstance(cuerpo, dict) else None
    if not isinstance(msg, str) or not msg.strip() or len(msg) > MAX_CHARS:
        return JSONResponse({"error": f"'mensaje' debe ser texto de 1 a {MAX_CHARS} caracteres"}, status_code=400)
    with tracer.start_as_current_span("jev.decidir") as span:  # atributos de decisión, nunca el texto
        d = await JEV.preguntar(anonimizar(msg), CAL["pregunta"], TIPO)
        top2 = sorted(d.probs, key=d.probs.get, reverse=True)[:2]
        destino, motivo = r10.decidir_ruta(d.valor, d.confianza, CAL["umbrales"]["0.05"], r10.ESPECIALISTAS,
                                           sospechoso=r10.es_sospechoso(msg))
        span.set_attributes({"jev.categoria": d.valor, "jev.confianza": round(d.confianza, 3),
                             "ruta.destino": destino, "ruta.motivo": motivo})
    return JSONResponse({"categoria": d.valor, "confianza": round(d.confianza, 3), "top2": top2,
                         "destino": destino, "motivo": motivo})


async def salud(request: Request) -> JSONResponse:
    return JSONResponse({"estado": "ok", "modelo": CAL["modelo"]})


app = BearerAuth(Starlette(routes=[Route("/v1/decidir", decidir, methods=["POST"]), Route("/salud", salud)]),
                 TOKEN, publicas={"/salud"})
