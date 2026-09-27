"""Gráficos de comparación migrados a `Resultado` (paso 4, familia 9).

Cambian a propósito, cada uno con su test: el gráfico de Youden pasa a ser el
interlaboratorio de MedCalc (antes, el índice J contra el umbral, que es de
ROC), la cascada es la de oncología (barras ordenadas; antes una cascada
contable acumulada) y el polar usa las columnas elegidas (antes, las 8
primeras de la hoja).
"""
import os
import re
from html import unescape

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.core.plots import mountain_plot_data  # noqa: E402
from src.resultado import render_html  # noqa: E402
from src.resultado.constructores import cascada, mountain, polar, youden  # noqa: E402

RNG = np.random.default_rng(71)


def _labs(n=40, sistematico=0.0):
    sesgo = RNG.normal(0, sistematico, n)
    return pd.DataFrame({"m1": 100 + sesgo + RNG.normal(0, 2, n),
                         "m2": 104 + sesgo + RNG.normal(0, 2, n)})


def _v(res, empieza):
    return next(v for v in res.valores if v.nombre.startswith(empieza))


def test_mountain_es_el_del_core():
    hoja = pd.DataFrame({"a": RNG.normal(10, 1, 50), "b": RNG.normal(10.5, 1, 50)})
    res = mountain(hoja, "a", "b")
    assert _v(res, "Mediana").valor == pytest.approx(mountain_plot_data(hoja["a"], hoja["b"])["mediana"])


def test_youden_es_interlaboratorio():
    """Cambió a propósito: antes graficaba el índice J contra el umbral."""
    hoja = _labs()
    hoja.loc[0, ["m1", "m2"]] = [108, 112]          # un laboratorio con sesgo propio
    res = youden(hoja, "m1", "m2")
    r = res.crudo["youden"]
    assert not r["lejanos"].any()
    assert r["mediana_x"] == pytest.approx(np.median(hoja["m1"]))
    assert r["fuera_del_circulo"][0]
    assert abs(r["perpendicular"][0]) < abs(r["a_lo_largo"][0])     # sistemático, no aleatorio


def test_youden_el_circulo_cubre_el_95():
    fuera = total = 0
    for _ in range(200):
        r = youden(_labs(), "m1", "m2").crudo["youden"]
        fuera += r["fuera_del_circulo"].sum()
        total += r["n"]
    assert fuera / total == pytest.approx(0.05, abs=0.015)


def test_youden_excluye_lejanos_de_las_medianas():
    hoja = _labs()
    hoja.loc[1, ["m1", "m2"]] = [500, 504]
    r = youden(hoja, "m1", "m2").crudo["youden"]
    assert r["lejanos"][1]
    assert r["mediana_x"] == pytest.approx(np.median(np.delete(hoja["m1"].to_numpy(), 1)))


def test_cascada_ordena_de_mayor_a_menor():
    """Cambió a propósito: antes era una cascada contable acumulada."""
    hoja = pd.DataFrame({"cambio": [-40, 10, -25, 35, -5, 0]})
    res = cascada(hoja, "cambio")
    assert list(res.crudo["valores_ordenados"]) == [35, 10, 0, -5, -25, -40]
    assert _v(res, "Disminuyen").valor == 3 and _v(res, "Aumentan").valor == 2


def test_polar_usa_las_columnas_elegidas():
    hoja = pd.DataFrame(RNG.normal(10, 1, (20, 5)), columns=list("abcde"))
    res = polar(hoja, ["a", "c", "e"])
    assert list(res.crudo["medias"]) == ["a", "c", "e"]
    assert "al menos 3" in polar(hoja, ["a", "b"]).error


@pytest.mark.parametrize("res", [
    mountain(pd.DataFrame({"a": RNG.normal(0, 1, 50), "b": RNG.normal(0, 1, 50)}), "a", "b"),
    youden(_labs(), "m1", "m2"),
    polar(pd.DataFrame(RNG.normal(10, 1, (20, 3)), columns=list("abc")), list("abc")),
    cascada(pd.DataFrame({"x": RNG.normal(-10, 30, 25)}), "x")],
    ids=["mountain", "youden", "polar", "cascada"])
def test_informe_y_figura(res):
    import matplotlib.pyplot as plt
    assert res.ok, res.error
    t = unescape(re.sub(r"<[^>]+>", " ", render_html(res)))
    assert "Qué se verificó" in t and "significativ" not in t.lower()
    fig = res.figuras[0].dibujar()
    assert fig.axes
    plt.close(fig)


@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("analisis, elegidas", [
    ("Mountain plot", None), ("Youden plot", None), ("Waterfall chart", None),
    ("Polar plot", ["m1", "m2", "m3"])])
def test_el_panel(qt_app, analisis, elegidas):
    from src.ui.analysis_panel import AnalysisPanel
    panel = AnalysisPanel()
    panel.set_data(_labs().assign(m3=lambda d: d["m1"] + 1))
    panel.combo_analysis.setCurrentText(analisis)
    panel.combo_col1.setCurrentText("m1")
    panel.combo_col2.setCurrentText("m2")
    panel.columnas_elegidas = elegidas
    panel._run()
    assert "Qué se verificó y qué se decidió" in panel.txt_results.toPlainText()
