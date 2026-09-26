"""El esqueleto de la envoltura `Resultado`: modelo, lenguaje, datos y renderizador.

Lo que se fija acá no es "que no rompa". Son las propiedades que motivaron la
envoltura (`docs/plans/2026-09-26-envoltura-resultado.md`):

  - un rechazo no puede colarse como verdadero en un `if`;
  - el panel y el Omnianálisis dicen los números con la MISMA función;
  - las filas se emparejan en un solo lugar, contando lo que queda afuera;
  - el informe no dice «significativo», no imprime p=0.0000 y escapa lo que
    escribe el usuario.
"""
import os
import re
from html import unescape

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.resultado import (  # noqa: E402
    Cita, Entrada, Figura, Metodo, Resultado, ResultadoComoBooleano, Supuesto, Valor,
    render_html,
)
from src.resultado import lenguaje  # noqa: E402
from src.resultado.datos import columnas_faltantes, filas_completas  # noqa: E402


def _texto(html):
    """Lo que lee la persona: sin etiquetas y con las entidades resueltas."""
    return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))).strip()


def _completo():
    return Resultado(
        analisis="prueba",
        titulo="Prueba — A vs B",
        entrada=Entrada(columnas=("A", "B"), n=19, descartadas=2),
        valores=[Valor("n", np.int64(19)),
                 Valor("Sesgo", 0.03412, ic=(-0.51, 0.58)),
                 Valor("p", lenguaje.p_token(3e-9))],
        metodo=Metodo("Bland-Altman paramétrico",
                      "Las diferencias no se apartan de la normal."),
        supuestos=[Supuesto("¿Las diferencias son normales?", "Shapiro-Wilk, p=0.41",
                            "Sí", "Se usan los límites ± 1,96·DE.",
                            alternativa="se usarían los percentiles 2,5 y 97,5.")],
        formula="LoA = d̄ ± 1,96·s",
        citas=[Cita("Bland JM, Altman DG. Lancet 1986", "https://example.org/ba")],
        lectura="El 95 % de las diferencias cae entre −2,4 y 2,5.",
        matiz="Que el sesgo sea chico no dice si los límites son tolerables.",
        advertencias=["Menos de 40 pares: el IC de los límites es ancho."],
    )


# ---------------- Modelo ----------------

def test_un_resultado_no_se_puede_usar_como_booleano():
    """El core devuelve {"error": ...} y un `if res:` lo dejaba pasar."""
    res = Resultado.rechazo("x", "X", "Se necesitan 3 pares; hay 2.")
    with pytest.raises(ResultadoComoBooleano):
        if res:
            pass
    with pytest.raises(TypeError):
        bool(_completo())


def test_ok_distingue_rechazo_de_calculo():
    assert _completo().ok is True
    assert Resultado.rechazo("x", "X", "motivo").ok is False


@pytest.mark.parametrize("respuesta, motivo", [
    (None, "no devolvió resultado"),
    ({"error": "La primera variable es constante."}, "La primera variable es constante."),
])
def test_rechazo_del_core_trae_el_motivo(respuesta, motivo):
    res = Resultado.rechazo_del_core("x", "X", respuesta)
    assert res is not None and not res.ok
    assert motivo in res.error


def test_rechazo_del_core_deja_pasar_un_calculo():
    assert Resultado.rechazo_del_core("x", "X", {"slope": 1.0}) is None


def test_los_valores_se_formatean_sin_repr_de_numpy():
    assert Valor("n", np.int64(19)).texto() == "19"
    assert Valor("x", np.float64(1.23456)).texto() == "1.2346"
    assert Valor("x", float("nan")).texto() == "—"
    assert Valor("x", None).texto() == "—"
    assert Valor("x", True).texto() == "Sí"
    assert Valor("x", 1.0, ic=(np.float64(0.9), np.float64(1.1))).texto_ic() == "0.9000 a 1.1000"


# ---------------- Lenguaje ----------------

def test_el_omnianalisis_usa_las_mismas_funciones():
    """Una sola copia: si cada lado tiene la suya, vuelven a divergir."""
    from src.analysis import omni_analyzer, omni_caso
    assert omni_analyzer._fmt_p is lenguaje.fmt_p
    assert omni_analyzer._p is lenguaje.p_token
    assert omni_caso.probabilidad_en_palabras is lenguaje.probabilidad_en_palabras
    assert omni_caso._num is lenguaje.num
    assert omni_caso._ic is lenguaje.ic_texto


def test_p_nunca_sale_como_cero():
    assert lenguaje.fmt_p(0.0) == "<0.0001"
    assert lenguaje.p_token(3e-9) == "p<0.0001"
    assert lenguaje.p_token(0.0345) == "p=0.0345"


def test_pendiente_ancha_no_es_concluyente():
    assert lenguaje.pendiente_concluyente((-3.06, 5.25))[0] is False
    assert lenguaje.pendiente_concluyente((0.96, 1.05)) == (True, "")
    assert lenguaje.pendiente_concluyente(None) == (True, "")
    assert lenguaje.pendiente_concluyente(np.array([0.9, 1.1])) == (True, "")


# ---------------- Datos ----------------

def test_filas_completas_empareja_por_fila_y_cuenta_descartes():
    df = pd.DataFrame({"A": [1.0, np.nan, 3.0, 4.0, np.nan],
                       "B": [10.0, 20.0, np.nan, 40.0, np.nan]})
    completas, entrada = filas_completas(df, "A", "B")
    assert completas.index.tolist() == [0, 3]
    assert completas["B"].tolist() == [10.0, 40.0]
    # la fila 4 está vacía del todo: final de planilla, no par roto
    assert entrada.descartadas == 2
    assert entrada.n == 2 and entrada.columnas == ("A", "B")


def test_una_columna_repetida_entra_una_vez():
    df = pd.DataFrame({"A": [1.0, 2.0, 3.0]})
    completas, entrada = filas_completas(df, "A", "A")
    assert list(completas.columns) == ["A"]
    assert entrada.columnas == ("A",)


def test_columnas_faltantes_dice_cuales():
    df = pd.DataFrame({"A": [1.0]})
    assert columnas_faltantes(df, "A") is None
    assert "«Z»" in columnas_faltantes(df, "A", "Z")


# ---------------- Renderizador ----------------

def test_el_informe_trae_todas_las_partes():
    t = _texto(render_html(_completo()))
    for parte in ("Prueba — A vs B", "n = 19", "Sesgo", "0.0341", "-0.5100 a 0.5800",
                  "p<0.0001", "Bland-Altman paramétrico", "¿Las diferencias son normales?",
                  "Si hubiera dado al revés", "Cómo se lee", "Qué NO se puede concluir",
                  "Atención", "2 filas incompletas", "Fórmula", "LoA = d̄ ± 1,96·s",
                  "Referencias", "Bland JM, Altman DG"):
        assert parte in t, parte


def test_el_informe_no_dice_significativo():
    assert "significativ" not in render_html(_completo()).lower()


def test_el_informe_escapa_lo_que_escribe_el_usuario():
    res = _completo()
    res.titulo = "Método <b>A</b> & B"
    res.entrada = Entrada(columnas=("<script>",), n=3)
    html = render_html(res)
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "<b>A</b>" not in html


def test_un_rechazo_muestra_el_motivo_y_nada_mas():
    res = Resultado.rechazo("x", "Bland-Altman", "Se necesitan al menos 3 pares; hay 2.",
                            entrada=Entrada(("A", "B"), n=2, descartadas=1))
    t = _texto(render_html(res))
    assert "No se puede calcular: Se necesitan al menos 3 pares; hay 2." in t
    assert "1 fila incompleta" in t
    assert "Fórmula" not in t


def test_sin_descartes_no_hay_aviso():
    res = _completo()
    res.entrada = Entrada(("A", "B"), n=19)
    assert "incompleta" not in render_html(res)


# ---------------- Panel ----------------

@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_el_panel_muestra_un_resultado(qt_app, monkeypatch):
    """Mientras dura la migración, el dispatch acepta HTML o Resultado."""
    import matplotlib.pyplot as plt
    from src.ui.analysis_panel import AnalysisPanel

    def figura():
        fig, ax = plt.subplots()
        ax.plot([0, 1], [0, 1])
        return fig

    res = _completo()
    res.figuras = [Figura("Prueba", figura)]

    panel = AnalysisPanel()
    panel.set_data(pd.DataFrame({"A": [1.0, 2.0, 3.0], "B": [1.1, 2.1, 2.9]}))
    monkeypatch.setattr(panel, "_desc", lambda col: res)
    panel.combo_analysis.setCurrentText("Estadisticas descriptivas")
    panel._run()

    assert "Prueba — A vs B" in panel.txt_results.toPlainText()
    assert "LoA" in panel.txt_formula.toPlainText()
    assert panel.canvas is not None


def test_el_panel_muestra_un_rechazo_sin_figura(qt_app, monkeypatch):
    from src.ui.analysis_panel import AnalysisPanel

    panel = AnalysisPanel()
    panel.set_data(pd.DataFrame({"A": [1.0, 2.0, 3.0]}))
    monkeypatch.setattr(panel, "_desc",
                        lambda col: Resultado.rechazo("x", "X", "Todos los valores son iguales."))
    panel.combo_analysis.setCurrentText("Estadisticas descriptivas")
    panel._run()

    assert "Todos los valores son iguales." in panel.txt_results.toPlainText()
    assert panel.canvas is None
