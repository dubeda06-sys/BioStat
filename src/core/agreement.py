"""Concordancia y evaluacion — Kappa, ICC, Cronbach, concordance."""
import numpy as np
from scipy import stats


def cohens_kappa(matrix):
    """Kappa de Cohen para concordancia interevaluadores."""
    m = np.asarray(matrix, dtype=float)
    n = np.sum(m)
    k = m.shape[0]
    if n == 0 or k < 2:
        return None
    row_sums = np.sum(m, axis=1)
    col_sums = np.sum(m, axis=0)
    p_o = np.sum(np.diag(m)) / n
    p_e = np.sum(row_sums * col_sums) / n**2
    kappa = (p_o - p_e) / (1 - p_e) if (1 - p_e) != 0 else 0
    se = np.sqrt((p_o * (1 - p_o)) / (n * (1 - p_e)**2)) if (1 - p_e) != 0 else 0
    z = kappa / se if se > 0 else 0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    if kappa < 0.2:
        strength = "Pobre"
    elif kappa < 0.4:
        strength = "Regular"
    elif kappa < 0.6:
        strength = "Moderado"
    elif kappa < 0.8:
        strength = "Bueno"
    else:
        strength = "Muy bueno"
    return {"kappa": kappa, "se": se, "z": z, "p": p, "po": p_o, "pe": p_e,
            "strength": strength, "n": int(n), "matrix": m}


def weighted_kappa(matrix, weights="linear"):
    """Kappa ponderado."""
    m = np.asarray(matrix, dtype=float)
    n = np.sum(m)
    k = m.shape[0]
    if n == 0 or k < 2:
        return None
    w = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            if weights == "linear":
                w[i, j] = abs(i - j) / (k - 1)
            elif weights == "quadratic":
                w[i, j] = (i - j)**2 / (k - 1)**2
    row_sums = np.sum(m, axis=1)
    col_sums = np.sum(m, axis=0)
    p_o = 1 - np.sum(w * m) / n
    e = np.outer(row_sums, col_sums) / n**2
    p_e = 1 - np.sum(w * e) / n
    kappa = (p_o - p_e) / (1 - p_e) if (1 - p_e) != 0 else 0
    return {"kappa": kappa, "po": p_o, "pe": p_e, "weights": weights, "n": int(n)}


def intraclass_correlation(data, model="one-way"):
    """Coeficiente de correlacion intraclase (ICC)."""
    data = np.asarray(data, dtype=float)
    if data.ndim == 2:
        n, k = data.shape
    else:
        return None

    grand_mean = np.mean(data)
    row_means = np.mean(data, axis=1)
    col_means = np.mean(data, axis=0)

    ss_total = np.sum((data - grand_mean)**2)
    ss_rows = k * np.sum((row_means - grand_mean)**2)
    ss_cols = n * np.sum((col_means - grand_mean)**2)
    ss_error = ss_total - ss_rows - ss_cols

    ms_rows = ss_rows / (n - 1)
    ms_cols = ss_cols / (k - 1)
    ms_error = ss_error / ((n - 1) * (k - 1))

    if model == "one-way":
        icc = (ms_rows - ms_error) / (ms_rows + (k - 1) * ms_error)
    elif model == "two-way-random":
        icc = (ms_rows - ms_error) / (ms_rows + (k - 1) * ms_error + k * (ms_cols - ms_error) / n)
    elif model == "two-way-mixed":
        icc = (ms_rows - ms_error) / (ms_rows + (k - 1) * ms_error)
    else:
        icc = (ms_rows - ms_error) / (ms_rows + (k - 1) * ms_error)

    f_stat = ms_rows / ms_error if ms_error > 0 else np.inf
    p = 1 - stats.f.cdf(f_stat, n - 1, (n - 1) * (k - 1))

    return {"icc": icc, "f": f_stat, "p": p, "df1": n-1, "df2": (n-1)*(k-1),
            "ms_rows": ms_rows, "ms_error": ms_error, "n": n, "k": k, "model": model}


def cronbach_alpha(data):
    """Alfa de Cronbach para escala/likert."""
    data = np.asarray(data, dtype=float)
    if data.ndim != 2 or data.shape[0] < 2:
        return None
    n_items = data.shape[1]
    n_subjects = data.shape[0]
    item_variances = np.var(data, axis=0, ddof=1)
    total_variance = np.var(np.sum(data, axis=1), ddof=1)
    sum_var = np.sum(item_variances)
    if total_variance == 0:
        return {"alpha": 0, "n_items": n_items, "n_subjects": n_subjects}
    alpha = (n_items / (n_items - 1)) * (1 - sum_var / total_variance)
    return {"alpha": alpha, "n_items": n_items, "n_subjects": n_subjects,
            "item_variances": item_variances.tolist()}


def concordance_correlation(d1, d2):
    """Coeficiente de concordancia de Lin (CCC)."""
    d1 = np.asarray(d1, dtype=float)
    d2 = np.asarray(d2, dtype=float)
    valid = ~(np.isnan(d1) | np.isnan(d2))
    d1, d2 = d1[valid], d2[valid]
    n = len(d1)
    if n < 2:
        return None
    mean1, mean2 = np.mean(d1), np.mean(d2)
    var1, var2 = np.var(d1, ddof=1), np.var(d2, ddof=1)
    cov = np.sum((d1 - mean1) * (d2 - mean2)) / (n - 1)
    ccc = (2 * cov) / (var1 + var2 + (mean1 - mean2)**2)
    r = cov / np.sqrt(var1 * var2) if var1 > 0 and var2 > 0 else 0
    return {"ccc": ccc, "r": r, "mean1": mean1, "mean2": mean2,
            "var1": var1, "var2": var2, "cov": cov, "n": n}


def deming_regression(x, y, s_yx=1, s_xy=0):
    """Regresion de Deming."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    valid = ~(np.isnan(x) | np.isnan(y))
    x, y = x[valid], y[valid]
    n = len(x)
    if n < 3:
        return None
    mx, my = np.mean(x), np.mean(y)
    sx = np.var(x, ddof=1)
    sy = np.var(y, ddof=1)
    sxy = np.sum((x - mx) * (y - my)) / (n - 1)
    if sxy == 0:
        return None
    delta = s_yx / s_xy if s_xy != 0 else 1
    slope = (sy - delta * sx + np.sqrt((sy - delta * sx)**2 + 4 * delta * sxy**2)) / (2 * sxy)
    intercept = my - slope * mx
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred)**2)
    ss_tot = np.sum((y - my)**2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    return {"slope": slope, "intercept": intercept, "r2": r2, "n": n,
            "x_mean": mx, "y_mean": my}


def cv_from_duplicates(d1, d2):
    """CV desde mediciones duplicadas."""
    d1 = np.asarray(d1, dtype=float)
    d2 = np.asarray(d2, dtype=float)
    valid = ~(np.isnan(d1) | np.isnan(d2))
    d1, d2 = d1[valid], d2[valid]
    n = len(d1)
    if n < 3:
        return None
    means = (d1 + d2) / 2
    diffs = d1 - d2
    cv_dup = np.std(diffs, ddof=1) / (np.sqrt(2) * np.mean(means)) * 100
    return {"cv_dup": cv_dup, "cv_dup_pct": f"{cv_dup:.2f}%",
            "mean_cv": np.mean(means), "n": n}
