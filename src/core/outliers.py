"""Deteccion de valores atipicos — Grubbs, Tukey, ESD."""
import numpy as np
from scipy import stats


def grubbs_test(data, side="both", alpha=0.05):
    """Test de Grubbs para un outlier.

    side: 'both' prueba el punto mas alejado en cualquier direccion,
          'upper' solo el maximo, 'lower' solo el minimo.
    Las variantes de una cola reparten alpha entre n puntos en vez de 2n, asi
    que su valor critico es mas bajo y detectan mas. Antes el parametro se
    aceptaba y se ignoraba: pedir 'upper' devolvia el resultado de 'both'.
    """
    data = np.asarray(data, dtype=float)
    data = data[np.isfinite(data)]
    n = len(data)
    if n < 3:
        return None
    if side not in ("both", "upper", "lower"):
        return {"error": f"side='{side}' no reconocido: usa 'both', 'upper' o "
                         f"'lower'."}
    mean = np.mean(data)
    sd = np.std(data, ddof=1)
    if sd == 0:
        return None

    if side == "upper":
        idx_max = int(np.argmax(data))
        g = (data[idx_max] - mean) / sd
    elif side == "lower":
        idx_max = int(np.argmin(data))
        g = (mean - data[idx_max]) / sd
    else:
        idx_max = int(np.argmax(np.abs(data - mean)))
        g = abs(data[idx_max] - mean) / sd

    colas = 2 if side == "both" else 1
    t_crit_sq = stats.t.ppf(1 - alpha / (colas * n), n - 2) ** 2
    g_crit = ((n - 1) / np.sqrt(n)) * np.sqrt(t_crit_sq / (n - 2 + t_crit_sq))

    # El p sale de invertir esa relacion. El factor colas*n es una cota de
    # Bonferroni, y una cota puede pasarse de 1: sin recortarla se informaban
    # "probabilidades" de hasta 3.58.
    if g < np.sqrt(n - 1):
        t_obs = g * np.sqrt((n - 2) / (n - 1 - g ** 2))
        p = colas * n * stats.t.sf(t_obs, n - 2)
    else:
        p = 0.0
    p = float(min(1.0, max(0.0, p)))

    return {"outlier_value": data[idx_max], "outlier_index": idx_max,
            "g": g, "g_crit": g_crit, "p": p, "is_outlier": bool(g > g_crit),
            "mean": mean, "sd": sd, "n": n, "side": side, "alpha": alpha}


def tukey_outliers(data):
    """Deteccion de outliers por metodo de Tukey."""
    data = np.asarray(data, dtype=float)
    data = data[np.isfinite(data)]
    n = len(data)
    if n < 4:
        return None
    q25 = np.percentile(data, 25)
    q75 = np.percentile(data, 75)
    iqr = q75 - q25
    lower_inner = q25 - 1.5 * iqr
    upper_inner = q75 + 1.5 * iqr
    lower_outer = q25 - 3 * iqr
    upper_outer = q75 + 3 * iqr
    outliers_mild = data[(data < lower_inner) | (data > upper_inner)]
    outliers_extreme = data[(data < lower_outer) | (data > upper_outer)]
    return {"q25": q25, "q75": q75, "iqr": iqr,
            "lower_inner": lower_inner, "upper_inner": upper_inner,
            "lower_outer": lower_outer, "upper_outer": upper_outer,
            "outliers_mild": outliers_mild.tolist(),
            "outliers_extreme": outliers_extreme.tolist(),
            "n_mild": len(outliers_mild), "n_extreme": len(outliers_extreme),
            "n": n}


def generalized_esd(data, max_outliers=10, alpha=0.05):
    """Generalized ESD test (Rosner, 1983 Technometrics 25:165-172).

    Dos cosas que lo distinguen del test de Grubbs repetido:

    1. Los valores criticos lambda_i usan la n ORIGINAL, no la del subconjunto
       que va quedando. Aca se restaba `i` a una `n_i` que ya venia reducida,
       o sea se restaba dos veces, y lambda se desviaba cada vez mas: contra el
       ejemplo publicado del NIST daba -0.003 en el primer paso y -0.100 en el
       decimo.

    2. La cantidad de outliers es el MAYOR i con R_i > lambda_i, y se declaran
       los i primeros. No es "cada punto que pase su prueba": esa lectura
       rompe justo el enmascaramiento que este test existe para resolver. En
       el ejemplo del NIST R_1 y R_2 NO pasan y R_3 SI; la respuesta publicada
       es 3 outliers, y tomandolos de a uno se declaraba 1.
    """
    data = np.asarray(data, dtype=float)
    data = data[np.isfinite(data)]
    n = len(data)
    if n < 5:
        return None
    max_outliers = int(min(max_outliers, (n - 2) // 2)) if n >= 6 else 1
    if max_outliers < 1:
        return None

    test_stats, critical_vals, candidatos = [], [], []
    data_clean = data.copy()

    for i in range(1, max_outliers + 1):
        if len(data_clean) < 3:
            break
        mean = np.mean(data_clean)
        sd = np.std(data_clean, ddof=1)
        if sd == 0:
            break
        abs_diff = np.abs(data_clean - mean)
        idx_max = int(np.argmax(abs_diff))
        test_stats.append(abs_diff[idx_max] / sd)
        candidatos.append(float(data_clean[idx_max]))

        p = 1 - alpha / (2 * (n - i + 1))
        t_crit = stats.t.ppf(p, n - i - 1)
        lambda_i = ((n - i) * t_crit
                    / np.sqrt((n - i - 1 + t_crit**2) * (n - i + 1)))
        critical_vals.append(float(lambda_i))

        data_clean = np.delete(data_clean, idx_max)

    # El mayor i que supera su valor critico manda: todo lo sacado hasta ahi
    # es outlier, aunque alguno de los pasos anteriores no haya pasado solo.
    n_outliers = 0
    for i, (r_i, lam) in enumerate(zip(test_stats, critical_vals), start=1):
        if r_i > lam:
            n_outliers = i

    return {"outliers": candidatos[:n_outliers], "n_outliers": n_outliers,
            "test_stats": test_stats, "critical_vals": critical_vals,
            "candidatos": candidatos,
            "n_original": n, "alpha": alpha}
