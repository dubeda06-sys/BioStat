"""ANCOVA, probit y medidas repetidas contra statsmodels y pingouin.

Auditoría 2026-09: K4 (ANCOVA daba F = 168 donde corresponde 4,7, y SS del
error negativa), K5 (probit con EE fijos en 0,1 y AIC con el signo cambiado) y
K9 (épsilon de Greenhouse-Geisser sin doble centrado).
"""
import numpy as np
import pandas as pd
import pingouin as pg
import pytest
import statsmodels.api as sm
import statsmodels.formula.api as smf


def _hoja_ancova(semilla):
    rng = np.random.default_rng(semilla)
    g = np.repeat(["A", "B", "C"], 20)
    x = rng.normal(50, 10, 60) + np.where(g == "C", 8, 0)
    y = 5 + 0.6 * x + np.where(g == "B", 3, 0) + rng.normal(0, 4, 60)
    return pd.DataFrame({"y": y, "g": g, "x": x})


@pytest.mark.parametrize("semilla", [1, 2, 3])
def test_ancova_coincide_con_statsmodels_tipo_ii(semilla):
    from src.core.ancova import ancova
    df = _hoja_ancova(semilla)
    r = ancova(df["y"], df["g"], df["x"])
    aov = sm.stats.anova_lm(smf.ols("y ~ C(g) + x", df).fit(), typ=2)
    assert r["F"] == pytest.approx(aov.loc["C(g)", "F"], rel=1e-9)
    assert r["p"] == pytest.approx(aov.loc["C(g)", "PR(>F)"], rel=1e-9)
    assert r["F_covariate"] == pytest.approx(aov.loc["x", "F"], rel=1e-9)
    assert r["ss_error"] == pytest.approx(aov.loc["Residual", "sum_sq"], rel=1e-9)
    assert r["ss_error"] > 0


def test_ancova_da_las_medias_ajustadas_con_el_signo_correcto():
    from src.core.ancova import ancova
    df = _hoja_ancova(1)
    r = ancova(df["y"], df["g"], df["x"])
    fit = smf.ols("y ~ C(g) + x", df).fit()
    xbar = df["x"].mean()
    for grupo in ("A", "B", "C"):
        esperada = fit.predict(pd.DataFrame({"g": [grupo], "x": [xbar]}))[0]
        assert r["medias_ajustadas"][grupo] == pytest.approx(esperada, rel=1e-9)


def test_ancova_avisa_si_las_pendientes_no_son_paralelas():
    """El supuesto central de ANCOVA: la covariable pesa igual en todos los grupos."""
    from src.core.ancova import ancova
    rng = np.random.default_rng(9)
    g = np.repeat(["A", "B"], 40)
    x = rng.normal(50, 10, 80)
    y = np.where(g == "A", 0.2, 1.5) * x + rng.normal(0, 3, 80)
    r = ancova(y, g, x)
    assert r["p_interaccion"] < 0.05
    assert any("paralel" in a for a in r["avisos"])


@pytest.mark.parametrize("n, b1", [(60, 0.8), (200, 0.3), (40, 1.5)])
def test_probit_coincide_con_statsmodels(n, b1):
    from scipy import stats
    from src.core.probit import probit_regression
    rng = np.random.default_rng(n)
    x = rng.normal(0, 1, n)
    y = (rng.random(n) < stats.norm.cdf(-0.2 + b1 * x)).astype(float)
    r = probit_regression(x.reshape(-1, 1), y)
    ref = sm.Probit(y, sm.add_constant(x)).fit(disp=0)
    assert r["coefficients"] == pytest.approx(np.asarray(ref.params), rel=1e-5)
    assert r["se"] == pytest.approx(np.asarray(ref.bse), rel=1e-5)
    assert r["p_values"] == pytest.approx(np.asarray(ref.pvalues), rel=1e-4)
    assert r["aic"] == pytest.approx(ref.aic, rel=1e-9)


def test_probit_rechaza_una_respuesta_que_no_es_binaria():
    from src.core.probit import probit_regression
    r = probit_regression(np.arange(10.0).reshape(-1, 1), np.arange(10.0))
    assert "error" in r


@pytest.mark.parametrize("semilla", [1, 2])
def test_greenhouse_geisser_coincide_con_pingouin(semilla):
    from src.core.repeated_measures import repeated_measures_anova
    rng = np.random.default_rng(semilla)
    n, k = 15, 4
    datos = (10 + rng.normal(0, 3, (n, 1)) + np.arange(k) * 0.8
             + rng.normal(0, 1, (n, k)) * np.array([0.5, 1, 2, 4]))
    r = repeated_measures_anova(datos)
    largo = pd.DataFrame({"s": np.repeat(np.arange(n), k), "t": np.tile(np.arange(k), n),
                          "y": datos.ravel()})
    ref = pg.rm_anova(data=largo, dv="y", within="t", subject="s", correction=True)
    assert r["epsilon"] == pytest.approx(float(ref.loc[0, "eps"]), rel=1e-9)
    assert r["p_gg"] == pytest.approx(float(ref.loc[0, "p_GG_corr"]), rel=1e-9)
    assert r["F"] == pytest.approx(float(ref.loc[0, "F"]), rel=1e-9)


def test_medidas_repetidas_rechaza_sujetos_incompletos_con_motivo():
    from src.core.repeated_measures import repeated_measures_anova
    d = np.random.default_rng(0).normal(0, 1, (10, 3))
    d[2, 1] = np.nan
    r = repeated_measures_anova(d)
    assert r["n_excluidos"] == 1 and r["n"] == 9
