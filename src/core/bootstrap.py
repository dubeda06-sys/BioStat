"""Bootstrap: remuestreo para el IC de un estadistico, sin suponer su distribucion.

El remuestreo es vectorizado por lotes (antes, un bucle de Python con 10.000
vueltas) y el IC es BCa por defecto (Efron 1987): corrige el sesgo y la
asimetria de la distribucion bootstrap, que el percentil simple ignora. El
percentil sigue como opcion. Verificado contra `scipy.stats.bootstrap`
(`tests/test_bootstrap_resultado.py`).
"""
import numpy as np
from scipy import stats

SEMILLA = 42
B_DEFECTO = 10000
_LOTE = 500


def _lotes(rng, tamanos, B):
    """Indices de remuestreo por lotes: una matriz (m, n_j) por muestra."""
    hechos = 0
    while hechos < B:
        m = min(_LOTE, B - hechos)
        yield [rng.integers(0, n, size=(m, n)) for n in tamanos]
        hechos += m


def _distribucion(estadistico, muestras, B, seed, pareado=False):
    """El estadistico en B remuestreos. `pareado`: las muestras se remuestrean
    con los mismos indices (pares x, y)."""
    rng = np.random.default_rng(seed)
    tamanos = [len(muestras[0])] if pareado else [len(m) for m in muestras]
    partes = []
    for idx in _lotes(rng, tamanos, B):
        if pareado:
            partes.append(estadistico(*(m[idx[0]] for m in muestras)))
        else:
            partes.append(estadistico(*(m[i] for m, i in zip(muestras, idx))))
    return np.concatenate(partes)


def _jackknife(estadistico, muestras, pareado=False):
    """Estadisticos dejando uno afuera, por muestra: lista de arreglos."""
    if pareado:
        n = len(muestras[0])
        filas = np.array([np.delete(np.arange(n), i) for i in range(n)])
        return [estadistico(*(m[filas] for m in muestras))]
    salida = []
    for j, m in enumerate(muestras):
        n = len(m)
        filas = np.array([np.delete(np.arange(n), i) for i in range(n)])
        otras = [np.broadcast_to(o, (n, len(o))) for o in muestras]
        otras[j] = m[filas]
        salida.append(estadistico(*otras))
    return salida


def _ic(dist, estimado, alpha, metodo, jack=None):
    """(inferior, superior, metodo usado). BCa como `scipy.stats.bootstrap`."""
    if metodo == "bca" and jack is not None:
        prop = (np.sum(dist < estimado) + np.sum(dist <= estimado)) / (2 * len(dist))
        num = den = 0.0
        for t in jack:
            t = t[np.isfinite(t)]
            n = len(t)
            if n < 2:
                continue
            U = (n - 1) * (t.mean() - t)
            num += np.sum(U ** 3) / n ** 3
            den += np.sum(U ** 2) / n ** 2
        if 0 < prop < 1 and den > 0:
            z0 = stats.norm.ppf(prop)
            a = num / (6 * den ** 1.5)
            z = stats.norm.ppf([alpha / 2, 1 - alpha / 2])
            q = stats.norm.cdf(z0 + (z0 + z) / (1 - a * (z0 + z)))
            lo, hi = np.percentile(dist, 100 * q)
            return float(lo), float(hi), "BCa"
    lo, hi = np.percentile(dist, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi), "percentil"


def _resumen(dist, estimado, alpha, metodo, jack, B):
    """Claves comunes: la distribucion sin los remuestreos invalidos."""
    invalidos = int(np.sum(~np.isfinite(dist)))
    validos = dist[np.isfinite(dist)]
    lo, hi, usado = _ic(validos, estimado, alpha, metodo, jack)
    return {"ci_lower": lo, "ci_upper": hi, "metodo_ic": usado,
            "bootstrap_se": float(np.std(validos)), "bias": float(np.mean(validos) - estimado),
            "ci_level": 1 - alpha, "n_bootstrap": B, "n_invalidos": invalidos,
            "bootstrap_distribution": validos}


def _limpia(data):
    data = np.asarray(data, dtype=float)
    return data[np.isfinite(data)]


def _media(x):
    return x.mean(axis=-1)


def _mediana(x):
    return np.median(x, axis=-1)


def bootstrap_mean(data, n_bootstrap=B_DEFECTO, ci=0.95, seed=SEMILLA, metodo="bca"):
    """IC bootstrap de la media."""
    data = _limpia(data)
    n = len(data)
    if n < 2:
        return None
    est = float(np.mean(data))
    dist = _distribucion(_media, [data], n_bootstrap, seed)
    r = _resumen(dist, est, 1 - ci, metodo, _jackknife(_media, [data]), n_bootstrap)
    r.update({"original_mean": est, "bootstrap_mean": float(np.mean(dist)), "n_original": n})
    return r


def bootstrap_median(data, n_bootstrap=B_DEFECTO, ci=0.95, seed=SEMILLA, metodo="bca"):
    """IC bootstrap de la mediana, con el IC exacto por rangos como control."""
    data = _limpia(data)
    n = len(data)
    if n < 2:
        return None
    est = float(np.median(data))
    dist = _distribucion(_mediana, [data], n_bootstrap, seed)
    r = _resumen(dist, est, 1 - ci, metodo, _jackknife(_mediana, [data]), n_bootstrap)
    r.update({"original_median": est, "bootstrap_median": float(np.mean(dist)),
              "n_original": n, "distintos": int(len(np.unique(data))),
              "exacto": ic_mediana_exacto(data, 1 - ci)})
    return r


def ic_mediana_exacto(data, alpha=0.05):
    """IC de la mediana por estadisticos de orden (binomial, sin remuestreo).

    Rangos r y n - r + 1, con r el mayor tal que P(X <= r - 1) <= alpha/2,
    X ~ Binomial(n, 1/2) (Campbell y Gardner 1988). Cubre al menos 1 - alpha.
    None si n no alcanza: con n <= 5 ni los extremos cubren el 95 %.
    """
    x = np.sort(_limpia(data))
    n = len(x)
    B = stats.binom(n, 0.5)
    r = int(B.ppf(alpha / 2))
    while r > 0 and B.cdf(r - 1) > alpha / 2:
        r -= 1
    while B.cdf(r) <= alpha / 2:
        r += 1
    if r < 1:
        return None
    cobertura = float(1 - 2 * B.cdf(r - 1))
    return {"inferior": float(x[r - 1]), "superior": float(x[n - r]), "rangos": (r, n - r + 1),
            "cobertura": cobertura}


def _pearson(x, y):
    """r de Pearson por fila; NaN si una fila es constante."""
    xc = x - x.mean(axis=-1, keepdims=True)
    yc = y - y.mean(axis=-1, keepdims=True)
    sxx, syy = np.sum(xc ** 2, axis=-1), np.sum(yc ** 2, axis=-1)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = np.sum(xc * yc, axis=-1) / np.sqrt(sxx * syy)
    return np.where((sxx > 0) & (syy > 0), r, np.nan)


def _spearman(x, y):
    return _pearson(stats.rankdata(x, axis=-1), stats.rankdata(y, axis=-1))


def bootstrap_correlation(x, y, n_bootstrap=B_DEFECTO, ci=0.95, method="pearson",
                          seed=SEMILLA, metodo="bca"):
    """IC bootstrap de r (pares remuestreados juntos).

    Un remuestreo con una columna constante no tiene correlacion: con n chico
    pasa seguido (n=5: ~16 de cada 10.000) y un solo NaN bastaba para que el
    percentil diera NaN (auditoria 2026-09, M5). Se descartan y se cuentan.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    valid = np.isfinite(x) & np.isfinite(y)
    x, y = x[valid], y[valid]
    n = len(x)
    if n < 3:
        return None
    f = _pearson if method == "pearson" else _spearman
    dist = _distribucion(f, [x, y], n_bootstrap, seed, pareado=True)
    invalidos = int(np.sum(~np.isfinite(dist)))
    if invalidos > 0.5 * n_bootstrap:
        return {"error": "Mas de la mitad de los remuestreos no tienen correlacion "
                         "definida (columnas casi constantes): el bootstrap no "
                         "sirve con estos datos."}
    orig_r, orig_p = (stats.pearsonr(x, y) if method == "pearson" else stats.spearmanr(x, y))
    r = _resumen(dist, float(orig_r), 1 - ci, metodo,
                 _jackknife(f, [x, y], pareado=True), n_bootstrap)
    avisos = []
    if invalidos:
        avisos.append(f"{invalidos} de {n_bootstrap} remuestreos salieron con una "
                      f"columna constante y no tienen correlacion: el IC se "
                      f"calculo con los {n_bootstrap - invalidos} restantes.")
    r.update({"avisos": avisos, "original_r": float(orig_r), "original_p": float(orig_p),
              "bootstrap_r": float(np.mean(r["bootstrap_distribution"])), "method": method,
              "n_original": n})
    return r


def _dif_medias(a, b):
    return a.mean(axis=-1) - b.mean(axis=-1)


def bootstrap_difference(data1, data2, n_bootstrap=B_DEFECTO, ci=0.95, seed=SEMILLA,
                         metodo="bca"):
    """IC bootstrap de la diferencia de medias de dos grupos independientes:
    cada grupo se remuestrea por separado."""
    data1, data2 = _limpia(data1), _limpia(data2)
    n1, n2 = len(data1), len(data2)
    if n1 < 2 or n2 < 2:
        return None
    est = float(np.mean(data1) - np.mean(data2))
    dist = _distribucion(_dif_medias, [data1, data2], n_bootstrap, seed)
    r = _resumen(dist, est, 1 - ci, metodo, _jackknife(_dif_medias, [data1, data2]),
                 n_bootstrap)
    r.update({"original_diff": est, "bootstrap_diff": float(np.mean(dist)), "n1": n1, "n2": n2})
    return r


def _pendiente(x, y):
    xc = x - x.mean(axis=-1, keepdims=True)
    sxx = np.sum(xc ** 2, axis=-1)
    with np.errstate(invalid="ignore", divide="ignore"):
        b = np.sum(xc * y, axis=-1) / sxx
    return np.where(sxx > 0, b, np.nan)


def _intercepto(x, y):
    return y.mean(axis=-1) - _pendiente(x, y) * x.mean(axis=-1)


def bootstrap_regression(x, y, n_bootstrap=B_DEFECTO, ci=0.95, seed=SEMILLA, metodo="bca"):
    """IC bootstrap de la pendiente y el intercepto de la recta de minimos
    cuadrados, remuestreando pares. Un remuestreo con X constante no define
    recta: se descarta y se cuenta (antes polyfit daba una solucion de norma
    minima que entraba al percentil como si fuera dato)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    valid = np.isfinite(x) & np.isfinite(y)
    x, y = x[valid], y[valid]
    n = len(x)
    if n < 3:
        return None
    if np.ptp(x) == 0:
        return {"error": "X es constante: no hay recta que estimar."}
    alpha = 1 - ci
    b, a = float(_pendiente(x, y)), float(_intercepto(x, y))
    pend = _distribucion(_pendiente, [x, y], n_bootstrap, seed, pareado=True)
    inter = _distribucion(_intercepto, [x, y], n_bootstrap, seed, pareado=True)
    invalidos = int(np.sum(~np.isfinite(pend)))
    if invalidos > 0.5 * n_bootstrap:
        return {"error": "Mas de la mitad de los remuestreos tienen X constante: "
                         "el bootstrap de la recta no sirve con estos datos."}
    rp = _resumen(pend, b, alpha, metodo, _jackknife(_pendiente, [x, y], pareado=True),
                  n_bootstrap)
    ri = _resumen(inter, a, alpha, metodo, _jackknife(_intercepto, [x, y], pareado=True),
                  n_bootstrap)
    return {
        "original_slope": b, "original_intercept": a,
        "bootstrap_slope": float(np.mean(rp["bootstrap_distribution"])),
        "bootstrap_intercept": float(np.mean(ri["bootstrap_distribution"])),
        "se_slope": rp["bootstrap_se"], "se_intercept": ri["bootstrap_se"],
        "ci_slope": (rp["ci_lower"], rp["ci_upper"]),
        "ci_intercept": (ri["ci_lower"], ri["ci_upper"]),
        "metodo_ic": rp["metodo_ic"], "ci_level": ci, "n_bootstrap": n_bootstrap,
        "n_invalidos": invalidos, "n_original": n,
        "distribucion_pendiente": rp["bootstrap_distribution"],
    }
