"""Tests deterministas de los servicios de producción (spec: openspec/changes/produccion). Sin LLM.

uv run python servicios/test_servicios.py
"""
import os
import secrets
import sys
from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent))
from seguridad import BearerAuth, token_requerido  # noqa: E402

TOKEN = secrets.token_urlsafe(32)


def test_bearer() -> None:
    app = Starlette(routes=[Route("/protegido", lambda r: PlainTextResponse("ok")),
                            Route("/salud", lambda r: PlainTextResponse("vivo"))])
    c = TestClient(BearerAuth(app, TOKEN, publicas={"/salud"}))
    assert c.get("/protegido").status_code == 401
    assert c.get("/protegido", headers={"Authorization": "Bearer otro-token"}).status_code == 401
    assert c.get("/protegido", headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 200
    assert c.get("/salud").status_code == 200


def test_token_debil() -> None:
    os.environ["TOKEN_PRUEBA"] = "corto12345"
    try:
        token_requerido("TOKEN_PRUEBA")
        raise AssertionError("debió abortar")
    except SystemExit:
        pass
    os.environ["TOKEN_PRUEBA"] = TOKEN
    assert token_requerido("TOKEN_PRUEBA") == TOKEN


def test_router_valida_cuerpo() -> None:
    os.environ["API_TOKEN"] = TOKEN
    import router_api
    c = TestClient(router_api.app)
    assert c.post("/v1/decidir", json={"mensaje": "hola"}).status_code == 401
    auth = {"Authorization": f"Bearer {TOKEN}"}
    assert c.post("/v1/decidir", json={"mensaje": 123}, headers=auth).status_code == 400
    assert c.post("/v1/decidir", json={"mensaje": "x" * 4001}, headers=auth).status_code == 400
    assert c.get("/salud").status_code == 200


if __name__ == "__main__":
    test_bearer()
    test_token_debil()
    test_router_valida_cuerpo()
    print("ok")
