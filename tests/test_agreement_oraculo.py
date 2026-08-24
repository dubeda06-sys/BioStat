"""Concordancia verificada contra implementaciones independientes.

Un test que compara BioStat contra si mismo solo prueba que el codigo no
cambio. Estos comparan contra sklearn, scipy.odr y contra el valor verdadero
de un modelo simulado: si la formula esta mal, no hay forma de que coincidan.

Asi aparecio el kappa ponderado devolviendo -55, con kappa acotado a [-1, 1]:
la matriz de frecuencias esperadas se dividia por n dos veces, dejaba p_e ~ 1
y el cociente estallaba contra un denominador ~0. Se mostraba en la UI.
"""
import numpy as np
import pytest
from scipy import odr
from sklearn.metrics import cohen_kappa_score

from src.core.agreement import (cohens_kappa, weighted_kappa, deming_regression,
                                cv_from_duplicates)
from src.core.bland_altman import bland_altman_analysis, concordance_correlation


def _matriz(a, b, k):
    m = np.zeros((k, k))
    for i, j in zip(a, b):
        m[i, j] += 1
    return m


# ---------------- Kappa contra sklearn ----------------

@pytest.mark.parametrize("k", [2, 3, 4, 5])
@pytest.mark.parametrize("pesos", ["linear", "quadratic"])
def test_kappa_ponderado_coincide_con_sklearn(k, pesos):
    r = np.random.default_rng(200 + k)
    a = r.integers(0, k, 300)
    b = np.where(r.random(300) < 0.75, a, r.integers(0, k, 300))
    got = weighted_kappa(_matriz(a, b, k), weights=pesos)["kappa"]
    esperado = cohen_kappa_score(a, b, weights=pesos)
    assert got == pytest.approx(esperado, abs=1e-9)


@pytest.mark.parametrize("k", [2, 3, 4])
def test_kappa_simple_coincide_con_sklearn(k):
    r = np.random.default_rng(400 + k)
    a = r.integers(0, k, 300)
    b = np.where(r.random(300) < 0.7, a, r.integers(0, k, 300))
    got = cohens_kappa(_matriz(a, b, k))["kappa"]
    assert got == pytest.approx(cohen_kappa_score(a, b), abs=1e-9)


@pytest.mark.parametrize("pesos", ["linear", "quadratic"])
def test_kappa_ponderado_esta_acotado(pesos):
    """kappa vive en [-1, 1]. Cualquier cosa afuera es un error de formula, no
    un resultado. El defecto original daba -55."""
    for s in range(40):
        r = np.random.default_rng(s)
        k = int(r.integers(2, 7))
        a = r.integers(0, k, 150)
        # de concordancia perfecta a desacuerdo total
        p = s / 40
        b = np.where(r.random(150) < p, r.integers(0, k, 150), a)
        res = weighted_kappa(_matriz(a, b, k), weights=pesos)
        assert -1.0 <= res["kappa"] <= 1.0, f"semilla {s}: kappa={res['kappa']}"


def test_concordancia_perfecta_da_kappa_uno():
    a = np.array([0, 1, 2, 3] * 25)
    assert weighted_kappa(_matriz(a, a, 4))["kappa"] == pytest.approx(1.0)


def test_pesos_desconocidos_se_rechazan():
    """Antes cualquier string dejaba la matriz de pesos en ceros y devolvia 0
    en silencio, que se lee como 'no hay concordancia'."""
    r = np.random.default_rng(1)
    a = r.integers(0, 3, 60)
    res = weighted_kappa(_matriz(a, a, 3), weights="ponderado")
    assert "error" in res and "linear" in res["error"]


# ---------------- Deming contra scipy.odr ----------------

@pytest.mark.parametrize("semilla", range(4))
def test_deming_lambda_uno_es_la_regresion_ortogonal(semilla):
    """Con lambda=1 Deming ES la regresion ortogonal. scipy.odr la calcula por
    otro camino (minimizacion iterativa), asi que coincidir no es tautologico."""
    r = np.random.default_rng(50 + semilla)
    x = r.uniform(20, 200, 60) + r.normal(0, 8, 60)
    y = 1.1 * x + 4 + r.normal(0, 8, 60)
    got = deming_regression(x, y, lambda_ratio=1.0)["slope"]
    ajuste = odr.ODR(odr.RealData(x, y), odr.Model(lambda B, xx: B[0] * xx + B[1]),
                     beta0=[1.0, 0.0]).run()
    assert got == pytest.approx(ajuste.beta[0], abs=1e-4)


def test_lambda_apunta_en_la_direccion_correcta():
    """lambda = var_error(x)/var_error(y). Con mucho error en X, OLS atenua la
    pendiente; un lambda alto tiene que corregir esa atenuacion, no agravarla.
    Invertir la razon es un error silencioso: da un numero plausible y erroneo."""
    from scipy import stats as st
    r = np.random.default_rng(77)
    verdadero = r.uniform(20, 200, 200)
    x = verdadero + r.normal(0, 20, 200)   # mucho error en X
    y = verdadero + r.normal(0, 2, 200)    # poco error en Y
    ols = st.linregress(x, y).slope
    deming = deming_regression(x, y, lambda_ratio=100.0)["slope"]
    assert abs(deming - 1.0) < abs(ols - 1.0)


# ---------------- Bland-Altman contra el modelo simulado ----------------

def test_los_limites_encierran_el_95_por_ciento_de_las_diferencias():
    dentro = []
    for s in range(200):
        r = np.random.default_rng(s)
        base = r.uniform(50, 200, 60)
        res = bland_altman_analysis(base + r.normal(0, 3.5, 60),
                                    base - 2.0 + r.normal(0, 3.5, 60))
        d = res["diffs"]
        dentro.append(np.mean((d >= res["loa_lower"]) & (d <= res["loa_upper"])))
    assert 0.92 <= np.mean(dentro) <= 0.98


def test_el_ic_del_limite_usa_la_varianza_de_bland_altman_1999():
    """var(LoA) = s^2 (1/n + z^2/(2(n-1))). El error tipico es usar s/sqrt(n),
    el EE del SESGO, que da un intervalo casi la mitad de ancho."""
    r = np.random.default_rng(1)
    m1 = r.uniform(50, 200, 25)
    res = bland_altman_analysis(m1, m1 - 3 + r.normal(0, 6, 25))
    s, n = res["sd_difference"], 25
    esperado = np.sqrt(s ** 2 * (1 / n + 1.96 ** 2 / (2 * (n - 1))))
    assert res["se_loa"] == pytest.approx(esperado, rel=1e-12)
    assert res["se_loa"] > 1.5 * (s / np.sqrt(n)), "parece el EE del sesgo"


def test_el_ic_del_limite_cubre_el_limite_verdadero():
    sesgo, sd = 2.0, 5.0
    cubre = []
    for s in range(300):
        r = np.random.default_rng(s)
        base = r.uniform(50, 200, 60)
        res = bland_altman_analysis(base + r.normal(0, sd / np.sqrt(2), 60),
                                    base - sesgo + r.normal(0, sd / np.sqrt(2), 60))
        lo, hi = res["ci_upper"]
        cubre.append(lo <= sesgo + 1.96 * sd <= hi)
    assert 0.90 <= np.mean(cubre) <= 0.99


# ---------------- CCC ----------------

def test_la_identidad_del_ccc_se_cumple_en_datos_variados():
    peor = 0.0
    for s in range(200):
        r = np.random.default_rng(s)
        n = int(r.integers(5, 120))
        a = r.uniform(10, 300, n)
        b = a * r.uniform(0.8, 1.2) + r.normal(0, r.uniform(1, 30), n)
        c = concordance_correlation(a, b)
        if "error" not in c:
            peor = max(peor, abs(c["ccc"] - c["rho"] * c["cb"]))
    assert peor < 1e-12


def test_el_ic_del_ccc_cubre_el_valor_verdadero():
    """CCC verdadero calculable: base uniforme(50,200) mas ruido independiente
    de igual varianza en cada metodo, sin sesgo entre medias."""
    var_base = (200 - 50) ** 2 / 12.0
    var_err = 36.0
    verdadero = (2 * var_base) / (2 * (var_base + var_err))
    cubre = []
    for s in range(300):
        r = np.random.default_rng(9000 + s)
        base = r.uniform(50, 200, 60)
        c = concordance_correlation(base + r.normal(0, 6, 60),
                                    base + r.normal(0, 6, 60))
        if np.isfinite(c["ci_low"]):
            cubre.append(c["ci_low"] <= verdadero <= c["ci_high"])
    assert 0.90 <= np.mean(cubre) <= 0.995


# ---------------- CV de duplicados ----------------

def test_el_cv_de_duplicados_recupera_el_cv_verdadero():
    """sqrt(Sum d^2 / (2n)): el 2 sale de var(d1-d2) = 2*sigma^2. Olvidarlo
    infla el CV en sqrt(2) = 41%."""
    cv_real = 5.0
    r = np.random.default_rng(31)
    d1 = 100.0 * (1 + r.normal(0, cv_real / 100, 4000))
    d2 = 100.0 * (1 + r.normal(0, cv_real / 100, 4000))
    got = cv_from_duplicates(d1, d2)["cv_dup"]
    assert got == pytest.approx(cv_real, abs=0.3)
    assert abs(got - cv_real * np.sqrt(2)) > 1.0, "parece faltarle el sqrt(2)"
