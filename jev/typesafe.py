"""Cliente mínimo del Jev alojado de TypeSafe (POST /v1/systemone). Spec: openspec/specs/jev-typesafe.

Mismo contrato que `jev.Jev` (`preguntar` -> `Decision`), pero la distribución viene calibrada del servicio en lugar de
logprobs. Usa `probabilities`, no su `confidence`: esa es (p_max - 1/n) / (1 - 1/n), una medida de dispersión, y el ruteo
de este proyecto compara la probabilidad del ganador con un umbral derivado del error tolerado.
Solo Choice (lo que usa el router). La clave sale de TYPESAFE_API_KEY y nunca se imprime, registra ni va en errores.
"""
import asyncio
import os

import httpx

from jev import Choice, Decision, decidir

URL = "https://api.typesafe.ai/v1/systemone"
PREGUNTA = "categoria"
REINTENTABLES = {429, 529}  # límite de tasa y sobrecarga: la documentación pide backoff exponencial


class TypeSafeError(RuntimeError):
    pass


def solicitud(estado: str, pregunta: str, tipo: Choice, modelo: str) -> dict:
    """Cuerpo del POST. Las descripciones del Choice local pasan como `criteria` (null si no hay)."""
    descripciones = tipo.descripciones or (None,) * len(tipo.opciones)
    return {"state": estado, "model": modelo,
            "questions": {PREGUNTA: {"type": "choice", "instructions": pregunta,
                                     "criteria": dict(zip(tipo.opciones, descripciones))}}}


def leer_respuesta(datos: dict, tipo: Choice) -> tuple[dict[str, float], dict, str]:
    """Valida la respuesta antes de confiar en ella: opciones desconocidas o masa que no suma 1 son un error."""
    try:
        resp = datos["answers"][PREGUNTA]
        probs = {str(k): float(v) for k, v in resp["probabilities"].items()}
        uso = datos.get("usage") or {}
    except (KeyError, TypeError, ValueError, AttributeError) as e:
        raise TypeSafeError("respuesta con forma inesperada") from e
    extra = set(probs) - set(tipo.opciones)
    if extra or not probs or abs(sum(probs.values()) - 1) > 0.02 or any(p < 0 for p in probs.values()):
        raise TypeSafeError(f"distribución inválida (opciones ajenas: {sorted(extra)}, suma {sum(probs.values()):.3f})")
    return ({o: probs.get(o, 0.0) for o in tipo.opciones},
            {"input_tokens": int(uso.get("input_tokens", 0)), "output_tokens": int(uso.get("output_tokens", 0))},
            str(datos.get("model", "")))


class TypeSafeJev:
    def __init__(self, modelo: str | None = None, api_key: str | None = None, url: str | None = None,
                 timeout: float = 10.0, reintentos: int = 2) -> None:
        self.modelo = modelo or os.getenv("TYPESAFE_MODEL", "jev-latest")
        self.url = url or os.getenv("TYPESAFE_URL", URL)
        self._clave = api_key or os.getenv("TYPESAFE_API_KEY", "")
        if not self._clave:
            raise TypeSafeError("falta TYPESAFE_API_KEY")
        self.timeout, self.reintentos = timeout, reintentos
        self.uso = (0, 0)  # tokens (entrada, salida) de la última llamada
        self.modelo_servido = ""

    async def consultar(self, estado: str, pregunta: str, tipo: Choice) -> dict[str, float]:
        cuerpo = solicitud(estado, pregunta, tipo, self.modelo)
        async with httpx.AsyncClient(timeout=self.timeout) as http:
            for intento in range(self.reintentos + 1):
                try:
                    r = await http.post(self.url, json=cuerpo, headers={"Authorization": f"Bearer {self._clave}"})
                except httpx.HTTPError as e:  # red o plazo; el mensaje de httpx no lleva cabeceras
                    if intento == self.reintentos:
                        raise TypeSafeError(f"sin respuesta del servicio ({type(e).__name__})") from e
                else:
                    if r.status_code == 200:
                        probs, uso, self.modelo_servido = leer_respuesta(r.json(), tipo)
                        self.uso = (uso["input_tokens"], uso["output_tokens"])
                        return probs
                    if r.status_code not in REINTENTABLES or intento == self.reintentos:
                        raise TypeSafeError(f"HTTP {r.status_code}")  # sin cuerpo: puede repetir el estado enviado
                await asyncio.sleep(0.5 * 2 ** intento)
        raise TypeSafeError("reintentos agotados")

    async def preguntar(self, estado: str, pregunta: str, tipo: Choice) -> Decision:
        return decidir(tipo, await self.consultar(estado, pregunta, tipo))
