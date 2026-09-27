"""«Tamaño de muestra y poder» migrado a `Resultado` (paso 4, familia 13).

Oráculo: statsmodels (TTestPower, TTestIndPower) para las medias; las tablas
publicadas para proporciones (Fleiss) y correlación (Hulley). Cambia a
propósito: el tamaño muestral para una correlación pide la r esperada en el
diálogo, en vez de usar la r observada en la hoja (poder post hoc).
"""
import os
import re
from html import unescape

import numpy as np
import pandas as pd
import pytest
from statsmodels.stats.power import TTestIndPower, TTestPower

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.resultado import render_html  # noqa: E402
from src.resultado.constructores import (  # noqa: E402
    EJEMPLOS, poder_t, tam_correlacion, tam_dos_medias, tam_dos_proporciones, tam_una_media,
)


def _v(res, empieza):
    return next(v for v in res.valores if v.nombre.startswith(empieza))


def _texto(res):
    return unescape(re.sub(r"<[^>]+>", " ", render_html(res)))


@pytest.mark.parametrize("delta, sd, poder", [(5, 10, 0.8), (2, 4, 0.9), (20, 10, 0.8)])
def test_una_media_contra_statsmodels(delta, sd, poder):
    res = tam_una_media({"delta": delta, "sd": sd, "alpha": 0.05, "poder": poder})
    esperado = TTestPower().solve_power(effect_size=delta / sd, alpha=0.05, power=poder)
    assert _v(res, "n necesario").valor == int(np.ceil(esperado - 1e-9))


@pytest.mark.parametrize("ratio", [1.0, 2.0])
def test_dos_medias_es_el_n_mas_chico_que_alcanza(ratio):
    res = tam_dos_medias({"delta": 5, "sd": 10, "ratio": ratio, "alpha": 0.05, "poder": 0.8})
    n1, n2 = _v(res, "n grupo 1").valor, _v(res, "n grupo 2").valor
    assert n2 == int(np.ceil(n1 * ratio))
    alcanza = TTestIndPower().power(effect_size=0.5, nobs1=n1, ratio=n2 / n1, alpha=0.05)
    no_alcanza = TTestIndPower().power(effect_size=0.5, nobs1=n1 - 1,
                                       ratio=np.ceil((n1 - 1) * ratio) / (n1 - 1), alpha=0.05)
    assert alcanza >= 0.8 > no_alcanza


def test_dos_proporciones_como_fleiss():
    """p1 = 0,30 contra p2 = 0,50, α = 0,05, poder 80 %: 93 por grupo sin corrección."""
    res = tam_dos_proporciones(EJEMPLOS["tam_dos_proporciones"])
    assert _v(res, "n por grupo").valor == 93
    assert 0.80 <= res.crudo["tamano"]["power_real"] < 0.81


@pytest.mark.parametrize("r", [0.3, -0.3])
def test_correlacion_como_hulley(r):
    """r = 0,30, α = 0,05, poder 80 %: 85 sujetos (Hulley, tabla 6C)."""
    res = tam_correlacion({"r": r, "alpha": 0.05, "poder": 0.8})
    assert _v(res, "n necesario").valor == 85


def test_correlacion_imposible_se_rechaza():
    assert "entre -1 y 1" in tam_correlacion({"r": 1.2, "alpha": 0.05, "poder": 0.8}).error


@pytest.mark.parametrize("diseno", ["una", "dos"])
def test_poder_contra_statsmodels(diseno):
    res = poder_t({"n": 30, "delta": 5, "sd": 10, "alpha": 0.05, "diseno": diseno})
    ref = (TTestIndPower().power(effect_size=0.5, nobs1=30, alpha=0.05) if diseno == "dos" else
           TTestPower().power(effect_size=0.5, nobs=30, alpha=0.05))
    assert _v(res, "Poder").valor == pytest.approx(100 * ref, abs=1e-6)


def test_poder_bajo_dice_cuanto_hace_falta():
    res = poder_t({"n": 10, "delta": 5, "sd": 10, "alpha": 0.05, "diseno": "una"})
    n80 = _v(res, "n para 80 %").valor
    assert n80 == _v(tam_una_media({"delta": 5, "sd": 10, "alpha": 0.05, "poder": 0.8}),
                     "n necesario").valor
    assert "Para llegar al 80 %" in res.lectura


@pytest.mark.parametrize("nombre", sorted(EJEMPLOS.keys() & {
    "tam_una_media", "tam_dos_medias", "tam_dos_proporciones", "tam_correlacion", "poder_t"}))
def test_informe_y_curva(nombre):
    import matplotlib.pyplot as plt
    from src.resultado.constructores import CONSTRUCTORES
    res = CONSTRUCTORES[nombre](EJEMPLOS[nombre])
    assert res.ok, res.error
    t = _texto(res)
    assert "Qué se verificó" in t and "significativ" not in t.lower()
    fig = res.figuras[0].dibujar()
    assert fig.axes[0].lines
    plt.close(fig)


@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_el_panel_de_correlacion_no_lee_la_hoja(qt_app):
    """Cambió a propósito: antes calculaba el n con la r de las dos columnas elegidas."""
    from src.ui.analysis_panel import AnalysisPanel
    panel = AnalysisPanel()
    rng = np.random.default_rng(0)
    x = rng.normal(0, 1, 50)
    panel.set_data(pd.DataFrame({"A": x, "B": x + rng.normal(0, 0.1, 50)}))   # r ≈ 0,99
    panel.combo_analysis.setCurrentText("Tamaño muestral (correlacion)")
    panel.parametros = {"r": "0.3", "alpha": "0.05", "poder": "0.8"}
    panel._run()
    t = panel.txt_results.toPlainText()
    assert "n necesario" in t and "85" in t


@pytest.mark.parametrize("analisis", ["Tamano muestral (1 media)", "Tamano muestral (2 medias)",
                                      "Tamano muestral (2 proporciones)", "Poder estadistico"])
def test_el_panel_sin_dialogo_usa_el_ejemplo_y_lo_dice(qt_app, analisis):
    from src.ui.analysis_panel import AnalysisPanel
    panel = AnalysisPanel()
    panel.set_data(pd.DataFrame({"x": [1.0, 2.0]}))
    panel.combo_analysis.setCurrentText(analisis)
    panel._run()
    t = panel.txt_results.toPlainText()
    assert "Qué se verificó y qué se decidió" in t and "valores de ejemplo" in t
