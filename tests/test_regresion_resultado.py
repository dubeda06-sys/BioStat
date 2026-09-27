"""«Regresión» migrada a `Resultado` (paso 4, familia 3).

Oráculos: statsmodels (OLS, Logit, Probit, RESET, Breusch-Pagan, VIF) y
sklearn (AUC). Lo nuevo respecto del panel viejo, cada uno con su test:
diagnósticos de residuos, VIF, eventos por variable, Hosmer-Lemeshow, AUC, la
dosis efectiva del probit (ED50/ED95, el LoD de EP17) y que la logística
rechace la separación completa en vez de informar un OR de 1e12.
"""
import os
import re
from html import unescape

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy import stats

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.core.regression import hosmer_lemeshow  # noqa: E402
from src.resultado import render_html  # noqa: E402
from src.resultado.constructores import (  # noqa: E402
    probit, regresion_lineal, regresion_logistica, regresion_multiple,
)

RNG = np.random.default_rng(4)
N = 120
_X1, _X2 = RNG.normal(50, 10, N), RNG.normal(0, 1, N)
HOJA = pd.DataFrame({
    "x1": _X1, "x2": _X2, "ruido": RNG.normal(0, 1, N),
    "y": 3 + 0.8 * _X1 + 2 * _X2 + RNG.normal(0, 4, N),
})
HOJA["evento"] = (RNG.uniform(0, 1, N) < 1 / (1 + np.exp(-(-20 + 0.4 * _X1)))).astype(float)


def _v(res, empieza):
    return next(v for v in res.valores if v.nombre.startswith(empieza))


def _paso(res, texto):
    return next(s for s in res.supuestos if texto in s.pregunta)


def _texto(res):
    return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", render_html(res)))).strip()


# ---------------- Lineal ----------------

def test_lineal_contra_statsmodels():
    res = regresion_lineal(HOJA, "x1", "y")
    ref = sm.OLS(HOJA["y"], sm.add_constant(HOJA["x1"])).fit()
    assert _v(res, "Pendiente").valor == pytest.approx(ref.params["x1"])
    assert _v(res, "Pendiente").ic == pytest.approx(tuple(ref.conf_int().loc["x1"]))
    assert _v(res, "Intercepto").ic == pytest.approx(tuple(ref.conf_int().loc["const"]))
    assert _v(res, "R²").valor == pytest.approx(ref.rsquared)


def test_lineal_detecta_la_curva():
    x = np.linspace(1, 10, 80)
    hoja = pd.DataFrame({"x": x, "y": x ** 2 + RNG.normal(0, 2, 80)})
    paso = _paso(regresion_lineal(hoja, "x", "y"), "lineal")
    assert paso.respuesta == "Se detectó curvatura"


def test_lineal_detecta_el_embudo():
    x = np.linspace(1, 100, 150)
    hoja = pd.DataFrame({"x": x, "y": 2 * x + RNG.normal(0, 1, 150) * x * 0.3})
    assert _paso(regresion_lineal(hoja, "x", "y"), "dispersión").respuesta == "No"


def test_lineal_recuerda_que_no_compara_metodos():
    assert "Cornbleet" in regresion_lineal(HOJA, "x1", "y").matiz


# ---------------- Múltiple ----------------

def test_multiple_contra_statsmodels():
    res = regresion_multiple(HOJA, "y", ["x1", "x2"])
    ref = sm.OLS(HOJA["y"], sm.add_constant(HOJA[["x1", "x2"]])).fit()
    for nombre in ("x1", "x2"):
        v = _v(res, f"b — {nombre}")
        assert v.valor == pytest.approx(ref.params[nombre])
        assert v.ic == pytest.approx(tuple(ref.conf_int().loc[nombre]))
    assert _v(res, "R² ajustado").valor == pytest.approx(ref.rsquared_adj)


def test_multiple_vif_detecta_predictoras_repetidas():
    hoja = HOJA.assign(casi_x1=HOJA["x1"] + RNG.normal(0, 1, N))
    paso = _paso(regresion_multiple(hoja, "y", ["x1", "casi_x1", "x2"]), "repiten")
    assert paso.respuesta.startswith("Sí") and "casi_x1" in paso.respuesta
    assert _paso(regresion_multiple(HOJA, "y", ["x1", "x2"]), "repiten").respuesta == "No"


def test_multiple_colineal_exacta_se_rechaza():
    hoja = HOJA.assign(doble=2 * HOJA["x1"])
    assert "colineales" in regresion_multiple(hoja, "y", ["x1", "doble"]).error


def test_multiple_acepta_una_predictora_como_texto():
    assert regresion_multiple(HOJA, "y", "x1").ok


# ---------------- Logística ----------------

def test_logistica_contra_statsmodels_y_sklearn():
    from sklearn.metrics import roc_auc_score
    res = regresion_logistica(HOJA, "evento", ["x1"])
    ref = sm.Logit(HOJA["evento"], sm.add_constant(HOJA["x1"])).fit(disp=0)
    or_ = _v(res, "OR — x1")
    assert or_.valor == pytest.approx(np.exp(ref.params["x1"]))
    assert or_.ic == pytest.approx(tuple(np.exp(ref.conf_int().loc["x1"])))
    auc = roc_auc_score(HOJA["evento"], ref.predict())
    assert _v(res, "AUC del modelo").valor == pytest.approx(auc)


def test_hosmer_lemeshow_a_mano():
    """Diez grupos del mismo tamaño ordenados por riesgo; H contra chi2(8)."""
    ref = sm.Logit(HOJA["evento"], sm.add_constant(HOJA["x1"])).fit(disp=0)
    p = np.asarray(ref.predict())
    y = HOJA["evento"].to_numpy()
    orden = np.argsort(p, kind="mergesort")
    h = 0.0
    for idx in np.array_split(orden, 10):
        o, e, n = y[idx].sum(), p[idx].sum(), len(idx)
        h += (o - e) ** 2 / (e * (1 - e / n))
    r = hosmer_lemeshow(y, p)
    assert r["h"] == pytest.approx(h) and r["gl"] == 8
    assert r["p"] == pytest.approx(stats.chi2.sf(h, 8))


def test_logistica_con_pocos_eventos_por_variable():
    hoja = HOJA.iloc[:40].copy()
    res = regresion_logistica(hoja, "evento", ["x1", "x2", "ruido"])
    assert _paso(res, "eventos suficientes").respuesta == "No"


def test_logistica_con_separacion_completa_se_rechaza():
    """Antes el panel informaba el OR que devolvía un ajuste sin convergencia."""
    hoja = pd.DataFrame({"x": np.arange(20.0), "y": (np.arange(20) >= 10).astype(float)})
    assert "separacion completa" in regresion_logistica(hoja, "y", ["x"]).error


def test_logistica_con_respuesta_no_binaria():
    assert "tiene que ser 0/1" in regresion_logistica(HOJA, "y", ["x1"]).error


# ---------------- Probit ----------------

def _dilucion(semilla=9):
    """Un ensayo de detección: 8 niveles de concentración, 20 réplicas cada uno."""
    rng = np.random.default_rng(semilla)
    conc = np.repeat([1, 2, 4, 8, 16, 32, 64, 128.0], 20)
    detecta = rng.uniform(0, 1, len(conc)) < stats.norm.cdf(-3 + 2 * np.log10(conc) * 1.6)
    return pd.DataFrame({"copias": conc, "detectado": detecta.astype(float)})


def test_probit_dosis_contra_el_metodo_delta_a_mano():
    hoja = _dilucion()
    res = probit(hoja, "copias", "detectado", {"escala": "log10"})
    x = np.log10(hoja["copias"])
    ref = sm.Probit(hoja["detectado"], sm.add_constant(x)).fit(disp=0)
    b0, b1 = ref.params
    cov = ref.cov_params().to_numpy()
    x95 = (stats.norm.ppf(0.95) - b0) / b1
    g = np.array([-1 / b1, -x95 / b1])
    ee = np.sqrt(g @ cov @ g)
    v = _v(res, "Dosis con respuesta del 95 %")
    assert v.valor == pytest.approx(10 ** x95)
    assert v.ic == pytest.approx((10 ** (x95 - 1.959964 * ee), 10 ** (x95 + 1.959964 * ee)),
                                 rel=1e-5)
    assert "EP17" in v.nota


def test_probit_ed50_en_escala_lineal():
    hoja = _dilucion()
    res = probit(hoja, "copias", "detectado")
    ref = sm.Probit(hoja["detectado"], sm.add_constant(hoja["copias"])).fit(disp=0)
    assert _v(res, "Dosis con respuesta del 50 %").valor == pytest.approx(
        -ref.params["const"] / ref.params["copias"])
    assert _paso(res, "escala lineal").respuesta == "Sí"


def test_probit_log10_con_ceros_se_rechaza():
    hoja = _dilucion().assign(copias=lambda d: d["copias"] - 1)
    assert "positiva" in probit(hoja, "copias", "detectado", {"escala": "log10"}).error


# ---------------- Informe, figuras, panel ----------------

@pytest.mark.parametrize("res", [
    regresion_lineal(HOJA, "x1", "y"), regresion_multiple(HOJA, "y", ["x1", "x2"]),
    regresion_logistica(HOJA, "evento", ["x1"]),
    probit(_dilucion(), "copias", "detectado", {"escala": "log10"})],
    ids=["lineal", "multiple", "logistica", "probit"])
def test_informe_y_figuras(res):
    import matplotlib.pyplot as plt
    assert res.ok, res.error
    t = _texto(res)
    assert "Qué se verificó" in t and "significativ" not in t.lower()
    for figura in res.figuras:
        fig = figura.dibujar()
        assert fig.axes
        plt.close(fig)


@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("analisis, c1, c2, elegidas", [
    ("Regresion lineal", "x1", "y", None),
    ("Regresion multiple", "y", "x1", ["x1", "x2"]),
    ("Regresion logistica", "evento", "x1", ["x1"]),
    ("Probit regression", "x1", "evento", None),
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
    texto = panel.txt_results.toPlainText()
    assert "Qué se verificó y qué se decidió" in texto, texto[:300]
    if analisis in ("Regresion multiple", "Regresion logistica"):
        assert "todas las columnas numéricas" not in texto


def test_sin_dialogo_la_multiple_avisa_que_uso_todas(qt_app):
    from src.ui.analysis_panel import AnalysisPanel
    panel = AnalysisPanel()
    panel.set_data(HOJA[["y", "x1", "x2"]])
    panel.combo_analysis.setCurrentText("Regresion multiple")
    panel.combo_col1.setCurrentText("y")
    panel._run()
    assert "todas las columnas numéricas" in panel.txt_results.toPlainText()
