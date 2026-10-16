"""Tests del cliente de Jev alojado (TypeSafe) y de la grabación del perfil `typesafe`, contra un servicio falso. Sin red ni clave.

uv run python evals/test_typesafe.py
"""
import asyncio
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ruta = Path(__file__).parent / "evaluar.py"
spec = importlib.util.spec_from_file_location("evaluar", ruta)
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)
from typesafe import PREGUNTA, TypeSafeError, TypeSafeJev, leer_respuesta, solicitud  # noqa: E402

CAL = ev.r10.cargar_calibracion(ev.r10.CALIBRACION)
TIPO = ev.Choice(tuple(CAL["opciones"]), tuple(CAL["descripciones"]) if CAL.get("descripciones") else None)
CLAVE = "clave-falsa-de-prueba-0123456789"
ESPERADO = {ev.anonimizar(c["mensaje"]): c["esperado"] for c in ev.cargar_golden(ev.GOLDEN, CAL["opciones"]) if c["tipo"] == "ruteo"}


class Servicio(BaseHTTPRequestHandler):
    respuestas: list[int] = []   # códigos a devolver en orden; vacío = 200 normal
    recibidas: list[dict] = []
    cabeceras: list[str] = []
    malformada = False

    def log_message(self, *a):
        pass

    def do_POST(self):
        cuerpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).recibidas.append(cuerpo)
        type(self).cabeceras.append(self.headers.get("Authorization", ""))
        codigo = type(self).respuestas.pop(0) if type(self).respuestas else 200
        if codigo != 200:
            return self._json(codigo, {"error": f"falla {codigo}", "state": cuerpo["state"]})  # un servicio puede repetir el estado
        gana = ESPERADO.get(cuerpo["state"]) or TIPO.opciones[0]
        probs = {o: (0.9 if o == gana else 0.1 / (len(TIPO.opciones) - 1)) for o in TIPO.opciones}
        if type(self).malformada:
            probs = {"INVENTADA": 1.0}
        self._json(200, {"model": "jev-1.13.0", "answers": {PREGUNTA: {"type": "choice", "choice": gana, "confidence": 0.9,
                                                                       "probabilities": probs}},
                         "usage": {"input_tokens": 400, "output_tokens": 70}})

    def _json(self, codigo, datos):
        crudo = json.dumps(datos).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(crudo)))
        self.end_headers()
        self.wfile.write(crudo)


servidor = ThreadingHTTPServer(("127.0.0.1", 0), Servicio)
threading.Thread(target=servidor.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{servidor.server_port}/v1/systemone"


def reiniciar() -> None:
    Servicio.respuestas, Servicio.recibidas, Servicio.cabeceras, Servicio.malformada = [], [], [], False


def cliente(**kw) -> TypeSafeJev:
    return TypeSafeJev(api_key=CLAVE, url=URL, **kw)


def test_solicitud() -> None:
    cuerpo = solicitud("hola", "¿Qué área?", TIPO, "jev-latest")
    q = cuerpo["questions"][PREGUNTA]
    assert cuerpo["state"] == "hola" and cuerpo["model"] == "jev-latest" and q["type"] == "choice"
    assert list(q["criteria"]) == list(TIPO.opciones) and all(isinstance(v, str) for v in q["criteria"].values())
    assert set(solicitud("x", "p", ev.Choice(("A", "B")), "m")["questions"][PREGUNTA]["criteria"].values()) == {None}


def test_decision_y_auth() -> None:
    reiniciar()
    j = cliente()
    d = asyncio.run(j.preguntar("I forgot my password", CAL["pregunta"], TIPO))
    assert d.valor == TIPO.opciones[0] and abs(d.confianza - 0.9) < 1e-9
    assert Servicio.cabeceras == [f"Bearer {CLAVE}"] and j.uso == (400, 70) and j.modelo_servido == "jev-1.13.0"


def test_reintenta_429_y_529_con_backoff() -> None:
    reiniciar()
    Servicio.respuestas = [429, 529]
    asyncio.run(cliente().consultar("x", CAL["pregunta"], TIPO))
    assert len(Servicio.recibidas) == 3


def test_no_reintenta_errores_del_cliente_y_no_filtra_nada() -> None:
    reiniciar()
    Servicio.respuestas = [401]
    try:
        asyncio.run(cliente().consultar("mi correo secreto", CAL["pregunta"], TIPO))
        raise AssertionError("debió fallar")
    except TypeSafeError as e:
        assert "401" in str(e) and CLAVE not in str(e) and "secreto" not in str(e), e
    assert len(Servicio.recibidas) == 1, "401 no se reintenta"


def test_reintentos_agotados() -> None:
    reiniciar()
    Servicio.respuestas = [529, 529, 529]
    try:
        asyncio.run(cliente(reintentos=2).consultar("x", CAL["pregunta"], TIPO))
        raise AssertionError("debió fallar")
    except TypeSafeError as e:
        assert "529" in str(e)
    assert len(Servicio.recibidas) == 3


def test_respuesta_invalida_falla() -> None:
    reiniciar()
    Servicio.malformada = True
    try:
        asyncio.run(cliente().consultar("x", CAL["pregunta"], TIPO))
        raise AssertionError("debió rechazar una distribución con opciones ajenas")
    except TypeSafeError as e:
        assert "inválida" in str(e)
    for roto in ({}, {"answers": {}}, {"answers": {PREGUNTA: {"probabilities": {"ORDER": 0.2}}}}):
        try:
            leer_respuesta(roto, TIPO)
            raise AssertionError(f"debió rechazar {roto}")
        except TypeSafeError:
            pass


def test_sin_clave_aborta() -> None:
    os.environ.pop("TYPESAFE_API_KEY", None)
    try:
        TypeSafeJev()
        raise AssertionError("debió exigir la clave")
    except TypeSafeError as e:
        assert "TYPESAFE_API_KEY" in str(e)


def test_grabar_y_evaluar_de_extremo_a_extremo() -> None:
    reiniciar()
    os.environ["TYPESAFE_API_KEY"], os.environ["TYPESAFE_URL"] = CLAVE, URL
    original = ev.REPORTES
    with tempfile.TemporaryDirectory() as d:
        ev.REPORTES = Path(d) / "reportes"
        golden = Path(d) / "golden-v2.jsonl"
        shutil.copy(ev.GOLDEN, golden)
        casos = ev.cargar_golden(golden, CAL["opciones"])
        try:
            salida = asyncio.run(ev.grabar(casos, CAL, "typesafe", golden))
            meta, preds = ev.cargar_predicciones(salida)
            assert meta["backend"] == "typesafe" and meta["modelo"] == "jev-1.13.0" and not meta["local"]
            assert CLAVE not in salida.read_text(encoding="utf-8") and "probabilidades" in next(iter(preds.values()))
            ev.verificar_frescura(meta, ev.sha256(golden), CAL, casos, preds)
            m = ev.evaluar(casos, preds, CAL, meta, {"entrada_1m": 0.042, "salida_1m": 0.0})
            assert m["exactitud_global"] == 1.0 and m["logprobs_degenerados"] == 0
            assert m["tokens_por_decision"] == {"entrada": 400.0, "salida": 70.0} and m["costo_por_1000_usd"] == 0.0168
            assert len(Servicio.recibidas) == 70  # 69 casos + calentamiento
            assert all("@" not in c["state"] for c in Servicio.recibidas), "PII enviada al servicio"
            uso = (ev.REPORTES / "uso.jsonl").read_text(encoding="utf-8")
            assert '"llamadas": 70' in uso and CLAVE not in uso
        finally:
            ev.REPORTES = original
            for k in ("TYPESAFE_API_KEY", "TYPESAFE_URL"):
                os.environ.pop(k, None)


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("ok")
