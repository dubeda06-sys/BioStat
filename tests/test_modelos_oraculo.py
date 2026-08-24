"""Modelos contra lifelines, statsmodels y sklearn.

Dos defectos salieron de aca, y los dos devolvian numeros de aspecto razonable:

1. Cox leia `result.hes_inv` — el atributo de scipy es `hess_inv`. El hasattr
   daba siempre False y caia en un `np.eye(p)*0.01` de reserva, asi que TODOS
   los errores estandar valian exactamente 0.1 con cualquier dato y cualquier
   n. De ahi salian los z y los p. Ademas el conjunto de riesgo estaba dado
   vuelta (`np.cumsum(...)[::-1]`), y el AIC tenia el signo cambiado.
2. La varianza del log(OR) del CMH no era ninguna de las publicadas: daba un
   error estandar 4 veces mas grande, y entonces el IC incluia el 1 mientras
   el p decia 0.0004. Un IC y un p que se contradicen delatan que no salen de
   la misma varianza.
"""
import warnings

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from statsmodels.stats.contingency_tables import StratifiedTable
from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.statistics import logrank_test

from src.core.cox_regression import cox_regression
from src.core.cmh import cmh_test
from src.core.survival import kaplan_meier, log_rank_test
from src.core.regression import multiple_regression
from src.core.meta_analysis import meta_analysis


def _datos_cox(semilla, n=180, discreto=False):
    r = np.random.default_rng(semilla)
    x1, x2 = r.normal(0, 1, n), r.normal(0, 1, n)
    t = r.exponential(np.exp(-(0.8 * x1 - 0.4 * x2)) * (8 if discreto else 20))
    if discreto:
        t = np.maximum(np.ceil(t), 1)      # empates a proposito
    e = (r.random(n) < 0.78).astype(int)
    return t, e, np.column_stack([x1, x2])


# ---------------- Cox ----------------

@pytest.mark.parametrize("semilla", range(3))
@pytest.mark.parametrize("discreto", [False, True], ids=["sin empates", "con empates"])
def test_cox_coincide_con_lifelines(semilla, discreto):
    """Con empates la correccion importa: Breslow sesga los coeficientes hacia
    cero, Efron no. En laboratorio los tiempos vienen en dias o meses, asi que
    los empates son la regla."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        t, e, X = _datos_cox(200 + semilla, discreto=discreto)
        got = cox_regression(t, e, X)
        ref = CoxPHFitter().fit(
            pd.DataFrame({"T": t, "E": e, "x1": X[:, 0], "x2": X[:, 1]}), "T", "E")
    assert np.allclose(got["coefficients"], ref.params_.values, atol=1e-3)
    assert np.allclose(got["se"], ref.standard_errors_.values, atol=1e-3)
    assert np.allclose(got["p_values"], ref.summary["p"].values, atol=1e-4)
    assert got["log_likelihood"] == pytest.approx(ref.log_likelihood_, abs=1e-5)


def test_los_errores_estandar_de_cox_dependen_de_los_datos():
    """El defecto original devolvia se = 0.1 siempre. Basta con verificar que
    cambian entre datasets y que se achican al crecer n."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        se_chico = cox_regression(*_datos_cox(1, n=60))["se"]
        se_grande = cox_regression(*_datos_cox(1, n=600))["se"]
        se_otro = cox_regression(*_datos_cox(2, n=60))["se"]
    assert not np.allclose(se_chico, 0.1), "errores estandar constantes"
    assert not np.allclose(se_chico, se_otro), "no dependen de los datos"
    assert np.all(se_grande < se_chico), "no se achican al crecer n"


def test_el_aic_de_cox_penaliza_los_parametros():
    """AIC = 2k - 2logL. Con el signo invertido premiaba el peor modelo."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        t, e, X = _datos_cox(5)
        uno = cox_regression(t, e, X[:, :1])
        dos = cox_regression(t, e, X)
    assert dos["aic"] == pytest.approx(2 * 2 - 2 * dos["log_likelihood"])
    assert uno["aic"] == pytest.approx(2 * 1 - 2 * uno["log_likelihood"])


def test_sin_eventos_cox_lo_dice():
    t, _, X = _datos_cox(9)
    r = cox_regression(t, np.zeros(len(t), dtype=int), X)
    assert "error" in r and "censurados" in r["error"]


def test_cox_avisa_si_hay_pocos_eventos_por_covariable():
    r = np.random.default_rng(3)
    n = 40
    X = r.normal(0, 1, (n, 3))
    t = r.exponential(20, n)
    e = np.zeros(n, dtype=int)
    e[:12] = 1
    res = cox_regression(t, e, X)
    assert "error" not in res
    assert any("covariable" in a for a in res["avisos"])


# ---------------- CMH ----------------

@pytest.mark.parametrize("semilla", range(8))
def test_cmh_coincide_con_statsmodels(semilla):
    rng = np.random.default_rng(semilla)
    K = int(rng.integers(2, 6))
    tablas = [rng.integers(3, 30, (2, 2)).astype(float) for _ in range(K)]
    got = cmh_test(np.array(tablas))
    ref = StratifiedTable(list(tablas))
    prueba = ref.test_null_odds()
    assert got["cmh_statistic"] == pytest.approx(prueba.statistic, abs=1e-9)
    assert got["p_value"] == pytest.approx(prueba.pvalue, abs=1e-12)
    assert got["common_odds_ratio"] == pytest.approx(ref.oddsratio_pooled, abs=1e-9)
    assert got["se_log_or"] == pytest.approx(ref.logodds_pooled_se, abs=1e-9)


@pytest.mark.parametrize("semilla", range(10))
def test_el_ic_y_el_p_del_cmh_cuentan_la_misma_historia(semilla):
    """Si p < 0.05 el IC del OR no puede contener el 1, y al reves. Es la
    prueba que delata una varianza equivocada sin necesidad de oraculo."""
    rng = np.random.default_rng(500 + semilla)
    tablas = np.array([rng.integers(3, 40, (2, 2)).astype(float)
                       for _ in range(int(rng.integers(2, 5)))])
    g = cmh_test(tablas)
    contiene_uno = g["or_ci_low"] <= 1.0 <= g["or_ci_high"]
    assert contiene_uno == (g["p_value"] >= 0.05), (
        f"p={g['p_value']:.4f} pero IC=({g['or_ci_low']:.3f}, {g['or_ci_high']:.3f})")


# ---------------- Supervivencia ----------------

@pytest.mark.parametrize("semilla", range(3))
def test_kaplan_meier_coincide_con_lifelines(semilla):
    r = np.random.default_rng(semilla)
    t = r.exponential(20, 80)
    e = (r.random(80) < 0.7).astype(int)
    got = kaplan_meier(t, e)
    ref = KaplanMeierFitter().fit(t, e).survival_function_["KM_estimate"].values
    obtenido = np.asarray(got.get("survival", got.get("survival_probs")))
    m = min(len(obtenido), len(ref))
    assert np.allclose(obtenido[:m], ref[:m], atol=1e-9)


def test_la_supervivencia_de_km_nunca_sale_de_cero_uno():
    for s in range(20):
        r = np.random.default_rng(s)
        t = r.exponential(20, 50)
        got = kaplan_meier(t, (r.random(50) < 0.6).astype(int))
        for clave in ("survival", "survival_probs", "ci_lower", "ci_upper"):
            v = got.get(clave)
            if v is not None:
                v = np.asarray(v, dtype=float)
                v = v[np.isfinite(v)]
                assert np.all((v >= -1e-12) & (v <= 1 + 1e-12)), f"{clave} fuera de [0,1]"


@pytest.mark.parametrize("semilla", range(3))
def test_log_rank_coincide_con_lifelines(semilla):
    r = np.random.default_rng(100 + semilla)
    t1, e1 = r.exponential(20, 60), (r.random(60) < 0.7).astype(int)
    t2, e2 = r.exponential(30, 60), (r.random(60) < 0.7).astype(int)
    got = log_rank_test(t1, e1, t2, e2)
    ref = logrank_test(t1, t2, e1, e2)
    assert got["p"] == pytest.approx(ref.p_value, abs=1e-9)


# ---------------- Regresion multiple ----------------

@pytest.mark.parametrize("escala", [1e3, 1.0, 1e-2, 1e-4])
def test_la_regresion_multiple_no_depende_de_la_escala(escala):
    """Los errores estandar se calculaban tras un chequeo por DETERMINANTE, que
    no mide condicionamiento: con predictores de escala chica el determinante
    se va a cero y todos los p habrian salido 1."""
    r = np.random.default_rng(4)
    n = 80
    X = np.column_stack([r.normal(0, 1, n) for _ in range(3)]) * escala
    y = 2.0 * X[:, 0] / escala + 0.5 * X[:, 1] / escala + r.normal(0, 1, n)
    got = multiple_regression(X, y)
    ref = sm.OLS(y, sm.add_constant(X)).fit()
    assert np.allclose(got["p"], ref.pvalues, atol=1e-6)
    assert got["r2_adj"] == pytest.approx(ref.rsquared_adj, abs=1e-9)
    assert not np.all(got["se"] == 0), "errores estandar colapsados a cero"


# ---------------- Meta-analisis ----------------

def test_i2_nunca_es_negativo():
    """I2 = max(0, (Q-gl)/Q). Sin el max, estudios homogeneos dan I2 negativo."""
    m = meta_analysis(np.array([0.30] * 4), np.array([0.20] * 4), model="random")
    assert m["i2"] >= 0
    for s in range(20):
        r = np.random.default_rng(s)
        k = int(r.integers(2, 9))
        m = meta_analysis(r.normal(0.3, 0.02, k), np.full(k, 0.25), model="random")
        assert 0 <= m["i2"] <= 100
