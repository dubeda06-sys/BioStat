"""Pruebas de los metodos agregados por gap-analysis vs MedCalc:
Kendall tau, comparacion de correlaciones (Fisher r-a-z) y Bartlett.
"""
import numpy as np
import pytest

from src.core.statistics import kendall_tau, compare_correlations, bartlett_test


class TestKendallTau:
    def test_perfect_monotonic(self):
        x = np.arange(1, 21, dtype=float)
        y = x ** 2  # monotona creciente -> tau = 1
        r = kendall_tau(x, y, n_boot=500)
        assert r is not None
        assert r["tau"] == pytest.approx(1.0, abs=1e-9)
        assert r["p"] < 0.01
        assert r["n"] == 20
        assert r["ci95"][0] <= 1.0 and r["ci95"][1] <= 1.0

    def test_deterministic_ci(self):
        rng = np.random.default_rng(0)
        x = rng.normal(size=40)
        y = 0.6 * x + rng.normal(size=40)
        a = kendall_tau(x, y, n_boot=800, seed=7)
        b = kendall_tau(x, y, n_boot=800, seed=7)
        assert a["ci95"] == b["ci95"]  # mismo seed -> mismo IC

    def test_too_few(self):
        assert kendall_tau([1, 2], [1, 2]) is None

    def test_handles_nan(self):
        x = [1.0, 2.0, np.nan, 4.0, 5.0, 6.0]
        y = [2.0, 1.0, 5.0, 4.0, 3.0, 7.0]
        r = kendall_tau(x, y, n_boot=300)
        assert r["n"] == 5


class TestCompareCorrelations:
    def test_equal_correlations(self):
        r = compare_correlations(0.5, 100, 0.5, 100)
        assert r["z"] == pytest.approx(0.0, abs=1e-9)
        assert r["p"] == pytest.approx(1.0, abs=1e-9)

    def test_clearly_different(self):
        r = compare_correlations(0.8, 80, 0.2, 80)
        assert abs(r["z"]) > 3
        assert r["p"] < 0.01
        assert r["diff"] == pytest.approx(0.6)

    def test_known_value(self):
        # Fisher z: atanh(0.6)-atanh(0.3) sobre se con n=53 c/u
        r = compare_correlations(0.6, 53, 0.3, 53)
        se = np.sqrt(1 / 50 + 1 / 50)
        expected_z = (np.arctanh(0.6) - np.arctanh(0.3)) / se
        assert r["z"] == pytest.approx(expected_z, rel=1e-9)

    def test_guards(self):
        assert compare_correlations(0.5, 3, 0.5, 50) is None
        assert compare_correlations(1.0, 50, 0.5, 50) is None


class TestBartlett:
    def test_equal_variances(self):
        rng = np.random.default_rng(1)
        g1 = rng.normal(0, 1, 60)
        g2 = rng.normal(0, 1, 60)
        g3 = rng.normal(0, 1, 60)
        r = bartlett_test([g1, g2, g3])
        assert r["k"] == 3
        assert r["equal_var"] is True

    def test_unequal_variances(self):
        rng = np.random.default_rng(2)
        g1 = rng.normal(0, 1, 60)
        g2 = rng.normal(0, 5, 60)
        r = bartlett_test([g1, g2])
        assert r["p"] < 0.05
        assert r["equal_var"] is False

    def test_too_few_groups(self):
        assert bartlett_test([[1, 2, 3]]) is None
