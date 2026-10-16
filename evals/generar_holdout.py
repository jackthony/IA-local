"""Genera el hold-out independiente (evals/golden/golden-holdout-bitext-v1.jsonl), reproducible y sin solaparse con la calibración.

Toma de Bitext + data/ood-otro-v1.csv las filas que `jev/evaluar_empresa.py` NO usó para calibrar ni evaluar (mismas semillas
y tamaños que calibracion-bitext-otro.json) y saca 20 por clase con otra semilla. A diferencia de golden-v3, estos casos no los
escribimos para el proyecto: miden si lo calibrado generaliza. Todos son de ruteo, sin casos críticos ni de reembolso.

  uv run python evals/generar_holdout.py
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "jev"))
from ingesta import filas, muestra  # noqa: E402

CAL = json.loads((RAIZ / "data" / "calibracion-bitext-otro.json").read_text(encoding="utf-8"))
BITEXT = RAIZ / "data" / CAL["origen"]
EXTRA = RAIZ / "data" / CAL["extra"]
N_CAL, N_EV, N_HOLDOUT, SEMILLA = CAL["n_cal"] // len(CAL["opciones"]), CAL["n_ev"] // len(CAL["opciones"]), 20, 3


def main() -> None:
    requeridas = {"instruction", "category", "intent"}
    fs = [f for f in filas(BITEXT.read_text(encoding="utf-8-sig"), requeridas) if f["category"].strip() and f["instruction"].strip()]
    fs += [f for f in filas(EXTRA.read_text(encoding="utf-8-sig"), requeridas) if f["category"].strip() and f["instruction"].strip()]
    for f in fs:
        f["_a"] = f["category"].strip()
    cal = muestra(fs, N_CAL, semilla=1, etiqueta="_a")
    usados = {id(f) for f in cal}
    ev = muestra([f for f in fs if id(f) not in usados], N_EV, semilla=2, etiqueta="_a")
    usados |= {id(f) for f in ev}
    # Bitext repite textos en filas distintas: se excluye por TEXTO (calibración, evaluación y golden-v3), no por fila.
    golden_v3 = {json.loads(x)["mensaje"] for x in (RAIZ / "evals" / "golden" / "golden-v3.jsonl").read_text(encoding="utf-8").splitlines()
                 if x.strip() and "mensaje" in x}
    textos_usados = {f["instruction"] for f in cal + ev} | golden_v3
    vistos, resto = set(), []
    for f in fs:
        if id(f) not in usados and f["instruction"] not in textos_usados and f["instruction"] not in vistos:
            vistos.add(f["instruction"])
            resto.append(f)
    hold = muestra(resto, N_HOLDOUT, semilla=SEMILLA, etiqueta="_a")
    assert not [f for f in hold if f["instruction"] in textos_usados], "el hold-out se solapa con la calibración"
    salida = RAIZ / "evals" / "golden" / "golden-holdout-bitext-v1.jsonl"
    with salida.open("w", encoding="utf-8", newline="\n") as f:
        for n, caso in enumerate(sorted(hold, key=lambda x: (x["_a"], x["instruction"])), 1):
            otro = caso["_a"] == "OTRO"
            f.write(json.dumps({"id": f"holdout-{n:03d}", "tipo": "ruteo", "mensaje": caso["instruction"].strip(),
                                "esperado": caso["_a"], "destino_esperado": "humano" if otro else "auto", "critico": False,
                                "etiquetas": ["holdout", "otro" if otro else "bitext"]}, ensure_ascii=True) + "\n")
    print(f"{len(hold)} casos -> {salida.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
