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


def test_cmh_pide_exposicion_evento_y_estrato(app):
    # Hasta el paso 4, CMH partía la hoja entera en tablas 2x2 y no pedía columnas.
    d = DialogoAnalisis("CMH test", COLUMNAS)
    assert d.combo_col1 is not None and d.combo_col2 is not None and d.combo_col3 is not None


def test_chi_cuadrado_pide_las_dos_variables(app):
    d = DialogoAnalisis("Chi-cuadrado", COLUMNAS)
    assert d.combo_col1 is not None and d.combo_col2 is not None


def test_friedman_pide_una_lista_de_columnas_tildables(app):
    d = DialogoAnalisis("Friedman", COLUMNAS, columnas_numericas=["Metodo_A", "Metodo_B", "Edad"])
    assert d.lista_columnas is not None and d.lista_columnas.count() == 3
    d.lista_columnas.item(2).setCheckState(d.lista_columnas.item(2).checkState().Unchecked)
    assert d.seleccion()["columnas"] == ["Metodo_A", "Metodo_B"]


def test_el_tamano_muestral_pide_sus_parametros(app):
    d = DialogoAnalisis("Tamano muestral (2 medias)", COLUMNAS)
    assert set(d.inputs_parametro) == {"delta", "sd", "ratio", "alpha", "poder"}
    d.inputs_parametro["delta"].setText("2,5")
    assert d.seleccion()["parametros"]["delta"] == "2,5"


def test_la_segunda_variable_arranca_en_la_segunda_columna(app):
    """Comparar una columna consigo misma no es lo que nadie quiere por defecto."""
    d = DialogoAnalisis("Bland-Altman", COLUMNAS)
    assert d.combo_col1.currentText() == "Metodo_A"
    assert d.combo_col2.currentText() == "Metodo_B"


def test_la_tercera_variable_es_opcional(app):
    d = DialogoAnalisis("Curva ROC", COLUMNAS)
    assert d.combo_col3.currentText() == SIN_COLUMNA


def test_seleccion_devuelve_siempre_las_mismas_claves(app):
    """El panel lee estas claves siempre; si alguna falta, revienta al indexar."""
    d = DialogoAnalisis("Chi-cuadrado", COLUMNAS)
    assert set(d.seleccion()) == {"c1", "c2", "c3", "alpha", "opciones",
                                  "columnas", "parametros"}
    # Sin lista de columnas: None (no "ninguna tildada"); sin parametros: {}.
    assert d.seleccion()["columnas"] is None and d.seleccion()["parametros"] == {}


def test_un_analisis_sin_opciones_devuelve_el_diccionario_vacio(app):
    d = DialogoAnalisis("Chi-cuadrado", COLUMNAS)
    assert d.seleccion()["opciones"] == {}


def test_bland_altman_ofrece_limites_y_eje(app):
    """Las tres variantes del metodo tienen que estar al alcance del usuario."""
    d = DialogoAnalisis("Bland-Altman", COLUMNAS)
    assert set(d.combos_opcion) == {"limites", "referencia", "escala"}
    limites = d.combos_opcion["limites"]
    valores = [limites.itemData(i) for i in range(limites.count())]
    assert valores == ["auto", "parametrico", "no_parametrico"]
    ejes = d.combos_opcion["referencia"]
    assert [ejes.itemData(i) for i in range(ejes.count())] == ["promedio", "x", "y"]
    escalas = d.combos_opcion["escala"]
    assert [escalas.itemData(i) for i in range(escalas.count())] == [
        "auto", "unidades", "porcentaje"]


def test_las_opciones_devuelven_el_valor_y_no_el_texto(app):
    """El combo muestra prosa y devuelve la clave: si devolviera el texto, el
    analisis recibiria 'No paramétrico — percentiles 2,5 y 97,5' y no lo
    entenderia."""
    d = DialogoAnalisis("Bland-Altman", COLUMNAS)
    d.combos_opcion["limites"].setCurrentIndex(2)
    d.combos_opcion["referencia"].setCurrentIndex(1)
    d.combos_opcion["escala"].setCurrentIndex(2)
    assert d.seleccion()["opciones"] == {"limites": "no_parametrico", "referencia": "x",
                                         "escala": "porcentaje"}


def test_por_defecto_sale_lo_mismo_que_declara_la_ficha(app):
    from src.ui.analysis_specs import opciones_por_defecto
    d = DialogoAnalisis("Bland-Altman", COLUMNAS)
    assert d.seleccion()["opciones"] == opciones_por_defecto("Bland-Altman")


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
