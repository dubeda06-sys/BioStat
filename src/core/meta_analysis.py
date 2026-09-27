"""Meta-análisis - Modelos de efectos fijos y aleatorios."""
import numpy as np
from scipy import stats


def meta_analysis(effects, se_effects, labels=None, model="random"):
    """Meta-análisis de efectos.

    Args:
        effects: Lista de efectos (log odds ratios, diferencias de medias, etc.)
        se_effects: Lista de errores estandar de cada efecto
        labels: Nombres de cada estudio
        model: "fixed" o "random"

    Returns:
        dict con efecto combinado, heterogeneidad, forest plot data
    """
    effects = np.asarray(effects, dtype=float)
    se = np.asarray(se_effects, dtype=float)
    k = len(effects)

    if k < 2:
        return None

    valid = np.isfinite(effects) & np.isfinite(se) & (se > 0)
    effects, se = effects[valid], se[valid]
    k = len(effects)

    if k < 2:
        return None

    if labels is None:
        labels = [f"Estudio {i+1}" for i in range(k)]
    else:
        labels = [l for l, v in zip(labels, valid) if v]

    weights_fixed = 1 / se**2
    effect_fixed = np.sum(weights_fixed * effects) / np.sum(weights_fixed)
    se_fixed = np.sqrt(1 / np.sum(weights_fixed))

    q = np.sum(weights_fixed * (effects - effect_fixed)**2)
    df = k - 1
    p_heterogeneity = float(stats.chi2.sf(q, df))

    i2 = max(0, (q - df) / q * 100) if q > 0 else 0

    # DerSimonian-Laird. Con tau2 = 0 los aleatorios coinciden con los fijos,
    # pero el modelo sigue siendo el elegido: antes la etiqueta cambiaba a
    # «fijos» sola y parecia que se habia cambiado el modelo.
    tau2 = 0.0
    if model == "random":
        c = np.sum(weights_fixed) - np.sum(weights_fixed**2) / np.sum(weights_fixed)
        tau2 = max(0.0, (q - df) / c) if c > 0 else 0.0
        weights = 1 / (se**2 + tau2)
        model_used = "Efectos aleatorios (DerSimonian-Laird)"
    else:
        weights = weights_fixed
        model_used = "Efectos fijos (inverso de la varianza)"
    effect_combined = np.sum(weights * effects) / np.sum(weights)
    se_combined = np.sqrt(1 / np.sum(weights))

    ci_lower = effect_combined - 1.96 * se_combined
    ci_upper = effect_combined + 1.96 * se_combined

    z = effect_combined / se_combined if se_combined > 0 else 0
    p_combined = float(2 * stats.norm.sf(abs(z)))

    # Intervalo de prediccion (Higgins, Thompson y Spiegelhalter 2009): donde
    # caeria el efecto de un estudio nuevo. Solo con aleatorios y k >= 3.
    prediccion = None
    if model == "random" and k >= 3:
        t = stats.t.ppf(0.975, k - 2)
        semi = t * np.sqrt(tau2 + se_combined**2)
        prediccion = (float(effect_combined - semi), float(effect_combined + semi))

    return {
        "k": k,
        "model": model_used,
        "effect": effect_combined,
        "se": se_combined,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "z": z,
        "p": p_combined,
        "effects": effects,
        "se_effects": se,
        "weights": weights,
        "labels": labels,
        "q": q,
        "df": df,
        "p_heterogeneity": p_heterogeneity,
        "i2": i2,
        "tau2": tau2,
        "prediccion": prediccion,
        "egger": egger(effects, se),
        "weights_pct": weights / np.sum(weights) * 100,
    }


def egger(effects, se):
    """Prueba de Egger (1997) de efecto de estudios pequenos.

    Regresion del efecto estandarizado (efecto/EE) contra la precision (1/EE):
    sin sesgo la recta pasa por el origen. Se prueba el intercepto con t de
    k - 2 gl. Con menos de 10 estudios no tiene poder (Sterne et al. 2011):
    devuelve None.
    """
    effects, se = np.asarray(effects, dtype=float), np.asarray(se, dtype=float)
    k = len(effects)
    if k < 10:
        return None
    y, x = effects / se, 1 / se
    X = np.column_stack([np.ones(k), x])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ coef
    s2 = res @ res / (k - 2)
    cov = s2 * np.linalg.inv(X.T @ X)
    t = coef[0] / np.sqrt(cov[0, 0])
    return {"intercepto": float(coef[0]), "ee": float(np.sqrt(cov[0, 0])),
            "p": float(2 * stats.t.sf(abs(t), k - 2)), "k": k}


def odds_ratio_to_log(or_val, se_or):
    """Convierte OR y SE(OR) a log(OR) y SE(log(OR))."""
    if or_val <= 0 or se_or <= 0:
        return None, None
    return np.log(or_val), se_or / or_val
