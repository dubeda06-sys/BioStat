"""El IC del intercepto de Deming ponderado, y del sesgo en niveles bajos.

La auditoría del 26 sep dejó anotado que el jackknife del apéndice K1 cubría el
intercepto en 91-92 %. El diagnóstico (27 sep, 6 escenarios de CV constante,
1000 corridas cada uno): el intercepto casi no tiene sesgo y el EE jackknife
medio es correcto, pero lo deciden los pocos puntos bajos que cargan el peso
1/z², y un EE que sale de tan pocos puntos varía mucho de una muestra a otra.
t(N−2) es demasiado estrecho para esa variabilidad. Con t del n efectivo de
Kish, (Σw)²/Σw², la cobertura queda en 95-97 %. El bootstrap percentil y el
BCa no lo arreglaban.
"""
import numpy as np
import pytest
from scipy import stats

from src.core.agreement import (
    _deming_ponderado_fit, centro_ponderado, deming_ponderado,
)
from src.core.ep09 import DEMING_PONDERADO, sesgo_en_niveles


def _datos(rng, n=40, lo=1, hi=100, cv=0.10, a=2.0, b=1.05):
    t = rng.uniform(lo, hi, n)
    x = t * (1 + cv * rng.standard_normal(n))
    y = (a + b * t) * (1 + cv * rng.standard_normal(n))
    return x, y


def test_n_efectivo_es_el_de_kish_con_los_pesos_finales():
    x, y = _datos(np.random.default_rng(1))
    b, a = _deming_ponderado_fit(x, y, 1.0)
    xh = x + b * (y - a - b * x) / (1 + b * b)
    w = 1 / ((xh + a + b * xh) / 2) ** 2
    centro, n_ef = centro_ponderado(x, y, b, a, 1.0)
    assert n_ef == pytest.approx(w.sum() ** 2 / (w ** 2).sum())
    assert centro == pytest.approx(np.sum(w * x) / w.sum())
    assert n_ef < len(x) / 3  # los pesos se concentran abajo


def test_el_intercepto_va_con_t_de_n_efectivo_y_la_pendiente_con_t_n_menos_2():
    x, y = _datos(np.random.default_rng(2))
    r = deming_ponderado(x, y)
    n = len(x)
    js, ji = [], []
    for k in range(n):
        m = np.ones(n, bool)
        m[k] = False
        f = _deming_ponderado_fit(x[m], y[m], 1.0)
        js.append(f[0])
        ji.append(f[1])
    ee_b = np.sqrt((n - 1) / n * np.sum((np.array(js) - np.mean(js)) ** 2))
    ee_a = np.sqrt((n - 1) / n * np.sum((np.array(ji) - np.mean(ji)) ** 2))
    assert r["gl_intercepto"] == pytest.approx(min(n - 2, r["n_efectivo"]))
    assert r["ci_intercept"][1] - r["intercept"] == pytest.approx(
        stats.t.ppf(0.975, r["gl_intercepto"]) * ee_a)
    assert r["ci_slope"][1] - r["slope"] == pytest.approx(stats.t.ppf(0.975, n - 2) * ee_b)


def test_la_cobertura_del_intercepto_sube_al_nominal():
    """El escenario peor de la simulación: 40 muestras entre 1 y 100, CV 10 %."""
    rng = np.random.default_rng(3)
    a_real, n = 2.0, 40
    antes = ahora = corridas = 0
    for _ in range(250):
        x, y = _datos(rng, n=n, a=a_real)
        r = deming_ponderado(x, y)
        if "error" in r:
            continue
        corridas += 1
        lo, hi = r["ci_intercept"]
        ahora += lo <= a_real <= hi
        # el mismo EE con t(N−2), como estaba antes
        ee = (hi - r["intercept"]) / stats.t.ppf(0.975, r["gl_intercepto"])
        t2 = stats.t.ppf(0.975, n - 2)
        antes += r["intercept"] - t2 * ee <= a_real <= r["intercept"] + t2 * ee
    assert antes / corridas < 0.93
    assert ahora / corridas >= 0.94


def test_sesgo_en_niveles_bajo_el_centro_usa_n_efectivo():
    x, y = _datos(np.random.default_rng(4), lo=10, hi=200, cv=0.05)
    b, a = _deming_ponderado_fit(x, y, 1.0)
    centro, n_ef = centro_ponderado(x, y, b, a, 1.0)
    niveles = [centro / 2, centro * 3]
    r = sesgo_en_niveles(x, y, DEMING_PONDERADO, niveles)
    assert "n efectivo" in r["metodo_ic"]
    # misma EE jackknife, distinto t: el nivel bajo se abre más por gl
    n = len(x)
    dej = []
    for k in range(n):
        m = np.ones(n, bool)
        m[k] = False
        f = _deming_ponderado_fit(x[m], y[m], 1.0)
        dej.append(f[1] + (f[0] - 1) * np.asarray(niveles))
    dej = np.asarray(dej)
    ee = np.sqrt((n - 1) / n * np.sum((dej - dej.mean(0)) ** 2, 0))
    semi = np.asarray(r["ic_sup"]) - np.asarray(r["sesgo"])
    assert semi[0] == pytest.approx(stats.t.ppf(0.975, min(n - 2, n_ef)) * ee[0])
    assert semi[1] == pytest.approx(stats.t.ppf(0.975, n - 2) * ee[1])


def test_deming_sin_ponderar_no_cambia():
    x, y = _datos(np.random.default_rng(5), lo=10, hi=200, cv=0.05)
    r = sesgo_en_niveles(x, y, "deming", [20.0])
    assert r["metodo_ic"] == "jackknife, t(N−2) (EP09c, apéndice K)"
