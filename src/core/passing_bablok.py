"""Regresion de Passing-Bablok para comparacion de metodos."""
import numpy as np
from scipy import stats

from src.core.guards import finite_pair

# El manual de MedCalc recomienda n>=30 (Bablok & Passing, 1985), con tablas de
# n sugeridos entre 30 y 90 (Passing & Bablok, 1984) y n>=50 (Ludbrook, 2010).
# Por debajo de eso el IC es demasiado ancho para discriminar: se calcula igual,
# pero se avisa.
N_RECOMENDADO = 30


def _pendientes(m1, m2):
    """Las Sij de todos los pares i<j, ya ordenadas.

    Passing & Bablok descartan dos clases de par: los que tienen xi == xj, que
    dan pendiente infinita, y los que dan Sij == -1 exacto, que es el valor
    que rompe la simetria del estimador.
    """
    n = len(m1)
    i, j = np.triu_indices(n, k=1)
    dx = m1[j] - m1[i]
    dy = m2[j] - m2[i]
    usable = dx != 0
    s = dy[usable] / dx[usable]
    return np.sort(s[s != -1])


def passing_bablok(method1, method2, alpha=0.05):
    """Regresion de Passing-Bablok.

    Metodo no parametrico para comparar dos metodos de medicion.
    Robusto a errores en ambas variables.

    La pendiente es la mediana DESPLAZADA de las pendientes por pares: el
    desplazamiento K = #{Sij < -1} es lo que hace al estimador simetrico, o
    sea que b(x,y) * b(y,x) == 1 exacto. Sin K esto es Theil-Sen, que no lo
    cumple. El IC sale de estadisticos de orden sobre las Sij (Passing &
    Bablok 1983, seccion 3), no de los percentiles empiricos de las
    pendientes: las Sij no son observaciones independientes y sus cuantiles
    dan un intervalo mucho mas ancho que el que corresponde.

    Args:
        method1: Valores del metodo 1 (referencia)
        method2: Valores del metodo 2 (nuevo metodo)
        alpha: nivel del intervalo de confianza (0.05 -> IC 95%)

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

    slopes = _pendientes(m1, m2)
    N = len(slopes)
    if N == 0:
        return {"error": "Todos los valores del metodo de referencia son "
                         "iguales: no hay pendientes que estimar."}

    # K desplaza la mediana. Es lo que vuelve simetrico al estimador.
    K = int(np.count_nonzero(slopes < -1))

    if N % 2:
        centro = (N + 1) // 2 + K - 1
        fuera = centro >= N
        slope = slopes[min(centro, N - 1)]
    else:
        i1, i2 = N // 2 + K - 1, N // 2 + K
        fuera = i2 >= N
        slope = (slopes[min(i1, N - 1)] + slopes[min(i2, N - 1)]) / 2

    if fuera:
        # Mas de la mitad de las pendientes por pares son menores que -1: la
        # asociacion es predominantemente negativa y Passing-Bablok no aplica.
        # Supone relacion creciente entre los dos metodos.
        return {"error": "Mas de la mitad de las pendientes por pares son "
                         "negativas: los dos metodos no crecen juntos y "
                         "Passing-Bablok no aplica. Revisa si las columnas "
                         "estan invertidas o si miden cosas distintas."}

    intercept = np.median(m2 - slope * m1)

    # IC por estadisticos de orden (Passing & Bablok 1983).
    z = stats.norm.ppf(1 - alpha / 2)
    C = z * np.sqrt(n * (n - 1) * (2 * n + 5) / 18.0)
    M1 = int(round((N - C) / 2))
    M2 = N - M1 + 1
    lo_idx, hi_idx = M1 + K - 1, M2 + K - 1
    if lo_idx < 0 or hi_idx > N - 1:
        avisos.append(
            f"n={n} es tan bajo que el intervalo de confianza cubre todas las "
            f"pendientes por pares: no discrimina nada. Tomalo como "
            f"'no hay informacion', no como 'no hay sesgo'.")
    ci_slope = (slopes[max(0, lo_idx)], slopes[min(N - 1, hi_idx)])

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
        "n_pendientes": N,
        "k_desplazamiento": K,
        "se_residuals": se_residuals,
        "residuals": residuals,
        "correlation_r": r,
        "correlation_p": p,
        "method1_mean": np.mean(m1),
        "method2_mean": np.mean(m2),
        "method1": m1,
        "method2": m2,
    }
