"""Intervalos de referencia."""
import numpy as np
from scipy import stats


def reference_interval(data, percentiles=(2.5, 97.5)):
    """Calcula intervalos de referencia basados en percentiles."""
    data = np.asarray(data, dtype=float)
    data = data[~np.isnan(data)]
    n = len(data)
    if n < 10:
        return None

    lower_p, upper_p = percentiles
    lower = np.percentile(data, lower_p)
    upper = np.percentile(data, upper_p)

    ci_lower = stats.percentileofscore(data, lower)
    ci_upper = stats.percentileofscore(data, upper)

    # Bootstrap CI for percentiles
    rng = np.random.RandomState(42)
    boot_lower = np.array([np.percentile(rng.choice(data, n, replace=True), lower_p) for _ in range(10000)])
    boot_upper = np.array([np.percentile(rng.choice(data, n, replace=True), upper_p) for _ in range(10000)])

    return {
        "lower": lower, "upper": upper, "lower_p": lower_p, "upper_p": upper_p,
        "ci_lower_low": np.percentile(boot_lower, 2.5),
        "ci_lower_high": np.percentile(boot_lower, 97.5),
        "ci_upper_low": np.percentile(boot_upper, 2.5),
        "ci_upper_high": np.percentile(boot_upper, 97.5),
        "n": n, "percentiles": percentiles,
    }


def percentile_table(data, percentiles=None):
    """Tabla de percentiles con IC."""
    data = np.asarray(data, dtype=float)
    data = data[~np.isnan(data)]
    n = len(data)
    if n < 5:
        return None

    if percentiles is None:
        percentiles = [5, 10, 25, 50, 75, 90, 95]

    result = []
    for p in percentiles:
        if p / 100 >= 1/n and p / 100 <= (n-1)/n:
            val = np.percentile(data, p)
            # Simple bootstrap CI
            rng = np.random.RandomState(42)
            boot = np.array([np.percentile(rng.choice(data, n, replace=True), p) for _ in range(2000)])
            ci_low = np.percentile(boot, 2.5)
            ci_high = np.percentile(boot, 97.5)
            result.append({"percentile": p, "value": val, "ci_low": ci_low, "ci_high": ci_high})
        else:
            result.append({"percentile": p, "value": np.nan, "ci_low": np.nan, "ci_high": np.nan, "note": "n insuficiente"})

    return {"percentiles": result, "n": n}


def age_related_reference(ages, values, age_min=None, age_max=None):
    """Intervalo de referencia relacionado con la edad (percentiles por grupo)."""
    ages = np.asarray(ages, dtype=float)
    values = np.asarray(values, dtype=float)
    valid = ~(np.isnan(ages) | np.isnan(values))
    ages, values = ages[valid], values[valid]

    if age_min is None:
        age_min = np.min(ages)
    if age_max is None:
        age_max = np.max(ages)

    age_groups = np.arange(age_min, age_max + 1, max(1, int((age_max - age_min) / 10)))

    result = []
    for i in range(len(age_groups) - 1):
        mask = (ages >= age_groups[i]) & (ages < age_groups[i+1])
        group_vals = values[mask]
        if len(group_vals) >= 5:
            result.append({
                "age_group": f"{age_groups[i]}-{age_groups[i+1]}",
                "n": len(group_vals),
                "p5": np.percentile(group_vals, 5),
                "p25": np.percentile(group_vals, 25),
                "median": np.percentile(group_vals, 50),
                "p75": np.percentile(group_vals, 75),
                "p95": np.percentile(group_vals, 95),
                "mean": np.mean(group_vals),
            })

    return {"groups": result, "n_total": len(values)}
