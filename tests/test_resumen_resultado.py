"""«Resumen y distribución» migrado a `Resultado` (paso 4 de la propuesta).

Cada número se compara contra el core que lo calcula, y donde hay un oráculo
independiente (numpy, scipy, el ejemplo del NIST) contra ese. Lo que cambió a
propósito lo dice el nombre del test: los cuartiles, que ahora son los mismos en
las descriptivas, la tabla de percentiles y Tukey.
"""
import os
import re
from html import unescape

import numpy as np
import pandas as pd
import pytest
from scipy import stats

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.core.outliers import generalized_esd, grubbs_test, tukey_outliers  # noqa: E402
from src.core.reference import percentile_table  # noqa: E402
from src.core.statistics import (  # noqa: E402
    descriptive_stats, kurtosis_test, skewness_test, trimmed_mean,
)
from src.resultado import render_html  # noqa: E402
from src.resultado.constructores import (  # noqa: E402
    asimetria_curtosis, descriptivas, esd, grubbs, media_armonica, media_geometrica,
    media_recortada, percentiles, shapiro_wilk, tukey,
)
from tests.test_outliers_referencia import NIST  # noqa: E402

RNG = np.random.default_rng(21)
NORMAL = pd.DataFrame({"x": RNG.normal(100, 10, 60)})
SESGADA = pd.DataFrame({"x": RNG.lognormal(3, 0.8, 80)})
UNA_FAMILIA = [descriptivas, asimetria_curtosis, percentiles, media_recortada, media_geometrica,
               media_armonica, shapiro_wilk, grubbs, tukey, esd]


def _v(res, nombre):
    return next(v for v in res.valores if v.nombre == nombre)


def _paso(res, texto):
    return next(s for s in res.supuestos if texto in s.pregunta)


def _texto(res):
    return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", render_html(res)))).strip()


# ---------------- Descriptivas ----------------

def test_descriptivas_contra_numpy_y_scipy():
    x = NORMAL["x"].to_numpy()
    res = descriptivas(NORMAL, "x")
    n = len(x)
    assert _v(res, "Media").valor == pytest.approx(x.mean())
    assert _v(res, "DE").valor == pytest.approx(x.std(ddof=1))
    ee = x.std(ddof=1) / np.sqrt(n)
    t = stats.t.ppf(0.975, n - 1)
    assert _v(res, "Media").ic == pytest.approx((x.mean() - t * ee, x.mean() + t * ee))
    assert _v(res, "CV").valor == pytest.approx(100 * x.std(ddof=1) / x.mean())


def test_los_cuartiles_son_los_mismos_en_toda_la_familia():
    """Cambió a propósito: las descriptivas y Tukey usaban la interpolación
    lineal de numpy y la tabla de percentiles el rango p(n+1), así que la misma
    columna daba dos P25. Ahora todos usan p(n+1), la definición de EP28."""
    x = SESGADA["x"].to_numpy()
    p25 = np.percentile(x, 25, method="weibull")
    assert _v(descriptivas(SESGADA, "x"), "P25").valor == pytest.approx(p25)
    assert _v(percentiles(SESGADA, "x"), "P25").valor == pytest.approx(p25)
    assert _v(tukey(SESGADA, "x"), "P25").valor == pytest.approx(p25)
    assert descriptive_stats(x)["q25"] == pytest.approx(p25)


def test_descriptivas_normales_se_resumen_con_media_y_de():
    res = descriptivas(NORMAL, "x")
    assert _paso(res, "resumir").respuesta == "Media y DE"
    assert res.lectura.startswith("Resumen: media")
    assert "Rango del 95 % de los datos" in [v.nombre for v in res.valores]


def test_descriptivas_sesgadas_se_resumen_con_la_mediana():
    res = descriptivas(SESGADA, "x")
    assert _paso(res, "resumir").respuesta == "Mediana y rango intercuartílico"
    assert res.lectura.startswith("Resumen: mediana")
    assert "Rango del 95 % de los datos" not in [v.nombre for v in res.valores]


def test_texto_en_una_columna_de_numeros_se_rechaza_con_un_ejemplo():
    hoja = pd.DataFrame({"x": [1.0, 2.0, "<0,5", 4.0, None]})
    for f in UNA_FAMILIA:
        res = f(hoja, "x")
        assert not res.ok and "«<0,5»" in res.error, f.__name__


def test_los_infinitos_se_sacan_y_se_avisa():
    hoja = pd.DataFrame({"x": list(NORMAL["x"]) + [np.inf]})
    res = descriptivas(hoja, "x")
    assert res.entrada.n == 60
    assert any("infinito" in a for a in res.advertencias)


# ---------------- Asimetría, percentiles, medias ----------------

def test_asimetria_y_curtosis_son_las_del_core():
    x = SESGADA["x"].to_numpy()
    res = asimetria_curtosis(SESGADA, "x")
    assert _v(res, "Asimetría (g₁)").valor == pytest.approx(skewness_test(x)["skewness"])
    assert _v(res, "Exceso de curtosis (g₂)").valor == pytest.approx(kurtosis_test(x)["kurtosis"])
    assert _paso(res, "simétrica").respuesta == "Se detectó asimetría"
    assert "a la derecha" in res.lectura


def test_asimetria_con_pocos_datos_se_rechaza():
    assert "al menos 8" in asimetria_curtosis(pd.DataFrame({"x": [1, 2, 3.0]}), "x").error


def test_percentiles_son_los_del_core():
    x = NORMAL["x"].to_numpy()
    res = percentiles(NORMAL, "x")
    for fila in percentile_table(x)["percentiles"]:
        v = _v(res, f"P{fila['percentile']}")
        assert v.valor == pytest.approx(fila["value"])
        assert v.ic == pytest.approx((fila["ci_low"], fila["ci_high"]))


def test_con_pocos_datos_no_se_inventan_p5_ni_p95():
    res = percentiles(pd.DataFrame({"x": np.arange(1.0, 11.0)}), "x")
    assert _v(res, "P5").valor is None and "19 datos" in _v(res, "P5").nota
    assert _paso(res, "Alcanzan").respuesta == "No para P5, P95"


def test_media_recortada_es_la_del_core():
    x = SESGADA["x"].to_numpy()
    r = trimmed_mean(x, 0.10)
    res = media_recortada(SESGADA, "x")
    assert _v(res, "Media recortada").valor == pytest.approx(r["mean"])
    assert _v(res, "Media recortada").ic == pytest.approx(r["ci95"])
    assert _v(res, "Media recortada").valor == pytest.approx(stats.trim_mean(x, 0.10))


def test_media_geometrica_contra_scipy():
    x = SESGADA["x"].to_numpy()
    res = media_geometrica(SESGADA, "x")
    assert _v(res, "Media geométrica").valor == pytest.approx(stats.gmean(x))
    assert _paso(res, "logaritmos").respuesta == "Sí"


def test_media_armonica_contra_scipy():
    res = media_armonica(SESGADA, "x")
    assert _v(res, "Media armónica").valor == pytest.approx(stats.hmean(SESGADA["x"]))


def test_un_cero_rechaza_las_medias_geometrica_y_armonica():
    hoja = pd.DataFrame({"x": [0.0, 2.0, 8.0, 4.0]})
    for f in (media_geometrica, media_armonica):
        assert "cero o negativo" in f(hoja, "x").error


# ---------------- Normalidad ----------------

def test_shapiro_contra_scipy():
    res = shapiro_wilk(NORMAL, "x")
    w, p = stats.shapiro(NORMAL["x"])
    assert _v(res, "W").valor == pytest.approx(w)
    assert _paso(res, "apartan").respuesta == "No se detectó apartamiento"
    assert "no prueba que sea normal" in res.matiz


def test_shapiro_detecta_la_cola_larga():
    assert _paso(shapiro_wilk(SESGADA, "x"), "apartan").respuesta == "Se detectó apartamiento"


def test_shapiro_con_mas_de_5000_lo_avisa():
    hoja = pd.DataFrame({"x": np.random.default_rng(1).normal(0, 1, 6000)})
    res = shapiro_wilk(hoja, "x")
    assert any("submuestra de 5000" in a for a in res.advertencias)


# ---------------- Atípicos ----------------

def _con_atipico():
    x = list(NORMAL["x"])
    x[7] = 190.0
    return pd.DataFrame({"x": x})


def test_grubbs_es_el_del_core_y_marca_el_atipico():
    hoja = _con_atipico()
    r = grubbs_test(hoja["x"].to_numpy())
    res = grubbs(hoja, "x")
    assert _v(res, "G").valor == pytest.approx(r["g"])
    assert _v(res, "G crítico (α = 0,05)").valor == pytest.approx(r["g_crit"])
    assert _paso(res, "más alejado").respuesta == "Sí"
    assert _paso(res, "Sin los candidatos").respuesta == "Sí"
    assert "190" in res.lectura


def test_grubbs_sin_atipico():
    assert _paso(grubbs(NORMAL, "x"), "más alejado").respuesta == "No"


def test_tukey_es_el_del_core():
    x = SESGADA["x"].to_numpy()
    r = tukey_outliers(x)
    res = tukey(SESGADA, "x")
    assert _v(res, "Fuera de las internas («outside»)").valor == r["n_mild"]
    assert _v(res, "Fuera de las externas («far out»)").valor == r["n_extreme"]


def test_tukey_avisa_que_una_cola_larga_no_son_atipicos():
    paso = _paso(tukey(SESGADA, "x"), "simétrica")
    assert paso.respuesta == "No" and "logaritmos" in paso.consecuencia


def test_esd_contra_el_ejemplo_del_nist():
    """NIST/SEMATECH 1.3.5.17.3: 3 atípicos entre 54 datos."""
    hoja = pd.DataFrame({"x": NIST})
    res = esd(hoja, "x")
    assert _v(res, "Atípicos detectados").valor == 3
    assert res.crudo["esd"]["outliers"] == generalized_esd(np.array(NIST), 10, 0.05)["outliers"]
    assert _paso(res, "Cuántos atípicos").respuesta == "3"


# ---------------- Todos ----------------

@pytest.mark.parametrize("f", UNA_FAMILIA, ids=lambda f: f.__name__)
def test_el_informe_y_las_figuras(f):
    import matplotlib.pyplot as plt
    res = f(SESGADA, "x")
    assert res.ok, res.error
    t = _texto(res)
    assert "Qué se verificó y qué se decidió" in t and "Referencias" in t
    assert "significativ" not in t.lower()
    for figura in res.figuras:
        fig = figura.dibujar()
        assert fig.axes
        plt.close(fig)


@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("analisis", [
    "Estadisticas descriptivas", "Asimetria y curtosis", "Tabla de percentiles",
    "Media recortada", "Media geometrica", "Media armonica", "Shapiro-Wilk",
    "Outliers (Grubbs)", "Outliers (Tukey)", "Outliers (ESD)"])
def test_el_panel_los_muestra_como_resultado(qt_app, analisis):
    from src.ui.analysis_panel import AnalysisPanel
    panel = AnalysisPanel()
    panel.set_data(SESGADA)
    panel.combo_analysis.setCurrentText(analisis)
    panel.combo_col1.setCurrentText("x")
    panel._run()
    texto = panel.txt_results.toPlainText()
    assert "Qué se verificó y qué se decidió" in texto
    assert "Referencias" in texto
