"""«Bootstrap» migrado a `Resultado` (paso 4, familia 14).

Oráculo: `scipy.stats.bootstrap` con BCa y muchos remuestreos; las diferencias
son el error Monte Carlo de dos generadores distintos. Cambian a propósito: el
IC es BCa por defecto (antes, siempre percentil), la mediana trae su IC exacto
por rangos y la correlación puede ser de Spearman.
"""
import os
import re
import warnings
from html import unescape

import numpy as np
import pandas as pd
import pytest
from scipy import stats

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.core import bootstrap as core  # noqa: E402
from src.resultado import render_html  # noqa: E402
from src.resultado.constructores import (  # noqa: E402
    boot_correlacion, boot_diferencia, boot_media, boot_mediana, boot_regresion,
)

RNG = np.random.default_rng(3)
X = RNG.lognormal(2, 0.8, 40)
Y = 0.5 * X + RNG.normal(0, 3, 40)
Z = RNG.lognormal(2.3, 0.8, 35)
HOJA = pd.DataFrame({"x": X, "y": Y, "z": np.r_[Z, [np.nan] * 5]})


def _v(res, empieza):
    return next(v for v in res.valores if v.nombre.startswith(empieza))


def _texto(res):
    return unescape(re.sub(r"<[^>]+>", " ", render_html(res)))


def _scipy(datos, f, paired=False, vectorized=True):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return stats.bootstrap(datos, f, n_resamples=40000, method="BCa", paired=paired,
                               vectorized=vectorized, random_state=1).confidence_interval


def _cerca(got, ref, tol=0.05):
    """Cada límite a menos del 5 % del ancho del IC: el error Monte Carlo."""
    ancho = ref.high - ref.low
    return abs(got[0] - ref.low) < tol * ancho and abs(got[1] - ref.high) < tol * ancho


def test_media_bca_como_scipy():
    r = core.bootstrap_mean(X, 40000)
    assert r["metodo_ic"] == "BCa"
    assert _cerca((r["ci_lower"], r["ci_upper"]), _scipy((X,), np.mean))


def test_mediana_bca_como_scipy():
    r = core.bootstrap_median(X, 40000)
    assert _cerca((r["ci_lower"], r["ci_upper"]), _scipy((X,), np.median))


def test_diferencia_bca_como_scipy():
    r = core.bootstrap_difference(X, Z, 40000)
    ref = _scipy((X, Z), lambda a, b, axis=-1: a.mean(axis) - b.mean(axis))
    assert _cerca((r["ci_lower"], r["ci_upper"]), ref)


def test_correlacion_bca_como_scipy():
    r = core.bootstrap_correlation(X, Y, 40000)
    ref = _scipy((X, Y), lambda a, b: stats.pearsonr(a, b)[0], paired=True, vectorized=False)
    assert _cerca((r["ci_lower"], r["ci_upper"]), ref)


def test_pendiente_bca_como_scipy():
    r = core.bootstrap_regression(X, Y, 40000)
    ref = _scipy((X, Y), lambda a, b: np.polyfit(a, b, 1)[0], paired=True, vectorized=False)
    assert _cerca(r["ci_slope"], ref)


def test_percentil_a_pedido():
    res = boot_media(HOJA, "x", {"metodo_ic": "percentil"})
    dist = res.crudo["bootstrap"]["bootstrap_distribution"]
    assert _v(res, "Media").ic == pytest.approx(tuple(np.percentile(dist, [2.5, 97.5])))
    assert "percentil" in _v(res, "Media").nota


def test_la_mediana_trae_el_ic_exacto_por_rangos():
    """n = 40: rangos 14 y 27 (Campbell y Gardner 1988), cobertura ≥ 95 %."""
    ex = boot_mediana(HOJA, "x").crudo["bootstrap"]["exacto"]
    xs = np.sort(X)
    assert ex["rangos"] == (14, 27) and ex["cobertura"] >= 0.95
    assert (ex["inferior"], ex["superior"]) == (xs[13], xs[26])


def test_mediana_con_muchos_empates_lo_dice():
    hoja = pd.DataFrame({"x": np.random.default_rng(1).integers(1, 5, 60).astype(float)})
    paso = next(s for s in boot_mediana(hoja, "x").supuestos if "repetidos" in s.pregunta)
    assert not paso.ok and "IC exacto" in paso.consecuencia


def test_spearman_a_pedido():
    res = boot_correlacion(HOJA, "x", "y", {"coeficiente": "spearman"})
    assert _v(res, "ρ de Spearman").valor == pytest.approx(stats.spearmanr(X, Y)[0])


def test_la_diferencia_usa_cada_columna_entera():
    """Grupos independientes: z tiene 35 datos y x 40, no se recortan a pares."""
    res = boot_diferencia(HOJA, "x", "z")
    assert _v(res, "n — x").valor == 40 and _v(res, "n — z").valor == 35
    assert _v(res, "Diferencia").valor == pytest.approx(X.mean() - Z.mean())


def test_correlacion_con_n_chico_descarta_remuestreos_constantes():
    """Auditoría M5, ahora con BCa: los remuestreos sin r se cuentan y se avisan."""
    x = np.arange(5, dtype=float)
    hoja = pd.DataFrame({"a": x, "b": x + np.array([0.3, -0.2, 0.1, 0.4, -0.3])})
    res = boot_correlacion(hoja, "a", "b")
    assert res.ok and any("constante" in a for a in res.advertencias)
    assert np.all(np.isfinite(_v(res, "r de Pearson").ic))


@pytest.mark.parametrize("res", [
    boot_media(HOJA, "x"), boot_mediana(HOJA, "x"), boot_diferencia(HOJA, "x", "z"),
    boot_correlacion(HOJA, "x", "y"), boot_regresion(HOJA, "x", "y")],
    ids=["media", "mediana", "diferencia", "correlacion", "regresion"])
def test_informe_y_figura(res):
    import matplotlib.pyplot as plt
    assert res.ok, res.error
    t = _texto(res)
    assert "Qué se verificó" in t and "significativ" not in t.lower()
    plt.close(res.figuras[0].dibujar())


@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("analisis", ["Bootstrap (media)", "Bootstrap (mediana)",
                                      "Bootstrap (diferencia)", "Bootstrap (correlacion)",
                                      "Bootstrap (regresion)"])
def test_el_panel(qt_app, analisis):
    from src.ui.analysis_panel import AnalysisPanel
    panel = AnalysisPanel()
    panel.set_data(HOJA)
    panel.combo_analysis.setCurrentText(analisis)
    panel.combo_col1.setCurrentText("x")
    panel.combo_col2.setCurrentText("y")
    panel._run()
    assert "Qué se verificó y qué se decidió" in panel.txt_results.toPlainText()
