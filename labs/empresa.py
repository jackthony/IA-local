"""Sistemas de la empresa: fuente única de datos y cálculos de negocio.

Lo consumen el servidor MCP (08) y los labs 04/07. Deterministas: nada de LLM aquí.
ponytail: datos fijos. En prod estas funciones llaman al DWH / API del BCRP.
"""
import json
from typing import Annotated

PEN_POR_UNIDAD = {"PEN": 1.0, "USD": 3.75, "EUR": 4.10}
VENTAS = {"norte": (120_000, 138_000), "sur": (90_000, 81_000), "lima": (300_000, 345_000)}  # (Q2, Q3)


def convertir(monto: Annotated[float, "Monto a convertir"],
              de: Annotated[str, "Moneda origen: PEN, USD o EUR"],
              a: Annotated[str, "Moneda destino: PEN, USD o EUR"]) -> float:
    """Convierte un monto entre monedas usando la tabla oficial de tasas."""
    de, a = de.upper(), a.upper()
    for m in (de, a):
        if m not in PEN_POR_UNIDAD:
            raise ValueError(f"Moneda no soportada: {m}")
    return round(monto * PEN_POR_UNIDAD[de] / PEN_POR_UNIDAD[a], 2)


def _crec(q2: int, q3: int) -> float:
    return round((q3 - q2) / q2 * 100, 1)


def ventas_por_region() -> str:
    """Ventas Q2 y Q3 por región (en PEN) con crecimiento % ya calculado, más el total."""
    d = {r: {"q2": q2, "q3": q3, "crecimiento_pct": _crec(q2, q3)} for r, (q2, q3) in VENTAS.items()}
    q2, q3 = sum(v[0] for v in VENTAS.values()), sum(v[1] for v in VENTAS.values())
    d["total"] = {"q2": q2, "q3": q3, "crecimiento_pct": _crec(q2, q3)}
    return json.dumps(d)
