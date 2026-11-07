"""Las fórmulas del árbol deben poder renderizarse con mathtext (sin LaTeX
instalado) y cubrir todo el catálogo; las sustituciones deben dar números
coherentes con el cálculo del motor."""
import numpy as np
import pandas as pd
import pytest
from matplotlib.mathtext import MathTextParser

from src.analysis.omni_catalogo import ENSAYOS
from src.analysis.omni_formulas import FORMULAS, ensayo_de_texto

_PARSER = MathTextParser("agg")


def _render(latex):
    _PARSER.parse(f"${latex}$", dpi=72)


def test_todo_el_catalogo_tiene_formula():
    faltan = [e.id for e in ENSAYOS if e.id not in FORMULAS]
    assert faltan == []


@pytest.mark.parametrize("id_", sorted(FORMULAS))
def test_formulas_generales_renderizan(id_):
    f = FORMULAS[id_]
    assert f.que
    assert f.general or f.iterativo, "sin fórmula ni pasos"
    for _rotulo, latex in f.general:
        _render(latex)
    for latex, _significado in f.simbolos:
        _render(latex)
    if f.iterativo:
        assert f.pasos


def _valores_corrida():
    """Corre el motor real y junta los valores guardados por ensayo."""
    from src.analysis.omni_analyzer import run_omnianalysis
    from src.analysis.omni_auditoria import auditar
    rng = np.random.default_rng(3)
    dfs = [
        pd.DataFrame({"g": ["A"] * 40 + ["B"] * 40,
                      "y": np.r_[rng.normal(10, 2, 40), rng.normal(12, 2, 40)]}),
        pd.DataFrame({"g": ["A"] * 40 + ["B"] * 40,
                      "y": np.r_[rng.exponential(2, 40), rng.exponential(3, 40)]}),
        pd.DataFrame({"g": rng.choice(["A", "B", "C"], 90), "y": rng.normal(50, 5, 90)}),
        pd.DataFrame({"x": rng.normal(0, 1, 50), "y": rng.normal(0, 1, 50)}),
        pd.DataFrame({"a": rng.choice(["s", "n"], 200), "b": rng.choice(["x", "y", "z"], 200)}),
        pd.DataFrame({"a": ["s"] * 6 + ["n"] * 6, "b": ["x"] * 5 + ["y"] + ["x"] + ["y"] * 5}),
    ]
    vistos = {}
    for df in dfs:
        aud = auditar(run_omnianalysis(df, list(df.columns), confirmed_comparisons=[]))
        for fila in aud["filas"]:
            for ex in fila.get("ejecuciones", []):
                if ex.get("valores"):
                    vistos.setdefault(fila["id"], ex["valores"])
    return vistos


def test_sustituciones_reales_renderizan():
    vistos = _valores_corrida()
    assert len(vistos) >= 8
    for id_, valores in vistos.items():
        f = FORMULAS[id_]
        assert f.sustituir is not None, f"{id_} guarda valores pero no los sustituye"
        for _rotulo, latex in f.sustituir(valores):
            _render(latex)


def test_sustitucion_media_coincide():
    v = {"n": 4, "suma": 10.0, "media": 2.5, "ds": 1.2910, "ss": 5.0}
    lineas = FORMULAS["desc_numericos"].sustituir(v)
    assert "10" in lineas[0][1] and "2.5" in lineas[0][1]
    assert "5" in lineas[1][1] and "3" in lineas[1][1]


@pytest.mark.parametrize("texto, esperado", [
    ("Prueba de Levene: p=0.03", "levene"),
    ("t de Welch: t=2.1, p=0.04", "t_welch"),
    ("ANOVA de Welch: F=3.2", "anova_welch"),
    ("Mann-Whitney U: p<0.001", "mann_whitney"),
    ("Shapiro-Wilk: W=0.98", "shapiro"),
    ("Bland-Altman no paramétrico", "ba_no_parametrico"),
    ("algo sin prueba", None),
])
def test_ensayo_de_texto(texto, esperado):
    assert ensayo_de_texto(texto) == esperado
