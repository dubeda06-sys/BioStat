"""Regresion — lineal, multiple, logistica, no lineal."""
import numpy as np
from scipy import stats


def linear_regression(x, y):
    """Regresion lineal simple."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    valid = ~(np.isnan(x) | np.isnan(y))
    x, y = x[valid], y[valid]
    n = len(x)
    if n < 3:
        return None
    slope, intercept, r, p, se = stats.linregress(x, y)
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred)**2)
    ss_tot = np.sum((y - np.mean(y))**2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    r2_adj = 1 - (1 - r2) * (n - 1) / (n - 2) if n > 2 else 0
    se_slope = se
    se_intercept = np.sqrt(ss_res / (n - 2)) * np.sqrt(1/n + np.mean(x)**2 / np.sum((x - np.mean(x))**2)) if n > 2 else 0
    ci_slope = (slope - 1.96*se_slope, slope + 1.96*se_slope)
    ci_intercept = (intercept - 1.96*se_intercept, intercept + 1.96*se_intercept)
    rmse = np.sqrt(ss_res / (n - 2)) if n > 2 else 0
    f_stat = (ss_tot - ss_res) / 1 / (ss_res / (n - 2)) if n > 2 and ss_res > 0 else 0
    p_f = 1 - stats.f.cdf(f_stat, 1, n - 2) if n > 2 else p
    return {
        "slope": slope, "intercept": intercept, "r": r, "r2": r2, "r2_adj": r2_adj,
        "p_slope": p, "p_model": p_f, "f": f_stat,
        "se_slope": se_slope, "se_intercept": se_intercept,
        "ci_slope": ci_slope, "ci_intercept": ci_intercept,
        "rmse": rmse, "n": n, "x": x, "y": y, "y_pred": y_pred,
    }


def multiple_regression(X, y):
    """Regresion lineal multiple."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    valid = ~(np.isnan(X).any(axis=1) | np.isnan(y))
    X, y = X[valid], y[valid]
    n, p = X.shape
    if n < p + 2:
        return None
    X_design = np.column_stack([np.ones(n), X])
    try:
        coeffs, residuals, rank, sv = np.linalg.lstsq(X_design, y, rcond=None)
    except np.linalg.LinAlgError:
        return None
    y_pred = X_design @ coeffs
    ss_res = np.sum((y - y_pred)**2)
    ss_tot = np.sum((y - np.mean(y))**2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    r2_adj = 1 - (1 - r2) * (n - 1) / (n - p - 1) if n > p + 1 else 0
    mse = ss_res / (n - p - 1) if n > p + 1 else 0
    se = np.sqrt(np.diag(mse * np.linalg.inv(X_design.T @ X_design))) if mse > 0 and np.linalg.det(X_design.T @ X_design) > 0 else np.zeros(p + 1)
    t_stats = coeffs / se if np.all(se > 0) else np.zeros(p + 1)
    p_vals = 2 * (1 - stats.t.cdf(np.abs(t_stats), n - p - 1)) if n > p + 1 else np.ones(p + 1)
    f_stat = ((ss_tot - ss_res) / p) / (ss_res / (n - p - 1)) if n > p + 1 and ss_res > 0 else 0
    p_f = 1 - stats.f.cdf(f_stat, p, n - p - 1) if n > p + 1 else 0
    return {
        "coeffs": coeffs, "se": se, "t": t_stats, "p": p_vals,
        "r2": r2, "r2_adj": r2_adj, "f": f_stat, "p_model": p_f,
        "rmse": np.sqrt(mse), "n": n, "p_predictors": p,
    }


def logistic_regression(X, y, max_iter=100, lr=0.1):
    """Regresion logistica (gradiente descendente)."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    valid = ~(np.isnan(X).any(axis=1) | np.isnan(y))
    X, y = X[valid], y[valid]
    n, p = X.shape
    if n < p + 2:
        return None
    X_design = np.column_stack([np.ones(n), X])
    w = np.zeros(p + 1)
    for _ in range(max_iter):
        z = X_design @ w
        pred = 1 / (1 + np.exp(-np.clip(z, -500, 500)))
        grad = X_design.T @ (pred - y) / n
        w -= lr * grad
    y_pred = 1 / (1 + np.exp(-np.clip(X_design @ w, -500, 500)))
    y_class = (y_pred >= 0.5).astype(int)
    accuracy = np.mean(y_class == y)
    ll = np.sum(y * np.log(y_pred + 1e-10) + (1 - y) * np.log(1 - y_pred + 1e-10))
    aic = -2 * ll + 2 * (p + 1)
    se = np.zeros(p + 1)
    try:
        H = (X_design.T @ np.diag(y_pred * (1 - y_pred)) @ X_design) / n
        se = np.sqrt(np.diag(np.linalg.inv(H)))
    except np.linalg.LinAlgError:
        pass
    z_scores = w / se if np.all(se > 0) else np.zeros(p + 1)
    p_vals = 2 * (1 - stats.norm.cdf(np.abs(z_scores)))
    return {
        "coeffs": w, "se": se, "z": z_scores, "p": p_vals,
        "odds_ratios": np.exp(w), "accuracy": accuracy,
        "log_likelihood": ll, "aic": aic, "n": n, "p_predictors": p,
    }


def nonlinear_regression(x, y, func, p0=None):
    """Regresion no lineal basica usando curve_fit."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    valid = ~(np.isnan(x) | np.isnan(y))
    x, y = x[valid], y[valid]
    n = len(x)
    if n < 3:
        return None
    try:
        from scipy.optimize import curve_fit
        popt, pcov = curve_fit(func, x, y, p0=p0, maxfev=5000)
        perr = np.sqrt(np.diag(pcov))
        y_pred = func(x, *popt)
        ss_res = np.sum((y - y_pred)**2)
        ss_tot = np.sum((y - np.mean(y))**2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        return {"params": popt, "se": perr, "r2": r2, "n": n, "y_pred": y_pred}
    except Exception:
        return None
