"""Arreglos de fórmulas del core — auditoría del 26 sep (docs/AUDITORIA-2026-09.md).

Cada test lleva en el nombre la propiedad que el código violaba y, en el
docstring, el id del hallazgo. El oráculo es siempre independiente: scipy,
statsmodels, lifelines, pingouin, o el texto de la norma (CLSI EP28-A3c y
EP09c, leídos del PDF).
"""
import numpy as np
import pandas as pd
import pytest
from scipy import stats


# ------------------------------------------------------------------ A3 LR
def test_el_ic_de_las_razones_de_verosimilitud_usa_la_varianza_de_simel():
    """A3: el EE de ln(LR+) sumaba términos de LR−, y LR− reusaba el mismo EE."""
    from src.core.diagnostic_tests import likelihood_ratios
    a, b, c, d = 90, 20, 10, 80
    r = likelihood_ratios(a, b, c, d)
    se_p = np.sqrt(1/a - 1/(a+c) + 1/b - 1/(b+d))
    se_n = np.sqrt(1/c - 1/(a+c) + 1/d - 1/(b+d))
    assert r["ci_plr"] == pytest.approx(np.exp(np.log(4.5) + np.array([-1, 1]) * 1.959964 * se_p), rel=1e-4)
    assert r["ci_nlr"] == pytest.approx(np.exp(np.log(0.125) + np.array([-1, 1]) * 1.959964 * se_n), rel=1e-4)


def test_el_ic_de_lr_positiva_cubre_el_95_por_ciento():
    from src.core.diagnostic_tests import likelihood_ratios
    rng = np.random.default_rng(7)
    verdadera = 0.85 / 0.20
    cubre = 0
    for _ in range(1500):
        a = rng.binomial(100, 0.85); d = rng.binomial(100, 0.80)
        r = likelihood_ratios(a, 100 - d, 100 - a, d)
        cubre += r["ci_plr"][0] <= verdadera <= r["ci_plr"][1]
    assert 0.93 <= cubre / 1500 <= 0.97


# ------------------------------------------------------------------ A4 media recortada
def test_el_ee_de_la_media_recortada_es_el_de_tukey_mclaughlin():
    """A4: usaba la DE de la muestra recortada; va la varianza winsorizada."""
    from scipy.stats import mstats
    from src.core.statistics import trimmed_mean
    x = np.random.default_rng(3).standard_t(3, 40)
    r = trimmed_mean(x)
    assert r["se"] == pytest.approx(float(mstats.trimmed_stde(x, limits=(0.1, 0.1))), rel=1e-6)


def test_el_ic_de_la_media_recortada_cubre_el_95_por_ciento():
    from src.core.statistics import trimmed_mean
    rng = np.random.default_rng(3)
    cubre = sum(r["ci95"][0] <= 0 <= r["ci95"][1]
                for r in (trimmed_mean(rng.standard_t(3, 30)) for _ in range(1500)))
    assert 0.93 <= cubre / 1500 <= 0.97          # antes: 0,86


# ------------------------------------------------------------------ A5 Grubbs
@pytest.mark.parametrize("n", [8, 15, 30])
def test_el_p_de_grubbs_vale_alfa_justo_en_el_g_critico(n):
    """A5: en G = G crítico declaraba outlier con p = 0,13 (n=8)."""
    from src.core.outliers import grubbs_test
    rng = np.random.default_rng(n)
    base = np.sort(rng.normal(0, 1, n - 1))
    t2 = stats.t.ppf(1 - 0.05 / (2 * n), n - 2) ** 2
    gcrit = (n - 1) / np.sqrt(n) * np.sqrt(t2 / (n - 2 + t2))

    def g(v):
        z = np.r_[base, v]
        return (v - z.mean()) / z.std(ddof=1)
    lo, hi = base.max(), base.max() + 30
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if g(mid) < gcrit else (lo, mid)
    r = grubbs_test(np.r_[base, hi])
    assert r["p"] == pytest.approx(0.05, abs=1e-4)


def test_grubbs_no_declara_outlier_con_p_mayor_que_alfa():
    from src.core.outliers import grubbs_test
    rng = np.random.default_rng(0)
    for _ in range(300):
        x = np.r_[rng.normal(0, 1, 12), rng.normal(0, 1) * 4]
        r = grubbs_test(x)
        assert r["is_outlier"] == (r["p"] < 0.05)


# ------------------------------------------------------------------ A6 log-rank
def test_el_log_rank_cuenta_los_eventos_en_tiempo_cero():
    """A6: descartaba t=0 y dejaba esos sujetos en el conjunto de riesgo."""
    from lifelines.statistics import logrank_test
    from src.core.survival import log_rank_test
    t1 = np.array([0, 0, 2, 3, 5, 8, 9, 12, 15, 20], float)
    e1 = np.array([1, 1, 1, 0, 1, 1, 0, 1, 1, 0])
    t2 = np.array([0, 4, 6, 7, 10, 14, 18, 22, 25, 30], float)
    e2 = np.array([1, 0, 1, 1, 0, 1, 1, 0, 1, 1])
    r = log_rank_test(t1, e1, t2, e2)
    assert r["chi2"] == pytest.approx(logrank_test(t1, t2, e1, e2).test_statistic, rel=1e-9)


def test_el_log_rank_rechaza_tiempos_negativos():
    from src.core.survival import log_rank_test
    r = log_rank_test([-1, 2, 3], [1, 1, 0], [1, 2, 3], [1, 0, 1])
    assert isinstance(r, dict) and "error" in r


# ------------------------------------------------------------------ A7 edad
def test_los_intervalos_por_edad_no_pierden_a_nadie():
    """A7: 17 de 500 sujetos (≥ 88 años) quedaban fuera de todos los grupos."""
    from src.core.reference import age_related_reference
    rng = np.random.default_rng(8)
    edad = rng.integers(18, 91, 500).astype(float)
    valor = 50 + 0.3 * edad + rng.normal(0, 5, 500)
    r = age_related_reference(edad, valor)
    assert sum(g["n"] for g in r["groups"]) == r["n_total"] == 500


# ------------------------------------------------------------------ A1 EP28
def test_los_limites_de_referencia_usan_el_rango_de_ep28():
    """A1: EP28-A3c §9.4.1 — r1 = 0,025(n+1), r2 = 0,975(n+1), interpolando."""
    from src.core.reference import reference_interval
    x = np.sort(np.random.default_rng(21).lognormal(3, 0.35, 120))
    r = reference_interval(x)
    # n = 120: r1 = 3,025 y r2 = 117,975
    assert r["lower"] == pytest.approx(x[2] + 0.025 * (x[3] - x[2]))
    assert r["upper"] == pytest.approx(x[116] + 0.975 * (x[117] - x[116]))


@pytest.mark.parametrize("n, rangos", [(120, (1, 7)), (188, (2, 9)), (250, (3, 12)),
                                       (500, (7, 19)), (1000, (17, 34))])
def test_el_ic_90_de_los_limites_es_el_de_la_tabla_8_de_ep28(n, rangos):
    """A1: EP28 §9.5.1 — IC 90 % por rangos (tabla 8, Solberg 1987), no bootstrap 95 %."""
    from src.core.reference import reference_interval
    x = np.sort(np.random.default_rng(n).normal(100, 10, n))
    r = reference_interval(x)
    a, b = rangos
    assert r["ci_lower_low"] == pytest.approx(x[a - 1])
    assert r["ci_lower_high"] == pytest.approx(x[b - 1])
    assert r["ci_upper_low"] == pytest.approx(x[n + 1 - b - 1])
    assert r["ci_upper_high"] == pytest.approx(x[n + 1 - a - 1])
    assert r["nivel_ic"] == 0.90


def test_con_menos_de_120_no_hay_ic_normativo_y_se_dice():
    from src.core.reference import reference_interval
    r = reference_interval(np.random.default_rng(1).normal(100, 10, 60))
    assert np.isnan(r["ci_lower_low"]) and np.isnan(r["ci_upper_high"])
    assert any("120" in a for a in r["avisos"])


def test_la_tabla_de_percentiles_usa_el_mismo_rango_que_muestra_su_formula():
    """M10: la fórmula en pantalla dice k·(n+1)/100; el cálculo era el lineal."""
    from src.core.reference import percentile_table
    x = np.random.default_rng(2).normal(50, 5, 60)
    r = percentile_table(x)
    p25 = [p for p in r["percentiles"] if p["percentile"] == 25][0]
    assert p25["value"] == pytest.approx(np.percentile(x, 25, method="weibull"))


# ------------------------------------------------------------------ M1 kappa
def test_el_p_de_kappa_usa_el_ee_bajo_h0_y_hay_ic():
    """M1: el p usaba el EE bajo H1; y no había IC."""
    from statsmodels.stats.inter_rater import cohens_kappa as sm_kappa
    from src.core.agreement import cohens_kappa
    m = np.array([[20, 5], [10, 15]], float)
    r = cohens_kappa(m)
    s = sm_kappa(m)
    p0 = 2 * stats.norm.sf(abs(s.kappa / np.sqrt(s.var_kappa0)))
    assert r["p"] == pytest.approx(p0, rel=1e-9)
    assert r["ci"] == pytest.approx((s.kappa_low, s.kappa_upp), rel=1e-9)


# ------------------------------------------------------------------ M2 asimetria/curtosis
def test_las_pruebas_de_asimetria_y_curtosis_son_las_de_dagostino():
    """M2: EE asintótico → error tipo I de 0,1 % con n=10."""
    from src.core.statistics import skewness_test, kurtosis_test
    x = np.random.default_rng(4).normal(0, 1, 40)
    assert skewness_test(x)["p"] == pytest.approx(stats.skewtest(x).pvalue)
    assert kurtosis_test(x)["p"] == pytest.approx(stats.kurtosistest(x).pvalue)


# ------------------------------------------------------------------ M3 F
def test_el_p_de_la_prueba_f_nunca_pasa_de_uno():
    """M3: daba 1,008 con n muy desiguales."""
    from src.core.statistics import f_test_variances
    rng = np.random.default_rng(11)
    for _ in range(500):
        r = f_test_variances(rng.normal(0, 1, 101), rng.normal(0, 1, 3))
        assert 0 <= r["p"] <= 1


# ------------------------------------------------------------------ M4 proporciones
def test_el_ic_de_la_diferencia_de_proporciones_es_el_de_newcombe():
    """M4: usaba el EE agrupado (el de H0) para el IC."""
    from statsmodels.stats.proportion import confint_proportions_2indep
    from src.core.diagnostic_tests import compare_two_proportions
    r = compare_two_proportions(0.3, 200, 0.1, 40)
    lo, hi = confint_proportions_2indep(60, 200, 4, 40, method="newcomb", compare="diff")
    assert r["ci95"] == pytest.approx((lo, hi), rel=1e-6)


# ------------------------------------------------------------------ M5 bootstrap
def test_el_bootstrap_de_la_correlacion_con_n_chico_no_devuelve_nan():
    """M5: con n=5 algún remuestreo sale constante y el percentil propagaba el NaN."""
    from src.core.bootstrap import bootstrap_correlation
    x = np.arange(5, dtype=float)
    r = bootstrap_correlation(x, x + np.array([0.3, -0.2, 0.1, 0.4, -0.3]))
    assert np.isfinite(r["ci_lower"]) and np.isfinite(r["ci_upper"])
    assert r["n_invalidos"] > 0 and any("constante" in a for a in r["avisos"])


# ------------------------------------------------------------------ M6 colinealidad
def test_la_regresion_multiple_rechaza_predictoras_colineales():
    """M6: devolvía EE = 0 y p = 1 en todos los coeficientes."""
    from src.core.regression import multiple_regression
    rng = np.random.default_rng(0)
    x1 = rng.normal(0, 1, 30)
    r = multiple_regression(np.c_[x1, 2 * x1, rng.normal(0, 1, 30)], 1 + x1 + rng.normal(0, 1, 30))
    assert isinstance(r, dict) and "colineal" in r.get("error", "")


# ------------------------------------------------------------------ M7 medias
@pytest.mark.parametrize("fn", ["geometric_mean", "harmonic_mean"])
def test_las_medias_geometrica_y_armonica_no_descartan_en_silencio(fn):
    """M7: [0, 2, 8, −1, 4] daba MG = 4 usando solo los positivos."""
    from src.core import statistics as st
    r = getattr(st, fn)([0.0, 2.0, 8.0, -1.0, 4.0])
    assert isinstance(r, dict) and "error" in r and "2" in r["error"]


def test_la_media_geometrica_trae_su_ic():
    from src.core.statistics import geometric_mean
    x = np.random.default_rng(5).lognormal(2, 0.4, 30)
    r = geometric_mean(x)
    lg = np.log(x)
    tc = stats.t.ppf(0.975, 29)
    assert r["gm"] == pytest.approx(np.exp(lg.mean()))
    assert r["ci95"] == pytest.approx(np.exp(lg.mean() + np.array([-1, 1]) * tc * lg.std(ddof=1) / np.sqrt(30)))


# ------------------------------------------------------------------ A13 Deming
def test_lambda_de_deming_respeta_su_definicion_contra_odr():
    """A13: λ = var_err(x)/var_err(y) se usaba invertido."""
    from scipy import odr
    from src.core.agreement import deming_regression
    rng = np.random.default_rng(4)
    verdad = rng.uniform(20, 200, 300)
    sx, sy = 6.0, 1.5
    x = verdad + rng.normal(0, sx, 300)
    y = 1.10 * verdad + rng.normal(0, sy, 300)
    ref = odr.ODR(odr.RealData(x, y, sx=sx, sy=sy), odr.unilinear).run().beta[0]
    assert deming_regression(x, y, lambda_ratio=sx**2 / sy**2)["slope"] == pytest.approx(ref, abs=5e-4)


# ------------------------------------------------------------------ M9 Passing-Bablok
def _pb_ep09c(x, y):
    """EP09c, apéndice I2, literal: xᵢ = xⱼ → S = ±∞ según yᵢ − yⱼ; 0/0 se ignora."""
    n = len(x)
    s = []
    for i in range(n - 1):
        for j in range(i + 1, n):
            dx, dy = x[i] - x[j], y[i] - y[j]
            if dx == 0:
                if dy != 0:
                    s.append(np.inf if dy > 0 else -np.inf)
                continue
            v = dy / dx
            if v != -1:
                s.append(v)
    s = np.sort(np.array(s))
    N, K = len(s), int(np.sum(s < -1))
    return s[(N + 1) // 2 + K - 1] if N % 2 else 0.5 * (s[N // 2 + K - 1] + s[N // 2 + K])


def test_passing_bablok_toma_los_pares_verticales_como_infinitos():
    """M9: descartaba los pares con xᵢ = xⱼ; EP09c los toma como ±∞."""
    from src.core.passing_bablok import passing_bablok
    rng = np.random.default_rng(2)
    v = rng.uniform(50, 150, 60)
    x = np.round(v + rng.normal(0, 3, 60))
    y = np.round(1.05 * v + rng.normal(0, 3, 60))
    assert passing_bablok(x, y)["slope"] == pytest.approx(_pb_ep09c(x, y), abs=1e-12)


def test_passing_bablok_no_depende_del_orden_de_las_filas():
    """El signo que EP09c le da al par vertical depende del orden; el estimador no."""
    from src.core.passing_bablok import passing_bablok
    rng = np.random.default_rng(5)
    v = rng.uniform(50, 150, 50)
    x = np.round(v + rng.normal(0, 3, 50)); y = np.round(v + rng.normal(0, 3, 50))
    orden = rng.permutation(50)
    a, b = passing_bablok(x, y), passing_bablok(x[orden], y[orden])
    assert a["slope"] == b["slope"] and a["ci_slope"] == b["ci_slope"]


# ------------------------------------------------------------------ A11 seriadas
def test_la_tendencia_de_las_mediciones_seriadas_se_prueba_sobre_las_pendientes():
    """A11: el 'p global' trataba las n×k mediciones como independientes (19,7 % de
    falsos positivos con pendientes individuales y sin tendencia)."""
    from src.core.serial_measurements import serial_measurements_summary
    fp = 0
    for s in range(400):
        r = np.random.default_rng(s)
        d = 50 + r.normal(0, 2, (8, 1)) * np.arange(6) + r.normal(0, 1, (8, 6))
        fp += serial_measurements_summary(d)["p_tendencia"] < 0.05
    assert fp / 400 < 0.08


def test_la_prueba_de_tendencia_es_la_t_sobre_las_pendientes_individuales():
    from src.core.serial_measurements import serial_measurements_summary
    d = np.random.default_rng(1).normal(10, 2, (12, 5)) + np.arange(5) * 0.3
    r = serial_measurements_summary(d)
    pend = [stats.linregress(np.arange(5), fila).slope for fila in d]
    assert r["p_tendencia"] == pytest.approx(stats.ttest_1samp(pend, 0).pvalue)
