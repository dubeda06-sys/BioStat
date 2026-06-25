"""Modulo de funciones estadisticas — todas las pruebas."""
from __future__ import annotations
import numpy as np
from scipy import stats
from typing import Any


def descriptive_stats(data: np.ndarray | list[float]) -> dict[str, Any] | None:
    """Estadisticas descriptivas completas.
    
    Args:
        data: Array o lista de datos numericos.
        
    Returns:
        Diccionario con estadisticas descriptivas o None si no hay datos validos.
    """
    data = np.asarray(data, dtype=float)
    data = data[~np.isnan(data)]
    n = len(data)
    if n == 0:
        return None
    
    mean = np.mean(data)
    median = np.median(data)
    sd = np.std(data, ddof=1)
    var = np.var(data, ddof=1)
    sem = sd / np.sqrt(n)
    skew = stats.skew(data) if n >= 8 else np.nan
    kurt = stats.kurtosis(data) if n >= 8 else np.nan
    
    return {
        "n": n, 
        "mean": float(mean), 
        "median": float(median), 
        "std": float(sd), 
        "var": float(var),
        "sem": float(sem), 
        "min": float(np.min(data)), 
        "max": float(np.max(data)),
        "range": float(np.max(data) - np.min(data)),
        "ci95": (float(mean - 1.96 * sem), float(mean + 1.96 * sem)),
        "cv": float((sd / mean * 100) if mean != 0 else np.nan),
        "skewness": float(skew), 
        "kurtosis": float(kurt),
        "q25": float(np.percentile(data, 25)), 
        "q75": float(np.percentile(data, 75)),
        "iqr": float(np.percentile(data, 75) - np.percentile(data, 25)),
    }


def trimmed_mean(data, proportion=0.1):
    """Media recortada."""
    data = np.asarray(data, dtype=float)
    data = data[~np.isnan(data)]
    n = len(data)
    if n < 5:
        return None
    trim_count = int(n * proportion)
    sorted_data = np.sort(data)
    trimmed = sorted_data[trim_count:n - trim_count] if trim_count > 0 else sorted_data
    mean = np.mean(trimmed)
    se = np.std(trimmed, ddof=1) / np.sqrt(len(trimmed))
    return {"mean": mean, "se": se, "ci95": (mean - 1.96*se, mean + 1.96*se), "n_trimmed": len(trimmed)}


def geometric_mean(data):
    """Media geometrica."""
    data = np.asarray(data, dtype=float)
    data = data[~np.isnan(data)]
    data = data[data > 0]
    if len(data) == 0:
        return None
    return np.exp(np.mean(np.log(data)))


def harmonic_mean(data):
    """Media armonica."""
    data = np.asarray(data, dtype=float)
    data = data[~np.isnan(data)]
    data = data[data > 0]
    if len(data) == 0:
        return None
    return len(data) / np.sum(1.0 / data)


def skewness_test(data):
    """Test de asimetria."""
    data = np.asarray(data, dtype=float)
    data = data[~np.isnan(data)]
    n = len(data)
    if n < 8:
        return None
    skew = stats.skew(data)
    se = np.sqrt(6 / n)
    z = skew / se
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    return {"skewness": skew, "se": se, "z": z, "p": p}


def kurtosis_test(data):
    """Test de curtosis."""
    data = np.asarray(data, dtype=float)
    data = data[~np.isnan(data)]
    n = len(data)
    if n < 8:
        return None
    kurt = stats.kurtosis(data)
    se = np.sqrt(24 / n)
    z = kurt / se
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    return {"kurtosis": kurt, "se": se, "z": z, "p": p}


# --- Pruebas parametricas ---

def ttest_1sample(data, mu=0):
    """t-test una muestra."""
    data = np.asarray(data, dtype=float)
    data = data[~np.isnan(data)]
    n = len(data)
    if n < 2:
        return None
    t, p = stats.ttest_1samp(data, mu)
    mean = np.mean(data)
    sd = np.std(data, ddof=1)
    se = sd / np.sqrt(n)
    return {"t": t, "p": p, "df": n-1, "mean": mean, "sd": sd, "se": se, "mu": mu, "n": n}


def ttest_paired(d1, d2):
    """t-test pareado."""
    d1 = np.asarray(d1, dtype=float)
    d2 = np.asarray(d2, dtype=float)
    valid = ~(np.isnan(d1) | np.isnan(d2))
    d1, d2 = d1[valid], d2[valid]
    n = len(d1)
    if n < 2:
        return None
    t, p = stats.ttest_rel(d1, d2)
    diff = d1 - d2
    return {"t": t, "p": p, "df": n-1, "mean_diff": np.mean(diff), "sd_diff": np.std(diff, ddof=1), "n": n}


def ttest_ind(d1, d2):
    """t-test independiente (Welch)."""
    d1 = np.asarray(d1, dtype=float)
    d2 = np.asarray(d2, dtype=float)
    d1 = d1[~np.isnan(d1)]
    d2 = d2[~np.isnan(d2)]
    if len(d1) < 2 or len(d2) < 2:
        return None
    t, p = stats.ttest_ind(d1, d2, equal_var=False)
    return {"t": t, "p": p, "mean1": np.mean(d1), "mean2": np.mean(d2),
            "sd1": np.std(d1, ddof=1), "sd2": np.std(d2, ddof=1),
            "n1": len(d1), "n2": len(d2)}


def anova_oneway(groups):
    """ANOVA una via."""
    groups = [np.asarray(g, dtype=float) for g in groups]
    groups = [g[~np.isnan(g)] for g in groups]
    groups = [g for g in groups if len(g) > 0]
    if len(groups) < 2:
        return None
    f, p = stats.f_oneway(*groups)
    return {"f": f, "p": p, "df_between": len(groups)-1,
            "df_within": sum(len(g)-1 for g in groups),
            "n_groups": len(groups), "group_means": [np.mean(g) for g in groups]}


def f_test_variances(d1, d2):
    """Prueba F para comparar varianzas."""
    d1 = np.asarray(d1, dtype=float)
    d2 = np.asarray(d2, dtype=float)
    d1 = d1[~np.isnan(d1)]
    d2 = d2[~np.isnan(d2)]
    if len(d1) < 3 or len(d2) < 3:
        return None
    v1, v2 = np.var(d1, ddof=1), np.var(d2, ddof=1)
    f_stat = v1 / v2 if v1 >= v2 else v2 / v1
    df1 = (len(d1)-1) if v1 >= v2 else (len(d2)-1)
    df2 = (len(d2)-1) if v1 >= v2 else (len(d1)-1)
    p = 2 * (1 - stats.f.cdf(f_stat, df1, df2))
    return {"f": f_stat, "p": p, "df1": df1, "df2": df2,
            "var1": v1, "var2": v2, "sd1": np.std(d1, ddof=1), "sd2": np.std(d2, ddof=1)}


# --- Pruebas no parametricas ---

def mannwhitneyu(d1, d2):
    """Mann-Whitney U (Wilcoxon rank-sum)."""
    d1 = np.asarray(d1, dtype=float)
    d2 = np.asarray(d2, dtype=float)
    d1 = d1[~np.isnan(d1)]
    d2 = d2[~np.isnan(d2)]
    if len(d1) < 2 or len(d2) < 2:
        return None
    u, p = stats.mannwhitneyu(d1, d2, alternative='two-sided')
    return {"u": u, "p": p, "n1": len(d1), "n2": len(d2),
            "mean1": np.mean(d1), "mean2": np.mean(d2),
            "median1": np.median(d1), "median2": np.median(d2)}


def wilcoxon_signed_rank(d1, d2):
    """Wilcoxon signed-rank (pareado)."""
    d1 = np.asarray(d1, dtype=float)
    d2 = np.asarray(d2, dtype=float)
    valid = ~(np.isnan(d1) | np.isnan(d2))
    d1, d2 = d1[valid], d2[valid]
    mask = d1 != d2
    d1, d2 = d1[mask], d2[mask]
    if len(d1) < 5:
        return None
    try:
        w, p = stats.wilcoxon(d1, d2)
    except ValueError:
        return None
    return {"w": w, "p": p, "n": len(d1), "mean_diff": np.mean(d1-d2)}


def sign_test(d1, d2):
    """Sign test (prueba de signos)."""
    d1 = np.asarray(d1, dtype=float)
    d2 = np.asarray(d2, dtype=float)
    valid = ~(np.isnan(d1) | np.isnan(d2))
    d1, d2 = d1[valid], d2[valid]
    diff = d1 - d2
    diff = diff[diff != 0]
    n = len(diff)
    if n < 5:
        return None
    n_pos = np.sum(diff > 0)
    n_neg = np.sum(diff < 0)
    try:
        p = stats.binomtest(n_pos, n, 0.5).pvalue
    except AttributeError:
        p = 2 * stats.binom.sf(min(n_pos, n_neg) - 1, n, 0.5)
    return {"n_pos": int(n_pos), "n_neg": int(n_neg), "n": n, "p": min(p, 1.0)}


def kruskal_wallis(groups):
    """Kruskal-Wallis."""
    groups = [np.asarray(g, dtype=float) for g in groups]
    groups = [g[~np.isnan(g)] for g in groups]
    groups = [g for g in groups if len(g) > 0]
    if len(groups) < 2:
        return None
    h, p = stats.kruskal(*groups)
    return {"h": h, "p": p, "k": len(groups),
            "group_medians": [np.median(g) for g in groups]}


def friedman_test(*groups):
    """Friedman test (medidas repetidas)."""
    groups = [np.asarray(g, dtype=float) for g in groups]
    groups = [g for g in groups if len(g) > 0]
    if len(groups) < 3:
        return None
    min_len = min(len(g) for g in groups)
    groups = [g[:min_len] for g in groups]
    try:
        chi2, p = stats.friedmanchisquare(*groups)
    except ValueError:
        return None
    return {"chi2": chi2, "p": p, "k": len(groups), "n": min_len}


def cochran_q(data_matrix):
    """Cochran Q test."""
    data = np.asarray(data_matrix, dtype=float)
    k = data.shape[1]
    n = data.shape[0]
    if k < 2 or n < 2:
        return None
    col_sums = np.sum(data, axis=0)
    row_sums = np.sum(data, axis=1)
    T = np.sum(row_sums)
    denom = T * (k - T) / (k * (k - 1))
    if denom == 0:
        return {"q": 0, "p": 1.0, "k": k, "n": n}
    q = (k - 1) * (k * np.sum(col_sums**2) - T**2) / denom
    p = 1 - stats.chi2.cdf(q, k - 1)
    return {"q": q, "p": p, "k": k, "n": n, "col_sums": col_sums.tolist()}


# --- Pruebas de tablas de contingencia ---

def chi_square_test(data_matrix):
    """Chi-cuadrado para tablas de contingencia."""
    data = np.asarray(data_matrix, dtype=float)
    if data.ndim != 2 or data.shape[0] < 2 or data.shape[1] < 2:
        return None
    chi2, p, dof, expected = stats.chi2_contingency(data)
    return {"chi2": chi2, "p": p, "df": dof, "expected": expected,
            "observed": data, "n": int(np.sum(data))}


def fisher_exact_test(a, b, c, d):
    """Fisher exact test para tabla 2x2."""
    table = np.array([[a, b], [c, d]])
    odds_ratio, p = stats.fisher_exact(table)
    return {"odds_ratio": odds_ratio, "p": p, "table": table,
            "a": a, "b": b, "c": c, "d": d}


def mcnemar_test(b, c):
    """McNemar test para proporciones apareadas (tabla 2x2)."""
    if b + c == 0:
        return {"chi2": 0, "p": 1.0, "b": b, "c": c}
    chi2 = (abs(b - c) - 1)**2 / (b + c) if (b + c) > 0 else 0
    p = 1 - stats.chi2.cdf(chi2, df=1)
    return {"chi2": chi2, "p": p, "b": b, "c": c, "discordant": b + c}


# --- Correlacion ---

def pearson_r(d1, d2):
    """Correlacion de Pearson."""
    d1 = np.asarray(d1, dtype=float)
    d2 = np.asarray(d2, dtype=float)
    valid = ~(np.isnan(d1) | np.isnan(d2))
    d1, d2 = d1[valid], d2[valid]
    n = len(d1)
    if n < 3:
        return None
    r, p = stats.pearsonr(d1, d2)
    return {"r": r, "r2": r**2, "p": p, "n": n}


def spearman_rho(d1, d2):
    """Correlacion de Spearman."""
    d1 = np.asarray(d1, dtype=float)
    d2 = np.asarray(d2, dtype=float)
    valid = ~(np.isnan(d1) | np.isnan(d2))
    d1, d2 = d1[valid], d2[valid]
    n = len(d1)
    if n < 3:
        return None
    r, p = stats.spearmanr(d1, d2)
    return {"rho": r, "p": p, "n": n}


def partial_correlation(x, y, z):
    """Correlacion parcial controlando z."""
    x, y, z = np.asarray(x, dtype=float), np.asarray(y, dtype=float), np.asarray(z, dtype=float)
    valid = ~(np.isnan(x) | np.isnan(y) | np.isnan(z))
    x, y, z = x[valid], y[valid], z[valid]
    n = len(x)
    if n < 4:
        return None
    r_xz = np.corrcoef(x, z)[0, 1]
    r_yz = np.corrcoef(y, z)[0, 1]
    r_xy = np.corrcoef(x, y)[0, 1]
    denom = np.sqrt(max(0, (1 - r_xz**2) * (1 - r_yz**2)))
    if denom == 0:
        return None
    r_partial = (r_xy - r_xz * r_yz) / denom
    r_partial = np.clip(r_partial, -1, 1)
    t_denom = 1 - r_partial**2
    if t_denom <= 0:
        return None
    t_stat = r_partial * np.sqrt((n - 3) / t_denom)
    p = 2 * (1 - stats.t.cdf(abs(t_stat), n - 3))
    return {"r_partial": r_partial, "t": t_stat, "p": p, "df": n-3, "n": n}


def normality_test(data):
    """Shapiro-Wilk para normalidad."""
    data = np.asarray(data, dtype=float)
    data = data[~np.isnan(data)]
    n = len(data)
    if n < 3:
        return None
    if n > 5000:
        data = np.random.RandomState(42).choice(data, 5000, replace=False)
    w, p = stats.shapiro(data)
    return {"w": w, "p": p, "n": len(data), "normal": p >= 0.05}
