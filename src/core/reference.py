"""Intervalos de referencia."""
import numpy as np
from scipy import stats


# CLSI EP28-A3c: el metodo no parametrico necesita al menos 120 sujetos de
# referencia para poder estimar los percentiles 2,5 y 97,5 con un intervalo de
# confianza util. Con 120 los limites caen justo en los estadisticos de orden
# 3 y 118. Por debajo, el limite queda determinado por dos o tres datos.
N_MINIMO_EP28 = 120
# Por debajo de esto ni siquiera hay un dato en cada cola.
N_MINIMO_ABSOLUTO = 40


def reference_interval(data, percentiles=(2.5, 97.5)):
    """Intervalo de referencia no parametrico por percentiles (CLSI EP28-A3c).

    Los IC de los limites salen por bootstrap percentil (10.000 remuestreos),
    no por los rangos de orden tabulados en la norma. Con n >= 120 los dos
    coinciden de cerca; por debajo el bootstrap es optimista, porque remuestrea
    de una cola que casi no tiene datos.
    """
    data = np.asarray(data, dtype=float)
    data = data[np.isfinite(data)]
    n = len(data)
    if n < 10:
        return None

    lower_p, upper_p = percentiles
    lower = np.percentile(data, lower_p)
    upper = np.percentile(data, upper_p)

    avisos = []
    if n < N_MINIMO_ABSOLUTO:
        avisos.append(
            f"n={n}: muy por debajo de los {N_MINIMO_EP28} sujetos que pide "
            f"CLSI EP28-A3c para el metodo no parametrico. Con esta n cada "
            f"limite depende de uno o dos datos y el intervalo no es "
            f"defendible en una acreditacion. Sirve como exploracion, no como "
            f"intervalo de referencia propio.")
    elif n < N_MINIMO_EP28:
        avisos.append(
            f"n={n}: por debajo de los {N_MINIMO_EP28} sujetos que pide CLSI "
            f"EP28-A3c para establecer un intervalo de referencia no "
            f"parametrico. Para VERIFICAR un intervalo ya publicado alcanza "
            f"con 20 (EP28, seccion de transferencia); para establecer uno "
            f"propio, no.")

    # Cuantos datos sostienen realmente cada limite: es la cifra que explica
    # por que la norma pide 120.
    n_bajo_limite = int(np.sum(data <= lower))
    n_sobre_limite = int(np.sum(data >= upper))
    if min(n_bajo_limite, n_sobre_limite) < 3:
        avisos.append(
            f"El limite inferior se apoya en {n_bajo_limite} dato(s) y el "
            f"superior en {n_sobre_limite}. Un solo valor atipico los mueve "
            f"entero.")

    # Bootstrap CI for percentiles
    rng = np.random.RandomState(42)
    boot_lower = np.array([np.percentile(rng.choice(data, n, replace=True), lower_p) for _ in range(10000)])
    boot_upper = np.array([np.percentile(rng.choice(data, n, replace=True), upper_p) for _ in range(10000)])

    return {
        "avisos": avisos,
        "lower": lower, "upper": upper, "lower_p": lower_p, "upper_p": upper_p,
        "ci_lower_low": np.percentile(boot_lower, 2.5),
        "ci_lower_high": np.percentile(boot_lower, 97.5),
        "ci_upper_low": np.percentile(boot_upper, 2.5),
        "ci_upper_high": np.percentile(boot_upper, 97.5),
        "n": n, "percentiles": percentiles,
        "cumple_ep28": n >= N_MINIMO_EP28,
        "n_bajo_limite": n_bajo_limite, "n_sobre_limite": n_sobre_limite,
        "metodo_ic": "bootstrap percentil (10.000 remuestreos)",
    }


def percentile_table(data, percentiles=None):
    """Tabla de percentiles con IC."""
    data = np.asarray(data, dtype=float)
    data = data[np.isfinite(data)]
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
    valid = np.isfinite(ages) & np.isfinite(values)
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
