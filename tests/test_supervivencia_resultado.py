"""«Supervivencia» migrada a `Resultado` (paso 4, familia 11).

Oráculo: lifelines (KaplanMeierFitter, multivariate_logrank_test, CoxPHFitter,
proportional_hazard_test). Cambian a propósito, cada uno con su test:

- Kaplan-Meier ya no imprime la «supervivencia media», que era el promedio de
  los puntos de la curva; da la mediana con su IC. El IC de la curva es log-log.
- Log-rank acepta más de dos grupos y, con dos, da el hazard ratio.
- Cox usa las covariables tildadas (antes, en silencio, `columns[3:]`), prueba
  los riesgos proporcionales con Schoenfeld y no avisa «no convergió» en
  ajustes sanos (lo avisaba en 19 de cada 20).
"""
import os
import re
import warnings
from html import unescape

import numpy as np
import pandas as pd
import pytest
from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test, proportional_hazard_test
from lifelines.utils import qth_survival_times

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.core.cox_regression import _km_izquierda, cox_regression  # noqa: E402
from src.resultado import render_html  # noqa: E402
from src.resultado.constructores import kaplan_meier, log_rank, regresion_cox  # noqa: E402


def _hoja(semilla=0, n=120, grupos=2, discreto=False):
    """Tiempo exponencial que depende de X y del grupo, con ~25 % de censura."""
    rng = np.random.default_rng(semilla)
    x, z = rng.normal(0, 1, n), rng.normal(0, 1, n)
    g = np.arange(n) % grupos
    t = rng.exponential(20 * np.exp(-(0.7 * x + 0.5 * g)))
    if discreto:
        t = np.maximum(np.ceil(t), 1)
    return pd.DataFrame({"T": t, "E": (rng.random(n) < 0.75) * 1.0, "G": g, "X": x, "Z": z,
                         "ID": np.arange(n) + 1000.0})


def _v(res, empieza):
    return next(v for v in res.valores if v.nombre.startswith(empieza))


def _texto(res):
    return unescape(re.sub(r"<[^>]+>", " ", render_html(res)))


# ---------------- Kaplan-Meier ----------------

@pytest.mark.parametrize("semilla", range(3))
def test_km_contra_lifelines(semilla):
    hoja = _hoja(semilla)
    km = kaplan_meier(hoja, "T", "E").crudo["km"]
    ref = KaplanMeierFitter().fit(hoja["T"], hoja["E"])
    ci = ref.confidence_interval_
    assert np.allclose(km["survival"], ref.survival_function_["KM_estimate"].values, atol=1e-12)
    assert np.allclose(km["ci_lower"], ci["KM_estimate_lower_0.95"].values, atol=1e-10)
    assert np.allclose(km["ci_upper"], ci["KM_estimate_upper_0.95"].values, atol=1e-10)
    for q in (0.25, 0.5, 0.75):
        t_q, lo, hi = km["cuantiles"][q]
        assert t_q == pytest.approx(qth_survival_times(1 - q, ref.survival_function_))
        ref_ic = np.ravel(qth_survival_times(1 - q, ci))
        assert lo == pytest.approx(ref_ic[0])
        assert (hi is None and np.isinf(ref_ic[1])) or hi == pytest.approx(ref_ic[1])


def test_km_ya_no_da_la_supervivencia_media():
    """Cambió a propósito: era np.mean de los puntos de la curva, sin sentido."""
    res = kaplan_meier(_hoja(), "T", "E")
    t = _texto(res)
    assert "Supervivencia media" not in t
    med = _v(res, "Mediana de supervivencia")
    assert med.ic is not None and med.ic[0] <= med.valor <= med.ic[1]


def test_km_mediana_no_alcanzada_se_dice():
    hoja = _hoja().assign(E=lambda d: (d["T"] <= d["T"].quantile(0.2)) * 1.0)
    res = kaplan_meier(hoja, "T", "E")
    assert _v(res, "Mediana").valor == "no se alcanzó"
    assert res.lectura.startswith("La curva no bajó de 0,5")


@pytest.mark.parametrize("cambio, motivo", [
    (lambda d: d.assign(E=d["E"] * 2), "tiene que ser 0/1"),
    (lambda d: d.assign(T=d["T"] - 100), "negativos"),
    (lambda d: d.assign(E=0.0), "ningún evento"),
    (lambda d: d.assign(E="vivo"), "tiene texto"),
])
def test_km_rechaza_con_motivo(cambio, motivo):
    assert motivo in kaplan_meier(cambio(_hoja()), "T", "E").error


# ---------------- Log-rank ----------------

@pytest.mark.parametrize("grupos", [2, 3, 4])
def test_log_rank_contra_lifelines(grupos):
    """Cambió a propósito: antes exigía exactamente dos grupos."""
    hoja = _hoja(1, n=150, grupos=grupos)
    res = log_rank(hoja, "T", "E", "G")
    ref = multivariate_logrank_test(hoja["T"], hoja["G"], hoja["E"])
    assert res.crudo["log_rank"]["chi2"] == pytest.approx(ref.test_statistic, rel=1e-9)
    assert res.crudo["log_rank"]["gl"] == grupos - 1


def test_log_rank_hr_del_segundo_grupo_sobre_el_primero():
    """El grupo 1 tiene más riesgo; el HR sale > 1 aunque la hoja empiece por él."""
    hoja = _hoja(2, n=200).sort_values("G", ascending=False)
    res = log_rank(hoja, "T", "E", "G")
    lr = res.crudo["log_rank"]
    O, E = lr["observados"], lr["esperados"]
    hr = _v(res, "Hazard ratio 1 / 0")
    assert hr.valor == pytest.approx((O[1] / E[1]) / (O[0] / E[0]))
    assert hr.valor > 1 and hr.ic[0] < hr.valor < hr.ic[1]
    # Parecido al HR de Cox con el grupo como covariable (no idéntico: otro método)
    cox = CoxPHFitter().fit(hoja[["T", "E", "G"]], "T", "E")
    assert hr.valor == pytest.approx(float(np.exp(cox.params_["G"])), rel=0.1)


def test_log_rank_curvas_que_se_cruzan_fallan_riesgos_proporcionales():
    rng = np.random.default_rng(3)
    n = 150
    t = np.concatenate([10 * rng.weibull(0.5, n), 10 * rng.weibull(3.0, n)])
    hoja = pd.DataFrame({"T": t, "E": 1.0, "G": np.repeat(["A", "B"], n)})
    res = log_rank(hoja, "T", "E", "G")
    paso = next(s for s in res.supuestos if "proporcionales" in s.pregunta)
    assert not paso.ok and "cambia con el tiempo" in paso.consecuencia


def test_log_rank_un_grupo_que_es_una_medicion_se_rechaza():
    assert "parece una medición" in log_rank(_hoja(), "T", "E", "X").error


# ---------------- Cox ----------------

@pytest.mark.parametrize("discreto", [False, True], ids=["sin empates", "con empates"])
def test_cox_contra_lifelines(discreto):
    hoja = _hoja(4, n=180, discreto=discreto)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = regresion_cox(hoja, "T", "E", ["X", "Z"])
        ref = CoxPHFitter().fit(hoja[["T", "E", "X", "Z"]], "T", "E")
    r = res.crudo["cox"]
    assert np.allclose(r["hazard_ratios"], np.exp(ref.params_.values), rtol=1e-3)
    assert r["lr_chi2"] == pytest.approx(ref.log_likelihood_ratio_test().test_statistic, rel=1e-6)
    assert _v(res, "HR — X").valor == pytest.approx(r["hazard_ratios"][0])


def test_cox_usa_las_covariables_tildadas():
    """Cambió a propósito: antes tomaba columns[3:] (acá G, X, Z e ID) sin avisar."""
    res = regresion_cox(_hoja(), "T", "E", ["X"])
    assert res.crudo["covariables"] == ["X"]
    assert [v.nombre for v in res.valores if v.nombre.startswith("HR")] == ["HR — X"]
    assert "Tildá al menos una" in regresion_cox(_hoja(), "T", "E", ["T", "E"]).error


def test_cox_sano_no_avisa_que_no_convergio():
    """Cambió a propósito: `success` de BFGS da False por «precision loss» casi siempre."""
    for semilla in range(10):
        res = regresion_cox(_hoja(semilla), "T", "E", ["X", "Z"])
        assert res.crudo["cox"]["convergio"]
        assert not any("convergi" in a for a in res.advertencias)


def test_cox_separacion_se_nombra():
    hoja = _hoja().assign(S=lambda d: d["E"])      # todos los eventos con S = 1
    res = regresion_cox(hoja, "T", "E", ["S"])
    assert any("«S»" in a and "máximo finito" in a for a in res.advertencias)


@pytest.mark.parametrize("semilla", range(3))
def test_schoenfeld_contra_lifelines(semilla):
    """Misma escala de tiempo que R (1 − KM por izquierda), pasada a lifelines."""
    hoja = _hoja(10 + semilla, n=150)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = cox_regression(hoja["T"].values, hoja["E"].values, hoja[["X", "Z"]].values)
        cph = CoxPHFitter().fit(hoja[["T", "E", "X", "Z"]], "T", "E")

        def km(T, c, w):
            return pd.Series(_km_izquierda(np.asarray(T, float), np.asarray(c).astype(int),
                                           np.asarray(T, float)), index=T.index)
        ref = proportional_hazard_test(cph, hoja[["T", "E", "X", "Z"]], time_transform=km)
    assert np.allclose(r["riesgos_proporcionales"]["chi2"], np.ravel(ref.test_statistic),
                       rtol=2e-3)


def test_schoenfeld_global_con_una_covariable_es_la_misma():
    r = cox_regression(*(_hoja(5)[c].values for c in ("T", "E")), _hoja(5)[["X"]].values)
    ph = r["riesgos_proporcionales"]
    assert ph["chi2_global"] == pytest.approx(ph["chi2"][0])


def test_schoenfeld_de_efron_suma_cero_con_empates():
    """Son la ecuación de score de Efron: en el óptimo suman cero."""
    hoja = _hoja(6, n=150, discreto=True)
    r = cox_regression(hoja["T"].values, hoja["E"].values, hoja[["X", "Z"]].values)
    assert np.allclose(r["riesgos_proporcionales"]["suma_residuos"], 0, atol=1e-3)


def test_cox_detecta_un_efecto_que_cambia_con_el_tiempo():
    rng = np.random.default_rng(7)
    n = 300
    g = (np.arange(n) % 2).astype(float)
    t = np.where(g == 1, 10 * rng.weibull(0.5, n), 10 * rng.weibull(3.0, n))
    res = regresion_cox(pd.DataFrame({"T": t, "E": 1.0, "G": g}), "T", "E", ["G"])
    paso = next(s for s in res.supuestos if "proporcionales" in s.pregunta)
    assert not paso.ok and "«G»" in paso.consecuencia


# ---------------- Informe, figuras y panel ----------------

@pytest.mark.parametrize("res", [kaplan_meier(_hoja(), "T", "E"),
                                 log_rank(_hoja(grupos=3), "T", "E", "G"),
                                 regresion_cox(_hoja(), "T", "E", ["X", "Z"])],
                         ids=["km", "log-rank", "cox"])
def test_informe_y_figuras(res):
    import matplotlib.pyplot as plt
    assert res.ok, res.error
    t = _texto(res)
    assert "Qué se verificó" in t and "significativ" not in t.lower()
    for figura in res.figuras:
        plt.close(figura.dibujar())


@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("analisis, elegidas", [
    ("Kaplan-Meier", None), ("Log-rank test", None), ("Cox regression", ["X", "Z"])])
def test_el_panel(qt_app, analisis, elegidas):
    from src.ui.analysis_panel import AnalysisPanel
    panel = AnalysisPanel()
    panel.set_data(_hoja())
    panel.combo_analysis.setCurrentText(analisis)
    panel.combo_col1.setCurrentText("T")
    panel.combo_col2.setCurrentText("E")
    panel.combo_col3.setCurrentText("G")
    panel.columnas_elegidas = elegidas
    panel._run()
    assert "Qué se verificó y qué se decidió" in panel.txt_results.toPlainText()
