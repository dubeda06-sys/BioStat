"""Analisis de supervivencia: Kaplan-Meier y log-rank.

Verificado contra lifelines (`tests/test_modelos_oraculo.py`,
`tests/test_supervivencia_resultado.py`).
"""
import numpy as np
from scipy import stats

# Tolerancia para decidir si la curva llego a un nivel (0,5 para la mediana).
# S(t) sale de un producto y 0,5 exacto puede quedar en 0,5000000000000001;
# R usa sqrt(eps) por lo mismo.
_TOL = 1e-9


def _limpiar(times, events):
    """(tiempos, eventos, error). Descarta los no finitos; rechaza tiempos
    negativos y eventos que no son 0/1."""
    times = np.asarray(times, dtype=float)
    events = np.asarray(events, dtype=float)
    valid = np.isfinite(times) & np.isfinite(events)
    times, events = times[valid], events[valid]
    if len(times) == 0:
        return None, None, "No quedan observaciones validas."
    if np.any(times < 0):
        return None, None, ("Hay tiempos negativos: el tiempo de seguimiento no puede "
                            "ser menor que cero. Revisa la columna de tiempo.")
    if not np.all(np.isin(events, (0.0, 1.0))):
        return None, None, "El evento tiene que ser 0/1 (1 = evento, 0 = censura)."
    return times, events.astype(int), None


def _primer_tiempo(tiempos, curva, nivel):
    """Primer tiempo en que la curva queda en `nivel` o debajo; None si no llega."""
    idx = np.nonzero(curva <= nivel + _TOL)[0]
    return float(tiempos[idx[0]]) if len(idx) else None


def kaplan_meier(times, events, alpha=0.05):
    """Estimacion de Kaplan-Meier con IC log-log y los tiempos cuantiles.

    El IC de cada punto es el log-log de Kalbfleisch y Prentice (el default de
    lifelines): S^exp(±z·se), con se = sqrt(Greenwood)/|ln S|. Queda siempre
    dentro de [0, 1]. Antes era S ± 1,96·EE recortado a [0, 1], que en la cola
    da intervalos que tocan 0 o 1 sin motivo.

    `cuantiles[q]` = (tiempo, limite inferior, limite superior) en que la
    fraccion q tuvo el evento: q = 0,5 es la mediana. El tiempo es el primero
    con S(t) <= 1 - q; su IC, donde las bandas del IC cruzan 1 - q
    (Brookmeyer y Crowley 1982, con la transformacion log-log). None = la curva
    no llego a ese nivel en el seguimiento.
    """
    times, events, error = _limpiar(times, events)
    if error:
        return {"error": error}

    unicos = np.unique(times)
    n = len(times)
    en_riesgo = np.array([np.sum(times >= t) for t in unicos])
    eventos = np.array([np.sum((times == t) & (events == 1)) for t in unicos])
    censurados = np.array([np.sum((times == t) & (events == 0)) for t in unicos])

    surv = np.cumprod(1.0 - eventos / en_riesgo)
    with np.errstate(divide="ignore", invalid="ignore"):
        # Si todos los que quedan tienen el evento, S cae a 0 y ese termino de
        # Greenwood es infinito; de ahi en adelante la curva es 0 y su IC tambien.
        termino = np.where(en_riesgo - eventos > 0,
                           eventos / (en_riesgo * (en_riesgo - eventos)), 0.0)
    greenwood = np.cumsum(termino)

    # La curva arranca en 1 a tiempo 0, salvo que haya eventos en t = 0.
    if unicos[0] > 0:
        unicos = np.concatenate([[0.0], unicos])
        surv = np.concatenate([[1.0], surv])
        greenwood = np.concatenate([[0.0], greenwood])
        en_riesgo = np.concatenate([[n], en_riesgo])
        eventos = np.concatenate([[0], eventos])
        censurados = np.concatenate([[0], censurados])

    se = surv * np.sqrt(greenwood)
    z = stats.norm.ppf(1 - alpha / 2)
    with np.errstate(divide="ignore", invalid="ignore"):
        se_theta = np.sqrt(greenwood) / np.abs(np.log(surv))
        inferior = surv ** np.exp(z * se_theta)
        superior = surv ** np.exp(-z * se_theta)
    extremo = (surv >= 1.0) | (surv <= 0.0)
    inferior = np.where(extremo, surv, inferior)
    superior = np.where(extremo, surv, superior)

    cuantiles = {}
    for q in (0.25, 0.5, 0.75):
        nivel = 1.0 - q
        cuantiles[q] = (_primer_tiempo(unicos, surv, nivel),
                        _primer_tiempo(unicos, inferior, nivel),
                        _primer_tiempo(unicos, superior, nivel))

    con_evento = np.nonzero(eventos > 0)[0]
    return {
        "times": unicos,
        "survival": surv,
        "se": se,
        "ci_lower": inferior,
        "ci_upper": superior,
        "at_risk": en_riesgo,
        "events_at": eventos,
        "censored_at": censurados,
        "n_total": n,
        "n_events": int(np.sum(events)),
        "n_censored": int(n - np.sum(events)),
        "median_survival": cuantiles[0.5][0],
        "median_ci": cuantiles[0.5][1:],
        "cuantiles": cuantiles,
        # Cuantos quedaban en riesgo en el ultimo evento: la cola de la curva
        # se apoya en ellos.
        "en_riesgo_ultimo_evento": int(en_riesgo[con_evento[-1]]) if len(con_evento) else n,
        "censura_tiempos": times[events == 0],
    }


def log_rank_k(times, events, groups):
    """Log-rank de k grupos (Mantel 1966). `groups`: un codigo por sujeto.

    chi2 = (O - E)' V^-1 (O - E) sobre k - 1 grupos, gl = k - 1. Con dos
    grupos es la prueba de siempre y ademas da el hazard ratio por O/E
    (Altman 1991): HR = (O2/E2)/(O1/E1) del segundo grupo respecto del primero,
    con IC exp(ln HR ± z·sqrt(1/E1 + 1/E2)).
    """
    groups = np.asarray(groups)
    times_f = np.asarray(times, dtype=float)
    events_f = np.asarray(events, dtype=float)
    valid = np.isfinite(times_f) & np.isfinite(events_f)
    groups = groups[valid]
    times, events, error = _limpiar(times_f[valid], events_f[valid])
    if error:
        return {"error": error}
    niveles = list(dict.fromkeys(groups.tolist()))
    k = len(niveles)
    if k < 2:
        return {"error": "Hace falta mas de un grupo para comparar curvas."}
    G = np.column_stack([groups == nivel for nivel in niveles])

    O = np.zeros(k)
    E = np.zeros(k)
    V = np.zeros((k, k))
    for t in np.unique(times[events == 1]):
        riesgo = times >= t
        n_j = (G & riesgo[:, None]).sum(axis=0).astype(float)
        d_j = (G & ((times == t) & (events == 1))[:, None]).sum(axis=0).astype(float)
        n, d = n_j.sum(), d_j.sum()
        O += d_j
        E += d * n_j / n
        if n > 1:
            V += d * (n - d) / (n - 1) * (np.diag(n_j / n) - np.outer(n_j, n_j) / n ** 2)

    diff = (O - E)[:-1]
    try:
        chi2 = float(diff @ np.linalg.solve(V[:-1, :-1], diff))
    except np.linalg.LinAlgError:
        chi2 = float(diff @ np.linalg.pinv(V[:-1, :-1]) @ diff)
    gl = k - 1
    resultado = {"chi2": chi2, "gl": gl, "p": float(stats.chi2.sf(chi2, gl)),
                 "niveles": niveles, "observados": O, "esperados": E, "varianza": V}
    if k == 2 and np.all(E > 0) and np.all(O > 0):
        hr = (O[1] / E[1]) / (O[0] / E[0])
        se = np.sqrt(1 / E[0] + 1 / E[1])
        resultado["hr"] = float(hr)
        resultado["hr_ic95"] = (float(np.exp(np.log(hr) - 1.96 * se)),
                                float(np.exp(np.log(hr) + 1.96 * se)))
    return resultado


def log_rank_test(times1, events1, times2, events2):
    """Prueba log-rank para comparar dos curvas (atajo de `log_rank_k`).

    Todos los tiempos cuentan, el 0 incluido. Antes se descartaba t=0, pero los
    sujetos con ese tiempo seguian contados en el conjunto de riesgo de ahi en
    adelante: con eventos en t=0 el chi2 daba 0,001 donde lifelines da 1,705
    (auditoria 2026-09, A6).
    """
    times1, times2 = np.asarray(times1, dtype=float), np.asarray(times2, dtype=float)
    grupos = np.concatenate([np.zeros(len(times1), dtype=int), np.ones(len(times2), dtype=int)])
    r = log_rank_k(np.concatenate([times1, times2]),
                   np.concatenate([np.asarray(events1, dtype=float),
                                   np.asarray(events2, dtype=float)]), grupos)
    if "error" in r:
        return r
    return {"chi2": r["chi2"], "p": r["p"], "observed": r["observados"][0],
            "expected": r["esperados"][0], "variance": r["varianza"][0, 0]}
