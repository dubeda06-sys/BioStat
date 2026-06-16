"""Repeated Measures ANOVA."""
import numpy as np
from scipy import stats


def repeated_measures_anova(data):
    """
    Repeated Measures ANOVA with Greenhouse-Geisser correction.

    Args:
        data: 2D array (subjects x time_points)

    Returns:
        dict with F statistic, p-value, and epsilon (GG correction)
    """
    data = np.asarray(data, dtype=float)
    n, k = data.shape

    grand_mean = np.mean(data)
    subject_means = np.mean(data, axis=1)
    time_means = np.mean(data, axis=0)

    ss_total = np.sum((data - grand_mean) ** 2)
    ss_subjects = k * np.sum((subject_means - grand_mean) ** 2)
    ss_time = n * np.sum((time_means - grand_mean) ** 2)
    ss_error = ss_total - ss_subjects - ss_time

    df_time = k - 1
    df_error_time = (n - 1) * (k - 1)

    ms_time = ss_time / df_time if df_time > 0 else 0
    ms_error = ss_error / df_error_time if df_error_time > 0 else 1

    f_time = ms_time / ms_error if ms_error > 0 else 0
    p_time = 1 - stats.f.cdf(f_time, df_time, df_error_time) if df_time > 0 and df_error_time > 0 else 1

    epsilon = 1.0
    if k > 2:
        diff = data - time_means
        cov_matrix = np.cov(diff.T)
        epsilon_num = np.trace(cov_matrix) ** 2
        epsilon_den = (k - 1) * np.sum(cov_matrix ** 2)
        epsilon = epsilon_num / epsilon_den if epsilon_den > 0 else 1
        epsilon = max(1.0 / (k - 1), min(epsilon, 1.0))

    df_time_gg = df_time * epsilon
    df_error_gg = df_error_time * epsilon
    f_gg = f_time
    p_gg = 1 - stats.f.cdf(f_gg, df_time_gg, df_error_gg) if df_time_gg > 0 and df_error_gg > 0 else 1

    return {
        'F': f_time, 'p': p_time,
        'F_gg': f_gg, 'p_gg': p_gg,
        'epsilon': epsilon,
        'df_time': df_time, 'df_error': df_error_time,
        'df_time_gg': df_time_gg, 'df_error_gg': df_error_gg,
        'ss_time': ss_time, 'ss_error': ss_error, 'ss_subjects': ss_subjects
    }
