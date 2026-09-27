"""«Valores de referencia» migrados a `Resultado` (paso 4, familia 12).

Oráculos: el rango de EP28 (numpy, método weibull), statsmodels para el
polinomio de la media y cobertura simulada para los centiles por edad.
Cambian a propósito, cada uno con su test:

- El intervalo revisa extremos con Dixon y verifica uno publicado (EP28: 20
  sujetos, hasta 2 afuera); su IC se rotula 90 %, no 95 %.
- Los intervalos por edad salen por regresión (Altman 1993). Los grupos quedan
  como opción, con percentiles 2,5 y 97,5 de EP28 (antes 5 y 95 lineales).
"""
import os
import re
from html import unescape

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.core.reference import reference_interval  # noqa: E402
from src.resultado import render_html  # noqa: E402
from src.resultado.constructores import intervalo_referencia, intervalos_por_edad  # noqa: E402


def _texto(res):
    return unescape(re.sub(r"<[^>]+>", " ", render_html(res)))


def _v(res, empieza):
    return next(v for v in res.valores if v.nombre.startswith(empieza))


def _sanos(n=150, semilla=0):
    return pd.DataFrame({"x": np.random.default_rng(semilla).lognormal(3, 0.3, n)})


def _edades(n=300, semilla=0, curva=0.004, sd_pend=0.05):
    rng = np.random.default_rng(semilla)
    edad = rng.uniform(18, 90, n)
    media = 50 + 0.3 * edad + curva * (edad - 50) ** 2
    return pd.DataFrame({"edad": edad, "valor": rng.normal(media, 2 + sd_pend * edad)})


# ---------------- Intervalo de referencia ----------------

def test_los_limites_son_los_de_ep28_con_ic_90():
    hoja = _sanos()
    res = intervalo_referencia(hoja, "x")
    ri = reference_interval(hoja["x"].values)
    li, ls = _v(res, "Límite inferior"), _v(res, "Límite superior")
    assert li.valor == pytest.approx(ri["lower"]) and ls.valor == pytest.approx(ri["upper"])
    assert li.ic == (ri["ci_lower_low"], ri["ci_lower_high"])
    t = _texto(res)
    assert "IC 90 %" in t and "IC 95 %" not in t


def test_dixon_marca_un_extremo_alejado():
    hoja = _sanos()
    hoja.loc[0, "x"] = hoja["x"].max() * 3
    res = intervalo_referencia(hoja, "x")
    paso = next(s for s in res.supuestos if "Dixon" in s.pregunta)
    assert not paso.ok and paso.respuesta.startswith("Sí: el más alto")


def test_dixon_no_marca_datos_limpios():
    paso = next(s for s in intervalo_referencia(_sanos(semilla=3), "x").supuestos
                if "Dixon" in s.pregunta)
    assert paso.ok


@pytest.mark.parametrize("afuera, verificado", [(2, True), (3, False)])
def test_verificacion_con_20_sujetos(afuera, verificado):
    """EP28, transferencia: se adopta con 2 o menos de 20 afuera."""
    x = np.r_[np.linspace(10, 20, 20 - afuera), np.full(afuera, 25.0)]
    res = intervalo_referencia(pd.DataFrame({"x": x}), "x", {"inferior": 9.0, "superior": 21.0})
    paso = next(s for s in res.supuestos if "publicado" in s.pregunta)
    assert paso.ok is verificado
    assert res.crudo["verificacion"]["fuera"] == afuera


def test_verificacion_con_un_solo_limite():
    x = np.linspace(0, 9, 40)
    res = intervalo_referencia(pd.DataFrame({"x": x}), "x", {"inferior": None, "superior": 8.0})
    v = res.crudo["verificacion"]
    assert v["fuera"] == int(np.sum(x > 8.0)) and v["permitidos"] == 4


def test_menos_de_20_se_rechaza():
    assert "al menos 20" in intervalo_referencia(_sanos(n=15), "x").error


# ---------------- Intervalos por edad ----------------

def test_la_media_es_el_polinomio_de_minimos_cuadrados():
    hoja = _edades()
    res = intervalos_por_edad(hoja, "edad", "valor")
    c = res.crudo["centiles"]
    assert c["grado"] == 2
    X = sm.add_constant(np.column_stack([hoja["edad"], hoja["edad"] ** 2]))
    ols = sm.OLS(hoja["valor"], X).fit()
    edades = np.array([20.0, 50.0, 85.0])
    esperado = ols.predict(sm.add_constant(np.column_stack([edades, edades ** 2]), has_constant="add"))
    assert np.allclose(c["centiles"](edades)[1], esperado, rtol=1e-9)


def test_los_centiles_cubren_el_95():
    """Datos con media curva y DE que crece con la edad, n = 300 por muestra."""
    fuera = []
    for semilla in range(40):
        c = intervalos_por_edad(_edades(semilla=semilla), "edad", "valor").crudo["centiles"]
        nuevos = _edades(n=4000, semilla=1000 + semilla)
        lo, _, hi = c["centiles"](nuevos["edad"].values)
        fuera.append(np.mean((nuevos["valor"] < lo) | (nuevos["valor"] > hi)))
    assert np.mean(fuera) == pytest.approx(0.05, abs=0.012)


def test_la_de_se_abre_con_la_edad_si_los_datos_lo_hacen():
    assert intervalos_por_edad(_edades(), "edad", "valor").crudo["centiles"]["sd_lineal"]
    plano = intervalos_por_edad(_edades(sd_pend=0.0, semilla=5), "edad", "valor")
    assert not plano.crudo["centiles"]["sd_lineal"]


def test_valores_con_cola_piden_escala_log():
    rng = np.random.default_rng(2)
    edad = rng.uniform(1, 80, 400)
    hoja = pd.DataFrame({"edad": edad, "valor": np.exp(rng.normal(1 + 0.01 * edad, 0.5))})
    lineal = intervalos_por_edad(hoja, "edad", "valor")
    paso = next(s for s in lineal.supuestos if "normales" in s.pregunta)
    assert not paso.ok and "escala log" in paso.consecuencia
    log = intervalos_por_edad(hoja, "edad", "valor", {"escala": "log"})
    assert next(s for s in log.supuestos if "normales" in s.pregunta).ok


def test_por_grupos_usa_los_percentiles_de_ep28():
    """Cambió a propósito: antes, percentiles 5 y 95 lineales."""
    hoja = _edades(n=1000)
    res = intervalos_por_edad(hoja, "edad", "valor", {"metodo": "grupos"})
    grupos = res.crudo["grupos"]["groups"]
    assert sum(g["n"] for g in grupos) == len(hoja)
    g = next(g for g in grupos if g["n"] >= 39)
    en = hoja[(hoja["edad"] >= g["desde"]) & (hoja["edad"] < g["hasta"])]["valor"]
    assert g["p2_5"] == pytest.approx(np.percentile(en, 2.5, method="weibull"))
    assert g["p97_5"] == pytest.approx(np.percentile(en, 97.5, method="weibull"))


def test_grupo_chico_queda_sin_percentiles_y_se_dice():
    res = intervalos_por_edad(_edades(n=120), "edad", "valor", {"metodo": "grupos"})
    assert any(v.valor == "sin percentiles 2,5 y 97,5" for v in res.valores)
    assert not res.supuestos[0].ok


# ---------------- Informe, figuras y panel ----------------

@pytest.mark.parametrize("res", [
    intervalo_referencia(_sanos(), "x", {"inferior": 12.0, "superior": 38.0}),
    intervalos_por_edad(_edades(), "edad", "valor"),
    intervalos_por_edad(_edades(), "edad", "valor", {"metodo": "grupos"})],
    ids=["intervalo", "edad regresion", "edad grupos"])
def test_informe_y_figuras(res):
    import matplotlib.pyplot as plt
    assert res.ok, res.error
    t = _texto(res)
    assert "Qué se verificó" in t and "significativ" not in t.lower()
    for figura in res.figuras:
        plt.close(figura.dibujar())


@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_el_panel_verifica_con_los_limites_del_dialogo(qt_app):
    from src.ui.analysis_panel import AnalysisPanel
    panel = AnalysisPanel()
    panel.set_data(_sanos())
    panel.combo_analysis.setCurrentText("Intervalos de referencia")
    panel.combo_col1.setCurrentText("x")
    panel.parametros = {"inferior": "12", "superior": "38"}
    panel._run()
    assert "¿Se verifica el intervalo publicado?" in panel.txt_results.toPlainText()


@pytest.mark.parametrize("metodo", ["regresion", "grupos"])
def test_el_panel_por_edad(qt_app, metodo):
    from src.ui.analysis_panel import AnalysisPanel
    panel = AnalysisPanel()
    panel.set_data(_edades())
    panel.combo_analysis.setCurrentText("Edad-relacionada")
    panel.combo_col1.setCurrentText("edad")
    panel.combo_col2.setCurrentText("valor")
    panel.opciones_metodo = {"metodo": metodo}
    panel._run()
    assert "Qué se verificó y qué se decidió" in panel.txt_results.toPlainText()
