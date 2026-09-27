"""«Proporciones y tablas» migradas a `Resultado` (paso 4, familia 7).

Oráculos: scipy (chi2_contingency, fisher_exact, odds_ratio condicional,
association), statsmodels (StratifiedTable para CMH y Breslow-Day). Cambios a
propósito: CMH toma exposición, evento y estrato de datos crudos (antes partía
la hoja entera en tablas 2×2), y «Comparar 2 proporciones» toma sus cuatro
conteos del diálogo.
"""
import os
import re
from html import unescape

import numpy as np
import pandas as pd
import pytest
from scipy import stats
from scipy.stats.contingency import association, odds_ratio as or_scipy

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.analysis.omni_analyzer import run_omnianalysis  # noqa: E402
from src.resultado import render_html  # noqa: E402
from src.resultado.constructores import (  # noqa: E402
    EJEMPLOS, chi_cuadrado, cmh, dos_proporciones, fisher, mcnemar, odds_ratio_tabla,
    riesgo_relativo,
)

RNG = np.random.default_rng(51)
N = 200
_EXP = (RNG.uniform(0, 1, N) < 0.4).astype(int)
HOJA = pd.DataFrame({
    "expuesto": _EXP,
    "evento": (RNG.uniform(0, 1, N) < np.where(_EXP == 1, 0.45, 0.2)).astype(int),
    "sexo": RNG.choice(["F", "M"], N),
    "grupo": RNG.choice(["A", "B", "C"], N),
    "antes": (RNG.uniform(0, 1, N) < 0.3).astype(int),
})
HOJA["despues"] = np.where(RNG.uniform(0, 1, N) < 0.8, HOJA["antes"], 1)


def _v(res, empieza):
    return next(v for v in res.valores if v.nombre.startswith(empieza))


def _tabla(df, f, c):
    return pd.crosstab(df[f], df[c]).loc[[1, 0], [1, 0]].to_numpy()


def test_chi_cuadrado_contra_scipy_y_cramer():
    res = chi_cuadrado(HOJA, "grupo", "evento")
    t = pd.crosstab(HOJA["grupo"], HOJA["evento"]).to_numpy()
    ref = stats.chi2_contingency(t)
    assert _v(res, "χ²").valor == pytest.approx(ref.statistic)
    assert _v(res, "V de Cramér").valor == pytest.approx(association(t, method="cramer"))


def test_chi_cuadrado_con_esperadas_chicas_sigue_al_omnianalisis():
    chica = pd.DataFrame({"x": ["a"] * 12 + ["b"] * 4 + ["c"] * 3,
                          "y": ["s"] * 10 + ["n"] * 2 + ["s"] * 1 + ["n"] * 3 + ["n"] * 3})
    res = chi_cuadrado(chica, "x", "y")
    assert res.crudo["camino"] == "Chi-cuadrado con p por simulación"
    rep = run_omnianalysis(chica, ["x", "y"])
    bloque = next(b for b in rep["blocks"] if b.get("tipo") == "tabla de contingencia")
    assert bloque["pruebas"][0]["p"] == pytest.approx(res.crudo["p"], abs=1e-4)


def test_fisher_con_su_or_condicional():
    res = fisher(HOJA, "expuesto", "evento")
    t = _tabla(HOJA, "expuesto", "evento")
    assert res.crudo["p"] == pytest.approx(stats.fisher_exact(t).pvalue)
    ref = or_scipy(t, kind="conditional")
    assert _v(res, "OR").valor == pytest.approx(ref.statistic)


def test_mcnemar_exacto_con_pocos_discordantes():
    res = mcnemar(HOJA, "antes", "despues")
    t = _tabla(HOJA, "antes", "despues")
    b, c = t[0, 1], t[1, 0]
    if b + c < 25:
        assert res.crudo["mcnemar"]["p"] == pytest.approx(
            stats.binomtest(min(b, c), b + c, 0.5).pvalue)


def test_odds_ratio_y_riesgo_relativo():
    t = _tabla(HOJA, "expuesto", "evento")
    (a, b), (c, d) = t
    res = odds_ratio_tabla(HOJA, "expuesto", "evento")
    assert _v(res, "OR").valor == pytest.approx(a * d / (b * c))
    se = np.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
    assert _v(res, "OR").ic == pytest.approx(tuple(np.exp(np.log(a * d / (b * c)) + np.array([-1, 1]) * 1.96 * se)))
    rr = riesgo_relativo(HOJA, "expuesto", "evento")
    assert _v(rr, "RR").valor == pytest.approx((a / (a + b)) / (c / (c + d)))


def test_dos_proporciones_desde_el_dialogo():
    """Cambió a propósito: los conteos vienen de campos, no de la primera columna."""
    res = dos_proporciones(EJEMPLOS["dos_proporciones"])
    assert _v(res, "Diferencia").valor == pytest.approx(24 / 80 - 12 / 75)
    assert not dos_proporciones({"x1": 90, "n1": 80, "x2": 1, "n2": 5}).ok


def test_cmh_de_datos_crudos_contra_statsmodels():
    """Cambió a propósito: exposición, evento y estrato; antes partía la hoja en 2×2."""
    from statsmodels.stats.contingency_tables import StratifiedTable
    res = cmh(HOJA, "expuesto", "evento", "sexo")
    tablas = [_tabla(HOJA[HOJA["sexo"] == s], "expuesto", "evento") for s in ("F", "M")]
    ref = StratifiedTable(np.transpose(np.asarray(tablas, float), (1, 2, 0)))
    assert _v(res, "OR común").valor == pytest.approx(ref.oddsratio_pooled)
    assert res.crudo["breslow_day_p"] == pytest.approx(ref.test_equal_odds().pvalue)


def test_rechazos():
    assert "exactamente 2" in fisher(HOJA, "grupo", "evento").error
    assert "misma columna" in chi_cuadrado(HOJA, "grupo", "grupo").error


@pytest.mark.parametrize("res", [
    chi_cuadrado(HOJA, "grupo", "evento"), fisher(HOJA, "expuesto", "evento"),
    mcnemar(HOJA, "antes", "despues"), odds_ratio_tabla(HOJA, "expuesto", "evento"),
    riesgo_relativo(HOJA, "expuesto", "evento"), cmh(HOJA, "expuesto", "evento", "sexo")],
    ids=["chi2", "fisher", "mcnemar", "or", "rr", "cmh"])
def test_informe(res):
    assert res.ok, res.error
    t = unescape(re.sub(r"<[^>]+>", " ", render_html(res)))
    assert "Qué se verificó" in t and "significativ" not in t.lower()


@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("analisis, c1, c2, c3", [
    ("Chi-cuadrado", "grupo", "evento", "(ninguna)"),
    ("Fisher exact", "expuesto", "evento", "(ninguna)"),
    ("McNemar", "antes", "despues", "(ninguna)"),
    ("Odds Ratio", "expuesto", "evento", "(ninguna)"),
    ("Riesgo Relativo", "expuesto", "evento", "(ninguna)"),
    ("CMH test", "expuesto", "evento", "sexo"),
    ("Comparar 2 proporciones", "expuesto", "evento", "(ninguna)"),
])
def test_el_panel(qt_app, analisis, c1, c2, c3):
    from src.ui.analysis_panel import AnalysisPanel
    panel = AnalysisPanel()
    panel.set_data(HOJA)
    panel.combo_analysis.setCurrentText(analisis)
    panel.combo_col1.setCurrentText(c1)
    panel.combo_col2.setCurrentText(c2)
    panel.combo_col3.setCurrentText(c3)
    panel._run()
    assert "Qué se verificó y qué se decidió" in panel.txt_results.toPlainText()
