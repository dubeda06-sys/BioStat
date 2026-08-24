"""La identidad de la compilacion en la pantalla de carga.

El 23 de agosto de 2026 habia tres BioStat abiertos en la misma maquina y
ninguno decia cual era. Con el del 1 de julio se validaron metodos durante dos
meses con los intervalos de confianza impresos mal. Estos tests cubren la
propiedad que evita que se repita: **la pantalla siempre dice que build es, y
cuando no lo sabe lo dice en vez de inventarlo**.
"""
import datetime
import os
import subprocess
import sys

import pytest

from src import __version__, version


# ---------------- Nunca inventa ----------------

def test_sin_git_y_sin_archivo_lo_dice_en_vez_de_inventar(monkeypatch):
    """Una fecha inventada es peor que ninguna: se le cree."""
    monkeypatch.setattr(version, "_desde_git", lambda: None)
    monkeypatch.setattr(version, "_desde_archivo", lambda: None)
    d = version.info()
    assert d["commit"] == version.DESCONOCIDO
    assert d["fecha"] == version.DESCONOCIDO
    assert "sin datos" in version.etiqueta(d)


def test_la_etiqueta_nunca_sale_vacia():
    """Es lo unico que se ve; un string vacio deja la esquina en blanco y nadie
    se entera de que falta."""
    assert version.etiqueta().strip()
    for d in ({"commit": version.DESCONOCIDO, "rama": version.DESCONOCIDO,
               "fecha": version.DESCONOCIDO, "sucio": False, "origen": "ninguno"},
              {"commit": "abc1234", "rama": "develop", "fecha": "2026-08-23",
               "sucio": False, "origen": "git"}):
        assert version.etiqueta(d).strip()


def test_git_que_falla_no_tumba_la_app(monkeypatch):
    """Si no hay git instalado, o el timeout salta, la app tiene que arrancar
    igual: la version es informativa, no funcional."""
    def revienta(*args, **kwargs):
        raise OSError("git no existe")
    monkeypatch.setattr(subprocess, "run", revienta)
    monkeypatch.setattr(version, "_desde_archivo", lambda: None)
    assert version.info()["commit"] == version.DESCONOCIDO
    assert version.etiqueta().strip()


# ---------------- El dato util es la fecha y el commit ----------------

def test_la_etiqueta_lleva_fecha_y_commit():
    """`v0.1.0` no contesta "¿es este el build actual?". La fecha y el commit si."""
    d = {"commit": "eb45d39", "rama": "develop", "fecha": "2026-08-23",
         "sucio": False, "origen": "git"}
    e = version.etiqueta(d)
    assert "2026-08-23" in e and "eb45d39" in e
    assert __version__ in e


def test_avisa_cuando_el_build_tiene_cambios_sin_commitear():
    """Un build sucio no es reproducible desde su hash. Citar ese commit como
    si describiera lo que corrio es el error que esto evita."""
    d = {"commit": "eb45d39", "rama": "develop", "fecha": "2026-08-23",
         "sucio": True, "origen": "git"}
    assert "sin commitear" in version.etiqueta(d)


def test_head_suelto_no_se_muestra_como_rama():
    """En detached HEAD git devuelve la cadena 'HEAD', que no es un nombre de
    rama y solo confunde."""
    d = {"commit": "eb45d39", "rama": "HEAD", "fecha": "2026-08-23",
         "sucio": False, "origen": "git"}
    assert "HEAD" not in version.etiqueta(d)


# ---------------- Precedencia ----------------

def test_desde_el_fuente_manda_git(monkeypatch):
    """Un _build_info.py que quedo de una compilacion anterior describe ESE
    build, no el arbol de trabajo: taparia justo el dato que se quiere."""
    monkeypatch.setattr(version, "congelado", lambda: False)
    monkeypatch.setattr(version, "_desde_git", lambda: {"commit": "gitgit",
        "rama": "develop", "fecha": "2026-08-23", "sucio": False, "origen": "git"})
    monkeypatch.setattr(version, "_desde_archivo", lambda: {"commit": "viejo00",
        "rama": "master", "fecha": "2026-06-16", "sucio": False,
        "origen": "compilacion"})
    assert version.info()["commit"] == "gitgit"


def test_dentro_del_exe_manda_el_archivo(monkeypatch):
    """No hay repositorio git dentro del .exe: el horneado es lo unico que hay."""
    monkeypatch.setattr(version, "congelado", lambda: True)
    monkeypatch.setattr(version, "_desde_git", lambda: None)
    monkeypatch.setattr(version, "_desde_archivo", lambda: {"commit": "horneado",
        "rama": "develop", "fecha": "2026-08-23", "sucio": False,
        "origen": "compilacion"})
    assert version.info()["commit"] == "horneado"


# ---------------- El archivo horneado ----------------

def test_el_build_info_generado_es_python_valido(tmp_path):
    destino = tmp_path / "_build_info.py"
    version.escribir_build_info(str(destino))
    espacio = {}
    exec(compile(destino.read_text(encoding="utf-8"), str(destino), "exec"), espacio)
    for clave in ("COMMIT", "RAMA", "FECHA", "SUCIO", "COMPILADO"):
        assert clave in espacio
    datetime.date.fromisoformat(espacio["FECHA"])


def test_el_spec_declara_el_modulo_horneado():
    """Se importa dentro de un try/except, asi que si no se nombra en el spec
    PyInstaller puede no incluirlo y el exe pierde su identidad."""
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = open(os.path.join(raiz, "biostat.spec"), encoding="utf-8").read()
    assert "src._build_info" in spec


def test_el_build_info_no_se_versiona():
    """Se regenera en cada build: versionarlo solo produce conflictos."""
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ignore = open(os.path.join(raiz, ".gitignore"), encoding="utf-8").read()
    assert "_build_info" in ignore


# ---------------- La imagen ----------------

def test_la_ventana_de_carga_se_genera_con_la_version():
    """La version va dibujada en el PNG porque la unica linea de texto del
    splash la ocupa la barra de progreso."""
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    r = subprocess.run([sys.executable, os.path.join("scripts", "make_splash.py")],
                       cwd=raiz, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    png = os.path.join(raiz, "assets", "splash.png")
    assert os.path.exists(png) and os.path.getsize(png) > 1000


def test_el_generador_del_splash_dibuja_la_version():
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fuente = open(os.path.join(raiz, "scripts", "make_splash.py"),
                  encoding="utf-8").read()
    assert "__version__" in fuente and "info()" in fuente


def test_el_build_hornea_la_identidad_antes_de_compilar():
    """Si el splash no se regenerara en cada build, el exe nuevo mostraria el
    commit del anterior: peor que no mostrar nada."""
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    build = open(os.path.join(raiz, "build_exe.py"), encoding="utf-8").read()
    assert "escribir_build_info" in build
    assert build.index("escribir_build_info") < build.index("make_splash.py")
