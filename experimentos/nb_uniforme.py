"""NB con priors uniformes + validación cruzada simple en la mezcla natural (sin LLM)."""
import collections
import math
import random
import re
import sys

sys.path.insert(0, "jev")
from diagnostico_kaggle import N_CAL, N_EV, NaiveBayes  # noqa: E402
from eval_kaggle import cargar, texto  # noqa: E402
from ingesta import muestra  # noqa: E402

fs = cargar()
cal = muestra(fs, N_CAL, semilla=1)
usados = {id(f) for f in cal}
ev = muestra([f for f in fs if id(f) not in usados], N_EV, semilla=2)
usados |= {id(f) for f in ev}
entren = [f for f in fs if id(f) not in usados]
nb = NaiveBayes().fit([texto(f) for f in entren], [f["queue"] for f in entren])
n_clases = len(nb.docs)
v = len(nb.vocab)


def pred_uniforme(t: str) -> str:
    tokens = [w for w in re.findall(r"\w+", t.lower()) if w in nb.vocab]
    return max(nb.docs, key=lambda e: sum(math.log((nb.palabras[e][w] + 1) / (nb.totales[e] + v)) for w in tokens))


ok = sum(pred_uniforme(texto(f)) == f["queue"] for f in ev)
print(f"NB priors uniformes, eval balanceado: {ok}/{len(ev)} = {ok / len(ev):.1%} (azar {1 / n_clases:.0%})")

# Mezcla natural: 80/20 aleatorio sobre todo el inglés
rnd = random.Random(0)
todo = fs[:]
rnd.shuffle(todo)
corte = int(len(todo) * 0.8)
nb2 = NaiveBayes().fit([texto(f) for f in todo[:corte]], [f["queue"] for f in todo[:corte]])
prueba = todo[corte:]
ok2 = sum(nb2.predecir(texto(f)) == f["queue"] for f in prueba)
mayoritaria = collections.Counter(f["queue"] for f in todo[:corte]).most_common(1)[0]
base = sum(f["queue"] == mayoritaria[0] for f in prueba) / len(prueba)
print(f"NB mezcla natural (80/20, {len(prueba)} prueba): {ok2 / len(prueba):.1%} | siempre '{mayoritaria[0]}': {base:.1%}")

# Duplicados de texto casi idénticos con etiquetas distintas (ruido de etiqueta directo)
por_asunto = collections.defaultdict(set)
for f in fs:
    por_asunto[f["subject"].strip().lower()].add(f["queue"])
rep = [s for s, q in por_asunto.items() if s and len(q) > 1]
print(f"asuntos idénticos con colas distintas: {len(rep)} (ej: {rep[:3]})")
