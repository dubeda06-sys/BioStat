"""Regresion — lineal, multiple, logistica, no lineal."""
import numpy as np
from scipy import stats
import statsmodels.api as sm

from src.core.guards import finite_pair


def linear_regression(x, y):
    """Regresion lineal simple."""
    # `need_variance="x"` evita el ValueError de scipy cuando todos los x son
    # iguales: antes eso subia como excepcion no controlada y crasheaba la UI.
    x, y, motivo = finite_pair(x, y, min_n=3, need_variance="x",
                               nombre_metodo="la regresion lineal")
    if motivo:
        return {"error": motivo}
    n = len(x)
    slope, intercept, r, p, se = stats.linregress(x, y)
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred)**2)
    ss_tot = np.sum((y - np.mean(y))**2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    r2_adj = 1 - (1 - r2) * (n - 1) / (n - 2) if n > 2 else 0
    se_slope = se
    se_intercept = np.sqrt(ss_res / (n - 2)) * np.sqrt(1/n + np.mean(x)**2 / np.sum((x - np.mean(x))**2)) if n > 2 else 0
    tcrit = stats.t.ppf(0.975, n - 2) if n > 2 else 1.96
    ci_slope = (slope - tcrit*se_slope, slope + tcrit*se_slope)
    ci_intercept = (intercept - tcrit*se_intercept, intercept + tcrit*se_intercept)
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
    valid = np.isfinite(X).all(axis=1) & np.isfinite(y)
    X, y = X[valid], y[valid]
    n, p = X.shape
    if n < p + 2:
        return None
    X_design = np.column_stack([np.ones(n), X])
    # Con predictoras colineales X'X no se invierte: los coeficientes no estan
    # identificados. Antes salian EE = 0 y p = 1 en todos, sin aviso
    # (auditoria 2026-09, M6).
    if np.linalg.matrix_rank(X_design) < p + 1:
        return {"error": "Las predictoras son colineales: al menos una es "
                         "combinacion lineal de las otras (o es constante). Los "
                         "coeficientes no se pueden separar; saca la que repite "
                         "informacion."}
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
    """Regresion logistica por maxima verosimilitud (statsmodels Logit).

    Devuelve coeficientes, errores estandar, z, p, odds ratios e IC95% de los OR.
    Los argumentos max_iter/lr se conservan por compatibilidad de firma (no se usan).
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    valid = np.isfinite(X).all(axis=1) & np.isfinite(y)
    X, y = X[valid], y[valid]
    n, p = X.shape
    if n < p + 2:
        return None
    if not np.all(np.isin(y, (0.0, 1.0))):
        return {"error": "La respuesta de la regresion logistica tiene que ser 0/1."}
    if len(np.unique(y)) < 2:
        return {"error": "La respuesta tiene un solo valor: no hay nada que modelar."}
    X_design = sm.add_constant(X, has_constant="add")
    try:
        model = sm.Logit(y, X_design).fit(disp=0, maxiter=200)
    except Exception as e:
        return {"error": f"La regresion logistica no converge con estos datos "
                         f"({type(e).__name__}): suele ser separacion completa."}
    # Como en el probit: statsmodels ya no lanza excepcion ante la separacion
    # completa, devuelve un ajuste sin convergencia con coeficientes enormes. Un
    # OR de 1e12 no se informa como si fuera un resultado.
    predichas = np.asarray(model.predict(X_design), dtype=float)
    if (not model.mle_retvals.get("converged", True)
            or np.all((predichas < 1e-6) | (predichas > 1 - 1e-6))):
        return {"error": "La regresion logistica no converge: alguna predictora separa "
                         "perfectamente los 0 de los 1 (separacion completa) o casi. El "
                         "OR tiende a infinito y no hay estimacion que dar."}
    coeffs = np.asarray(model.params, dtype=float)
    se = np.asarray(model.bse, dtype=float)
    z_scores = np.asarray(model.tvalues, dtype=float)
    p_vals = np.asarray(model.pvalues, dtype=float)
    or_vals = np.exp(coeffs)
    conf = np.asarray(model.conf_int(), dtype=float)  # (p+1, 2) en escala log-odds
    or_ci_low = np.exp(conf[:, 0])
    or_ci_high = np.exp(conf[:, 1])
    y_pred = np.asarray(model.predict(X_design), dtype=float)
    accuracy = float(np.mean((y_pred >= 0.5).astype(int) == y))
    return {
        "coeffs": coeffs, "se": se, "z": z_scores, "p": p_vals,
        "odds_ratios": or_vals, "or_ci_low": or_ci_low, "or_ci_high": or_ci_high,
        "accuracy": accuracy, "log_likelihood": float(model.llf),
        "aic": float(model.aic), "n": n, "p_predictors": p,
        "pseudo_r2": float(model.prsquared), "prob": y_pred, "y": y,
        "hosmer_lemeshow": hosmer_lemeshow(y, y_pred),
    }


def hosmer_lemeshow(y, prob, grupos=10):
    """Bondad de ajuste de Hosmer y Lemeshow (1980): observados contra esperados
    en grupos de riesgo (deciles de la probabilidad predicha).

    H = suma de (O - E)^2 / (E (1 - E/n_g)) sobre los grupos, contra chi2 con
    g - 2 gl. Un p chico dice que el modelo predice mal en algun tramo de riesgo.
    """
    y = np.asarray(y, dtype=float)
    prob = np.asarray(prob, dtype=float)
    orden = np.argsort(prob, kind="mergesort")
    partes = [p for p in np.array_split(orden, min(grupos, len(y))) if len(p)]
    h, filas = 0.0, []
    for idx in partes:
        n_g = len(idx)
        obs, esp = float(y[idx].sum()), float(prob[idx].sum())
        filas.append({"n": n_g, "observados": obs, "esperados": esp})
        denom = esp * (1 - esp / n_g)
        if denom > 0:
            h += (obs - esp) ** 2 / denom
    gl = len(partes) - 2
    p = float(stats.chi2.sf(h, gl)) if gl > 0 else float("nan")
    return {"h": float(h), "gl": gl, "p": p, "grupos": filas}


def nonlinear_regression(x, y, func, p0=None):
    """Regresion no lineal basica usando curve_fit."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    valid = np.isfinite(x) & np.isfinite(y)
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
