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
    """Riesgo Relativo con IC 95% (tabla 2x2)."""
    n1, n0 = a + b, c + d
    if n1 == 0 or n0 == 0 or b == 0 or d == 0:
        return None
    rr = (a / n1) / (c / n0)
    ln_rr = np.log(rr)
    se_ln = np.sqrt(1/a - 1/n1 + 1/c - 1/n0) if a > 0 and c > 0 else 0
    ci_lower = np.exp(ln_rr - 1.96 * se_ln)
    ci_upper = np.exp(ln_rr + 1.96 * se_ln)
    z = ln_rr / se_ln if se_ln > 0 else 0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    risk1 = a / n1
    risk0 = c / n0
    arr = risk0 - risk1
    nnt = 1 / arr if arr > 0 else np.inf
    return {"rr": rr, "ci_lower": ci_lower, "ci_upper": ci_upper,
            "z": z, "p": p, "risk1": risk1, "risk0": risk0,
            "arr": arr, "nnt": nnt, "a": a, "b": b, "c": c, "d": d}


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
    """Comparar 2 medias con datos resumidos."""
    se_diff = np.sqrt(sd1**2/n1 + sd2**2/n2)
    diff = m1 - m2
    t = diff / se_diff if se_diff > 0 else 0
    df_num = (sd1**2/n1 + sd2**2/n2)**2
    df_den = (sd1**2/n1)**2/(n1-1) + (sd2**2/n2)**2/(n2-1)
    df = df_num / df_den if df_den > 0 else n1 + n2 - 2
    p = 2 * (1 - stats.t.cdf(abs(t), df))
    return {"diff": diff, "t": t, "df": df, "p": p,
            "se_diff": se_diff, "ci95": (diff - 1.96*se_diff, diff + 1.96*se_diff)}


def compare_two_proportions(p1, n1, p2, n2):
    """Comparar 2 proporciones con datos resumidos."""
    x1, x2 = int(p1 * n1), int(p2 * n2)
    p_pool = (x1 + x2) / (n1 + n2)
    se = np.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
    z = (p1 - p2) / se if se > 0 else 0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    rr = p1 / p2 if p2 > 0 else np.inf
    or_val = (p1/(1-p1)) / (p2/(1-p2)) if p2 < 1 and p1 < 1 else np.inf
    return {"diff": p1-p2, "z": z, "p": p, "rr": rr, "or": or_val,
            "se_diff": se, "ci95": (p1-p2 - 1.96*se, p1-p2 + 1.96*se)}


def diagnostic_test(a, b, c, d):
    """Prueba diagnostica completa (tabla 2x2)."""
    sens = a / (a + c) if (a + c) > 0 else 0
    spec = d / (b + d) if (b + d) > 0 else 0
    ppv = a / (a + b) if (a + b) > 0 else 0
    npv = d / (c + d) if (c + d) > 0 else 0
    acc = (a + d) / (a + b + c + d) if (a + b + c + d) > 0 else 0
    prev = (a + c) / (a + b + c + d) if (a + b + c + d) > 0 else 0
    plr = sens / (1 - spec) if (1 - spec) > 0 else np.inf
    nlr = (1 - sens) / spec if spec > 0 else np.inf
    return {"sens": sens, "spec": spec, "ppv": ppv, "npv": npv,
            "acc": acc, "prev": prev, "plr": plr, "nlr": nlr,
            "a": a, "b": b, "c": c, "d": d}


def compare_two_auc(auc1, se1, n1, auc2, se2, n2):
    """Comparar 2 AUC ROC independientes."""
    z = (auc1 - auc2) / np.sqrt(se1**2 + se2**2) if (se1**2 + se2**2) > 0 else 0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    return {"diff": auc1-auc2, "z": z, "p": p,
            "ci95": (auc1-auc2 - 1.96*np.sqrt(se1**2+se2**2), auc1-auc2 + 1.96*np.sqrt(se1**2+se2**2))}
