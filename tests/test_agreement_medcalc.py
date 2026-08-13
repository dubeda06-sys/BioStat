"""Tests de concordancia contra valores VERIFICADOS de MedCalc 23.6.5.

El set de datos es real: 15 muestras del panel de evaluacion externa CAP para
carga viral de EBV (log10), comparando el consenso all-method del CAP contra dos
ensayos de PCR cuantitativa. Los valores esperados de Bland-Altman salen de los
informes que genero MedCalc 23.6.5 sobre estos mismos datos, con precision
completa leida del atributo `title` de cada resultado del informe HTML.

Eso hace que estos tests sean una comprobacion cruzada contra una implementacion
independiente y ampliamente usada, no contra nuestra propia aritmetica.
"""
import numpy as np
import pytest
from scipy import stats

from src.core.bland_altman import bland_altman_analysis, concordance_correlation

# CAP = consenso all-method; A = RQ-EBV (AB Analitica); B = EBVq Viasure. log10.
CAP_CP = [5.352, 3.511, 3.677, 5.116, 4.726, 4.220, 5.740, 4.365,
          4.961, 3.902, 4.412, 3.142, 3.700, 4.647, 3.381]
A_CP = [5.249, 3.508, 3.478, 4.614, 3.900, 4.481, 5.848, 4.300,
        5.384, 4.143, 5.155, 3.796, 3.400, 4.850, 3.511]
CAP_UI = [4.817, 3.089, 3.292, 4.155, 3.775, 3.877, 5.279, 3.682,
          4.946, 3.884, 4.745, 3.507, 3.629, 4.555, 3.152]
A_UI = [4.793, 3.052, 3.022, 4.158, 3.444, 4.025, 5.393, 3.844,
        4.928, 3.687, 4.699, 3.340, 2.944, 4.394, 3.055]
B_UI = [5.004771946, 3.660493608, 2.973167585, 3.740984154, 3.429635376,
        3.900010697, 5.250572632, 3.657176558, 5.024827042, 4.084154933,
        4.770045256, 3.554841783, 3.629348630, 4.702086515, 3.417140739]


# --------------------------------------------------------------------------
# Bland-Altman: media y limites de concordancia contra MedCalc
# --------------------------------------------------------------------------

@pytest.mark.parametrize("m1,m2,mean_exp,lo_exp,hi_exp", [
    # informe mc_AB38: CAP vs AB Analitica, cp/mL
    (CAP_CP, A_CP, -0.051000000, -0.86156605, 0.75956605),
    # informe mc_1F04: CAP_UI vs AB_UI
    (CAP_UI, A_UI, 0.10706667, -0.31438312, 0.52851646),
    # informe mc_65E8: CAP_UI vs Viasure_UI
    (CAP_UI, B_UI, -0.027683830, -0.52069496, 0.46532730),
])
def test_bland_altman_contra_medcalc(m1, m2, mean_exp, lo_exp, hi_exp):
    res = bland_altman_analysis(m1, m2)
    assert res["n"] == 15
    assert res["mean_difference"] == pytest.approx(mean_exp, abs=1e-7)
    assert res["loa_lower"] == pytest.approx(lo_exp, abs=1e-7)
    assert res["loa_upper"] == pytest.approx(hi_exp, abs=1e-7)


def test_ic_de_los_loa_usa_t_no_z():
    """El IC de un limite de concordancia se multiplica por t(n-1), no por 1.96.

    Valores del informe mc_AB38 de MedCalc (CAP vs AB Analitica, cp/mL):
    LoA inferior -0.86156605, IC [-1.26205410, -0.46107801].
    Con 1.96 en vez de t(14)=2.1448 el semiancho sale ~9% mas corto.
    """
    res = bland_altman_analysis(CAP_CP, A_CP)
    assert res["ci_lower"][0] == pytest.approx(-1.26205410, abs=1e-6)
    assert res["ci_lower"][1] == pytest.approx(-0.46107801, abs=1e-6)
    assert res["t_crit"] == pytest.approx(stats.t.ppf(0.975, 14))

    semiancho = res["ci_lower"][1] - res["loa_lower"]
    assert semiancho == pytest.approx(res["t_crit"] * res["se_loa"], rel=1e-9)
    assert semiancho > 1.96 * res["se_loa"]      # el bug anterior daba esto


def test_loa_no_parametrico_y_normalidad():
    """Percentiles 2,5-97,5 como alternativa sin supuesto de normalidad."""
    res = bland_altman_analysis(CAP_CP, A_CP)
    lo, hi = np.percentile(np.asarray(A_CP) - np.asarray(CAP_CP), [2.5, 97.5])
    # el modulo calcula diffs = m1 - m2, o sea CAP - A: se invierte el signo
    lo_esp, hi_esp = np.percentile(np.asarray(CAP_CP) - np.asarray(A_CP), [2.5, 97.5])
    assert res["loa_np_lower"] == pytest.approx(lo_esp)
    assert res["loa_np_upper"] == pytest.approx(hi_esp)
    # estas diferencias SI son compatibles con normal (Shapiro-Wilk P=0.98)
    assert res["shapiro_p"] > 0.05
    assert res["normal_diffs"] is True


# --------------------------------------------------------------------------
# Eje X: referencia vs promedio (Krouwer 2008 / CLSI EP09)
# --------------------------------------------------------------------------

def test_pendiente_contra_referencia_difiere_de_contra_promedio():
    """Con una referencia, el grafico clasico ATENUA el sesgo proporcional.

    Datos reales: Viasure vs consenso CAP en cp/mL. Contra CAP la pendiente de
    la diferencia es +0.336 (P=0.08); contra el promedio se aplana a +0.097
    (P=0.67). Es el motivo por el que EP09 distingue metodo de referencia.
    """
    B_CP = [4.785, 3.441, 2.754, 3.521, 3.210, 3.680, 5.031, 3.438,
            4.805, 3.865, 4.550, 3.335, 3.410, 4.483, 3.198]
    res = bland_altman_analysis(CAP_CP, B_CP, reference="x")

    assert res["reference"] == "x"
    assert res["x_axis_label"] == "referencia"
    np.testing.assert_allclose(res["x_axis"], np.asarray(CAP_CP))

    assert res["slope_vs_reference"]["slope"] == pytest.approx(0.3356, abs=5e-4)
    assert res["slope_vs_mean"]["slope"] == pytest.approx(0.0968, abs=5e-4)
    # el clasico da un P mucho mayor: enmascara el sesgo proporcional
    assert res["slope_vs_mean"]["p"] > res["slope_vs_reference"]["p"]


def test_sin_referencia_no_hay_pendiente_contra_referencia():
    res = bland_altman_analysis(CAP_CP, A_CP)
    assert res["reference"] is None
    assert res["slope_vs_reference"] is None
    assert res["x_axis_label"] == "promedio"


# --------------------------------------------------------------------------
# CCC de Lin: identidad rho_c = rho * Cb
# --------------------------------------------------------------------------

@pytest.mark.parametrize("m1,m2", [(CAP_CP, A_CP), (CAP_UI, A_UI), (CAP_UI, B_UI)])
def test_ccc_cumple_la_identidad_rho_por_cb(m1, m2):
    """rho_c = rho * Cb debe cumplirse EXACTO.

    Es la definicion del estadistico y la formula que publica el manual de
    MedCalc. Con momentos muestrales (ddof=1) la identidad se rompe y la
    descomposicion deja de ser coherente con el CCC reportado.
    """
    res = concordance_correlation(m1, m2)
    assert res["ccc"] == pytest.approx(res["rho"] * res["cb"], abs=1e-12)


def test_ccc_descomposicion_separa_precision_de_veracidad():
    """Dos ensayos con el mismo CAP: uno falla en veracidad, el otro en precision.

    Viasure en cp/mL tiene Cb=0.807 (problema de VERACIDAD: subestima ~3x).
    AB Analitica en cp/mL tiene Cb=0.997 pero rho=0.860 (problema de PRECISION).
    """
    B_CP = [4.785, 3.441, 2.754, 3.521, 3.210, 3.680, 5.031, 3.438,
            4.805, 3.865, 4.550, 3.335, 3.410, 4.483, 3.198]
    vias = concordance_correlation(CAP_CP, B_CP)
    ab = concordance_correlation(CAP_CP, A_CP)

    assert vias["cb"] == pytest.approx(0.8073, abs=5e-4)
    assert vias["rho"] == pytest.approx(0.7222, abs=5e-4)
    assert vias["ccc"] == pytest.approx(0.5831, abs=5e-4)

    assert ab["cb"] == pytest.approx(0.9974, abs=5e-4)
    assert ab["rho"] == pytest.approx(0.8598, abs=5e-4)
    assert ab["ccc"] == pytest.approx(0.8575, abs=5e-4)

    # el defecto esta en distinto sitio en cada ensayo
    assert vias["cb"] < ab["cb"]
    assert vias["rho"] < ab["rho"]


def test_ccc_escala_de_mcbride():
    from src.core.bland_altman import _mcbride_strength
    assert _mcbride_strength(0.85) == "Pobre"
    assert _mcbride_strength(0.92) == "Moderada"
    assert _mcbride_strength(0.97) == "Sustancial"
    assert _mcbride_strength(0.995) == "Casi perfecta"
    assert concordance_correlation(CAP_CP, A_CP)["strength"] == "Pobre"
    assert concordance_correlation(CAP_UI, A_UI)["strength"] == "Moderada"


def test_ccc_ic_contiene_al_estimador_y_es_finito():
    res = concordance_correlation(CAP_UI, A_UI)
    assert np.isfinite(res["ci_low"]) and np.isfinite(res["ci_high"])
    assert res["ci_low"] < res["ccc"] < res["ci_high"]
    # comprobado contra bootstrap de 10000 remuestreos: [0.840, 0.987]
    assert res["ci_low"] == pytest.approx(0.867, abs=0.03)
    assert res["ci_high"] == pytest.approx(0.980, abs=0.02)


def test_ccc_perfecto_cuando_los_metodos_son_identicos():
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    res = concordance_correlation(x, x)
    assert res["ccc"] == pytest.approx(1.0)
    assert res["rho"] == pytest.approx(1.0)
    assert res["cb"] == pytest.approx(1.0)


def test_ccc_conserva_las_claves_previas():
    """Compatibilidad: la UI y el omni leen estas claves."""
    res = concordance_correlation(CAP_CP, A_CP)
    for k in ("ccc", "mean1", "mean2", "var1", "var2", "covariance"):
        assert k in res
