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
    p_value = float(stats.chi2.sf(cmh_stat, 1))

    R_i = a * d / n
    S_i = b * c / n
    R, S = np.sum(R_i), np.sum(S_i)
    common_or = R / S if S > 0 else float('inf')

    log_or = np.log(common_or) if 0 < common_or < np.inf else np.nan

    # Varianza de Robins, Breslow & Greenland (1986) Biometrics 42:311-323.
    # La formula que habia aca no era ninguna de las publicadas: daba un error
    # estandar 4 veces mas grande y un IC que incluia el 1 con holgura mientras
    # el p decia 0.0004. Un IC y un p que se contradicen delatan que uno de los
    # dos no sale de la misma varianza.
    P_i = (a + d) / n
    Q_i = (b + c) / n
    if R > 0 and S > 0:
        var_log_or = (np.sum(P_i * R_i) / (2 * R ** 2)
                      + np.sum(P_i * S_i + Q_i * R_i) / (2 * R * S)
                      + np.sum(Q_i * S_i) / (2 * S ** 2))
        se_log_or = float(np.sqrt(var_log_or))
        ci = (float(np.exp(log_or - 1.96 * se_log_or)),
              float(np.exp(log_or + 1.96 * se_log_or)))
    else:
        se_log_or = np.nan
        ci = (np.nan, np.nan)

    return {
        'cmh_statistic': cmh_stat,
        'p_value': p_value,
        'common_odds_ratio': common_or,
        'log_or': log_or,
        'se_log_or': se_log_or,
        'or_ci_low': ci[0],
        'or_ci_high': ci[1],
        'K': K
    }
