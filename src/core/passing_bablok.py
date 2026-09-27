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

    CLSI EP09c, apendice I2: si xi == xj y yi != yj, el par NO se descarta, entra
    como pendiente +inf o -inf segun el signo de la diferencia en y; solo se
    ignora el par con xi == xj y yi == yj (0/0). Antes se descartaban todos los
    pares verticales, y con datos redondeados —la regla en el laboratorio— la
    pendiente cambiaba en 190 de 200 corridas (auditoria 2026-09, M9).

    El signo que se le asigna al infinito depende del orden de las filas, pero
    el estimador no: un -inf suma 1 a N y 1 a K, un +inf suma 1 a N, y en los
    dos casos la mediana desplazada se corre medio lugar. Se sigue descartando
    Sij == -1 exacto, como en el trabajo original de 1983.
    """
    n = len(m1)
    i, j = np.triu_indices(n, k=1)
    dx = m1[j] - m1[i]
    dy = m2[j] - m2[i]
    vertical = dx == 0
    s = np.empty(dx.shape, dtype=float)
    s[~vertical] = dy[~vertical] / dx[~vertical]
    s[vertical & (dy > 0)] = np.inf
    s[vertical & (dy < 0)] = -np.inf
    indefinido = vertical & (dy == 0)          # 0/0: el unico par que se ignora
    s = s[~indefinido]
    return np.sort(s[s != -1])


def _recta(m1, m2):
    """Pendiente de Passing-Bablok: la mediana de las Sij corrida K lugares.

    Aparte del resto porque el sesgo en los niveles de decision se acota por
    bootstrap (`src/core/ep09.py`), que reajusta la recta mil veces y no
    necesita intervalos, residuos ni Cusum en cada vuelta.
    """
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

    if not np.isfinite(slope):
        # Con los pares verticales como +-inf (EP09c I2), la mediana solo cae en
        # uno si la mayoria de los pares tiene el mismo valor en X.
        return {"error": "El metodo de referencia repite tanto sus valores que la "
                         "pendiente mediana cae en un par vertical (pendiente "
                         "infinita). Hace falta un rango de concentraciones mas "
                         "amplio en la variable 1."}
    return {"pendientes": slopes, "N": N, "K": K, "pendiente": slope,
            "intercepto": float(np.median(m2 - slope * m1))}


def cusum_linealidad(x, y, pendiente, intercepto):
    """Prueba Cusum de linealidad de Passing y Bablok (1983).

    Si la relacion es lineal, los residuos por encima y por debajo de la recta
    se alternan al azar a lo largo de ella; si es curva, se agrupan (arriba en
    los extremos, abajo en el medio). Pasos, como NCSS y el paquete `mcr`:

    1. puntaje r = +sqrt(n_neg/n_pos) arriba de la recta, -sqrt(n_pos/n_neg)
       abajo, 0 sobre ella (asi la suma total es cero);
    2. los puntos se ordenan por su proyeccion sobre la recta,
       D = (y + x/B - A) / sqrt(1 + 1/B^2);
    3. cusum = suma acumulada de r en ese orden;
    4. H = max|cusum| / sqrt(n_neg + 1), contra la distribucion de
       Kolmogorov-Smirnov (1,36 al 5 %, 1,63 al 1 %).

    El p sale de la distribucion limite de Kolmogorov. Solo dice si Passing-
    Bablok es aplicable: nada sobre si los metodos concuerdan. Simulado con
    datos lineales, rechaza entre el 4 y el 9 % de las veces al 5 % nominal
    (tests/test_cusum.py): un p apenas debajo de 0,05 es evidencia debil.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if not (np.isfinite(pendiente) and pendiente > 0):
        return {"error": "La pendiente no es positiva: la prueba Cusum no se puede calcular."}
    res = y - intercepto - pendiente * x
    n_pos = int(np.count_nonzero(res > 0))
    n_neg = int(np.count_nonzero(res < 0))
    if n_pos == 0 or n_neg == 0:
        return {"error": "Todos los residuos caen del mismo lado de la recta: la prueba "
                         "Cusum no se puede calcular."}
    r = np.where(res > 0, np.sqrt(n_neg / n_pos),
                 np.where(res < 0, -np.sqrt(n_pos / n_neg), 0.0))
    d = (y + x / pendiente - intercepto) / np.sqrt(1 + 1 / pendiente ** 2)
    orden = np.argsort(d, kind="mergesort")
    acumulada = np.cumsum(r[orden])
    maximo = float(np.max(np.abs(acumulada)))
    h = maximo / np.sqrt(n_neg + 1)
    return {
        "max_cusum": maximo,
        "h": float(h),
        "p": float(stats.kstwobign.sf(h)),
        "critico_05": float(stats.kstwobign.isf(0.05)),
        "n_pos": n_pos,
        "n_neg": n_neg,
        "cusum": acumulada,
        "orden": orden,
    }


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

    recta = _recta(m1, m2)
    if "error" in recta:
        return recta
    slopes, N, K, slope = recta["pendientes"], recta["N"], recta["K"], recta["pendiente"]

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
    if np.all(np.isfinite(ci_slope)):
        intercept_low = np.median(m2 - ci_slope[1] * m1)
        intercept_high = np.median(m2 - ci_slope[0] * m1)
    else:
        avisos.append("El intervalo de la pendiente llega a un par vertical "
                      "(valores repetidos en la variable 1): no esta acotado, y "
                      "el del intercepto tampoco.")
        intercept_low = intercept_high = np.nan
    ci_intercept = (intercept_low, intercept_high)

    residuals = m2 - (slope * m1 + intercept)
    se_residuals = np.std(residuals, ddof=1)
    cusum = cusum_linealidad(m1, m2, slope, intercept)

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
        "cusum": cusum,
        "correlation_r": r,
        "correlation_p": p,
        "method1_mean": np.mean(m1),
        "method2_mean": np.mean(m2),
        "method1": m1,
        "method2": m2,
    }
