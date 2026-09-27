"""La familia de validación migrada a `Resultado`: Passing-Bablok, Deming,
imprecisión desde duplicados, ICC y Bland-Altman múltiple.

Cada constructor muestra los números del core sin tocarlos (paridad). Donde el
número o el veredicto cambia a propósito, el test lo dice en su nombre:

- Passing-Bablok decide por los intervalos, y un intervalo ancho no concluye.
  El panel viejo declaraba «Métodos concordantes» con el IC de la pendiente y un
  intercepto menor que el 10 % de la media: ese 10 % no sale de ninguna norma
  (decisión 3 de docs/plans/2026-09-26-envoltura-resultado.md).
- Deming elige ponderar según la variabilidad (EP09c §6.2) y acepta λ.
- El CV de duplicados usa los métodos de MedCalc (DE intrasujeto, raíz
  cuadrática media, logarítmico). El panel mostraba DE(d)/(√2·media) con la DE
  centrada, que no es ninguno de los tres.

El contrato común (ficha, sin «significativo», p nunca impreso como cero) lo
aplica `test_bland_resultado.py::test_contrato` a todo `CONSTRUCTORES`.
"""
import os

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.core.agreement import (  # noqa: E402
    cv_duplicados as cv_core, deming_ponderado as dem_pond_core,
    deming_regression as dem_core, intraclass_correlation,
)
from src.core.bland_altman import bland_altman_analysis  # noqa: E402
from src.core.passing_bablok import passing_bablok as pb_core  # noqa: E402
from src.resultado.constructores import (  # noqa: E402
    bland_altman_multiple, cv_duplicados, deming, icc, passing_bablok,
)


def _valores(res):
    return {v.nombre: v for v in res.valores}


def _paso(res, texto):
    return next(s for s in res.supuestos if texto in s.pregunta)


def _hoja_sesgo():
    """B lee 8 % alto contra A, DE constante."""
    rng = np.random.default_rng(11)
    ref = rng.uniform(20, 200, 40)
    return pd.DataFrame({"A": ref, "B": ref * 1.08 + rng.normal(0, 3, 40)})


def _hoja_cv():
    rng = np.random.default_rng(1)
    ref = rng.uniform(5, 400, 60)
    return pd.DataFrame({"A": ref * (1 + rng.normal(0, 0.05, 60)),
                         "B": 1.05 * ref * (1 + rng.normal(0, 0.05, 60))})


# ---------------- Passing-Bablok ----------------

def test_passing_bablok_muestra_los_numeros_del_core():
    df = _hoja_sesgo()
    core = pb_core(df["A"].values, df["B"].values)
    v = _valores(passing_bablok(df, "A", "B"))
    assert v["Pendiente (B)"].texto() == f"{core['slope']:.4f}"
    assert v["Pendiente (B)"].texto_ic() == f"{core['ci_slope'][0]:.4f} a {core['ci_slope'][1]:.4f}"
    assert v["Intercepto (A)"].texto() == f"{core['intercept']:.4f}"
    assert v["DE residual (RSD)"].texto() == f"{core['se_residuals']:.4f}"
    assert v["r de Pearson"].texto() == f"{core['correlation_r']:.4f}"
    assert v["Media A"].texto() == f"{core['method1_mean']:.4f}"


def test_passing_bablok_detecta_el_error_de_escala_de_un_metodo_8_por_ciento_alto():
    res = passing_bablok(_hoja_sesgo(), "A", "B")
    assert _paso(res, "pendiente").respuesta == "Sí"
    assert "error de escala" in res.lectura


def test_passing_bablok_ya_no_usa_el_10_por_ciento_de_la_media():
    """Decisión 3: pendiente e intercepto con el 1 y el 0 en sus intervalos, y un
    intervalo de pendiente angosto. El panel viejo decía «Discordancia
    detectada» porque |intercepto| superaba el 10 % de la media."""
    rng = np.random.default_rng(6)
    x = rng.uniform(0.5, 3, 80)
    df = pd.DataFrame({"X": x, "Y": x + rng.normal(0, 0.3, 80)})
    core = pb_core(df["X"].values, df["Y"].values)
    assert abs(core["intercept"]) >= 0.1 * core["method1_mean"], "el caso que el 10 % marcaba"
    res = passing_bablok(df, "X", "Y")
    assert _paso(res, "pendiente").respuesta == "No se detectó"
    assert _paso(res, "intercepto").respuesta == "No se detectó"
    assert "no se aparta de la identidad" in res.lectura


def test_passing_bablok_con_intervalo_ancho_no_concluye():
    """El panel viejo decía «Métodos concordantes» con cualquier IC que incluyera
    el 1, por ancho que fuera."""
    rng = np.random.default_rng(3)
    x = rng.uniform(90, 110, 12)
    df = pd.DataFrame({"X": x, "Y": x + rng.normal(0, 3, 12)})
    res = passing_bablok(df, "X", "Y")
    paso = _paso(res, "pendiente")
    assert paso.respuesta == "No concluyente" and not paso.ok
    assert "demasiado ancho" in res.lectura
    assert _paso(res, "muestras suficientes").respuesta == "No"


def test_passing_bablok_informa_el_sesgo_en_los_cuartiles_del_comparativo():
    df = _hoja_sesgo()
    core = pb_core(df["A"].values, df["B"].values)
    v = _valores(passing_bablok(df, "A", "B"))
    mediana = float(np.percentile(df["A"], 50))
    clave = next(k for k in v if k.endswith("(P50)"))
    esperado = core["intercept"] + (core["slope"] - 1) * mediana
    assert v[clave].valor == pytest.approx(esperado)


# ---------------- Deming ----------------

def test_deming_con_de_constante_es_el_del_core_sin_ponderar():
    df = _hoja_sesgo()
    res = deming(df, "A", "B")
    core = dem_core(df["A"].values, df["B"].values, lambda_ratio=1.0)
    assert res.crudo["ponderado"] is False
    v = _valores(res)
    assert v["Pendiente"].texto() == f"{core['slope']:.4f}"
    assert v["Pendiente"].texto_ic() == f"{core['ci_slope'][0]:.4f} a {core['ci_slope'][1]:.4f}"
    assert v["R²"].texto() == f"{core['r2']:.4f}"


def test_deming_con_cv_constante_pondera_solo():
    df = _hoja_cv()
    res = deming(df, "A", "B")
    core = dem_pond_core(df["A"].values, df["B"].values, lambda_ratio=1.0)
    assert res.crudo["variabilidad"]["clase"] == "CV constante"
    assert res.crudo["ponderado"] is True
    assert _valores(res)["Pendiente"].valor == pytest.approx(core["slope"])
    assert "ponderado" in res.titulo


def test_deming_se_puede_forzar_sin_ponderar():
    res = deming(_hoja_cv(), "A", "B", {"tipo": "constante"})
    assert res.crudo["ponderado"] is False
    assert "a mano" in _paso(res, "dispersión").consecuencia


def test_deming_usa_el_lambda_declarado():
    df = _hoja_sesgo()
    res = deming(df, "A", "B", {"tipo": "constante", "lambda": 4.0})
    core = dem_core(df["A"].values, df["B"].values, lambda_ratio=4.0)
    assert _valores(res)["Pendiente"].valor == pytest.approx(core["slope"])
    assert "λ = 4" in _paso(res, "error de medición").respuesta


def test_deming_rechaza_un_lambda_que_no_es_positivo():
    res = deming(_hoja_sesgo(), "A", "B", {"lambda": -1})
    assert not res.ok and "λ" in res.error


def test_deming_con_dispersion_mixta_recomienda_passing_bablok():
    rng = np.random.default_rng(3)
    x = rng.uniform(1, 400, 120)
    sd = np.where(x < 100, 3.0, 0.03 * x)
    df = pd.DataFrame({"X": x + rng.normal(0, 1, 120) * sd, "Y": x + rng.normal(0, 1, 120) * sd})
    res = deming(df, "X", "Y")
    assert any("Passing-Bablok" in a for a in res.advertencias)


# ---------------- Imprecisión desde duplicados ----------------

def test_cv_duplicados_muestra_los_tres_metodos_de_medcalc():
    df = _hoja_cv()
    core = cv_core(df["A"].values, df["B"].values)
    v = _valores(cv_duplicados(df, "A", "B"))
    assert v["DE intrasujeto"].texto() == f"{core['de_intra']:.4f}"
    assert v["CV, raíz cuadrática media"].texto() == f"{core['cv_rms']:.2f}%"
    assert v["CV, método logarítmico"].texto() == f"{core['cv_log']:.2f}%"


def test_cv_duplicados_formulas_a_mano():
    x1 = np.array([10.0, 20.0, 30.0, 40.0])
    x2 = np.array([11.0, 19.0, 33.0, 38.0])
    r = cv_core(x1, x2)
    d, m = x1 - x2, (x1 + x2) / 2
    assert r["de_intra"] == pytest.approx(np.sqrt(np.sum(d ** 2) / 8))
    assert r["cv_rms"] == pytest.approx(100 * np.sqrt(np.sum((d / m) ** 2) / 8))
    assert r["cv_log"] == pytest.approx(100 * (np.exp(np.sqrt(np.sum(np.log(x1 / x2) ** 2) / 8)) - 1))


def test_cv_duplicados_cubre_el_cv_verdadero():
    """CV constante del 5 %: el de la raíz cuadrática media es insesgado y su IC
    (χ² con n grados de libertad, Bland 2006) cubre ~95 %."""
    rng = np.random.default_rng(0)
    cubre, estimados = 0, []
    for _ in range(600):
        mu = rng.uniform(10, 500, 30)
        r = cv_core(mu * (1 + rng.normal(0, 0.05, 30)), mu * (1 + rng.normal(0, 0.05, 30)))
        estimados.append(r["cv_rms"])
        cubre += r["ic_cv_rms"][0] <= 5 <= r["ic_cv_rms"][1]
    assert np.mean(estimados) == pytest.approx(5, abs=0.1)
    assert 0.92 <= cubre / 600 <= 0.98


def test_cv_duplicados_lee_la_cifra_que_corresponde():
    con_cv = cv_duplicados(_hoja_cv(), "A", "B")
    assert con_cv.crudo["variabilidad"]["clase"] == "CV constante"
    assert "CV de" in con_cv.lectura
    rng = np.random.default_rng(2)
    mu = rng.uniform(50, 150, 40)
    con_de = cv_duplicados(pd.DataFrame({"R1": mu + rng.normal(0, 3, 40),
                                         "R2": mu + rng.normal(0, 3, 40)}), "R1", "R2")
    assert con_de.crudo["variabilidad"]["clase"] == "DE constante"
    assert "DE de" in con_de.lectura


def test_cv_duplicados_avisa_si_las_replicas_estan_corridas():
    rng = np.random.default_rng(4)
    mu = rng.uniform(50, 150, 40)
    df = pd.DataFrame({"R1": mu + rng.normal(0, 2, 40), "R2": mu + 3 + rng.normal(0, 2, 40)})
    paso = _paso(cv_duplicados(df, "R1", "R2"), "primera y la segunda réplica")
    assert not paso.ok and "sobreestima" in paso.consecuencia


# ---------------- ICC ----------------

def test_el_icc_es_el_de_pingouin():
    df = _hoja_sesgo()
    datos = df[["A", "B"]].to_numpy()
    a = intraclass_correlation(datos, model="two-way-random")
    c = intraclass_correlation(datos, model="two-way-mixed")
    v = _valores(icc(df, "A", "B"))
    assert v["ICC(A,1) — acuerdo absoluto"].texto() == f"{a['icc']:.4f}"
    assert v["ICC(C,1) — consistencia"].texto() == f"{c['icc']:.4f}"


def test_el_icc_explica_por_que_el_de_acuerdo_queda_abajo():
    res = icc(_hoja_sesgo(), "A", "B")
    assert _paso(res, "sistemáticamente").respuesta == "Sí"
    assert "Koo y Li" in _paso(res, "fiable").consecuencia


def test_el_p_del_icc_nunca_sale_como_cero():
    assert _valores(icc(_hoja_sesgo(), "A", "B"))["p (ICC = 0)"].texto() == "<0.0001"


# ---------------- Bland-Altman múltiple ----------------

def test_bland_altman_multiple_es_cada_metodo_contra_la_referencia():
    rng = np.random.default_rng(1)
    ref = rng.uniform(50, 150, 40)
    df = pd.DataFrame({"Ref": ref, "M1": ref + rng.normal(2, 3, 40),
                       "M2": ref * 1.05 + rng.normal(0, 3, 40)})
    res = bland_altman_multiple(df, "Ref", ["M1", "M2"])
    v = _valores(res)
    for m in ("M1", "M2"):
        core = bland_altman_analysis(df[m].values, df["Ref"].values, reference="y")
        sesgo = v[f"{m} − Ref: sesgo"]
        assert sesgo.texto() == f"{core['mean_difference']:.4f}"
        assert v[f"{m} − Ref: límite superior"].texto_ic() == (
            f"{core['ci_upper'][0]:.4f} a {core['ci_upper'][1]:.4f}")


def test_bland_altman_multiple_sin_metodos_se_rechaza():
    res = bland_altman_multiple(_hoja_sesgo(), "A", [])
    assert not res.ok and "al menos un método" in res.error


# ---------------- Figuras ----------------

@pytest.mark.parametrize("constructor,args", [
    (passing_bablok, ("A", "B")), (deming, ("A", "B")),
    (bland_altman_multiple, ("A", ["B"])),
])
def test_las_figuras_se_dibujan(constructor, args):
    res = constructor(_hoja_sesgo(), *args)
    assert res.figuras
    for figura in res.figuras:
        fig = figura.dibujar()
        assert fig.axes, figura.titulo
        plt.close(fig)


# ---------------- El panel ----------------

@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("analisis", ["Passing-Bablok", "Deming regression", "CV duplicatas",
                                      "ICC", "Bland-Altman múltiple"])
def test_el_panel_los_muestra_como_resultado(qt_app, analisis):
    from src.ui.analysis_panel import AnalysisPanel
    panel = AnalysisPanel()
    panel.set_data(_hoja_sesgo())
    panel.combo_analysis.setCurrentText(analisis)
    panel.combo_col1.setCurrentText("A")
    panel.combo_col2.setCurrentText("B")
    panel._run()
    texto = panel.txt_results.toPlainText()
    assert "Qué se verificó y qué se decidió" in texto
    assert "Referencias" in texto
    assert "significativ" not in texto.lower()


def test_el_dialogo_de_deming_pide_ponderacion_y_lambda(qt_app):
    from src.ui.dialogs import DialogoAnalisis
    d = DialogoAnalisis("Deming regression", ["A", "B"])
    assert set(d.combos_opcion) == {"tipo"}
    assert set(d.inputs_parametro) == {"lambda"}
    d.inputs_parametro["lambda"].setText("0,5")
    assert d.seleccion()["parametros"]["lambda"] == "0,5"
