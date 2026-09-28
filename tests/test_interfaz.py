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


@pytest.mark.parametrize("valores, rotulo", [
    ([1.5, 2.25, np.nan, 3.75, 4.5, 5.0, 6.5, 7.25, 8.0, 9.5, 10.25, 11.0, 12.75], "numérica · 1 vacía"),
    ([1, 2, 3, 1, 2, 3, 1, 2, 3, 1.0], "códigos 1–3"),
    (["05/01/2026", "06/01/2026", "07/01/2026"], "fecha"),
    (["Control", "Diabetes", "Otro", None, None], "categórica · 2 vacías"),
    (["Sí", "No", "Sí"], "binaria"),
])
def test_el_tipo_de_columna_es_el_del_omnianalisis(valores, rotulo):
    from src.ui.data_panel import tipo_en_la_hoja
    corto, ayuda = tipo_en_la_hoja(pd.Series(valores))
    assert corto == rotulo
    assert "Omnianálisis" in ayuda


def test_una_columna_vacia_no_lleva_tipo():
    from src.ui.data_panel import tipo_en_la_hoja
    assert tipo_en_la_hoja(pd.Series([np.nan, np.nan])) is None


def _hoja_con_huecos():
    df = _hoja()
    df.loc[[2, 5], "Glucosa_B"] = np.nan
    return df


def _cargada(qt_app, df):
    from src.ui.data_panel import DataPanel
    d = DataPanel()
    d.data = df
    d._populate_table()
    return d


def test_el_encabezado_dice_el_tipo_y_los_vacios_sin_ensuciar_el_nombre(qt_app):
    d = _cargada(qt_app, _hoja_con_huecos())
    textos = [d.table.horizontalHeaderItem(i).text() for i in range(4)]
    assert textos[0] == "A  Glucosa_A\nnumérica"
    assert textos[1] == "B  Glucosa_B\nnumérica · 2 vacías"
    assert textos[2] == "C  Grupo\nbinaria"
    assert d.nombres_de_columna() == ["Glucosa_A", "Glucosa_B", "Grupo", "Edad"]
    assert "Omnianálisis" in d.table.horizontalHeaderItem(1).toolTip()


def test_las_celdas_vacias_se_ven(qt_app):
    from PyQt6.QtCore import Qt
    from src.ui.data_panel import FONDO_FALTANTE
    d = _cargada(qt_app, _hoja_con_huecos())
    assert d.table.item(2, 1).background().color() == FONDO_FALTANTE
    assert d.table.item(3, 1).background().style() == Qt.BrushStyle.NoBrush
    d.table.item(2, 1).setText("101,5")                          # se completa
    assert d.data.iloc[2, 1] == 101.5
    assert d.table.item(2, 1).background().style() == Qt.BrushStyle.NoBrush
    assert d.table.horizontalHeaderItem(1).text().endswith("numérica · 1 vacía")


def test_con_el_tema_puesto_la_celda_vacia_se_pinta(qt_app):
    """La regla `QTableWidget::item` del tema hace que Qt no pinte el fondo de
    la celda: sin el delegado, el fondo quedaba en el modelo y no en pantalla."""
    from src.ui.data_panel import FONDO_FALTANTE
    from src.ui.styles import MAIN_STYLE
    d = _cargada(qt_app, _hoja_con_huecos())
    d.setStyleSheet(MAIN_STYLE)
    d.resize(900, 500)
    d.show()
    qt_app.processEvents()
    centro = d.table.visualItemRect(d.table.item(2, 1)).center()
    assert d.table.viewport().grab().toImage().pixelColor(centro) == FONDO_FALTANTE
    d.close()


def test_vaciar_una_celda_deja_un_faltante_y_la_columna_numerica(qt_app):
    """Antes quedaba "" y la columna entera pasaba a texto."""
    d = _cargada(qt_app, _hoja())
    d.table.item(0, 0).setText("")
    assert np.isnan(d.data.iloc[0, 0])
    assert d.data["Glucosa_A"].dtype == float
    assert d.table.item(0, 0).background().color().name() == "#fbeccc"


def test_un_texto_en_una_columna_numerica_se_ve_en_el_encabezado(qt_app):
    import warnings
    d = _cargada(qt_app, _hoja())
    with warnings.catch_warnings():
        warnings.simplefilter("error")                 # pandas 3 falla donde 2 avisa
        d.table.item(0, 3).setText("ochenta")
    assert d.table.horizontalHeaderItem(3).text().endswith("categórica")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        d.table.item(0, 3).setText("80")               # se corrige
    assert d.data["Edad"].dtype == float
    assert "numérica" in d.table.horizontalHeaderItem(3).text()


def test_lo_escrito_en_una_fila_agregada_no_se_pierde(qt_app):
    from PyQt6.QtWidgets import QTableWidgetItem
    d = _cargada(qt_app, _hoja())
    d._add_row()
    d.table.setItem(40, 0, QTableWidgetItem("123"))
    assert len(d.data) == 41 and d.data.iloc[40, 0] == 123.0
    assert np.isnan(d.data.iloc[40, 1])


def test_escrita_a_mano_una_celda_vacia_es_un_faltante(qt_app):
    from PyQt6.QtWidgets import QTableWidgetItem
    from src.ui.data_panel import DataPanel
    d = DataPanel()
    for fila, (a, b) in enumerate([("1,5", "x"), ("2", ""), ("3,25", "y")]):
        d.table.setItem(fila, 0, QTableWidgetItem(a))
        d.table.setItem(fila, 1, QTableWidgetItem(b))
    df = d.get_data()
    assert df["Var2"].isna().tolist() == [False, True, False]
    # Tres valores distintos: el Omnianálisis pide confirmar si es numérica.
    assert d.table.horizontalHeaderItem(0).text() == "A  Var1\na confirmar"
    assert d.table.horizontalHeaderItem(2).text() == "C  Var3"      # vacía: sin tipo


def test_editar_una_celda_con_coma_guarda_un_numero(qt_app):
    from PyQt6.QtWidgets import QTableWidgetItem
    from src.ui.data_panel import DataPanel
    d = DataPanel()
    d.data = _hoja()
    d._populate_table()
    d.table.setItem(0, 0, QTableWidgetItem("99,75"))
    assert d.data.iloc[0, 0] == 99.75
    assert d.table.item(1, 0).text() == str(_hoja().iloc[1, 0])   # el valor entero, sin redondear


# ---------------- el diálogo ----------------

_COLS = ["Glucosa_A", "Glucosa_B", "Grupo", "Edad", "Día 1", "Día 2", "Día 3"]


def _dialogo(nombre):
    from src.ui.dialogs import DialogoAnalisis
    return DialogoAnalisis(nombre, _COLS, columnas_numericas=[c for c in _COLS if c != "Grupo"])


def test_validar_un_metodo_entra_en_la_pantalla(qt_app):
    """Medía 1150 px: en una notebook los botones quedaban afuera."""
    d = _dialogo("Validar un método")
    d.show()
    limite = d.screen().availableGeometry().height()
    assert d.height() <= limite
    d.close()


def test_validar_un_metodo_va_por_secciones(qt_app):
    d = _dialogo("Validar un método")
    assert list(d.secciones) == [
        "Criterio del veredicto", "Niveles de decisión médica", "Recta de Deming",
        "Precisión por EP15 (opcional)", "Lo que declara el fabricante",
        "Valor asignado del material"]
    caja = d.secciones["Criterio del veredicto"]
    assert d.inputs_parametro["tea"].parent() is caja


def test_lo_de_ep15_se_prende_al_tildar_una_corrida(qt_app):
    from PyQt6.QtCore import Qt
    d = _dialogo("Validar un método")
    fabricante = d.secciones["Lo que declara el fabricante"]
    asignado = d.secciones["Valor asignado del material"]
    assert not fabricante.isEnabled() and not asignado.isEnabled()
    d.lista_columnas.item(3).setCheckState(Qt.CheckState.Checked)
    assert fabricante.isEnabled() and asignado.isEnabled()
    d.lista_columnas.item(3).setCheckState(Qt.CheckState.Unchecked)
    assert not fabricante.isEnabled()


def test_cada_campo_de_una_seccion_existe_y_ninguno_queda_afuera():
    from src.ui.analysis_specs import SECCIONES, multi, opciones, parametros
    for analisis, secs in SECCIONES.items():
        claves = [c for s in secs for c in s.claves]
        propias = ([o.clave for o in opciones(analisis)] + [p.clave for p in parametros(analisis)]
                   + (["multi"] if multi(analisis) else []))
        assert sorted(claves) == sorted(propias), analisis
        assert len(claves) == len(set(claves)), analisis


def test_la_seleccion_sigue_igual_con_secciones(qt_app):
    d = _dialogo("Validar un método")
    d.inputs_parametro["tea"].setText("10")
    sel = d.seleccion()
    assert sel["parametros"]["tea"] == "10"
    assert sel["columnas"] == []          # sin tildar: sin corridas


def test_el_titulo_es_el_nombre_en_castellano(qt_app):
    d = _dialogo("Diagnostic test")
    assert d.windowTitle() == "Evaluación de una prueba diagnóstica"


# ---------------- la ventana ----------------

def test_la_barra_de_estado_dice_que_hay_cargado(qt_app):
    from src.ui.main_window import MainWindow
    w = MainWindow()
    w._on_data_changed(_hoja())
    assert w.statusBar().currentMessage() == "Datos: 40 filas × 4 columnas (3 numéricas)"
    w._on_data_changed(None)
    assert w.statusBar().currentMessage().startswith("Sin datos")


def test_el_panel_no_repite_la_descripcion_ni_una_formula_vieja(qt_app):
    from src.ui import analysis_panel
    from src.ui.analysis_panel import AnalysisPanel
    assert not hasattr(analysis_panel, "ANALYSIS_LEGENDS")
    assert not hasattr(AnalysisPanel(), "lbl_legend")


def test_la_formula_del_panel_va_una_linea_por_renglon(qt_app):
    """Se pegaba sin los saltos de línea: diez líneas en un párrafo corrido."""
    from src.ui.analysis_panel import AnalysisPanel
    p = AnalysisPanel()
    p._set_formula("Fórmula: Bland-Altman", "d = x1 − x2\nLoA = d̄ ± 1,96·s\nx < y & z")
    assert p.txt_formula.toPlainText().splitlines() == [
        "Fórmula: Bland-Altman", "d = x1 − x2", "LoA = d̄ ± 1,96·s", "x < y & z"]


# ---------------- el informe ----------------

def _informe_completo():
    from src.resultado import Cita, Entrada, Metodo, Resultado, Supuesto, Valor
    return Resultado(
        analisis="prueba", titulo="Prueba — A vs B",
        entrada=Entrada(("A", "B"), n=19, descartadas=2),
        valores=[Valor("Sesgo", 0.03, ic=(-0.5, 0.6))],
        metodo=Metodo("Bland-Altman paramétrico", "Las diferencias son normales."),
        supuestos=[Supuesto("¿Normales?", "p=0.41", "Sí", "Límites ± 1,96·DE.")],
        formula="LoA = d̄ ± 1,96·s", citas=[Cita("Bland JM, Altman DG. Lancet 1986")],
        lectura="LECTURA", matiz="MATIZ", advertencias=["ADVERTENCIA"])


def test_el_informe_empieza_por_la_conclusion():
    """Antes lo primero eran 15 filas de números y la lectura quedaba abajo,
    fuera de la vista en el recuadro del panel."""
    from src.resultado import render_html
    html = render_html(_informe_completo())
    orden = ["Prueba — A vs B", "LECTURA", "MATIZ", "ADVERTENCIA", "2 filas incompletas",
             "Resultados", "Sesgo", "Método", "Qué se verificó", "Fórmula", "Referencias"]
    posiciones = [html.index(t) for t in orden]
    assert posiciones == sorted(posiciones)


def test_en_el_panel_la_conclusion_se_ve_sin_desplazar(qt_app):
    """Con el recuadro de Resultados del alto que tiene en la ventana."""
    from src.resultado import Valor, render_html
    from PyQt6.QtWidgets import QTextEdit
    res = _informe_completo()
    res.valores = [Valor(f"Valor {i}", float(i)) for i in range(15)]
    t = QTextEdit()
    t.resize(900, 330)
    t.setHtml(render_html(res))
    t.show()
    qt_app.processEvents()
    visible = t.cursorForPosition(t.viewport().rect().bottomLeft()).position()
    assert t.toPlainText().index("MATIZ") < visible
    t.close()
