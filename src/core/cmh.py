"""Cochran-Mantel-Haenszel Test."""
import numpy as np
from scipy import stats


def cmh_test(tables):
    """
    Cochran-Mantel-Haenszel test for stratified 2x2 tables.

    Args:
        tables: 3D array (K x 2 x 2) of contingency tables

    Returns:
        dict with CMH statistic, p-value, and common odds ratio
    """
    tables = np.asarray(tables, dtype=float)
    K = tables.shape[0]

    a = tables[:, 0, 0]
    b = tables[:, 0, 1]
    c = tables[:, 1, 0]
    d = tables[:, 1, 1]

    n = a + b + c + d
    n1 = a + b
    n0 = c + d
    m1 = a + c
    m0 = b + d

    numerator = np.sum(a - n1 * m1 / n)
    var_num = np.sum(n1 * n0 * m1 * m0 / (n ** 2 * (n - 1)))
    var_num = np.maximum(var_num, 1e-10)

    cmh_stat = numerator ** 2 / var_num
    p_value = 1 - stats.chi2.cdf(cmh_stat, 1)

    odds_num = np.sum(a * d / n)
    odds_den = np.sum(b * c / n)
    common_or = odds_num / odds_den if odds_den > 0 else float('inf')

    log_or = np.log(common_or) if common_or > 0 else 0
    var_log_or = np.sum((a + d) * n1 * n0 * m1 * m0 / (n ** 3 * (n - 1)))
    var_log_or = np.maximum(var_log_or, 1e-10)
    se_log_or = np.sqrt(var_log_or)

    return {
        'cmh_statistic': cmh_stat,
        'p_value': p_value,
        'common_odds_ratio': common_or,
        'log_or': log_or,
        'se_log_or': se_log_or,
        'or_ci_low': np.exp(log_or - 1.96 * se_log_or),
        'or_ci_high': np.exp(log_or + 1.96 * se_log_or),
        'K': K
    }
