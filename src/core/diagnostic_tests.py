"""Pruebas diagnosticas — OR, RR, verosimilitud, datos resumidos."""
import numpy as np
from scipy import stats


def odds_ratio(a, b, c, d):
    """Odds Ratio con IC 95% (tabla 2x2)."""
    if min(a, b, c, d) == 0:
        table = np.array([[a, b], [c, d]]) + 0.5
        a2, b2, c2, d2 = table[0, 0], table[0, 1], table[1, 0], table[1, 1]
    else:
        a2, b2, c2, d2 = a, b, c, d
    or_val = (a2 * d2) / (b2 * c2)
    ln_or = np.log(or_val)
    se_ln = np.sqrt(1/a2 + 1/b2 + 1/c2 + 1/d2)
    ci_lower = np.exp(ln_or - 1.96 * se_ln)
    ci_upper = np.exp(ln_or + 1.96 * se_ln)
    z = ln_or / se_ln if se_ln > 0 else 0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    return {"or": or_val, "ci_lower": ci_lower, "ci_upper": ci_upper,
            "ln_or": ln_or, "se_ln": se_ln, "z": z, "p": p,
            "a": a, "b": b, "c": c, "d": d}


def relative_risk(a, b, c, d):
    """Riesgo Relativo con IC 95% (tabla 2x2).

    RR = (a/(a+b)) / (c/(c+d)). Solo necesita que las dos filas tengan sujetos
    y que el grupo de referencia haya tenido algun evento. Que b o d valgan
    cero no impide nada: b=0 significa que TODOS los expuestos tuvieron el
    evento, y el RR sigue perfectamente definido.
    """
    n1, n0 = a + b, c + d
    if n1 == 0 or n0 == 0:
        return {"error": "Alguno de los dos grupos no tiene sujetos: el riesgo "
                         "relativo es un cociente de riesgos y no esta definido."}
    if c == 0:
        return {"error": "El grupo de referencia no tuvo ningun evento: el "
                         "riesgo relativo dividiria por cero. Informa los "
                         "riesgos por separado o usa la diferencia de riesgos."}

    # Correccion de Haldane-Anscombe si hay ceros: sin ella el log y su error
    # estandar quedan indefinidos y el IC sale de ancho cero, que se lee como
    # precision absoluta cuando es exactamente lo contrario.
    corregido = a == 0
    a2, b2, c2, d2 = (a + 0.5, b + 0.5, c + 0.5, d + 0.5) if corregido else (a, b, c, d)
    n1c, n0c = a2 + b2, c2 + d2

    risk1, risk0 = a / n1, c / n0
    rr = (a2 / n1c) / (c2 / n0c)
    ln_rr = np.log(rr)
    se_ln = np.sqrt(1 / a2 - 1 / n1c + 1 / c2 - 1 / n0c)
    ci_lower = np.exp(ln_rr - 1.96 * se_ln)
    ci_upper = np.exp(ln_rr + 1.96 * se_ln)
    z = ln_rr / se_ln if se_ln > 0 else 0
    p = 2 * (1 - stats.norm.cdf(abs(z)))

    arr = risk0 - risk1
    # NNT y NNH son el mismo numero con signo distinto: 1/|ARR|. Devolver inf
    # cuando la exposicion AUMENTA el riesgo diria "no hay efecto" justo donde
    # el efecto es dañino.
    nnt = np.inf if arr == 0 else 1 / abs(arr)
    return {"rr": rr, "ci_lower": ci_lower, "ci_upper": ci_upper,
            "z": z, "p": p, "risk1": risk1, "risk0": risk0,
            "arr": arr, "nnt": nnt, "nnt_tipo": ("NNT" if arr > 0 else
                                                 "NNH" if arr < 0 else "sin efecto"),
            "haldane": corregido, "a": a, "b": b, "c": c, "d": d}


def likelihood_ratios(a, b, c, d):
    """Razones de verosimilitud positiva y negativa."""
    sens = a / (a + c) if (a + c) > 0 else 0
    spec = d / (b + d) if (b + d) > 0 else 0
    plr = sens / (1 - spec) if (1 - spec) > 0 else np.inf
    nlr = (1 - sens) / spec if spec > 0 else np.inf
    ln_plr = np.log(plr) if plr > 0 and plr < np.inf else 0
    se_plr = np.sqrt(1/a + 1/c - 1/(a+c) + 1/b + 1/d - 1/(b+d)) if min(a, b, c, d) > 0 else 0
    ln_nlr = np.log(nlr) if nlr > 0 and nlr < np.inf else 0
    se_nlr = se_plr
    return {"plr": plr, "nlr": nlr, "sens": sens, "spec": spec,
            "ci_plr": (np.exp(ln_plr - 1.96*se_plr), np.exp(ln_plr + 1.96*se_plr)) if se_plr > 0 else None,
            "ci_nlr": (np.exp(ln_nlr - 1.96*se_nlr), np.exp(ln_nlr + 1.96*se_nlr)) if se_nlr > 0 else None}


def compare_two_means(m1, sd1, n1, m2, sd2, n2):
    """Comparar 2 medias con datos resumidos (Welch)."""
    if n1 < 2 or n2 < 2:
        return {"error": "Cada grupo necesita al menos 2 observaciones: los "
                         "grados de libertad de Welch dividen por (n-1)."}
    if sd1 < 0 or sd2 < 0:
        return {"error": "Las desviaciones estandar no pueden ser negativas."}
    if sd1 == 0 and sd2 == 0:
        return {"error": "Los dos grupos tienen desviacion estandar cero: no "
                         "hay variabilidad contra la cual comparar las medias."}
    se_diff = np.sqrt(sd1**2/n1 + sd2**2/n2)
    diff = m1 - m2
    t = diff / se_diff if se_diff > 0 else 0
    df_num = (sd1**2/n1 + sd2**2/n2)**2
    df_den = (sd1**2/n1)**2/(n1-1) + (sd2**2/n2)**2/(n2-1)
    df = df_num / df_den if df_den > 0 else n1 + n2 - 2
    p = 2 * (1 - stats.t.cdf(abs(t), df))
    tcrit = stats.t.ppf(0.975, df)
    return {"diff": diff, "t": t, "df": df, "p": p,
            "se_diff": se_diff, "ci95": (diff - tcrit*se_diff, diff + tcrit*se_diff)}


def compare_two_proportions(p1, n1, p2, n2):
    """Comparar 2 proporciones con datos resumidos.

    p1 y p2 son PROPORCIONES entre 0 y 1, no conteos. Pasarle conteos dejaba
    p_pool por encima de 1, y entonces p_pool*(1-p_pool) sale negativo y la
    raiz devuelve NaN. Ese NaN llegaba a la pantalla como si fuera un
    resultado.
    """
    if n1 < 1 or n2 < 1:
        return {"error": "Los tamanos de grupo tienen que ser al menos 1."}
    if not (0 <= p1 <= 1 and 0 <= p2 <= 1):
        return {"error": f"p1={p1} y p2={p2} tienen que ser proporciones entre "
                         f"0 y 1, no conteos. Si tenes conteos, divididos por "
                         f"su n."}
    x1, x2 = int(round(p1 * n1)), int(round(p2 * n2))
    p_pool = (x1 + x2) / (n1 + n2)
    se = np.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
    z = (p1 - p2) / se if se > 0 else 0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    rr = p1 / p2 if p2 > 0 else np.inf
    or_val = (p1/(1-p1)) / (p2/(1-p2)) if p2 < 1 and p1 < 1 else np.inf
    return {"diff": p1-p2, "z": z, "p": p, "rr": rr, "or": or_val,
            "se_diff": se, "ci95": (p1-p2 - 1.96*se, p1-p2 + 1.96*se)}


def wilson_ci(exitos, total, conf=0.95):
    """IC de una proporcion por el metodo de puntaje de Wilson (1927).

    Es el que pide CLSI EP12 para sensibilidad y especificidad. El de Wald
    (p +- z*sqrt(p(1-p)/n)) colapsa a ancho cero cuando la proporcion es 0 o 1:
    con 20 de 20 aciertos informaria "sensibilidad 100% (IC 100%-100%)", que
    afirma certeza absoluta a partir de 20 casos. Wilson da (83.9%, 100%).
    """
    if total <= 0:
        return (np.nan, np.nan)
    z = stats.norm.ppf(1 - (1 - conf) / 2)
    p = exitos / total
    denom = 1 + z**2 / total
    centro = (p + z**2 / (2 * total)) / denom
    medio = (z / denom) * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2))
    return (max(0.0, centro - medio), min(1.0, centro + medio))


def diagnostic_test(a, b, c, d):
    """Prueba diagnostica completa (tabla 2x2), con IC de Wilson (CLSI EP12).

    a = verdaderos positivos, b = falsos positivos,
    c = falsos negativos, d = verdaderos negativos.
    """
    n_enfermos, n_sanos = a + c, b + d
    n_pos, n_neg = a + b, c + d
    total = a + b + c + d

    avisos = []
    if n_enfermos == 0:
        avisos.append("No hay sujetos enfermos: la sensibilidad y el VPN no "
                      "estan definidos.")
    if n_sanos == 0:
        avisos.append("No hay sujetos sanos: la especificidad y el VPP no "
                      "estan definidos.")

    def _prop(num, den):
        return (num / den, wilson_ci(num, den)) if den > 0 else (np.nan, (np.nan, np.nan))

    sens, ic_sens = _prop(a, n_enfermos)
    spec, ic_spec = _prop(d, n_sanos)
    ppv, ic_ppv = _prop(a, n_pos)
    npv, ic_npv = _prop(d, n_neg)
    acc, ic_acc = _prop(a + d, total)
    prev, ic_prev = _prop(n_enfermos, total)

    plr = sens / (1 - spec) if np.isfinite(spec) and (1 - spec) > 0 else np.inf
    nlr = (1 - sens) / spec if np.isfinite(spec) and spec > 0 else np.inf
    if not np.isfinite(plr):
        avisos.append("Especificidad del 100%: la razon de verosimilitud "
                      "positiva es infinita. Con n finito eso es un limite del "
                      "muestreo, no una propiedad de la prueba: mira el IC de "
                      "la especificidad.")
    return {"avisos": avisos,
            "sens": sens, "spec": spec, "ppv": ppv, "npv": npv,
            "acc": acc, "prev": prev, "plr": plr, "nlr": nlr,
            "ci_sens": ic_sens, "ci_spec": ic_spec, "ci_ppv": ic_ppv,
            "ci_npv": ic_npv, "ci_acc": ic_acc, "ci_prev": ic_prev,
            "n": total, "a": a, "b": b, "c": c, "d": d}


def compare_two_auc(auc1, se1, n1, auc2, se2, n2):
    """Comparar 2 AUC ROC INDEPENDIENTES (grupos de pacientes distintos).

    z = (A1 - A2) / sqrt(se1^2 + se2^2) supone que las dos AUC son
    independientes. Si las dos pruebas se midieron sobre LOS MISMOS pacientes
    —que es el caso clinico habitual: comparar el metodo nuevo contra el viejo
    en la misma serie— las AUC estan correlacionadas y esta formula ignora el
    termino -2*r*se1*se2 del denominador. Al ignorarlo, el denominador queda
    mas grande de lo que corresponde, el z mas chico y el p mas grande: se
    pierde potencia para detectar una diferencia real.

    Hanley & McNeil (1983) dan la version pareada, que necesita la correlacion
    r entre las dos AUC. Esta firma no la recibe, asi que no puede calcularla.
    """
    var = se1**2 + se2**2
    if var <= 0:
        return {"error": "Los dos errores estandar son cero: no hay incertidumbre "
                         "que comparar."}
    se = np.sqrt(var)
    z = (auc1 - auc2) / se
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    return {"diff": auc1 - auc2, "z": z, "p": p, "se_diff": se,
            "ci95": (auc1 - auc2 - 1.96 * se, auc1 - auc2 + 1.96 * se),
            "avisos": ["Supone que las dos curvas vienen de pacientes DISTINTOS. "
                       "Si las dos pruebas se midieron sobre los mismos "
                       "pacientes, las AUC estan correlacionadas y este p es "
                       "conservador: hace falta la prueba pareada de Hanley & "
                       "McNeil (1983) o el test de DeLong."]}
