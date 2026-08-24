"""Identidad de la compilacion: que build es este.

El numero semantico solo no alcanza. El 23 de agosto de 2026 habia tres
BioStat abiertos en la misma maquina —uno del 1 de julio en el Escritorio, uno
del 16 de junio detras de un acceso directo, y el bueno— y ninguno decia cual
era. Los tres arrancaban igual. Con el del 1 de julio se validaron metodos
durante dos meses con los IC impresos mal.

Lo que responde "¿este es el actual?" no es `0.1.0`: es la FECHA y el COMMIT.
Por eso la etiqueta los lleva a los dos, y el semantico va de acompanamiento.

De donde sale el dato, en orden:

1. `src/_build_info.py`, que `build_exe.py` escribe justo antes de compilar.
   Dentro del .exe no hay repositorio git, asi que el dato tiene que viajar
   horneado. El archivo esta en .gitignore: se regenera en cada build y
   versionarlo solo produciria conflictos.
2. `git` en vivo, cuando se corre desde el codigo fuente.
3. Nada de lo anterior: se dice "sin datos de compilacion" en vez de inventar
   una fecha. Una fecha inventada es peor que ninguna, porque se le cree.
"""
import datetime
import os
import subprocess
import sys

from src import __version__

DESCONOCIDO = "desconocido"


def _desde_archivo():
    """Lo que horneo `build_exe.py`. Es la fuente dentro del .exe."""
    try:
        from src import _build_info
    except ImportError:
        return None
    return {
        "commit": getattr(_build_info, "COMMIT", DESCONOCIDO),
        "rama": getattr(_build_info, "RAMA", DESCONOCIDO),
        "fecha": getattr(_build_info, "FECHA", DESCONOCIDO),
        "sucio": getattr(_build_info, "SUCIO", False),
        "origen": "compilacion",
    }


def _git(*args):
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        salida = subprocess.run(("git",) + args, cwd=raiz, capture_output=True,
                                text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return salida.stdout.strip() if salida.returncode == 0 else None


def _desde_git():
    """Consulta al repositorio. Solo funciona corriendo desde el fuente."""
    commit = _git("rev-parse", "--short", "HEAD")
    if not commit:
        return None
    return {
        "commit": commit,
        "rama": _git("rev-parse", "--abbrev-ref", "HEAD") or DESCONOCIDO,
        "fecha": (_git("log", "-1", "--format=%cd", "--date=short")
                  or datetime.date.today().isoformat()),
        # Un build con cambios sin commitear no es reproducible desde el hash:
        # decirlo evita que alguien confie en un commit que no describe lo que
        # esta corriendo.
        "sucio": bool(_git("status", "--porcelain")),
        "origen": "git",
    }


def congelado():
    """True dentro del .exe de PyInstaller."""
    return getattr(sys, "frozen", False)


def info():
    """Datos de la compilacion. Nunca lanza; nunca inventa.

    El orden depende de donde se corre. Dentro del .exe manda el archivo
    horneado, que es lo unico que hay. Desde el codigo fuente manda git, porque
    un `_build_info.py` que quedo de una compilacion anterior describiria ese
    build y no el arbol de trabajo actual: taparia justo el dato que se quiere.
    """
    fuentes = ((_desde_archivo, _desde_git) if congelado()
               else (_desde_git, _desde_archivo))
    for fuente in fuentes:
        datos = fuente()
        if datos:
            return datos
    return {"commit": DESCONOCIDO, "rama": DESCONOCIDO, "fecha": DESCONOCIDO,
            "sucio": False, "origen": "ninguno"}


def etiqueta(datos=None):
    """Una linea para mostrar. Nunca vacia."""
    d = datos or info()
    if d["commit"] == DESCONOCIDO:
        return f"v{__version__} · sin datos de compilacion"
    partes = [f"v{__version__}", d["fecha"], d["commit"]]
    if d["rama"] not in (DESCONOCIDO, "HEAD"):
        partes.insert(2, d["rama"])
    if d["sucio"]:
        partes.append("con cambios sin commitear")
    return " · ".join(partes)


def escribir_build_info(destino=None):
    """Hornea `src/_build_info.py` con lo que dice git ahora.

    La llama `build_exe.py` antes de compilar. Devuelve el dict escrito.
    """
    d = _desde_git() or {"commit": DESCONOCIDO, "rama": DESCONOCIDO,
                         "fecha": datetime.date.today().isoformat(),
                         "sucio": False}
    destino = destino or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "_build_info.py")
    contenido = (
        '"""Generado por build_exe.py. No editar a mano ni versionar."""\n'
        f'COMMIT = {d["commit"]!r}\n'
        f'RAMA = {d["rama"]!r}\n'
        f'FECHA = {d["fecha"]!r}\n'
        f'SUCIO = {bool(d["sucio"])!r}\n'
        f'COMPILADO = {datetime.datetime.now().isoformat(timespec="seconds")!r}\n'
    )
    with open(destino, "w", encoding="utf-8") as f:
        f.write(contenido)
    return d


if __name__ == "__main__":
    print(etiqueta())
    sys.exit(0)
