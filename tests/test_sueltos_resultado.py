"""Los sueltos migrados a `Resultado` (paso 4, familia 16): meta-análisis,
mediciones seriales, prueba diagnóstica y razones de verosimilitud.

Oráculos: statsmodels (`combine_effects`, OLS para Egger), scipy (t de las
pendientes) y el cálculo a mano de la tabla 2×2. Cambian a propósito: el
meta-análisis trae τ², intervalo de predicción, Egger y funnel; la prueba
diagnóstica recalcula VPP y VPN para la prevalencia cargada; las razones de
verosimilitud dan la probabilidad post-test.
"""
import os
import re
from html import unescape

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.meta_analysis import combine_effects

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.resultado import render_html  # noqa: E402
from src.resultado.constructores import (  # noqa: E402
    mediciones_seriales, meta_analisis, prueba_diagnostica, razones_verosimilitud,
)


def _v(res, empieza):
    return next(v for v in res.valores if v.nombre.startswith(empieza))


def _texto(res):
    return unescape(re.sub(r"<[^>]+>", " ", render_html(res)))


def _estudios(k=12, semilla=1):
    rng = np.random.default_rng(semilla)
    se = rng.uniform(0.1, 0.5, k)
    return pd.DataFrame({"efecto": rng.normal(0.3, 0.2, k) + rng.normal(0, se), "ee": se})


def _diagnostica(n=300, semilla=2):
    rng = np.random.default_rng(semilla)
    enfermo = (rng.random(n) < 0.3).astype(float)
    prueba = np.where(enfermo == 1, rng.random(n) < 0.85, rng.random(n) < 0.10).astype(float)
    return pd.DataFrame({"prueba": prueba, "oro": enfermo})


# ---------------- Meta-análisis ----------------

@pytest.mark.parametrize("modelo", ["aleatorio", "fijo"])
def test_meta_como_statsmodels(modelo):
    hoja = _estudios()
    res = meta_analisis(hoja, "efecto", "ee", {"modelo": modelo})
    ref = combine_effects(hoja["efecto"].values, hoja["ee"].values ** 2, method_re="dl")
    esperado = ref.mean_effect_re if modelo == "aleatorio" else ref.mean_effect_fe
    assert _v(res, "Efecto combinado").valor == pytest.approx(esperado)
    assert _v(res, "I²").valor == pytest.approx(100 * ref.i2)
    if modelo == "aleatorio":
        assert _v(res, "τ²").valor == pytest.approx(ref.tau2)


def test_intervalo_de_prediccion_mas_ancho_que_el_ic():
    res = meta_analisis(_estudios(), "efecto", "ee")
    r = res.crudo["meta"]
    assert r["prediccion"][0] < r["ci_lower"] and r["prediccion"][1] > r["ci_upper"]


def test_egger_como_ols_desde_10_estudios():
    hoja = _estudios()
    eg = meta_analisis(hoja, "efecto", "ee").crudo["meta"]["egger"]
    ols = sm.OLS(hoja["efecto"] / hoja["ee"], sm.add_constant(1 / hoja["ee"])).fit()
    assert eg["intercepto"] == pytest.approx(ols.params.iloc[0])
    assert eg["p"] == pytest.approx(ols.pvalues.iloc[0])
    pocos = meta_analisis(_estudios(k=6), "efecto", "ee")
    assert next(s for s in pocos.supuestos if "pequeños" in s.pregunta).respuesta == "Sin evaluar"


def test_meta_con_tau_cero_sigue_diciendo_aleatorios():
    """Cambió a propósito: antes la etiqueta pasaba a «fijos» sola."""
    hoja = pd.DataFrame({"efecto": [0.3] * 4, "ee": [0.2] * 4})
    assert "aleatorios" in _v(meta_analisis(hoja, "efecto", "ee"), "Efecto combinado").nota


def test_meta_rechaza_ee_cero():
    hoja = _estudios().assign(ee=lambda d: d["ee"].where(d.index != 0, 0.0))
    assert "mayor que 0" in meta_analisis(hoja, "efecto", "ee").error


# ---------------- Mediciones seriales ----------------

def test_seriales_la_t_es_sobre_las_pendientes():
    rng = np.random.default_rng(3)
    base = rng.normal(10, 2, 30)
    hoja = pd.DataFrame({f"t{i}": base + 0.5 * i + rng.normal(0, 1, 30) for i in range(4)})
    res = mediciones_seriales(hoja, list(hoja.columns))
    pendientes = [stats.linregress(np.arange(4), fila).slope for fila in hoja.values]
    assert _v(res, "Pendiente media").valor == pytest.approx(np.mean(pendientes))
    assert res.crudo["seriales"]["p_tendencia"] == pytest.approx(
        stats.ttest_1samp(pendientes, 0).pvalue)


# ---------------- Prueba diagnóstica ----------------

def test_diagnostica_a_mano():
    hoja = _diagnostica()
    res = prueba_diagnostica(hoja, "prueba", "oro")
    a = int(((hoja.prueba == 1) & (hoja.oro == 1)).sum())
    c = int(((hoja.prueba == 0) & (hoja.oro == 1)).sum())
    d = int(((hoja.prueba == 0) & (hoja.oro == 0)).sum())
    b = len(hoja) - a - c - d
    assert _v(res, "Verdaderos positivos").valor == a
    assert _v(res, "Sensibilidad").valor == pytest.approx(a / (a + c))
    assert _v(res, "Especificidad").valor == pytest.approx(d / (b + d))
    assert _v(res, "LR+").valor == pytest.approx((a / (a + c)) / (b / (b + d)))


def test_vpp_para_otra_prevalencia_por_bayes():
    res = prueba_diagnostica(_diagnostica(), "prueba", "oro", {"prevalencia": 0.02})
    s, e = _v(res, "Sensibilidad").valor, _v(res, "Especificidad").valor
    esperado = s * 0.02 / (s * 0.02 + (1 - e) * 0.98)
    assert _v(res, "VPP con prevalencia").valor == pytest.approx(esperado)
    assert _v(res, "VPP con prevalencia").valor < _v(res, "VPP (en la muestra)").valor


def test_con_la_prevalencia_de_la_muestra_el_post_test_es_el_vpp():
    hoja = _diagnostica()
    lr = razones_verosimilitud(hoja, "prueba", "oro")
    dx = prueba_diagnostica(hoja, "prueba", "oro")
    assert _v(lr, "Probabilidad si da positivo").valor == pytest.approx(_v(dx, "VPP").valor)


def test_post_test_con_pretest_cargado():
    res = razones_verosimilitud(_diagnostica(), "prueba", "oro", {"pretest": 0.5})
    lr = _v(res, "LR+").valor
    assert _v(res, "Probabilidad si da positivo").valor == pytest.approx(lr / (1 + lr))


# ---------------- Informe, figuras y panel ----------------

@pytest.mark.parametrize("res", [
    meta_analisis(_estudios(), "efecto", "ee"),
    mediciones_seriales(pd.DataFrame(np.random.default_rng(0).normal(0, 1, (20, 3)),
                                     columns=["a", "b", "c"]), ["a", "b", "c"]),
    prueba_diagnostica(_diagnostica(), "prueba", "oro"),
    razones_verosimilitud(_diagnostica(), "prueba", "oro")],
    ids=["meta", "seriales", "diagnostica", "lr"])
def test_informe_y_figuras(res):
    import matplotlib.pyplot as plt
    assert res.ok, res.error
    t = _texto(res)
    assert "Qué se verificó" in t and "significativ" not in t.lower()
    for f in res.figuras:
        plt.close(f.dibujar())


@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("analisis, hoja, c1, c2", [
    ("Meta-analisis", _estudios(), "efecto", "ee"),
    ("Diagnostic test", _diagnostica(), "prueba", "oro"),
    ("Likelihood Ratios", _diagnostica(), "prueba", "oro"),
    ("Mediciones seriales", pd.DataFrame(np.random.default_rng(0).normal(0, 1, (20, 3)),
                                         columns=["a", "b", "c"]), "a", "b")])
def test_el_panel(qt_app, analisis, hoja, c1, c2):
    from src.ui.analysis_panel import AnalysisPanel
    panel = AnalysisPanel()
    panel.set_data(hoja)
    panel.combo_analysis.setCurrentText(analisis)
    panel.combo_col1.setCurrentText(c1)
    panel.combo_col2.setCurrentText(c2)
    panel._run()
    assert "Qué se verificó y qué se decidió" in panel.txt_results.toPlainText()
