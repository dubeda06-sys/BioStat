"""Tests de VALORES de referencia (no solo de claves).

Cada prueba compara la salida de una funcion de `src.core` contra un valor
calculado de forma independiente (scipy/statsmodels/pingouin) o contra un valor
publicado/textbook. Estos tests son la red de seguridad que faltaba: los tests
previos solo verificaban que existieran las claves del dict, nunca los numeros.
"""
import numpy as np
import pandas as pd
import pytest
from scipy import stats
import statsmodels.api as sm


# --------------------------------------------------------------------------
# Bugs de calculo corregidos en Fase 1
# --------------------------------------------------------------------------

def test_cochran_q_valor_correcto():
    """Antes daba Q=-3.51, p=1.0. Correcto: Q=7.6, p≈0.0224."""
    from src.core.statistics import cochran_q
    m = np.array([[1, 0, 0], [1, 1, 0], [1, 1, 1], [1, 0, 0],
                  [1, 1, 0], [0, 0, 0], [1, 1, 1], [1, 0, 0]], dtype=float)
    res = cochran_q(m)
    assert res["q"] == pytest.approx(7.6, rel=1e-3)
    assert res["p"] == pytest.approx(0.02237, rel=1e-2)
    assert res["df"] == 2
    assert res["Q"] == pytest.approx(res["q"])  # alias para la UI


def test_descriptive_ci_usa_t_no_z():
    """El IC95% de la media debe usar t de Student, no 1.96 (z)."""
    from src.core.statistics import descriptive_stats
    data = np.array([1, 2, 3, 4, 5], dtype=float)
    r = descriptive_stats(data)
    n = 5
    sem = np.std(data, ddof=1) / np.sqrt(n)
    tcrit = stats.t.ppf(0.975, n - 1)
    esperado = (3 - tcrit * sem, 3 + tcrit * sem)
    assert r["ci95"][0] == pytest.approx(esperado[0])
    assert r["ci95"][1] == pytest.approx(esperado[1])
    # y NO debe coincidir con el z=1.96
    assert r["ci95"][1] != pytest.approx(3 + 1.96 * sem)


def test_logistic_regression_coincide_con_statsmodels():
    """La logistica ahora es MLE (statsmodels); validar OR y p."""
    from src.core.regression import logistic_regression
    rng = np.random.RandomState(1)
    n = 80
    x = rng.normal(0, 1, n)
    logit = -0.5 + 1.5 * x
    y = (rng.uniform(size=n) < 1 / (1 + np.exp(-logit))).astype(float)
    r = logistic_regression(x.reshape(-1, 1), y)

    ref = sm.Logit(y, sm.add_constant(x)).fit(disp=0)
    assert r["coeffs"][1] == pytest.approx(ref.params[1], rel=1e-4)
    assert r["odds_ratios"][1] == pytest.approx(np.exp(ref.params[1]), rel=1e-4)
    assert r["p"][1] == pytest.approx(ref.pvalues[1], rel=1e-3)
    assert "or_ci_low" in r and "or_ci_high" in r
    assert r["or_ci_low"][1] < r["odds_ratios"][1] < r["or_ci_high"][1]


def test_two_way_anova_detecta_efecto():
    """Antes ss_error=0 -> p=1 siempre. Ahora debe detectar el efecto de A."""
    from src.core.two_way_anova import two_way_anova
    rng = np.random.RandomState(0)
    A = np.repeat([0, 1], 12)
    B = np.tile(np.repeat([0, 1], 6), 2)
    y = 2.0 * A + 0.0 * B + rng.normal(0, 0.3, 24)
    r = two_way_anova(y, A, B)
    assert r["df_error"] > 0
    assert r["ss_error"] > 0          # ya no colapsa a 0
    assert r["p_A"] < 0.05            # efecto real de A
    assert r["p_B"] > 0.05            # B sin efecto


def test_icc_alta_concordancia():
    """ICC cercano a 1 cuando los evaluadores concuerdan; coincide con pingouin."""
    import pingouin as pg
    from src.core.agreement import intraclass_correlation
    rng = np.random.RandomState(2)
    base = rng.normal(50, 10, 30)
    data = np.column_stack([base + rng.normal(0, 0.5, 30), base + rng.normal(0, 0.5, 30)])
    r = intraclass_correlation(data, model="two-way-random")
    assert r["icc"] > 0.95

    long = pd.DataFrame({
        "target": np.repeat(np.arange(30), 2),
        "rater": np.tile([0, 1], 30),
        "score": data.ravel(),
    })
    ref = pg.intraclass_corr(data=long, targets="target", raters="rater", ratings="score")
    icc2 = float(ref[ref["Type"] == "ICC(A,1)"]["ICC"].iloc[0])
    assert r["icc"] == pytest.approx(icc2, rel=1e-6)


# --------------------------------------------------------------------------
# Contratos clave core<->UI (los KeyError que crasheaban la app)
# --------------------------------------------------------------------------

def test_anova_oneway_tiene_alias_F():
    from src.core.statistics import anova_oneway
    g1 = [1, 2, 3, 4, 5]; g2 = [2, 3, 4, 5, 6]; g3 = [5, 6, 7, 8, 9]
    r = anova_oneway([g1, g2, g3])
    f_ref, p_ref = stats.f_oneway(g1, g2, g3)
    assert r["F"] == pytest.approx(f_ref) and r["f"] == pytest.approx(f_ref)
    assert r["p"] == pytest.approx(p_ref)


def test_shapiro_tiene_alias_statistic():
    from src.core.statistics import normality_test
    data = np.array([2.1, 2.4, 2.9, 3.1, 3.3, 3.8, 4.0, 4.2, 4.5])
    r = normality_test(data)
    w_ref, p_ref = stats.shapiro(data)
    assert r["statistic"] == pytest.approx(w_ref) and r["w"] == pytest.approx(w_ref)
    assert r["p"] == pytest.approx(p_ref)


def test_sign_test_tiene_statistic():
    from src.core.statistics import sign_test
    d1 = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=float)
    d2 = np.array([2, 3, 4, 5, 6, 7, 8, 9, 10, 11], dtype=float)
    r = sign_test(d1, d2)
    assert "statistic" in r
    assert 0 <= r["p"] <= 1


def test_ttest_paired_y_ind_coinciden_con_scipy():
    from src.core.statistics import ttest_paired, ttest_ind
    a = np.array([1.2, 2.5, 3.1, 4.8, 5.3, 6.7, 7.2])
    b = np.array([2.1, 3.6, 2.9, 5.5, 4.8, 7.3, 8.1])
    rp = ttest_paired(a, b)
    t_ref, p_ref = stats.ttest_rel(a, b)
    assert rp["t"] == pytest.approx(t_ref) and rp["p"] == pytest.approx(p_ref)

    ri = ttest_ind(a, b)
    t_ref2, p_ref2 = stats.ttest_ind(a, b, equal_var=False)
    assert ri["t"] == pytest.approx(t_ref2) and ri["p"] == pytest.approx(p_ref2)


# --------------------------------------------------------------------------
# Sanidad de otras pruebas clave
# --------------------------------------------------------------------------

def test_odds_ratio_2x2():
    from src.core.diagnostic_tests import odds_ratio
    a, b, c, d = 30, 10, 15, 25
    r = odds_ratio(a, b, c, d)
    assert r["or"] == pytest.approx((a * d) / (b * c))


def test_bland_altman_loa():
    from src.core.bland_altman import bland_altman_analysis
    m1 = np.array([10, 12, 14, 16, 18, 20.0])
    m2 = np.array([11, 11, 15, 15, 19, 19.0])
    r = bland_altman_analysis(m1, m2)
    diffs = m1 - m2
    assert r["mean_difference"] == pytest.approx(np.mean(diffs))
    assert r["loa_upper"] == pytest.approx(np.mean(diffs) + 1.96 * np.std(diffs, ddof=1))


def test_pearson_coincide_con_scipy():
    from src.core.statistics import pearson_r
    x = np.array([1, 2, 3, 4, 5, 6.0])
    y = np.array([2, 4, 5, 4, 6, 7.0])
    r = pearson_r(x, y)
    r_ref, p_ref = stats.pearsonr(x, y)
    assert r["r"] == pytest.approx(r_ref) and r["p"] == pytest.approx(p_ref)
