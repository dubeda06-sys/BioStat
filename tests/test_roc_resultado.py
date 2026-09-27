"""«Curvas ROC» migradas a `Resultado` (paso 4, familia 10).

Oráculo: sklearn (roc_auc_score, roc_curve). El IC de DeLong ya tiene su test
en la auditoría; acá se verifica que llegue al informe, junto con el gráfico de
sensibilidad y especificidad según el umbral que antes vivía mal nombrado como
«Youden plot». Cambio a propósito: «Comparar 2 AUC» toma sus seis números del
diálogo.
"""
import os
import re
from html import unescape

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.resultado import render_html  # noqa: E402
from src.resultado.constructores import EJEMPLOS, comparar_auc, curva_roc  # noqa: E402

RNG = np.random.default_rng(81)
_Y = RNG.integers(0, 2, 150)
HOJA = pd.DataFrame({"marcador": RNG.normal(10 + 2 * _Y, 2), "enfermo": _Y})


def _v(res, empieza):
    return next(v for v in res.valores if v.nombre.startswith(empieza))


def test_auc_contra_sklearn():
    res = curva_roc(HOJA, "marcador", "enfermo")
    assert _v(res, "AUC").valor == pytest.approx(roc_auc_score(HOJA["enfermo"], HOJA["marcador"]))
    lo, hi = _v(res, "AUC").ic
    assert lo < _v(res, "AUC").valor < hi


def test_el_umbral_trae_sensibilidad_con_ic_y_el_grafico_de_youden():
    res = curva_roc(HOJA, "marcador", "enfermo")
    sens = _v(res, "Sensibilidad en el umbral")
    assert sens.ic is not None and sens.ic[0] <= sens.valor <= sens.ic[1]
    assert [f.titulo for f in res.figuras] == ["Curva ROC",
                                               "Sensibilidad y especificidad según el umbral"]


def test_curva_invertida_se_dice():
    res = curva_roc(HOJA.assign(marcador=-HOJA["marcador"]), "marcador", "enfermo")
    assert res.lectura.startswith("La curva sale invertida")


def test_etiqueta_no_binaria_se_rechaza():
    assert "tiene que ser 0/1" in curva_roc(HOJA, "enfermo", "marcador").error


def test_comparar_auc_desde_el_dialogo():
    res = comparar_auc(EJEMPLOS["comparar_auc"])
    assert _v(res, "Diferencia").valor == pytest.approx(0.08)
    assert "pacientes distintos" in next(s.pregunta for s in res.supuestos if not s.ok)


@pytest.mark.parametrize("res", [curva_roc(HOJA, "marcador", "enfermo"),
                                 comparar_auc(EJEMPLOS["comparar_auc"])], ids=["curva", "comparar"])
def test_informe(res):
    import matplotlib.pyplot as plt
    assert res.ok, res.error
    t = unescape(re.sub(r"<[^>]+>", " ", render_html(res)))
    assert "Qué se verificó" in t and "significativ" not in t.lower()
    for figura in res.figuras:
        plt.close(figura.dibujar())


@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("analisis", ["Curva ROC", "Comparar 2 AUC"])
def test_el_panel(qt_app, analisis):
    from src.ui.analysis_panel import AnalysisPanel
    panel = AnalysisPanel()
    panel.set_data(HOJA)
    panel.combo_analysis.setCurrentText(analisis)
    panel.combo_col1.setCurrentText("marcador")
    panel.combo_col3.setCurrentText("enfermo")
    panel._run()
    assert "Qué se verificó y qué se decidió" in panel.txt_results.toPlainText()
