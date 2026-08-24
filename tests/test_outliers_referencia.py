"""Outliers e intervalos de referencia contra ejemplos publicados.

El ESD generalizado se verifica contra el ejemplo del NIST/SEMATECH porque ese
dataset esta construido justo para el caso dificil: R_1 y R_2 NO superan su
valor critico y R_3 SI. La respuesta publicada es 3 outliers. Evaluando cada
punto por su cuenta se declaraba 1, que es perder exactamente el
enmascaramiento que el test existe para resolver.
"""
import numpy as np
import pytest
from scipy import stats

from src.core.outliers import generalized_esd, grubbs_test, tukey_outliers
from src.core.reference import reference_interval, N_MINIMO_EP28

# NIST/SEMATECH e-Handbook 1.3.5.17.3
NIST = [-0.25, 0.68, 0.94, 1.15, 1.20, 1.26, 1.26, 1.34, 1.38, 1.43, 1.49,
        1.49, 1.55, 1.56, 1.58, 1.65, 1.69, 1.70, 1.76, 1.77, 1.81, 1.91,
        1.94, 1.96, 1.99, 2.06, 2.09, 2.10, 2.14, 2.15, 2.23, 2.24, 2.26,
        2.35, 2.37, 2.40, 2.47, 2.54, 2.62, 2.64, 2.90, 2.92, 2.92, 2.93,
        3.21, 3.26, 3.30, 3.59, 3.68, 4.30, 4.64, 5.34, 5.42, 6.01]
NIST_R = [3.118, 2.942, 3.179, 2.810, 2.815, 2.848, 2.279, 2.310, 2.101, 2.067]
NIST_LAMBDA = [3.159, 3.151, 3.143, 3.136, 3.128, 3.120, 3.111, 3.103, 3.094, 3.085]


# ---------------- ESD generalizado ----------------

def test_los_estadisticos_r_coinciden_con_el_nist():
    r = generalized_esd(NIST, max_outliers=10, alpha=0.05)
    for i, esperado in enumerate(NIST_R):
        assert r["test_stats"][i] == pytest.approx(esperado, abs=0.001)


def test_los_valores_criticos_lambda_coinciden_con_el_nist():
    """lambda_i usa la n ORIGINAL. Restarle `i` a una n ya reducida hacia que
    el error creciera con cada paso: -0.003 en el primero, -0.100 en el decimo."""
    r = generalized_esd(NIST, max_outliers=10, alpha=0.05)
    for i, esperado in enumerate(NIST_LAMBDA):
        assert r["critical_vals"][i] == pytest.approx(esperado, abs=0.002), (
            f"lambda_{i+1}: {r['critical_vals'][i]:.4f} vs NIST {esperado}")


def test_declara_los_tres_outliers_del_ejemplo_nist():
    """El caso de enmascaramiento: R_1 y R_2 no pasan, R_3 si. La regla de
    Rosner es el MAYOR i que pasa, y se declaran los i primeros."""
    r = generalized_esd(NIST, max_outliers=10, alpha=0.05)
    assert r["test_stats"][0] < r["critical_vals"][0], "premisa del ejemplo"
    assert r["test_stats"][1] < r["critical_vals"][1], "premisa del ejemplo"
    assert r["test_stats"][2] > r["critical_vals"][2], "premisa del ejemplo"
    assert r["n_outliers"] == 3
    assert sorted(r["outliers"]) == pytest.approx([5.34, 5.42, 6.01])


def test_sin_outliers_no_inventa_ninguno():
    r = np.random.default_rng(0)
    res = generalized_esd(r.normal(100, 10, 60), max_outliers=5)
    assert res["n_outliers"] <= 1, "una normal limpia no tiene 2+ outliers"


def test_no_puede_declarar_mas_de_la_mitad_de_los_datos():
    """El ESD estima media y sd de lo que queda: sacar demasiados lo vacia."""
    r = np.random.default_rng(1)
    res = generalized_esd(r.normal(0, 1, 12), max_outliers=100)
    assert res["n_outliers"] <= 6


# ---------------- Grubbs ----------------

def test_el_parametro_side_cambia_el_resultado():
    """Antes se aceptaba y se ignoraba: pedir 'upper' devolvia 'both'."""
    datos = [1.0, 2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 9.5]
    both = grubbs_test(datos, side="both")
    upper = grubbs_test(datos, side="upper")
    lower = grubbs_test(datos, side="lower")
    assert upper["g_crit"] < both["g_crit"], (
        "una cola reparte alpha entre n y no entre 2n: su critico es mas bajo")
    assert upper["is_outlier"] is True
    assert lower["is_outlier"] is False, "el extremo esta arriba, no abajo"


def test_side_desconocido_se_rechaza():
    res = grubbs_test([1.0, 2.0, 3.0, 4.0, 20.0], side="derecha")
    assert "error" in res


@pytest.mark.parametrize("semilla", range(50))
def test_el_p_de_grubbs_es_una_probabilidad(semilla):
    """El factor 2*n es una cota de Bonferroni y puede pasarse de 1. Sin
    recortar se informaban 'probabilidades' de hasta 3.58."""
    r = np.random.default_rng(semilla)
    d = r.normal(100, 10, int(r.integers(5, 60)))
    g = grubbs_test(d)
    if g and "error" not in g:
        assert 0.0 <= g["p"] <= 1.0, f"p={g['p']}"


def test_el_critico_de_grubbs_coincide_con_la_formula_publicada():
    n, alpha = 20, 0.05
    r = np.random.default_rng(2)
    g = grubbs_test(r.normal(50, 5, n), side="both", alpha=alpha)
    t2 = stats.t.ppf(1 - alpha / (2 * n), n - 2) ** 2
    esperado = ((n - 1) / np.sqrt(n)) * np.sqrt(t2 / (n - 2 + t2))
    assert g["g_crit"] == pytest.approx(esperado, rel=1e-12)


def test_un_solo_valor_extremo_se_detecta():
    d = list(np.random.default_rng(3).normal(100, 2, 30)) + [180.0]
    assert grubbs_test(d)["is_outlier"] is True


# ---------------- Tukey ----------------

def test_tukey_usa_1_5_y_3_iqr():
    r = np.random.default_rng(4)
    res = tukey_outliers(r.normal(100, 10, 200))
    iqr = res["q75"] - res["q25"]
    assert res["upper_inner"] == pytest.approx(res["q75"] + 1.5 * iqr)
    assert res["upper_outer"] == pytest.approx(res["q75"] + 3.0 * iqr)
    assert res["n_extreme"] <= res["n_mild"], "los extremos son un subconjunto"


# ---------------- Intervalo de referencia ----------------

@pytest.mark.parametrize("n", [15, 40, 119])
def test_avisa_cuando_no_llega_al_minimo_de_ep28(n):
    """CLSI EP28-A3c pide 120 sujetos para ESTABLECER un intervalo no
    parametrico. Antes no lo mencionaba en ningun n, y el usuario lleva ese
    numero a una acreditacion."""
    r = np.random.default_rng(1)
    res = reference_interval(r.normal(100, 15, n))
    assert res["cumple_ep28"] is False
    assert any(str(N_MINIMO_EP28) in a for a in res["avisos"]), res["avisos"]


@pytest.mark.parametrize("n", [120, 200, 500])
def test_no_molesta_cuando_si_llega(n):
    """Un aviso que aparece siempre deja de leerse."""
    r = np.random.default_rng(1)
    res = reference_interval(r.normal(100, 15, n))
    assert res["cumple_ep28"] is True
    assert res["avisos"] == []


def test_dice_cuantos_datos_sostienen_cada_limite():
    r = np.random.default_rng(1)
    res = reference_interval(r.normal(100, 15, 30))
    assert res["n_bajo_limite"] >= 1 and res["n_sobre_limite"] >= 1
    assert any("dato" in a for a in res["avisos"])


def test_el_intervalo_contiene_aproximadamente_el_95_por_ciento():
    r = np.random.default_rng(7)
    d = r.normal(100, 15, 5000)
    res = reference_interval(d)
    dentro = np.mean((d >= res["lower"]) & (d <= res["upper"]))
    assert dentro == pytest.approx(0.95, abs=0.01)


def test_los_ic_de_los_limites_contienen_a_los_limites():
    r = np.random.default_rng(8)
    res = reference_interval(r.normal(100, 15, 200))
    assert res["ci_lower_low"] <= res["lower"] <= res["ci_lower_high"]
    assert res["ci_upper_low"] <= res["upper"] <= res["ci_upper_high"]
