"""Inventario de la máquina para este proyecto (spec: openspec/specs/inventario). Solo stdlib.

Genera INVENTARIO.md: modelos vs modelos.json (por digest), almacenes de modelos detectados (Ollama,
Hugging Face, LM Studio), datasets verificados por SHA-256, credenciales SOLO por nombre y ubicación,
herramientas, imágenes y tamaños. Sale con código 1 si falta/cambió un modelo obligatorio o un dataset.
  uv run python scripts/inventario.py
"""
import ctypes
import datetime
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "jev"))
CREDENCIALES = [("API_TOKEN", "router-api"), ("A2A_TOKEN", "a2a-divisas"), ("MCP_TOKEN", "mcp-empresa")]
CLAVE_HMAC = Path(os.getenv("IA_HITL_KEY", str(Path.home() / ".ia-local" / "hitl.key")))


# ---------- funciones puras (tests en scripts/test_inventario.py) ----------
def ruta_legible(ruta: Path) -> str:
    """Home -> '~' y separadores '/': el inventario no expone usuario ni estructura personal."""
    s, home = str(Path(ruta)), str(Path.home())
    return ("~" + s[len(home):] if s.startswith(home) else s).replace("\\", "/")


def comparar_modelos(esperados: list[dict], locales: dict[str, str]) -> dict:
    estados = {m["nombre"]: ("falta" if m["nombre"] not in locales else
                             "ok" if locales[m["nombre"]] == m["digest"] else "distinto") for m in esperados}
    nombres = {m["nombre"] for m in esperados}
    return {"estados": estados, "no_inventariado": sorted(n for n in locales if n not in nombres)}


def inventario_credenciales(env_path: Path, clave_hmac: Path) -> list[dict]:
    """Nombre, archivo, presencia y fortaleza. El valor se lee solo para medir su largo y se descarta."""
    largos = {}
    if env_path.exists():
        for linea in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in linea and not linea.lstrip().startswith("#"):
                k, _, v = linea.partition("=")
                largos[k.strip()] = len(v.strip())
    filas = [{"nombre": n, "archivo": ".env (por máquina, fuera de git)", "usa": s, "presente": n in largos,
              "fuerte": largos.get(n, 0) >= 32} for n, s in CREDENCIALES]
    existe = clave_hmac.exists()
    filas.append({"nombre": "clave HMAC de checkpoints", "archivo": ruta_legible(clave_hmac), "usa": "lab 11 (HITL)",
                  "presente": existe, "fuerte": existe and clave_hmac.stat().st_size >= 32})
    return filas


def render_credenciales(filas: list[dict]) -> str:
    si = lambda b: "sí" if b else "no"
    return "\n".join(["| Credencial | Dónde vive | La usa | Presente | ≥32 bytes |", "|---|---|---|---|---|"] +
                     [f"| {f['nombre']} | {f['archivo']} | {f['usa']} | {si(f['presente'])} | {si(f['fuerte'])} |" for f in filas])


def validar_manifiesto(doc: dict) -> list[str]:
    errores, nombres, digests = [], set(), set()
    for m in doc.get("modelos", []):
        n = m.get("nombre", "?")
        d = str(m.get("digest", ""))
        if len(d) != 64 or any(c not in "0123456789abcdef" for c in d):
            errores.append(f"{n}: digest inválido")
        if not isinstance(m.get("bytes"), int) or m["bytes"] <= 0:
            errores.append(f"{n}: bytes inválido")
        if not isinstance(m.get("obligatorio"), bool):
            errores.append(f"{n}: obligatorio no es booleano")
        if not str(m.get("rol", "")).strip():
            errores.append(f"{n}: sin rol")
        if n in nombres:
            errores.append(f"{n}: nombre repetido")
        if d in digests and len(d) == 64:
            errores.append(f"{n}: digest repetido")
        nombres.add(n)
        digests.add(d)
    return errores


def recomendar(ram_gb: float, candidatos: list[dict]) -> list[dict]:
    return sorted((c for c in candidatos if c["ram_min_gb"] <= ram_gb), key=lambda c: -c["ram_min_gb"])


# ---------- lectura de la máquina ----------
def gb(n: int) -> str:
    return f"{n / 1e9:.2f} GB"


def tamano(p: Path) -> int:
    total = 0
    for base, _, archivos in os.walk(p):
        for a in archivos:
            try:
                total += os.lstat(os.path.join(base, a)).st_size
            except OSError:
                pass
    return total


def ram_total() -> float:
    if platform.system() == "Windows":
        class MEM(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                        ("a", ctypes.c_ulonglong), ("b", ctypes.c_ulonglong), ("c", ctypes.c_ulonglong),
                        ("d", ctypes.c_ulonglong), ("e", ctypes.c_ulonglong), ("f", ctypes.c_ulonglong)]
        m = MEM()
        m.dwLength = ctypes.sizeof(MEM)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return m.ullTotalPhys / 2**30
    return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30


def modelos_locales() -> dict[str, str] | None:
    base = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    base = base if base.startswith("http") else f"http://{base}"
    try:
        with urllib.request.urlopen(f"{base}/api/tags", timeout=10) as r:
            return {m["name"]: m["digest"] for m in json.load(r)["models"]}
    except OSError:
        return None


def almacenes() -> list[tuple[str, Path, int]]:
    home = Path.home()
    candidatos = [
        ("Ollama (OLLAMA_MODELS)" if os.getenv("OLLAMA_MODELS") else "Ollama", Path(os.getenv("OLLAMA_MODELS", home / ".ollama" / "models"))),
        ("Hugging Face (HF_HOME)" if os.getenv("HF_HOME") else "Hugging Face", Path(os.getenv("HF_HOME", home / ".cache" / "huggingface"))),
        ("LM Studio", home / ".lmstudio" / "models"),
        ("LM Studio (antiguo)", home / ".cache" / "lm-studio" / "models"),
    ]
    return [(n, p, tamano(p)) for n, p in candidatos if p.exists()]


def herramienta(cmd: str) -> str:
    if not shutil.which(cmd):
        return "no instalado"
    try:
        out = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=20)
        return (out.stdout or out.stderr).strip().splitlines()[0]
    except (OSError, subprocess.SubprocessError, IndexError):
        return "instalado (versión no disponible)"


def main() -> int:
    import ingesta
    manif = json.loads((RAIZ / "modelos.json").read_text(encoding="utf-8"))
    if errores := validar_manifiesto(manif):
        print("modelos.json inválido:", errores)
        return 1
    locales = modelos_locales()
    ram = ram_total()
    problemas, L = [], []
    L += [f"# Inventario — generado {datetime.date.today().isoformat()}", "",
          "Regenerar: `uv run python scripts/inventario.py`. Rutas con `~`; credenciales solo por nombre (nunca valores).", "",
          "## Máquina", "",
          f"- Sistema: {platform.system()} {platform.release()} ({platform.machine()}) · RAM {ram:.0f} GB · CPUs {os.cpu_count()}",
          f"- Python del proyecto: {platform.python_version()}", ""]

    L += ["## Modelos (manifiesto `modelos.json`)", ""]
    if locales is None:
        L += ["Ollama no responde: no se pudo verificar (¿`ollama serve`?).", ""]
        problemas.append("Ollama no responde")
    else:
        cmp = comparar_modelos(manif["modelos"], locales)
        L += ["| Modelo | Rol | Obligatorio | Tamaño | Estado | Uso |", "|---|---|---|---|---|---|"]
        for m in manif["modelos"]:
            est = cmp["estados"][m["nombre"]]
            L.append(f"| {m['nombre']} | {m['rol']} | {'sí' if m['obligatorio'] else 'no'} | {gb(m['bytes'])} | {est} | {m['uso']} |")
            if m["obligatorio"] and est != "ok":
                problemas.append(f"modelo {m['nombre']}: {est}")
        L += ["", f"Otros modelos locales (de otros proyectos): {', '.join(cmp['no_inventariado']) or 'ninguno'}", ""]
    L += ["### Almacenes de modelos detectados en esta máquina", "", "| Almacén | Ruta | Tamaño |", "|---|---|---|"]
    L += [f"| {n} | {ruta_legible(p)} | {gb(t)} |" for n, p, t in almacenes()] + [""]
    rec = recomendar(round(ram), manif["candidatos_mac"])  # un equipo de "24 GB" reporta ~23.7 GiB utilizables
    L += [f"### Candidatos que caben en {ram:.0f} GB de RAM (medir con `jev/eval_bitext.py` antes de adoptar)", ""]
    L += [f"- `{c['nombre']}` ({gb(c['bytes'])}, ≥{c['ram_min_gb']} GB RAM): {c['uso']}" for c in rec] or ["- ninguno"]
    L.append("")

    L += ["## Datasets (verificados por SHA-256 contra su manifiesto)", "", "| Fuente | Archivo | Tamaño | Estado | Licencia |", "|---|---|---|---|---|"]
    for nombre, fu in ingesta.FUENTES.items():
        p = ingesta.DATA / fu["archivo"]
        try:
            ingesta.verificar(p.read_bytes(), fu["sha256"], ingesta.MAX_BYTES)
            est = "ok"
        except (OSError, ValueError) as e:
            est = "falta" if isinstance(e, OSError) else "NO VERIFICA"
            problemas.append(f"dataset {nombre}: {est}")
        L.append(f"| {nombre} | {fu['archivo'][:48]} | {gb(p.stat().st_size) if p.exists() else '-'} | {est} | {fu['licencia'].split(' (')[0]} |")
    L.append("")

    L += ["## Credenciales", "", render_credenciales(inventario_credenciales(RAIZ / ".env", CLAVE_HMAC)), "",
          "Generar/rotar tokens: borra `.env` y ejecuta `uv run python scripts/generar_env.py`. "
          "Rotar la clave HMAC invalida los checkpoints pendientes del lab 11 (por diseño).", ""]

    imgs = re.findall(r"([\w./-]+:[\w.-]+@sha256:[0-9a-f]{64})", (RAIZ / "Dockerfile").read_text(encoding="utf-8") +
                      (RAIZ / "compose.yaml").read_text(encoding="utf-8"))
    L += ["## Imágenes de contenedor (fijadas por digest)", ""] + [f"- `{i.split('@')[0]}` @ `{i.split('@')[1][:19]}…`" for i in dict.fromkeys(imgs)] + [""]

    L += ["## Herramientas", "", "| Herramienta | Versión |", "|---|---|"]
    L += [f"| {c} | {herramienta(c)} |" for c in ("uv", "ollama", "git", "gh", "docker", "openspec")] + [""]

    venv = RAIZ / ".venv"
    L += ["## Proyecto", "",
          f"- Labs: {len(list((RAIZ / 'labs').glob('[0-9][0-9]_*.py')))} · specs OpenSpec: {len(list((RAIZ / 'openspec' / 'specs').iterdir()))} "
          f"· changes archivados: {len(list((RAIZ / 'openspec' / 'changes' / 'archive').iterdir()))} "
          f"· suites de tests: {len(list(RAIZ.glob('*/test_*.py')))}",
          f"- Tamaños: .venv {gb(tamano(venv)) if venv.exists() else '-'} · data {gb(tamano(RAIZ / 'data'))}",
          f"- Paquetes Python en uv.lock: {(RAIZ / 'uv.lock').read_text(encoding='utf-8').count('[[package]]')}", ""]

    L += ["## Estado", "", ("✅ Todo lo obligatorio está presente y verificado." if not problemas else
                            "❌ " + "; ".join(problemas)), ""]
    (RAIZ / "INVENTARIO.md").write_text("\n".join(L), encoding="utf-8")
    print(f"INVENTARIO.md escrito | problemas: {problemas or 'ninguno'}")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
