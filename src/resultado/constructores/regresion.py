"""Regresión: lineal, múltiple, logística y probit, migradas a `Resultado`.

Los números salen del core (`src/core/regression.py`, `src/core/probit.py`);
los diagnósticos que el panel no hacía (linealidad, normalidad y varianza de los
residuos, colinealidad, eventos por variable, calibración) salen de
statsmodels, que es el oráculo de los modelos en esta app.
"""
from __future__ import annotations

import numpy as np
from scipy import stats

from src.core.probit import dosis_efectiva, probit_regression
from src.core.regression import linear_regression, logistic_regression, multiple_regression
from src.core.statistics import normality_test
from src.resultado.citas import ficha
from src.resultado.datos import columnas_faltantes, filas_completas
from src.resultado.lenguaje import p_token
from src.resultado.modelo import Figura, Metodo, Resultado, Supuesto, Valor

EPV_MINIMO = 10          # eventos por variable, Peduzzi et al. (1996)
VIF_ALTO = 5.0


def _f(x, dec=4) -> str:
    return Valor("", x, decimales=dec).texto()


def _lista(cols):
    if isinstance(cols, str):
        cols = [cols]
    return list(dict.fromkeys(cols or []))


def _datos(analisis, titulo, df, *cols):
    falta = columnas_faltantes(df, *cols)
    if falta:
        return None, None, Resultado.rechazo(analisis, titulo, falta)
    filas, entrada = filas_completas(df, *cols)
    try:
        return {c: filas[c].to_numpy(dtype=float) for c in cols}, entrada, None
    except (TypeError, ValueError):
        return None, None, Resultado.rechazo(analisis, titulo,
                                             "Alguna de las columnas tiene texto: el modelo "
                                             "necesita números.", entrada)


def _ols(X, y):
    import statsmodels.api as sm
    return sm.OLS(y, sm.add_constant(X, has_constant="add")).fit()


def _pasos_residuos(ajuste, pregunta_lineal=True) -> list[Supuesto]:
    """Linealidad (RESET), normalidad y varianza constante de los residuos."""
    from statsmodels.stats.diagnostic import het_breuschpagan, linear_reset

    pasos = []
    if pregunta_lineal:
        try:
            reset = linear_reset(ajuste, power=2, use_f=True)
            p = float(reset.pvalue)
            curva = p < 0.05
            pasos.append(Supuesto(
                "¿La relación es lineal?", f"RESET de Ramsey (término cuadrático): {p_token(p)}",
                "Se detectó curvatura" if curva else "No se detectó curvatura",
                ("Una recta no describe bien los datos: los coeficientes promedian una "
                 "curva. Mirá el gráfico de residuos." if curva else
                 "La recta describe la forma de los datos."),
                alternativa=("sin curvatura, la recta serviría." if curva else
                             "con curvatura, habría que transformar o agregar un término."),
                ok=not curva))
        except Exception:  # noqa: BLE001 - con pocos datos RESET no se puede calcular
            pass
    t = normality_test(ajuste.resid)
    if t is not None:
        pasos.append(Supuesto(
            "¿Los residuos son normales?", f"Shapiro-Wilk: {p_token(t['p'])}",
            "Sí" if t["normal"] else "No",
            ("Los IC y los p de los coeficientes valen." if t["normal"] else
             "Los IC y los p suponen residuos normales: con muchos datos importa poco, con "
             "pocos son aproximados."),
            ok=bool(t["normal"])))
    try:
        _, p_bp, _, _ = het_breuschpagan(ajuste.resid, ajuste.model.exog)
        pareja = p_bp >= 0.05
        pasos.append(Supuesto(
            "¿La dispersión de los residuos es pareja?", f"Breusch-Pagan: {p_token(p_bp)}",
            "Sí" if pareja else "No",
            ("La varianza constante que suponen los EE se cumple." if pareja else
             "La dispersión cambia con los valores: los EE y los p pueden estar mal. Probá "
             "con los logaritmos de la respuesta."),
            ok=bool(pareja)))
    except Exception:  # noqa: BLE001
        pass
    return pasos


# ============================================================
#  Lineal simple
# ============================================================

def regresion_lineal(df, c1, c2, opciones=None) -> Resultado:
    """Variable 1 = predictora (x), Variable 2 = respuesta (y)."""
    titulo = f"Regresión lineal — {c2} según {c1}"
    datos, entrada, rechazo = _datos("regresion_lineal", titulo, df, c1, c2)
    if rechazo is not None:
        return rechazo
    r = linear_regression(datos[c1], datos[c2])
    falla = Resultado.rechazo_del_core("regresion_lineal", titulo, r, entrada)
    if falla is not None:
        return falla
    entrada.n = r["n"]
    ajuste = _ols(r["x"], r["y"])
    valores = [
        Valor("Pendiente", r["slope"], ic=r["ci_slope"], nota=f"{p_token(r['p_slope'])}"),
        Valor("Intercepto", r["intercept"], ic=r["ci_intercept"]),
        Valor("R²", r["r2"]), Valor("R² ajustado", r["r2_adj"]),
        Valor("Error estándar residual", r["rmse"]),
        Valor("n", r["n"]),
    ]
    detecta = r["p_slope"] < 0.05
    pendiente = Supuesto(
        f"¿{c2} cambia con {c1}?",
        f"pendiente {_f(r['slope'])}, IC 95 % {_f(r['ci_slope'][0])} a {_f(r['ci_slope'][1])}, "
        f"{p_token(r['p_slope'])}",
        "Se detectó" if detecta else "No se detectó",
        (f"Por cada unidad de {c1}, {c2} cambia {_f(r['slope'])} en promedio." if detecta else
         "El intervalo de la pendiente incluye el 0: no se puede afirmar una relación lineal."),
        alternativa=("con el intervalo incluyendo el 0, no se afirmaría." if detecta else
                     "con el intervalo excluyendo el 0, se detectaría."))
    f = ficha("regresion_lineal")
    return Resultado(
        analisis="regresion_lineal", titulo=titulo, entrada=entrada, valores=valores,
        metodo=Metodo("Mínimos cuadrados ordinarios",
                      f"La recta que minimiza las distancias verticales de {c2} a la recta: "
                      f"supone {c1} medida sin error."),
        supuestos=[pendiente, *_pasos_residuos(ajuste)],
        formula=f.formula, citas=list(f.citas),
        lectura=(f"{c2} = {_f(r['intercept'])} + {_f(r['slope'])}·{c1}. La recta explica el "
                 f"{100 * r['r2']:.1f} % de la variación de {c2} (R²)."),
        matiz=("No sirve para comparar dos métodos de medición: supone que la X no tiene "
               "error, y cuando lo tiene la pendiente sale achicada (Cornbleet y Gochman "
               "1979). Para eso están Deming y Passing-Bablok. Y la recta solo vale dentro "
               f"del rango de {c1} medido."),
        figuras=[Figura("Recta", lambda: _figura_recta(ajuste, r["x"], r["y"], c1, c2)),
                 Figura("Residuos", lambda: _figura_residuos(ajuste, c2))],
        crudo={"lineal": r})


# ============================================================
#  Múltiple
# ============================================================

def regresion_multiple(df, respuesta, predictoras, opciones=None) -> Resultado:
    predictoras = [p for p in _lista(predictoras) if p != respuesta]
    titulo = f"Regresión múltiple — {respuesta}"
    if not predictoras:
        return Resultado.rechazo("regresion_multiple", titulo,
                                 "Hace falta al menos una predictora distinta de la respuesta.")
    datos, entrada, rechazo = _datos("regresion_multiple", titulo, df, respuesta, *predictoras)
    if rechazo is not None:
        return rechazo
    X = np.column_stack([datos[p] for p in predictoras])
    y = datos[respuesta]
    r = multiple_regression(X, y)
    if r is None:
        return Resultado.rechazo("regresion_multiple", titulo,
                                 f"Con {entrada.n} filas completas no alcanza para "
                                 f"{len(predictoras)} predictora(s).", entrada)
    falla = Resultado.rechazo_del_core("regresion_multiple", titulo, r, entrada)
    if falla is not None:
        return falla
    entrada.n = r["n"]
    gl = r["n"] - r["p_predictors"] - 1
    t = stats.t.ppf(0.975, gl)
    valores = [Valor("n", r["n"]), Valor("R²", r["r2"]), Valor("R² ajustado", r["r2_adj"]),
               Valor("F", r["f"], nota=f"{p_token(r['p_model'])}"),
               Valor("Error estándar residual", r["rmse"])]
    for nombre, b, se, p in zip(["Intercepto"] + predictoras, r["coeffs"], r["se"], r["p"]):
        valores.append(Valor(f"b — {nombre}", b, ic=(b - t * se, b + t * se),
                             nota=f"EE {_f(se)}, {p_token(p)}"))
    ajuste = _ols(X, y)
    supuestos = [_paso_modelo(r)]
    if len(predictoras) > 1:
        supuestos.append(_paso_vif(X, predictoras))
    supuestos += _pasos_residuos(ajuste, pregunta_lineal=True)
    aportan = [n for n, p in zip(predictoras, r["p"][1:]) if p < 0.05]
    f = ficha("regresion_multiple")
    return Resultado(
        analisis="regresion_multiple", titulo=titulo, entrada=entrada, valores=valores,
        metodo=Metodo("Mínimos cuadrados con varias predictoras",
                      "Cada coeficiente es el cambio de la respuesta por unidad de esa "
                      "predictora, con las demás quietas."),
        supuestos=supuestos, formula=f.formula, citas=list(f.citas),
        lectura=(f"El modelo explica el {100 * r['r2_adj']:.1f} % de la variación de "
                 f"{respuesta} (R² ajustado). "
                 + (f"Aportan, con las demás en el modelo: {', '.join(aportan)}." if aportan
                    else "Ninguna predictora aporta por sí sola con las demás en el modelo.")),
        matiz=("Cada coeficiente se lee «con las demás fijas»: si dos predictoras van juntas, "
               "ninguna parece aportar aunque juntas expliquen mucho. Asociación no es causa."),
        figuras=[Figura("Residuos", lambda: _figura_residuos(ajuste, respuesta))],
        crudo={"multiple": r, "predictoras": predictoras})


def _paso_modelo(r) -> Supuesto:
    detecta = r["p_model"] < 0.05
    return Supuesto(
        "¿El modelo explica algo?", f"F = {_f(r['f'])}, {p_token(r['p_model'])}",
        "Sí" if detecta else "No se detectó",
        ("Al menos una predictora se asocia con la respuesta." if detecta else
         "Con estos datos no se puede afirmar que las predictoras, juntas, expliquen la "
         "respuesta."),
        ok=True)


def _paso_vif(X, nombres) -> Supuesto:
    import statsmodels.api as sm
    from statsmodels.stats.outliers_influence import variance_inflation_factor

    diseno = sm.add_constant(X, has_constant="add")
    vif = [float(variance_inflation_factor(diseno, i + 1)) for i in range(X.shape[1])]
    altos = [f"{n} ({v:.1f})" for n, v in zip(nombres, vif) if v > VIF_ALTO]
    return Supuesto(
        "¿Las predictoras se repiten información?",
        "VIF: " + ", ".join(f"{n} {v:.1f}" for n, v in zip(nombres, vif)),
        "No" if not altos else "Sí: " + ", ".join(altos),
        ("Cada predictora aporta información propia." if not altos else
         f"Un VIF mayor que {VIF_ALTO:g} dice que esa predictora se explica casi entera por "
         "las otras: su coeficiente es inestable y su EE está inflado. Sacá una de las que "
         "van juntas."),
        ok=not altos)


# ============================================================
#  Logística
# ============================================================

def regresion_logistica(df, respuesta, predictoras, opciones=None) -> Resultado:
    predictoras = [p for p in _lista(predictoras) if p != respuesta]
    titulo = f"Regresión logística — {respuesta}"
    if not predictoras:
        return Resultado.rechazo("regresion_logistica", titulo,
                                 "Hace falta al menos una predictora distinta de la respuesta.")
    datos, entrada, rechazo = _datos("regresion_logistica", titulo, df, respuesta, *predictoras)
    if rechazo is not None:
        return rechazo
    y = datos[respuesta]
    valores_y = sorted(set(y[np.isfinite(y)].tolist()))
    if not set(valores_y) <= {0.0, 1.0}:
        return Resultado.rechazo("regresion_logistica", titulo,
                                 f"«{respuesta}» tiene que ser 0/1; tiene "
                                 + ", ".join(f"{v:g}" for v in valores_y[:6]) + ".", entrada)
    X = np.column_stack([datos[p] for p in predictoras])
    r = logistic_regression(X, y)
    if r is None:
        return Resultado.rechazo("regresion_logistica", titulo,
                                 f"Con {entrada.n} filas no alcanza para {len(predictoras)} "
                                 "predictora(s).", entrada)
    falla = Resultado.rechazo_del_core("regresion_logistica", titulo, r, entrada)
    if falla is not None:
        return falla
    entrada.n = r["n"]
    eventos = int(r["y"].sum())
    menor = min(eventos, r["n"] - eventos)
    from sklearn.metrics import roc_auc_score
    auc = float(roc_auc_score(r["y"], r["prob"]))
    hl = r["hosmer_lemeshow"]
    valores = [Valor("n", r["n"]), Valor("Eventos (1)", eventos),
               Valor("AUC del modelo", auc, nota="sobre los mismos datos: optimista"),
               Valor("R² de McFadden", r["pseudo_r2"]), Valor("AIC", r["aic"], decimales=2)]
    for i, nombre in enumerate(["Intercepto"] + predictoras):
        valores.append(Valor(f"OR — {nombre}" if i else "Intercepto (log-odds)",
                             r["odds_ratios"][i] if i else r["coeffs"][i],
                             ic=(r["or_ci_low"][i], r["or_ci_high"][i]) if i else None,
                             nota=f"b = {_f(r['coeffs'][i])}, {p_token(r['p'][i])}"))
    epv = menor / len(predictoras)
    supuestos = [
        Supuesto(
            "¿Hay eventos suficientes para tantas predictoras?",
            f"{menor} en la clase menos frecuente, {len(predictoras)} predictora(s): "
            f"{epv:.1f} por variable",
            "Sí" if epv >= EPV_MINIMO else "No",
            ("Con 10 o más eventos por variable los coeficientes son estables (Peduzzi et al. "
             "1996)." if epv >= EPV_MINIMO else
             "Con menos de 10 eventos por variable los coeficientes se sesgan y los IC fallan "
             "(Peduzzi et al. 1996): sacá predictoras o juntá más casos."),
            ok=epv >= EPV_MINIMO),
        Supuesto(
            "¿Las probabilidades predichas coinciden con lo observado?",
            f"Hosmer-Lemeshow: H = {_f(hl['h'], 3)}, {hl['gl']} gl, {p_token(hl['p'])}",
            "Sí" if not (hl["p"] < 0.05) else "No",
            ("No se detecta mala calibración: en cada tramo de riesgo los eventos observados "
             "se parecen a los esperados." if not (hl["p"] < 0.05) else
             "En algún tramo de riesgo el modelo predice mal: puede faltar una predictora o "
             "una no lineal."),
            ok=not (hl["p"] < 0.05)),
    ]
    aportan = [n for n, p in zip(predictoras, r["p"][1:]) if p < 0.05]
    f = ficha("regresion_logistica")
    return Resultado(
        analisis="regresion_logistica", titulo=titulo, entrada=entrada, valores=valores,
        metodo=Metodo("Regresión logística por máxima verosimilitud",
                      "Modela la probabilidad de que la respuesta sea 1; cada OR es cuánto se "
                      "multiplican las chances por unidad de la predictora, con las demás "
                      "fijas."),
        supuestos=supuestos, formula=f.formula, citas=list(f.citas),
        lectura=((f"Se asocian con {respuesta}, con las demás en el modelo: "
                  f"{', '.join(aportan)}. " if aportan else
                  "Ninguna predictora se asocia por sí sola con la respuesta. ")
                 + f"El modelo discrimina con AUC {auc:.3f}."),
        matiz=("La AUC y la exactitud se miden sobre los mismos datos con que se ajustó el "
               "modelo: en pacientes nuevos rinde menos. El modelo supone que el log-odds "
               "cambia en línea recta con cada predictora continua."),
        figuras=[Figura("Curva ROC del modelo", lambda: _figura_roc(r["y"], r["prob"], auc))],
        crudo={"logistica": r, "auc": auc, "predictoras": predictoras})


# ============================================================
#  Probit
# ============================================================

def probit(df, c1, c2, opciones=None) -> Resultado:
    """Variable 1 = dosis o concentración, Variable 2 = respuesta 0/1.

    `opciones["escala"]`: "lineal" | "log10" (la dosis en logaritmos, lo habitual en
    curvas dosis-respuesta y en el LoD de EP17).
    """
    opciones = opciones or {}
    en_log = opciones.get("escala", "lineal") == "log10"
    titulo = f"Regresión probit — {c2} según {c1}" + (" (log10)" if en_log else "")
    datos, entrada, rechazo = _datos("probit", titulo, df, c1, c2)
    if rechazo is not None:
        return rechazo
    x, y = datos[c1], datos[c2]
    if en_log:
        if np.any(x[np.isfinite(x)] <= 0):
            return Resultado.rechazo("probit", titulo,
                                     f"En escala log10 la dosis tiene que ser positiva, y «{c1}» "
                                     "tiene ceros o negativos.", entrada)
        x = np.log10(x)
    r = probit_regression(x.reshape(-1, 1), y)
    falla = Resultado.rechazo_del_core("probit", titulo, r, entrada)
    if falla is not None:
        return falla
    entrada.n = r["n"]
    b0, b1 = r["coefficients"]
    dosis = [dosis_efectiva(r["coefficients"], r["cov"], p) for p in (0.5, 0.95)]
    volver = (lambda v: 10 ** v) if en_log else (lambda v: v)
    valores = [Valor("n", r["n"]),
               Valor("b0 (intercepto)", b0, nota=f"EE {_f(r['se'][0])}, {p_token(r['p_values'][0])}"),
               Valor(f"b1 ({c1}{', log10' if en_log else ''})", b1,
                     nota=f"EE {_f(r['se'][1])}, {p_token(r['p_values'][1])}")]
    for d in dosis:
        if "error" in d:
            continue
        valores.append(Valor(f"Dosis con respuesta del {100 * d['prob']:.0f} %",
                             volver(d["dosis"]),
                             ic=tuple(volver(v) for v in d["ic95"]),
                             nota="ED50" if d["prob"] == 0.5 else
                             "ED95: el límite de detección por probit (CLSI EP17)"))
    valores += [Valor("Log-verosimilitud", r["log_likelihood"]), Valor("AIC", r["aic"], decimales=2)]
    detecta = r["p_values"][1] < 0.05
    supuestos = [Supuesto(
        f"¿La proporción de 1 cambia con {c1}?",
        f"b1 = {_f(b1)}, {p_token(r['p_values'][1])}",
        "Se detectó" if detecta else "No se detectó",
        ("La probabilidad de respuesta cambia con la dosis: las dosis efectivas tienen "
         "sentido." if detecta else
         "Sin una pendiente clara, las dosis efectivas no se pueden estimar con precisión."),
        ok=bool(detecta))]
    if not en_log:
        supuestos.append(Supuesto(
            "¿La dosis va en escala lineal?", "elegido en el diálogo", "Sí",
            "En curvas dosis-respuesta (y en el LoD de EP17) la dosis suele ir en log10: la "
            "curva queda simétrica y el modelo ajusta mejor.",
            alternativa="en log10, cada paso sería multiplicar la dosis.", ok=True))
    ed95 = next((d for d in dosis if d.get("prob") == 0.95 and "error" not in d), None)
    f = ficha("probit")
    return Resultado(
        analisis="probit", titulo=titulo, entrada=entrada, valores=valores,
        metodo=Metodo("Probit por máxima verosimilitud",
                      "Modela la probabilidad de respuesta como una normal acumulada de la "
                      "dosis: de ahí salen la dosis con la que responde el 50 % y el 95 %."),
        supuestos=supuestos, formula=f.formula, citas=list(f.citas),
        lectura=(f"La respuesta llega al 95 % con {c1} = {_f(volver(ed95['dosis']))} (IC 95 % "
                 f"{_f(volver(ed95['ic95'][0]))} a {_f(volver(ed95['ic95'][1]))})."
                 if ed95 else "No se pudo estimar la dosis efectiva."),
        matiz=("El ED95 es una extrapolación si pocas diluciones quedan cerca del 95 % de "
               "detección: EP17 pide diluciones alrededor del límite esperado."),
        figuras=[Figura("Curva dosis-respuesta", lambda: _figura_probit(
            x, y, b0, b1, c1, c2, en_log, [d for d in dosis if "error" not in d]))],
        crudo={"probit": r, "dosis": dosis, "escala": "log10" if en_log else "lineal"})


# ============================================================
#  Figuras
# ============================================================

def _figura_recta(ajuste, x, y, c1, c2):
    import matplotlib.pyplot as plt
    import statsmodels.api as sm

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(x, y, alpha=0.55, c='#4f6ef7', edgecolors='white', s=45)
    xs = np.linspace(np.min(x), np.max(x), 100)
    pred = ajuste.get_prediction(sm.add_constant(xs, has_constant="add")).summary_frame()
    ax.plot(xs, pred["mean"], color='#ef4444', lw=2, label="Recta")
    ax.fill_between(xs, pred["mean_ci_lower"], pred["mean_ci_upper"], color='#ef4444',
                    alpha=0.12, label="IC 95 % de la recta")
    ax.set_xlabel(str(c1))
    ax.set_ylabel(str(c2))
    ax.set_title(f"{c2} según {c1}", fontweight='bold')
    ax.legend(framealpha=0.9)
    fig.tight_layout()
    return fig


def _figura_residuos(ajuste, respuesta):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.scatter(ajuste.fittedvalues, ajuste.resid, alpha=0.55, c='#4f6ef7', edgecolors='white', s=40)
    ax.axhline(0, color='#ef4444', ls='--', lw=1.4)
    ax.set_xlabel(f"{respuesta} predicho")
    ax.set_ylabel("Residuo")
    ax.set_title("Residuos: sin forma ni embudo, el modelo está bien", fontweight='bold')
    fig.tight_layout()
    return fig


def _figura_roc(y, prob, auc):
    import matplotlib.pyplot as plt
    from sklearn.metrics import roc_curve

    fpr, tpr, _ = roc_curve(y, prob)
    fig, ax = plt.subplots(figsize=(6.5, 6))
    ax.plot(fpr, tpr, color='#4f6ef7', lw=2, label=f"AUC = {auc:.3f}")
    ax.plot([0, 1], [0, 1], color='#8892a4', ls='--', lw=1)
    ax.set_xlabel("1 − especificidad")
    ax.set_ylabel("Sensibilidad")
    ax.set_title("Curva ROC del modelo", fontweight='bold')
    ax.legend(loc="lower right", framealpha=0.9)
    fig.tight_layout()
    return fig


def _figura_probit(x, y, b0, b1, c1, c2, en_log, dosis):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5.5))
    niveles = np.unique(x)
    if len(niveles) <= 20:
        prop = [np.mean(y[x == v]) for v in niveles]
        ax.scatter(niveles, prop, color='#4f6ef7', s=60, zorder=3,
                   label="Proporción observada por nivel")
    else:
        ax.scatter(x, y, color='#4f6ef7', alpha=0.4, s=30, label="Observaciones")
    xs = np.linspace(np.min(x), np.max(x), 200)
    ax.plot(xs, stats.norm.cdf(b0 + b1 * xs), color='#ef4444', lw=2, label="Probit")
    for d in dosis:
        ax.axvline(d["dosis"], color='#d97706', ls='--', lw=1.2)
        ax.text(d["dosis"], 0.02 + 0.08 * (d["prob"] == 0.95),
                f" ED{100 * d['prob']:.0f}", color='#d97706')
    ax.set_xlabel(f"log10({c1})" if en_log else str(c1))
    ax.set_ylabel(f"Probabilidad de {c2} = 1")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("Curva dosis-respuesta", fontweight='bold')
    ax.legend(framealpha=0.9, loc="center right")
    fig.tight_layout()
    return fig
