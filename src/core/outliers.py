"""Deteccion de valores atipicos — Grubbs, Tukey, ESD."""
import numpy as np
from scipy import stats


def grubbs_test(data, side="both"):
    """Test de Grubbs para un outlier."""
    data = np.asarray(data, dtype=float)
    data = data[~np.isnan(data)]
    n = len(data)
    if n < 3:
        return None
    mean = np.mean(data)
    sd = np.std(data, ddof=1)
    if sd == 0:
        return None
    abs_diff = np.abs(data - mean)
    idx_max = np.argmax(abs_diff)
    g = abs_diff[idx_max] / sd
    t_crit_sq = stats.t.ppf(1 - 0.05/(2*n), n-2)**2
    g_crit = ((n-1)/np.sqrt(n)) * np.sqrt(t_crit_sq / (n - 2 + t_crit_sq))
    p = 2 * n * (1 - stats.t.cdf(g * np.sqrt((n-2)/(n-1-g**2)), n-2)) if g < np.sqrt((n-1)) else 0
    return {"outlier_value": data[idx_max], "outlier_index": int(idx_max),
            "g": g, "g_crit": g_crit, "p": p, "is_outlier": g > g_crit,
            "mean": mean, "sd": sd, "n": n}


def tukey_outliers(data):
    """Deteccion de outliers por metodo de Tukey."""
    data = np.asarray(data, dtype=float)
    data = data[~np.isnan(data)]
    n = len(data)
    if n < 4:
        return None
    q25 = np.percentile(data, 25)
    q75 = np.percentile(data, 75)
    iqr = q75 - q25
    lower_inner = q25 - 1.5 * iqr
    upper_inner = q75 + 1.5 * iqr
    lower_outer = q25 - 3 * iqr
    upper_outer = q75 + 3 * iqr
    outliers_mild = data[(data < lower_inner) | (data > upper_inner)]
    outliers_extreme = data[(data < lower_outer) | (data > upper_outer)]
    return {"q25": q25, "q75": q75, "iqr": iqr,
            "lower_inner": lower_inner, "upper_inner": upper_inner,
            "lower_outer": lower_outer, "upper_outer": upper_outer,
            "outliers_mild": outliers_mild.tolist(),
            "outliers_extreme": outliers_extreme.tolist(),
            "n_mild": len(outliers_mild), "n_extreme": len(outliers_extreme),
            "n": n}


def generalized_esd(data, max_outliers=10, alpha=0.05):
    """Generalized ESD test (Rosner)."""
    data = np.asarray(data, dtype=float)
    data = data[~np.isnan(data)]
    n = len(data)
    if n < 5:
        return None

    test_stats = []
    critical_vals = []
    outliers = []
    data_clean = data.copy()

    for i in range(max_outliers):
        if len(data_clean) < 3:
            break
        mean = np.mean(data_clean)
        sd = np.std(data_clean, ddof=1)
        if sd == 0:
            break
        abs_diff = np.abs(data_clean - mean)
        idx_max = np.argmax(abs_diff)
        r_i = abs_diff[idx_max] / sd
        n_i = len(data_clean)
        p = 1 - alpha / (2 * (n_i - i))
        t_crit = stats.t.ppf(p, n_i - i - 1)
        lambda_i = (n_i - i - 1) * t_crit / np.sqrt((n_i - i - 2 + t_crit**2) * (n_i - i))
        test_stats.append(r_i)
        critical_vals.append(lambda_i)
        if r_i > lambda_i:
            outliers.append(data_clean[idx_max])
        data_clean = np.delete(data_clean, idx_max)

    n_outliers = len(outliers)
    return {"outliers": outliers, "n_outliers": n_outliers,
            "test_stats": test_stats, "critical_vals": critical_vals,
            "n_original": n, "alpha": alpha}
