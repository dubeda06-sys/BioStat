"""Two-way ANOVA."""
import numpy as np
from scipy import stats


def two_way_anova(data, n_per_cell):
    """
    Two-way ANOVA.

    Args:
        data: 2D array (levels_A x levels_B) of cell means or raw data
        n_per_cell: number of observations per cell

    Returns:
        dict with F statistics and p-values for Factor A, B, and interaction AB
    """
    data = np.asarray(data, dtype=float)
    k, m = data.shape

    grand_mean = np.mean(data)
    a_means = np.mean(data, axis=1)
    b_means = np.mean(data, axis=0)

    ss_total = np.sum((data - grand_mean) ** 2) * n_per_cell
    ss_a = m * n_per_cell * np.sum((a_means - grand_mean) ** 2)
    ss_b = k * n_per_cell * np.sum((b_means - grand_mean) ** 2)
    ss_ab = n_per_cell * np.sum((data - a_means[:, np.newaxis] - b_means[np.newaxis, :] + grand_mean) ** 2)
    ss_error = ss_total - ss_a - ss_b - ss_ab

    df_a = k - 1
    df_b = m - 1
    df_ab = (k - 1) * (m - 1)
    df_error = k * m * (n_per_cell - 1)

    ms_a = ss_a / df_a if df_a > 0 else 0
    ms_b = ss_b / df_b if df_b > 0 else 0
    ms_ab = ss_ab / df_ab if df_ab > 0 else 0
    ms_error = ss_error / df_error if df_error > 0 else 1

    f_a = ms_a / ms_error if ms_error > 0 else 0
    f_b = ms_b / ms_error if ms_error > 0 else 0
    f_ab = ms_ab / ms_error if ms_error > 0 else 0

    p_a = 1 - stats.f.cdf(f_a, df_a, df_error) if df_a > 0 and df_error > 0 else 1
    p_b = 1 - stats.f.cdf(f_b, df_b, df_error) if df_b > 0 and df_error > 0 else 1
    p_ab = 1 - stats.f.cdf(f_ab, df_ab, df_error) if df_ab > 0 and df_error > 0 else 1

    return {
        'F_A': f_a, 'p_A': p_a, 'df_A': df_a,
        'F_B': f_b, 'p_B': p_b, 'df_B': df_b,
        'F_AB': f_ab, 'p_AB': p_ab, 'df_AB': df_ab,
        'df_error': df_error,
        'ss_A': ss_a, 'ss_B': ss_b, 'ss_AB': ss_ab, 'ss_error': ss_error
    }
