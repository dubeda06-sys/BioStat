"""Concordancia y evaluacion — Kappa, ICC, Cronbach, concordance."""
import numpy as np
import pandas as pd
import pingouin as pg
from scipy import stats

from src.core.guards import finite_pair


def cohens_kappa(matrix):
    """Kappa de Cohen con su IC 95 % y su p (Fleiss, Cohen y Everitt, 1969).

    Dos errores estandar distintos, cada uno para lo suyo:
      - el del IC es el de Fleiss bajo H1 (kappa como esta);
      - el del p es el que vale bajo H0 (kappa = 0).
    Antes el p usaba el de H1 y salia mas chico que el que corresponde (0,0020
    contra 0,0039), y no habia IC. Los dos salen de statsmodels.
    """
    from statsmodels.stats.inter_rater import cohens_kappa as _sm_kappa

    m = np.asarray(matrix, dtype=float)
    n = np.sum(m)
    k = m.shape[0]
    if n == 0 or k < 2:
        return None
    row_sums = np.sum(m, axis=1)
    col_sums = np.sum(m, axis=0)
    p_o = np.sum(np.diag(m)) / n
    p_e = np.sum(row_sums * col_sums) / n**2
    if 1 - p_e == 0:
        return {"error": "Todos los casos cayeron en una sola categoria para los "
                         "dos evaluadores: el acuerdo esperado por azar es 1 y "
                         "kappa no esta definido."}
    sm = _sm_kappa(m)
    kappa = float(sm.kappa)
    se = float(sm.std_kappa)
    se0 = float(np.sqrt(sm.var_kappa0))
    z = kappa / se0 if se0 > 0 else 0.0
    p = float(2 * stats.norm.sf(abs(z)))
    ci = (float(sm.kappa_low), float(sm.kappa_upp))
    if kappa < 0.2:
        strength = "Pobre"
    elif kappa < 0.4:
        strength = "Regular"
    elif kappa < 0.6:
        strength = "Moderado"
    elif kappa < 0.8:
        strength = "Bueno"
    else:
        strength = "Muy bueno"
    return {"kappa": kappa, "se": se, "se0": se0, "z": z, "p": p, "ci": ci,
            "po": p_o, "pe": p_e, "strength": strength, "n": int(n), "matrix": m}


def weighted_kappa(matrix, weights="linear"):
    """Kappa ponderado (Cohen, 1968).

    Pondera los desacuerdos por su distancia: confundir "leve" con "grave"
    pesa mas que confundir "leve" con "moderado". Pesos lineales |i-j| o
    cuadraticos (i-j)^2.

    El factor de normalizacion de los pesos se cancela en el cociente
    (kappa_w = 1 - d_obs/d_esp), asi que da igual dividir por (k-1) o no: el
    resultado coincide con `sklearn.metrics.cohen_kappa_score(weights=...)`.
    """
    m = np.asarray(matrix, dtype=float)
    n = np.sum(m)
    k = m.shape[0]
    if n == 0 or k < 2:
        return None
    if weights not in ("linear", "quadratic"):
        return {"error": f"Pesos '{weights}' no reconocidos: usa 'linear' o "
                         f"'quadratic'."}
    i, j = np.indices((k, k))
    w = (np.abs(i - j) / (k - 1) if weights == "linear"
         else (i - j) ** 2 / (k - 1) ** 2)

    row_sums = np.sum(m, axis=1)
    col_sums = np.sum(m, axis=0)
    # Frecuencias ESPERADAS en cuentas, no en proporciones: la division por n
    # se hace una sola vez, igual que para las observadas. Dividir dos veces
    # deja p_e ~ 1 y el cociente estalla contra un denominador ~0 (daba -55).
    esperadas = np.outer(row_sums, col_sums) / n
    p_o = 1 - np.sum(w * m) / n
    p_e = 1 - np.sum(w * esperadas) / n
    kappa = (p_o - p_e) / (1 - p_e) if (1 - p_e) != 0 else 0
    return {"kappa": kappa, "po": p_o, "pe": p_e, "weights": weights, "n": int(n)}


def intraclass_correlation(data, model="one-way"):
    """Coeficiente de correlacion intraclase (ICC) via pingouin.

    data: matriz 2D (n sujetos x k evaluadores).
    model: 'one-way' -> ICC1, 'two-way-random' -> ICC2, 'two-way-mixed' -> ICC3.
    """
    data = np.asarray(data, dtype=float)
    if data.ndim != 2:
        return None
    n, k = data.shape
    if n < 2 or k < 2:
        return None

    # Formato largo para pingouin
    targets = np.repeat(np.arange(n), k)
    raters = np.tile(np.arange(k), n)
    ratings = data.ravel()
    long_df = pd.DataFrame({"target": targets, "rater": raters, "score": ratings}).dropna()

    # Shrout & Fleiss: one-way=ICC(1,1), two-way-random absoluto=ICC(A,1),
    # two-way-mixed consistencia=ICC(C,1)
    type_map = {"one-way": "ICC(1,1)", "two-way-random": "ICC(A,1)", "two-way-mixed": "ICC(C,1)"}
    icc_type = type_map.get(model, "ICC(1,1)")
    try:
        res = pg.intraclass_corr(data=long_df, targets="target", raters="rater", ratings="score")
    except Exception:
        return None
    sub = res[res["Type"] == icc_type]
    if sub.empty:
        return None
    row = sub.iloc[0]
    ci_col = "CI95" if "CI95" in res.columns else ("CI95%" if "CI95%" in res.columns else None)
    ci = row[ci_col] if ci_col is not None else (np.nan, np.nan)
    return {"icc": float(row["ICC"]), "f": float(row["F"]), "p": float(row["pval"]),
            "df1": int(row["df1"]), "df2": int(row["df2"]),
            "ci_low": float(ci[0]), "ci_high": float(ci[1]),
            "n": n, "k": k, "model": model, "type": icc_type}


def cronbach_alpha(data):
    """Alfa de Cronbach para escala/likert."""
    data = np.asarray(data, dtype=float)
    if data.ndim != 2 or data.shape[0] < 2:
        return None
    n_items = data.shape[1]
    n_subjects = data.shape[0]
    if n_items < 2:
        return {"error": "El alfa de Cronbach necesita al menos 2 items."}
    item_variances = np.var(data, axis=0, ddof=1)
    total_variance = np.var(np.sum(data, axis=1), ddof=1)
    sum_var = np.sum(item_variances)
    if total_variance == 0:
        # Antes devolvia alfa = 0: un numero inventado donde no hay ninguno.
        return {"error": "La suma de los items es igual en todos los sujetos: la "
                         "varianza total es cero y el alfa no esta definido."}
    alpha = (n_items / (n_items - 1)) * (1 - sum_var / total_variance)
    return {"alpha": alpha, "n_items": n_items, "n_subjects": n_subjects,
            "item_variances": item_variances.tolist()}


def _deming_fit(x, y, lam):
    """Ajuste de Deming (núcleo). lam = λ = var_error(x)/var_error(y).

    La fórmula cerrada está escrita en términos de δ = var_error(y)/var_error(x)
    (Deming 1943; Cornbleet y Gochman 1979), o sea δ = 1/λ. Antes se metía λ
    directo donde va δ: con λ ≠ 1 la corrección iba para el lado contrario.
    Contra scipy.odr con errores conocidos (DE 6 en X, 1,5 en Y) daba 1,076
    donde corresponde 1,089 (auditoría 2026-09, A13). Con λ = 1 no cambia nada.
    """
    n = len(x)
    mx, my = np.mean(x), np.mean(y)
    sxx = np.sum((x - mx) ** 2) / (n - 1)
    syy = np.sum((y - my) ** 2) / (n - 1)
    sxy = np.sum((x - mx) * (y - my)) / (n - 1)
    if sxy == 0:
        return None
    delta = 1.0 / lam
    slope = ((syy - delta * sxx) + np.sqrt((syy - delta * sxx) ** 2 + 4 * delta * sxy ** 2)) / (2 * sxy)
    intercept = my - slope * mx
    return slope, intercept


def deming_regression(x, y, lambda_ratio=1.0):
    """Regresión de Deming (comparación de métodos, CLSI EP09).

    Modelo de error en ambos ejes. `lambda_ratio` (λ) es la razón de varianzas
    del error analítico entre X e Y (λ = σ²ε(x)/σ²ε(y)); λ=1 asume igual
    precisión (Deming ortogonal). IC 95% de pendiente e intercepto por jackknife
    (método de Linnet).

    Devuelve slope, intercept, ci_slope, ci_intercept, r2, n, lambda.
    """
    x, y, motivo = finite_pair(x, y, min_n=3, need_variance="both",
                               nombre_metodo="la regresion de Deming")
    if motivo:
        return {"error": motivo}
    n = len(x)
    lam = float(lambda_ratio) if lambda_ratio and lambda_ratio > 0 else 1.0

    fit = _deming_fit(x, y, lam)
    if fit is None:
        return {"error": "La covarianza entre los dos metodos es cero: no hay "
                         "relacion que ajustar por Deming."}
    slope, intercept = fit
    ci_slope, ci_intercept = _ic_jackknife(x, y, slope, intercept,
                                           lambda xs, ys: _deming_fit(xs, ys, lam))

    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    return {"slope": slope, "intercept": intercept,
            "ci_slope": ci_slope, "ci_intercept": ci_intercept,
            "r2": r2, "n": n, "lambda": lam,
            "x_mean": float(np.mean(x)), "y_mean": float(np.mean(y))}


def _ic_jackknife(x, y, slope, intercept, ajustar):
    """IC 95% de pendiente e intercepto por jackknife (CLSI EP09c, apéndice K1).

    Se deja afuera una muestra por vez y se reajusta con `ajustar`. Con las
    pseudo-desviaciones δᵢ = N·b − (N−1)·bᵢ, el EE es √(Σ(δᵢ − δ̄)² / (N(N−1)))
    (K7, K8), y el intervalo es la estimación del conjunto completo ± t(N−2)·EE
    (K12). Antes se usaba t(N−1): el grado de libertad de más estrechaba el
    intervalo, poco, pero en contra de la norma.
    """
    n = len(x)
    js, ji = [], []
    for k in range(n):
        m = np.ones(n, dtype=bool)
        m[k] = False
        f = ajustar(x[m], y[m])
        if f is None:
            continue
        js.append(f[0])
        ji.append(f[1])
    js, ji = np.asarray(js, dtype=float), np.asarray(ji, dtype=float)
    if len(js) < 2 or n < 3:
        return (np.nan, np.nan), (np.nan, np.nan)
    m = len(js)
    tcrit = stats.t.ppf(0.975, n - 2)
    se_slope = np.sqrt((m - 1) / m * np.sum((js - js.mean()) ** 2))
    se_int = np.sqrt((m - 1) / m * np.sum((ji - ji.mean()) ** 2))
    return ((slope - tcrit * se_slope, slope + tcrit * se_slope),
            (intercept - tcrit * se_int, intercept + tcrit * se_int))


def _deming_ponderado_fit(x, y, lam, max_iter=100, tol=1e-12):
    """Deming ponderado de CV constante (Linnet 1990; CLSI EP09c, apéndice B).

    Cada punto pesa wᵢ = 1/zᵢ², con zᵢ = (X̂ᵢ + λ·Ŷᵢ)/(1 + λ) la concentración
    verdadera estimada (B13-B15). Como X̂ e Ŷ salen de la recta, se itera: se
    arranca con los valores medidos, se ajusta con los momentos ponderados
    (B1-B11) y se recalculan los pesos hasta que la pendiente no se mueve.

    λ = var_error(x)/var_error(y), la misma convención que `_deming_fit`.
    Devuelve (pendiente, intercepto) o None si algún zᵢ no es positivo — el
    peso 1/z² no existe en cero (EP09c §6.2.2) — o si no converge.
    """
    z = (x + lam * y) / (1 + lam)
    if np.any(z <= 0):
        return None
    b_ant = None
    for _ in range(max_iter):
        w = 1.0 / z ** 2
        sw = np.sum(w)
        xw, yw = np.sum(w * x) / sw, np.sum(w * y) / sw
        u = np.sum(w * (x - xw) ** 2)
        q = np.sum(w * (y - yw) ** 2)
        p = np.sum(w * (x - xw) * (y - yw))
        if p == 0:
            return None
        b = ((lam * q - u) + np.sqrt((u - lam * q) ** 2 + 4 * lam * p ** 2)) / (2 * lam * p)
        a = yw - b * xw
        # Valor verdadero estimado de cada muestra: el punto de la recta al que
        # Deming proyecta (x, y), con λ como métrica.
        xh = x + (b * lam) * (y - a - b * x) / (1 + b * b * lam)
        yh = a + b * xh
        z = (xh + lam * yh) / (1 + lam)
        if np.any(z <= 0):
            return None
        if b_ant is not None and abs(b - b_ant) <= tol * max(1.0, abs(b)):
            return b, a
        b_ant = b
    return None


def deming_ponderado(x, y, lambda_ratio=1.0):
    """Regresión de Deming ponderada, de CV constante (CLSI EP09c, apéndice B).

    La que corresponde cuando la dispersión de las diferencias crece con la
    concentración (EP09c §6.2.2): los puntos altos, más ruidosos, pesan menos.
    Con Deming sin ponderar esos puntos arrastran la recta. Exige valores
    positivos en los dos métodos.

    IC 95% de pendiente e intercepto por jackknife (apéndice K1), reajustando
    la iteración completa en cada submuestra.

    Devuelve las mismas claves que `deming_regression`.
    """
    x, y, motivo = finite_pair(x, y, min_n=3, need_variance="both",
                               nombre_metodo="la regresion de Deming ponderada")
    if motivo:
        return {"error": motivo}
    no_positivos = int(np.sum((x <= 0) | (y <= 0)))
    if no_positivos:
        return {"error": f"Deming ponderado pesa cada punto por 1/concentración², y "
                         f"hay {no_positivos} par(es) con un valor ≤ 0: ese peso no "
                         f"existe (CLSI EP09c §6.2.2)."}
    n = len(x)
    lam = float(lambda_ratio) if lambda_ratio and lambda_ratio > 0 else 1.0
    fit = _deming_ponderado_fit(x, y, lam)
    if fit is None:
        return {"error": "La iteración de Deming ponderado no convergió con estos "
                         "datos."}
    slope, intercept = fit
    ci_slope, ci_intercept = _ic_jackknife(
        x, y, slope, intercept, lambda xs, ys: _deming_ponderado_fit(xs, ys, lam))

    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    return {"slope": slope, "intercept": intercept,
            "ci_slope": ci_slope, "ci_intercept": ci_intercept,
            "r2": r2, "n": n, "lambda": lam,
            "x_mean": float(np.mean(x)), "y_mean": float(np.mean(y))}


def cv_from_duplicates(d1, d2):
    """CV desde mediciones duplicadas."""
    d1, d2, motivo = finite_pair(d1, d2, min_n=3,
                                 nombre_metodo="el CV a partir de duplicados")
    if motivo:
        return {"error": motivo}
    n = len(d1)
    means = (d1 + d2) / 2
    diffs = d1 - d2
    if np.mean(means) == 0:
        return {"error": "La media de los duplicados es cero: el CV es un "
                         "cociente y no esta definido."}
    cv_dup = np.std(diffs, ddof=1) / (np.sqrt(2) * np.mean(means)) * 100
    return {"cv_dup": cv_dup, "cv_dup_pct": f"{cv_dup:.2f}%",
            "mean_cv": np.mean(means), "n": n}
