"""Concordancia y evaluacion — Kappa, ICC, Cronbach, concordance."""
import numpy as np
import pandas as pd
import pingouin as pg
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
    """Coeficiente de correlacion intraclase (ICC) via pingouin.

    data: matriz 2D (n sujetos x k evaluadores).
    model: 'one-way' -> ICC1, 'two-way-random' -> ICC2, 'two-way-mixed' -> ICC3.
    """
    data = np.asarray(data, dtype=float)
    if data.ndim != 2:
        return None
    n, k = data.shape
    if n < 2 or k < 2:
        return None

    # Formato largo para pingouin
    targets = np.repeat(np.arange(n), k)
    raters = np.tile(np.arange(k), n)
    ratings = data.ravel()
    long_df = pd.DataFrame({"target": targets, "rater": raters, "score": ratings}).dropna()

    # Shrout & Fleiss: one-way=ICC(1,1), two-way-random absoluto=ICC(A,1),
    # two-way-mixed consistencia=ICC(C,1)
    type_map = {"one-way": "ICC(1,1)", "two-way-random": "ICC(A,1)", "two-way-mixed": "ICC(C,1)"}
    icc_type = type_map.get(model, "ICC(1,1)")
    try:
        res = pg.intraclass_corr(data=long_df, targets="target", raters="rater", ratings="score")
    except Exception:
        return None
    sub = res[res["Type"] == icc_type]
    if sub.empty:
        return None
    row = sub.iloc[0]
    ci_col = "CI95" if "CI95" in res.columns else ("CI95%" if "CI95%" in res.columns else None)
    ci = row[ci_col] if ci_col is not None else (np.nan, np.nan)
    return {"icc": float(row["ICC"]), "f": float(row["F"]), "p": float(row["pval"]),
            "df1": int(row["df1"]), "df2": int(row["df2"]),
            "ci_low": float(ci[0]), "ci_high": float(ci[1]),
            "n": n, "k": k, "model": model, "type": icc_type}


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


def _deming_fit(x, y, lam):
    """Ajuste de Deming (núcleo). lam = λ = var_error(x)/var_error(y)."""
    n = len(x)
    mx, my = np.mean(x), np.mean(y)
    sxx = np.sum((x - mx) ** 2) / (n - 1)
    syy = np.sum((y - my) ** 2) / (n - 1)
    sxy = np.sum((x - mx) * (y - my)) / (n - 1)
    if sxy == 0:
        return None
    slope = ((syy - lam * sxx) + np.sqrt((syy - lam * sxx) ** 2 + 4 * lam * sxy ** 2)) / (2 * sxy)
    intercept = my - slope * mx
    return slope, intercept


def deming_regression(x, y, lambda_ratio=1.0):
    """Regresión de Deming (comparación de métodos, CLSI EP09).

    Modelo de error en ambos ejes. `lambda_ratio` (λ) es la razón de varianzas
    del error analítico entre X e Y (λ = σ²ε(x)/σ²ε(y)); λ=1 asume igual
    precisión (Deming ortogonal). IC 95% de pendiente e intercepto por jackknife
    (método de Linnet).

    Devuelve slope, intercept, ci_slope, ci_intercept, r2, n, lambda.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    valid = ~(np.isnan(x) | np.isnan(y))
    x, y = x[valid], y[valid]
    n = len(x)
    if n < 3:
        return None
    lam = float(lambda_ratio) if lambda_ratio and lambda_ratio > 0 else 1.0

    fit = _deming_fit(x, y, lam)
    if fit is None:
        return None
    slope, intercept = fit

    # Jackknife leave-one-out para IC de pendiente e intercepto (Linnet).
    js, ji = [], []
    for k in range(n):
        m = np.ones(n, dtype=bool); m[k] = False
        f = _deming_fit(x[m], y[m], lam)
        if f is None:
            continue
        js.append(f[0]); ji.append(f[1])
    js, ji = np.asarray(js), np.asarray(ji)
    if len(js) >= 2:
        tcrit = stats.t.ppf(0.975, len(js) - 1)
        se_slope = np.sqrt((len(js) - 1) / len(js) * np.sum((js - js.mean()) ** 2))
        se_int = np.sqrt((len(ji) - 1) / len(ji) * np.sum((ji - ji.mean()) ** 2))
        ci_slope = (slope - tcrit * se_slope, slope + tcrit * se_slope)
        ci_intercept = (intercept - tcrit * se_int, intercept + tcrit * se_int)
    else:
        ci_slope = (np.nan, np.nan)
        ci_intercept = (np.nan, np.nan)

    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    return {"slope": slope, "intercept": intercept,
            "ci_slope": ci_slope, "ci_intercept": ci_intercept,
            "r2": r2, "n": n, "lambda": lam,
            "x_mean": float(np.mean(x)), "y_mean": float(np.mean(y))}


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
