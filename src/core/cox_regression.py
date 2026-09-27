"""Cox Proportional Hazards Regression."""
import numpy as np
from scipy import optimize, stats


def _log_verosimilitud_efron(beta, x, eventos, grupos):
    """Log-verosimilitud parcial de Cox con la correccion de Efron para empates.

    Efron es el default de lifelines y de coxph() en R. Con tiempos continuos
    coincide con Breslow; con empates —que en laboratorio son la regla, porque
    los tiempos se anotan en dias o meses— Breslow sesga los coeficientes hacia
    cero y Efron no.

    `grupos` viene ordenado de MAYOR a menor tiempo, asi que el conjunto de
    riesgo de un tiempo es todo lo que quedo por delante en el arreglo, o sea
    la suma acumulada hasta ese punto.
    """
    xb = x @ beta
    # Corrimiento por el maximo para que exp() no desborde. Como M depende de
    # beta, NO es una constante que se cancele sola en el argmax: hay que
    # descontarla exacto. log(resto * e^-M) = log(resto) - M, y hay d terminos
    # por grupo, asi que sobran d*M que se restan.
    M = np.max(xb)
    exp_xb = np.exp(xb - M)
    acum = np.cumsum(exp_xb)

    ll = 0.0
    for fin, idx_evt in grupos:
        d = len(idx_evt)
        s0_riesgo = acum[fin]
        s0_muertos = np.sum(exp_xb[idx_evt])
        ll += np.sum(xb[idx_evt])
        for l in range(d):
            resto = s0_riesgo - (l / d) * s0_muertos
            if resto <= 0:
                return -np.inf
            ll -= np.log(resto)
        ll -= d * M
    return ll


def _hessiana(f, beta, h=1e-5):
    """Hessiana por diferencias centradas. La log-verosimilitud parcial es
    suave, asi que alcanza y evita derivar Efron a mano."""
    p = len(beta)
    H = np.zeros((p, p))
    paso = h * np.maximum(1.0, np.abs(beta))
    for i in range(p):
        for j in range(i, p):
            ei, ej = np.zeros(p), np.zeros(p)
            ei[i], ej[j] = paso[i], paso[j]
            H[i, j] = H[j, i] = (f(beta + ei + ej) - f(beta + ei - ej)
                                 - f(beta - ei + ej) + f(beta - ei - ej)
                                 ) / (4 * paso[i] * paso[j])
    return H


def cox_regression(times, events, covariates):
    """
    Cox Proportional Hazards Regression (correccion de Efron para empates).

    Args:
        times: event/censoring times
        events: event indicators (1=event, 0=censored)
        covariates: 2D array of covariates (n x p)

    Returns:
        dict with hazard ratios, p-values, and log-likelihood
    """
    times = np.asarray(times, dtype=float)
    events = np.asarray(events, dtype=int)
    covariates = np.atleast_2d(np.asarray(covariates, dtype=float))
    if covariates.shape[0] != len(times):
        covariates = covariates.T

    valido = np.isfinite(times) & np.isfinite(events) & np.all(np.isfinite(covariates), axis=1)
    times, events, covariates = times[valido], events[valido], covariates[valido]

    n = len(times)
    if n == 0:
        return {"error": "No quedan observaciones validas."}
    p = covariates.shape[1]
    n_eventos = int(np.sum(events == 1))
    if n_eventos == 0:
        return {"error": "No hay ningun evento observado: todos los sujetos "
                         "estan censurados y no hay nada que modelar."}
    if n_eventos <= p:
        return {"error": f"Hay {n_eventos} eventos para {p} covariables. Se "
                         f"necesitan bastantes mas eventos que covariables "
                         f"(regla habitual: al menos 10 por covariable)."}

    # Orden descendente por tiempo: el conjunto de riesgo de cada posicion es
    # el prefijo del arreglo. Con `mergesort` el orden de los empates es
    # estable y el resultado es reproducible.
    orden = np.argsort(-times, kind="mergesort")
    times, events, covariates = times[orden], events[orden], covariates[orden]

    # Un grupo por tiempo de evento distinto: (ultimo indice del conjunto de
    # riesgo, indices de los que tuvieron el evento en ese tiempo).
    grupos = []
    i = 0
    while i < n:
        j = i
        while j + 1 < n and times[j + 1] == times[i]:
            j += 1
        idx_evt = np.array([k for k in range(i, j + 1) if events[k] == 1])
        if len(idx_evt):
            grupos.append((j, idx_evt))
        i = j + 1

    def neg_ll(beta):
        v = _log_verosimilitud_efron(beta, covariates, events, grupos)
        return np.inf if not np.isfinite(v) else -v

    resultado = optimize.minimize(neg_ll, np.zeros(p), method="BFGS",
                                  options={"gtol": 1e-8, "maxiter": 500})
    beta = resultado.x

    # Errores estandar de la informacion observada: la inversa de la hessiana
    # de la log-verosimilitud NEGATIVA en el optimo. Antes esto leia un
    # atributo mal escrito (`hes_inv` en vez de `hess_inv`), el hasattr daba
    # siempre False y caia en un `np.eye(p)*0.01` de reserva: TODOS los
    # errores estandar valian 0.1, con cualquier dato y cualquier n, y de ahi
    # salian los z y los p.
    info = _hessiana(neg_ll, beta)
    try:
        cov = np.linalg.inv(info)
        se = np.sqrt(np.abs(np.diag(cov)))
    except np.linalg.LinAlgError:
        se = np.full(p, np.nan)

    # Convergencia por el gradiente en el optimo, no por `resultado.success`:
    # con gtol=1e-8 BFGS casi siempre termina con «precision loss» (success
    # False) aunque el gradiente ya sea ~1e-5, y el panel avisaba «no
    # convergio» en 19 de cada 20 ajustes sanos. Y al reves, con separacion
    # (todos los eventos en un grupo) la verosimilitud se aplana, BFGS da
    # success True con b = 17 y EE = 1258, y pasaba como convergido.
    paso = 1e-6 * np.maximum(1.0, np.abs(beta))
    gradiente = np.array([(neg_ll(beta + paso[i] * np.eye(p)[i])
                           - neg_ll(beta - paso[i] * np.eye(p)[i])) / (2 * paso[i])
                          for i in range(p)])
    de_x = covariates.std(axis=0)
    # Por DE de la covariable, para que no dependa de la unidad: un HR de
    # e^10 por DE, o un IC que abarca e^±10 por DE, es una verosimilitud sin
    # maximo finito, no un efecto.
    separadas = [j for j in range(p)
                 if np.isfinite(se[j]) and (abs(beta[j]) * de_x[j] > 10 or se[j] * de_x[j] > 5)]
    convergio = bool(np.all(np.isfinite(se)) and np.all(np.isfinite(gradiente))
                     and np.max(np.abs(gradiente)) < 1e-3 and not separadas)
    avisos = []
    if separadas:
        avisos.append("La verosimilitud no tiene maximo finito para la(s) covariable(s) "
                      + ", ".join(str(j + 1) for j in separadas) + " (separacion: por "
                      "ejemplo, todos los eventos en un solo grupo): el HR tiende a "
                      "infinito o a cero y su IC y su p no sirven.")
    elif not convergio:
        avisos.append("El ajuste de Cox no convergio o la matriz de informacion "
                      "es singular: los errores estandar y los p no son "
                      "confiables. Suele pasar con separacion completa o con "
                      "covariables colineales.")
    if n_eventos < 10 * p:
        avisos.append(f"{n_eventos} eventos para {p} covariables: por debajo de "
                      f"los 10 eventos por covariable que se recomiendan. Los "
                      f"coeficientes pueden estar sesgados.")

    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(se > 0, beta / se, np.nan)
    p_values = 2 * (1 - stats.norm.cdf(np.abs(z)))

    hr = np.exp(beta)
    hr_ci_low = np.exp(beta - 1.96 * se)
    hr_ci_high = np.exp(beta + 1.96 * se)

    log_likelihood = -resultado.fun
    # AIC = 2k - 2*logL. El signo del segundo termino estaba invertido, asi
    # que el AIC premiaba los modelos peores.
    aic = 2 * p - 2 * log_likelihood
    # Razon de verosimilitudes contra el modelo sin covariables (beta = 0).
    ll_nulo = -neg_ll(np.zeros(p))
    lr = max(2 * (log_likelihood - ll_nulo), 0.0)

    ph = None
    if convergio:
        ph = riesgos_proporcionales(times, events, covariates, beta, cov, grupos)

    return {
        'avisos': avisos,
        'convergio': convergio,
        'separadas': separadas,
        'coefficients': beta,
        'hazard_ratios': hr,
        'se': se,
        'z': z,
        'p_values': p_values,
        'hr_ci_low': hr_ci_low,
        'hr_ci_high': hr_ci_high,
        'log_likelihood': log_likelihood,
        'log_likelihood_nulo': ll_nulo,
        'lr_chi2': lr,
        'lr_gl': p,
        'lr_p': float(stats.chi2.sf(lr, p)),
        'cov': cov if convergio else None,
        'aic': aic,
        'n': n,
        'events': n_eventos,
        'empates': 'Efron',
        'riesgos_proporcionales': ph,
    }


def _schoenfeld(beta, x, grupos):
    """Residuos de Schoenfeld con la media de Efron, uno por evento.

    En un tiempo con d eventos empatados, la media ponderada del conjunto de
    riesgo se promedia sobre las d «bajas» parciales de Efron; sin empates es la
    media de siempre. En el optimo suman cero: son la ecuacion de score.
    Devuelve (residuos, indice de cada evento en `x`).
    """
    xb = x @ beta
    w = np.exp(xb - np.max(xb))
    acum0 = np.cumsum(w)
    acum1 = np.cumsum(w[:, None] * x, axis=0)
    filas, indices = [], []
    for fin, idx_evt in grupos:
        d = len(idx_evt)
        s0d = np.sum(w[idx_evt])
        s1d = np.sum(w[idx_evt, None] * x[idx_evt], axis=0)
        media = np.mean([(acum1[fin] - (l / d) * s1d) / (acum0[fin] - (l / d) * s0d)
                         for l in range(d)], axis=0)
        for i in idx_evt:
            filas.append(x[i] - media)
            indices.append(i)
    return np.array(filas), np.array(indices)


def _km_izquierda(times, events, t):
    """1 - KM(t-) de toda la muestra: la escala de tiempo `km` de R.

    Continua por izquierda, como `cox.zph`: en un tiempo con evento vale la
    supervivencia de justo antes."""
    ts = np.unique(times[events == 1])
    n_r = np.array([np.sum(times >= s) for s in ts])
    d = np.array([np.sum((times == s) & (events == 1)) for s in ts])
    S = np.cumprod(1 - d / n_r)
    antes = np.searchsorted(ts, t, side="left")
    return 1 - np.where(antes > 0, S[np.maximum(antes - 1, 0)], 1.0)


def riesgos_proporcionales(times, events, covariates, beta, cov, grupos,
                           transformacion="km"):
    """Prueba de riesgos proporcionales de Grambsch y Therneau (1994).

    Si el efecto de una covariable cambia con el tiempo, sus residuos de
    Schoenfeld escalados siguen una tendencia contra el tiempo. Con g(t) el
    tiempo transformado (`km`: 1 - KM(t-), el default de R; `rank`: el rango)
    y r los residuos:

        por covariable: T_j = (sum (g - g_media) r*_j)^2 / (D var(b_j) sum (g - g_media)^2)
        global:         T = U' V U · D / sum (g - g_media)^2,  U = sum (g - g_media) r

    con r* = D·r·V, D = eventos, V = var(b). chi2 con 1 y con p gl. Es la
    aproximacion que usaba `cox.zph` de R hasta 2019 y la que usa lifelines.
    `grupos` y los arreglos vienen como los deja `cox_regression`.
    """
    r, idx = _schoenfeld(beta, covariates, grupos)
    t_ev = times[idx]
    if transformacion == "rank":
        g = stats.rankdata(t_ev)
    else:
        g = _km_izquierda(times, events, t_ev)
    D, p = r.shape
    xx = g - g.mean()
    sxx = float(np.sum(xx ** 2))
    if sxx <= 0:
        return {"error": "Todos los eventos ocurrieron al mismo tiempo: no hay tendencia "
                         "en el tiempo que probar."}
    u = xx @ r
    escalados = D * r @ cov
    chi2 = (xx @ escalados) ** 2 / (D * np.diag(cov) * sxx)
    chi2_global = float(u @ cov @ u * D / sxx)
    with np.errstate(invalid="ignore"):
        rho = np.array([np.corrcoef(xx, escalados[:, j])[0, 1] for j in range(p)])
    return {
        "chi2": chi2,
        "p": stats.chi2.sf(chi2, 1),
        "rho": rho,
        "chi2_global": chi2_global,
        "gl_global": p,
        "p_global": float(stats.chi2.sf(chi2_global, p)),
        "transformacion": transformacion,
        "g": g,
        # beta(t) estimado: lo que se grafica contra g
        "residuos_escalados": escalados + beta,
        "suma_residuos": r.sum(axis=0),
    }
