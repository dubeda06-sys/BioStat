"""Analisis de Bland-Altman para concordancia entre metodos."""
import numpy as np
from scipy import stats

from src.core.guards import finite_pair

Z95 = 1.96


def bland_altman_analysis(method1, method2, reference=None):
    """Realiza el analisis de Bland-Altman.

    Args:
        method1: Valores del metodo 1
        method2: Valores del metodo 2
        reference: eje X para evaluar sesgo proporcional.
            None  -> clasico, diferencias contra el promedio (dos metodos pares).
            "x"   -> diferencias contra method1, cuando method1 es un metodo de
                     REFERENCIA o un valor asignado (consenso, material de control).
            "y"   -> idem contra method2.
            Con una referencia, graficar y regresar contra el promedio induce
            atenuacion del sesgo proporcional (Krouwer JS, 2008, Stat Med
            27:778-780; distincion recogida en CLSI EP09). Se devuelven ambas
            pendientes siempre, para poder contrastarlas.

    Returns:
        dict con medias, diferencias, limites de concordancia, etc.
    """
    m1, m2, motivo = finite_pair(method1, method2, min_n=3,
                                 nombre_metodo="el analisis de Bland-Altman")
    if motivo:
        return {"error": motivo}
    n = len(m1)

    means = (m1 + m2) / 2
    diffs = m1 - m2

    mean_diff = np.mean(diffs)
    sd_diff = np.std(diffs, ddof=1)
    se_diff = sd_diff / np.sqrt(n)

    mean_of_means = np.mean(means)

    loa_upper = mean_diff + Z95 * sd_diff
    loa_lower = mean_diff - Z95 * sd_diff

    # Error estandar de un limite de concordancia (Bland & Altman, 1999):
    #   var(LoA) = s^2 * (1/n + z^2 / (2(n-1)))
    # El multiplicador del IC es t(n-1), NO z: con n chico, usar 1.96 estrecha
    # el intervalo de forma apreciable (a n=15, ~9%).
    se_loa = np.sqrt(sd_diff**2 * (1/n + Z95**2/(2*(n-1))))
    t_crit = stats.t.ppf(0.975, n - 1)

    ic_mean = stats.t.interval(0.95, df=n-1, loc=mean_diff, scale=se_diff)
    ic_upper = (loa_upper - t_crit*se_loa, loa_upper + t_crit*se_loa)
    ic_lower = (loa_lower - t_crit*se_loa, loa_lower + t_crit*se_loa)

    # Limites no parametricos: percentiles 2,5 y 97,5 de las diferencias.
    # No exigen normalidad ni varianza constante (Bland & Altman, 1999). Usar
    # estos cuando la prueba de normalidad de las diferencias falle.
    loa_np_lower, loa_np_upper = np.percentile(diffs, [2.5, 97.5])
    # Shapiro-Wilk necesita n>=3 y varianza no nula; si no, se dice, no se
    # devuelve un NaN mudo.
    if n >= 3 and np.ptp(diffs) > 0:
        sw_w, sw_p = stats.shapiro(diffs)
        sw_nota = None
    else:
        sw_w, sw_p = np.nan, np.nan
        sw_nota = ("No se puede probar normalidad: las diferencias son todas "
                   "iguales." if np.ptp(diffs) == 0 else
                   "No se puede probar normalidad: se necesitan al menos 3 pares.")

    # Pearson entre promedios y diferencias: indefinido si alguno es constante.
    if np.ptp(means) > 0 and np.ptp(diffs) > 0:
        r, p = stats.pearsonr(means, diffs)
    else:
        r, p = np.nan, np.nan

    # Sesgo proporcional contra el eje que corresponda. Se calculan los dos.
    def _slope(base):
        if np.ptp(base) == 0:
            return {"slope": np.nan, "p": np.nan, "ci": (np.nan, np.nan)}
        lr = stats.linregress(base, diffs)
        tc = stats.t.ppf(0.975, n - 2) if n > 2 else np.nan
        return {"slope": lr.slope, "p": lr.pvalue,
                "ci": (lr.slope - tc*lr.stderr, lr.slope + tc*lr.stderr)}

    slope_vs_mean = _slope(means)
    if reference == "x":
        ref_axis, slope_vs_ref = m1, _slope(m1)
    elif reference == "y":
        ref_axis, slope_vs_ref = m2, _slope(m2)
    else:
        ref_axis, slope_vs_ref = None, None

    bias_pct = (mean_diff / np.mean(m1)) * 100 if np.mean(m1) != 0 else 0

    avisos = [a for a in (sw_nota,) if a]

    return {
        "avisos": avisos,
        "n": n,
        "mean_method1": np.mean(m1),
        "mean_method2": np.mean(m2),
        "mean_of_means": mean_of_means,
        "mean_difference": mean_diff,
        "sd_difference": sd_diff,
        "se_difference": se_diff,
        "loa_upper": loa_upper,
        "loa_lower": loa_lower,
        "se_loa": se_loa,
        "t_crit": t_crit,
        "ci_mean": ic_mean,
        "ci_upper": ic_upper,
        "ci_lower": ic_lower,
        "loa_np_lower": loa_np_lower,
        "loa_np_upper": loa_np_upper,
        "shapiro_w": sw_w,
        "shapiro_p": sw_p,
        "normal_diffs": bool(sw_p > 0.05) if np.isfinite(sw_p) else None,
        "correlation_r": r,
        "correlation_p": p,
        "slope_vs_mean": slope_vs_mean,
        "slope_vs_reference": slope_vs_ref,
        "reference": reference,
        "x_axis": ref_axis if ref_axis is not None else means,
        "x_axis_label": ("referencia" if reference else "promedio"),
        "bias_pct": bias_pct,
        "means": means,
        "diffs": diffs,
    }


def _mcbride_strength(rc):
    """Escala de fuerza de concordancia para el CCC (McBride GB, 2005)."""
    if not np.isfinite(rc):
        return "no calculable"
    if rc < 0.90:
        return "Pobre"
    if rc < 0.95:
        return "Moderada"
    if rc < 0.99:
        return "Sustancial"
    return "Casi perfecta"


def concordance_correlation(method1, method2):
    """Coeficiente de correlacion de concordancia de Lin (CCC).

    Se calcula con momentos POBLACIONALES (ddof=0) para que se cumpla de forma
    exacta la identidad que define el estadistico:

        rho_c = rho * Cb

    donde `rho` es la correlacion de Pearson (componente de PRECISION) y `Cb` es
    el factor de correccion de sesgo (componente de VERACIDAD). Mezclar momentos
    muestrales (ddof=1) con el termino (mean1-mean2)^2, que no se escala, rompe
    esa identidad y hace que rho y Cb ya no multipliquen al CCC reportado.

    La descomposicion es la parte util en comparacion de metodos: separa cuanto
    del desacuerdo es dispersion y cuanto es sesgo, que pueden apuntar a causas
    distintas y corregirse por vias distintas.

    Referencias: Lin LI (1989) Biometrics 45:255-268; escala de interpretacion
    segun McBride GB (2005), NIWA Client Report HAM2005-062.
    """
    m1, m2, motivo = finite_pair(method1, method2, min_n=3, need_variance="both",
                                 nombre_metodo="el CCC de Lin")
    if motivo:
        return {"error": motivo}
    n = len(m1)

    mean1, mean2 = np.mean(m1), np.mean(m2)
    var1_p, var2_p = np.var(m1, ddof=0), np.var(m2, ddof=0)
    cov_p = np.mean((m1 - mean1) * (m2 - mean2))

    denom = var1_p + var2_p + (mean1 - mean2)**2
    ccc = (2 * cov_p) / denom if denom > 0 else np.nan

    # Descomposicion precision x veracidad. `need_variance="both"` ya garantiza
    # var>0, asi que rho esta definido.
    rho = cov_p / np.sqrt(var1_p * var2_p)
    cb = ccc / rho if rho != 0 else np.nan

    # IC 95% por transformacion z de Fisher sobre el CCC (Lin, 1989). Es
    # indefinido con correlacion perfecta o con n=2; se dice cual es el motivo
    # en vez de devolver un NaN mudo.
    ci_low, ci_high, ci_nota = np.nan, np.nan, None
    if n <= 2:
        ci_nota = "IC del CCC no definido: se necesitan mas de 2 pares."
    elif not np.isfinite(rho) or rho == 0:
        ci_nota = "IC del CCC no definido: la correlacion es nula o indefinida."
    elif abs(rho) >= 1 or abs(ccc) >= 1:
        ci_nota = ("IC del CCC no definido: concordancia perfecta "
                   "(la transformacion z diverge).")
    if ci_nota is None:
        u = (mean1 - mean2) / ((var1_p * var2_p) ** 0.25)
        var_z = (((1 - rho**2) * ccc**2) / ((1 - ccc**2) * rho**2)
                 + (2 * ccc**3 * (1 - ccc) * u**2) / (rho * (1 - ccc**2)**2)
                 - (ccc**4 * u**4) / (2 * rho**2 * (1 - ccc**2)**2)) / (n - 2)
        if np.isfinite(var_z) and var_z > 0:
            z = np.arctanh(ccc)
            se = np.sqrt(var_z)
            ci_low = float(np.tanh(z - Z95 * se))
            ci_high = float(np.tanh(z + Z95 * se))
        else:
            ci_nota = "IC del CCC no definido: la varianza asintotica no es positiva."

    return {
        "avisos": [ci_nota] if ci_nota else [],
        "ci_nota": ci_nota,
        "ccc": ccc,
        "rho": rho,
        "cb": cb,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "strength": _mcbride_strength(ccc),
        "n": n,
        "mean1": mean1,
        "mean2": mean2,
        # se conservan las varianzas MUESTRALES por compatibilidad con la salida previa
        "var1": np.var(m1, ddof=1),
        "var2": np.var(m2, ddof=1),
        "covariance": np.sum((m1 - mean1) * (m2 - mean2)) / (n - 1),
    }


def bland_altman_multiple(data, method_labels=None):
    """
    Bland-Altman analysis for multiple methods/measurements.

    Args:
        data: 2D array (subjects x methods) or DataFrame
        method_labels: optional list of method names

    Returns:
        dict with pairwise comparisons
    """
    if hasattr(data, 'values'):
        data = data.values
    data = np.asarray(data, dtype=float)

    n_subjects, n_methods = data.shape

    if method_labels is None:
        method_labels = [f"Método {i+1}" for i in range(n_methods)]

    comparisons = []
    for i in range(n_methods):
        for j in range(i+1, n_methods):
            m1 = data[:, i]
            m2 = data[:, j]

            valid = ~(np.isnan(m1) | np.isnan(m2))
            m1_clean, m2_clean = m1[valid], m2[valid]

            if len(m1_clean) < 2:
                continue

            means = (m1_clean + m2_clean) / 2
            diffs = m1_clean - m2_clean

            mean_diff = np.mean(diffs)
            sd_diff = np.std(diffs, ddof=1)

            loa_upper = mean_diff + 1.96 * sd_diff
            loa_lower = mean_diff - 1.96 * sd_diff

            bias_pct = (mean_diff / np.mean(m1_clean)) * 100 if np.mean(m1_clean) != 0 else 0

            comparisons.append({
                'method1': method_labels[i],
                'method2': method_labels[j],
                'n': len(m1_clean),
                'mean_diff': mean_diff,
                'sd_diff': sd_diff,
                'loa_upper': loa_upper,
                'loa_lower': loa_lower,
                'bias_pct': bias_pct,
                'means': means,
                'diffs': diffs,
            })

    return {
        'n_subjects': n_subjects,
        'n_methods': n_methods,
        'method_labels': method_labels,
        'comparisons': comparisons,
        'n_comparisons': len(comparisons)
    }
