"""Pruebas de los metodos agregados: Kendall tau, comparacion de
correlaciones independientes (Fisher r-a-z) y Bartlett."""
import numpy as np
import pytest

from src.core.statistics import kendall_tau, compare_correlations, bartlett_test


class TestKendallTau:
    def test_perfect_monotonic(self):
        x = np.arange(1, 21, dtype=float)
        y = x ** 2
        r = kendall_tau(x, y, n_boot=400)
        assert r["tau"] == pytest.approx(1.0, abs=1e-9)
        assert r["p"] < 0.01
        assert r["n"] == 20
        assert r["ci95"][1] <= 1.0

    def test_deterministic_ci(self):
        rng = np.random.default_rng(0)
        x = rng.normal(size=40)
        y = 0.6 * x + rng.normal(size=40)
        assert kendall_tau(x, y, n_boot=600, seed=7)["ci95"] == \
               kendall_tau(x, y, n_boot=600, seed=7)["ci95"]

    def test_too_few_returns_none(self):
        assert kendall_tau([1, 2], [1, 2]) is None

    def test_ignores_nan(self):
        x = [1.0, 2.0, np.nan, 4.0, 5.0, 6.0]
        y = [2.0, 1.0, 5.0, 4.0, 3.0, 7.0]
        assert kendall_tau(x, y, n_boot=200)["n"] == 5


class TestCompareCorrelations:
    def test_equal(self):
        r = compare_correlations(0.5, 100, 0.5, 100)
        assert r["z"] == pytest.approx(0.0, abs=1e-9)
        assert r["p"] == pytest.approx(1.0, abs=1e-9)

    def test_different(self):
        r = compare_correlations(0.8, 80, 0.2, 80)
        assert abs(r["z"]) > 3 and r["p"] < 0.01
        assert r["diff"] == pytest.approx(0.6)

    def test_known_value(self):
        r = compare_correlations(0.6, 53, 0.3, 53)
        ee = np.sqrt(1 / 50 + 1 / 50)
        assert r["z"] == pytest.approx((np.arctanh(0.6) - np.arctanh(0.3)) / ee, rel=1e-9)

    def test_guards(self):
        assert compare_correlations(0.5, 3, 0.5, 50) is None
        assert compare_correlations(1.0, 50, 0.5, 50) is None


class TestBartlett:
    def test_equal_variances(self):
        rng = np.random.default_rng(1)
        r = bartlett_test([rng.normal(0, 1, 60), rng.normal(0, 1, 60), rng.normal(0, 1, 60)])
        assert r["k"] == 3 and r["equal_var"] is True

    def test_unequal_variances(self):
        rng = np.random.default_rng(2)
        r = bartlett_test([rng.normal(0, 1, 60), rng.normal(0, 5, 60)])
        assert r["p"] < 0.05 and r["equal_var"] is False

    def test_too_few_groups(self):
        assert bartlett_test([[1, 2, 3]]) is None
