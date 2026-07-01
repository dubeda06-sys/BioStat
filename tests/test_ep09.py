"""Tests de comparación de métodos CLSI EP09: Deming (λ + IC), sesgo en niveles,
datos y figuras de gráficos."""
import numpy as np
import pandas as pd
import pytest


def test_deming_devuelve_ic_y_lambda():
    from src.core.agreement import deming_regression
    rng = np.random.RandomState(0)
    x = rng.normal(100, 20, 60)
    y = 1.05 * x + 2.0 + rng.normal(0, 2, 60)
    r = deming_regression(x, y, lambda_ratio=1.0)
    assert r["lambda"] == 1.0
    assert "ci_slope" in r and "ci_intercept" in r
    assert r["ci_slope"][0] < r["slope"] < r["ci_slope"][1]
    assert r["slope"] == pytest.approx(1.05, abs=0.1)


def test_deming_lambda_cambia_pendiente():
    from src.core.agreement import deming_regression
    rng = np.random.RandomState(3)
    x = rng.normal(50, 10, 80)
    y = 0.9 * x + 5 + rng.normal(0, 3, 80)
    s1 = deming_regression(x, y, lambda_ratio=1.0)["slope"]
    s2 = deming_regression(x, y, lambda_ratio=4.0)["slope"]
    assert s1 != s2  # λ afecta la pendiente


def test_concordancia_ep09_completa():
    from src.analysis.omni_analyzer import concordance_analysis
    from src.analysis.omni_config import DEFAULT_CONFIG
    rng = np.random.RandomState(1)
    x = rng.normal(100, 20, 50)
    y = 1.02 * x + 1.5 + rng.normal(0, 2, 50)
    s1 = pd.Series(x, name="MetA")
    s2 = pd.Series(y, name="MetB")
    block = concordance_analysis("MetA", s1, "MetB", s2, DEFAULT_CONFIG)
    res = block["resultados"]
    # regresión con IC (Passing-Bablok o Deming)
    assert res["regresion"]["metodo"] in ("Passing-Bablok", "Deming")
    assert "ic_pendiente" in res["regresion"]
    # sesgo en niveles de decisión (P25/P50/P75 por defecto)
    assert len(res["sesgo_en_niveles"]) == 3
    assert all("sesgo_abs" in s for s in res["sesgo_en_niveles"])
    # datos para graficar
    assert "_plot" in res
    assert res["_plot"]["reg_slope"] is not None
    assert len(res["_plot"]["x"]) == 50
    # CCC presente
    assert "ccc" in res


def test_omni_plots_construye_figuras():
    from src.analysis.omni_plots import comparison_figures
    rng = np.random.RandomState(2)
    x = rng.normal(10, 2, 40)
    y = x + 0.5 + rng.normal(0, 0.3, 40)
    pdata = {
        "x": x, "y": y, "nombre_x": "MetA", "nombre_y": "MetB",
        "ba_tipo": "paramétrico", "sesgo": 0.5, "loa": (-0.1, 1.1),
        "reg_metodo": "Deming", "reg_slope": 1.0, "reg_intercept": 0.5,
    }
    figs = comparison_figures(pdata)
    nombres = [n for n, _ in figs]
    assert "Bland-Altman" in nombres
    assert "Regresión de comparación" in nombres
    import matplotlib.pyplot as plt
    for _, f in figs:
        plt.close(f)
