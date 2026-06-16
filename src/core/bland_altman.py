"""Analisis de Bland-Altman para concordancia entre metodos."""
import numpy as np
from scipy import stats


def bland_altman_analysis(method1, method2):
    """Realiza el analisis de Bland-Altman.

    Args:
        method1: Valores del metodo 1
        method2: Valores del metodo 2

    Returns:
        dict con medias, diferencias, limites de concordancia, etc.
    """
    method1 = np.asarray(method1, dtype=float)
    method2 = np.asarray(method2, dtype=float)

    valid = ~(np.isnan(method1) | np.isnan(method2))
    m1, m2 = method1[valid], method2[valid]
    n = len(m1)

    if n < 2:
        return None

    means = (m1 + m2) / 2
    diffs = m1 - m2

    mean_diff = np.mean(diffs)
    sd_diff = np.std(diffs, ddof=1)
    se_diff = sd_diff / np.sqrt(n)

    mean_of_means = np.mean(means)

    loa_upper = mean_diff + 1.96 * sd_diff
    loa_lower = mean_diff - 1.96 * sd_diff

    se_loa = np.sqrt(sd_diff**2 * (1/n + 1.96**2/(2*(n-1))))

    ic_mean = stats.t.interval(0.95, df=n-1, loc=mean_diff, scale=se_diff)
    ic_upper = (loa_upper - 1.96*se_loa, loa_upper + 1.96*se_loa)
    ic_lower = (loa_lower - 1.96*se_loa, loa_lower + 1.96*se_loa)

    r, p = stats.pearsonr(means, diffs)

    bias_pct = (mean_diff / np.mean(m1)) * 100 if np.mean(m1) != 0 else 0

    return {
        "n": n,
        "mean_method1": np.mean(m1),
        "mean_method2": np.mean(m2),
        "mean_of_means": mean_of_means,
        "mean_difference": mean_diff,
        "sd_difference": sd_diff,
        "se_difference": se_diff,
        "loa_upper": loa_upper,
        "loa_lower": loa_lower,
        "se_loa": se_loa,
        "ci_mean": ic_mean,
        "ci_upper": ic_upper,
        "ci_lower": ic_lower,
        "correlation_r": r,
        "correlation_p": p,
        "bias_pct": bias_pct,
        "means": means,
        "diffs": diffs,
    }


def concordance_correlation(method1, method2):
    """Calcula el coeficiente de concordancia de Lin (CCC)."""
    method1 = np.asarray(method1, dtype=float)
    method2 = np.asarray(method2, dtype=float)

    valid = ~(np.isnan(method1) | np.isnan(method2))
    m1, m2 = method1[valid], method2[valid]
    n = len(m1)

    if n < 2:
        return None

    mean1, mean2 = np.mean(m1), np.mean(m2)
    var1, var2 = np.var(m1, ddof=1), np.var(m2, ddof=1)

    cov = np.sum((m1 - mean1) * (m2 - mean2)) / (n - 1)

    ccc = (2 * cov) / (var1 + var2 + (mean1 - mean2)**2)

    return {
        "ccc": ccc,
        "mean1": mean1,
        "mean2": mean2,
        "var1": var1,
        "var2": var2,
        "covariance": cov,
    }
