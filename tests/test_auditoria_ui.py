"""Qué columnas y qué filas llegan a cada análisis del panel — auditoría 2026-09.

K2: ANOVA/Kruskal tomaban cada columna numérica como un grupo.
K3: Fisher, McNemar, OR, RR, diagnóstico y LR leían las dos primeras filas como
    conteos; Chi² y Kappa tabulaban crudos.
K6: tamaño muestral y poder con valores fijos en el código.
K8: Random Forest informaba la exactitud sobre los datos de entrenamiento.
A9, A10, A12, M11, M13, M16 y la decisión 2 (sin «significativo»).

Se compara el número que muestra el panel con el de un oráculo aplicado a la
tabla o a los grupos armados a mano.
"""
import os
import re
from html import unescape

import numpy as np
import pandas as pd
import pytest
from scipy import stats

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def _panel(df):
    from src.ui.analysis_panel import AnalysisPanel
    p = AnalysisPanel()
    p.set_data(df)
    return p


def _texto(html):
    # Los análisis migrados devuelven un Resultado; los viejos, su HTML.
    if not isinstance(html, str):
        from src.resultado import render_html
        html = render_html(html)
    return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))).strip()


def _p_mostrado(texto, etiqueta="p"):
    m = re.search(rf"\b{etiqueta} ?[=<] ?([0-9.]+)", texto)
    return float(m.group(1))


# ------------------------------------------------------------------ K2
@pytest.fixture
def hoja_larga():
    rng = np.random.default_rng(1)
    return pd.DataFrame({
        "Valor": np.r_[rng.normal(100, 10, 20), rng.normal(100, 10, 20), rng.normal(100, 10, 20)],
        "Grupo": np.repeat([1, 2, 3], 20),
        "ID": np.arange(60)})


def test_la_anova_usa_respuesta_y_grupo_elegidos(qt_app, hoja_larga):
    t = _texto(_panel(hoja_larga)._anova("Valor", "Grupo", 0.05))
    esperado = stats.f_oneway(*[g["Valor"] for _, g in hoja_larga.groupby("Grupo")])
    assert f"{esperado.statistic:.4f}" in t
    assert "7460" not in t


def test_la_anova_rechaza_un_grupo_que_parece_una_medicion(qt_app, hoja_larga):
    t = _texto(_panel(hoja_larga)._anova("Valor", "ID", 0.05))
    assert "parece una medición" in t


def test_kruskal_usa_respuesta_y_grupo(qt_app, hoja_larga):
    t = _texto(_panel(hoja_larga)._kruskal("Valor", "Grupo"))
    esperado = stats.kruskal(*[g["Valor"] for _, g in hoja_larga.groupby("Grupo")])
    assert f"{esperado.statistic:.4f}" in t


def test_la_anova_avisa_y_usa_welch_con_varianzas_distintas(qt_app):
    rng = np.random.default_rng(5)
    df = pd.DataFrame({"v": np.r_[rng.normal(50, 1, 30), rng.normal(50, 8, 30), rng.normal(50, 20, 30)],
                       "g": np.repeat(["A", "B", "C"], 30)})
    t = _texto(_panel(df)._anova("v", "g", 0.05))
    assert "ANOVA de Welch" in t and "no supone varianzas iguales" in t


# ------------------------------------------------------------------ K3
@pytest.fixture
def crudos():
    rng = np.random.default_rng(2)
    prueba = rng.integers(0, 2, 80)
    oro = np.where(rng.random(80) < 0.85, prueba, 1 - prueba)
    return pd.DataFrame({"Prueba": prueba.astype(float), "Oro": oro.astype(float)})


def _tabla(df):
    """[[a, b], [c, d]] con 1 = positivo primero, filas = Prueba, columnas = Oro."""
    p, o = df["Prueba"], df["Oro"]
    return np.array([[np.sum((p == 1) & (o == 1)), np.sum((p == 1) & (o == 0))],
                     [np.sum((p == 0) & (o == 1)), np.sum((p == 0) & (o == 0))]])


def test_fisher_tabula_los_datos_crudos(qt_app, crudos):
    t = _texto(_panel(crudos)._fisher("Prueba", "Oro"))
    tabla = _tabla(crudos)
    or_ok, p_ok = stats.fisher_exact(tabla)
    assert f"{or_ok:.4f}" in t
    assert "p<0.0001" in t.replace(" ", "") if p_ok < 1e-4 else f"{p_ok:.4f}" in t
    assert "Tabla armada con 80 filas" in t


def test_una_tabla_de_conteos_ya_armada_se_reconoce_y_se_dice(qt_app):
    df = pd.DataFrame({"Enfermos": [34, 9], "Sanos": [3, 34]})
    t = _texto(_panel(df)._fisher("Enfermos", "Sanos"))
    assert "tabla de conteos ya armada" in t
    assert f"{stats.fisher_exact([[34, 3], [9, 34]])[0]:.4f}" in t


def test_la_prueba_diagnostica_cuenta_vp_fp_fn_vn(qt_app, crudos):
    t = _texto(_panel(crudos)._diag_test("Prueba", "Oro"))
    (a, b), (c, d) = _tabla(crudos)
    assert f"Sensibilidad {a / (a + c):.4f}" in t
    assert f"Especificidad {d / (b + d):.4f}" in t


def test_mcnemar_usa_los_pares_discordantes(qt_app, crudos):
    from statsmodels.stats.contingency_tables import mcnemar
    t = _texto(_panel(crudos)._mcnemar("Prueba", "Oro"))
    tabla = _tabla(crudos)
    b, c = tabla[0, 1], tabla[1, 0]
    assert f"Discordantes b {b}" in t and f"Discordantes c {c}" in t
    esperado = mcnemar(tabla, exact=(b + c < 25)).pvalue
    assert _p_mostrado(t) == pytest.approx(esperado, abs=5e-5)


def test_odds_ratio_y_riesgo_relativo_sobre_crudos(qt_app, crudos):
    (a, b), (c, d) = _tabla(crudos)
    p = _panel(crudos)
    assert f"{(a * d) / (b * c):.4f}" in _texto(p._odds_ratio("Prueba", "Oro"))
    assert f"{(a / (a + b)) / (c / (c + d)):.4f}" in _texto(p._riesgo_relativo("Prueba", "Oro"))


def test_una_variable_con_tres_valores_no_arma_tabla_2x2(qt_app):
    df = pd.DataFrame({"x": [0, 1, 2, 0, 1, 2], "y": [0, 1, 0, 1, 0, 1]})
    assert "exactamente 2" in _texto(_panel(df)._fisher("x", "y"))


def test_chi_cuadrado_sobre_las_variables_elegidas(qt_app):
    rng = np.random.default_rng(3)
    df = pd.DataFrame({"a": rng.choice(["x", "y", "z"], 90), "b": rng.choice(["p", "q"], 90),
                       "otra": rng.normal(0, 1, 90)})
    t = _texto(_panel(df)._chi2("a", "b"))
    esperado = stats.chi2_contingency(pd.crosstab(df["a"], df["b"]).values)
    assert f"{esperado.statistic:.4f}" in t


def test_kappa_sobre_las_dos_clasificaciones(qt_app):
    from sklearn.metrics import cohen_kappa_score
    rng = np.random.default_rng(4)
    a = rng.integers(1, 4, 60)
    b = np.where(rng.random(60) < 0.7, a, rng.integers(1, 4, 60))
    t = _texto(_panel(pd.DataFrame({"A": a, "B": b}))._kappa("A", "B"))
    assert f"Kappa {cohen_kappa_score(a, b):.4f}" in t and "IC 95%" in t


# ------------------------------------------------------------------ K6 / A10
def test_el_tamano_muestral_usa_los_parametros_del_dialogo(qt_app):
    from src.core.sample_size import sample_size_mean
    p = _panel(pd.DataFrame({"x": [1.0]}))
    p.parametros = {"delta": "2", "sd": "4", "alpha": "0,05", "poder": "0.9"}
    t = _texto(p._ss_mean())
    assert f"n necesario {sample_size_mean(2, 4, 0.05, 0.9)['n_per_group']}" in t
    assert "valores de ejemplo" not in t


def test_sin_dialogo_el_tamano_muestral_dice_que_es_un_ejemplo(qt_app):
    t = _texto(_panel(pd.DataFrame({"x": [1.0]}))._ss_mean())
    assert "valores de ejemplo" in t


def test_un_parametro_que_no_es_numero_se_rechaza_con_su_nombre(qt_app):
    p = _panel(pd.DataFrame({"x": [1.0]}))
    p.parametros = {"delta": "dos"}
    assert "Diferencia a detectar" in _texto(p._ss_mean())


def test_el_poder_para_dos_grupos_es_el_de_statsmodels(qt_app):
    from statsmodels.stats.power import TTestIndPower
    p = _panel(pd.DataFrame({"x": [1.0]}))
    p.parametros = {"n": "30", "delta": "5", "sd": "10", "alpha": "0.05"}
    p.opciones_metodo = {"diseno": "dos"}
    esperado = TTestIndPower().power(effect_size=0.5, nobs1=30, alpha=0.05)
    assert f"{esperado:.1%}" in _texto(p._power())


def test_la_calculadora_de_2_medias_no_lee_una_hoja_de_datos(qt_app):
    """Antes leía seis celdas de la primera columna (y rechazaba una hoja de
    datos); desde el paso 4 toma los seis números del diálogo y la hoja no entra."""
    p = _panel(pd.DataFrame({"Glucosa": np.random.default_rng(0).normal(95, 12, 40)}))
    t = _texto(p._comparar_medias())
    assert "Glucosa" not in t and "valores de ejemplo" in t


# ------------------------------------------------------------------ K8
def test_random_forest_informa_la_validacion_cruzada(qt_app):
    rng = np.random.default_rng(0)
    df = pd.DataFrame(rng.normal(0, 1, (80, 5)), columns=list("abcde"))
    df["clase"] = rng.integers(0, 2, 80)
    t = _texto(_panel(df)._rf_class("clase"))
    cv = float(re.search(r"validación cruzada \(k=\d+\) ([0-9.]+)", t).group(1))
    assert cv < 0.75          # ruido puro: cerca de 0,5; la de entrenamiento daba 0,95
    assert "optimista" in t


# ------------------------------------------------------------------ A9
def test_la_roc_da_el_ic_del_auc_por_delong(qt_app):
    rng = np.random.default_rng(3)
    df = pd.DataFrame({"S": np.r_[rng.normal(10, 2, 50), rng.normal(6, 2, 50)],
                       "L": np.r_[np.ones(50), np.zeros(50)]})
    t = _texto(_panel(df)._roc("S", "L"))
    assert "EE (DeLong)" in t and "IC 95% del AUC" in t


def test_una_roc_invertida_no_se_llama_pobre(qt_app):
    rng = np.random.default_rng(3)
    df = pd.DataFrame({"S": np.r_[rng.normal(10, 2, 50), rng.normal(6, 2, 50)],
                       "L": np.r_[np.zeros(50), np.ones(50)]})
    t = _texto(_panel(df)._roc("S", "L"))
    assert "invertida" in t and "pobre" not in t.lower()


def test_el_ee_de_delong_se_parece_al_bootstrap():
    from sklearn.metrics import roc_auc_score
    from src.core.roc import auc_delong
    rng = np.random.default_rng(8)
    y = np.r_[np.ones(60), np.zeros(80)]
    s = np.r_[rng.normal(1, 1, 60), rng.normal(0, 1, 80)]
    r = auc_delong(y, s)
    assert r["auc"] == pytest.approx(roc_auc_score(y, s))
    boot = []
    for _ in range(1500):
        i = rng.integers(0, 140, 140)
        if len(set(y[i])) == 2:
            boot.append(roc_auc_score(y[i], s[i]))
    assert r["se"] == pytest.approx(np.std(boot), rel=0.12)


# ------------------------------------------------------------------ A12 / M16 / M11
def test_el_mountain_plot_es_de_las_diferencias_entre_dos_metodos(qt_app):
    rng = np.random.default_rng(0)
    a = rng.normal(100, 10, 60)
    t = _texto(_panel(pd.DataFrame({"A": a, "B": a - 2 + rng.normal(0, 1, 60)}))._run_mountain("A", "B"))
    assert "Mediana de las diferencias" in t
    assert f"{np.median(a - (a - 2 + np.random.default_rng(0).normal(0, 1, 60)))}"  # noqa


def test_bland_altman_multiple_compara_cada_metodo_contra_la_referencia(qt_app):
    from src.core.bland_altman import bland_altman_analysis
    rng = np.random.default_rng(1)
    ref = rng.uniform(50, 150, 40)
    df = pd.DataFrame({"Ref": ref, "M1": ref + rng.normal(2, 3, 40), "M2": ref * 1.05 + rng.normal(0, 3, 40)})
    t = _texto(_panel(df)._run_bland_multi("Ref"))
    esperado = bland_altman_analysis(df["M1"].values, df["Ref"].values, reference="y")
    assert f"{esperado['mean_difference']:.4f}" in t and f"{esperado['ci_upper'][1]:.4f}" in t
    assert "M1 vs M2" not in t


def test_el_icc_es_el_de_dos_vias_acuerdo_absoluto(qt_app):
    import pingouin as pg
    rng = np.random.default_rng(2)
    v = rng.normal(100, 15, 30)
    df = pd.DataFrame({"A": v + rng.normal(0, 4, 30), "B": v + 6 + rng.normal(0, 4, 30)})
    largo = pd.DataFrame({"s": np.tile(np.arange(30), 2), "r": np.repeat(["A", "B"], 30),
                          "y": np.r_[df["A"], df["B"]]})
    icc = pg.intraclass_corr(data=largo, targets="s", raters="r", ratings="y")
    esperado = float(icc.loc[icc["Type"] == "ICC(A,1)", "ICC"].iloc[0])
    assert f"ICC(A,1) — acuerdo absoluto {esperado:.4f}" in _texto(_panel(df)._icc("A", "B"))


# ------------------------------------------------------------------ listas de columnas
def test_friedman_usa_las_columnas_tildadas(qt_app):
    rng = np.random.default_rng(4)
    base = rng.normal(100, 10, 30)
    df = pd.DataFrame({"C1": base, "C2": base + 2 + rng.normal(0, 1, 30),
                       "C3": base + 4 + rng.normal(0, 1, 30), "Edad": rng.integers(20, 80, 30)})
    p = _panel(df)
    p.columnas_elegidas = ["C1", "C2", "C3"]
    t = _texto(p._friedman())
    assert f"{stats.friedmanchisquare(df['C1'], df['C2'], df['C3']).statistic:.4f}" in t
    assert "Columnas usadas: C1, C2, C3" in t


def test_sin_dialogo_el_informe_nombra_todas_las_columnas_que_entraron(qt_app):
    rng = np.random.default_rng(4)
    df = pd.DataFrame({"C1": rng.normal(0, 1, 20), "C2": rng.normal(0, 1, 20),
                       "C3": rng.normal(0, 1, 20), "Edad": rng.integers(20, 80, 20)})
    t = _texto(_panel(df)._friedman())
    assert "todas las columnas numéricas de la hoja: C1, C2, C3, Edad" in t


def test_cambiar_de_analisis_limpia_lo_que_dejo_el_dialogo(qt_app):
    p = _panel(pd.DataFrame({"x": [1.0, 2.0]}))
    p.columnas_elegidas, p.parametros, p.opciones_metodo = ["x"], {"delta": "3"}, {"a": 1}
    p.combo_analysis.setCurrentText("Friedman")
    p.combo_analysis.setCurrentText("Cronbach alfa")
    assert p.columnas_elegidas is None and p.parametros == {} and p.opciones_metodo == {}


# ------------------------------------------------------------------ decisión 2 y M13
def test_ningun_analisis_dice_significativo(qt_app):
    """Se corren los 76 análisis sobre una hoja de ejemplo y se lee cada informe."""
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"A": rng.normal(10, 2, 40), "B": rng.normal(11, 2, 40),
                       "C": rng.normal(9, 3, 40), "bin01": rng.integers(0, 2, 40).astype(float),
                       "grp": rng.integers(0, 3, 40).astype(float), "pos": rng.uniform(1, 5, 40)})
    p = _panel(df)
    encontrados = []
    for i in range(p.combo_analysis.count()):
        nombre = p.combo_analysis.itemText(i)
        p.combo_analysis.setCurrentText(nombre)
        p.combo_col1.setCurrentText("A")
        p.combo_col2.setCurrentText("B")
        p.combo_col3.setCurrentText("bin01")
        p._run()
        if "significativ" in p.txt_results.toPlainText().lower():
            encontrados.append(nombre)
    assert encontrados == []


def test_shapiro_no_afirma_que_los_datos_son_normales(qt_app):
    t = _texto(_panel(pd.DataFrame({"x": np.random.default_rng(0).normal(0, 1, 30)}))._shapiro("x"))
    assert "Es normal" not in t and "no prueba que sea normal" in t
