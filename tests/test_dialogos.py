"""El dialogo pide lo que el analisis usa, ni mas ni menos.

Un selector de mas no es cosmetico: el usuario elige una variable, el analisis
la ignora y el informe sale sobre otra cosa sin decir nada. Uno de menos deja
el analisis corriendo con la columna por defecto.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from src.ui import report_window  # noqa: E402
from src.ui.dialogs import SIN_COLUMNA, DialogoAnalisis  # noqa: E402

COLUMNAS = ["Metodo_A", "Metodo_B", "Edad"]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def sin_informes_abiertos():
    yield
    report_window.cerrar_todas()


def test_dos_variables_y_alfa(app):
    d = DialogoAnalisis("t-test pareado", COLUMNAS)
    assert d.combo_col1 is not None
    assert d.combo_col2 is not None
    assert d.combo_col3 is None
    assert d.input_alpha is not None


def test_una_sola_variable(app):
    d = DialogoAnalisis("Estadisticas descriptivas", COLUMNAS)
    assert d.combo_col1 is not None
    assert d.combo_col2 is None
    assert d.input_alpha is None


def test_analisis_sobre_toda_la_hoja_no_pide_columnas(app):
    d = DialogoAnalisis("Chi-cuadrado", COLUMNAS)
    assert d.combo_col1 is None and d.combo_col2 is None and d.combo_col3 is None


def test_la_segunda_variable_arranca_en_la_segunda_columna(app):
    """Comparar una columna consigo misma no es lo que nadie quiere por defecto."""
    d = DialogoAnalisis("Bland-Altman", COLUMNAS)
    assert d.combo_col1.currentText() == "Metodo_A"
    assert d.combo_col2.currentText() == "Metodo_B"


def test_la_tercera_variable_es_opcional(app):
    d = DialogoAnalisis("Curva ROC", COLUMNAS)
    assert d.combo_col3.currentText() == SIN_COLUMNA


def test_seleccion_devuelve_siempre_las_cuatro_claves(app):
    d = DialogoAnalisis("Chi-cuadrado", COLUMNAS)
    assert set(d.seleccion()) == {"c1", "c2", "c3", "alpha"}


def test_ventana_de_informe_se_registra_y_se_cierra(app):
    assert report_window.abiertas() == []
    v = report_window.abrir("Bland-Altman", "<b>hola</b>")
    assert report_window.abiertas() == [v]
    assert "hola" in v.txt.toPlainText()

    report_window.abrir("Passing-Bablok", "<b>otro</b>")
    assert len(report_window.abiertas()) == 2, "los informes tienen que acumularse"

    v.close()
    assert len(report_window.abiertas()) == 1, "al cerrar tiene que salir de la lista"


def test_cerrar_todas_no_deja_ninguna(app):
    report_window.abrir("uno", "<i>1</i>")
    report_window.abrir("dos", "<i>2</i>")
    report_window.cerrar_todas()
    assert report_window.abiertas() == []
