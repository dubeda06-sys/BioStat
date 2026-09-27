"""«Concordancia y confiabilidad» migrada a `Resultado` (paso 4, familia 8).

Oráculos: sklearn (cohen_kappa_score, con y sin pesos), statsmodels (EE e IC
del kappa, que ahora tiene también el ponderado) y pingouin (alfa de Cronbach
con el IC de Feldt, que el panel viejo no daba).
"""
import os
import re
from html import unescape

import numpy as np
import pandas as pd
import pingouin as pg
import pytest
from sklearn.metrics import cohen_kappa_score

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.resultado import render_html  # noqa: E402
from src.resultado.constructores import cronbach, kappa, kappa_ponderado  # noqa: E402

RNG = np.random.default_rng(61)
_VERDAD = RNG.integers(1, 4, 120)
HOJA = pd.DataFrame({"eval1": np.where(RNG.uniform(0, 1, 120) < 0.8, _VERDAD, RNG.integers(1, 4, 120)),
                     "eval2": np.where(RNG.uniform(0, 1, 120) < 0.7, _VERDAD, RNG.integers(1, 4, 120))})
_B = RNG.normal(0, 1, 80)
ESCALA = pd.DataFrame({f"i{j}": _B + RNG.normal(0, 1, 80) for j in range(1, 5)})


def _v(res, empieza):
    return next(v for v in res.valores if v.nombre.startswith(empieza))


def test_kappa_contra_sklearn():
    res = kappa(HOJA, "eval1", "eval2")
    assert _v(res, "Kappa").valor == pytest.approx(cohen_kappa_score(HOJA["eval1"], HOJA["eval2"]))


@pytest.mark.parametrize("pesos", ["linear", "quadratic"])
def test_kappa_ponderado_contra_sklearn_y_con_ic(pesos):
    res = kappa_ponderado(HOJA, "eval1", "eval2", {"pesos": pesos})
    esperado = cohen_kappa_score(HOJA["eval1"], HOJA["eval2"], weights=pesos)
    v = _v(res, "Kappa ponderado")
    assert v.valor == pytest.approx(esperado)
    assert v.ic is not None and v.ic[0] < esperado < v.ic[1]


def test_kappa_ponderado_avisa_el_orden_alfabetico():
    hoja = pd.DataFrame({"a": ["leve", "grave", "moderado"] * 10,
                         "b": ["leve", "grave", "grave"] * 10})
    paso = next(s for s in kappa_ponderado(hoja, "a", "b").supuestos if "orden" in s.pregunta)
    assert paso.respuesta == "Alfabético" and not paso.ok


def test_cronbach_contra_pingouin():
    res = cronbach(ESCALA, list(ESCALA.columns))
    alfa, ic = pg.cronbach_alpha(ESCALA)
    v = _v(res, "α de Cronbach")
    assert v.valor == pytest.approx(alfa)
    assert v.ic == pytest.approx(tuple(ic), abs=5e-4)


def test_cronbach_detecta_un_item_invertido():
    hoja = ESCALA.assign(i5=-ESCALA["i1"])
    paso = next(s for s in cronbach(hoja, list(hoja.columns)).supuestos if "sentido" in s.pregunta)
    assert "i5" in paso.respuesta and not paso.ok


@pytest.mark.parametrize("res", [kappa(HOJA, "eval1", "eval2"),
                                 kappa_ponderado(HOJA, "eval1", "eval2"),
                                 cronbach(ESCALA, list(ESCALA.columns))],
                         ids=["kappa", "ponderado", "cronbach"])
def test_informe(res):
    assert res.ok, res.error
    t = unescape(re.sub(r"<[^>]+>", " ", render_html(res)))
    assert "Qué se verificó" in t and "significativ" not in t.lower()


@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("analisis", ["Kappa", "Kappa ponderado", "Cronbach alfa"])
def test_el_panel(qt_app, analisis):
    from src.ui.analysis_panel import AnalysisPanel
    panel = AnalysisPanel()
    panel.set_data(HOJA.join(ESCALA))
    panel.combo_analysis.setCurrentText(analisis)
    panel.combo_col1.setCurrentText("eval1")
    panel.combo_col2.setCurrentText("eval2")
    panel.columnas_elegidas = list(ESCALA.columns) if analisis == "Cronbach alfa" else None
    panel._run()
    assert "Qué se verificó y qué se decidió" in panel.txt_results.toPlainText()
