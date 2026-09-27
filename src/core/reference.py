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


def dixon_reed(data):
    """Regla de Dixon en la forma de Reed et al. (1971), la que cita EP28-A3c.

    Un extremo es sospechoso si la distancia al dato vecino (D) supera un
    tercio del rango (R). Se mira el mas bajo y el mas alto. Con dos atipicos
    del mismo lado el segundo tapa al primero: la regla no lo ve.
    """
    x = np.sort(np.asarray(data, dtype=float)[np.isfinite(data)])
    if len(x) < 3 or x[-1] == x[0]:
        return {"bajo": None, "alto": None}
    R = x[-1] - x[0]
    bajo, alto = (x[1] - x[0]) / R, (x[-1] - x[-2]) / R
    return {"bajo": {"valor": float(x[0]), "d_r": float(bajo), "sospechoso": bool(bajo > 1 / 3)},
            "alto": {"valor": float(x[-1]), "d_r": float(alto), "sospechoso": bool(alto > 1 / 3)}}


def verificar_intervalo(data, inferior=None, superior=None):
    """Verificacion de un intervalo publicado (EP28-A3c, transferencia).

    La norma mide 20 sujetos sanos: si 2 o menos caen fuera del intervalo, se
    adopta; con 3 o mas se miden otros 20, y si vuelve a pasar, se revisa. Con
    otro n se aplica la misma proporcion: hasta el 10 % afuera. `p` es la
    probabilidad de ver tantos afuera o mas si el intervalo fuera el correcto
    (5 % afuera con los dos limites, 2,5 % con uno solo).
    """
    x = np.asarray(data, dtype=float)
    x = x[np.isfinite(x)]
    if inferior is None and superior is None:
        return {"error": "No se declaro ningun limite para verificar."}
    if inferior is not None and superior is not None and inferior >= superior:
        return {"error": "El limite inferior tiene que ser menor que el superior."}
    debajo = int(np.sum(x < inferior)) if inferior is not None else 0
    encima = int(np.sum(x > superior)) if superior is not None else 0
    n, fuera = len(x), debajo + encima
    permitidos = int(np.floor(0.10 * n + 1e-9))
    esperado = 0.05 if (inferior is not None and superior is not None) else 0.025
    return {"n": n, "debajo": debajo, "encima": encima, "fuera": fuera,
            "permitidos": permitidos, "verificado": fuera <= permitidos,
            "p": float(stats.binom.sf(fuera - 1, n, esperado)) if fuera else 1.0,
            "n_norma": 20}


def _polinomio(x, y, grado):
    """(coeficientes, residuos, p del termino de mayor grado) por minimos cuadrados."""
    X = np.vander(x, grado + 1, increasing=True)
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ coef
    gl = len(y) - (grado + 1)
    s2 = res @ res / gl
    cov = s2 * np.linalg.inv(X.T @ X)
    t = coef[-1] / np.sqrt(cov[-1, -1])
    return coef, res, float(2 * stats.t.sf(abs(t), gl))


def centiles_por_edad(ages, values, z=1.959963984540054, escala="lineal", grado_max=3):
    """Centiles de referencia por edad con residuos absolutos (Altman 1993).

    1. La media es un polinomio de la edad: se ajusta el de grado `grado_max` y
       se baja de grado mientras el termino mas alto no aporte (p >= 0,05).
    2. La DE sale de los residuos absolutos: si |e| tiene pendiente con la edad
       (p < 0,05), DE(edad) = sqrt(pi/2)·(a + b·edad); si no, sqrt(pi/2)·media|e|.
       Para una normal E|e| = DE·sqrt(2/pi).
    3. Centiles = media(edad) ± z·DE(edad); en escala log se vuelve con exp.

    Los z = e/DE(edad) tienen que ser normales estandar: si no, los centiles
    extremos no cubren lo que dicen (se prueba y se cuenta cuantos quedan
    fuera). La edad se centra para que el polinomio no quede mal condicionado.
    """
    ages = np.asarray(ages, dtype=float)
    values = np.asarray(values, dtype=float)
    valid = np.isfinite(ages) & np.isfinite(values)
    ages, values = ages[valid], values[valid]
    n = len(values)
    if n < 20:
        return {"error": f"Hacen falta al menos 20 sujetos; hay {n}."}
    if np.ptp(ages) == 0:
        return {"error": "Todos los sujetos tienen la misma edad."}
    if escala == "log":
        if np.any(values <= 0):
            return {"error": "En escala log los valores tienen que ser positivos."}
        y = np.log(values)
    else:
        y = values
    centro = ages.mean()
    x = ages - centro

    grado, p_grado = grado_max, None
    while True:
        coef, res, p = _polinomio(x, y, grado)
        if p < 0.05 or grado == 1:
            p_grado = p
            break
        grado -= 1

    abs_res = np.abs(res)
    coef_sd, _, p_sd = _polinomio(x, abs_res, 1)
    factor = np.sqrt(np.pi / 2)
    sd_lineal = p_sd < 0.05
    if sd_lineal:
        extremos = factor * (coef_sd[0] + coef_sd[1] * np.array([x.min(), x.max()]))
        if np.any(extremos <= 0):
            sd_lineal = False      # la recta cruzaria cero dentro del rango de edades

    def media(edad):
        return np.polyval(coef[::-1], np.asarray(edad, dtype=float) - centro)

    def de(edad):
        e = np.asarray(edad, dtype=float) - centro
        if sd_lineal:
            return factor * (coef_sd[0] + coef_sd[1] * e)
        return np.full_like(e, factor * abs_res.mean(), dtype=float)

    def volver(v):
        return np.exp(v) if escala == "log" else v

    def centiles(edad):
        m, s = media(edad), de(edad)
        return volver(m - z * s), volver(m), volver(m + z * s)

    zs = res / de(ages)
    shapiro_p = float(stats.shapiro(zs).pvalue) if n <= 5000 else float("nan")
    return {
        "n": n, "grado": grado, "p_grado": p_grado, "coeficientes": coef, "centro": centro,
        "sd_lineal": sd_lineal, "p_sd": p_sd, "coef_sd": coef_sd,
        "z": zs, "shapiro_p": shapiro_p, "fuera": float(np.mean(np.abs(zs) > z)),
        "z_critico": z, "escala": escala, "centiles": centiles,
        "edad_min": float(ages.min()), "edad_max": float(ages.max()),
    }


def age_related_reference(ages, values, age_min=None, age_max=None):
    """Intervalo de referencia por grupos de edad de ancho fijo.

    En cada grupo, los percentiles 2,5, 50 y 97,5 con el rango de EP28
    (p(n+1), interpolado: el mismo que `reference_interval`). Antes eran los
    percentiles 5 y 95 lineales: un intervalo del 90 % con otra regla de
    rangos que el intervalo de referencia de la misma app. El percentil 2,5
    solo existe desde n = 39 en el grupo (rango 0,025·40 = 1).
    """
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
        m = len(group_vals)
        grupo = {"age_group": f"[{bordes[i]:g}, {bordes[i+1]:g})", "desde": float(bordes[i]),
                 "hasta": float(bordes[i + 1]), "n": m, "mean": np.mean(group_vals)}
        # Se informa aunque no alcance: sacarlo en silencio hacia desaparecer sujetos.
        for clave, p in (("p2_5", 2.5), ("median", 50), ("p97_5", 97.5)):
            grupo[clave] = (np.percentile(group_vals, p, method="weibull")
                            if 1 <= p / 100 * (m + 1) <= m else np.nan)
        if not np.isfinite(grupo["p2_5"]):
            grupo["nota"] = "menos de 39 sujetos: sin percentiles 2,5 y 97,5"
        result.append(grupo)

    return {"groups": result, "n_total": len(values)}
