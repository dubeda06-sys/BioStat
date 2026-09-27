"""«Machine learning» migrado a `Resultado` (paso 4, familia 15).

Oráculo: scikit-learn (`cross_val_predict` con la misma partición). Cambian a
propósito: el desempeño es fuera de muestra y se compara con no tener modelo,
la importancia es por permutación y el gráfico observado contra predicho usa
predicciones fuera de muestra.
"""
import os
import re
from html import unescape

import numpy as np
import pandas as pd
import pytest
from sklearn.base import clone
from sklearn.model_selection import KFold, StratifiedKFold, cross_val_predict

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.core.random_forest import RandomForestClassifier, RandomForestRegressor  # noqa: E402
from src.resultado import render_html  # noqa: E402
from src.resultado.constructores import rf_clasificacion, rf_regresion  # noqa: E402


def _texto(res):
    return unescape(re.sub(r"<[^>]+>", " ", render_html(res)))


def _paso(res, empieza):
    return next(s for s in res.supuestos if s.pregunta.startswith(empieza))


def _hoja(n=200, semilla=0, senal=True, rara=False):
    rng = np.random.default_rng(semilla)
    x1, x2, x3 = rng.normal(0, 1, n), rng.normal(0, 1, n), rng.normal(0, 1, n)
    if senal:
        clase = (x1 + rng.normal(0, 0.7, n) > 0).astype(float)
    else:
        clase = (rng.random(n) < (0.2 if rara else 0.5)).astype(float)
    return pd.DataFrame({"clase": clase, "y": 2 * x1 + rng.normal(0, 1, n) if senal
                         else rng.normal(0, 1, n), "x1": x1, "x2": x2, "x3": x3})


def test_clasificacion_fuera_de_muestra_como_sklearn():
    hoja = _hoja()
    res = rf_clasificacion(hoja, "clase", ["x1", "x2", "x3"])
    X, y = hoja[["x1", "x2", "x3"]].values, hoja["clase"].values
    modelo = RandomForestClassifier(n_trees=100, max_depth=8, random_state=42)._model
    ref = cross_val_predict(clone(modelo), X, y, method="predict_proba",
                            cv=StratifiedKFold(5, shuffle=True, random_state=42))
    assert np.allclose(res.crudo["evaluacion"]["oof"], ref)


def test_con_senal_supera_la_linea_de_base_y_la_importancia_la_encuentra():
    res = rf_clasificacion(_hoja(), "clase", ["x1", "x2", "x3"])
    assert _paso(res, "¿Supera").ok
    imp = dict(zip(res.crudo["predictoras"], res.crudo["evaluacion"]["importancia"]))
    assert imp["x1"] > 5 * max(imp["x2"], imp["x3"], 0.01)
    auc = next(v for v in res.valores if v.nombre.startswith("AUC"))
    assert auc.ic[0] < auc.valor < auc.ic[1]


def test_ruido_con_clase_rara_no_le_gana_a_adivinar():
    """Cambió a propósito: la exactitud se compara con la clase más frecuente."""
    res = rf_clasificacion(_hoja(senal=False, rara=True), "clase", ["x1", "x2", "x3"])
    assert not _paso(res, "¿Supera").ok
    entreno = next(v for v in res.valores if v.nombre.startswith("Exactitud sobre el entre"))
    assert entreno.valor > 0.9          # memoriza: por eso no se usa


def test_la_importancia_por_permutacion_no_premia_al_ruido_continuo():
    """La de impureza sí: el ruido continuo aparece importante frente a una binaria útil."""
    rng = np.random.default_rng(4)
    n = 300
    b = rng.integers(0, 2, n).astype(float)
    hoja = pd.DataFrame({"clase": ((b + rng.normal(0, 0.6, n)) > 0.5) * 1.0, "b": b,
                         "ruido": rng.normal(0, 1, n)})
    res = rf_clasificacion(hoja, "clase", ["b", "ruido"])
    imp = dict(zip(["b", "ruido"], res.crudo["evaluacion"]["importancia"]))
    assert imp["b"] > 0.1 and abs(imp["ruido"]) < 0.03


def test_una_clase_continua_se_rechaza():
    assert "parece una medición" in rf_clasificacion(_hoja(), "y", ["x1"]).error


def test_regresion_fuera_de_muestra_como_sklearn():
    hoja = _hoja()
    res = rf_regresion(hoja, "y", ["x1", "x2"])
    X, y = hoja[["x1", "x2"]].values, hoja["y"].values
    modelo = RandomForestRegressor(n_trees=100, max_depth=8, random_state=42)._model
    ref = cross_val_predict(clone(modelo), X, y, cv=KFold(5, shuffle=True, random_state=42))
    assert np.allclose(res.crudo["evaluacion"]["oof"], ref)
    assert res.crudo["r2_cv"] > 0.5 and _paso(res, "¿Predice").ok


def test_regresion_con_ruido_no_predice_mejor_que_la_media():
    res = rf_regresion(_hoja(senal=False), "y", ["x1", "x2", "x3"])
    assert res.crudo["r2_cv"] < 0.05


@pytest.mark.parametrize("res", [rf_clasificacion(_hoja(), "clase", ["x1", "x2"]),
                                 rf_regresion(_hoja(), "y", ["x1", "x2"])],
                         ids=["clasificacion", "regresion"])
def test_informe_y_figuras(res):
    import matplotlib.pyplot as plt
    assert res.ok, res.error
    t = _texto(res)
    assert "Qué se verificó" in t and "significativ" not in t.lower()
    for f in res.figuras:
        plt.close(f.dibujar())


@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("analisis, respuesta", [("Random Forest (clasificacion)", "clase"),
                                                 ("Random Forest (regresion)", "y")])
def test_el_panel(qt_app, analisis, respuesta):
    from src.ui.analysis_panel import AnalysisPanel
    panel = AnalysisPanel()
    panel.set_data(_hoja())
    panel.combo_analysis.setCurrentText(analisis)
    panel.combo_col1.setCurrentText(respuesta)
    panel.columnas_elegidas = ["x1", "x2"]
    panel._run()
    assert "Qué se verificó y qué se decidió" in panel.txt_results.toPlainText()
