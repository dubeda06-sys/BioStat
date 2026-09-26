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


def _rangos_ic_ep28(n, fraccion=0.025, confianza=0.90):
    """Rangos (base 1) del IC no parametrico de un percentil, o None si no alcanza n.

    X = cuantos datos caen por debajo del percentil verdadero ~ Binomial(n, p).
    Se busca el mayor rango a con P(X <= a-1) <= (1-conf)/2 y el menor rango b
    con P(X >= b) <= (1-conf)/2: colas iguales. Con p = 0,025 y conf = 0,90
    reproduce EXACTA la tabla 8 de EP28-A3c (Solberg 1987) para los 882 tamanos
    de 119 a 1000 que tabula. Por debajo de 119 ni siquiera el dato mas chico
    deja una cola de 5 %: no hay IC al 90 %.
    """
    B = stats.binom(n, fraccion)
    cola = (1 - confianza) / 2
    if B.cdf(0) > cola:
        return None
    a = max(1, int(B.ppf(cola)))
    while a > 1 and B.cdf(a - 1) > cola:
        a -= 1
    while B.cdf(a) <= cola:
        a += 1
    b = int(B.ppf(1 - cola)) + 1
    while B.sf(b - 1) <= cola and b > a + 1:
        b -= 1
    while B.sf(b - 1) > cola:
        b += 1
    return a, b


def reference_interval(data, percentiles=(2.5, 97.5)):
    """Intervalo de referencia no parametrico, como lo define CLSI EP28-A3c.

    §9.4.1: el limite inferior es la observacion de rango r1 = 0,025(n+1) y el
    superior la de r2 = 0,975(n+1), interpolando entre rangos. Es el percentil
    "weibull" de numpy (tipo 6 de Hyndman y Fan). Antes se usaba el lineal (tipo
    7), que con n = 120 cae en los rangos 4 y 117 en vez de 3 y 118.

    §9.5.1: el IC de cada limite es un IC **90 %** por rangos de orden (tabla 8,
    de Solberg 1987), que exige n >= 119. Antes era un bootstrap al 95 %: otro
    nivel y otro metodo que el que se presenta en una acreditacion. Con n < 119
    no hay IC normativo y se dice.
    """
    data = np.asarray(data, dtype=float)
    data = data[np.isfinite(data)]
    n = len(data)
    if n < 10:
        return None

    lower_p, upper_p = percentiles
    lower = np.percentile(data, lower_p, method="weibull")
    upper = np.percentile(data, upper_p, method="weibull")

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

    # IC 90 % de cada limite por rangos de orden (EP28 §9.5.1, tabla 8). Los
    # rangos del limite superior son los del inferior reflejados: n+1-b, n+1-a.
    ordenados = np.sort(data)
    ic_inf = ic_sup = (np.nan, np.nan)
    rangos = _rangos_ic_ep28(n, lower_p / 100) if (lower_p, upper_p) == (2.5, 97.5) else None
    if rangos is not None:
        a, b = rangos
        ic_inf = (ordenados[a - 1], ordenados[b - 1])
        ic_sup = (ordenados[n - b], ordenados[n - a])
    else:
        avisos.append(
            f"Sin IC de los limites: EP28-A3c da el IC 90 % por rangos de orden a "
            f"partir de n=119, y la norma pide {N_MINIMO_EP28} sujetos. Con n={n} "
            f"no hay un IC que se pueda presentar como el de la norma.")

    return {
        "avisos": avisos,
        "lower": lower, "upper": upper, "lower_p": lower_p, "upper_p": upper_p,
        "ci_lower_low": ic_inf[0], "ci_lower_high": ic_inf[1],
        "ci_upper_low": ic_sup[0], "ci_upper_high": ic_sup[1],
        "rangos_ic": rangos, "nivel_ic": 0.90,
        "n": n, "percentiles": percentiles,
        "cumple_ep28": n >= N_MINIMO_EP28,
        "n_bajo_limite": n_bajo_limite, "n_sobre_limite": n_sobre_limite,
        "metodo_limites": "rangos 0,025(n+1) y 0,975(n+1), interpolados (EP28 §9.4.1)",
        "metodo_ic": "IC 90 % por rangos de orden (EP28 §9.5.1, tabla 8)",
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
        # Rango p(n+1)/100, el mismo que dice la formula en pantalla y que usa
        # EP28. Solo existe entre el primer y el ultimo dato.
        if 1 <= p / 100 * (n + 1) <= n:
            val = np.percentile(data, p, method="weibull")
            # Simple bootstrap CI
            rng = np.random.RandomState(42)
            boot = np.array([np.percentile(rng.choice(data, n, replace=True), p, method="weibull")
                             for _ in range(2000)])
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

    # Los bordes tienen que pasar al maximo: con arange(min, max + 1, ancho) el
    # ultimo borde podia quedar por debajo y las edades de arriba no caian en
    # ningun grupo (17 de 500 sujetos, auditoria 2026-09, A7).
    ancho = max(1, int((age_max - age_min) / 10))
    bordes = np.arange(age_min, age_max + ancho, ancho)
    if bordes[-1] <= age_max:
        bordes = np.append(bordes, bordes[-1] + ancho)

    result = []
    for i in range(len(bordes) - 1):
        mask = (ages >= bordes[i]) & (ages < bordes[i+1])
        group_vals = values[mask]
        if len(group_vals) == 0:
            continue
        grupo = {"age_group": f"[{bordes[i]:g}, {bordes[i+1]:g})", "n": len(group_vals),
                 "mean": np.mean(group_vals)}
        if len(group_vals) >= 5:
            grupo.update({
                "p5": np.percentile(group_vals, 5),
                "p25": np.percentile(group_vals, 25),
                "median": np.percentile(group_vals, 50),
                "p75": np.percentile(group_vals, 75),
                "p95": np.percentile(group_vals, 95),
            })
        else:
            # Se informa igual: sacarlo en silencio hacia desaparecer sujetos.
            grupo.update({k: np.nan for k in ("p5", "p25", "median", "p75", "p95")})
            grupo["nota"] = "menos de 5 sujetos: sin percentiles"
        result.append(grupo)

    return {"groups": result, "n_total": len(values)}
