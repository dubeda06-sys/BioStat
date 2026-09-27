"""Bland-Altman migrado a `Resultado`: los números del core, más el CCC.

El informe viejo imprimía los números del core con 4 decimales (el sesgo % con
2). Estos tests comparan cada `Valor` contra `bland_altman_analysis` en las
nueve combinaciones de límites × eje, con diferencias normales y sin ellas.

Desde la auditoría del 26 sep (G5) la resta es candidato − referencia cuando se
declara una (CLSI EP09c, tabla 1), así que el core se llama con el par ya
orientado; la escala se fija en unidades para comparar número contra número (la
elección automática de escala tiene sus propios tests). Los tests de contrato
recorren todos los constructores migrados (`CONSTRUCTORES`), no solo este.
"""
import os
import re
from html import unescape

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.core.bland_altman import bland_altman_analysis, concordance_correlation  # noqa: E402
from src.resultado import render_html  # noqa: E402
from src.resultado.citas import ficha  # noqa: E402
from src.resultado.constructores import CONSTRUCTORES, bland_altman  # noqa: E402
from src.resultado.lenguaje import p_token  # noqa: E402

MODOS = ("auto", "parametrico", "no_parametrico")
EJES = ("promedio", "x", "y")


def _texto(res):
    return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", render_html(res)))).strip()


def _hoja_normal():
    """Un método que lee 8 % alto: diferencias normales y sesgo proporcional."""
    rng = np.random.default_rng(11)
    ref = rng.uniform(20, 200, 40)
    return pd.DataFrame({"A": ref, "B": ref * 1.08 + rng.normal(0, 3, 40)})


def _hoja_asimetrica():
    """Diferencias con cola: Shapiro-Wilk las rechaza."""
    rng = np.random.default_rng(5)
    a = rng.uniform(50, 150, 60)
    return pd.DataFrame({"A": a, "B": a + rng.exponential(4, 60) - 2})


def _valores(res):
    return {v.nombre: v for v in res.valores}


@pytest.mark.parametrize("hoja", [_hoja_normal, _hoja_asimetrica], ids=["normal", "asimetrica"])
@pytest.mark.parametrize("eje", EJES)
@pytest.mark.parametrize("modo", MODOS)
def test_los_numeros_son_los_del_core(hoja, modo, eje):
    df = hoja()
    referencia = eje if eje in ("x", "y") else None
    # Candidato − referencia: con A de referencia, la resta es B − A.
    cand, comp = ("B", "A") if eje == "x" else ("A", "B")
    core = bland_altman_analysis(df[cand].values, df[comp].values,
                                 reference="y" if referencia else None)
    res = bland_altman(df, "A", "B", {"limites": modo, "referencia": eje,
                                      "escala": "unidades"})
    v = _valores(res)
    medias = {cand: core["mean_method1"], comp: core["mean_method2"]}

    elegido = modo
    if modo == "auto":
        elegido = "parametrico" if core["normal_diffs"] in (True, None) else "no_parametrico"

    assert res.ok and res.entrada.n == core["n"]
    assert v["Media A"].texto() == f"{medias['A']:.4f}"
    assert v["Media B"].texto() == f"{medias['B']:.4f}"
    assert v["Sesgo %"].texto() == f"{core['bias_pct']:.2f}%"
    assert v["DE de las diferencias"].texto() == f"{core['sd_difference']:.4f}"

    if elegido == "parametrico":
        rotulo = "Límites de acuerdo (± 1,96·DE)"
        sesgo = v["Sesgo (media de las diferencias)"]
        assert sesgo.texto() == f"{core['mean_difference']:.4f}"
        assert sesgo.texto_ic() == f"{core['ci_mean'][0]:.4f} a {core['ci_mean'][1]:.4f}"
        sup, inf = v[f"{rotulo} — superior"], v[f"{rotulo} — inferior"]
        assert sup.texto() == f"{core['loa_upper']:.4f}"
        assert inf.texto() == f"{core['loa_lower']:.4f}"
        assert sup.texto_ic() == f"{core['ci_upper'][0]:.4f} a {core['ci_upper'][1]:.4f}"
        assert inf.texto_ic() == f"{core['ci_lower'][0]:.4f} a {core['ci_lower'][1]:.4f}"
    else:
        rotulo = "Límites de acuerdo (percentiles 2,5 y 97,5)"
        sesgo = v["Sesgo (mediana de las diferencias)"]
        assert sesgo.texto() == f"{np.median(core['diffs']):.4f}"
        assert sesgo.texto_ic() == ""
        assert v[f"{rotulo} — superior"].texto() == f"{core['loa_np_upper']:.4f}"
        assert v[f"{rotulo} — inferior"].texto() == f"{core['loa_np_lower']:.4f}"

    prom = v["Pendiente contra el promedio"]
    assert prom.texto() == f"{core['slope_vs_mean']['slope']:.4f}"
    assert p_token(core["slope_vs_mean"]["p"]) in prom.nota
    if referencia:
        nombre = {"x": "A", "y": "B"}[eje]
        ref = v[f"Pendiente contra {nombre} (referencia)"]
        assert ref.texto() == f"{core['slope_vs_reference']['slope']:.4f}"
    else:
        assert not any("(referencia)" in nombre for nombre in v)


def test_el_ccc_es_el_del_core():
    df = _hoja_normal()
    ccc = concordance_correlation(df["A"].values, df["B"].values)
    v = _valores(bland_altman(df, "A", "B"))
    assert v["CCC de Lin (ρc)"].texto() == f"{ccc['ccc']:.4f}"
    assert v["CCC de Lin (ρc)"].texto_ic() == f"{ccc['ci_low']:.4f} a {ccc['ci_high']:.4f}"
    assert ccc["strength"].lower() in v["CCC de Lin (ρc)"].nota
    assert v["Precisión: ρ de Pearson"].texto() == f"{ccc['rho']:.4f}"
    assert v["Veracidad: Cb"].texto() == f"{ccc['cb']:.4f}"


def test_el_paso_del_ccc_no_niega_el_sesgo_que_muestra_la_tabla():
    """Un método que lee 8 % alto, con concentraciones de 20 a 200: ρ y Cb quedan
    cerca de 1 porque Cb mide el corrimiento frente a la dispersión de la
    muestra. El paso decía «ni corrimiento apreciable» debajo de una tabla con
    un sesgo de −8 %: el informe se contradecía a sí mismo."""
    res = bland_altman(_hoja_normal(), "A", "B")
    assert abs(_valores(res)["Sesgo %"].valor) > 5
    paso = next(s for s in res.supuestos if "cuánto concuerdan" in s.pregunta)
    assert "ni corrimiento apreciable" not in paso.consecuencia
    assert "límites de acuerdo" in paso.consecuencia


def test_trae_el_grafico_de_diferencias_y_el_del_ccc():
    import matplotlib.pyplot as plt
    res = bland_altman(_hoja_normal(), "A", "B")
    assert [f.titulo for f in res.figuras] == ["Bland-Altman", "CCC de Lin descompuesto"]
    for figura in res.figuras:
        fig = figura.dibujar()
        assert fig.axes, figura.titulo
        plt.close(fig)


def test_sin_ccc_calculable_avisa_y_no_dibuja_su_grafico():
    """Una columna constante deja al CCC sin definición; el Bland-Altman sigue."""
    df = pd.DataFrame({"A": np.linspace(10, 50, 20), "B": np.full(20, 30.0)})
    res = bland_altman(df, "A", "B")
    assert res.ok
    assert any("CCC de Lin" in a for a in res.advertencias)
    assert [f.titulo for f in res.figuras] == ["Bland-Altman"]
    assert "CCC de Lin (ρc)" not in _valores(res)


def test_dos_metodos_identicos_no_rompen_nada():
    df = pd.DataFrame({"A": np.linspace(10, 50, 20)})
    df["B"] = df["A"]
    res = bland_altman(df, "A", "B")
    assert res.ok
    t = _texto(res)
    assert "No evaluable" in t          # Shapiro sin varianza en las diferencias
    assert "IC del CCC no definido" in t


def test_la_referencia_declarada_manda_en_la_pendiente():
    """Con referencia, el paso del sesgo proporcional mide contra ella."""
    res = bland_altman(_hoja_normal(), "A", "B", {"referencia": "x"})
    paso = next(s for s in res.supuestos if "sesgo proporcional" in s.pregunta)
    assert paso.medicion.startswith("pendiente contra A")
    clasico = bland_altman(_hoja_normal(), "A", "B")
    paso = next(s for s in clasico.supuestos if "sesgo proporcional" in s.pregunta)
    assert paso.medicion.startswith("pendiente contra el promedio")


def test_un_metodo_que_lee_8_por_ciento_alto_tiene_sesgo_proporcional():
    res = bland_altman(_hoja_normal(), "A", "B", {"referencia": "x"})
    paso = next(s for s in res.supuestos if "sesgo proporcional" in s.pregunta)
    assert paso.respuesta == "Sí" and paso.ok is False


def test_si_los_ejes_no_concluyen_lo_mismo_lo_dice():
    """Método en prueba = referencia + ruido, sin sesgo proporcional real: contra
    el promedio el ruido aparece en los dos ejes y puede fabricar una pendiente."""
    for semilla in range(200):
        rng = np.random.default_rng(semilla)
        ref = rng.uniform(80, 120, 15)
        df = pd.DataFrame({"R": ref, "P": ref + rng.normal(0, 8, 15)})
        core = bland_altman_analysis(df["R"].values, df["P"].values, reference="x")
        lo_m, hi_m = core["slope_vs_mean"]["ci"]
        lo_r, hi_r = core["slope_vs_reference"]["ci"]
        if (lo_m > 0 or hi_m < 0) != (lo_r > 0 or hi_r < 0):
            break
    else:
        pytest.skip("no apareció un caso de ejes en desacuerdo en 200 semillas")
    res = bland_altman(df, "R", "P", {"referencia": "x"})
    assert any("no concluye lo mismo" in a for a in res.advertencias)


# ---------------- Rechazos ----------------

def test_columna_inexistente():
    res = bland_altman(_hoja_normal(), "A", "Z")
    assert not res.ok and "«Z»" in res.error


def test_menos_de_tres_pares_trae_el_motivo_del_core():
    df = pd.DataFrame({"A": [1.0, 2.0, np.nan, 4.0], "B": [1.1, np.nan, 3.0, 4.2]})
    res = bland_altman(df, "A", "B")
    assert not res.ok
    assert "al menos 3" in res.error
    assert res.entrada.descartadas == 2


# ---------------- Contrato de todo constructor migrado ----------------

# Los que no reciben un par de columnas: EP15 toma una lista de corridas.
_LLAMADAS = {"precision_ep15": lambda f, df: f(df, ["A", "B"])}


@pytest.mark.parametrize("analisis", sorted(CONSTRUCTORES))
def test_contrato(analisis):
    llamar = _LLAMADAS.get(analisis, lambda f, df: f(df, "A", "B"))
    res = llamar(CONSTRUCTORES[analisis], _hoja_normal())
    assert res.ok, res.error
    f = ficha(analisis)
    assert f.formula and f.citas, "todo análisis migrado lleva fórmula y cita"
    assert res.formula == f.formula and len(res.citas) == len(f.citas)
    html = render_html(res)
    t = _texto(res)
    assert "significativ" not in html.lower()
    assert not re.search(r"p=0\.0+\b", t), "un p no sale como cero"
    assert "Fórmula" in t and "Referencias" in t
    assert res.lectura and res.matiz, "qué dice y qué NO se puede concluir"
    for s in res.supuestos:
        assert s.pregunta and s.medicion and s.respuesta and s.consecuencia


# ---------------- Panel e informe ----------------

@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _correr_en_panel(df):
    from src.ui.analysis_panel import AnalysisPanel
    panel = AnalysisPanel()
    panel.set_data(df)
    panel.combo_analysis.setCurrentText("Bland-Altman")
    panel.combo_col1.setCurrentText("A")
    panel.combo_col2.setCurrentText("B")
    panel._run()
    return panel


def test_el_panel_apila_los_dos_graficos(qt_app):
    from src.ui.grafico_editable import GraficoEditable
    panel = _correr_en_panel(_hoja_normal())
    graficos = panel.canvas.findChildren(GraficoEditable)
    assert len(graficos) == 2
    assert "CCC de Lin" in panel.txt_results.toPlainText()
    assert "LoA" in panel.txt_formula.toPlainText()


def test_la_ventana_de_informe_se_lleva_los_dos_graficos(qt_app):
    from src.ui import report_window
    from src.ui.grafico_editable import GraficoEditable
    panel = _correr_en_panel(_hoja_normal())
    ventana = report_window.abrir("Bland-Altman", panel.txt_results.toHtml(),
                                  panel.tomar_grafico())
    try:
        assert len(ventana.findChildren(GraficoEditable)) == 2
        assert panel.canvas is None
        assert "Referencias" in ventana.txt.toPlainText()
    finally:
        report_window.cerrar_todas()


# ---------------- G5: orientación y escala ----------------

def test_g5_con_referencia_la_resta_es_candidato_menos_referencia():
    """G5: con la Variable 1 de referencia, la resta seguía siendo V1 − V2 y un
    método que lee 8 % alto salía con sesgo negativo."""
    df = _hoja_normal()   # B lee 8 % alto contra A
    res = bland_altman(df, "A", "B", {"referencia": "x", "escala": "unidades"})
    v = _valores(res)
    assert v["Sesgo (media de las diferencias)"].valor > 0
    assert "B − A" in v["Sesgo (media de las diferencias)"].nota
    assert 6 < v["Sesgo %"].valor < 10, "en % de la referencia"
    assert res.crudo["diferencia"] == "B − A"


def test_g5_el_sesgo_porcentual_es_sobre_la_referencia():
    df = _hoja_normal()
    res = bland_altman(df, "A", "B", {"referencia": "x", "escala": "unidades"})
    v = _valores(res)
    esperado = (df["B"] - df["A"]).mean() / df["A"].mean() * 100
    assert v["Sesgo %"].valor == pytest.approx(esperado)


def _hoja_cv():
    rng = np.random.default_rng(1)
    ref = rng.uniform(10, 400, 60)
    return pd.DataFrame({"Ref": ref * (1 + rng.normal(0, 0.04, 60)),
                         "Nuevo": 1.1 * ref * (1 + rng.normal(0, 0.04, 60))})


def test_g5_con_cv_constante_la_escala_automatica_es_porcentaje():
    res = bland_altman(_hoja_cv(), "Ref", "Nuevo", {"referencia": "x"})
    assert res.crudo["variabilidad"]["clase"] == "CV constante"
    assert res.crudo["bland_altman"]["escala"] == "porcentaje"
    v = _valores(res)
    sesgo = v.get("Sesgo (media de las diferencias)") or v["Sesgo (mediana de las diferencias)"]
    assert sesgo.texto().endswith("%")
    assert 7 < sesgo.valor < 13
    assert "Sesgo %" not in v, "en porcentaje el sesgo ya es el sesgo %"
    paso = res.supuestos[0]
    assert "dispersión" in paso.pregunta and "CV constante" in paso.respuesta


def test_g5_la_escala_se_puede_forzar_y_el_paso_lo_dice():
    res = bland_altman(_hoja_cv(), "Ref", "Nuevo", {"referencia": "x", "escala": "unidades"})
    assert res.crudo["bland_altman"]["escala"] == "unidades"
    paso = res.supuestos[0]
    assert "a mano" in paso.consecuencia
    assert "porcentaje" in paso.alternativa


def test_g5_porcentaje_con_ceros_se_rechaza_con_motivo():
    df = _hoja_cv()
    df.loc[0, "Ref"] = 0.0
    res = bland_altman(df, "Ref", "Nuevo", {"referencia": "x", "escala": "porcentaje"})
    assert not res.ok
    assert "positivos" in res.error
