"""Mediciones seriadas por medidas resumen (Matthews, Altman, Campbell y Royston,
BMJ 1990;300:230-235).

Cada sujeto se reduce a UN numero —su pendiente en el tiempo— y la pregunta
"hay tendencia?" se contesta con esos numeros, uno por sujeto. Antes se ajustaba
una sola recta a las n x k mediciones como si fueran independientes y se
informaba su p: con pendientes individuales y ninguna tendencia real daba
p < 0,05 en el 19,7 % de los casos, y con niveles propios por sujeto casi nunca
(auditoria 2026-09, A11). Las mediciones de un mismo sujeto no son independientes;
las pendientes de sujetos distintos si.
"""
import numpy as np
from scipy import stats


def serial_measurements_summary(data):
    """Resume mediciones seriadas: media por tiempo y tendencia por sujeto.

    Args:
        data: 2D array (sujetos x tiempos). Los tiempos se toman equiespaciados
            (0, 1, ..., k-1). Los faltantes se admiten: cada sujeto necesita al
            menos 2 mediciones para tener pendiente.

    Returns:
        dict con medias/DE/EE por tiempo (ignorando faltantes), la pendiente de
        cada sujeto, la pendiente media con su IC 95 % y la t de una muestra
        sobre las pendientes (H0: pendiente media = 0).
    """
    data = np.asarray(data, dtype=float)
    data = np.where(np.isfinite(data), data, np.nan)
    n, k = data.shape

    n_por_tiempo = np.sum(np.isfinite(data), axis=0)
    means = np.nanmean(data, axis=0)
    sds = np.nanstd(data, axis=0, ddof=1)
    sems = sds / np.sqrt(n_por_tiempo)

    time_points = np.arange(k)
    slopes = []
    individual_trajectories = []
    for i in range(n):
        valid = np.isfinite(data[i])
        if np.sum(valid) < 2:
            continue
        lr = stats.linregress(time_points[valid], data[i, valid])
        slopes.append(lr.slope)
        individual_trajectories.append({
            'subject': i + 1,
            'slope': lr.slope,
            'intercept': lr.intercept,
            'values': data[i].tolist(),
        })
    slopes = np.array(slopes)

    avisos = []
    n_con_pendiente = len(slopes)
    if n_con_pendiente < n:
        avisos.append(f"{n - n_con_pendiente} sujeto(s) con menos de 2 mediciones: "
                      f"sin pendiente, no entran en la prueba de tendencia.")

    t_tend = p_tend = np.nan
    ic = (np.nan, np.nan)
    if n_con_pendiente >= 2 and np.ptp(slopes) > 0:
        t_tend, p_tend = stats.ttest_1samp(slopes, 0)
        tc = stats.t.ppf(0.975, n_con_pendiente - 1)
        ee = np.std(slopes, ddof=1) / np.sqrt(n_con_pendiente)
        ic = (float(np.mean(slopes) - tc * ee), float(np.mean(slopes) + tc * ee))
    else:
        avisos.append("No hay suficientes pendientes distintas para probar si hay "
                      "tendencia.")

    return {
        'avisos': avisos,
        'means': means.tolist(),
        'sds': sds.tolist(),
        'sems': sems.tolist(),
        'n_por_tiempo': n_por_tiempo.tolist(),
        'slopes': slopes.tolist(),
        'mean_slope': float(np.mean(slopes)) if n_con_pendiente else np.nan,
        'sd_slope': float(np.std(slopes, ddof=1)) if n_con_pendiente >= 2 else np.nan,
        'ic_pendiente_media': ic,
        't_tendencia': float(t_tend),
        'p_tendencia': float(p_tend),
        'n_con_pendiente': n_con_pendiente,
        'individual_trajectories': individual_trajectories,
        'n_subjects': n,
        'n_timepoints': k,
    }
