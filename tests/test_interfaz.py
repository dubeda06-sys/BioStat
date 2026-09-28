"""Defectos de la interfaz encontrados mirando capturas reales (27 sep).

Cada test es uno que se veía en pantalla, no una preferencia de estilo.
"""
import os

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def _hoja():
    rng = np.random.default_rng(1)
    t = rng.uniform(60, 300, 40)
    return pd.DataFrame({"Glucosa_A": t, "Glucosa_B": t * 1.03 + rng.normal(0, 3, 40),
                         "Grupo": rng.choice(["Control", "Diabetes"], 40),
                         "Edad": rng.integers(18, 90, 40).astype(float)})


# ---------------- las selecciones no se pierden al cambiar de pestaña ----------------

def test_el_panel_analisis_conserva_las_variables_al_volver(qt_app):
    from src.ui.analysis_panel import AnalysisPanel
    p = AnalysisPanel()
    p.set_data(_hoja())
    assert p.combo_col2.currentText() == "Glucosa_B"   # no arranca igual a la 1
    p.combo_col1.setCurrentText("Edad")
    p.combo_col2.setCurrentText("Glucosa_A")
    p.combo_col3.setCurrentText("Grupo")
    p.set_data(_hoja())                                # volver a la pestaña
    assert (p.combo_col1.currentText(), p.combo_col2.currentText(),
            p.combo_col3.currentText()) == ("Edad", "Glucosa_A", "Grupo")


def test_una_columna_que_ya_no_existe_vuelve_al_defecto(qt_app):
    from src.ui.analysis_panel import AnalysisPanel
    p = AnalysisPanel()
    p.set_data(_hoja())
    p.combo_col2.setCurrentText("Edad")
    p.set_data(_hoja().rename(columns={"Edad": "Años"}))
    assert p.combo_col2.currentText() == "Glucosa_B"


def test_el_panel_graficos_conserva_las_variables(qt_app):
    from src.ui.graphs_panel import GraphsPanel
    g = GraphsPanel()
    g.set_data(_hoja())
    g.combo_col1.setCurrentText("Edad")
    g.set_data(_hoja())
    assert g.combo_col1.currentText() == "Edad"
    assert g.combo_col2.currentText() == "Glucosa_B"


def test_el_omnianalisis_conserva_lo_tildado_y_los_pares_manuales(qt_app):
    from src.ui.omni_panel import OmniPanel
    o = OmniPanel()
    o.set_data(_hoja())
    for i in (0, 1):
        o.list_vars.item(i).setSelected(True)
    o.cmb_target.setCurrentText("Edad")
    o._manual_pairs = [("Glucosa_A", "Glucosa_B")]
    o.set_data(_hoja())
    assert o._selected_cols() == ["Glucosa_A", "Glucosa_B"]
    assert o.cmb_target.currentText() == "Edad"
    assert o._manual_pairs == [("Glucosa_A", "Glucosa_B")]
    o.set_data(_hoja().rename(columns={"Edad": "Años"}))   # otra hoja: todo a cero
    assert o._selected_cols() == [] and o._manual_pairs == []


# ---------------- una columna contra sí misma ----------------

@pytest.mark.parametrize("nombre", ["Bland-Altman", "t-test pareado", "Correlacion de Pearson",
                                    "Passing-Bablok", "Kappa"])
def test_la_misma_columna_dos_veces_se_rechaza(nombre):
    from src.ui import entradas
    res = entradas.correr(nombre, entradas.Eleccion(_hoja(), "Glucosa_A", "Glucosa_A"))
    assert not res.ok
    assert "elegida dos veces" in res.error


def test_la_variable_3_repetida_tambien(qt_app):
    from src.ui import entradas
    res = entradas.correr("ANCOVA", entradas.Eleccion(_hoja(), "Glucosa_A", "Grupo", "Grupo"))
    assert not res.ok and "«Grupo»" in res.error


# ---------------- la hoja de datos ----------------

@pytest.mark.parametrize("texto, valor", [
    ("12,5", 12.5), ("12.5", 12.5), ("-3", -3.0), (",5", 0.5), ("1e3", 1000.0),
    ("abc", None), ("1.234,5", None), ("", None), ("12,5 mg", None),
])
def test_numero_acepta_coma_decimal(texto, valor):
    from src.ui.data_panel import numero
    assert numero(texto) == valor


@pytest.mark.parametrize("texto, visto", [
    ("181.115415006832", "181.1154"), ("44.0", "44"), ("0.000123456", "0.0001235"),
    ("2.5", "2.5"), ("Control", "Control"), ("12345678.9", "1.235e+07"),
])
def test_la_vista_redondea_sin_tocar_el_valor(texto, visto):
    from src.ui.data_panel import para_mostrar
    assert para_mostrar(texto) == visto


def test_escribir_con_coma_deja_la_columna_numerica(qt_app):
    from PyQt6.QtWidgets import QTableWidgetItem
    from src.ui.data_panel import DataPanel
    d = DataPanel()
    for fila, texto in enumerate(["12,5", "13", "", "14,25"]):
        d.table.setItem(fila, 0, QTableWidgetItem(texto))
    d.table.setItem(0, 1, QTableWidgetItem("a"))
    df = d.get_data()
    assert df["Var1"].dtype == float
    assert df["Var1"].tolist()[:2] == [12.5, 13.0] and df["Var1"].tolist()[-1] == 14.25


def test_editar_una_celda_con_coma_guarda_un_numero(qt_app):
    from PyQt6.QtWidgets import QTableWidgetItem
    from src.ui.data_panel import DataPanel
    d = DataPanel()
    d.data = _hoja()
    d._populate_table()
    d.table.setItem(0, 0, QTableWidgetItem("99,75"))
    assert d.data.iloc[0, 0] == 99.75
    assert d.table.item(1, 0).text() == str(_hoja().iloc[1, 0])   # el valor entero, sin redondear
