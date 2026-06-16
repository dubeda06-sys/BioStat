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

    valid = ~(np.isnan(effects) | np.isnan(se) | (se <= 0))
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
    p_heterogeneity = 1 - stats.chi2.cdf(q, df)

    i2 = max(0, (q - df) / q * 100) if q > 0 else 0

    if model == "random" and i2 > 0:
        c = np.sum(weights_fixed) - np.sum(weights_fixed**2) / np.sum(weights_fixed)
        tau2 = max(0, (q - df) / c)
        weights_random = 1 / (se**2 + tau2)
        effect_random = np.sum(weights_random * effects) / np.sum(weights_random)
        se_random = np.sqrt(1 / np.sum(weights_random))

        effect_combined = effect_random
        se_combined = se_random
        weights = weights_random
        model_used = "Aleatorios (DerSimonian-Laird)"
    else:
        effect_combined = effect_fixed
        se_combined = se_fixed
        weights = weights_fixed
        model_used = "Efectos fijos"

    ci_lower = effect_combined - 1.96 * se_combined
    ci_upper = effect_combined + 1.96 * se_combined

    z = effect_combined / se_combined if se_combined > 0 else 0
    p_combined = 2 * (1 - stats.norm.cdf(abs(z)))

    p_fail = 1 - stats.norm.cdf(effect_combined / se_combined) if se_combined > 0 else 0.5

    return {
        "k": k,
        "model": model_used,
        "effect": effect_combined,
        "se": se_combined,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "z": z,
        "p": p_combined,
        "p_fail": p_fail,
        "effects": effects,
        "se_effects": se,
        "weights": weights,
        "labels": labels,
        "q": q,
        "df": df,
        "p_heterogeneity": p_heterogeneity,
        "i2": i2,
        "weights_pct": weights / np.sum(weights) * 100,
    }


def odds_ratio_to_log(or_val, se_or):
    """Convierte OR y SE(OR) a log(OR) y SE(log(OR))."""
    if or_val <= 0:
        return None, None
    return np.log(or_val), se_or / or_val
