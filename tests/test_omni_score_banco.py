"""Banco sintético del puntaje de sospecha de comparación de métodos.

Con esto se calibraron el 27 sep los pesos de `omni_config` (el spec los dejó
«a calibrar»). No hay datos reales etiquetados en el repo: cuando los haya,
se agregan como casos acá y se recalibra con el mismo test.

- POSITIVOS: el mismo analito por dos métodos, con y sin unidad en el nombre,
  con nombres que no se parecen, con faltantes, con rango angosto.
- NEGATIVOS: pares que conviven en una hoja de laboratorio y NO son
  comparación de métodos.

Lo que salió de calibrar:

- La unidad compartida casi no discrimina (5 de los 9 negativos la
  comparten). Con el 2,0 del spec, glucosa contra colesterol y dos
  calibradores en Ct pasaban a candidatos. Queda en 0,5; la unidad DISTINTA
  resta 2,0.
- Umbral 3,5: todos los positivos pasan (mínimo 5,0); 7 de 9 negativos quedan
  abajo.
- Colesterol total contra LDL y AST contra ALT siguen como candidatos: son
  analitos correlacionados en la misma unidad, y ninguna regla sin semántica
  los separa de dos métodos. Ya lo eran antes. Por eso el motor pregunta en
  vez de decidir.
"""
import numpy as np
import pandas as pd
import pytest

from src.analysis.omni_analyzer import _comparison_score, _unidad_declarada
from src.analysis.omni_config import DEFAULT_CONFIG as CFG


def met(t, cv, r, sesgo=1.0, cte=0.0):
    return (cte + sesgo * t) * (1 + cv * r.standard_normal(len(t)))


def faltan(v, r, frac):
    v = v.copy()
    v[r.random(len(v)) < frac] = np.nan
    return v


POS = {
    "Glucosa A/B (mg/dL), +4 %": lambda r: ("Glucosa A (mg/dL)", "Glucosa B (mg/dL)",
        *(lambda t: (met(t, .03, r), met(t, .03, r, 1.04)))(r.uniform(60, 300, 40))),
    "Roche vs Abbott, sin unidad, +10 %": lambda r: ("Roche", "Abbott",
        *(lambda t: (met(t, .05, r), met(t, .05, r, 1.10)))(np.exp(r.uniform(1, 5, 40)))),
    "TSH ancho, CV 8 %": lambda r: ("TSH (mUI/L)", "TSH nuevo (mUI/L)",
        *(lambda t: (met(t, .08, r), met(t, .08, r)))(np.exp(r.uniform(np.log(.1), np.log(20), 40)))),
    "Hb lab vs POCT, faltantes": lambda r: ("Hb lab (g/dL)", "Hb POCT (g/dL)",
        *(lambda t: (met(t, .02, r), faltan(met(t, .04, r, 1, .3), r, .2)))(r.uniform(7, 17, 40))),
    "Na ISE directo/indirecto, rango angosto": lambda r: ("Na_ISE_directo", "Na_ISE_indirecto",
        *(lambda t: (met(t, .008, r), met(t, .008, r, 1, 2)))(r.uniform(128, 150, 40))),
    "Ct ensayo 1 vs 2": lambda r: ("ADV Ct kit 1", "ADV Ct kit 2",
        *(lambda t: (t + r.normal(0, .4, 40), t + 0.8 + r.normal(0, .4, 40)))(r.uniform(18, 36, 40))),
    "Metodo_A / Metodo_B": lambda r: ("Metodo_A", "Metodo_B",
        *(lambda t: (met(t, .04, r), met(t, .04, r, 0.95)))(r.uniform(5, 50, 40))),
}

NEG = {
    "Glucosa vs Colesterol (mg/dL)": lambda r: ("Glucosa (mg/dL)", "Colesterol (mg/dL)",
        r.uniform(70, 200, 40), r.uniform(150, 300, 40)),
    "Colesterol total vs LDL": lambda r: ("Colesterol total (mg/dL)", "LDL (mg/dL)",
        *(lambda tc: (tc, 0.65 * tc - 10 + r.normal(0, 8, 40)))(r.uniform(140, 320, 40))),
    "AST vs ALT (U/L)": lambda r: ("AST (U/L)", "ALT (U/L)",
        *(lambda z: (np.exp(3.2 + .5 * z + .3 * r.standard_normal(40)),
                     np.exp(3.3 + .6 * z + .35 * r.standard_normal(40))))(r.standard_normal(40))),
    "Edad vs Peso": lambda r: ("Edad", "Peso", r.uniform(18, 90, 40), r.normal(72, 12, 40)),
    "Hto % vs Hb g/dL": lambda r: ("Hematocrito (%)", "Hemoglobina (g/dL)",
        *(lambda hb: (3 * hb + r.normal(0, 1, 40), hb))(r.uniform(8, 17, 40))),
    "Calibrador A vs B (Ct)": lambda r: ("Calibrador A Ct", "Calibrador B Ct",
        *(lambda d: (24.7 + d + r.normal(0, .3, 40), 28.0 + d + r.normal(0, .4, 40)))(r.normal(0, .5, 40))),
    "Urea vs Creatinina (mg/dL)": lambda r: ("Urea (mg/dL)", "Creatinina (mg/dL)",
        r.uniform(15, 80, 40), r.uniform(.5, 2, 40)),
    "Control nivel 1 vs 2 mismo analito": lambda r: ("Glucosa control N1", "Glucosa control N2",
        r.normal(95, 3, 40), r.normal(260, 7, 40)),
    "Ferritina vs Hierro": lambda r: ("Ferritina (ng/mL)", "Hierro (ug/dL)",
        np.exp(r.uniform(2, 6, 40)), r.uniform(30, 180, 40)),
}



DIFICILES = {"Colesterol total vs LDL", "AST vs ALT (U/L)"}


def _puntajes(gen, semilla, reps=40):
    r = np.random.default_rng(semilla)
    out = []
    for _ in range(reps):
        c1, c2, a, b = gen(r)
        out.append(_comparison_score(c1, pd.Series(a), c2, pd.Series(b), CFG)["score"])
    return np.asarray(out)


@pytest.mark.parametrize("nombre", list(POS))
def test_toda_comparacion_de_metodos_supera_el_umbral(nombre):
    sc = _puntajes(POS[nombre], len(nombre))
    assert sc.min() >= CFG.SCORE_UMBRAL_COMPARACION + 1.0, (nombre, sc.min())


@pytest.mark.parametrize("nombre", [n for n in NEG if n not in DIFICILES])
def test_los_pares_que_no_son_comparacion_quedan_abajo(nombre):
    sc = _puntajes(NEG[nombre], len(nombre))
    assert np.mean(sc >= CFG.SCORE_UMBRAL_COMPARACION) <= 0.05, (nombre, sc.mean())


def test_los_dificiles_siguen_como_candidatos_y_por_eso_se_pregunta():
    for nombre in DIFICILES:
        sc = _puntajes(NEG[nombre], len(nombre))
        assert np.mean(sc >= CFG.SCORE_UMBRAL_COMPARACION) > 0.5, nombre


@pytest.mark.parametrize("nombre,unidad", [
    ("Glucosa (mg/dL)", "mg/dl"), ("Hb [g/dL]", "g/dl"), ("glu_mg_dl", "mg/dl"),
    ("TSH mUI/L", "mui/l"), ("Hematocrito %", "%"), ("ferritina_ng_ml", "ng/ml"),
    ("TSH (mIU/L)", "mui/l"), ("Metodo_A", None), ("Ct", None), ("Edad", None),
])
def test_unidad_declarada_en_el_nombre(nombre, unidad):
    assert _unidad_declarada(nombre) == unidad


def test_la_unidad_distinta_resta_y_la_unidad_no_cuenta_como_nombre_parecido():
    rng = np.random.default_rng(1)
    t = rng.uniform(60, 300, 40)
    a = pd.Series(t * (1 + 0.03 * rng.standard_normal(40)))
    b = pd.Series(t * (1 + 0.03 * rng.standard_normal(40)))
    igual = _comparison_score("Glucosa (mg/dL)", a, "Glucosa B (mg/dL)", b, CFG)
    distinta = _comparison_score("Glucosa (mg/dL)", a, "Glucosa B (mmol/L)", b, CFG)
    assert igual["score"] - distinta["score"] == pytest.approx(
        CFG.PESO_UNIDAD + CFG.PESO_UNIDAD_DISTINTA)
    ast = _comparison_score("AST (U/L)", a, "Colesterol (U/L)", b, CFG)
    assert "nombres de columna parecidos" not in ast["reasons"]


def test_pareado_suma_solo_con_los_faltantes_en_las_mismas_filas():
    rng = np.random.default_rng(2)
    t = rng.uniform(5, 50, 40)
    a = pd.Series(t * 1.01)
    b = pd.Series(t * 0.99)
    completo = _comparison_score("X", a, "Y", b, CFG)
    b2 = b.copy()
    b2.iloc[3] = np.nan
    desalineado = _comparison_score("X", a, "Y", b2, CFG)
    a2 = a.copy()
    a2.iloc[3] = np.nan
    alineado = _comparison_score("X", a2, "Y", b2, CFG)
    assert "mismo n y faltantes en las mismas filas" in completo["reasons"]
    assert "mismo n y faltantes en las mismas filas" not in desalineado["reasons"]
    assert "mismo n y faltantes en las mismas filas" in alineado["reasons"]


def test_la_auditoria_muestra_el_puntaje_de_cada_par():
    """Deuda de julio: la auditoría decía cuántos pares se puntuaron, no cuánto
    sacó cada uno."""
    from src.analysis.omni_analyzer import run_omnianalysis
    rng = np.random.default_rng(3)
    t = rng.uniform(60, 300, 40)
    df = pd.DataFrame({"Glucosa A (mg/dL)": t * (1 + 0.03 * rng.standard_normal(40)),
                       "Glucosa B (mg/dL)": t * (1 + 0.03 * rng.standard_normal(40)),
                       "Edad": rng.uniform(18, 90, 40)})
    rep = run_omnianalysis(df, list(df.columns))
    assert len(rep["comparison_scores"]) == 3
    marcas = [m for m in rep["ensayos"] if m["id"] == "score_comparacion"]
    assert len(marcas) == 3
    glucosa = next(m for m in marcas if "Edad" not in m["detalle"])
    assert "≥ 3.5" in glucosa["detalle"] and "misma unidad declarada" in glucosa["detalle"]
    assert all(" × " in m["detalle"] for m in marcas)
    assert [c["col1"] for c in rep["comparison_candidates"]] == ["Glucosa A (mg/dL)"]
