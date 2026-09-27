"""«Pruebas no paramétricas» migradas a `Resultado` (paso 4, familia 6).

Oráculos: scipy (mannwhitneyu, wilcoxon, kruskal, friedmanchisquare, binomtest)
y statsmodels (Cochran). Lo nuevo es Hodges-Lehmann con su IC (cobertura
simulada) y que Kruskal-Wallis corra Dunn cuando detecta.
"""
import os
import re
from html import unescape

import numpy as np
import pandas as pd
import pytest
from scipy import stats

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.core.statistics import hodges_lehmann  # noqa: E402
from src.resultado import render_html  # noqa: E402
from src.resultado.constructores import (  # noqa: E402
    cochran, friedman, kruskal, mann_whitney, signos, wilcoxon,
)

RNG = np.random.default_rng(41)
_B = RNG.normal(10, 2, 30)
HOJA = pd.DataFrame({"a": RNG.exponential(2, 30), "b": RNG.exponential(2, 30) + 1.5,
                     "antes": _B, "despues": _B + RNG.exponential(1, 30),
                     "c3": _B + 2 + RNG.normal(0, 1, 30),
                     "t1": RNG.integers(0, 2, 30).astype(float),
                     "t2": RNG.integers(0, 2, 30).astype(float),
                     "t3": (RNG.uniform(0, 1, 30) < 0.8).astype(float)})


def _v(res, empieza):
    return next(v for v in res.valores if v.nombre.startswith(empieza))


def _texto(res):
    return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", render_html(res)))).strip()


def test_mann_whitney_contra_scipy_con_hodges_lehmann():
    res = mann_whitney(HOJA, "a", "b")
    ref = stats.mannwhitneyu(HOJA["a"], HOJA["b"], alternative="two-sided")
    assert _v(res, "U").valor == pytest.approx(ref.statistic)
    dif = np.subtract.outer(HOJA["a"].to_numpy(), HOJA["b"].to_numpy()).ravel()
    assert _v(res, "Corrimiento").valor == pytest.approx(np.median(dif))


def test_hodges_lehmann_cubre_el_95():
    rng = np.random.default_rng(0)
    dos = una = 0
    for _ in range(800):
        x, y = rng.standard_t(4, 25) + 1, rng.standard_t(4, 30)
        lo, hi = hodges_lehmann(x, y)["ic95"]
        dos += lo <= 1 <= hi
        lo, hi = hodges_lehmann(rng.standard_t(4, 20) + 0.5)["ic95"]
        una += lo <= 0.5 <= hi
    assert dos / 800 == pytest.approx(0.95, abs=0.02)
    assert una / 800 == pytest.approx(0.95, abs=0.02)


def test_wilcoxon_contra_scipy():
    res = wilcoxon(HOJA, "despues", "antes")
    ref = stats.wilcoxon(HOJA["despues"], HOJA["antes"])
    assert _v(res, "W").valor == pytest.approx(ref.statistic)
    assert res.crudo["wilcoxon"]["p"] == pytest.approx(ref.pvalue)
    d = (HOJA["despues"] - HOJA["antes"]).to_numpy()
    assert _v(res, "Pseudomediana").valor == pytest.approx(hodges_lehmann(d)["estimacion"])


def test_wilcoxon_avisa_la_asimetria():
    paso = next(s for s in wilcoxon(HOJA, "despues", "antes").supuestos if "simétricas" in s.pregunta)
    assert paso.respuesta == "No" and "signos" in paso.consecuencia


def test_kruskal_contra_scipy_y_dunn():
    largo = pd.DataFrame({"y": np.r_[RNG.normal(0, 1, 20), RNG.normal(0, 1, 20),
                                     RNG.normal(2, 1, 20)],
                          "g": np.repeat(["A", "B", "C"], 20)})
    res = kruskal(largo, "y", "g")
    ref = stats.kruskal(*[g["y"] for _, g in largo.groupby("g")])
    assert _v(res, "H").valor == pytest.approx(ref.statistic)
    assert res.crudo["posthoc"]["metodo"].startswith("Dunn")


def test_friedman_contra_scipy():
    res = friedman(HOJA, ["antes", "despues", "c3"])
    ref = stats.friedmanchisquare(HOJA["antes"], HOJA["despues"], HOJA["c3"])
    assert _v(res, "χ²").valor == pytest.approx(ref.statistic)
    assert _v(res, "W de Kendall").valor == pytest.approx(ref.statistic / (30 * 2))


def test_signos_contra_binomial():
    res = signos(HOJA, "despues", "antes")
    d = (HOJA["despues"] - HOJA["antes"]).to_numpy()
    d = d[d != 0]
    ref = stats.binomtest(int((d > 0).sum()), len(d), 0.5)
    assert res.crudo["signos"]["p"] == pytest.approx(ref.pvalue)


def test_cochran_contra_statsmodels():
    from statsmodels.stats.contingency_tables import cochrans_q
    res = cochran(HOJA, ["t1", "t2", "t3"])
    ref = cochrans_q(HOJA[["t1", "t2", "t3"]].to_numpy())
    assert _v(res, "Q").valor == pytest.approx(ref.statistic)


def test_cochran_rechaza_lo_que_no_es_0_1():
    assert "0/1" in cochran(HOJA, ["a", "b"]).error


@pytest.mark.parametrize("res", [
    mann_whitney(HOJA, "a", "b"), wilcoxon(HOJA, "despues", "antes"),
    friedman(HOJA, ["antes", "despues", "c3"]), signos(HOJA, "despues", "antes"),
    cochran(HOJA, ["t1", "t2", "t3"])],
    ids=["mw", "wilcoxon", "friedman", "signos", "cochran"])
def test_informe(res):
    import matplotlib.pyplot as plt
    assert res.ok, res.error
    t = _texto(res)
    assert "Qué se verificó" in t and "significativ" not in t.lower()
    for figura in res.figuras:
        fig = figura.dibujar()
        plt.close(fig)


@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("analisis, c1, c2, elegidas", [
    ("Mann-Whitney U", "a", "b", None), ("Wilcoxon pareado", "despues", "antes", None),
    ("Kruskal-Wallis", "a", "t1", None), ("Friedman", "a", "b", ["antes", "despues", "c3"]),
    ("Sign test", "despues", "antes", None), ("Cochran Q", "a", "b", ["t1", "t2", "t3"]),
])
def test_el_panel(qt_app, analisis, c1, c2, elegidas):
    from src.ui.analysis_panel import AnalysisPanel
    panel = AnalysisPanel()
    panel.set_data(HOJA)
    panel.combo_analysis.setCurrentText(analisis)
    panel.combo_col1.setCurrentText(c1)
    panel.combo_col2.setCurrentText(c2)
    panel.columnas_elegidas = elegidas
    panel._run()
    assert "Qué se verificó y qué se decidió" in panel.txt_results.toPlainText()
