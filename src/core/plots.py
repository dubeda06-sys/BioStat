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


def mountain_plot_data(data, n_bins=50):
    """
    Prepare data for mountain plot (folded normal distribution).

    Args:
        data: array of values
        n_bins: number of bins for histogram

    Returns:
        dict with x, y, and reference lines
    """
    data = np.asarray(data, dtype=float)
    data = data[~np.isnan(data)]

    if len(data) < 5:
        return None

    mean = np.mean(data)
    sd = np.std(data, ddof=1)

    x_min = mean - 4 * sd
    x_max = mean + 4 * sd
    x = np.linspace(x_min, x_max, 200)

    y_density = stats.norm.pdf(x, mean, sd)

    hist, bin_edges = np.histogram(data, bins=n_bins, density=True)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    return {
        'x': x,
        'y_density': y_density,
        'hist_x': bin_centers,
        'hist_y': hist,
        'mean': mean,
        'sd': sd,
        'median': np.median(data),
        'q25': np.percentile(data, 25),
        'q75': np.percentile(data, 75),
        'n': len(data)
    }
