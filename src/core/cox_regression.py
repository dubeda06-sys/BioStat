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

    convergio = bool(resultado.success) and np.all(np.isfinite(se))
    avisos = []
    if not convergio:
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

    return {
        'avisos': avisos,
        'convergio': convergio,
        'coefficients': beta,
        'hazard_ratios': hr,
        'se': se,
        'z': z,
        'p_values': p_values,
        'hr_ci_low': hr_ci_low,
        'hr_ci_high': hr_ci_high,
        'log_likelihood': log_likelihood,
        'aic': aic,
        'n': n,
        'events': n_eventos,
        'empates': 'Efron',
    }
