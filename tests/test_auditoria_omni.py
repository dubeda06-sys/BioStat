"""Arreglos del Omnianálisis — auditoría del 26 sep (docs/AUDITORIA-2026-09.md).

K1, K7, K10, A2, A8, A14, A15, A16, M8, M14 y M15. Cada test lleva en el
nombre la propiedad que el motor violaba. Los oráculos son independientes:
scipy (Kruskal-Wallis, permutación a mano), scipy.odr, pingouin, y el texto de
CLSI EP09c leído del PDF (tabla 1, §5.4, §6.2, apéndices B y K1).
"""
import os

import numpy as np
import pandas as pd
import pytest
from scipy import odr, stats

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.analysis import omni_arbol  # noqa: E402
from src.analysis.omni_analyzer import (  # noqa: E402
    CATEGORICAL_ORDINAL, NUMERIC_DISCRETE, _classify_column, _compare_groups,
    _decidir, concordance_analysis, run_omnianalysis,
)
from src.analysis.omni_auditoria import DESCARTADO, EJECUTADO, auditar  # noqa: E402
from src.analysis.omni_caso import casos  # noqa: E402
from src.analysis.omni_catalogo import ENSAYOS, POR_ID  # noqa: E402
from src.analysis.omni_config import DEFAULT_CONFIG as CFG  # noqa: E402
from src.analysis.omni_plots import bland_altman_figure  # noqa: E402


def _bloque(report, tipo):
    return next(b for b in report["blocks"] if b.get("tipo") == tipo)


def _concordancia(df, par, referencia=None):
    refs = {par: referencia} if referencia else None
    rep = run_omnianalysis(df, list(df.columns), confirmed_comparisons=[par],
                           referencias=refs)
    return rep, _bloque(rep, "concordancia")


def _bloque_vacio():
    return {"titulo": "Bivariado — y × g", "traza": [], "advertencias": [],
            "resultados": {}, "conclusion": "", "pruebas": [], "ensayos": []}


# ------------------------------------------------------------------ K1
@pytest.fixture(scope="module")
def mas_diez_por_ciento():
    """Un método que lee 10 % alto. La referencia se llama `Z_ref`, así que en
    orden alfabético queda SEGUNDA: es el caso que el motor invertía."""
    rng = np.random.default_rng(1)
    ref = rng.uniform(20, 200, 60)
    return pd.DataFrame({"A_prueba": ref * 1.10 + rng.normal(0, 1.5, 60),
                         "Z_ref": ref + rng.normal(0, 1.5, 60)})


def test_k1_el_sesgo_en_niveles_tiene_el_signo_del_metodo_en_prueba(mas_diez_por_ciento):
    """K1: con la referencia en la segunda columna, +10 % salía −9,3 %."""
    _, b = _concordancia(mas_diez_por_ciento, ("A_prueba", "Z_ref"), "Z_ref")
    niveles = b["resultados"]["sesgo_en_niveles"]
    assert all(8 < s["sesgo_pct"] < 12 for s in niveles), niveles
    assert b["resultados"]["bland_altman"]["sesgo"] > 0


def test_k1_x_es_la_referencia_e_y_el_candidato(mas_diez_por_ciento):
    """EP09c, tabla 1: X = comparativo, Y = candidato; d = Y − X."""
    _, b = _concordancia(mas_diez_por_ciento, ("A_prueba", "Z_ref"), "Z_ref")
    orient = b["resultados"]["orientacion"]
    assert (orient["x"], orient["y"]) == ("Z_ref", "A_prueba")
    assert orient["diferencia"] == "A_prueba − Z_ref"
    plot = b["resultados"]["_plot"]
    assert plot["nombre_x"] == "Z_ref"
    # Los niveles de decisión son concentraciones de la REFERENCIA.
    ref = mas_diez_por_ciento["Z_ref"].to_numpy()
    assert b["resultados"]["sesgo_en_niveles"][1]["nivel"] == pytest.approx(
        np.percentile(ref, 50), abs=1e-3)


def test_k1_el_orden_del_par_no_cambia_nada(mas_diez_por_ciento):
    _, derecho = _concordancia(mas_diez_por_ciento, ("A_prueba", "Z_ref"), "Z_ref")
    _, revez = _concordancia(mas_diez_por_ciento, ("Z_ref", "A_prueba"), "Z_ref")
    assert derecho["resultados"]["sesgo_en_niveles"] == revez["resultados"]["sesgo_en_niveles"]
    assert derecho["resultados"]["regresion"] == revez["resultados"]["regresion"]


def test_k1_sin_referencia_el_informe_dice_que_resta_hizo(mas_diez_por_ciento):
    _, b = _concordancia(mas_diez_por_ciento, ("A_prueba", "Z_ref"))
    assert b["resultados"]["orientacion"]["referencia_declarada"] is False
    aviso = " ".join(b["advertencias"])
    assert "Ninguna de las dos columnas se declaró método de referencia" in aviso
    assert "Z_ref − A_prueba" in aviso, "sin referencia, X es la primera en orden alfabético"


def test_k1_el_grafico_usa_la_misma_resta_que_el_motor(mas_diez_por_ciento):
    """El gráfico dibujaba Y − X y el motor informaba X − Y: la línea de sesgo
    quedaba del lado opuesto a los puntos."""
    _, b = _concordancia(mas_diez_por_ciento, ("A_prueba", "Z_ref"), "Z_ref")
    plot = b["resultados"]["_plot"]
    fig = bland_altman_figure(plot)
    try:
        puntos = fig.axes[0].collections[0].get_offsets()
        assert np.mean(puntos[:, 1]) == pytest.approx(plot["sesgo"], abs=1e-3)
        # Con referencia declarada, el eje X es la referencia (Krouwer).
        assert np.allclose(np.sort(puntos[:, 0]), np.sort(plot["x"]))
    finally:
        plt.close(fig)


# ------------------------------------------------------------------ A2
def _clase(x, y, referencia="X"):
    b = concordance_analysis("X", pd.Series(x), "Y", pd.Series(y), CFG, referencia=referencia)
    return b


def test_a2_cv_constante_se_reconoce_y_va_a_deming_ponderado():
    """A2: con CV constante y sin sesgo, el motor decía «homocedástico» 190/200."""
    rng = np.random.default_rng(0)
    clases, rectas = [], []
    for _ in range(40):
        X = rng.uniform(5, 400, 60)
        b = _clase(X * (1 + rng.normal(0, 0.05, 60)), X * (1 + rng.normal(0, 0.05, 60)))
        clases.append(b["resultados"]["variabilidad"])
        rectas.append(b["resultados"]["regresion"]["metodo"])
    assert clases.count("CV constante") >= 34
    assert rectas.count("Deming ponderado") >= 30


def test_a2_el_sesgo_proporcional_no_descarta_deming():
    """A2: con sesgo proporcional y DE constante, Deming salía descartado por
    «error heterocedástico» 200/200. El sesgo proporcional es cosa de la recta,
    no de la dispersión."""
    rng = np.random.default_rng(2)
    clases, rectas = [], []
    for _ in range(40):
        X = rng.uniform(20, 200, 60)
        b = _clase(X + rng.normal(0, 2, 60), 1.1 * X + rng.normal(0, 2, 60))
        clases.append(b["resultados"]["variabilidad"])
        rectas.append(b["resultados"]["regresion"]["metodo"])
    assert clases.count("DE constante") >= 34
    assert rectas.count("Deming") >= 28
    assert "Deming ponderado" not in rectas


def test_a2_la_variabilidad_mixta_va_a_passing_bablok():
    """EP09c §5.4.3 y §6.2.3: constante abajo, proporcional arriba."""
    rng = np.random.default_rng(3)
    X = rng.uniform(1, 400, 120)
    sd = np.where(X < 100, 3.0, 0.03 * X)
    b = _clase(X + rng.normal(0, 1, 120) * sd, X + rng.normal(0, 1, 120) * sd)
    assert b["resultados"]["variabilidad"] == "mixta"
    assert b["resultados"]["regresion"]["metodo"] == "Passing-Bablok"
    assert any("variabilidad mixta" in a for a in b["advertencias"])


def test_a2_con_cv_constante_el_bland_altman_va_en_porcentaje():
    """EP09c §5.4.2 y tabla 3: d = (y − x)/x cuando el CV es constante."""
    rng = np.random.default_rng(4)
    X = rng.uniform(10, 500, 80)
    x = X * (1 + rng.normal(0, 0.04, 80))
    y = 1.05 * X * (1 + rng.normal(0, 0.04, 80))
    b = _clase(x, y)
    ba = b["resultados"]["bland_altman"]
    assert ba["escala"] == "porcentaje"
    esperado = np.mean(100 * (y - x) / x)
    assert ba.get("sesgo", ba.get("sesgo_mediana")) == pytest.approx(
        esperado if "sesgo" in ba else np.median(100 * (y - x) / x), abs=1e-3)
    assert 3 < esperado < 7


def test_a2_la_tendencia_del_sesgo_no_elige_la_recta():
    """El p de la tendencia sigue en el informe, pero ya no decide Deming contra
    Passing-Bablok: esa elección la hace la variabilidad (EP09c §6.2)."""
    rng = np.random.default_rng(2)
    X = rng.uniform(20, 200, 60)
    b = _clase(X + rng.normal(0, 2, 60), 1.1 * X + rng.normal(0, 2, 60))
    sup = b["resultados"]["supuestos"]
    assert sup["proporcional"] is True
    assert b["resultados"]["variabilidad"] == "DE constante"
    assert b["resultados"]["regresion"]["metodo"] == "Deming"


# ------------------------------------------------------------------ Deming ponderado (core)
def _datos_cv(semilla=3, n=60):
    rng = np.random.default_rng(semilla)
    X = rng.uniform(5, 300, n)
    return X * (1 + rng.normal(0, 0.06, n)), (2 + 1.08 * X) * (1 + rng.normal(0, 0.06, n))


@pytest.mark.parametrize("lam", [0.5, 1.0, 2.0])
def test_deming_ponderado_es_el_minimo_que_encuentra_odr(lam):
    """EP09c apéndice B: con los pesos finales wᵢ = 1/zᵢ², la recta es el mínimo
    de Σ wᵢ[(xᵢ − X̂ᵢ)² + λ(yᵢ − a − bX̂ᵢ)²]. scipy.odr lo encuentra por su lado."""
    from src.core.agreement import _deming_ponderado_fit
    x, y = _datos_cv()
    b, a = _deming_ponderado_fit(x, y, lam)
    xh = x + (b * lam) * (y - a - b * x) / (1 + b * b * lam)
    z = (xh + lam * (a + b * xh)) / (1 + lam)
    w = 1 / z ** 2
    salida = odr.ODR(odr.Data(x, y, wd=w, we=lam * w),
                     odr.Model(lambda beta, t: beta[0] + beta[1] * t),
                     beta0=[a, b], maxit=500).run()
    assert salida.beta[1] == pytest.approx(b, abs=1e-6)
    assert salida.beta[0] == pytest.approx(a, abs=1e-5)


def test_deming_ponderado_rinde_mas_que_sin_ponderar_con_cv_constante():
    from src.core.agreement import deming_ponderado, deming_regression
    rng = np.random.default_rng(0)
    pond, sin = [], []
    cubre = 0
    for _ in range(150):
        X = rng.uniform(5, 400, 40)
        x = X * (1 + rng.normal(0, 0.08, 40))
        y = 1.08 * X * (1 + rng.normal(0, 0.08, 40))
        p = deming_ponderado(x, y)
        pond.append(p["slope"])
        sin.append(deming_regression(x, y)["slope"])
        cubre += p["ci_slope"][0] <= 1.08 <= p["ci_slope"][1]
    assert np.mean(pond) == pytest.approx(1.08, abs=0.01)
    assert np.std(pond) < 0.75 * np.std(sin)
    assert cubre / 150 >= 0.90


def test_deming_ponderado_rechaza_valores_no_positivos():
    """EP09c §6.2.2: el peso 1/concentración² no existe en cero."""
    from src.core.agreement import deming_ponderado
    x, y = _datos_cv()
    x[0] = 0.0
    assert "error" in deming_ponderado(x, y)


def test_el_ic_jackknife_usa_t_con_n_menos_2():
    """EP09c K12: estimación ± t(N−2)·EE. Se usaba t(N−1)."""
    from src.core.agreement import _deming_fit, deming_regression
    rng = np.random.default_rng(5)
    x = rng.uniform(10, 100, 12)
    y = x + rng.normal(0, 3, 12)
    r = deming_regression(x, y)
    js = np.array([_deming_fit(np.delete(x, k), np.delete(y, k), 1.0)[0] for k in range(12)])
    pseudo = 12 * r["slope"] - 11 * js
    se = np.sqrt(np.sum((pseudo - pseudo.mean()) ** 2) / (12 * 11))
    assert r["ci_slope"][1] - r["slope"] == pytest.approx(stats.t.ppf(0.975, 10) * se, rel=1e-9)


# ------------------------------------------------------------------ Bland-Altman en % (core)
def test_bland_altman_en_porcentaje_usa_la_referencia_como_base():
    from src.core.bland_altman import bland_altman_analysis
    rng = np.random.default_rng(6)
    ref = rng.uniform(10, 100, 30)
    prueba = ref * 1.1 + rng.normal(0, 1, 30)
    r = bland_altman_analysis(prueba, ref, reference="y", escala="porcentaje")
    d = 100 * (prueba - ref) / ref
    assert r["mean_difference"] == pytest.approx(d.mean())
    assert r["sd_difference"] == pytest.approx(d.std(ddof=1))
    sin_ref = bland_altman_analysis(prueba, ref, escala="porcentaje")
    assert sin_ref["mean_difference"] == pytest.approx(
        np.mean(100 * (prueba - ref) / ((prueba + ref) / 2)))


def test_bland_altman_en_porcentaje_rechaza_ceros():
    from src.core.bland_altman import bland_altman_analysis
    # Sin referencia la base es el promedio: el primer par promedia 0.
    assert "error" in bland_altman_analysis([0, 1, 2, 3], [0, 1, 2, 4], escala="porcentaje")
    # Con referencia, la base es la referencia.
    assert "error" in bland_altman_analysis([1, 1, 2, 3], [0, 1, 2, 3], reference="y",
                                            escala="porcentaje")


# ------------------------------------------------------------------ K7
@pytest.fixture(scope="module")
def ruido():
    # Semilla elegida para que haya pares con p crudo < 0,05 que no pasan la
    # corrección: el caso que K7 describe.
    rng = np.random.default_rng(13)
    return pd.DataFrame({f"V{i}": rng.normal(0, 1, 40) for i in range(8)})


def test_k7_el_bloque_y_la_matriz_dicen_lo_mismo(ruido):
    """K7: el bloque decidía con el p crudo y la matriz con el corregido."""
    rep = run_omnianalysis(ruido, list(ruido.columns))
    celdas = {c["par"]: c for c in rep["correlation_matrix"]["celdas"]}
    for b in rep["blocks"]:
        if b.get("tipo") != "correlación":
            continue
        pr = b["pruebas"][0]
        celda = celdas[b["titulo"].replace("Bivariado — ", "")]
        assert celda["p_adj"] == pr["p_adj"]
        assert celda["detectado"] == pr["detectado"]


def test_k7_se_decide_con_el_p_corregido_por_toda_la_familia(ruido):
    rep = run_omnianalysis(ruido, list(ruido.columns))
    pruebas = [b["pruebas"][0] for b in rep["blocks"] if b.get("pruebas")]
    assert {pr["n_familia"] for pr in pruebas} == {28}
    crudos = [pr["p"] for pr in pruebas]
    from statsmodels.stats.multitest import multipletests
    esperado = multipletests(crudos, method="fdr_bh")[1]
    # Los p del informe van redondeados a 4 decimales; los corregidos salen del
    # p sin redondear, así que se comparan con esa tolerancia.
    assert [pr["p_adj"] for pr in pruebas] == pytest.approx(list(esperado), abs=2e-3)
    for pr in pruebas:
        assert pr["detectado"] == (pr["p_adj"] < 0.05)


def test_k7_un_p_crudo_chico_no_alcanza_si_el_corregido_no_llega(ruido):
    rep = run_omnianalysis(ruido, list(ruido.columns))
    engañosos = [b for b in rep["blocks"] if b.get("pruebas")
                 and b["pruebas"][0]["p"] < 0.05 <= b["pruebas"][0]["p_adj"]]
    assert engañosos, "el fixture tiene que tener un falso positivo sin corregir"
    for b in engañosos:
        assert b["pruebas"][0]["detectado"] is False
        assert "No se detectó" in b["conclusion"]
        assert "corregido" in b["conclusion"]


def test_k7_en_la_rama_b_no_hay_familia():
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"a": rng.normal(0, 1, 30), "b": rng.normal(0, 1, 30)})
    rep = run_omnianalysis(df, ["a", "b"])
    pr = _bloque(rep, "correlación")["pruebas"][0]
    assert pr["n_familia"] == 1 and pr["p_adj"] == pr["p"]
    assert auditar(rep)["estado"]["fdr_bh"] == DESCARTADO


def test_k7_el_posthoc_espera_al_p_corregido():
    """Un ANOVA con p crudo 0,03 que tras corregir no llega no abre el post-hoc."""
    rng = np.random.default_rng(8)
    y = np.concatenate([rng.normal(m, 2, 30) for m in (10, 10, 11.3)])
    g = np.repeat(["a", "b", "c"], 30)
    block = _bloque_vacio()
    _compare_groups("y", pd.Series(y), pd.Series(g), CFG, block)
    assert block["pruebas"][0]["prueba"] == "ANOVA una vía"
    _decidir(block, 0.2, 10, CFG)
    assert "posthoc" not in block["resultados"]
    motivos = {e["id"]: e.get("motivo", "") for e in block["ensayos"]}
    assert "no detectó" in motivos["tukey_hsd"]


# ------------------------------------------------------------------ K10
def test_k10_normales_con_varianzas_distintas_van_a_welch():
    rng = np.random.default_rng(1)
    y = np.concatenate([rng.normal(10, 2, 40), rng.normal(10, 6, 20), rng.normal(10, 14, 10)])
    df = pd.DataFrame({"y": y, "g": np.repeat(["A", "B", "C"], [40, 20, 10])})
    rep = run_omnianalysis(df, ["y", "g"])
    b = _bloque(rep, "comparación de grupos")
    assert b["pruebas"][0]["prueba"] == "ANOVA de Welch"
    aud = auditar(rep)
    assert aud["estado"]["anova_welch"] == EJECUTADO
    assert aud["estado"]["kruskal"] == DESCARTADO


def test_k10_welch_coincide_con_pingouin():
    import pingouin as pg
    from src.core.statistics import welch_anova
    rng = np.random.default_rng(3)
    grupos = [rng.normal(10, 2, 40), rng.normal(11, 6, 20), rng.normal(12, 14, 10)]
    datos = pd.DataFrame({"y": np.concatenate(grupos), "g": np.repeat([0, 1, 2], [40, 20, 10])})
    ref = pg.welch_anova(data=datos, dv="y", between="g")
    r = welch_anova(grupos)
    assert r["f"] == pytest.approx(float(ref["F"].iloc[0]))
    assert r["p"] == pytest.approx(float(ref["p_unc"].iloc[0]))


def test_k10_el_error_tipo_i_baja():
    """K10: medias iguales, DE 2/6/14, n 40/20/10. El motor iba a Kruskal-Wallis
    1000/1000 veces y detectaba diferencia en el 16,7 %.

    Queda algo por encima del 5 %: el pre-test de normalidad (Shapiro al 5 % en
    cada grupo) manda ~15 % de las corridas a Kruskal-Wallis, y ahí la
    dispersión distinta sigue inflando. Ese camino sale con aviso.
    """
    rng = np.random.default_rng(1)
    detecta = 0
    for _ in range(400):
        y = np.concatenate([rng.normal(10, 2, 40), rng.normal(10, 6, 20), rng.normal(10, 14, 10)])
        block = _bloque_vacio()
        _compare_groups("y", pd.Series(y), pd.Series(np.repeat(["A", "B", "C"], [40, 20, 10])),
                        CFG, block)
        _decidir(block, block["_p"], 1, CFG)
        detecta += block["pruebas"][0]["detectado"]
    assert detecta / 400 < 0.10


def test_k10_welch_abre_games_howell():
    rng = np.random.default_rng(5)
    y = np.concatenate([rng.normal(10, 1, 40), rng.normal(14, 5, 20), rng.normal(20, 10, 15)])
    df = pd.DataFrame({"y": y, "g": np.repeat(["A", "B", "C"], [40, 20, 15])})
    rep = run_omnianalysis(df, ["y", "g"])
    b = _bloque(rep, "comparación de grupos")
    assert b["pruebas"][0]["prueba"] == "ANOVA de Welch"
    assert b["resultados"]["posthoc"]["metodo"] == "Games-Howell"
    aud = auditar(rep)
    assert aud["estado"]["games_howell"] == EJECUTADO
    assert aud["estado"]["tukey_hsd"] == DESCARTADO


def test_k10_rangos_con_dispersion_distinta_llevan_aviso():
    rng = np.random.default_rng(9)
    y = np.concatenate([rng.exponential(1, 40), rng.exponential(4, 40), rng.exponential(9, 40)])
    df = pd.DataFrame({"y": y, "g": np.repeat(["A", "B", "C"], 40)})
    b = _bloque(run_omnianalysis(df, ["y", "g"]), "comparación de grupos")
    assert b["pruebas"][0]["prueba"] == "Kruskal-Wallis"
    assert any("reacciona a la diferencia de dispersión" in a for a in b["advertencias"])


# ------------------------------------------------------------------ M8
def test_m8_dunn_con_dos_grupos_es_kruskal_wallis():
    """Con dos grupos, z² de Dunn es la H de Kruskal-Wallis con empates."""
    from src.core.statistics import dunn_test
    rng = np.random.default_rng(4)
    a, b = np.round(rng.normal(10, 3, 25)), np.round(rng.normal(12, 3, 18))
    z = dunn_test([a, b], ["A", "B"])["comparaciones"][0]["z"]
    assert z ** 2 == pytest.approx(stats.kruskal(a, b).statistic, rel=1e-10)


def test_m8_dunn_no_es_mann_whitney_de_a_pares():
    from src.core.statistics import dunn_test
    rng = np.random.default_rng(4)
    g = [rng.normal(0, 1, 20), rng.normal(0.8, 1, 20), rng.normal(1.6, 1, 20)]
    d = dunn_test(g, ["A", "B", "C"])["comparaciones"][0]["p"]
    mw = stats.mannwhitneyu(g[0], g[1], alternative="two-sided").pvalue
    assert d != pytest.approx(mw, abs=1e-4)


# ------------------------------------------------------------------ A8
@pytest.fixture(scope="module")
def tabla_rala():
    filas = [("x", "p")] * 6 + [("x", "q")] * 1 + [("y", "q")] * 5 + [("y", "r")] * 2 + \
            [("z", "r")] * 6 + [("z", "p")] * 1 + [("x", "r")] * 1
    return pd.DataFrame(filas, columns=["F", "C"])


def test_a8_tabla_rala_mayor_que_2x2_usa_p_por_simulacion(tabla_rala):
    rep = run_omnianalysis(tabla_rala, ["F", "C"])
    b = _bloque(rep, "tabla de contingencia")
    assert b["resultados"]["supuestos"]["esperada_minima"] < 5
    assert b["pruebas"][0]["prueba"] == "Chi-cuadrado (p por simulación)"
    motivos = {e["id"]: e.get("motivo", "") for e in b["ensayos"] if e["estado"] == DESCARTADO}
    assert "≥" not in motivos["chi2"], "decía «esperada mínima 0,1 ≥ 5»"
    assert "<" in motivos["chi2"]


def test_a8_el_p_por_simulacion_coincide_con_permutar_a_mano(tabla_rala):
    rep = run_omnianalysis(tabla_rala, ["F", "C"])
    p_motor = _bloque(rep, "tabla de contingencia")["pruebas"][0]["p"]
    f, nf = pd.factorize(tabla_rala["F"])[0], tabla_rala["F"].nunique()
    c, nc = pd.factorize(tabla_rala["C"])[0], tabla_rala["C"].nunique()

    def chi2(cols):
        obs = np.bincount(f * nc + cols, minlength=nf * nc).reshape(nf, nc)
        esp = obs.sum(1, keepdims=True) * obs.sum(0, keepdims=True) / obs.sum()
        return np.sum((obs - esp) ** 2 / esp)

    real = chi2(c)
    assert real == pytest.approx(stats.chi2_contingency(
        pd.crosstab(tabla_rala["F"], tabla_rala["C"]).values, correction=False).statistic)
    rng = np.random.default_rng(0)
    B = 20000
    mayores = sum(chi2(rng.permutation(c)) >= real - 1e-9 for _ in range(B))
    assert p_motor == pytest.approx((mayores + 1) / (B + 1), abs=0.01)


def test_a8_el_p_por_simulacion_es_reproducible(tabla_rala):
    p1 = _bloque(run_omnianalysis(tabla_rala, ["F", "C"]), "tabla de contingencia")
    p2 = _bloque(run_omnianalysis(tabla_rala, ["F", "C"]), "tabla de contingencia")
    assert p1["pruebas"][0]["p"] == p2["pruebas"][0]["p"]


def test_a8_el_caso_no_promete_una_probabilidad_exacta(tabla_rala):
    rep = run_omnianalysis(tabla_rala, ["F", "C"])
    caso = next(c for c in casos(rep) if c.tipo == "¿Las categorías se asocian?")
    paso = next(p for p in caso.pasos if "casillero" in p.pregunta)
    assert "3×3" in paso.consecuencia
    assert "se calcula la probabilidad exacta" not in paso.consecuencia


# ------------------------------------------------------------------ A15
def test_a15_un_grupo_codificado_1_2_3_se_compara_como_grupos():
    """A15: Hb × Grupo(1,2,3) salía como correlación de Spearman."""
    rng = np.random.default_rng(3)
    df = pd.DataFrame({"Hb": rng.normal(13, 1.5, 90), "Grupo": np.repeat([1, 2, 3], 30)})
    rep = run_omnianalysis(df, ["Hb", "Grupo"])
    assert rep["profile"]["col_types"]["Grupo"]["tipo"] == CATEGORICAL_ORDINAL
    assert "códigos" in rep["profile"]["col_types"]["Grupo"]["nota"]
    b = rep["blocks"][-1]
    assert b["tipo"] == "comparación de grupos"
    assert b["resultados"]["supuestos"]["etiquetas"] == ["1", "2", "3"]


def test_a15_enteros_con_huecos_siguen_siendo_numericos():
    rng = np.random.default_rng(3)
    s = pd.Series(rng.choice([0, 2, 3, 5, 8, 9], 100))
    assert _classify_column(s, CFG)["tipo"] == NUMERIC_DISCRETE


def test_a15_enteros_sin_repeticion_no_son_codigos():
    s = pd.Series([1, 2, 3, 4, 5, 6])
    assert _classify_column(s, CFG)["tipo"] != CATEGORICAL_ORDINAL


# ------------------------------------------------------------------ A14
def _escenarios():
    rng = np.random.default_rng(21)
    n = 60
    ref = rng.uniform(5, 400, n)
    yield "cv", pd.DataFrame({"R": ref * (1 + rng.normal(0, 0.05, n)),
                              "P": ref * (1 + rng.normal(0, 0.05, n))}), ("P", "R"), "R"
    yield "de", pd.DataFrame({"R": ref + rng.normal(0, 3, n),
                              "P": 1.1 * ref + rng.normal(0, 3, n)}), ("P", "R"), None
    y = np.concatenate([rng.normal(10, 2, 40), rng.normal(14, 6, 20), rng.normal(18, 14, 10)])
    yield "welch", pd.DataFrame({"y": y, "g": np.repeat(["A", "B", "C"], [40, 20, 10])}), None, None
    y = np.concatenate([rng.normal(m, 2, 30) for m in (10, 12, 14)])
    yield "anova", pd.DataFrame({"y": y, "g": np.repeat(["A", "B", "C"], 30)}), None, None
    y = np.concatenate([rng.exponential(s, 40) for s in (1, 3, 6)])
    yield "kruskal", pd.DataFrame({"y": y, "g": np.repeat(["A", "B", "C"], 40)}), None, None


@pytest.mark.parametrize("nombre,df,par,ref", list(_escenarios()),
                         ids=[e[0] for e in _escenarios()])
def test_a14_el_camino_ejecutado_es_un_camino_del_arbol(nombre, df, par, ref):
    """A14: el árbol dibujado omitía condiciones del motor. Todo ensayo que corre
    tiene que poder alcanzarse por una arista desde algo que también corrió o
    desde una pregunta."""
    rep = run_omnianalysis(df, list(df.columns),
                           confirmed_comparisons=[par] if par else None,
                           referencias={par: ref} if ref else None)
    estados = auditar(rep)["estado"]
    for etapa, layout in omni_arbol.LAYOUT.items():
        entrantes = {}
        for origen, destino, _ in layout["aristas"]:
            entrantes.setdefault(destino, []).append(origen)
        for clave, _c, _f in layout["nodos"]:
            if clave.startswith("?") or estados.get(clave) != EJECUTADO:
                continue
            origenes = entrantes.get(clave)
            if not origenes:
                continue  # raíz de la etapa
            assert any(o.startswith("?") or estados.get(o) == EJECUTADO for o in origenes), (
                f"{nombre}: {clave} corrió pero ninguna arista del árbol llega desde "
                f"algo que corrió ({origenes})")


def test_a14_las_etiquetas_de_3_grupos_nombran_la_varianza():
    etiquetas = {d: e for o, d, e in omni_arbol.LAYOUT["Bivariado"]["aristas"]
                 if o == "?k_grupos"}
    assert "var =" in etiquetas["anova"] and "var ≠" in etiquetas["anova_welch"]


# ------------------------------------------------------------------ A16
def test_a16_el_caso_no_le_da_la_razon_a_un_paso():
    """Doce pares en un rango angosto: la tendencia detecta y la recta no."""
    rng = np.random.default_rng(5)
    x = rng.uniform(90, 110, 12)
    df = pd.DataFrame({"Metodo_A": x, "Metodo_B": x + rng.normal(0, 3, 12)})
    rep = run_omnianalysis(df, list(df.columns),
                           confirmed_comparisons=[("Metodo_A", "Metodo_B")])
    caso = next(c for c in casos(rep) if c.tipo.startswith("¿Los dos métodos"))
    paso = next(p for p in caso.pasos if "corrimiento parejo" in p.pregunta)
    assert "Vale la del paso" not in paso.consecuencia
    assert "ninguna manda" in paso.consecuencia


# ------------------------------------------------------------------ M14, M15
def _textos(rep):
    from src.ui.omni_panel import OmniPanel
    from src.ui.omni_render import resumen_html
    salida = [OmniPanel._render(None, rep), resumen_html(rep, auditar(rep))]
    for b in rep["blocks"]:
        salida += [b.get("conclusion", "")] + b.get("traza", []) + b.get("advertencias", [])
        salida += [e.get("detalle", "") + e.get("motivo", "") for e in b.get("ensayos", [])]
    for c in casos(rep):
        salida += [c.veredicto, c.matiz] + [f"{p.pregunta} {p.medicion} {p.respuesta} "
                                            f"{p.consecuencia} {p.alternativa}" for p in c.pasos]
    return salida


@pytest.mark.parametrize("nombre,df,par,ref", list(_escenarios()),
                         ids=[e[0] for e in _escenarios()])
def test_m14_el_omnianalisis_no_dice_significativo(nombre, df, par, ref):
    rep = run_omnianalysis(df, list(df.columns),
                           confirmed_comparisons=[par] if par else None,
                           referencias={par: ref} if ref else None)
    usos = [t for t in _textos(rep) if "significativ" in t.lower()]
    assert usos == [], usos[:3]


def test_m14_ni_la_rama_c_ni_las_tablas(ruido, tabla_rala):
    for rep in (run_omnianalysis(ruido, list(ruido.columns)),
                run_omnianalysis(tabla_rala, ["F", "C"])):
        usos = [t for t in _textos(rep) if "significativ" in t.lower()]
        assert usos == [], usos[:3]


def test_m14_el_catalogo_tampoco():
    for e in ENSAYOS:
        for texto in (e.nombre, e.gatillo, e.porque):
            assert "significativ" not in texto.lower(), e.id


def test_m15_el_catalogo_no_repite_las_dos_afirmaciones_falsas():
    assert "ATENÚA" not in POR_ID["ba_eje_referencia"].porque
    assert "dos direcciones" in POR_ID["ba_eje_referencia"].porque
    assert "desviaciones triviales" not in POR_ID["anderson"].porque
    assert "No es más indulgente" in POR_ID["anderson"].porque


def test_passing_bablok_del_omnianalisis_corre_la_cusum():
    """Lo mismo que el panel: si Passing-Bablok es la recta elegida y los datos
    son curvos, el Omnianálisis lo avisa en vez de leer la pendiente."""
    rng = np.random.default_rng(3)
    X = rng.uniform(1, 400, 120)
    sd = np.where(X < 100, 3.0, 0.03 * X)
    x = X + rng.normal(0, 1, 120) * sd
    y = X + 0.3 * (X - 200) ** 2 / 200 + rng.normal(0, 1, 120) * sd
    b = _clase(x, y)
    reg = b["resultados"]["regresion"]
    assert reg["metodo"] == "Passing-Bablok"
    assert reg["cusum_p"] < 0.05
    assert any("Cusum" in a and "linealidad" in a for a in b["advertencias"])
    assert any(t.startswith("Cusum de linealidad") for t in b["traza"])
