"""Ingesta zero trust de datasets públicos (solo CSV desde Hugging Face, fijados a commit).

1. Descarga en memoria con tope de tamaño (nada toca disco sin verificar).
2. SHA-256 contra el hash LFS publicado para ese commit.
3. Parseo con `csv` (stdlib) + chequeo de esquema. Sin librería `datasets` (puede ejecutar scripts).
4. Escaneo de celdas hostiles (fórmulas, prompt injection, Unicode invisible): se reporta, no se altera.
5. Escribe data/<archivo> (solo lectura) + data/MANIFEST-<fuente>.json (procedencia).

uv run python jev/ingesta.py <fuente>      # fuentes: ver FUENTES
"""
import collections
import csv
import datetime
import hashlib
import io
import json
import os
import random
import re
import stat
import unicodedata
import urllib.request
from pathlib import Path

def _fuente(repo: str, commit: str, archivo: str, sha256: str, licencia: str, requeridas: set, etiqueta: str) -> dict:
    return {"repo": repo, "commit": commit, "archivo": archivo, "sha256": sha256, "licencia": licencia,
            "requeridas": requeridas, "etiqueta": etiqueta,
            "url": f"https://huggingface.co/datasets/{repo}/resolve/{commit}/{archivo}"}  # fijada al commit, no a main


# sha256 = hash LFS publicado por Hugging Face para ese commit (verificado vía API antes de registrar la fuente)
FUENTES = {
    "tickets": _fuente("Tobi-Bueck/customer-support-tickets", "ddf1c81a5475992c4fa6752bf1e8b4e31f07bbeb",
                       "dataset-tickets-multi-lang-4-20k.csv",
                       "9be3bf810584fe01e8e83383e83dfd33f4c3910938ecad03ef151da79d8f0635",
                       "CC BY-NC 4.0 (solo evaluación, no producción)", {"subject", "body", "queue", "language"}, "queue"),
    "bitext": _fuente("bitext/Bitext-customer-support-llm-chatbot-training-dataset",
                      "430d1a89bd93bd1fa23c16f29dd53e73f0087443",
                      "Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv",
                      "6f81102b0100b97b8468eb04368033a23206bf1fde9d53500d5806ec1001a434",
                      "CDLA-Sharing-1.0 (permite uso comercial; datos derivados con la misma licencia)",
                      {"instruction", "category", "intent"}, "category"),
}
MAX_BYTES = 25_000_000
DATA = Path(__file__).parent.parent / "data"
REQUERIDAS = FUENTES["tickets"]["requeridas"]

INYECCION = re.compile(
    r"ignore (all |any )?(the )?(previous|prior|above|earlier) (instructions|prompts)|disregard (all )?(previous|prior)"
    r"|ignora (todas )?(las )?instrucciones|olvida (todas )?(tus|las) instrucciones|system prompt|you are now"
    r"|ahora eres|</?(system|assistant)>", re.IGNORECASE)  # <user> no: marcador de anonimización del dataset
# Rangos construidos con chr(): nunca caracteres invisibles literales en el fuente (Trojan Source).
INVISIBLE = re.compile("[" + "".join(f"{chr(a)}-{chr(b)}" for a, b in ((0x202A, 0x202E), (0x2066, 0x2069),
                                                                       (0x200B, 0x200F))) + "]")


def verificar(datos: bytes, sha256: str, max_bytes: int) -> None:
    if len(datos) > max_bytes:
        raise ValueError(f"tamaño {len(datos)} excede el máximo {max_bytes}")
    real = hashlib.sha256(datos).hexdigest()
    if real != sha256:
        raise ValueError(f"SHA-256 no coincide: {real} != {sha256}")


def normalizar(texto: str) -> str:
    """Forma canónica para el detector: sin caracteres de formato (Cf), NFKC y espacios colapsados.

    Medido: un zero-width entre "Ignore" y "all", o un salto de línea entre palabras, evadía el patrón.
    """
    sin_formato = "".join(c for c in texto if unicodedata.category(c) != "Cf")
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", sin_formato))


def hallazgos(celda: str) -> list[str]:
    h = []
    if celda[:1] in ("=", "+", "-", "@", "\t", "\r"):
        h.append("formula")
    if INYECCION.search(normalizar(celda)):
        h.append("prompt_injection")
    if INVISIBLE.search(celda):
        h.append("unicode_invisible")
    return h


def filas(texto: str, requeridas: set = REQUERIDAS) -> list[dict]:
    csv.field_size_limit(1_000_000)  # tope por celda: un CSV hostil no agota memoria con una celda gigante
    lector = csv.DictReader(io.StringIO(texto))
    faltan = requeridas - {c.strip().lower() for c in lector.fieldnames or []}
    if faltan:
        raise ValueError(f"faltan columnas requeridas: {sorted(faltan)}")
    return [{(k or "").strip().lower(): (v or "") for k, v in f.items()} for f in lector]


def muestra(fs: list[dict], n_por_cola: int, semilla: int = 42, etiqueta: str = "queue") -> list[dict]:
    """Hasta n filas por clase, reproducible con la misma semilla."""
    grupos = collections.defaultdict(list)
    for f in fs:
        grupos[f[etiqueta]].append(f)
    rnd = random.Random(semilla)
    return [f for q in sorted(grupos) for f in rnd.sample(grupos[q], min(n_por_cola, len(grupos[q])))]


def cargar(nombre: str) -> list[dict]:
    """Lee el CSV de una fuente re-verificando su SHA-256 contra el manifiesto (el disco también es no confiable)."""
    m = json.loads((DATA / f"MANIFEST-{nombre}.json").read_text(encoding="utf-8"))
    datos = (DATA / m["archivo"]).read_bytes()
    verificar(datos, m["sha256"], MAX_BYTES)
    return filas(datos.decode("utf-8-sig"), FUENTES[nombre]["requeridas"])


def main(nombre: str) -> None:
    fu = FUENTES[nombre]
    destino = DATA / fu["archivo"]
    if destino.exists():
        verificar(destino.read_bytes(), fu["sha256"], MAX_BYTES)
        print(f"ya existe y verifica SHA-256: {destino}")
        return
    with urllib.request.urlopen(urllib.request.Request(fu["url"], headers={"User-Agent": "zt-ingesta"}), timeout=120) as r:
        datos = r.read(MAX_BYTES + 1)  # en memoria; +1 para detectar exceso
    verificar(datos, fu["sha256"], MAX_BYTES)
    fs = filas(datos.decode("utf-8-sig"), fu["requeridas"])  # utf-8 estricto: bytes inválidos abortan

    cuenta, ejemplos = collections.Counter(), collections.defaultdict(list)
    for i, f in enumerate(fs):
        for col, val in f.items():
            for h in hallazgos(val):
                cuenta[h] += 1
                if len(ejemplos[h]) < 3:
                    ejemplos[h].append(f"fila {i} [{col}]: {val[:80]!r}")
    clases = collections.Counter(f[fu["etiqueta"]] for f in fs)

    DATA.mkdir(exist_ok=True)
    destino.write_bytes(datos)
    os.chmod(destino, stat.S_IREAD)  # solo lectura: detectar/evitar modificaciones accidentales
    manifiesto = {"fuente": fu["url"], "repo": fu["repo"], "commit": fu["commit"], "archivo": fu["archivo"],
                  "sha256": fu["sha256"], "bytes": len(datos), "descargado": datetime.date.today().isoformat(),
                  "filas": len(fs), "licencia": fu["licencia"], fu["etiqueta"]: dict(clases), "hallazgos": dict(cuenta)}
    (DATA / f"MANIFEST-{nombre}.json").write_text(json.dumps(manifiesto, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"OK verificado SHA-256 y escrito {destino} ({len(datos):,} bytes, {len(fs):,} filas)")
    print(f"columnas: {list(fs[0])}")
    print(f"{fu['etiqueta']}: {dict(clases)}")
    print(f"hallazgos: {dict(cuenta) or 'ninguno'}")
    for h, ej in ejemplos.items():
        print(f"  {h}:", *ej, sep="\n    ")


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else "tickets")
