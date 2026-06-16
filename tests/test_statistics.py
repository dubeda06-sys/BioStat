"""Pruebas para el modulo de estadisticas."""
import pytest
import numpy as np
import pandas as pd
from src.core.statistics import descriptive_stats, t_test_paired, t_test_independent


class TestDescriptiveStats:
    def test_basic_stats(self):
        data = pd.Series([1, 2, 3, 4, 5])
        result = descriptive_stats(data)
        assert result['mean'] == 3.0
        assert result['median'] == 3.0
        assert result['std'] == pytest.approx(1.5811, rel=1e-2)

    def test_empty_data(self):
        data = pd.Series([])
        result = descriptive_stats(data)
        assert result is None


class TestTTest:
    def test_paired_ttest(self):
        data1 = pd.Series([1.2, 2.5, 3.1, 4.8, 5.3, 6.7, 7.2])
        data2 = pd.Series([2.1, 3.6, 2.9, 5.5, 4.8, 7.3, 8.1])
        t_stat, p_value = t_test_paired(data1, data2)
        assert isinstance(t_stat, float)
        assert isinstance(p_value, float)

    def test_independent_ttest(self):
        data1 = pd.Series([1, 2, 3, 4, 5])
        data2 = pd.Series([6, 7, 8, 9, 10])
        t_stat, p_value = t_test_independent(data1, data2)
        assert isinstance(t_stat, float)
        assert isinstance(p_value, float)
