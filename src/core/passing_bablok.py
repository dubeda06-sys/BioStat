"""Regresion de Passing-Bablok para comparacion de metodos."""
import numpy as np
from scipy import stats

from src.core.guards import finite_pair

# El manual de MedCalc recomienda n>=30 (Bablok & Passing, 1985), con tablas de
# n sugeridos entre 30 y 90 (Passing & Bablok, 1984) y n>=50 (Ludbrook, 2010).
# Por debajo de eso el IC es demasiado ancho para discriminar: se calcula igual,
# pero se avisa.
N_RECOMENDADO = 30


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
    m1, m2, motivo = finite_pair(method1, method2, min_n=3, need_variance="x",
                                 nombre_metodo="la regresion de Passing-Bablok")
    if motivo:
        return {"error": motivo}
    n = len(m1)

    avisos = []
    if n < N_RECOMENDADO:
        avisos.append(
            f"n={n}: por debajo del minimo recomendado de {N_RECOMENDADO} "
            f"(Bablok & Passing, 1985; Ludbrook, 2010 sugiere n>=50). El "
            f"intervalo de confianza sera demasiado ancho para descartar sesgo.")

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
        return {"error": "Todos los valores del metodo de referencia son "
                         "iguales: no hay pendientes que estimar."}

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

    if np.ptp(m2) > 0:
        r, p = stats.pearsonr(m1, m2)
    else:
        r, p = np.nan, np.nan
        avisos.append("El segundo metodo es constante: la correlacion no esta definida.")

    return {
        "avisos": avisos,
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
