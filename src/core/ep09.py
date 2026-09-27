"""Comparación de métodos con muestras de pacientes, CLSI EP09c (2018).

Dos piezas que usan el asistente «Validar un método» y el Omnianálisis:

- `regla_ep09`: qué recta corresponde (§6.2). DE constante con diferencias
  normales → Deming; CV constante con diferencias normales → Deming ponderado
  (apéndice B); variabilidad mixta o diferencias no normales → Passing-Bablok.
  Una sola copia: si cada lado tuviera la suya, volverían a divergir.
- `sesgo_en_niveles`: el sesgo que predice la recta en cada nivel de decisión
  médica, con su IC 95 % (§6.3), y `veredicto` contra el sesgo permitido.

X = comparativo, Y = candidato, sesgo = Y − X (EP09c, tabla 1).
"""
from __future__ import annotations

import numpy as np
from scipy import stats

from src.core.agreement import _deming_fit, _deming_ponderado_fit
from src.core.bland_altman import CV_CONSTANTE, DE_CONSTANTE, variabilidad_diferencias
from src.core.passing_bablok import _recta as _recta_pb
from src.core.statistics import normality_test

N_EP09 = 40             # EP09c: al menos 40 muestras de pacientes
DEMING, DEMING_PONDERADO, PASSING_BABLOK = "deming", "deming_ponderado", "passing_bablok"
NOMBRES = {DEMING: "Deming", DEMING_PONDERADO: "Deming ponderado",
           PASSING_BABLOK: "Passing-Bablok"}
BOOTSTRAP_B = 1000
SEMILLA = 20260927      # fija: el mismo archivo da el mismo intervalo

CUMPLE, NO_CUMPLE, NO_CONCLUYENTE, NO_EVALUABLE = (
    "Cumple", "No cumple", "No concluyente", "No evaluable")


def regla_ep09(clase: str, diferencias_normales: bool) -> str:
    """La recta que corresponde según EP09c §6.2."""
    if diferencias_normales and clase == DE_CONSTANTE:
        return DEMING
    if diferencias_normales and clase == CV_CONSTANTE:
        return DEMING_PONDERADO
    return PASSING_BABLOK


def elegir_regresion(x, y, alpha: float = 0.05) -> dict:
    """Mide lo que pide la regla y la aplica.

    La variabilidad se clasifica contra X (el comparativo), y la normalidad se
    prueba en la escala que corresponde: en % si el CV es constante.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    d = y - x
    var = variabilidad_diferencias(x, d, alpha)
    en_pct = var["clase"] == CV_CONSTANTE and bool(np.all(x > 0))
    d_esc = 100 * d / x if en_pct else d
    norm = normality_test(d_esc)
    normales = True if norm is None else bool(norm["normal"])
    return {"metodo": regla_ep09(var["clase"], normales), "variabilidad": var,
            "normalidad": norm, "normales": normales, "en_pct": en_pct}


def _ajustador(metodo: str, lam: float):
    """(x, y) → (pendiente, intercepto), o None si no se puede ajustar."""
    if metodo == DEMING:
        return lambda x, y: _deming_fit(x, y, lam)
    if metodo == DEMING_PONDERADO:
        return lambda x, y: _deming_ponderado_fit(x, y, lam)

    def pb(x, y):
        r = _recta_pb(x, y)
        return None if "error" in r else (r["pendiente"], r["intercepto"])
    return pb


def sesgo_en_niveles(x, y, metodo: str, niveles, lam: float = 1.0,
                     b: int = BOOTSTRAP_B, semilla: int = SEMILLA) -> dict:
    """Sesgo predicho por la recta en cada nivel Xc, con IC 95 %.

    sesgo(Xc) = a + (b − 1)·Xc. El IC:
    - Deming (con o sin ponderar): jackknife, como el de la pendiente y el
      intercepto (EP09c, apéndice K): pseudovalores dejando una muestra afuera,
      estimación ± t(N−2)·EE.
    - Passing-Bablok: bootstrap percentil. El jackknife no sirve para
      estimadores de mediana: sus pseudovalores saltan de a escalones y el EE
      no converge (Efron y Tibshirani 1993, cap. 11).
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    niveles = np.atleast_1d(np.asarray(niveles, dtype=float))
    ajustar = _ajustador(metodo, lam)
    completo = ajustar(x, y)
    if completo is None:
        return {"error": f"La recta de {NOMBRES[metodo]} no se pudo ajustar con estos datos."}
    pend, inter = completo
    sesgo = inter + (pend - 1) * niveles
    n = len(x)

    if metodo == PASSING_BABLOK:
        rng = np.random.default_rng(semilla)
        vueltas = []
        for _ in range(b):
            idx = rng.integers(0, n, n)
            f = ajustar(x[idx], y[idx])
            if f is not None and np.isfinite(f[0]):
                vueltas.append(f[1] + (f[0] - 1) * niveles)
        if len(vueltas) < b // 2:
            return {"error": "El bootstrap de Passing-Bablok falló en más de la mitad de "
                             "las vueltas: hay demasiados valores repetidos en X."}
        vueltas = np.asarray(vueltas)
        ic_inf, ic_sup = np.percentile(vueltas, [2.5, 97.5], axis=0)
        metodo_ic = f"bootstrap percentil, {len(vueltas)} remuestras"
    else:
        dejando = []
        for k in range(n):
            m = np.ones(n, dtype=bool)
            m[k] = False
            f = ajustar(x[m], y[m])
            if f is not None:
                dejando.append(f[1] + (f[0] - 1) * niveles)
        if len(dejando) < 2 or n < 3:
            return {"error": "El jackknife no pudo reajustar la recta."}
        dejando = np.asarray(dejando)
        m_ok = len(dejando)
        ee = np.sqrt((m_ok - 1) / m_ok * np.sum((dejando - dejando.mean(axis=0)) ** 2, axis=0))
        t = stats.t.ppf(0.975, n - 2)
        ic_inf, ic_sup = sesgo - t * ee, sesgo + t * ee
        metodo_ic = "jackknife, t(N−2) (EP09c, apéndice K)"

    return {"metodo": metodo, "pendiente": float(pend), "intercepto": float(inter),
            "niveles": niveles.tolist(), "sesgo": sesgo.tolist(),
            "ic_inf": np.atleast_1d(ic_inf).tolist(), "ic_sup": np.atleast_1d(ic_sup).tolist(),
            "metodo_ic": metodo_ic}


def veredicto(ic_inf: float, ic_sup: float, permitido: float) -> str:
    """El IC del sesgo contra ±sesgo permitido, con la lógica de equivalencia.

    - todo el IC dentro de ±permitido  → cumple;
    - todo el IC del mismo lado, afuera → no cumple;
    - el IC cruza el límite            → no concluyente: con estos datos el sesgo
      real puede estar de cualquiera de los dos lados, y hacen falta más muestras.
    """
    if not (np.isfinite(ic_inf) and np.isfinite(ic_sup)) or not permitido > 0:
        return NO_EVALUABLE
    if -permitido <= ic_inf and ic_sup <= permitido:
        return CUMPLE
    if ic_inf > permitido or ic_sup < -permitido:
        return NO_CUMPLE
    return NO_CONCLUYENTE
