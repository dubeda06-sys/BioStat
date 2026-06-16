"""Bootstrap - remuestreo para estimacion de incertidumbre."""
import numpy as np
from scipy import stats


def bootstrap_mean(data, n_bootstrap=10000, ci=0.95, seed=42):
    """Bootstrap para la media.

    Args:
        data: Array de datos
        n_bootstrap: Numero de remuestreos
        ci: Nivel de confianza (default 0.95)

    Returns:
        dict con estimaciones bootstrap
    """
    data = np.asarray(data, dtype=float)
    data = data[~np.isnan(data)]
    n = len(data)
    if n < 2:
        return None

    rng = np.random.RandomState(seed)
    means = np.array([np.mean(rng.choice(data, size=n, replace=True)) for _ in range(n_bootstrap)])

    alpha = 1 - ci
    ci_lower = np.percentile(means, 100 * alpha / 2)
    ci_upper = np.percentile(means, 100 * (1 - alpha / 2))

    return {
        "original_mean": np.mean(data),
        "bootstrap_mean": np.mean(means),
        "bootstrap_se": np.std(means),
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "ci_level": ci,
        "n_bootstrap": n_bootstrap,
        "n_original": n,
        "bias": np.mean(means) - np.mean(data),
        "bootstrap_distribution": means,
    }


def bootstrap_median(data, n_bootstrap=10000, ci=0.95, seed=42):
    """Bootstrap para la mediana."""
    data = np.asarray(data, dtype=float)
    data = data[~np.isnan(data)]
    n = len(data)
    if n < 2:
        return None

    rng = np.random.RandomState(seed)
    medians = np.array([np.median(rng.choice(data, size=n, replace=True)) for _ in range(n_bootstrap)])

    alpha = 1 - ci
    return {
        "original_median": np.median(data),
        "bootstrap_median": np.mean(medians),
        "bootstrap_se": np.std(medians),
        "ci_lower": np.percentile(medians, 100 * alpha / 2),
        "ci_upper": np.percentile(medians, 100 * (1 - alpha / 2)),
        "ci_level": ci,
        "n_bootstrap": n_bootstrap,
        "n_original": n,
        "bootstrap_distribution": medians,
    }


def bootstrap_correlation(x, y, n_bootstrap=10000, ci=0.95, method="pearson", seed=42):
    """Bootstrap para correlacion."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    valid = ~(np.isnan(x) | np.isnan(y))
    x, y = x[valid], y[valid]
    n = len(x)
    if n < 3:
        return None

    rng = np.random.RandomState(seed)
    corrs = []
    for _ in range(n_bootstrap):
        idx = rng.choice(n, size=n, replace=True)
        xb, yb = x[idx], y[idx]
        if method == "pearson":
            r, _ = stats.pearsonr(xb, yb)
        else:
            r, _ = stats.spearmanr(xb, yb)
        corrs.append(r)

    corrs = np.array(corrs)
    alpha = 1 - ci

    if method == "pearson":
        orig_r, orig_p = stats.pearsonr(x, y)
    else:
        orig_r, orig_p = stats.spearmanr(x, y)

    return {
        "original_r": orig_r,
        "original_p": orig_p,
        "bootstrap_r": np.mean(corrs),
        "bootstrap_se": np.std(corrs),
        "ci_lower": np.percentile(corrs, 100 * alpha / 2),
        "ci_upper": np.percentile(corrs, 100 * (1 - alpha / 2)),
        "ci_level": ci,
        "n_bootstrap": n_bootstrap,
        "method": method,
        "bootstrap_distribution": corrs,
    }


def bootstrap_difference(data1, data2, n_bootstrap=10000, ci=0.95, seed=42):
    """Bootstrap para la diferencia de medias."""
    data1 = np.asarray(data1, dtype=float)
    data2 = np.asarray(data2, dtype=float)
    data1 = data1[~np.isnan(data1)]
    data2 = data2[~np.isnan(data2)]
    n1, n2 = len(data1), len(data2)
    if n1 < 2 or n2 < 2:
        return None

    rng = np.random.RandomState(seed)
    diffs = np.array([
        np.mean(rng.choice(data1, n1, replace=True)) - np.mean(rng.choice(data2, n2, replace=True))
        for _ in range(n_bootstrap)
    ])

    alpha = 1 - ci
    orig_diff = np.mean(data1) - np.mean(data2)

    return {
        "original_diff": orig_diff,
        "bootstrap_diff": np.mean(diffs),
        "bootstrap_se": np.std(diffs),
        "ci_lower": np.percentile(diffs, 100 * alpha / 2),
        "ci_upper": np.percentile(diffs, 100 * (1 - alpha / 2)),
        "ci_level": ci,
        "n_bootstrap": n_bootstrap,
        "bootstrap_distribution": diffs,
    }


def bootstrap_regression(x, y, n_bootstrap=10000, ci=0.95, seed=42):
    """Bootstrap para regresion lineal."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    valid = ~(np.isnan(x) | np.isnan(y))
    x, y = x[valid], y[valid]
    n = len(x)
    if n < 3:
        return None

    rng = np.random.RandomState(seed)
    slopes, intercepts = [], []
    for _ in range(n_bootstrap):
        idx = rng.choice(n, size=n, replace=True)
        xb, yb = x[idx], y[idx]
        z = np.polyfit(xb, yb, 1)
        slopes.append(z[0])
        intercepts.append(z[1])

    slopes = np.array(slopes)
    intercepts = np.array(intercepts)
    alpha = 1 - ci

    orig_z = np.polyfit(x, y, 1)

    return {
        "original_slope": orig_z[0],
        "original_intercept": orig_z[1],
        "bootstrap_slope": np.mean(slopes),
        "bootstrap_intercept": np.mean(intercepts),
        "se_slope": np.std(slopes),
        "se_intercept": np.std(intercepts),
        "ci_slope": (np.percentile(slopes, 100*alpha/2), np.percentile(slopes, 100*(1-alpha/2))),
        "ci_intercept": (np.percentile(intercepts, 100*alpha/2), np.percentile(intercepts, 100*(1-alpha/2))),
        "ci_level": ci,
        "n_bootstrap": n_bootstrap,
    }
