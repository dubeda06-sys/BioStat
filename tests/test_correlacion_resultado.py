"""«Correlación» migrada a `Resultado` (paso 4, familia 2).

Oráculos: scipy (r, ρ, p y el IC de Pearson) y pingouin (la parcial, con su
IC). Lo nuevo respecto del panel viejo son los IC 95 %: por la z de Fisher para
Pearson y la parcial, y con el EE de Bonett y Wright para Spearman.
"""
import os
import re
from html import unescape

import numpy as np
import pandas as pd
import pingouin as pg
import pytest
from scipy import stats

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.resultado import render_html  # noqa: E402
from src.resultado.constructores import parcial, pearson, spearman  # noqa: E402
from src.resultado.constructores.correlacion import fuerza  # noqa: E402

RNG = np.random.default_rng(3)
_Z = RNG.normal(0, 1, 60)
HOJA = pd.DataFrame({"x": _Z + RNG.normal(0, 0.7, 60), "y": _Z + RNG.normal(0, 0.7, 60),
                     "z": _Z, "ruido": RNG.normal(0, 1, 60)})


def _v(res, empieza):
    return next(v for v in res.valores if v.nombre.startswith(empieza))


def _paso(res, texto):
    return next(s for s in res.supuestos if texto in s.pregunta)


def _texto(res):
    return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", render_html(res)))).strip()


def test_pearson_contra_scipy():
    res = pearson(HOJA, "x", "y")
    ref = stats.pearsonr(HOJA["x"], HOJA["y"])
    assert _v(res, "r de Pearson").valor == pytest.approx(ref.statistic)
    ic = ref.confidence_interval()
    assert _v(res, "r de Pearson").ic == pytest.approx((ic.low, ic.high))
    assert _paso(res, "¿Hay").respuesta == "Se detectó, positiva"


def test_spearman_contra_scipy_con_el_ic_de_bonett_wright():
    res = spearman(HOJA, "x", "y")
    rho = stats.spearmanr(HOJA["x"], HOJA["y"]).statistic
    assert _v(res, "ρ de Spearman").valor == pytest.approx(rho)
    ee = np.sqrt((1 + rho ** 2 / 2) / (60 - 3))
    lo, hi = np.tanh(np.arctanh(rho) + np.array([-1, 1]) * 1.959964 * ee)
    assert _v(res, "ρ de Spearman").ic == pytest.approx((lo, hi), abs=1e-6)


def test_el_ic_de_spearman_cubre_el_95():
    """El EE de Pearson (1/√(n−3)) aplicado a ρ cubre de menos; Bonett-Wright no."""
    from src.core.statistics import spearman_rho
    rng = np.random.default_rng(8)
    cov = [[1, 0.6], [0.6, 1]]
    verdadero = 6 / np.pi * np.arcsin(0.6 / 2)       # ρ poblacional de una normal
    cubre = 0
    for _ in range(600):
        x, y = rng.multivariate_normal([0, 0], cov, 40).T
        lo, hi = spearman_rho(x, y)["ci95"]
        cubre += lo <= verdadero <= hi
    assert cubre / 600 == pytest.approx(0.95, abs=0.025)


def test_parcial_contra_pingouin():
    res = parcial(HOJA, "x", "y", "z")
    ref = pg.partial_corr(HOJA, "x", "y", covar="z")
    assert _v(res, "r parcial").valor == pytest.approx(ref["r"].iloc[0])
    assert _v(res, "r parcial").ic == pytest.approx(tuple(ref["CI95"].iloc[0]), abs=0.005)
    assert float(_v(res, "p").valor) == pytest.approx(ref["p_val"].iloc[0], abs=5e-5)


def test_parcial_dice_cuanto_pasa_por_la_tercera():
    """x e y se correlacionan solo porque las dos dependen de z."""
    res = parcial(HOJA, "x", "y", "z")
    assert _paso(res, "pasa por").respuesta == "Casi toda"
    assert _v(res, "r simple").valor > 0.5
    res = parcial(HOJA, "x", "y", "ruido")
    assert _paso(res, "pasa por").respuesta == "Poca"


def test_la_normalidad_de_pearson_sugiere_spearman():
    hoja = HOJA.assign(sesgada=np.exp(HOJA["x"] * 1.5))
    paso = _paso(pearson(hoja, "sesgada", "y"), "normales")
    assert paso.respuesta.startswith("No") and "Spearman" in paso.consecuencia


def test_sin_correlacion():
    res = pearson(HOJA, "x", "ruido")
    assert _paso(res, "¿Hay").respuesta == "No se detectó"
    assert res.lectura.startswith("No se detectó")


def test_palabras_de_mukaka():
    assert [fuerza(r) for r in (0.95, -0.75, 0.55, 0.35, 0.1)] == [
        "muy alta", "alta", "moderada", "baja", "despreciable"]


@pytest.mark.parametrize("llamar, motivo", [
    (lambda: pearson(HOJA, "x", "x"), "columnas distintas"),
    (lambda: spearman(HOJA, "x", "nada"), "no está en la hoja"),
    (lambda: pearson(pd.DataFrame({"a": [1.0, 2], "b": [2.0, 3]}), "a", "b"), "al menos 3"),
    (lambda: pearson(pd.DataFrame({"a": [1.0, 1, 1, 1], "b": [1.0, 2, 3, 4]}), "a", "b"),
     "constante"),
])
def test_rechazos_con_motivo(llamar, motivo):
    res = llamar()
    assert not res.ok and motivo in res.error


def test_los_pares_quedan_alineados():
    hoja = HOJA.copy()
    hoja.loc[0, "x"] = np.nan
    res = pearson(hoja, "x", "y")
    assert res.entrada.n == 59 and res.entrada.descartadas == 1
    assert _v(res, "r de Pearson").valor == pytest.approx(
        stats.pearsonr(hoja["x"][1:], hoja["y"][1:]).statistic)


@pytest.mark.parametrize("res", [pearson(HOJA, "x", "y"), spearman(HOJA, "x", "y"),
                                 parcial(HOJA, "x", "y", "z")], ids=["pearson", "spearman",
                                                                     "parcial"])
def test_informe_y_figura(res):
    import matplotlib.pyplot as plt
    t = _texto(res)
    assert "Correlación no es acuerdo" in t and "significativ" not in t.lower()
    fig = res.figuras[0].dibujar()
    assert fig.axes
    plt.close(fig)


@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("analisis", ["Correlacion de Pearson", "Correlacion de Spearman",
                                      "Correlacion parcial"])
def test_el_panel(qt_app, analisis):
    from src.ui.analysis_panel import AnalysisPanel
    panel = AnalysisPanel()
    panel.set_data(HOJA)
    panel.combo_analysis.setCurrentText(analisis)
    panel.combo_col1.setCurrentText("x")
    panel.combo_col2.setCurrentText("y")
    panel.combo_col3.setCurrentText("z")
    panel._run()
    assert "Qué se verificó y qué se decidió" in panel.txt_results.toPlainText()


def test_la_parcial_sin_tercera_variable_lo_pide(qt_app):
    from src.ui.analysis_panel import AnalysisPanel
    panel = AnalysisPanel()
    panel.set_data(HOJA)
    panel.combo_analysis.setCurrentText("Correlacion parcial")
    panel.combo_col3.setCurrentText("(ninguna)")
    panel._run()
    assert "Variable 3" in panel.txt_results.toPlainText()
