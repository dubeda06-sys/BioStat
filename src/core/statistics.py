"""Modulo de funciones estadisticas — todas las pruebas."""
import numpy as np
from scipy import stats
from statsmodels.stats.contingency_tables import cochrans_q as _sm_cochrans_q


def descriptive_stats(data):
    """Estadisticas descriptivas completas."""
    data = np.asarray(data, dtype=float)
    data = data[np.isfinite(data)]
    n = len(data)
    if n == 0:
        return None
    mean = np.mean(data)
    median = np.median(data)
    sd = np.std(data, ddof=1)
    var = np.var(data, ddof=1)
    sem = sd / np.sqrt(n)
    constante = np.ptp(data) == 0
    calculable = n >= 8 and not constante
    skew = stats.skew(data) if calculable else np.nan
    kurt = stats.kurtosis(data) if calculable else np.nan
    # La media, la mediana y los extremos de datos constantes son validos; lo
    # indefinido es solo lo que divide por la dispersion. Por eso avisa en vez
    # de rechazar todo el bloque.
    avisos = []
    if constante:
        avisos.append(f"Todos los valores son iguales a {data[0]:g}: la "
                      f"asimetria, la curtosis y el CV no estan definidos.")
    elif n < 8:
        avisos.append(f"n={n}: la asimetria y la curtosis necesitan al menos 8 "
                      f"datos para ser informativas.")
    return {
        "avisos": avisos,
        "n": n, "mean": mean, "median": median, "std": sd, "var": var,
        "sem": sem, "min": np.min(data), "max": np.max(data),
        "range": np.max(data) - np.min(data),
        "ci95": (mean - stats.t.ppf(0.975, n - 1) * sem, mean + stats.t.ppf(0.975, n - 1) * sem),
        "cv": (sd / mean * 100) if mean != 0 else np.nan,
        "skewness": skew, "kurtosis": kurt,
        "q25": np.percentile(data, 25), "q75": np.percentile(data, 75),
        "iqr": np.percentile(data, 75) - np.percentile(data, 25),
    }


def trimmed_mean(data, proportion=0.1):
    """Media recortada con su IC (Tukey y McLaughlin, 1963).

    El error estandar sale de la varianza WINSORIZADA, no de la DE de los datos
    que quedaron despues de recortar: al sacar las colas, la muestra recortada
    tiene menos dispersion que la que corresponde a la media que se estima. Con
    la DE recortada el IC 95 % cubria el 86 % (auditoria 2026-09, A4).

        EE = s_w / ((1 - 2g) * sqrt(n)),   gl = h - 1

    s_w = DE de la muestra winsorizada, g = proporcion recortada de cada cola,
    h = n que queda despues de recortar. Mismo calculo que
    scipy.stats.mstats.trimmed_stde y que `trimse` de Wilcox.
    """
    data = np.asarray(data, dtype=float)
    data = data[np.isfinite(data)]
    n = len(data)
    if n < 5:
        return None
    trim_count = int(n * proportion)
    sorted_data = np.sort(data)
    trimmed = sorted_data[trim_count:n - trim_count] if trim_count > 0 else sorted_data
    h = len(trimmed)
    mean = np.mean(trimmed)
    winsorizada = sorted_data.copy()
    if trim_count > 0:
        winsorizada[:trim_count] = sorted_data[trim_count]
        winsorizada[n - trim_count:] = sorted_data[n - trim_count - 1]
    se = np.std(winsorizada, ddof=1) / ((1 - 2 * proportion) * np.sqrt(n))
    tcrit = stats.t.ppf(0.975, h - 1)
    return {"mean": mean, "se": se, "ci95": (mean - tcrit*se, mean + tcrit*se),
            "n_trimmed": h, "df": h - 1}


def _motivo_no_positivos(data, nombre):
    k = int(np.sum(data <= 0))
    return (f"Hay {k} valor(es) cero o negativo(s): la {nombre} no esta definida "
            f"para ellos. No se descartan en silencio: si son errores de carga, "
            f"corregilos; si son datos reales, esta media no corresponde.")


def geometric_mean(data):
    """Media geometrica con su IC 95 % (media de los logaritmos, retransformada).

    Antes descartaba en silencio los ceros y los negativos y promediaba el
    resto: [0, 2, 8, -1, 4] daba 4. Ahora rechaza y dice cuantos hay.
    """
    data = np.asarray(data, dtype=float)
    data = data[np.isfinite(data)]
    n = len(data)
    if n == 0:
        return None
    if np.any(data <= 0):
        return {"error": _motivo_no_positivos(data, "media geometrica")}
    logs = np.log(data)
    gm = float(np.exp(np.mean(logs)))
    if n >= 2:
        tc = stats.t.ppf(0.975, n - 1)
        medio = tc * np.std(logs, ddof=1) / np.sqrt(n)
        ci = (float(np.exp(np.mean(logs) - medio)), float(np.exp(np.mean(logs) + medio)))
    else:
        ci = (np.nan, np.nan)
    return {"gm": gm, "ci95": ci, "n": n}


def harmonic_mean(data):
    """Media armonica. Rechaza ceros y negativos con motivo, no los descarta."""
    data = np.asarray(data, dtype=float)
    data = data[np.isfinite(data)]
    n = len(data)
    if n == 0:
        return None
    if np.any(data <= 0):
        return {"error": _motivo_no_positivos(data, "media armonica")}
    return {"hm": float(n / np.sum(1.0 / data)), "n": n}


def skewness_test(data):
    """Prueba de asimetria de D'Agostino (1970), la de scipy.stats.skewtest.

    Antes dividia la asimetria por sqrt(6/n), el EE asintotico: con n chico ese
    EE es demasiado grande y la prueba casi nunca rechazaba (1,2 % de rechazos
    con datos normales y n=10, en vez del 5 %). D'Agostino transforma el
    estadistico para que sea normal ya con n >= 8.
    """
    data = np.asarray(data, dtype=float)
    data = data[np.isfinite(data)]
    n = len(data)
    if n < 8:
        return None
    if np.ptp(data) == 0:
        return {"error": f"Todos los valores son iguales a {data[0]:g}: la "
                         f"asimetria divide por la dispersion y no esta definida."}
    skew = stats.skew(data)
    z, p = stats.skewtest(data)
    return {"skewness": skew, "z": float(z), "p": float(p), "n": n,
            "prueba": "D'Agostino"}


def kurtosis_test(data):
    """Prueba de curtosis de Anscombe y Glynn (1983), la de scipy.stats.kurtosistest.

    El EE asintotico sqrt(24/n) daba 0,1 % de rechazos con datos normales y
    n=10: la curtosis tiene una distribucion muy asimetrica con n chico y la
    aproximacion normal directa no sirve.
    """
    data = np.asarray(data, dtype=float)
    data = data[np.isfinite(data)]
    n = len(data)
    if n < 8:
        return None
    if np.ptp(data) == 0:
        return {"error": f"Todos los valores son iguales a {data[0]:g}: la "
                         f"curtosis divide por la dispersion y no esta definida."}
    kurt = stats.kurtosis(data)
    z, p = stats.kurtosistest(data)
    avisos = []
    if n < 20:
        avisos.append(f"n={n}: la prueba de curtosis es poco confiable por debajo "
                      f"de 20 datos.")
    return {"kurtosis": kurt, "z": float(z), "p": float(p), "n": n,
            "prueba": "Anscombe-Glynn", "avisos": avisos}


# --- Pruebas parametricas ---

def ttest_1sample(data, mu=0):
    """t-test una muestra."""
    data = np.asarray(data, dtype=float)
    data = data[np.isfinite(data)]
    n = len(data)
    if n < 2:
        return None
    if np.ptp(data) == 0:
        return {"error": f"Todos los valores son iguales a {data[0]:g}: el "
                         f"error estandar es cero y la t no esta definida."}
    t, p = stats.ttest_1samp(data, mu)
    mean = np.mean(data)
    sd = np.std(data, ddof=1)
    se = sd / np.sqrt(n)
    return {"t": t, "p": p, "df": n-1, "mean": mean, "sd": sd, "se": se, "mu": mu, "n": n}


def ttest_paired(d1, d2):
    """t-test pareado."""
    d1 = np.asarray(d1, dtype=float)
    d2 = np.asarray(d2, dtype=float)
    valid = np.isfinite(d1) & np.isfinite(d2)
    d1, d2 = d1[valid], d2[valid]
    n = len(d1)
    if n < 2:
        return None
    t, p = stats.ttest_rel(d1, d2)
    diff = d1 - d2
    return {"t": t, "p": p, "df": n-1, "mean_diff": np.mean(diff), "sd_diff": np.std(diff, ddof=1), "n": n}


def ttest_ind(d1, d2):
    """t-test independiente (Welch)."""
    d1 = np.asarray(d1, dtype=float)
    d2 = np.asarray(d2, dtype=float)
    d1 = d1[np.isfinite(d1)]
    d2 = d2[np.isfinite(d2)]
    if len(d1) < 2 or len(d2) < 2:
        return None
    if np.ptp(d1) == 0 and np.ptp(d2) == 0:
        return {"error": "Los dos grupos son constantes: no hay dispersion "
                         "contra la cual medir la diferencia de medias."}
    t, p = stats.ttest_ind(d1, d2, equal_var=False)
    return {"t": t, "p": p, "mean1": np.mean(d1), "mean2": np.mean(d2),
            "sd1": np.std(d1, ddof=1), "sd2": np.std(d2, ddof=1),
            "n1": len(d1), "n2": len(d2)}


def anova_oneway(groups):
    """ANOVA una via."""
    groups = [np.asarray(g, dtype=float) for g in groups]
    groups = [g[np.isfinite(g)] for g in groups]
    groups = [g for g in groups if len(g) > 0]
    if len(groups) < 2:
        return None
    f, p = stats.f_oneway(*groups)
    return {"f": f, "F": f, "p": p, "df_between": len(groups)-1,
            "df_within": sum(len(g)-1 for g in groups),
            "n_groups": len(groups), "group_means": [np.mean(g) for g in groups]}


def f_test_variances(d1, d2):
    """Prueba F para comparar varianzas."""
    d1 = np.asarray(d1, dtype=float)
    d2 = np.asarray(d2, dtype=float)
    d1 = d1[np.isfinite(d1)]
    d2 = d2[np.isfinite(d2)]
    if len(d1) < 3 or len(d2) < 3:
        return None
    v1, v2 = np.var(d1, ddof=1), np.var(d2, ddof=1)
    if v1 == 0 or v2 == 0:
        return {"error": "Uno de los dos grupos tiene varianza cero: la razon "
                         "de varianzas divide por cero."}
    f_stat = v1 / v2 if v1 >= v2 else v2 / v1
    df1 = (len(d1)-1) if v1 >= v2 else (len(d2)-1)
    df2 = (len(d2)-1) if v1 >= v2 else (len(d1)-1)
    # A dos colas es el doble de la cola MAS CHICA. Poner la varianza mayor
    # arriba no garantiza que esa cola sea la de la derecha: con grados de
    # libertad muy desiguales la mediana de F se aleja de 1, y 2*P(F > f) llego
    # a dar 1,008 (auditoria 2026-09, M3).
    p = float(min(1.0, 2 * min(stats.f.sf(f_stat, df1, df2),
                               stats.f.cdf(f_stat, df1, df2))))
    return {"f": f_stat, "p": p, "df1": df1, "df2": df2,
            "var1": v1, "var2": v2, "sd1": np.std(d1, ddof=1), "sd2": np.std(d2, ddof=1)}


# --- Pruebas no parametricas ---

def mannwhitneyu(d1, d2):
    """Mann-Whitney U (Wilcoxon rank-sum)."""
    d1 = np.asarray(d1, dtype=float)
    d2 = np.asarray(d2, dtype=float)
    d1 = d1[np.isfinite(d1)]
    d2 = d2[np.isfinite(d2)]
    if len(d1) < 2 or len(d2) < 2:
        return None
    u, p = stats.mannwhitneyu(d1, d2, alternative='two-sided')
    return {"u": u, "p": p, "n1": len(d1), "n2": len(d2),
            "mean1": np.mean(d1), "mean2": np.mean(d2),
            "median1": np.median(d1), "median2": np.median(d2)}


def wilcoxon_signed_rank(d1, d2):
    """Wilcoxon signed-rank (pareado)."""
    d1 = np.asarray(d1, dtype=float)
    d2 = np.asarray(d2, dtype=float)
    valid = np.isfinite(d1) & np.isfinite(d2)
    d1, d2 = d1[valid], d2[valid]
    mask = d1 != d2
    d1, d2 = d1[mask], d2[mask]
    if len(d1) < 5:
        return None
    try:
        w, p = stats.wilcoxon(d1, d2)
    except ValueError:
        return None
    return {"w": w, "p": p, "n": len(d1), "mean_diff": np.mean(d1-d2)}


def sign_test(d1, d2):
    """Sign test (prueba de signos)."""
    d1 = np.asarray(d1, dtype=float)
    d2 = np.asarray(d2, dtype=float)
    valid = np.isfinite(d1) & np.isfinite(d2)
    d1, d2 = d1[valid], d2[valid]
    diff = d1 - d2
    diff = diff[diff != 0]
    n = len(diff)
    if n < 5:
        return None
    n_pos = np.sum(diff > 0)
    n_neg = np.sum(diff < 0)
    try:
        p = stats.binomtest(n_pos, n, 0.5).pvalue
    except AttributeError:
        p = 2 * stats.binom.sf(min(n_pos, n_neg) - 1, n, 0.5)
    return {"n_pos": int(n_pos), "n_neg": int(n_neg), "n": n, "p": min(p, 1.0),
            "statistic": float(min(n_pos, n_neg))}


def kruskal_wallis(groups):
    """Kruskal-Wallis."""
    groups = [np.asarray(g, dtype=float) for g in groups]
    groups = [g[np.isfinite(g)] for g in groups]
    groups = [g for g in groups if len(g) > 0]
    if len(groups) < 2:
        return None
    h, p = stats.kruskal(*groups)
    return {"h": h, "p": p, "k": len(groups),
            "group_medians": [np.median(g) for g in groups]}


def dunn_test(groups, labels=None):
    """Post-hoc de Dunn (1964) con corrección de Bonferroni.

    Compara los RANGOS MEDIOS de cada par dentro del ranking conjunto del
    Kruskal-Wallis, con la varianza corregida por empates:

        z = (R̄ᵢ − R̄ⱼ) / √[(N(N+1)/12 − Σ(t³ − t)/(12(N − 1))) · (1/nᵢ + 1/nⱼ)]

    No es lo mismo que Mann-Whitney por pares: Mann-Whitney re-rankea cada par
    por separado y descarta la información de los demás grupos. Con dos grupos
    z² coincide con la H de Kruskal-Wallis, que es como se lo verifica.
    """
    groups = [np.asarray(g, dtype=float) for g in groups]
    groups = [g[np.isfinite(g)] for g in groups]
    if labels is None:
        labels = [str(i + 1) for i in range(len(groups))]
    pares = [(g, lab) for g, lab in zip(groups, labels) if len(g) > 0]
    if len(pares) < 2:
        return None
    groups = [g for g, _ in pares]
    labels = [lab for _, lab in pares]
    todos = np.concatenate(groups)
    n_total = len(todos)
    rangos = stats.rankdata(todos)
    _, conteos = np.unique(todos, return_counts=True)
    empates = float(np.sum(conteos ** 3 - conteos))
    varianza = n_total * (n_total + 1) / 12.0 - empates / (12.0 * (n_total - 1))
    cortes = np.cumsum([0] + [len(g) for g in groups])
    medios = [float(np.mean(rangos[cortes[i]:cortes[i + 1]])) for i in range(len(groups))]
    comparaciones = []
    m = len(groups) * (len(groups) - 1) // 2
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            ee = np.sqrt(varianza * (1 / len(groups[i]) + 1 / len(groups[j]))) if varianza > 0 else 0.0
            z = (medios[i] - medios[j]) / ee if ee > 0 else 0.0
            p = float(2 * stats.norm.sf(abs(z)))
            comparaciones.append({"par": f"{labels[i]} vs {labels[j]}", "z": float(z),
                                  "p": p, "p_adj": min(p * m, 1.0)})
    return {"metodo": "Dunn (Bonferroni)", "rangos_medios": dict(zip(labels, medios)),
            "comparaciones": comparaciones, "n_comparaciones": m}


def welch_anova(groups):
    """ANOVA de Welch: compara medias sin suponer varianzas iguales (pingouin).

    Es la salida cuando los grupos son normales pero dispersan distinto. Kruskal-
    Wallis no sirve ahí: supone la misma forma de distribución bajo H0, y con
    dispersiones distintas rechaza por la dispersión, no por la posición.
    """
    import pandas as pd
    import pingouin as pg
    groups = [np.asarray(g, dtype=float) for g in groups]
    groups = [g[np.isfinite(g)] for g in groups]
    groups = [g for g in groups if len(g) > 0]
    if len(groups) < 2:
        return None
    if any(len(g) < 2 or np.ptp(g) == 0 for g in groups):
        return {"error": "ANOVA de Welch necesita al menos 2 valores distintos por "
                         "grupo: pondera cada grupo por su varianza."}
    datos = pd.DataFrame({"y": np.concatenate(groups),
                          "g": np.repeat(np.arange(len(groups)), [len(g) for g in groups])})
    t = pg.welch_anova(data=datos, dv="y", between="g")
    return {"f": float(t["F"].iloc[0]), "df1": float(t["ddof1"].iloc[0]),
            "df2": float(t["ddof2"].iloc[0]), "p": float(t["p_unc"].iloc[0]),
            "k": len(groups)}


def games_howell(groups, labels=None):
    """Post-hoc de Games-Howell (pingouin): el que acompaña al ANOVA de Welch.

    Cada par con su propio error estándar y grados de libertad de Welch; la
    multiplicidad la controla el rango studentizado, sin corrección aparte.
    """
    import pandas as pd
    import pingouin as pg
    groups = [np.asarray(g, dtype=float) for g in groups]
    groups = [g[np.isfinite(g)] for g in groups]
    if labels is None:
        labels = [str(i + 1) for i in range(len(groups))]
    pares = [(g, str(lab)) for g, lab in zip(groups, labels) if len(g) > 1]
    if len(pares) < 2:
        return None
    datos = pd.DataFrame({"y": np.concatenate([g for g, _ in pares]),
                          "g": np.repeat([lab for _, lab in pares], [len(g) for g, _ in pares])})
    t = pg.pairwise_gameshowell(data=datos, dv="y", between="g")
    return {"metodo": "Games-Howell",
            "comparaciones": [{"par": f"{fila['A']} vs {fila['B']}",
                               "diferencia": float(fila["diff"]),
                               "p_adj": float(fila["pval"])}
                              for _, fila in t.iterrows()]}


def friedman_test(*groups):
    """Friedman test (medidas repetidas)."""
    groups = [np.asarray(g, dtype=float) for g in groups]
    groups = [g for g in groups if len(g) > 0]
    if len(groups) < 3:
        return None
    min_len = min(len(g) for g in groups)
    groups = [g[:min_len] for g in groups]
    try:
        chi2, p = stats.friedmanchisquare(*groups)
    except ValueError:
        return None
    return {"chi2": chi2, "p": p, "k": len(groups), "n": min_len}


def cochran_q(data_matrix):
    """Cochran Q test (statsmodels). Filas = sujetos, columnas = tratamientos (0/1)."""
    data = np.asarray(data_matrix, dtype=float)
    if data.ndim != 2 or data.shape[1] < 2 or data.shape[0] < 2:
        return None
    k = data.shape[1]
    n = data.shape[0]
    res = _sm_cochrans_q(data, return_object=True)
    q = float(res.statistic)
    p = float(res.pvalue)
    df = k - 1
    return {"q": q, "Q": q, "p": p, "df": df, "k": k, "n": n,
            "col_sums": np.sum(data, axis=0).tolist()}


# --- Pruebas de tablas de contingencia ---

def chi_square_test(data_matrix):
    """Chi-cuadrado para tablas de contingencia."""
    data = np.asarray(data_matrix, dtype=float)
    if data.ndim != 2 or data.shape[0] < 2 or data.shape[1] < 2:
        return None
    chi2, p, dof, expected = stats.chi2_contingency(data)
    return {"chi2": chi2, "p": p, "df": dof, "expected": expected,
            "observed": data, "n": int(np.sum(data))}


def fisher_exact_test(a, b, c, d):
    """Fisher exact test para tabla 2x2."""
    table = np.array([[a, b], [c, d]])
    odds_ratio, p = stats.fisher_exact(table)
    return {"odds_ratio": odds_ratio, "p": p, "table": table,
            "a": a, "b": b, "c": c, "d": d}


def mcnemar_test(b, c):
    """McNemar para proporciones apareadas (b y c = pares discordantes).

    Con menos de 25 discordantes el chi2 con correccion de continuidad es una
    aproximacion pobre: se usa la binomial exacta (la que usa statsmodels con
    exact=True). Con 25 o mas, el chi2 corregido de Edwards.
    """
    b, c = int(b), int(c)
    if b + c == 0:
        return {"chi2": 0.0, "p": 1.0, "b": b, "c": c, "discordant": 0,
                "metodo": "sin pares discordantes"}
    chi2 = (abs(b - c) - 1)**2 / (b + c)
    p_chi2 = float(stats.chi2.sf(chi2, df=1))
    p_exacto = float(min(1.0, stats.binomtest(min(b, c), b + c, 0.5).pvalue))
    exacto = b + c < 25
    return {"chi2": chi2, "p": p_exacto if exacto else p_chi2,
            "p_chi2": p_chi2, "p_exacto": p_exacto,
            "metodo": "binomial exacta" if exacto else "chi2 con correccion de Edwards",
            "b": b, "c": c, "discordant": b + c}


# --- Correlacion ---

def pearson_r(d1, d2):
    """Correlacion de Pearson."""
    d1 = np.asarray(d1, dtype=float)
    d2 = np.asarray(d2, dtype=float)
    valid = np.isfinite(d1) & np.isfinite(d2)
    d1, d2 = d1[valid], d2[valid]
    n = len(d1)
    if n < 3:
        return None
    if np.ptp(d1) == 0 or np.ptp(d2) == 0:
        return {"error": "Una de las dos variables es constante: la "
                         "correlacion divide por su dispersion."}
    r, p = stats.pearsonr(d1, d2)
    return {"r": r, "r2": r**2, "p": p, "n": n}


def spearman_rho(d1, d2):
    """Correlacion de Spearman."""
    d1 = np.asarray(d1, dtype=float)
    d2 = np.asarray(d2, dtype=float)
    valid = np.isfinite(d1) & np.isfinite(d2)
    d1, d2 = d1[valid], d2[valid]
    n = len(d1)
    if n < 3:
        return None
    if np.ptp(d1) == 0 or np.ptp(d2) == 0:
        return {"error": "Una de las dos variables es constante: todos sus "
                         "rangos empatan y la correlacion no esta definida."}
    r, p = stats.spearmanr(d1, d2)
    return {"rho": r, "p": p, "n": n}


def partial_correlation(x, y, z):
    """Correlacion parcial controlando z."""
    x, y, z = np.asarray(x, dtype=float), np.asarray(y, dtype=float), np.asarray(z, dtype=float)
    valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    x, y, z = x[valid], y[valid], z[valid]
    n = len(x)
    if n < 4:
        return None
    if np.ptp(x) == 0 or np.ptp(y) == 0 or np.ptp(z) == 0:
        return {"error": "Alguna de las tres variables es constante: la "
                         "correlacion parcial divide por su dispersion."}
    r_xz = np.corrcoef(x, z)[0, 1]
    r_yz = np.corrcoef(y, z)[0, 1]
    r_xy = np.corrcoef(x, y)[0, 1]
    denom = np.sqrt(max(0, (1 - r_xz**2) * (1 - r_yz**2)))
    if denom == 0:
        return None
    r_partial = (r_xy - r_xz * r_yz) / denom
    r_partial = np.clip(r_partial, -1, 1)
    t_denom = 1 - r_partial**2
    if t_denom <= 0:
        return None
    t_stat = r_partial * np.sqrt((n - 3) / t_denom)
    p = 2 * (1 - stats.t.cdf(abs(t_stat), n - 3))
    return {"r_partial": r_partial, "t": t_stat, "p": p, "df": n-3, "n": n}


def normality_test(data):
    """Shapiro-Wilk para normalidad."""
    data = np.asarray(data, dtype=float)
    data = data[np.isfinite(data)]
    n = len(data)
    if n < 3:
        return None
    if n > 5000:
        data = np.random.RandomState(42).choice(data, 5000, replace=False)
    w, p = stats.shapiro(data)
    return {"w": w, "statistic": w, "p": p, "n": len(data), "normal": p >= 0.05}
