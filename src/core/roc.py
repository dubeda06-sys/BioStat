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
    y_score = np.asarray(y_score, dtype=float)

    n_pos = int(np.count_nonzero(y_true == 1))
    n_neg = int(np.count_nonzero(y_true == 0))

    if n_pos == 0 or n_neg == 0:
        # Sin las dos clases no hay curva. Devolver ceros hacia arriba hacia
        # que `auc` informe 0.0000, que se lee como "prueba pesima" cuando en
        # realidad es "no se puede calcular". NaN obliga a mirarlo.
        nan3 = np.array([np.nan, np.nan])
        return nan3, nan3.copy(), nan3.copy()

    orden = np.argsort(-y_score, kind="mergesort")
    y = y_true[orden]
    s = y_score[orden]

    tp_acum = np.cumsum(y == 1)
    fp_acum = np.cumsum(y == 0)

    # Un score empatado no se puede partir por la mitad: o entran todos los
    # casos con ese valor o no entra ninguno. Se toma el ULTIMO indice de cada
    # grupo de empate. Evaluar cada umbral por separado, como se hacia antes,
    # deja la curva arrancando fuera del origen y el trapecio se come el
    # triangulo inicial: con scores de pocos niveles el AUC salia hasta 0.11
    # por debajo del real, siempre subestimando.
    fin_de_grupo = np.r_[np.where(np.diff(s))[0], len(s) - 1]

    tpr = np.r_[0.0, tp_acum[fin_de_grupo] / n_pos]
    fpr = np.r_[0.0, fp_acum[fin_de_grupo] / n_neg]
    thresholds = np.r_[np.inf, s[fin_de_grupo]]

    return fpr, tpr, thresholds


def auc(fpr, tpr):
    """Calcula el Area Under the Curve (AUC)."""
    return np.trapezoid(tpr, fpr) if hasattr(np, 'trapezoid') else np.trapz(tpr, fpr)


def optimal_threshold(fpr, tpr, thresholds):
    """Encuentra el umbral optimo usando el indice de Youden (J = sens + esp - 1).

    Se saltea el punto (0,0), que la curva incluye por construccion y lleva
    umbral +inf: no es un punto de corte utilizable, es "no diagnosticar a
    nadie". Con una curva peor que el azar el argmax caeria ahi y se mostraria
    un umbral 'inf'.
    """
    fpr, tpr, thresholds = np.asarray(fpr), np.asarray(tpr), np.asarray(thresholds)
    if len(fpr) < 2 or not np.all(np.isfinite(fpr[1:])):
        return np.nan, np.nan, np.nan, np.nan
    youden = tpr[1:] - fpr[1:]
    idx = int(np.argmax(youden)) + 1
    return thresholds[idx], youden[idx - 1], tpr[idx], fpr[idx]


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
