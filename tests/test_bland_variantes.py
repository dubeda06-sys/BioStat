"""Las tres variantes de Bland-Altman tienen que dar resultados distintos.

El core ya calculaba las tres; lo que faltaba era poder elegir. El riesgo de
una capa de opciones es que se vea el selector y no haga nada: el usuario elige
"no paramétrico", el informe cambia de título y los números siguen siendo los
paramétricos. Estos tests comparan los números, no los rótulos.

El eje X es el que más silenciosamente engaña. Si uno de los métodos es de
referencia y se grafica contra el promedio, la referencia entra en los dos ejes
y **atenúa** el sesgo proporcional: se ve menos desvío del que hay
(Krouwer 2008, Stat Med 27:778-780; recogido en CLSI EP09).
"""
import os
import re

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from src.core.bland_altman import bland_altman_analysis  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def _sin_html(texto):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", texto))


@pytest.fixture(scope="module")
def par_con_sesgo_proporcional():
    """Un método que lee 8 % alto: sesgo proporcional real, no ruido."""
    rng = np.random.default_rng(11)
    referencia = rng.uniform(20, 200, 40)
    prueba = referencia * 1.08 + rng.normal(0, 3, 40)
    return referencia, prueba


@pytest.fixture(scope="module")
def par_asimetrico():
    """Diferencias con cola: los límites paramétricos no corresponden."""
    rng = np.random.default_rng(5)
    a = rng.uniform(50, 150, 60)
    b = a + rng.exponential(4, 60) - 2
    return a, b


# ---------------- El core ----------------

def test_el_core_devuelve_las_dos_familias_de_limites(par_con_sesgo_proporcional):
    a, b = par_con_sesgo_proporcional
    r = bland_altman_analysis(a, b)
    assert np.isfinite(r["loa_lower"]) and np.isfinite(r["loa_upper"])
    assert np.isfinite(r["loa_np_lower"]) and np.isfinite(r["loa_np_upper"])
    assert (r["loa_lower"], r["loa_upper"]) != (r["loa_np_lower"], r["loa_np_upper"])


def test_el_eje_de_referencia_cambia_el_eje_x(par_con_sesgo_proporcional):
    a, b = par_con_sesgo_proporcional
    clasico = bland_altman_analysis(a, b)
    krouwer = bland_altman_analysis(a, b, reference="x")
    assert np.allclose(clasico["x_axis"], clasico["means"])
    assert np.allclose(krouwer["x_axis"], a)
    assert clasico["x_axis_label"] == "promedio"
    assert krouwer["x_axis_label"] == "referencia"


def test_sin_referencia_no_se_inventa_una_pendiente(par_con_sesgo_proporcional):
    a, b = par_con_sesgo_proporcional
    assert bland_altman_analysis(a, b)["slope_vs_reference"] is None


def test_el_promedio_atenua_el_sesgo_proporcional(par_con_sesgo_proporcional):
    """El motivo entero de la modificación de Krouwer, en un assert.

    Con una referencia real, la pendiente contra el promedio sale más chica en
    magnitud que la pendiente contra la referencia. Ese achicamiento es el que
    hace parecer que un método está mejor calibrado de lo que está.
    """
    a, b = par_con_sesgo_proporcional
    r = bland_altman_analysis(a, b, reference="x")
    contra_promedio = abs(r["slope_vs_mean"]["slope"])
    contra_referencia = abs(r["slope_vs_reference"]["slope"])
    assert contra_promedio < contra_referencia, (
        f"contra el promedio {contra_promedio:.4f} debería salir atenuada "
        f"frente a {contra_referencia:.4f} contra la referencia"
    )


def test_las_dos_referencias_no_dan_lo_mismo(par_con_sesgo_proporcional):
    a, b = par_con_sesgo_proporcional
    rx = bland_altman_analysis(a, b, reference="x")
    ry = bland_altman_analysis(a, b, reference="y")
    assert not np.allclose(rx["x_axis"], ry["x_axis"])


# ---------------- El panel ----------------

@pytest.fixture
def panel(qt_app):
    import pandas as pd
    from src.ui.analysis_panel import AnalysisPanel
    rng = np.random.default_rng(11)
    ref = rng.uniform(20, 200, 40)
    df = pd.DataFrame({"Referencia": ref, "Prueba": ref * 1.08 + rng.normal(0, 3, 40)})
    p = AnalysisPanel()
    p.set_data(df)
    return p


def _informe(panel, opciones):
    panel.opciones_metodo = opciones
    return _sin_html(panel._bland("Referencia", "Prueba", opciones))


def test_el_modo_elegido_cambia_los_numeros(panel):
    """Que el selector no sea decorativo: los límites tienen que cambiar."""
    param = _informe(panel, {"limites": "parametrico", "referencia": "promedio"})
    nopar = _informe(panel, {"limites": "no_parametrico", "referencia": "promedio"})
    assert "± 1,96·DE" in param
    assert "percentiles 2,5 y 97,5" in nopar
    assert param != nopar


def test_el_no_parametrico_centra_en_la_mediana(panel):
    nopar = _informe(panel, {"limites": "no_parametrico", "referencia": "promedio"})
    assert "mediana de las diferencias" in nopar
    param = _informe(panel, {"limites": "parametrico", "referencia": "promedio"})
    assert "media de las diferencias" in param


def test_krouwer_informa_las_dos_pendientes(panel):
    """Con referencia hay que poder contrastar: si solo se mostrara una, no se
    vería la atenuación, que es todo el punto."""
    texto = _informe(panel, {"limites": "parametrico", "referencia": "x"})
    assert "Pendiente contra el promedio" in texto
    assert "Pendiente contra Referencia" in texto
    assert "Krouwer" in texto


def test_sin_referencia_solo_hay_una_pendiente(panel):
    texto = _informe(panel, {"limites": "parametrico", "referencia": "promedio"})
    assert "Pendiente contra el promedio" in texto
    assert "Pendiente contra Referencia" not in texto


def test_el_informe_dice_en_que_se_apoyo_la_eleccion(panel):
    """Unos límites sin la evidencia que los justifica no se pueden auditar."""
    texto = _informe(panel, {})
    assert "Shapiro-Wilk" in texto
    assert "Normalidad de las diferencias" in texto


def test_forzar_parametrico_sobre_diferencias_no_normales_avisa(qt_app):
    import pandas as pd
    from src.ui.analysis_panel import AnalysisPanel
    rng = np.random.default_rng(5)
    a = rng.uniform(50, 150, 60)
    df = pd.DataFrame({"A": a, "B": a + rng.exponential(4, 60) - 2})
    p = AnalysisPanel()
    p.set_data(df)
    texto = _sin_html(p._bland("A", "B", {"limites": "parametrico",
                                          "referencia": "promedio"}))
    assert "no son normales" in texto
    assert "no son los que corresponden" in texto


def test_el_automatico_elige_no_parametrico_si_las_diferencias_no_lo_son(qt_app):
    import pandas as pd
    from src.ui.analysis_panel import AnalysisPanel
    rng = np.random.default_rng(5)
    a = rng.uniform(50, 150, 60)
    df = pd.DataFrame({"A": a, "B": a + rng.exponential(4, 60) - 2})
    p = AnalysisPanel()
    p.set_data(df)
    texto = _sin_html(p._bland("A", "B", {"limites": "auto", "referencia": "promedio"}))
    assert "no paramétrico" in texto
    assert "por ese resultado" in texto


def test_no_se_dictamina_concordancia_con_un_umbral_inventado(panel):
    """El programa no sabe qué diferencia tolera el analito: eso lo pone el
    laboratorio desde el requisito de calidad."""
    texto = _informe(panel, {})
    assert "Los metodos son concordantes" not in texto
    assert "requisito de calidad" in texto


def test_ningun_p_sale_como_cero_exacto(panel):
    texto = _informe(panel, {"limites": "parametrico", "referencia": "x"})
    assert "p=0.0000" not in texto
    assert "p=<" not in texto, "el igual y el menor quedaron pegados"
