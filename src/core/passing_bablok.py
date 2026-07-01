"""Regresion de Passing-Bablok para comparacion de metodos."""
import numpy as np
from scipy import stats


def passing_bablok(method1, method2):
    """Regresion de Passing-Bablok.

    Metodo no parametrico para comparar dos metodos de medicion.
    Robusto a errores en ambas variables.

    Args:
        method1: Valores del metodo 1 (referencia)
        method2: Valores del metodo 2 (nuevo metodo)

    Returns:
        dict con pendiente, intercepto, IC, etc.
    """
    m1 = np.asarray(method1, dtype=float)
    m2 = np.asarray(method2, dtype=float)

    valid = ~(np.isnan(m1) | np.isnan(m2))
    m1, m2 = m1[valid], m2[valid]
    n = len(m1)

    if n < 3:
        return None

    sorted_idx = np.argsort(m1)
    m1_sorted = m1[sorted_idx]
    m2_sorted = m2[sorted_idx]

    slopes = []
    for i in range(n):
        for j in range(i + 1, n):
            dx = m1_sorted[j] - m1_sorted[i]
            if dx != 0:
                slope = (m2_sorted[j] - m2_sorted[i]) / dx
                slopes.append(slope)

    if not slopes:
        return None

    slopes = np.array(slopes)
    k = len(slopes)

    median_idx = k // 2
    slopes_sorted = np.sort(slopes)
    if k % 2 == 0:
        slope = (slopes_sorted[median_idx - 1] + slopes_sorted[median_idx]) / 2
    else:
        slope = slopes_sorted[median_idx]

    intercept = np.median(m2 - slope * m1)

    ci_slope_idx_low = max(0, int(np.floor(k * 0.025)) - 1)
    ci_slope_idx_high = min(k - 1, int(np.floor(k * 0.975)))
    ci_slope = (slopes_sorted[ci_slope_idx_low], slopes_sorted[ci_slope_idx_high])

    # IC del intercepto: derivado de los limites del IC de la pendiente
    # intercepto(b) = mediana(m2 - b*m1); mayor pendiente -> menor intercepto
    intercept_low = np.median(m2 - ci_slope[1] * m1)
    intercept_high = np.median(m2 - ci_slope[0] * m1)
    ci_intercept = (intercept_low, intercept_high)

    residuals = m2 - (slope * m1 + intercept)
    se_residuals = np.std(residuals, ddof=1)

    r, p = stats.pearsonr(m1, m2)

    return {
        "n": n,
        "slope": slope,
        "intercept": intercept,
        "ci_slope": ci_slope,
        "ci_intercept": ci_intercept,
        "se_residuals": se_residuals,
        "residuals": residuals,
        "correlation_r": r,
        "correlation_p": p,
        "method1_mean": np.mean(m1),
        "method2_mean": np.mean(m2),
        "method1": m1,
        "method2": m2,
    }
