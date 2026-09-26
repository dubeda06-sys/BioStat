"""Additional plot types for BioStat."""
import numpy as np
from scipy import stats


def youden_data(y_true, y_score):
    """
    Calculate Youden's J statistic for each threshold.

    Args:
        y_true: binary true labels (0/1)
        y_score: predicted scores

    Returns:
        dict with thresholds, sensitivity, specificity, and J statistic
    """
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)

    thresholds = np.unique(y_score)[::-1]
    n_pos = np.sum(y_true == 1)
    n_neg = np.sum(y_true == 0)

    if n_pos == 0 or n_neg == 0:
        return None

    sensitivity = np.zeros(len(thresholds))
    specificity = np.zeros(len(thresholds))

    for i, thresh in enumerate(thresholds):
        y_pred = (y_score >= thresh).astype(int)
        tp = np.sum((y_pred == 1) & (y_true == 1))
        tn = np.sum((y_pred == 0) & (y_true == 0))
        sensitivity[i] = tp / n_pos if n_pos > 0 else 0
        specificity[i] = tn / n_neg if n_neg > 0 else 0

    j_stat = sensitivity + specificity - 1

    return {
        'thresholds': thresholds,
        'sensitivity': sensitivity,
        'specificity': specificity,
        'j_statistic': j_stat,
        'optimal_idx': np.argmax(j_stat),
        'optimal_threshold': thresholds[np.argmax(j_stat)],
        'optimal_j': j_stat[np.argmax(j_stat)]
    }


def polar_plot_data(categories, values):
    """
    Prepare data for polar plot (radar chart).

    Args:
        categories: list of category names
        values: list of values for each category

    Returns:
        dict with angles and values for plotting
    """
    categories = list(categories)
    values = list(values)
    n = len(categories)

    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    values_closed = values + [values[0]]
    angles_closed = angles + [angles[0]]

    return {
        'categories': categories + [categories[0]],
        'angles': angles_closed,
        'values': values_closed,
        'n': n
    }


def waterfall_data(values, labels=None):
    """
    Prepare data for waterfall chart.

    Args:
        values: list of values (positive = increase, negative = decrease)
        labels: optional list of labels for each bar

    Returns:
        dict with cumulative values for plotting
    """
    values = list(values)
    n = len(values)

    if labels is None:
        labels = [f'Item {i+1}' for i in range(n)]

    cumulative = [0]
    for v in values:
        cumulative.append(cumulative[-1] + v)

    starts = cumulative[:-1]
    ends = cumulative[1:]

    return {
        'labels': labels + ['Total'],
        'values': values + [cumulative[-1]],
        'starts': starts + [0],
        'ends': ends + [cumulative[-1]],
        'is_positive': [v >= 0 for v in values] + [cumulative[-1] >= 0],
        'n': n
    }


def mountain_plot_data(method1, method2):
    """Mountain plot: la distribucion acumulada PLEGADA de las diferencias entre
    dos metodos (Krouwer y Monti, 1995; CLSI EP09).

    Se ordenan las diferencias d = metodo 1 - metodo 2, a cada una se le asigna
    su percentil (rango / (n + 1)) y los percentiles de arriba de 50 se pliegan
    (100 - percentil). El pico cae en la mediana de las diferencias; lo ancho de
    la montana es cuanto difieren los metodos. Dos metodos intercambiables dan
    una montana angosta centrada en 0.

    Antes esto era un histograma de UNA columna con una normal ajustada: no
    tenia nada de mountain plot (auditoria 2026-09, A12).
    """
    m1 = np.asarray(method1, dtype=float)
    m2 = np.asarray(method2, dtype=float)
    validos = np.isfinite(m1) & np.isfinite(m2)
    d = np.sort(m1[validos] - m2[validos])
    n = len(d)
    if n < 5:
        return {"error": f"Se necesitan al menos 5 pares completos; hay {n}."}

    percentil = 100.0 * np.arange(1, n + 1) / (n + 1)
    plegado = np.where(percentil <= 50, percentil, 100 - percentil)
    return {
        'diferencias': d,
        'percentil': percentil,
        'percentil_plegado': plegado,
        'mediana': float(np.median(d)),
        'p2_5': float(np.percentile(d, 2.5, method="weibull")) if n >= 39 else np.nan,
        'p97_5': float(np.percentile(d, 97.5, method="weibull")) if n >= 39 else np.nan,
        'p25': float(np.percentile(d, 25, method="weibull")),
        'p75': float(np.percentile(d, 75, method="weibull")),
        'n': n,
    }
