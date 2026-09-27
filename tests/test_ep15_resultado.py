"""EP15-A3 como `Resultado`: la hoja con una columna por corrida.

Mismo ejemplo de ferritina que `test_ep15.py` (muestra 2 de la tabla 10). Las
declaraciones del fabricante para esa muestra (CV 2,0 % de repetibilidad, 3,4 %
intralaboratorio) son las del ejemplo de EP15-A3 que publica Analyse-it; el
grupo de pares (142,5; DE 4,5; 43 laboratorios; tres muestras) es el del
ejemplo resuelto 1A.
"""
import os
import re
from html import unescape

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from scipy import stats  # noqa: E402

from src.core.ep15 import precision_ep15 as core  # noqa: E402
from src.resultado import render_html  # noqa: E402
from src.resultado.constructores import precision_ep15  # noqa: E402
from tests.test_ep15 import CORRIDAS  # noqa: E402

COLS = [f"Día {i}" for i in range(1, 6)]
HOJA = pd.DataFrame({c: v for c, v in zip(COLS, CORRIDAS)})


def _valor(res, nombre):
    return next(v for v in res.valores if v.nombre == nombre)


def _paso(res, texto):
    return next(s for s in res.supuestos if texto in s.pregunta)


def _texto(res):
    return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", render_html(res)))).strip()


def test_los_numeros_son_los_del_core():
    res = precision_ep15(HOJA, COLS)
    c = core(CORRIDAS)
    assert res.ok
    assert _valor(res, "Repetibilidad (s_R)").valor == c["s_r"]
    assert _valor(res, "Intralaboratorio (s_WL)").valor == c["s_wl"]
    assert _valor(res, "MS entre corridas").valor == pytest.approx(15.86)
    assert res.entrada.n == 25


def test_sin_declaracion_no_hay_nada_que_verificar():
    res = precision_ep15(HOJA, COLS)
    assert "Sin imprecisión declarada" in res.lectura
    assert not any("compatible con la declarada" in s.pregunta for s in res.supuestos)


def test_declaracion_del_fabricante_en_cv_verificada():
    res = precision_ep15(HOJA, COLS, {"declaracion": "cv", "sigma_r": 2.0, "sigma_wl": 3.4})
    rep = _paso(res, "repetibilidad observada")
    wl = _paso(res, "intralaboratorio observada")
    assert rep.respuesta == wl.respuesta == "Sí"
    assert "sin necesitar el límite" in rep.consecuencia
    assert "repetibilidad declarada por el fabricante quedó verificada" in res.lectura


def test_por_encima_de_lo_declarado_pero_debajo_del_uvl():
    """s_R = 1,78: declarado 1,6, UVL = 1,6·√(χ²(0,95; 20)/20) = 1,6·1,253 = 2,005."""
    res = precision_ep15(HOJA, COLS, {"sigma_r": 1.6})
    rep = _paso(res, "repetibilidad observada")
    assert rep.respuesta == "Sí" and rep.ok
    assert "no el límite de verificación" in rep.consecuencia
    assert _valor(res, "Límite de verificación (UVL) de la repetibilidad").valor == \
        pytest.approx(1.6 * np.sqrt(stats.chi2.ppf(0.95, 20) / 20), rel=1e-12)


def test_por_encima_del_uvl_no_se_verifica():
    res = precision_ep15(HOJA, COLS, {"sigma_r": 1.0, "sigma_wl": 1.2})
    assert _paso(res, "repetibilidad observada").respuesta == "No"
    assert "NO se verificó" in res.lectura


def test_varias_muestras_suben_el_uvl():
    una = precision_ep15(HOJA, COLS, {"sigma_r": 1.6})
    tres = precision_ep15(HOJA, COLS, {"sigma_r": 1.6, "n_muestras": 3})
    nombre = "Límite de verificación (UVL) de la repetibilidad"
    assert _valor(tres, nombre).valor > _valor(una, nombre).valor


def test_veracidad_contra_grupo_de_pares_ejemplo_1a():
    """Desde los datos (s_WL = 2,387, no el 2,40 redondeado de la tabla),
    Satterthwaite da 11,6 gl → 12, los mismos que la norma lee en la tabla 15A,
    y el intervalo publicado sale exacto: 139,6 a 145,4."""
    res = precision_ep15(HOJA, COLS, {"valor_asignado": 142.5, "incertidumbre": "pares",
                                      "u": 4.5, "n_lab": 43, "n_muestras": 3})
    v = res.crudo["veracidad"]
    assert v["dentro"] and v["df_c"] == 12
    assert v["m"] == pytest.approx(2.78, abs=0.005)
    assert v["intervalo"][0] == pytest.approx(139.6, abs=0.05)
    assert v["intervalo"][1] == pytest.approx(145.4, abs=0.05)
    assert _paso(res, "sesgo se distingue").respuesta == "No"
    assert "no se distingue del azar" in res.lectura


def test_veracidad_con_incertidumbre_expandida():
    """U = 2, k = 2 → u = 1: el intervalo es el de u = 1."""
    con_u = precision_ep15(HOJA, COLS, {"valor_asignado": 142.5, "incertidumbre": "u", "u": 1})
    con_U = precision_ep15(HOJA, COLS, {"valor_asignado": 142.5, "incertidumbre": "U",
                                        "u": 2, "k": 2})
    assert con_U.crudo["veracidad"]["intervalo"] == con_u.crudo["veracidad"]["intervalo"]


def test_sesgo_fuera_del_intervalo():
    res = precision_ep15(HOJA, COLS, {"valor_asignado": 150.0})
    assert not res.crudo["veracidad"]["dentro"]
    assert _paso(res, "sesgo se distingue").respuesta == "Sí"
    assert "fuera del intervalo" in res.lectura


def test_atipico_marcado_y_no_sacado():
    hoja = HOJA.copy()
    hoja.loc[2, "Día 2"] = 170
    res = precision_ep15(hoja, COLS)
    paso = _paso(res, "atípico")
    assert paso.respuesta == "Sí" and not paso.ok
    assert res.entrada.n == 25


def test_una_celda_vacia_es_una_replica_menos():
    hoja = HOJA.copy()
    hoja.loc[4, "Día 3"] = np.nan
    res = precision_ep15(hoja, COLS)
    assert res.ok and res.entrada.n == 24
    assert res.crudo["ep15"]["n0"] == pytest.approx(4.79, abs=0.005)
    assert _paso(res, "diseño").respuesta == "No"


@pytest.mark.parametrize("opciones, motivo", [
    ({"sigma_r": -1}, "positivo"),
    ({"valor_asignado": 140, "incertidumbre": "u"}, "Falta la incertidumbre"),
    ({"valor_asignado": 140, "incertidumbre": "pares", "u": 4, "n_lab": 1},
     "al menos 2 laboratorios"),
])
def test_rechazos_con_motivo(opciones, motivo):
    res = precision_ep15(HOJA, COLS, opciones)
    assert not res.ok and motivo in res.error


def test_una_sola_corrida_se_rechaza():
    assert "al menos 2 corridas" in precision_ep15(HOJA, ["Día 1"]).error


def test_el_informe_se_lee_entero():
    res = precision_ep15(HOJA, COLS, {"declaracion": "cv", "sigma_r": 2.0, "sigma_wl": 3.4,
                                      "valor_asignado": 142.5})
    t = _texto(res)
    for pieza in ("Repetibilidad", "Intralaboratorio", "UVL", "Intervalo de verificación",
                  "EP15-A3", "Fórmula", "Referencias"):
        assert pieza in t
    fig = res.figuras[0].dibujar()
    try:
        assert len(fig.axes[0].collections) == 5
    finally:
        import matplotlib.pyplot as plt
        plt.close(fig)


# ---------------- El panel y el diálogo ----------------

@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _panel(hoja):
    from src.ui.analysis_panel import AnalysisPanel
    panel = AnalysisPanel()
    panel.set_data(hoja)
    panel.combo_analysis.setCurrentText("Precisión EP15")
    return panel


def test_el_panel_sin_dialogo_usa_todas_y_lo_dice(qt_app):
    panel = _panel(HOJA)
    panel._run()
    texto = panel.txt_results.toPlainText()
    assert "Repetibilidad" in texto and "Qué se verificó y qué se decidió" in texto
    assert "todas las columnas numéricas" in texto


def test_el_panel_con_lo_elegido_en_el_dialogo(qt_app):
    panel = _panel(HOJA.assign(ID=range(5)))
    panel.columnas_elegidas = COLS
    panel.opciones_metodo = {"declaracion": "cv", "incertidumbre": "pares"}
    panel.parametros = {"sigma_r": "2,0", "sigma_wl": "3.4", "valor_asignado": "142.5",
                        "u": "4.5", "n_lab": "43", "n_muestras": "3", "k": ""}
    panel._run()
    texto = panel.txt_results.toPlainText()
    assert "quedó verificada" in texto
    assert "139.5" in texto or "139.6" in texto
    assert "todas las columnas numéricas" not in texto


def test_un_parametro_que_no_es_numero_se_dice(qt_app):
    panel = _panel(HOJA)
    panel.columnas_elegidas = COLS
    panel.parametros = {"sigma_r": "dos"}
    panel._run()
    assert "tiene que ser un número" in panel.txt_results.toPlainText()


def test_el_dialogo_deja_los_opcionales_vacios(qt_app):
    from src.ui.dialogs import DialogoAnalisis
    d = DialogoAnalisis("Precisión EP15", COLS)
    assert d.inputs_parametro["sigma_r"].text() == ""
    assert d.inputs_parametro["valor_asignado"].text() == ""
    assert d.inputs_parametro["n_muestras"].text() == "1"
    assert set(d.combos_opcion) == {"declaracion", "incertidumbre"}
    assert d.lista_columnas is not None
