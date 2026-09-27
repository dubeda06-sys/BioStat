"""El asistente B «Validar un método»: EP09c + EP15-A3 en un veredicto.

Lo que se prueba: que la recta la elija la misma regla que el Omnianálisis (una
sola verdad), que el sesgo en los niveles salga de la recta que se muestra, que
su IC cubra lo que dice cubrir, y que el veredicto siga la lógica de
equivalencia contra el sesgo permitido.
"""
import os
import re
from html import unescape

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.analysis.omni_analyzer import concordance_analysis  # noqa: E402
from src.analysis.omni_config import DEFAULT_CONFIG as CFG  # noqa: E402
from src.core.ep09 import (  # noqa: E402
    CUMPLE, NO_CONCLUYENTE, NO_CUMPLE, NO_EVALUABLE, regla_ep09, sesgo_en_niveles, veredicto,
)
from src.resultado import render_html  # noqa: E402
from src.resultado.constructores import validar_metodo  # noqa: E402
from tests.test_ep15 import CORRIDAS  # noqa: E402

NIVELES = [50, 100, 150]


def _texto(res):
    return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", render_html(res)))).strip()


def _hoja(semilla=1, n=60, pendiente=1.02, de=2.0):
    rng = np.random.default_rng(semilla)
    v = rng.uniform(20, 200, n)
    return pd.DataFrame({"Viejo": v + rng.normal(0, de, n),
                         "Nuevo": pendiente * v + rng.normal(0, de, n)})


def _paso(res, texto):
    return next(s for s in res.supuestos if texto in s.pregunta)


# ---------------- La regla y el veredicto ----------------

@pytest.mark.parametrize("ic, permitido, esperado", [
    ((-1.0, 1.0), 2.0, CUMPLE),
    ((2.5, 4.0), 2.0, NO_CUMPLE),
    ((-4.0, -2.5), 2.0, NO_CUMPLE),
    ((1.0, 3.0), 2.0, NO_CONCLUYENTE),
    ((-3.0, 3.0), 2.0, NO_CONCLUYENTE),
    ((np.nan, 1.0), 2.0, NO_EVALUABLE),
    ((-1.0, 1.0), 0.0, NO_EVALUABLE),
])
def test_veredicto_por_equivalencia(ic, permitido, esperado):
    assert veredicto(*ic, permitido) == esperado


def test_la_regla_de_ep09():
    assert regla_ep09("DE constante", True) == "deming"
    assert regla_ep09("CV constante", True) == "deming_ponderado"
    assert regla_ep09("mixta", True) == "passing_bablok"
    assert regla_ep09("DE constante", False) == "passing_bablok"


def _hoja_cv(semilla=4, n=80):
    rng = np.random.default_rng(semilla)
    v = rng.uniform(5, 400, n)
    return pd.DataFrame({"Viejo": v * (1 + rng.normal(0, 0.05, n)),
                         "Nuevo": v * (1 + rng.normal(0, 0.05, n))})


def _hoja_mixta(semilla=3, n=120):
    rng = np.random.default_rng(semilla)
    v = rng.uniform(1, 400, n)
    sd = np.where(v < 100, 3.0, 0.03 * v)
    return pd.DataFrame({"Viejo": v + rng.normal(0, 1, n) * sd,
                         "Nuevo": v + rng.normal(0, 1, n) * sd})


@pytest.mark.parametrize("hoja, esperado", [
    (_hoja(), "Deming"), (_hoja_cv(), "Deming ponderado"), (_hoja_mixta(), "Passing-Bablok"),
])
def test_elige_la_misma_recta_que_el_omnianalisis(hoja, esperado):
    """Una sola verdad: el panel y el Omnianálisis, con los mismos datos y el
    comparativo declarado como referencia, eligen la misma recta."""
    res = validar_metodo(hoja, "Viejo", "Nuevo", {"niveles": NIVELES})
    omni = concordance_analysis("Viejo", hoja["Viejo"], "Nuevo", hoja["Nuevo"], CFG,
                                referencia="Viejo")
    assert omni["resultados"]["regresion"]["metodo"] == esperado
    assert res.crudo["sesgos"]["metodo"] == {"Deming": "deming",
                                             "Deming ponderado": "deming_ponderado",
                                             "Passing-Bablok": "passing_bablok"}[esperado]


def test_el_sesgo_sale_de_la_recta_que_se_muestra():
    res = validar_metodo(_hoja(), "Viejo", "Nuevo", {"niveles": NIVELES})
    recta = next(p for p in res.partes if p.analisis == "deming").crudo["deming"]
    b, a = recta["slope"], recta["intercept"]
    for fila in res.crudo["niveles"]:
        assert fila["sesgo"] == pytest.approx(a + (b - 1) * fila["nivel"], rel=1e-10)


# ---------------- Cobertura del IC del sesgo ----------------

def _cobertura(metodo, reps, b):
    rng = np.random.default_rng(0)
    niveles = np.array([40.0, 100.0, 160.0])
    verdadero = 2 + 0.05 * niveles
    cubre = np.zeros(3)
    for _ in range(reps):
        v = rng.uniform(20, 200, 40)
        x, y = v + rng.normal(0, 3, 40), 2 + 1.05 * v + rng.normal(0, 3, 40)
        r = sesgo_en_niveles(x, y, metodo, niveles, b=b, semilla=int(rng.integers(1e9)))
        cubre += (np.array(r["ic_inf"]) <= verdadero) & (verdadero <= np.array(r["ic_sup"]))
    return cubre / reps


def test_el_ic_de_deming_cubre_el_95():
    """Jackknife con t(N−2): 94,5 a 97 % en la simulación de referencia."""
    assert np.all(np.abs(_cobertura("deming", 300, 0) - 0.95) < 0.035)


def test_el_ic_de_passing_bablok_cubre_el_95():
    assert np.all(np.abs(_cobertura("passing_bablok", 120, 300) - 0.95) < 0.05)


def test_el_bootstrap_es_reproducible():
    h = _hoja_mixta()
    a = validar_metodo(h, "Viejo", "Nuevo", {"niveles": NIVELES}).crudo["sesgos"]
    b = validar_metodo(h, "Viejo", "Nuevo", {"niveles": NIVELES}).crudo["sesgos"]
    assert a["ic_inf"] == b["ic_inf"] and a["ic_sup"] == b["ic_sup"]


# ---------------- El veredicto del asistente ----------------

@pytest.mark.parametrize("permitido, esperado", [
    (None, None), (5.0, CUMPLE), (1.0, NO_CUMPLE), (3.0, NO_CONCLUYENTE),
])
def test_veredicto_unico(permitido, esperado):
    """Un método que lee 2 % alto, contra cuatro criterios."""
    res = validar_metodo(_hoja(), "Viejo", "Nuevo",
                         {"sesgo_permitido": permitido, "niveles": NIVELES})
    assert res.ok and res.crudo["veredicto"] == esperado
    if esperado is None:
        assert res.lectura.startswith("Sin sesgo permitido no hay veredicto")
        assert _paso(res, "Contra qué").respuesta == "Sin criterio"
    else:
        assert res.valores[0].valor == esperado


def test_el_permitido_en_unidades_es_fijo():
    res = validar_metodo(_hoja(), "Viejo", "Nuevo", {"sesgo_permitido": 5.0,
                                                     "escala_permitido": "unidades",
                                                     "niveles": NIVELES})
    assert [f["permitido"] for f in res.crudo["niveles"]] == [5.0, 5.0, 5.0]


def test_sin_niveles_usa_los_cuartiles_y_lo_dice():
    h = _hoja()
    res = validar_metodo(h, "Viejo", "Nuevo", {"sesgo_permitido": 5.0})
    niveles = [f["nivel"] for f in res.crudo["niveles"]]
    assert niveles == pytest.approx(list(np.percentile(h["Viejo"], [25, 50, 75])))
    paso = _paso(res, "Contra qué")
    assert "cuartiles" in paso.medicion and not paso.ok


def test_una_curva_no_puede_cumplir():
    """Con la relación curva, el sesgo de una recta no vale en todo el rango."""
    rng = np.random.default_rng(12)
    v = rng.uniform(10, 100, 60)
    h = pd.DataFrame({"Viejo": v + rng.normal(0, 2, 60),
                      "Nuevo": v + 0.3 * (v - 55) ** 2 / 55 + rng.normal(0, 2, 60)})
    res = validar_metodo(h, "Viejo", "Nuevo", {"sesgo_permitido": 50.0})
    assert _paso(res, "lineal").respuesta == "Se detectó desvío"
    assert res.crudo["veredicto"] != CUMPLE
    assert "no parece lineal" in res.lectura


def test_pocas_muestras_se_avisan():
    res = validar_metodo(_hoja(n=25), "Viejo", "Nuevo", {"sesgo_permitido": 5.0})
    paso = _paso(res, "muestras suficientes")
    assert paso.respuesta == "No" and "40" in paso.medicion


# ---------------- Con la precisión de EP15 ----------------

def _hoja_con_corridas():
    h = _hoja()
    for j, corrida in enumerate(CORRIDAS, start=1):
        h[f"Día {j}"] = pd.Series(corrida, dtype=float)
    return h


def test_la_precision_entra_como_parte():
    res = validar_metodo(_hoja_con_corridas(), "Viejo", "Nuevo",
                         {"sesgo_permitido": 5.0, "niveles": NIVELES,
                          "corridas": [f"Día {j}" for j in range(1, 6)],
                          "declaracion": "cv", "sigma_r": 2.0, "sigma_wl": 3.4})
    assert [p.analisis for p in res.partes][-1] == "precision_ep15"
    assert _paso(res, "precisión verifica").respuesta == "Sí"
    assert res.crudo["veredicto"] == CUMPLE
    assert "la precisión verificó" in res.lectura


def test_una_precision_que_no_verifica_no_cumple():
    res = validar_metodo(_hoja_con_corridas(), "Viejo", "Nuevo",
                         {"sesgo_permitido": 5.0, "niveles": NIVELES,
                          "corridas": [f"Día {j}" for j in range(1, 6)],
                          "sigma_r": 0.8, "sigma_wl": 1.0})
    assert res.crudo["veredicto"] == NO_CUMPLE
    assert "no se verificó" in res.lectura


def test_corridas_sin_declaracion_no_entran_al_veredicto():
    res = validar_metodo(_hoja_con_corridas(), "Viejo", "Nuevo",
                         {"sesgo_permitido": 5.0, "niveles": NIVELES,
                          "corridas": [f"Día {j}" for j in range(1, 6)]})
    assert _paso(res, "precisión verifica").respuesta == "Sin declaración"
    assert res.crudo["veredicto"] == CUMPLE


# ---------------- El informe ----------------

def test_el_informe_lleva_cada_analisis_debajo():
    res = validar_metodo(_hoja(), "Viejo", "Nuevo", {"sesgo_permitido": 5.0,
                                                     "niveles": NIVELES})
    t = _texto(res)
    assert "De dónde sale" in t
    for titulo in ("Bland-Altman", "Deming", "Passing-Bablok"):
        assert titulo in t
    assert [p.analisis for p in res.partes] == ["bland_altman", "deming", "passing_bablok"]
    assert "significativ" not in t.lower()


def test_las_figuras_se_dibujan():
    import matplotlib.pyplot as plt
    res = validar_metodo(_hoja(), "Viejo", "Nuevo", {"sesgo_permitido": 5.0,
                                                     "niveles": NIVELES})
    assert len(res.figuras) == 3
    for figura in res.figuras:
        fig = figura.dibujar()
        assert fig.axes
        plt.close(fig)


@pytest.mark.parametrize("args, opciones, motivo", [
    (("Viejo", "Viejo"), {}, "misma columna"),
    (("Viejo", "Otro"), {}, "no está en la hoja"),
    (("Viejo", "Nuevo"), {"sesgo_permitido": -1}, "positivo"),
    (("Viejo", "Nuevo"), {"sesgo_permitido": "mucho"}, "tienen que ser números"),
])
def test_rechazos_con_motivo(args, opciones, motivo):
    res = validar_metodo(_hoja(), *args, opciones)
    assert not res.ok and motivo in res.error
