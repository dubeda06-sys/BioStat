"""ANOVA de medidas repetidas de un factor, con correccion de Greenhouse-Geisser."""
import numpy as np
from scipy import stats


def _epsilon_gg(data):
    """Epsilon de Greenhouse-Geisser (Box 1954; Greenhouse y Geisser 1959).

    Se calcula sobre la matriz de covarianzas DOBLEMENTE CENTRADA (se le restan
    las medias de fila y de columna y se suma la media general):

        eps = tr(S*)^2 / ((k-1) * sum(S*_ij^2))

    La version anterior usaba la covarianza sin centrar, y daba 0,747 donde
    corresponde 0,548 (auditoria 2026-09, K9). Es el mismo calculo que
    pingouin.epsilon(correction="gg").
    """
    k = data.shape[1]
    if k <= 2:
        return 1.0
    S = np.cov(data, rowvar=False, ddof=1)
    S_dc = S - S.mean(axis=0)[None, :] - S.mean(axis=1)[:, None] + S.mean()
    den = (k - 1) * np.sum(S_dc ** 2)
    return float(np.trace(S_dc) ** 2 / den) if den > 0 else 1.0


def repeated_measures_anova(data):
    """ANOVA de medidas repetidas (sujetos x tiempos) con correccion GG.

    Solo entran los sujetos con todas las mediciones: el diseno exige una
    medicion de cada sujeto en cada tiempo. Los que tienen alguna faltante se
    cuentan y se informan, no se imputan.
    """
    data = np.asarray(data, dtype=float)
    completos = np.all(np.isfinite(data), axis=1)
    n_excluidos = int(np.sum(~completos))
    data = data[completos]
    n, k = data.shape
    if k < 2:
        return {"error": "Hacen falta al menos 2 mediciones por sujeto."}
    if n < 2:
        return {"error": f"Quedan {n} sujeto(s) con todas las mediciones "
                         f"({n_excluidos} excluidos por faltantes): no alcanza."}

    grand_mean = np.mean(data)
    subject_means = np.mean(data, axis=1)
    time_means = np.mean(data, axis=0)

    ss_total = np.sum((data - grand_mean) ** 2)
    ss_subjects = k * np.sum((subject_means - grand_mean) ** 2)
    ss_time = n * np.sum((time_means - grand_mean) ** 2)
    ss_error = ss_total - ss_subjects - ss_time

    df_time = k - 1
    df_error_time = (n - 1) * (k - 1)

    ms_time = ss_time / df_time
    ms_error = ss_error / df_error_time
    if ms_error <= 0:
        return {"error": "El error residual es cero: todos los sujetos cambian "
                         "exactamente igual entre tiempos y la F no esta definida."}

    f_time = ms_time / ms_error
    p_time = float(stats.f.sf(f_time, df_time, df_error_time))

    epsilon = _epsilon_gg(data)
    df_time_gg = df_time * epsilon
    df_error_gg = df_error_time * epsilon
    p_gg = float(stats.f.sf(f_time, df_time_gg, df_error_gg))

    avisos = []
    if n_excluidos:
        avisos.append(f"{n_excluidos} sujeto(s) excluidos por tener alguna medicion "
                      f"faltante.")

    return {
        'avisos': avisos,
        'F': f_time, 'p': p_time,
        'F_gg': f_time, 'p_gg': p_gg,
        'epsilon': epsilon,
        'df_time': df_time, 'df_error': df_error_time,
        'df_time_gg': df_time_gg, 'df_error_gg': df_error_gg,
        'ss_time': ss_time, 'ss_error': ss_error, 'ss_subjects': ss_subjects,
        'n': n, 'k': k, 'n_excluidos': n_excluidos,
    }
