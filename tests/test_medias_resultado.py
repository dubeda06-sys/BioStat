"""«Comparación de medias» migrada a `Resultado` (paso 4, familia 4).

Oráculo: scipy (ttest_1samp, ttest_rel, ttest_ind de Welch, sus IC y
ttest_ind_from_stats). Cambios a propósito, cada uno con su test: la t de una
muestra compara contra el valor que elige el usuario (antes, siempre 0), y la
calculadora de medias resumidas toma sus seis números del diálogo (antes, de
seis celdas de la primera columna).
"""
import os
import re
from html import unescape

import numpy as np
import pandas as pd
import pytest
from scipy import stats

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.resultado import render_html  # noqa: E402
from src.resultado.constructores import (  # noqa: E402
    EJEMPLOS, comparar_medias, f_varianzas, t_independiente, t_pareada, t_una_muestra,
)

RNG = np.random.default_rng(12)
_BASE = RNG.normal(100, 10, 40)
HOJA = pd.DataFrame({"antes": _BASE, "despues": _BASE + 3 + RNG.normal(0, 4, 40),
                     "grupo_a": RNG.normal(50, 5, 40)})
HOJA["grupo_b"] = pd.Series(RNG.normal(54, 9, 25))     # otro n: grupos independientes


def _v(res, empieza):
    return next(v for v in res.valores if v.nombre.startswith(empieza))


def _paso(res, texto):
    return next(s for s in res.supuestos if texto in s.pregunta)


def _texto(res):
    return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", render_html(res)))).strip()


def test_t_una_muestra_contra_scipy_y_con_el_valor_elegido():
    """Cambió a propósito: antes se comparaba siempre contra 0."""
    res = t_una_muestra(HOJA, "antes", {"mu": 98})
    ref = stats.ttest_1samp(HOJA["antes"], 98)
    assert _v(res, "t").valor == pytest.approx(ref.statistic)
    ic = ref.confidence_interval()
    assert _v(res, "Media").ic == pytest.approx((ic.low, ic.high))
    assert _v(res, "Diferencia").ic == pytest.approx((ic.low - 98, ic.high - 98))
    assert "98" in res.titulo


def test_t_una_muestra_contra_cero_lo_recuerda():
    res = t_una_muestra(HOJA, "antes")
    assert _paso(res, "Contra qué valor").respuesta == "0"


def test_t_pareada_contra_scipy():
    res = t_pareada(HOJA, "despues", "antes")
    ref = stats.ttest_rel(HOJA["despues"], HOJA["antes"])
    assert _v(res, "t").valor == pytest.approx(ref.statistic)
    ic = ref.confidence_interval()
    assert _v(res, "Diferencia media").ic == pytest.approx((ic.low, ic.high))
    assert _paso(res, "difieren en promedio").respuesta == "Se detectó diferencia"
    assert res.lectura.startswith("En promedio, despues supera a antes")


def test_t_pareada_con_alfa_elegido():
    res = t_pareada(HOJA, "despues", "antes", {"alpha": 1e-12})
    assert _paso(res, "difieren en promedio").respuesta == "No se detectó diferencia"


def test_t_pareada_mantiene_los_pares():
    hoja = HOJA.copy()
    hoja.loc[3, "antes"] = np.nan
    res = t_pareada(hoja, "despues", "antes")
    assert res.entrada.n == 39 and res.entrada.descartadas == 1


def test_t_independiente_es_welch():
    res = t_independiente(HOJA, "grupo_a", "grupo_b")
    b = HOJA["grupo_b"].dropna()
    ref = stats.ttest_ind(HOJA["grupo_a"], b, equal_var=False)
    assert _v(res, "t").valor == pytest.approx(ref.statistic)
    ic = ref.confidence_interval()
    assert _v(res, "Diferencia de medias").ic == pytest.approx((ic.low, ic.high))
    assert _paso(res, "varianzas sean iguales").respuesta == "No"
    assert res.entrada.n == 65


def test_la_normalidad_sugiere_la_no_parametrica():
    hoja = pd.DataFrame({"a": np.exp(RNG.normal(0, 1.2, 15)), "b": RNG.normal(1, 1, 15)})
    paso = _paso(t_independiente(hoja, "a", "b"), "Los datos de a")
    assert paso.respuesta == "No" and "Mann-Whitney" in paso.consecuencia


def test_comparar_medias_contra_scipy():
    """Cambió a propósito: los seis números vienen del diálogo, no de la hoja."""
    e = EJEMPLOS["comparar_medias"]
    res = comparar_medias(e)
    ref = stats.ttest_ind_from_stats(e["m1"], e["de1"], e["n1"], e["m2"], e["de2"], e["n2"],
                                     equal_var=False)
    assert _v(res, "t").valor == pytest.approx(ref.statistic)
    assert float(_v(res, "p").valor) == pytest.approx(ref.pvalue, abs=5e-5)
    assert _paso(res, "normalidad").respuesta == "No"


def test_comparar_medias_sin_un_dato():
    res = comparar_medias({"m1": 1, "de1": 1, "n1": 5, "m2": 2, "de2": 1})
    assert not res.ok and "n2" in res.error


def test_f_varianzas_y_brown_forsythe():
    res = f_varianzas(HOJA, "grupo_a", "grupo_b")
    a, b = HOJA["grupo_a"], HOJA["grupo_b"].dropna()
    va, vb = a.var(ddof=1), b.var(ddof=1)
    assert _v(res, "F").valor == pytest.approx(max(va, vb) / min(va, vb))
    bf = stats.levene(a, b, center="median")
    assert float(_v(res, "p (Brown-Forsythe)").valor) == pytest.approx(bf.pvalue, abs=5e-5)


@pytest.mark.parametrize("res", [
    t_una_muestra(HOJA, "antes", {"mu": 98}), t_pareada(HOJA, "despues", "antes"),
    t_independiente(HOJA, "grupo_a", "grupo_b"), comparar_medias(EJEMPLOS["comparar_medias"]),
    f_varianzas(HOJA, "grupo_a", "grupo_b")],
    ids=["una", "pareada", "independiente", "resumidas", "F"])
def test_informe_y_figuras(res):
    import matplotlib.pyplot as plt
    assert res.ok, res.error
    t = _texto(res)
    assert "Qué se verificó" in t and "significativ" not in t.lower()
    for figura in res.figuras:
        fig = figura.dibujar()
        assert fig.axes
        plt.close(fig)


@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _panel(analisis, c1="antes", c2="despues", parametros=None):
    from src.ui.analysis_panel import AnalysisPanel
    panel = AnalysisPanel()
    panel.set_data(HOJA)
    panel.combo_analysis.setCurrentText(analisis)
    panel.combo_col1.setCurrentText(c1)
    panel.combo_col2.setCurrentText(c2)
    panel.parametros = parametros or {}
    panel._run()
    return panel.txt_results.toPlainText()


@pytest.mark.parametrize("analisis", ["t-test pareado", "t-test independiente",
                                      "F-test (varianzas)", "t-test 1 muestra",
                                      "Comparar 2 medias"])
def test_el_panel(qt_app, analisis):
    assert "Qué se verificó y qué se decidió" in _panel(analisis)


def test_el_panel_usa_el_valor_de_referencia(qt_app):
    assert "contra 98" in _panel("t-test 1 muestra", parametros={"mu": "98"})


def test_el_panel_usa_los_seis_numeros(qt_app):
    texto = _panel("Comparar 2 medias", parametros={"m1": "10", "de1": "2", "n1": "20",
                                                    "m2": "12", "de2": "2", "n2": "20"})
    assert "media 10" in texto and "valores de ejemplo" not in texto


def test_el_dialogo_pide_los_seis_numeros(qt_app):
    from src.ui.dialogs import DialogoAnalisis
    d = DialogoAnalisis("Comparar 2 medias", ["x"])
    assert set(d.inputs_parametro) == {"m1", "de1", "n1", "m2", "de2", "n2"}
    d = DialogoAnalisis("t-test 1 muestra", ["x"])
    assert set(d.inputs_parametro) == {"mu"}
