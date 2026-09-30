"""Tests deterministas del router con aprobación humana (spec: openspec/specs/hitl). Sin LLM.

uv run python labs/test_hitl.py
"""
import asyncio
import importlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from agent_framework import FileCheckpointStorage, WorkflowCheckpoint  # noqa: E402

h = importlib.import_module("11_hitl_router")
CLAVE = b"clave-de-prueba-32-bytes-exactos!"


def falla(fn, texto: str = "") -> None:
    try:
        fn()
    except ValueError as e:
        assert texto in str(e), e
        return
    raise AssertionError("debió lanzar ValueError")


def test_sello() -> None:
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "abc.json").write_text('{"estado": 1}', encoding="utf-8")
        h.sellar(d, "abc", CLAVE)
        h.verificar_checkpoint(d, "abc", CLAVE)
        (d / "abc.json").write_text('{"estado": 2}', encoding="utf-8")
        h.sellar(d, "abc", CLAVE)  # re-sellar NO debe legitimar el archivo manipulado
        falla(lambda: h.verificar_checkpoint(d, "abc", CLAVE), "sello")
        (d / "plantado.json").write_text("{}", encoding="utf-8")
        (d / "otro.json").write_text("{}", encoding="utf-8")
        h.sellar(d, "otro", CLAVE)  # sellar un checkpoint propio NO sella lo que haya alrededor
        falla(lambda: h.verificar_checkpoint(d, "plantado", CLAVE))


def test_almacen_sellado() -> None:
    async def caso(d: Path) -> None:
        almacen = h.AlmacenSellado(d, CLAVE)
        propio = await almacen.save(WorkflowCheckpoint(workflow_name="wf", graph_signature_hash="g"))
        assert (await almacen.load(propio)).workflow_name == "wf"
        # un tercero escribe un checkpoint "más nuevo" sin pasar por el almacén sellado
        plantado = WorkflowCheckpoint(workflow_name="wf", graph_signature_hash="g",
                                      timestamp="2999-01-01T00:00:00+00:00")
        await FileCheckpointStorage(d).save(plantado)
        await almacen.save(WorkflowCheckpoint(workflow_name="otro", graph_signature_hash="g"))  # guardados posteriores
        assert (await almacen.get_latest(workflow_name="wf")).checkpoint_id == propio  # el plantado no se ve
        try:
            await almacen.load(plantado.checkpoint_id)
            raise AssertionError("debió rechazar el checkpoint plantado")
        except ValueError as e:
            assert "sin sello" in str(e), e

    with tempfile.TemporaryDirectory() as d:
        asyncio.run(caso(Path(d)))


def test_cola_firmada() -> None:
    entrada = {"checkpoint": "abc", "tipo": "aprobacion", "tool": "emitir_reembolso",
               "argumentos": {"monto": 450.0, "motivo": "cobro doble"}, "operacion": "c1:call_1"}
    firmada = json.loads(json.dumps(h.firmar_entrada("rid-1", entrada, CLAVE)))  # ida y vuelta por pendientes.json
    assert h.verificar_entrada("rid-1", firmada, CLAVE) == entrada
    editada = {**firmada, "argumentos": {"monto": 45.0, "motivo": "cobro doble"}}  # lo que vería el supervisor
    falla(lambda: h.verificar_entrada("rid-1", editada, CLAVE), "sello")
    falla(lambda: h.verificar_entrada("rid-2", firmada, CLAVE), "sello")  # no se traslada a otra solicitud
    falla(lambda: h.verificar_entrada("rid-1", entrada, CLAVE), "sello")  # sin firma


def test_reembolso_idempotente() -> None:
    original = h.LEDGER
    with tempfile.TemporaryDirectory() as d:
        h.LEDGER = Path(d) / "reembolsos.jsonl"
        try:
            assert "emitido" in h.ejecutar_reembolso("caso1:call_1", 50.0, "cobro doble")
            assert "ya emitido" in h.ejecutar_reembolso("caso1:call_1", 50.0, "cobro doble")  # reintento tras caída
            h.ejecutar_reembolso("caso2:call_1", 20.0, "otro caso")
            lineas = h.LEDGER.read_text(encoding="utf-8").splitlines()
            assert [json.loads(x)["operacion"] for x in lineas] == ["caso1:call_1", "caso2:call_1"]
        finally:
            h.LEDGER = original


def test_tool_no_ejecuta() -> None:
    try:
        h.proponer_reembolso(50.0, "x")
        raise AssertionError("la tool nunca debe ejecutar el pago por sí misma")
    except RuntimeError:
        pass


def test_acuerdo() -> None:
    cs = [{"jev": "ORDER", "humano": "ORDER"}, {"jev": "CANCEL", "humano": "ORDER"}, {"jev": "REFUND", "humano": "REFUND"}]
    assert h.acuerdo(cs) == 2 / 3
    assert h.acuerdo(cs + [{"jev": "ACCOUNT", "humano": "DESCARTADO"}]) == 2 / 3
    assert h.acuerdo([]) is None and h.acuerdo([{"jev": "ACCOUNT", "humano": "DESCARTADO"}]) is None


def test_validar_reembolso() -> None:
    assert h.validar_reembolso({"monto": 900, "motivo": "x"})[0] is False
    assert h.validar_reembolso({"monto": -5, "motivo": "x"})[0] is False
    assert h.validar_reembolso({"monto": "mucho", "motivo": "x"})[0] is False
    assert h.validar_reembolso({"monto": 50, "motivo": "x"}) == (True, "")


def test_limpiar_marcadores() -> None:
    assert h.limpiar_marcadores("escríbanos a [EMAIL_1] hoy") == ("escríbanos a (dato no disponible) hoy", 1)
    assert h.limpiar_marcadores("sin marcadores") == ("sin marcadores", 0)


if __name__ == "__main__":
    test_limpiar_marcadores()
    test_sello()
    test_almacen_sellado()
    test_cola_firmada()
    test_reembolso_idempotente()
    test_tool_no_ejecuta()
    test_acuerdo()
    test_validar_reembolso()
    print("ok")
