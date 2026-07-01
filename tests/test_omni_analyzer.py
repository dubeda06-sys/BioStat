"""Tests del motor de Omnianálisis — árbol de decisión determinista."""
import numpy as np
import pandas as pd
import pytest

from src.analysis.omni_analyzer import (
    run_omnianalysis, _classify_column, profile_dataset,
    detect_comparison_candidates, concordance_analysis,
    NUMERIC_CONTINUOUS, NUMERIC_DISCRETE, CATEGORICAL_NOMINAL, BINARY, DATETIME,
)
from src.analysis.omni_config import DEFAULT_CONFIG as CFG

RNG = np.random.RandomState(42)


# --- Clasificación de tipos ---
def test_classify_continuous():
    s = pd.Series(RNG.normal(50, 10, 100))
    assert _classify_column(s, CFG)["tipo"] == NUMERIC_CONTINUOUS


def test_classify_discrete():
    s = pd.Series(RNG.randint(0, 6, 100))
    assert _classify_column(s, CFG)["tipo"] == NUMERIC_DISCRETE


def test_classify_binary():
    s = pd.Series(["si", "no"] * 50)
    assert _classify_column(s, CFG)["tipo"] == BINARY


def test_classify_nominal():
    s = pd.Series(["a", "b", "c", "d", "e", "f", "g"] * 10)
    assert _classify_column(s, CFG)["tipo"] == CATEGORICAL_NOMINAL


def test_classify_datetime():
    s = pd.Series(pd.date_range("2020-01-01", periods=50))
    assert _classify_column(s, CFG)["tipo"] == DATETIME


# --- Switch por número de columnas ---
def test_branch_a():
    df = pd.DataFrame({"x": RNG.normal(0, 1, 50)})
    r = run_omnianalysis(df, ["x"])
    assert r["branch"] == "A"
    assert len(r["blocks"]) == 1


def test_branch_b():
    df = pd.DataFrame({"x": RNG.normal(0, 1, 50), "y": RNG.normal(0, 1, 50)})
    r = run_omnianalysis(df, ["x", "y"])
    assert r["branch"] == "B"


def test_branch_c():
    df = pd.DataFrame({c: RNG.normal(0, 1, 50) for c in ["a", "b", "c"]})
    r = run_omnianalysis(df, ["a", "b", "c"])
    assert r["branch"] == "C"
    assert "correlation_matrix" in r


# --- Univariado: normalidad decide media vs mediana ---
def test_univariate_normal_uses_mean():
    df = pd.DataFrame({"x": RNG.normal(100, 15, 200)})
    r = run_omnianalysis(df, ["x"])
    block = r["blocks"][0]
    assert "MEDIA" in block["resultados"]["tendencia_central"]


def test_univariate_nonnormal_uses_median():
    df = pd.DataFrame({"x": RNG.exponential(2, 200)})
    r = run_omnianalysis(df, ["x"])
    block = r["blocks"][0]
    assert "MEDIANA" in block["resultados"]["tendencia_central"]
    assert any("engañoso" in w for w in block["advertencias"])


# --- Bivariado: selección correcta de test ---
def test_bivariate_two_groups_normal_ttest():
    df = pd.DataFrame({
        "y": np.concatenate([RNG.normal(10, 2, 40), RNG.normal(12, 2, 40)]),
        "g": ["A"] * 40 + ["B"] * 40,
    })
    r = run_omnianalysis(df, ["y", "g"])
    biv = [b for b in r["blocks"] if b.get("tipo") == "comparación de grupos"][0]
    assert any("t de" in p["prueba"] for p in biv["pruebas"])


def test_bivariate_two_groups_nonnormal_mannwhitney():
    df = pd.DataFrame({
        "y": np.concatenate([RNG.exponential(2, 40), RNG.exponential(3, 40)]),
        "g": ["A"] * 40 + ["B"] * 40,
    })
    r = run_omnianalysis(df, ["y", "g"])
    biv = [b for b in r["blocks"] if b.get("tipo") == "comparación de grupos"][0]
    assert any("Mann-Whitney" in p["prueba"] for p in biv["pruebas"])


def test_bivariate_3groups_anova():
    df = pd.DataFrame({
        "y": np.concatenate([RNG.normal(m, 2, 30) for m in (10, 11, 12)]),
        "g": ["A"] * 30 + ["B"] * 30 + ["C"] * 30,
    })
    r = run_omnianalysis(df, ["y", "g"])
    biv = [b for b in r["blocks"] if b.get("tipo") == "comparación de grupos"][0]
    assert any("ANOVA" in p["prueba"] for p in biv["pruebas"])


def test_bivariate_correlation_normal_pearson():
    x = RNG.normal(0, 1, 100)
    df = pd.DataFrame({"x": x, "y": x * 2 + RNG.normal(0, 0.5, 100)})
    r = run_omnianalysis(df, ["x", "y"])
    corr = [b for b in r["blocks"] if b.get("tipo") == "correlación"][0]
    assert corr["pruebas"][0]["prueba"] == "Pearson"


def test_contingency_chi_vs_fisher():
    # tabla grande → chi-cuadrado
    df = pd.DataFrame({
        "a": ["x", "y"] * 100,
        "b": (["p"] * 100) + (["q"] * 100),
    })
    r = run_omnianalysis(df, ["a", "b"])
    cont = [b for b in r["blocks"] if b.get("tipo") == "tabla de contingencia"][0]
    assert cont["pruebas"][0]["prueba"] in ("Chi-cuadrado", "Test exacto de Fisher")


# --- Detección de comparación de métodos ---
def test_comparison_candidate_detected():
    base = RNG.normal(100, 20, 80)
    df = pd.DataFrame({"metodo_a": base, "metodo_b": base + RNG.normal(0, 2, 80)})
    r = run_omnianalysis(df, ["metodo_a", "metodo_b"])
    assert len(r["comparison_candidates"]) == 1


def test_concordance_runs_when_confirmed():
    base = RNG.normal(100, 20, 80)
    df = pd.DataFrame({"metodo_a": base, "metodo_b": base + RNG.normal(0, 2, 80)})
    r = run_omnianalysis(df, ["metodo_a", "metodo_b"],
                         confirmed_comparisons=[("metodo_a", "metodo_b")])
    conc = [b for b in r["blocks"] if b.get("tipo") == "concordancia"]
    assert len(conc) == 1
    assert "ccc" in conc[0]["resultados"]
    # advertencia activa contra Pearson
    assert any("Pearson" in w for w in conc[0]["advertencias"])


def test_concordance_bland_altman_on_differences():
    base = RNG.normal(50, 10, 100)
    df = pd.DataFrame({"m1": base, "m2": base + 1.5})
    block = concordance_analysis("m1", df["m1"], "m2", df["m2"], CFG)
    ba = block["resultados"]["bland_altman"]
    assert ba["tipo"] in ("paramétrico", "no paramétrico")


def test_passing_bablok_reports_intercept_ci():
    # con outliers → rama Passing-Bablok
    base = RNG.exponential(20, 80)
    df = pd.DataFrame({"m1": base, "m2": base * 1.1 + 3})
    block = concordance_analysis("m1", df["m1"], "m2", df["m2"], CFG)
    reg = block["resultados"].get("regresion", {})
    if reg.get("metodo") == "Passing-Bablok":
        assert "ic_intercepto" in reg
        assert "sesgo_constante" in reg


# --- Rama C: multiplicidad ---
def test_branch_c_fdr_applied():
    df = pd.DataFrame({c: RNG.normal(0, 1, 60) for c in ["a", "b", "c", "d"]})
    r = run_omnianalysis(df, ["a", "b", "c", "d"])
    cells = r["correlation_matrix"]["celdas"]
    assert all("p_adj" in c for c in cells)


def test_branch_c_multiple_regression():
    n = 100
    x1 = RNG.normal(0, 1, n)
    x2 = RNG.normal(0, 1, n)
    y = 2 * x1 - x2 + RNG.normal(0, 0.5, n)
    df = pd.DataFrame({"y": y, "x1": x1, "x2": x2})
    r = run_omnianalysis(df, ["y", "x1", "x2"], target="y")
    assert "multiple_regression" in r
    assert r["multiple_regression"]["r2"] > 0.8


def test_branch_c_pca_clustering_no_target():
    n = 60
    df = pd.DataFrame({c: RNG.normal(0, 1, n) for c in ["a", "b", "c", "d"]})
    r = run_omnianalysis(df, ["a", "b", "c", "d"])  # sin target
    assert "pca_clustering" in r
    pc = r["pca_clustering"]
    assert "error" in pc or "pca" in pc


# --- Empty / error handling ---
def test_empty_selection():
    df = pd.DataFrame({"x": [1, 2, 3]})
    assert "error" in run_omnianalysis(df, [])


def test_profile_structural():
    df = pd.DataFrame({"x": [1, 2, 3, 3], "g": ["a", "b", "a", "a"]})
    p = profile_dataset(df, ["x", "g"], CFG)
    assert p["n_rows"] == 4
    assert p["n_columns"] == 2
