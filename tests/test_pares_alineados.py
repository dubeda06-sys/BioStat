"""Un análisis pareado compara cada fila consigo misma, aunque haya celdas vacías.

El panel manual hacía, en 22 lugares:

    d1, d2 = data[c1].dropna(), data[c2].dropna()
    n = min(len(d1), len(d2))
    f(d1[:n], d2[:n])

Cada columna descartaba SUS faltantes y después se cortaban al mismo largo. Con
una sola celda vacía, desde esa fila en adelante cada valor se comparaba con el
del paciente siguiente. Un Bland-Altman de 20 pares con un NaN daba límites de
±90 donde corresponden ±2,4, sin ningún aviso.

La propiedad que se fija acá: correr el análisis sobre la hoja con huecos tiene
que dar **exactamente** lo mismo que correrlo sobre las filas completas. Se
compara el informe entero, no un número elegido: si el emparejamiento falla en
cualquier cosa que el informe muestre, el test lo ve.
"""
import os
import re

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def _texto(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def _panel(df):
    from src.ui.analysis_panel import AnalysisPanel
    p = AnalysisPanel()
    p.set_data(df)
    return p


def _hoja_general():
    """Dos métodos, etiqueta 0/1, tiempo/evento y error estándar.

    Los huecos caen en filas DISTINTAS de cada columna: es el caso que desalinea.
    """
    rng = np.random.default_rng(7)
    n = 40
    a = rng.uniform(50, 150, n)
    df = pd.DataFrame({
        "A": a,
        "B": a + rng.normal(0, 1, n),
        "L": (a + rng.normal(0, 25, n) > 100).astype(float),
        "T": rng.uniform(1, 60, n).round(1),
        "E": rng.integers(0, 2, n).astype(float),
        "SE": rng.uniform(0.5, 2, n),
    })
    df.loc[0, "A"] = np.nan
    df.loc[5, "B"] = np.nan
    df.loc[9, "L"] = np.nan
    df.loc[3, "T"] = np.nan
    df.loc[12, "E"] = np.nan
    df.loc[15, "SE"] = np.nan
    return df


def _hoja_categorica():
    rng = np.random.default_rng(3)
    x = rng.integers(1, 4, 50).astype(float)
    y = np.where(rng.random(50) < 0.7, x, rng.integers(1, 4, 50)).astype(float)
    df = pd.DataFrame({"X": x, "Y": y})
    df.loc[0, "X"] = np.nan
    df.loc[4, "Y"] = np.nan
    return df


def _hoja_tres_condiciones():
    rng = np.random.default_rng(4)
    base = rng.normal(100, 10, 30)
    df = pd.DataFrame({"C1": base, "C2": base + 2 + rng.normal(0, 1, 30),
                       "C3": base + 4 + rng.normal(0, 1, 30)})
    df.loc[0, "C1"] = np.nan
    df.loc[6, "C3"] = np.nan
    return df


def _hoja_edad():
    rng = np.random.default_rng(8)
    edad = rng.uniform(18, 90, 200).round()
    valor = 50 + 0.3 * edad + rng.normal(0, 5, 200)
    df = pd.DataFrame({"Edad": edad, "Valor": valor})
    df.loc[0, "Edad"] = np.nan
    df.loc[10, "Valor"] = np.nan
    return df


def _hoja_cox():
    rng = np.random.default_rng(9)
    n = 60
    z = rng.normal(0, 1, n)
    df = pd.DataFrame({"T": rng.exponential(10 * np.exp(-0.5 * z)).round(2),
                       "E": (rng.random(n) < 0.7).astype(float),
                       "X": rng.normal(0, 1, n), "Z": z})
    df.loc[0, "T"] = np.nan
    df.loc[7, "Z"] = np.nan
    return df


# (nombre, hoja, columnas que el análisis empareja, llamada)
CASOS = [
    ("t pareado", _hoja_general, ["A", "B"], lambda p: p._t_paired("A", "B", 0.05)),
    ("curva ROC", _hoja_general, ["A", "L"], lambda p: p._roc("A", "L")),
    ("Bland-Altman", _hoja_general, ["A", "B"], lambda p: p._bland("A", "B")),
    ("Passing-Bablok", _hoja_general, ["A", "B"], lambda p: p._passing("A", "B")),
    ("Kaplan-Meier", _hoja_general, ["T", "E"], lambda p: p._kaplan_meier("T", "E")),
    ("meta-análisis", _hoja_general, ["A", "SE"], lambda p: p._meta("A", "SE")),
    ("bootstrap de correlación", _hoja_general, ["A", "B"], lambda p: p._boot_corr("A", "B")),
    ("Wilcoxon", _hoja_general, ["A", "B"], lambda p: p._wilcoxon("A", "B")),
    ("ICC", _hoja_general, ["A", "B"], lambda p: p._icc("A", "B")),
    ("regresión lineal", _hoja_general, ["A", "B"], lambda p: p._reg_lineal("A", "B")),
    ("sign test", _hoja_general, ["A", "B"], lambda p: p._run_core("sign_test", "A", "B")),
    ("Deming", _hoja_general, ["A", "B"], lambda p: p._run_core("deming", "A", "B")),
    ("CV de duplicados", _hoja_general, ["A", "B"], lambda p: p._run_core("cv_duplicates", "A", "B")),
    ("bootstrap de regresión", _hoja_general, ["A", "B"],
     lambda p: p._run_core("bootstrap_regression", "A", "B")),
    ("tamaño muestral por correlación", _hoja_general, ["A", "B"],
     lambda p: p._run_core("sample_size_corr", "A", "B")),
    ("probit", _hoja_general, ["A", "L"], lambda p: p._run_probit("A", "L")),
    ("Youden", _hoja_general, ["A", "L"], lambda p: p._run_youden("A", "L")),
    ("chi-cuadrado", _hoja_categorica, ["X", "Y"], lambda p: p._chi2()),
    ("kappa ponderado", _hoja_categorica, ["X", "Y"], lambda p: p._run_core("weighted_kappa")),
    ("Friedman", _hoja_tres_condiciones, ["C1", "C2", "C3"], lambda p: p._friedman()),
    ("intervalos por edad", _hoja_edad, ["Edad", "Valor"], lambda p: p._run_core("age_related")),
    ("Cox", _hoja_cox, ["T", "E", "Z"], lambda p: p._run_cox("T", "E")),
]


@pytest.mark.parametrize("nombre, hoja, columnas, correr", CASOS, ids=[c[0] for c in CASOS])
def test_con_huecos_da_lo_mismo_que_con_las_filas_completas(qt_app, nombre, hoja, columnas, correr):
    df = hoja()
    completas = df.dropna(subset=columnas).reset_index(drop=True)
    assert len(completas) < len(df), "la hoja de prueba tiene que traer huecos"

    con_huecos = _texto(correr(_panel(df)))
    sin_huecos = _texto(correr(_panel(completas)))

    assert "Error" not in sin_huecos, f"{nombre}: la referencia misma falló: {sin_huecos[:200]}"
    assert con_huecos == sin_huecos


def test_bland_altman_con_un_hueco_no_infla_los_limites(qt_app):
    """El caso que destapó el defecto, con sus números."""
    from src.core.bland_altman import bland_altman_analysis

    rng = np.random.default_rng(1)
    ref = rng.uniform(50, 150, 20)
    df = pd.DataFrame({"A": ref, "B": ref + rng.normal(0, 1, 20)})
    df.loc[0, "A"] = np.nan

    panel = _panel(df)
    texto = _texto(panel._bland("A", "B"))
    esperado = bland_altman_analysis(df.dropna()["A"].values, df.dropna()["B"].values)

    assert f"{esperado['sd_difference']:.4f}" in texto
    assert esperado["sd_difference"] < 2  # desalineado daba 46


def test_el_informe_avisa_cuantas_filas_quedaron_afuera(qt_app):
    df = _hoja_general()
    panel = _panel(df)
    panel.combo_analysis.setCurrentText("Bland-Altman")
    panel.combo_col1.setCurrentText("A")
    panel.combo_col2.setCurrentText("B")
    panel._run()

    texto = _texto(panel.txt_results.toHtml())
    # A vacía en la fila 0, B en la 5: dos filas con un solo dato.
    assert "2 filas" in texto and "incompletas" in texto


def test_sin_huecos_no_hay_aviso(qt_app):
    df = _hoja_general().dropna().reset_index(drop=True)
    panel = _panel(df)
    panel.combo_analysis.setCurrentText("Bland-Altman")
    panel.combo_col1.setCurrentText("A")
    panel.combo_col2.setCurrentText("B")
    panel._run()

    assert "incompletas" not in _texto(panel.txt_results.toHtml())


def test_las_filas_vacias_del_final_no_cuentan_como_descartes(qt_app):
    """Una planilla trae filas totalmente vacías al final. No son pares rotos:
    avisar por ellas enseñaría a ignorar el aviso."""
    df = _hoja_general().dropna().reset_index(drop=True)
    vacias = pd.DataFrame(np.nan, index=range(5), columns=df.columns)
    df = pd.concat([df, vacias], ignore_index=True)
    panel = _panel(df)
    panel.combo_analysis.setCurrentText("Bland-Altman")
    panel.combo_col1.setCurrentText("A")
    panel.combo_col2.setCurrentText("B")
    panel._run()

    assert "incompletas" not in _texto(panel.txt_results.toHtml())
