"""Servidor falso compatible con OpenAI (/v1/chat/completions) para escenarios deterministas, sin LLM real.

Atiende los dos tipos de llamada del proyecto:
  - Jev (max_tokens=1, logprobs): repite los logprobs grabados en evals/golden/ por mensaje; sin grabación, `defecto`.
  - Agentes (chat): si hay tools y el cliente pide devolver dinero ("<monto> soles"), propone `emitir_reembolso`
    con ese monto; si no, responde texto. Nunca ejecuta nada: solo propone, como el modelo real.
Modos de fallo para probar la degradación: "caido" (500), "basura" (200 sin logprobs), "lento" (1 s).
Cada llamada queda en `recibidas` para afirmar qué vio el "modelo" (p. ej. que la PII no llegó).
"""
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEFECTO = [["REFUND", -0.01], ["PAYMENT", -4.6]]
MONTO = re.compile(r"(\d+(?:\.\d+)?)\s*soles", re.IGNORECASE)


class LlmFalso:
    def __init__(self, rotulo: str, por_estado: dict[str, list] | None = None, defecto: list | None = None) -> None:
        self.rotulo, self.por_estado, self.defecto = rotulo, por_estado or {}, defecto or DEFECTO
        self.recibidas: list[dict] = []
        self.modo = "repite"
        falso = self

        class Manejador(BaseHTTPRequestHandler):
            def log_message(self, *a):  # servidor de prueba: sin ruido en la salida
                pass

            def do_POST(self):
                cuerpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                codigo, datos = falso.atender(cuerpo)
                crudo = json.dumps(datos).encode()
                self.send_response(codigo)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(crudo)))
                self.end_headers()
                self.wfile.write(crudo)

        self.servidor = ThreadingHTTPServer(("127.0.0.1", 0), Manejador)
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.servidor.server_port}/v1"

    def cerrar(self) -> None:
        self.servidor.shutdown()

    def chats(self) -> list[dict]:
        return [r for r in self.recibidas if r["tipo"] == "chat"]

    def atender(self, cuerpo: dict) -> tuple[int, dict]:
        es_jev = cuerpo.get("max_tokens") == 1 and cuerpo.get("logprobs")
        texto = next((m["content"] for m in reversed(cuerpo["messages"]) if m["role"] == "user"), "")
        texto = texto if isinstance(texto, str) else "".join(p.get("text", "") for p in texto)
        estado = texto.split(f"\n{self.rotulo}: ", 1)[-1] if es_jev else texto
        self.recibidas.append({"tipo": "jev" if es_jev else "chat", "estado": estado, "tools": bool(cuerpo.get("tools"))})
        if self.modo == "lento":
            time.sleep(1.0)
        if self.modo == "caido":
            return 500, {"error": {"message": "modelo caído", "type": "server_error"}}
        base = {"id": "x", "object": "chat.completion", "created": 0, "model": cuerpo["model"],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
        if es_jev:
            top = [] if self.modo == "basura" else self.por_estado.get(estado, self.defecto)
            primero = top[0] if top else ["", 0.0]
            return 200, {**base, "choices": [{"index": 0, "finish_reason": "length",
                         "message": {"role": "assistant", "content": primero[0]},
                         "logprobs": {"content": [{"token": primero[0], "logprob": primero[1],
                                                   "top_logprobs": [{"token": t, "logprob": lp} for t, lp in top]}]}}]}
        monto = MONTO.search(texto)
        if cuerpo.get("tools") and monto:
            llamada = {"id": "call_1", "type": "function", "function": {
                "name": "emitir_reembolso", "arguments": json.dumps({"monto": float(monto.group(1)), "motivo": "cobro doble"})}}
            mensaje, motivo = {"role": "assistant", "content": None, "tool_calls": [llamada]}, "tool_calls"
        else:
            mensaje, motivo = {"role": "assistant", "content": "Gracias, un especialista atenderá tu caso."}, "stop"
        return 200, {**base, "choices": [{"index": 0, "finish_reason": motivo, "message": mensaje}]}
