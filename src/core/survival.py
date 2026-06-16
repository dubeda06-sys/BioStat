"""Analisis de supervivencia - Kaplan-Meier y Cox."""
import numpy as np
from scipy import stats


def kaplan_meier(times, events):
    """Estimacion de Kaplan-Meier."""
    times = np.asarray(times, dtype=float)
    events = np.asarray(events, dtype=int)

    valid = ~(np.isnan(times)) & ~np.isnan(events)
    times, events = times[valid], events[valid]

    order = np.argsort(times)
    times, events = times[order], events[order]

    unique_times = np.unique(times)
    n = len(times)

    surv = 1.0
    km_times = [0]
    km_surv = [1.0]
    at_risk_list = [n]
    events_list = [0]

    for t in unique_times:
        at_r = np.sum(times >= t)
        ev = np.sum((times == t) & (events == 1))

        if at_r > 0:
            surv *= (1 - ev / at_r)

        km_times.append(t)
        km_surv.append(surv)
        at_risk_list.append(at_r)
        events_list.append(ev)

    variance = 0
    km_se = [0] * len(km_times)
    for i in range(1, len(km_times)):
        ev = events_list[i]
        ar = at_risk_list[i]
        if ar > 0 and ar - ev > 0:
            variance += ev / (ar * (ar - ev))
        km_se[i] = km_surv[i] * np.sqrt(variance)

    km_surv_arr = np.array(km_surv)
    km_se_arr = np.array(km_se)
    ci_lower = np.clip(km_surv_arr - 1.96 * km_se_arr, 0, 1)
    ci_upper = np.clip(km_surv_arr + 1.96 * km_se_arr, 0, 1)

    median_survival = None
    for i, s in enumerate(km_surv):
        if s <= 0.5:
            median_survival = km_times[i]
            break

    return {
        "times": np.array(km_times),
        "survival": km_surv_arr,
        "se": km_se_arr,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "n_total": n,
        "n_events": int(np.sum(events)),
        "n_censored": int(n - np.sum(events)),
        "median_survival": median_survival,
    }


def log_rank_test(times1, events1, times2, events2):
    """Prueba log-rank para comparar dos curvas."""
    times1 = np.asarray(times1, dtype=float)
    events1 = np.asarray(events1, dtype=int)
    times2 = np.asarray(times2, dtype=float)
    events2 = np.asarray(events2, dtype=int)

    valid1 = ~np.isnan(times1)
    times1, events1 = times1[valid1], events1[valid1]
    valid2 = ~np.isnan(times2)
    times2, events2 = times2[valid2], events2[valid2]

    all_times = np.unique(np.concatenate([times1, times2]))
    all_times = all_times[all_times > 0]

    n1 = len(times1)
    n2 = len(times2)
    O1 = E1 = V = 0

    for t in all_times:
        d1 = np.sum((times1 == t) & (events1 == 1))
        d2 = np.sum((times2 == t) & (events2 == 1))
        d = d1 + d2
        n_at_risk = n1 + n2

        if n_at_risk > 0:
            e1 = n1 * d / n_at_risk
            O1 += d1
            E1 += e1
            if n_at_risk > 1:
                V += d * n1 * n2 * (n_at_risk - d) / (n_at_risk**2 * (n_at_risk - 1))

        n1 -= np.sum(times1 == t)
        n2 -= np.sum(times2 == t)

    chi2 = (O1 - E1)**2 / V if V > 0 else 0
    p = 1 - stats.chi2.cdf(chi2, df=1)

    return {"chi2": chi2, "p": p, "observed": O1, "expected": E1, "variance": V}
