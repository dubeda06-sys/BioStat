"""Tests for new features added to BioStat."""
import pytest
import numpy as np
import pandas as pd


class TestTwoWayAnova:
    def test_basic_two_way(self):
        from src.core.two_way_anova import two_way_anova
        rng = np.random.RandomState(0)
        # Diseño balanceado 2x2 con 6 réplicas por celda
        A = np.repeat([0, 1], 12)
        B = np.tile(np.repeat([0, 1], 6), 2)
        y = 1.0 * A + 0.0 * B + rng.normal(0, 0.3, 24)
        result = two_way_anova(y, A, B)
        assert 'F_A' in result and 'p_A' in result
        assert 'F_B' in result and 'p_B' in result
        assert 'F_AB' in result and 'p_AB' in result
        assert result['df_error'] > 0


class TestAncova:
    def test_basic_ancova(self):
        from src.core.ancova import ancova
        dependent = np.array([2, 4, 5, 7, 8, 3, 5, 6, 8, 9])
        group = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])
        covariate = np.array([1, 2, 3, 4, 5, 2, 3, 4, 5, 6])
        result = ancova(dependent, group, covariate)
        assert 'F' in result
        assert 'p' in result
        assert 'eta_squared' in result
        assert 0 <= result['eta_squared'] <= 1


class TestRepeatedMeasures:
    def test_basic_repeated(self):
        from src.core.repeated_measures import repeated_measures_anova
        data = np.array([
            [5, 6, 7],
            [4, 5, 6],
            [6, 7, 8],
            [3, 4, 5],
            [7, 8, 9]
        ])
        result = repeated_measures_anova(data)
        assert 'F' in result
        assert 'p' in result
        assert 'epsilon' in result
        assert 0 <= result['epsilon'] <= 1


class TestCoxRegression:
    def test_basic_cox(self):
        from src.core.cox_regression import cox_regression
        times = np.array([1, 2, 3, 4, 5, 6, 7, 8])
        events = np.array([1, 0, 1, 1, 0, 1, 0, 1])
        covariates = np.array([[1, 0], [0, 1], [1, 0], [0, 1], [1, 0], [0, 1], [1, 0], [0, 1]])
        result = cox_regression(times, events, covariates)
        assert 'hazard_ratios' in result
        assert 'p_values' in result
        assert 'log_likelihood' in result
        assert len(result['hazard_ratios']) == 2


class TestProbit:
    def test_basic_probit(self):
        from src.core.probit import probit_regression
        X = np.array([[1], [2], [3], [4], [5], [6], [7], [8]])
        y = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        result = probit_regression(X, y)
        assert 'coefficients' in result
        assert 'p_values' in result
        assert 'predictions' in result
        assert len(result['coefficients']) == 2


class TestCMH:
    def test_basic_cmh(self):
        from src.core.cmh import cmh_test
        tables = np.array([
            [[10, 20], [30, 40]],
            [[15, 25], [35, 45]]
        ])
        result = cmh_test(tables)
        assert 'cmh_statistic' in result
        assert 'p_value' in result
        assert 'common_odds_ratio' in result
        assert result['K'] == 2


class TestSerialMeasurements:
    def test_basic_serial(self):
        from src.core.serial_measurements import serial_measurements_summary
        data = np.array([
            [1, 2, 3, 4],
            [2, 3, 4, 5],
            [3, 4, 5, 6],
        ])
        result = serial_measurements_summary(data)
        assert 'means' in result
        assert 'slopes' in result
        assert 'overall_slope' in result
        assert len(result['means']) == 4


class TestPlots:
    def test_youden_data(self):
        from src.core.plots import youden_data
        y_true = np.array([0, 0, 1, 1, 0, 1, 0, 1])
        y_score = np.array([0.1, 0.4, 0.35, 0.8, 0.4, 0.9, 0.2, 0.7])
        result = youden_data(y_true, y_score)
        assert 'thresholds' in result
        assert 'sensitivity' in result
        assert 'specificity' in result
        assert 'j_statistic' in result
        assert 'optimal_j' in result

    def test_polar_plot_data(self):
        from src.core.plots import polar_plot_data
        categories = ['A', 'B', 'C', 'D']
        values = [1, 2, 3, 4]
        result = polar_plot_data(categories, values)
        assert 'angles' in result
        assert 'values' in result
        assert len(result['angles']) == 5

    def test_waterfall_data(self):
        from src.core.plots import waterfall_data
        values = [10, -5, 8, -3, 15]
        result = waterfall_data(values)
        assert 'labels' in result
        assert 'values' in result
        assert 'starts' in result
        assert 'ends' in result
        assert result['values'][-1] == 25

    def test_mountain_plot_data(self):
        from src.core.plots import mountain_plot_data
        data = np.random.normal(0, 1, 100)
        result = mountain_plot_data(data)
        assert 'x' in result
        assert 'y_density' in result
        assert 'mean' in result
        assert 'sd' in result


class TestBlandAltmanMultiple:
    def test_basic_multiple(self):
        from src.core.bland_altman import bland_altman_multiple
        data = np.array([
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9],
            [10, 11, 12]
        ])
        result = bland_altman_multiple(data)
        assert 'comparisons' in result
        assert 'n_comparisons' in result
        assert result['n_comparisons'] == 3


class TestSampleSizeFixes:
    def test_sample_size_mean_zero_sd(self):
        from src.core.sample_size import sample_size_mean
        result = sample_size_mean(delta=1, sd=0)
        assert result is None

    def test_sample_size_proportions_equal(self):
        from src.core.sample_size import sample_size_proportions
        result = sample_size_proportions(p1=0.5, p2=0.5)
        assert result is None

    def test_sample_size_correlation_zero(self):
        from src.core.sample_size import sample_size_correlation
        result = sample_size_correlation(r=0)
        assert result is None


class TestStatisticsFixes:
    def test_sign_test_returns_valid_p(self):
        from src.core.statistics import sign_test
        d1 = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        d2 = np.array([2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
        result = sign_test(d1, d2)
        assert result is not None
        assert 0 <= result['p'] <= 1

    def test_partial_correlation_alignment(self):
        from src.core.statistics import partial_correlation
        x = np.array([1, 2, 3, 4, 5])
        y = np.array([2, 4, 5, 4, 5])
        z = np.array([1, 1, 2, 2, 3])
        result = partial_correlation(x, y, z)
        assert result is not None
        assert 'r_partial' in result
        assert -1 <= result['r_partial'] <= 1
