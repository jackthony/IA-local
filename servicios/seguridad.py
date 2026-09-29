"""Autenticación entre servicios: Bearer fail-closed (spec: openspec/changes/produccion).

Zero trust también dentro de la red de contenedores: cada servicio exige su token, compara en tiempo
constante y no arranca si el token falta o es débil.
"""
import hmac
import os

from starlette.responses import JSONResponse

MIN_LARGO = 32


def token_requerido(nombre: str) -> str:
    token = os.getenv(nombre, "")
    if len(token) < MIN_LARGO:
        raise SystemExit(f"{nombre} ausente o débil (< {MIN_LARGO} caracteres): el servicio no arranca. "
                         "Genera tokens con: uv run python scripts/generar_env.py")
    return token


class BearerAuth:
    """Middleware ASGI: 401 si falta o no coincide `Authorization: Bearer <token>` (salvo rutas públicas)."""

    def __init__(self, app, token: str, publicas: set[str] = frozenset()) -> None:
        self.app, self.publicas = app, set(publicas)
        self._esperado = f"Bearer {token}".encode()

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "lifespan" or scope.get("path") in self.publicas:
            return await self.app(scope, receive, send)
        recibido = dict(scope.get("headers") or []).get(b"authorization", b"")
        if not hmac.compare_digest(recibido, self._esperado):
            respuesta = JSONResponse({"error": "no autorizado"}, status_code=401, headers={"WWW-Authenticate": "Bearer"})
            return await respuesta(scope, receive, send)
        return await self.app(scope, receive, send)
