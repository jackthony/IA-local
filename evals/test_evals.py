"""Tests de la puerta de evaluación (sin LLM): comprueba que la puerta SÍ falla cuando algo se degrada.

uv run python evals/test_evals.py
"""
import copy
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ruta = Path(__file__).parent / "evaluar.py"
spec = importlib.util.spec_from_file_location("evaluar", ruta)
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)

CAL = ev.r10.cargar_calibracion(ev.r10.CALIBRACION)
CASOS = ev.cargar_golden(ev.GOLDEN, CAL["opciones"])
META, PREDS = ev.cargar_predicciones(ev.ruta_predicciones("ollama"))
U = ev.cargar_umbrales(ev.UMBRALES)


def medir(cal=CAL, preds=PREDS) -> dict:
    return ev.evaluar(CASOS, preds, cal, META)


def test_golden_set() -> None:
    ruteo = [c for c in CASOS if c["tipo"] == "ruteo"]
    assert len(CASOS) >= 50 and len(ruteo) >= 50
    assert {c["esperado"] for c in ruteo if c["esperado"]} == set(CAL["opciones"]), "toda clase con casos"
    assert any(c["critico"] for c in CASOS) and any("inyeccion" in c.get("etiquetas", []) for c in ruteo)


def test_linea_base_aprueba() -> None:
    assert ev.compuerta(medir(), U) == []
    ev.verificar_frescura(META, ev.sha256(ev.GOLDEN), CAL, CASOS, PREDS)


CONOCIDAS = ev.cargar_limitaciones(ev.ruta_limitaciones())


def test_limitaciones_conocidas_son_exactas() -> None:
    m = medir()
    assert ev.compuerta(m, U, CONOCIDAS) == []
    assert {x["id"] for x in m["divergencias_destino"]} == set(CONOCIDAS)
    assert m["exactitud_destino"] == round(1 - len(CONOCIDAS) / m["n"]["ruteo"], 4)


def test_divergencia_nueva_falla() -> None:
    cal = copy.deepcopy(CAL)
    cal["umbrales"]["0.05"] = 0.99  # más caso a humano que lo esperado: divergencias que nadie aceptó
    v = ev.compuerta(medir(cal), U, CONOCIDAS)
    assert any("divergencia nueva" in x for x in v)


def test_limitacion_resuelta_obliga_a_retirarla() -> None:
    v = ev.compuerta(medir(), U, {**CONOCIDAS, "account-01": {"destino": "humano", "impacto": "ya no aplica"}})
    assert any("resuelta" in x and "account-01" in x for x in v)


def test_limitacion_que_cambia_de_destino_falla() -> None:
    primera = next(iter(CONOCIDAS))
    cambiada = {**CONOCIDAS, primera: {**CONOCIDAS[primera], "destino": "pagos"}}
    assert any("cambió de destino" in x for x in ev.compuerta(medir(), U, cambiada))


def test_limitacion_sin_impacto_es_invalida() -> None:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "l.json"
        p.write_text(json.dumps({"x": {"destino": "humano", "impacto": " "}}), encoding="utf-8")
        try:
            ev.cargar_limitaciones(p)
            raise AssertionError("debió lanzar ValueError")
        except ValueError as e:
            assert "impacto" in str(e)


def test_logprobs_degenerados_se_detectan() -> None:
    assert medir()["logprobs_degenerados"] == 0
    rotos = {k: {**v, "logprobs": [[v["logprobs"][0][0], 0.0]] + [[t, -9999.0] for t, _ in v["logprobs"][1:]]}
             for k, v in PREDS.items()}
    assert medir(preds=rotos)["logprobs_degenerados"] == 1.0


def test_limitaciones_son_por_perfil() -> None:
    assert ev.ruta_limitaciones(perfil="ollama").name == "limitaciones-v2-ollama.json"
    assert ev.ruta_limitaciones(perfil="deepseek") != ev.ruta_limitaciones(perfil="ollama")


def test_umbral_alto_manda_todo_a_humano() -> None:
    cal = copy.deepcopy(CAL)
    cal["umbrales"]["0.05"] = 1.01
    m = medir(cal)
    assert m["pct_automatizado"] == 0
    assert any("automatizado" in v for v in ev.compuerta(m, U))


def test_detector_roto_deja_pasar_inyeccion() -> None:
    original = ev.r10.es_sospechoso
    ev.r10.es_sospechoso = lambda _m: False
    try:
        m = medir()
    finally:
        ev.r10.es_sospechoso = original
    assert len(m["criticos"]["mal_a_automatico"]) > U["max_criticos_automaticos"]
    assert any("críticos" in v for v in ev.compuerta(m, U))


def test_politica_reembolso_rota() -> None:
    original = ev.h11.MAX_REEMBOLSO
    ev.h11.MAX_REEMBOLSO = 10_000.0
    try:
        m = medir()
    finally:
        ev.h11.MAX_REEMBOLSO = original
    assert m["criticos"]["reembolsos_invalidos_aceptados"]
    assert any("reembolso" in v for v in ev.compuerta(m, U))


def test_temperatura_mal_calibrada_sube_ece() -> None:
    cal = copy.deepcopy(CAL)
    cal["T"] = 20.0  # subconfiado: con exactitud alta, la confianza queda muy por debajo
    assert medir(cal)["ece"] > U["max_ece"]


def falla(meta: dict, texto: str, preds: dict = PREDS) -> None:
    try:
        ev.verificar_frescura(meta, ev.sha256(ev.GOLDEN), CAL, CASOS, preds)
    except ValueError as e:
        assert texto in str(e), e
        return
    raise AssertionError(f"debió fallar: {texto}")


def test_frescura() -> None:
    falla({**META, "golden_sha256": "0" * 64}, "golden set cambió")
    falla({**META, "prompt_sha256": "0" * 64}, "prompt")
    falla(META, "sin cubrir", {k: v for k, v in PREDS.items() if k != CASOS[0]["id"]})


def test_golden_invalido() -> None:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "g.jsonl"
        base = {"id": "a", "tipo": "ruteo", "mensaje": "x", "esperado": "NOEXISTE", "destino_esperado": "auto", "critico": False}
        p.write_text(json.dumps(base) + "\n", encoding="utf-8")
        for contenido, texto in ((json.dumps(base), "fuera de las opciones"),
                                 (json.dumps({**base, "esperado": "ORDER"}), "al menos 50")):
            p.write_text(contenido + "\n", encoding="utf-8")
            try:
                ev.cargar_golden(p, CAL["opciones"])
                raise AssertionError("debió lanzar ValueError")
            except ValueError as e:
                assert texto in str(e), e


def test_costo() -> None:
    assert ev.costo_1000(200, 1, {"local": True}, None) == 0.0
    assert ev.costo_1000(200, 1, {"local": False}, None) is None
    assert ev.costo_1000(1000, 1, {"local": False}, {"entrada_1m": 0.5, "salida_1m": 2.0}) == 0.502


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("ok")
