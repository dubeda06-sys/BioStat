"""Analisis de curvas ROC."""
import numpy as np


def roc_curve(y_true, y_score):
    """Calcula la curva ROC.

    Args:
        y_true: Valores reales (0 o 1)
        y_score: Puntuaciones o probabilidades predichas

    Returns:
        fpr: Tasa de falsos positivos
        tpr: Tasa de verdaderos positivos
        thresholds: Umbrales
    """
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)

    desc_order = np.argsort(y_score)[::-1]
    y_score_sorted = y_score[desc_order]
    y_true_sorted = y_true[desc_order]

    thresholds = np.unique(y_score_sorted)[::-1]
    fpr = np.zeros(len(thresholds) + 1)
    tpr = np.zeros(len(thresholds) + 1)

    n_pos = np.sum(y_true == 1)
    n_neg = np.sum(y_true == 0)

    if n_pos == 0 or n_neg == 0:
        return fpr, tpr, np.append(thresholds, 0)

    for i, thresh in enumerate(thresholds):
        y_pred = (y_score >= thresh).astype(int)
        tp = np.sum((y_pred == 1) & (y_true == 1))
        fp = np.sum((y_pred == 1) & (y_true == 0))
        tpr[i] = tp / n_pos
        fpr[i] = fp / n_neg

    tpr[-1] = 1.0
    fpr[-1] = 1.0

    return fpr, tpr, np.append(thresholds, thresholds[-1] - 1)


def auc(fpr, tpr):
    """Calcula el Area Under the Curve (AUC)."""
    return np.trapezoid(tpr, fpr) if hasattr(np, 'trapezoid') else np.trapz(tpr, fpr)


def optimal_threshold(fpr, tpr, thresholds):
    """Encuentra el umbral optimo usando el indice de Youden."""
    youden = tpr - fpr
    idx = np.argmax(youden)
    return thresholds[idx], youden[idx], tpr[idx], fpr[idx]


def sensitivity_at_specificity(fpr, tpr, target_spec):
    """Calcula sensibilidad a una especificidad objetivo."""
    spec = 1 - fpr
    idx = np.argmin(np.abs(spec - target_spec))
    return tpr[idx], spec[idx]


def diagnostic_stats(y_true, y_score, threshold=None):
    """Calcula estadisticas diagnosticas completas."""
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)

    if threshold is None:
        threshold = np.median(y_score)

    y_pred = (y_score >= threshold).astype(int)

    tp = np.sum((y_pred == 1) & (y_true == 1))
    tn = np.sum((y_pred == 0) & (y_true == 0))
    fp = np.sum((y_pred == 1) & (y_true == 0))
    fn = np.sum((y_pred == 0) & (y_true == 1))

    total = tp + tn + fp + fn
    if total == 0:
        return {}

    sens = tp / (tp + fn) if (tp + fn) > 0 else 0
    spec = tn / (tn + fp) if (tn + fp) > 0 else 0
    ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
    npv = tn / (tn + fn) if (tn + fn) > 0 else 0
    acc = (tp + tn) / total
    prev = (tp + fn) / total

    return {
        "tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn),
        "sensitivity": sens, "specificity": spec,
        "ppv": ppv, "npv": npv, "accuracy": acc,
        "prevalence": prev, "threshold": threshold,
    }
