"""«ANOVA» migrada a `Resultado` (paso 4, familia 5).

Oráculos: scipy (f_oneway, levene), pingouin (welch_anova, pairwise_gameshowell,
ancova, rm_anova) y statsmodels (Tukey, ANOVA de dos vías). La de una vía sigue
el mismo árbol que el Omnianálisis; el test lo compara bloque contra bloque.
Cambio a propósito: la diferencia de Tukey se informa primero − segundo, como
Games-Howell (statsmodels la da al revés).
"""
import os
import re
from html import unescape

import numpy as np
import pandas as pd
import pingouin as pg
import pytest
from scipy import stats

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.analysis.omni_analyzer import run_omnianalysis  # noqa: E402
from src.core.statistics import tukey_hsd  # noqa: E402
from src.resultado import render_html  # noqa: E402
from src.resultado.constructores import (  # noqa: E402
    ancova, anova_dos_vias, anova_una_via, medidas_repetidas,
)

RNG = np.random.default_rng(31)


def _hoja(des=(5, 5, 5), medias=(50, 50, 58), n=25):
    return pd.DataFrame({
        "valor": np.concatenate([RNG.normal(m, d, n) for m, d in zip(medias, des)]),
        "grupo": np.repeat(["A", "B", "C"], n)})


IGUALES = _hoja()
DISTINTAS = _hoja(des=(2, 6, 14))


def _v(res, empieza):
    return next(v for v in res.valores if v.nombre.startswith(empieza))


def _paso(res, texto):
    return next(s for s in res.supuestos if texto in s.pregunta)


def _texto(res):
    return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", render_html(res)))).strip()


def test_varianzas_iguales_anova_clasico_y_tukey():
    res = anova_una_via(IGUALES, "valor", "grupo")
    grupos = [g["valor"].to_numpy() for _, g in IGUALES.groupby("grupo")]
    assert _v(res, "F (ANOVA de una vía)").valor == pytest.approx(stats.f_oneway(*grupos).statistic)
    assert res.crudo["posthoc"]["metodo"] == "Tukey HSD"
    assert _paso(res, "dispersan igual").respuesta == "Sí"


def test_varianzas_distintas_welch_y_games_howell():
    res = anova_una_via(DISTINTAS, "valor", "grupo")
    ref = pg.welch_anova(data=DISTINTAS, dv="valor", between="grupo")
    assert _v(res, "F (ANOVA de Welch)").valor == pytest.approx(ref["F"].iloc[0])
    assert res.crudo["posthoc"]["metodo"] == "Games-Howell"
    assert "Kruskal-Wallis no es la salida" in _paso(res, "dispersan igual").consecuencia


def test_la_misma_prueba_que_el_omnianalisis():
    """Una sola verdad: mismos datos, misma prueba y mismo p en los dos lados."""
    for hoja in (IGUALES, DISTINTAS):
        res = anova_una_via(hoja, "valor", "grupo")
        rep = run_omnianalysis(hoja, ["valor", "grupo"])
        bloque = next(b for b in rep["blocks"] if b.get("tipo") == "comparación de grupos")
        prueba = bloque["pruebas"][0]
        assert prueba["prueba"] == res.crudo["prueba"].replace("ANOVA de una vía", "ANOVA una vía")
        assert prueba["p"] == pytest.approx(res.crudo["p"], abs=1e-4)


def test_tukey_se_lee_primero_menos_segundo():
    """Cambió a propósito: statsmodels informa media(B) − media(A) para «A vs B»."""
    a, c = RNG.normal(10, 1, 30), RNG.normal(20, 1, 30)
    ph = tukey_hsd([a, c], ["A", "C"])
    comp = ph["comparaciones"][0]
    assert comp["par"] == "A vs C"
    assert comp["diferencia"] == pytest.approx(a.mean() - c.mean())
    assert comp["ic95"][0] < comp["diferencia"] < comp["ic95"][1] < 0


def test_sin_diferencia_global_no_hay_post_hoc():
    res = anova_una_via(_hoja(medias=(50, 50, 50)), "valor", "grupo")
    assert res.crudo["posthoc"] is None
    assert "no se corre el post-hoc" in _paso(res, "medias de los grupos").consecuencia


def test_grupos_no_normales_remiten_a_kruskal():
    hoja = pd.DataFrame({"valor": np.exp(RNG.normal(0, 1.2, 36)),
                         "grupo": np.repeat(["A", "B", "C"], 12)})
    res = anova_una_via(hoja, "valor", "grupo")
    assert _paso(res, "Cada grupo es normal").respuesta.startswith("No")
    assert any("Kruskal-Wallis" in a for a in res.advertencias)


def test_un_grupo_que_parece_medicion_se_rechaza():
    hoja = pd.DataFrame({"valor": RNG.normal(0, 1, 30), "otra": RNG.normal(0, 1, 30)})
    assert "parece una medición" in anova_una_via(hoja, "valor", "otra").error


def test_dos_vias_contra_statsmodels():
    import statsmodels.api as sm
    from statsmodels.formula.api import ols
    i = np.arange(60)
    hoja = pd.DataFrame({"y": RNG.normal(0, 1, 60) + (i % 3) + 2 * ((i // 3) % 2),
                         "A": i % 3, "B": (i // 3) % 2})
    res = anova_dos_vias(hoja, "y", "A", "B")
    ref = sm.stats.anova_lm(ols("y ~ C(A) * C(B)", data=hoja).fit(), typ=2)
    assert _v(res, "Factor A").valor == pytest.approx(ref.loc["C(A)", "F"])
    assert _v(res, "Interacción").valor == pytest.approx(ref.loc["C(A):C(B)", "F"])


def test_ancova_contra_pingouin():
    x = RNG.normal(50, 10, 60)
    g = np.repeat(["A", "B"], 30)
    hoja = pd.DataFrame({"y": 0.5 * x + (g == "B") * 3 + RNG.normal(0, 2, 60), "g": g, "x": x})
    res = ancova(hoja, "y", "g", "x")
    ref = pg.ancova(data=hoja, dv="y", between="g", covar="x")
    assert _v(res, "Grupo").valor == pytest.approx(ref.set_index("Source").loc["g", "F"])
    assert _paso(res, "pesa igual").respuesta == "Sí"


def test_medidas_repetidas_contra_pingouin():
    base = RNG.normal(100, 10, 20)
    hoja = pd.DataFrame({"t0": base + RNG.normal(0, 2, 20), "t1": base + 2 + RNG.normal(0, 2, 20),
                         "t2": base + 4 + RNG.normal(0, 5, 20)})
    res = medidas_repetidas(hoja, ["t0", "t1", "t2"])
    largo = hoja.reset_index().melt(id_vars="index", var_name="t", value_name="y")
    ref = pg.rm_anova(data=largo, dv="y", within="t", subject="index", correction=True)
    assert _v(res, "F").valor == pytest.approx(ref["F"].iloc[0])
    assert _v(res, "ε de Greenhouse-Geisser").valor == pytest.approx(ref["eps"].iloc[0], abs=1e-6)


@pytest.mark.parametrize("res", [
    anova_una_via(IGUALES, "valor", "grupo"), anova_una_via(DISTINTAS, "valor", "grupo"),
    medidas_repetidas(pd.DataFrame(RNG.normal(0, 1, (15, 3)), columns=list("abc")), list("abc"))],
    ids=["clasico", "welch", "repetidas"])
def test_informe_y_figuras(res):
    import matplotlib.pyplot as plt
    assert res.ok, res.error
    t = _texto(res)
    assert "Qué se verificó" in t and "significativ" not in t.lower()
    for figura in res.figuras:
        fig = figura.dibujar()
        assert fig.axes
        plt.close(fig)


@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("analisis, c1, c2, c3", [
    ("ANOVA una via", "valor", "grupo", "(ninguna)"),
    ("ANOVA una via (core)", "valor", "grupo", "(ninguna)"),
    ("ANOVA dos vias", "valor", "grupo", "bloque"),
    ("ANCOVA", "valor", "grupo", "edad"),
    ("Medidas repetidas", "valor", "grupo", "(ninguna)"),
])
def test_el_panel(qt_app, analisis, c1, c2, c3):
    from src.ui.analysis_panel import AnalysisPanel
    hoja = IGUALES.assign(bloque=np.arange(75) % 2, edad=RNG.normal(40, 8, 75),
                          t1=RNG.normal(0, 1, 75))
    panel = AnalysisPanel()
    panel.set_data(hoja)
    panel.combo_analysis.setCurrentText(analisis)
    panel.combo_col1.setCurrentText(c1)
    panel.combo_col2.setCurrentText(c2)
    panel.combo_col3.setCurrentText(c3)
    if analisis == "Medidas repetidas":
        panel.columnas_elegidas = ["valor", "t1"]
    panel._run()
    assert "Qué se verificó y qué se decidió" in panel.txt_results.toPlainText()
