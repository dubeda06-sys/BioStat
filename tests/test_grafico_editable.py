"""Gráficos editables: el núcleo puro y el widget.

El núcleo se prueba sin Qt porque son funciones sobre `Figure`: así los tests
que importan —los que dicen si un ajuste recupera la recta correcta o si el
control es reversible— corren rápido y no dependen de que haya ventana.

La capa Qt se prueba aparte y sólo para lo que le corresponde: que se construya
sobre las figuras reales de la app, que aplicar todos los controles seguidos no
reviente, y que el control de tendencia quede apagado donde no hay datos que
ajustar.
"""
import os

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.text import Text  # noqa: E402

from src.analysis.omni_analyzer import run_omnianalysis  # noqa: E402
from src.analysis.omni_plots import comparison_figures  # noqa: E402
from src.ui import grafico_editable as ed  # noqa: E402


@pytest.fixture(scope="module")
def figuras():
    """Las tres figuras reales del Omnianálisis, no una inventada para el test."""
    r = np.random.default_rng(3)
    a = r.uniform(40, 180, 60)
    df = pd.DataFrame({"Metodo_A": a, "Metodo_B": a * 1.12 + 6 + r.normal(0, 3, 60)})
    rep = run_omnianalysis(df, list(df.columns),
                           confirmed_comparisons=[("Metodo_A", "Metodo_B")])
    res = next(b for b in rep["blocks"]
               if b.get("tipo") == "concordancia")["resultados"]
    return dict(comparison_figures(res["_plot"]))


# ---------------- Qué cuenta como dato ----------------

def test_encuentra_la_nube_de_puntos(figuras):
    series = ed.series_de_datos(figuras["Bland-Altman"])
    assert len(series) == 1
    assert len(series[0][2]) == 60


def test_no_confunde_las_rectas_de_referencia_con_datos(figuras):
    """El sesgo, los límites de acuerdo y la identidad son resultados del
    análisis. Reajustarles una tendencia no significa nada."""
    fig = figuras["Bland-Altman"]
    artistas = [a for _ax, a, _x, _y in ed.series_de_datos(fig)]
    lineas_de_referencia = [ln for ax in fig.axes for ln in ax.lines]
    assert lineas_de_referencia, "la figura debería tener rectas de referencia"
    for ln in lineas_de_referencia:
        assert ln not in artistas


def test_el_ccc_no_ofrece_tendencia(figuras):
    """Su panel izquierdo ubica UN punto y el derecho son barras: no hay nube."""
    assert ed.hay_datos_ajustables(figuras["CCC de Lin descompuesto"]) is False


def test_la_regresion_si_ofrece_tendencia(figuras):
    assert ed.hay_datos_ajustables(figuras["Regresión de comparación"]) is True


# ---------------- El ajuste ----------------

def test_recupera_una_recta_conocida():
    x = np.linspace(0, 100, 50)
    coef, r2, texto = ed.ajustar_tendencia(x, 2.5 * x + 7.0, grado=1)
    assert coef[0] == pytest.approx(2.5, abs=1e-9)
    assert coef[1] == pytest.approx(7.0, abs=1e-8)
    assert r2 == pytest.approx(1.0, abs=1e-12)
    assert "R²" in texto


def test_recupera_una_parabola_conocida():
    x = np.linspace(-5, 5, 60)
    coef, r2, _ = ed.ajustar_tendencia(x, 3 * x**2 - 2 * x + 1, grado=2)
    assert coef[0] == pytest.approx(3.0, abs=1e-9)
    assert r2 == pytest.approx(1.0, abs=1e-12)


def test_el_r2_baja_con_ruido():
    r = np.random.default_rng(1)
    x = np.linspace(0, 100, 80)
    _c, r2_limpio, _ = ed.ajustar_tendencia(x, 2 * x, grado=1)
    _c, r2_ruido, _ = ed.ajustar_tendencia(x, 2 * x + r.normal(0, 40, 80), grado=1)
    assert r2_limpio > r2_ruido


def test_se_niega_a_ajustar_con_x_constante():
    """Sin dispersión en X no hay pendiente: informa el motivo en vez de
    devolver coeficientes infinitos."""
    coef, _r2, texto = ed.ajustar_tendencia([5.0] * 10, list(range(10)), grado=1)
    assert coef is None and "iguales" in texto


def test_se_niega_con_menos_puntos_que_parametros():
    coef, _r2, texto = ed.ajustar_tendencia([1.0, 2.0], [1.0, 2.0], grado=1)
    assert coef is None and "al menos" in texto


def test_los_no_finitos_no_entran_en_el_ajuste():
    coef, r2, _ = ed.ajustar_tendencia([1., 2., np.nan, 4., 5.],
                                       [2., 4., 999., 8., 10.], grado=1)
    assert coef[0] == pytest.approx(2.0, abs=1e-9)
    assert r2 == pytest.approx(1.0, abs=1e-9)


# ---------------- Agregar y quitar sin dejar rastro ----------------

def test_la_tendencia_se_saca_sin_dejar_rastro(figuras):
    fig = figuras["Regresión de comparación"]
    antes = (sum(len(ax.lines) for ax in fig.axes),
             sum(len(ax.collections) for ax in fig.axes))
    ed.agregar_tendencia(fig, grado=1)
    assert sum(len(ax.lines) for ax in fig.axes) == antes[0] + 1
    ed.quitar_tendencia(fig)
    despues = (sum(len(ax.lines) for ax in fig.axes),
               sum(len(ax.collections) for ax in fig.axes))
    assert antes == despues


def test_dos_tendencias_seguidas_no_se_apilan(figuras):
    """Dos ajustes superpuestos sobre los mismos datos no se distinguen."""
    fig = figuras["Regresión de comparación"]
    ed.agregar_tendencia(fig, grado=1)
    ed.agregar_tendencia(fig, grado=2)
    ed.agregar_tendencia(fig, grado=3)
    n = sum(1 for ax in fig.axes for ln in ax.lines
            if ln.get_gid() == ed.GID_TENDENCIA)
    assert n == 1
    ed.quitar_tendencia(fig)


def test_una_tendencia_no_alimenta_la_siguiente(figuras):
    """Si la recta agregada contara como datos, el segundo ajuste saldría
    distinto del primero sobre los mismos puntos."""
    fig = figuras["Regresión de comparación"]
    primero = ed.agregar_tendencia(fig, grado=1)
    segundo = ed.agregar_tendencia(fig, grado=1)
    assert primero == segundo
    ed.quitar_tendencia(fig)


# ---------------- Los controles son reversibles ----------------

def test_escalar_la_fuente_no_se_compone(figuras):
    """Mover el control tres veces multiplicaría tres veces si la base no se
    guardara: la letra crecería sin control y no habría vuelta atrás."""
    fig = figuras["Bland-Altman"]
    base = [t.get_fontsize() for t in fig.findobj(Text)]
    ed.escalar_fuentes(fig, 1.5)
    una = [t.get_fontsize() for t in fig.findobj(Text)]
    ed.escalar_fuentes(fig, 1.5)
    otra = [t.get_fontsize() for t in fig.findobj(Text)]
    assert una == otra
    ed.escalar_fuentes(fig, 1.0)
    assert np.allclose(base, [t.get_fontsize() for t in fig.findobj(Text)])


def test_escalar_los_puntos_no_se_compone(figuras):
    fig = figuras["Regresión de comparación"]
    col = ed.series_de_datos(fig)[0][1]
    base = np.array(col.get_sizes(), dtype=float).copy()
    ed.escalar_puntos(fig, 2.0)
    una = np.array(col.get_sizes(), dtype=float).copy()
    ed.escalar_puntos(fig, 2.0)
    assert np.allclose(una, col.get_sizes())
    ed.escalar_puntos(fig, 1.0)
    assert np.allclose(base, col.get_sizes())


def test_los_factores_se_acotan(figuras):
    """Un factor de 1000 deja la figura inutilizable y sin forma de volver."""
    fig = figuras["Bland-Altman"]
    assert ed.escalar_fuentes(fig, 9999) <= 4.0
    assert ed.escalar_puntos(fig, -3) >= 0.1
    assert ed.opacidad_puntos(fig, 5) == 1.0
    ed.escalar_fuentes(fig, 1.0)
    ed.escalar_puntos(fig, 1.0)


def test_cambiar_la_tipografia_alcanza_a_todo_el_texto(figuras):
    fig = figuras["Bland-Altman"]
    ed.cambiar_fuente(fig, "Courier New")
    familias = {t.get_fontfamily()[0] if isinstance(t.get_fontfamily(), list)
                else t.get_fontfamily() for t in fig.findobj(Text)}
    assert familias == {"Courier New"}
    ed.cambiar_fuente(fig, "DejaVu Sans")


def test_sin_cambiar_no_toca_la_tipografia(figuras):
    """La primera opción del selector no puede alterar nada."""
    fig = figuras["Regresión de comparación"]
    antes = [t.get_fontfamily() for t in fig.findobj(Text)]
    assert ed.cambiar_fuente(fig, ed.FAMILIAS[0]) is None
    assert ed.cambiar_fuente(fig, "") is None
    assert [t.get_fontfamily() for t in fig.findobj(Text)] == antes


def test_pedir_leyenda_donde_no_hay_nada_rotulado_no_deja_un_recuadro_vacio():
    fig, ax = plt.subplots()
    ax.scatter([1, 2, 3], [1, 2, 3])          # sin label
    ed.mostrar_leyenda(fig, True)
    assert ax.get_legend() is None
    plt.close(fig)


def test_apagar_la_grilla_la_apaga_de_verdad():
    """`ax.grid(False, alpha=0.3)` la ENCIENDE: matplotlib avisa que le pasaron
    propiedades de linea junto al False y hace lo contrario de lo pedido. El
    checkbox no apagaba nada."""
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 2, 3])
    ed.mostrar_grilla(fig, True)
    assert any(ln.get_visible() for ln in ax.get_xgridlines())
    ed.mostrar_grilla(fig, False)
    assert not any(ln.get_visible() for ln in ax.get_xgridlines())
    assert not any(ln.get_visible() for ln in ax.get_ygridlines())
    plt.close(fig)


def test_redimensionar_se_acota():
    fig, _ax = plt.subplots()
    assert ed.redimensionar(fig, 999, 999) == (24.0, 18.0)
    assert ed.redimensionar(fig, 0.1, 0.1) == (3.0, 2.0)
    plt.close(fig)


# ---------------- La capa Qt ----------------

@pytest.fixture(scope="module")
def app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("nombre", ["Bland-Altman", "Regresión de comparación",
                                    "CCC de Lin descompuesto"])
def test_el_widget_se_construye_sobre_las_figuras_reales(app, figuras, nombre):
    w = ed.GraficoEditable(figuras[nombre])
    assert w.figure is figuras[nombre]
    assert w.canvas is not None
    assert w.barra is not None, "sin barra no hay zoom ni guardar"
    w.deleteLater()


def test_el_widget_se_comporta_como_un_canvas(app, figuras):
    """La ventana de informe lo trata como trataba al canvas."""
    w = ed.GraficoEditable(figuras["Bland-Altman"])
    assert hasattr(w, "figure") and callable(w.draw)
    w.draw()
    w.deleteLater()


def test_el_dialogo_aplica_todos_los_controles_sin_reventar(app, figuras):
    w = ed.GraficoEditable(figuras["Regresión de comparación"])
    d = ed.DialogoEditor(w)
    d.ed_titulo.setText("Título nuevo")
    d.ed_x.setText("Eje X nuevo")
    d.sp_fuente.setValue(1.4)
    d.sp_puntos.setValue(2.0)
    d.sl_alfa.setValue(40)
    d.ck_grilla.setChecked(False)
    d.ck_leyenda.setChecked(False)
    d.cb_tend.setCurrentIndex(1)
    d.sp_ancho.setValue(9.0)
    assert w.figure.axes[0].get_title() == "Título nuevo"
    assert "R²" in d.lbl_tend.text()
    d.deleteLater()
    w.deleteLater()


def test_restablecer_vuelve_al_titulo_y_al_tamano_originales(app, figuras):
    fig = figuras["Bland-Altman"]
    w = ed.GraficoEditable(fig)
    d = ed.DialogoEditor(w)
    titulo0 = fig.axes[0].get_title()
    ancho0, alto0 = fig.get_size_inches()

    d.ed_titulo.setText("otra cosa")
    d.sp_fuente.setValue(2.0)
    d.sp_ancho.setValue(15.0)
    d.cb_tend.setCurrentIndex(2)
    d._restablecer()

    assert fig.axes[0].get_title() == titulo0
    assert np.allclose(fig.get_size_inches(), (ancho0, alto0))
    assert d.sp_fuente.value() == 1.0
    assert not any(ln.get_gid() == ed.GID_TENDENCIA
                   for ax in fig.axes for ln in ax.lines)
    d.deleteLater()
    w.deleteLater()


def test_el_control_de_tendencia_se_apaga_y_dice_por_que(app, figuras):
    """Un control gris sin motivo se lee como una falla de la aplicación."""
    w = ed.GraficoEditable(figuras["CCC de Lin descompuesto"])
    d = ed.DialogoEditor(w)
    assert d.cb_tend.isEnabled() is False
    assert d.lbl_tend.text().strip(), "apagado y sin explicación"
    d.deleteLater()
    w.deleteLater()
