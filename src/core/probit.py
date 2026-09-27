"""Regresion probit (statsmodels).

La version anterior tenia el mismo defecto que Cox antes de agosto y nunca se
habia arreglado aca (auditoria 2026-09, K5): leia `result.hes_inv`, que no
existe, un `except:` desnudo lo tapaba, y TODOS los errores estandar valian
0,1. De ahi salian z y p inventados. Aun con el nombre bien escrito, invertir
`hess_inv` daba el Hessiano en vez de la covarianza. Y el AIC tenia el signo
cambiado. Los coeficientes estaban bien; todo lo que sale de la varianza, no.
"""
import numpy as np
import statsmodels.api as sm


def probit_regression(X, y):
    """Regresion probit por maxima verosimilitud.

    Args:
        X: 2D array de predictoras (n x p).
        y: respuesta binaria (0 o 1).

    Returns:
        dict con coeficientes, EE, z, p, predicciones, log-verosimilitud y AIC.
    """
    X = np.atleast_2d(np.asarray(X, dtype=float))
    if X.shape[0] == 1 and X.shape[1] > 1:
        X = X.T
    y = np.asarray(y, dtype=float)
    valid = np.isfinite(X).all(axis=1) & np.isfinite(y)
    X, y = X[valid], y[valid]
    n, p = X.shape

    if not np.all(np.isin(y, (0.0, 1.0))):
        return {"error": "La respuesta del probit tiene que ser binaria (0/1)."}
    if len(np.unique(y)) < 2:
        return {"error": "La respuesta tiene un solo valor: no hay nada que modelar."}
    if n < p + 2:
        return {"error": f"Con {n} observaciones no alcanza para {p} predictora(s)."}

    diseno = sm.add_constant(X, has_constant="add")
    try:
        modelo = sm.Probit(y, diseno).fit(disp=0, maxiter=200)
    except Exception as e:
        return {"error": f"El probit no converge con estos datos ({type(e).__name__}): "
                         f"suele ser separacion completa — una predictora separa "
                         f"perfectamente los 0 de los 1."}

    # statsmodels ya no lanza una excepcion ante la separacion completa: devuelve
    # un ajuste sin convergencia con EE del orden de 1e8. Un resultado asi no se
    # informa como si fuera uno.
    predichas = np.asarray(modelo.predict(diseno), dtype=float)
    separa = np.all((predichas < 1e-6) | (predichas > 1 - 1e-6))
    if not modelo.mle_retvals.get("converged", True) or separa:
        return {"error": "El probit no converge: una predictora separa perfectamente "
                         "los 0 de los 1 (separacion completa) o casi. Con esos datos "
                         "el coeficiente tiende a infinito y no hay estimacion que dar."}
    avisos = []

    return {
        "avisos": avisos,
        "coefficients": np.asarray(modelo.params, dtype=float),
        "se": np.asarray(modelo.bse, dtype=float),
        "z": np.asarray(modelo.tvalues, dtype=float),
        "p_values": np.asarray(modelo.pvalues, dtype=float),
        "predictions": np.asarray(modelo.predict(diseno), dtype=float),
        "log_likelihood": float(modelo.llf),
        "aic": float(modelo.aic),
        "n": n,
        "cov": np.asarray(modelo.cov_params(), dtype=float),
    }


def dosis_efectiva(coeficientes, cov, prob):
    """La dosis (valor de x) con la que responde una proporcion `prob`, e IC 95 %.

    Probit con una predictora: Phi(b0 + b1 x) = prob, asi que
    x_p = (Phi^-1(prob) - b0) / b1. El IC es el del metodo delta, el mismo que
    `dose.p` del paquete MASS de R (Venables y Ripley 2002):
        grad = (-1/b1, -x_p/b1),   EE = sqrt(grad' Cov grad).
    Con x_p = ED95 es el limite de deteccion por probit de CLSI EP17.
    """
    from scipy import stats as _st
    b0, b1 = float(coeficientes[0]), float(coeficientes[1])
    if b1 == 0:
        return {"error": "La pendiente es 0: la respuesta no cambia con la dosis."}
    z = _st.norm.ppf(prob)
    x = (z - b0) / b1
    grad = np.array([-1.0 / b1, -x / b1])
    ee = float(np.sqrt(grad @ np.asarray(cov)[:2, :2] @ grad))
    medio = _st.norm.ppf(0.975) * ee
    return {"prob": prob, "dosis": x, "ee": ee, "ic95": (x - medio, x + medio)}
