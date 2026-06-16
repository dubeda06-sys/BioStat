"""ANCOVA - Analysis of Covariance."""
import numpy as np
from scipy import stats


def ancova(dependent, group, covariate):
    """
    One-way ANCOVA.

    Args:
        dependent: dependent variable
        group: group factor (categorical)
        covariate: continuous covariate

    Returns:
        dict with F statistic, p-value, and eta-squared
    """
    dependent = np.asarray(dependent, dtype=float)
    group = np.asarray(group)
    covariate = np.asarray(covariate, dtype=float)

    valid = ~(np.isnan(dependent) | np.isnan(covariate))
    dependent, group, covariate = dependent[valid], group[valid], covariate[valid]

    groups = np.unique(group)
    k = len(groups)
    n = len(dependent)

    grand_mean = np.mean(dependent)
    group_means = [np.mean(dependent[group == g]) for g in groups]
    cov_mean = np.mean(covariate)

    ss_total = np.sum((dependent - grand_mean) ** 2)

    cov_deviations = covariate - cov_mean
    dep_deviations = dependent - grand_mean
    ss_cov = np.sum(cov_deviations ** 2)
    slope = np.sum(cov_deviations * dep_deviations) / ss_cov if ss_cov > 0 else 0
    ss_reg = slope ** 2 * ss_cov

    ss_group = 0
    for g, gm in zip(groups, group_means):
        n_g = np.sum(group == g)
        adj_mean = gm - slope * (cov_mean - np.mean(covariate[group == g]))
        ss_group += n_g * (adj_mean - grand_mean) ** 2

    ss_error = ss_total - ss_reg - ss_group

    df_group = k - 1
    df_cov = 1
    df_error = n - k - 1

    ms_group = ss_group / df_group if df_group > 0 else 0
    ms_cov = ss_reg / df_cov if df_cov > 0 else 0
    ms_error = ss_error / df_error if df_error > 0 else 1

    f_group = ms_group / ms_error if ms_error > 0 else 0
    f_cov = ms_cov / ms_error if ms_error > 0 else 0

    p_group = 1 - stats.f.cdf(f_group, df_group, df_error) if df_group > 0 and df_error > 0 else 1
    p_cov = 1 - stats.f.cdf(f_cov, df_cov, df_error) if df_cov > 0 and df_error > 0 else 1

    eta_squared = ss_group / (ss_group + ss_error) if (ss_group + ss_error) > 0 else 0

    return {
        'F': f_group, 'p': p_group, 'df_group': df_group, 'df_error': df_error,
        'F_covariate': f_cov, 'p_covariate': p_cov,
        'eta_squared': eta_squared,
        'ss_group': ss_group, 'ss_covariate': ss_reg, 'ss_error': ss_error
    }
