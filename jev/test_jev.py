"""Tests deterministas de Jev local (spec: openspec/specs/jev). Sin LLM.

uv run python jev/test_jev.py
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from auditar_deps import paquetes  # noqa: E402
from jev import (Choice, Noul, Score, brier, calibrar, decidir, distribucion, ece, prompt, ruta,  # noqa: E402
                 umbral_auto)


def cerca(a: float, b: float, tol: float = 1e-3) -> bool:
    return math.isclose(a, b, abs_tol=tol)


def test_distribucion() -> None:
    d = distribucion([("A", 0.0), ("B", -2.0), (" a", -3.0), ("X", -1.0)], ["A", "B", "C"])
    assert cerca(d["A"], 0.8858) and cerca(d["B"], 0.1142) and d["C"] == 0.0
    d = distribucion([("fact", -0.1), (" Si", -5.0)], ["facturacion", "Sí"])
    assert cerca(d["facturacion"], math.exp(-0.1) / (math.exp(-0.1) + math.exp(-5.0))) and d["Sí"] > 0
    assert distribucion([("X", 0.0)], ["A", "B", "C"]) == {"A": 1 / 3, "B": 1 / 3, "C": 1 / 3}
    assert cerca(distribucion([("A", 0.0), ("B", -2.0)], ["A", "B"])["A"], 0.8808)
    assert cerca(distribucion([("A", 0.0), ("B", -2.0)], ["A", "B"], t=2)["A"], 0.7311)
    variantes = [("cuenta", -0.1), ("fact", -2.0), ("Fact", -2.5), (" fact", -3.0)]
    for t in (1, 8):
        d = distribucion(variantes, ["facturacion", "cuenta"], t=t)
        assert max(d, key=d.get) == "cuenta"


def test_prompt() -> None:
    msgs = prompt("Me cobraron doble", "Clasifica el ticket en una de estas áreas",
                  Choice(("facturacion", "tecnico")), rotulo="Ticket")
    assert len(msgs) == 1 and msgs[0]["role"] == "user"
    assert "áreas: facturacion, tecnico" in msgs[0]["content"] and "Ticket: Me cobraron doble" in msgs[0]["content"]


def test_descripciones() -> None:
    tipo = Choice(("IT Support", "Billing"), ("Internal IT, laptops", "Invoices, refunds"))
    contenido = prompt("x", "Classify the ticket into one of these queues", tipo)[0]["content"]
    assert "- IT Support: Internal IT, laptops" in contenido and "- Billing: Invoices, refunds" in contenido
    try:
        Choice(("A", "B"), ("solo una",))
        raise AssertionError("debió lanzar ValueError")
    except ValueError:
        pass


def test_decidir() -> None:
    c = decidir(Choice(("facturacion", "tecnico", "ventas")), {"facturacion": 0.7, "tecnico": 0.2, "ventas": 0.1})
    assert c.valor == "facturacion" and c.confianza == 0.7
    assert c.probs == {"facturacion": 0.7, "tecnico": 0.2, "ventas": 0.1}
    s = decidir(Score(3), {"1": 0.0, "2": 0.5, "3": 0.5})
    assert s.valor == 2.5 and s.confianza == 0.5
    n = decidir(Noul(), {"Sí": 0.8, "No": 0.2})
    assert n.valor == 0.8 and n.confianza == 0.8


def test_calibracion_y_metricas() -> None:
    ejemplos = [([("A", 0.0), ("B", -4.0)], ["A", "B"], "A")] * 7 + [([("A", 0.0), ("B", -4.0)], ["A", "B"], "B")] * 3
    assert 4.0 <= calibrar(ejemplos) <= 5.5
    assert cerca(ece([0.9, 0.9], [True, False]), 0.4)
    assert brier([1.0, 0.0], [True, True]) == 0.5


def test_ruta() -> None:
    assert [ruta(c) for c in (0.95, 0.7, 0.4)] == ["auto", "escalar", "humano"]


def test_umbral_auto() -> None:
    assert umbral_auto([0.95, 0.9, 0.8, 0.7], [True, True, True, False]) == 0.8
    assert umbral_auto([0.9], [False]) > 1


def test_paquetes() -> None:
    lock = {"package": [{"name": "openai", "version": "3.20.0", "source": {"registry": "https://pypi.org/simple"}},
                        {"name": "ia-local", "version": "0.1.0", "source": {"virtual": "."}}]}
    assert paquetes(lock) == [("openai", "3.20.0")]


if __name__ == "__main__":
    test_distribucion()
    test_prompt()
    test_descripciones()
    test_decidir()
    test_calibracion_y_metricas()
    test_ruta()
    test_umbral_auto()
    test_paquetes()
    print("ok")
