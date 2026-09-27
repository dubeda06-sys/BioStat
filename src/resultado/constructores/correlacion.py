"""Correlación: Pearson, Spearman y parcial, migradas a `Resultado`.

Las tres dicen cuánto se mueven juntas dos variables, y las tres cargan con el
mismo malentendido: en el laboratorio se usan para comparar métodos, y una
correlación alta no dice que dos métodos concuerden (Bland y Altman 1986). Por
eso el matiz de cada una lo recuerda.
"""
from __future__ import annotations

import numpy as np

from src.core.statistics import normality_test, partial_correlation, pearson_r, spearman_rho
from src.resultado.citas import ficha
from src.resultado.datos import columnas_faltantes, filas_completas
from src.resultado.lenguaje import fmt_p, p_token
from src.resultado.modelo import Figura, Metodo, Resultado, Supuesto, Valor

# Mukaka (2012): una escala para poner palabras a |r|. Es convención, no ley.
_FUERZA = ((0.9, "muy alta"), (0.7, "alta"), (0.5, "moderada"), (0.3, "baja"), (0.0, "despreciable"))

_MATIZ = ("Correlación no es acuerdo: dos métodos pueden correlacionar casi perfecto y "
          "diferir en 20 unidades en cada paciente (Bland y Altman 1986). Para comparar "
          "métodos está Bland-Altman. Y correlación no es causa.")


def _f(x, dec=4) -> str:
    return Valor("", x, decimales=dec).texto()


def fuerza(r) -> str:
    a = abs(float(r))
    return next(t for corte, t in _FUERZA if a >= corte)


def _pares(analisis, titulo, df, *cols):
    """(datos, entrada, None) o (None, None, rechazo)."""
    falta = columnas_faltantes(df, *cols)
    if falta:
        return None, None, Resultado.rechazo(analisis, titulo, falta)
    if len(set(cols)) < len(cols):
        return None, None, Resultado.rechazo(analisis, titulo,
                                             "Elegí columnas distintas: una variable consigo "
                                             "misma correlaciona 1 por definición.")
    pares, entrada = filas_completas(df, *cols)
    try:
        datos = [pares[c].to_numpy(dtype=float) for c in cols]
    except (TypeError, ValueError):
        return None, None, Resultado.rechazo(analisis, titulo,
                                             "Alguna de las columnas tiene texto: la "
                                             "correlación necesita números.", entrada)
    return datos, entrada, None


def _ic_ok(ic) -> bool:
    return ic is not None and all(np.isfinite(v) for v in ic)


def _paso_deteccion(nombre, coef, ic, p, n) -> Supuesto:
    detecta = p < 0.05
    sentido = "positiva" if coef > 0 else "negativa"
    return Supuesto(
        f"¿Hay {nombre}?",
        f"{_f(coef)}" + (f", IC 95 % {_f(ic[0])} a {_f(ic[1])}" if _ic_ok(ic) else "")
        + f", {p_token(p)}, n = {n}",
        f"Se detectó, {sentido}" if detecta else "No se detectó",
        (f"El intervalo no incluye el 0: las variables se mueven juntas ({sentido})."
         if detecta else
         "El intervalo incluye el 0: con estos datos no se puede afirmar que se muevan "
         "juntas — tampoco descartarlo."),
        alternativa=("si el intervalo incluyera el 0, no se podría afirmar." if detecta else
                     "si lo excluyera, se detectaría."))


def _lectura(nombre, coef, p) -> str:
    if p >= 0.05:
        return f"No se detectó {nombre} entre las dos variables."
    sube = "sube" if coef > 0 else "baja"
    return (f"Se detectó {nombre} {'positiva' if coef > 0 else 'negativa'}, "
            f"{fuerza(coef)} (Mukaka 2012): cuando una variable sube, la otra tiende a {sube}.")


# ============================================================

def pearson(df, c1, c2, opciones=None) -> Resultado:
    titulo = f"Correlación de Pearson — {c1} y {c2}"
    datos, entrada, rechazo = _pares("pearson", titulo, df, c1, c2)
    if rechazo is not None:
        return rechazo
    x, y = datos
    r = pearson_r(x, y)
    if r is None:
        return Resultado.rechazo("pearson", titulo,
                                 f"Hacen falta al menos 3 pares completos; hay {entrada.n}.",
                                 entrada)
    falla = Resultado.rechazo_del_core("pearson", titulo, r, entrada)
    if falla is not None:
        return falla
    entrada.n = r["n"]
    valores = [Valor("n", r["n"]),
               Valor("r de Pearson", r["r"], ic=r["ci95"] if _ic_ok(r["ci95"]) else None,
                     nota=f"asociación {fuerza(r['r'])}"),
               Valor("R²", r["r2"], nota="proporción de la variación de una que acompaña "
                                         "a la otra"),
               Valor("p", fmt_p(r["p"]))]
    normales = [(c, normality_test(v)) for c, v in ((c1, x), (c2, y))]
    no_normales = [c for c, t in normales if t is not None and not t["normal"]]
    medicion = "; ".join(f"{c}: {p_token(t['p'])}" if t else f"{c}: no evaluable"
                         for c, t in normales)
    paso_normal = Supuesto(
        "¿Las dos variables son normales?", f"Shapiro-Wilk — {medicion}",
        "Sí" if not no_normales else "No: " + ", ".join(no_normales),
        ("Pearson supone variables normales: se cumple." if not no_normales else
         "Pearson supone variables normales (MedCalc), y no se cumple: un par de valores "
         "extremos puede fabricar o esconder una correlación. Spearman, que usa rangos, no "
         "lo supone."),
        alternativa=("si no lo fueran, convendría Spearman." if not no_normales else
                     "con variables normales, Pearson sería el indicado."),
        ok=not no_normales)
    f = ficha("pearson")
    return Resultado(
        analisis="pearson", titulo=titulo, entrada=entrada, valores=valores,
        metodo=Metodo("Correlación de Pearson",
                      "Mide cuánto se alinean los puntos sobre una recta. Solo ve relaciones "
                      "lineales."),
        supuestos=[paso_normal, _paso_deteccion("correlación lineal", r["r"], r["ci95"],
                                                r["p"], r["n"])],
        formula=f.formula, citas=list(f.citas),
        lectura=_lectura("correlación lineal", r["r"], r["p"]), matiz=_MATIZ,
        figuras=[Figura("Dispersión", lambda: _figura_dispersion(x, y, c1, c2, recta=True))],
        crudo={"pearson": r})


def spearman(df, c1, c2, opciones=None) -> Resultado:
    titulo = f"Correlación de Spearman — {c1} y {c2}"
    datos, entrada, rechazo = _pares("spearman", titulo, df, c1, c2)
    if rechazo is not None:
        return rechazo
    x, y = datos
    r = spearman_rho(x, y)
    if r is None:
        return Resultado.rechazo("spearman", titulo,
                                 f"Hacen falta al menos 3 pares completos; hay {entrada.n}.",
                                 entrada)
    falla = Resultado.rechazo_del_core("spearman", titulo, r, entrada)
    if falla is not None:
        return falla
    entrada.n = r["n"]
    valores = [Valor("n", r["n"]),
               Valor("ρ de Spearman", r["rho"], ic=r["ci95"] if _ic_ok(r["ci95"]) else None,
                     nota=f"asociación {fuerza(r['rho'])}"),
               Valor("p", fmt_p(r["p"]))]
    n = r["n"]
    paso_n = Supuesto(
        "¿El p es confiable con este n?", f"n = {n}",
        "Sí" if n >= 10 else "Aproximado",
        ("Con 10 pares o más, la aproximación t del p de Spearman es buena." if n >= 10 else
         "Con menos de 10 pares el p sale de una aproximación: tomalo como orientativo."),
        ok=n >= 10)
    f = ficha("spearman")
    return Resultado(
        analisis="spearman", titulo=titulo, entrada=entrada, valores=valores,
        metodo=Metodo("Correlación de Spearman",
                      "La correlación de Pearson de los rangos: mide si una variable crece "
                      "cuando crece la otra, aunque no sea en línea recta, y no supone "
                      "ninguna distribución."),
        supuestos=[paso_n, _paso_deteccion("correlación monótona", r["rho"], r["ci95"],
                                           r["p"], n)],
        formula=f.formula, citas=list(f.citas),
        lectura=_lectura("correlación monótona", r["rho"], r["p"]), matiz=_MATIZ,
        figuras=[Figura("Dispersión", lambda: _figura_dispersion(x, y, c1, c2))],
        crudo={"spearman": r})


def parcial(df, c1, c2, c3, opciones=None) -> Resultado:
    titulo = f"Correlación parcial — {c1} y {c2}, controlando {c3}"
    datos, entrada, rechazo = _pares("parcial", titulo, df, c1, c2, c3)
    if rechazo is not None:
        return rechazo
    x, y, z = datos
    r = partial_correlation(x, y, z)
    if r is None:
        return Resultado.rechazo("parcial", titulo,
                                 f"Hacen falta al menos 4 filas completas con dispersión en las "
                                 f"tres variables; hay {entrada.n}.", entrada)
    falla = Resultado.rechazo_del_core("parcial", titulo, r, entrada)
    if falla is not None:
        return falla
    entrada.n = r["n"]
    valores = [Valor("n", r["n"]),
               Valor(f"r parcial ({c1}, {c2} | {c3})", r["r_partial"],
                     ic=r["ci95"] if _ic_ok(r["ci95"]) else None),
               Valor("p", fmt_p(r["p"]), nota=f"t = {_f(r['t'], 3)}, {r['df']} gl"),
               Valor(f"r simple ({c1}, {c2})", r["r_xy"], nota="sin controlar"),
               Valor(f"r ({c1}, {c3})", r["r_xz"]),
               Valor(f"r ({c2}, {c3})", r["r_yz"])]
    simple, resto = abs(r["r_xy"]), abs(r["r_partial"])
    if simple - resto >= 0.1 and resto < 0.5 * simple:
        cuanto, porque = "Casi toda", (f"casi toda la asociación se explica porque las dos "
                                       f"dependen de {c3}.")
    elif simple - resto >= 0.1:
        cuanto, porque = "Parte", f"una parte de la asociación pasa por {c3}."
    elif resto - simple >= 0.1:
        cuanto, porque = "Ninguna: la escondía", (f"controlar {c3} destapa una asociación "
                                                   "que la correlación simple escondía.")
    else:
        cuanto, porque = "Poca", f"la asociación no se debe a {c3}."
    paso_z = Supuesto(
        f"¿Cuánto de la asociación pasa por {c3}?",
        f"r simple {_f(r['r_xy'])} → r parcial {_f(r['r_partial'])}",
        cuanto, f"Al controlar {c3}, {porque}")
    f = ficha("parcial")
    return Resultado(
        analisis="parcial", titulo=titulo, entrada=entrada, valores=valores,
        metodo=Metodo("Correlación parcial",
                      f"La correlación entre {c1} y {c2} que queda después de sacarles a "
                      f"las dos la parte que se explica linealmente por {c3}."),
        supuestos=[paso_z, _paso_deteccion("correlación parcial", r["r_partial"], r["ci95"],
                                           r["p"], r["n"])],
        formula=f.formula, citas=list(f.citas),
        lectura=_lectura("correlación parcial", r["r_partial"], r["p"]),
        matiz=("Solo controla lo que se mide y de forma lineal: una cuarta variable no medida "
               "puede seguir explicando la asociación. " + _MATIZ),
        figuras=[Figura("Residuos", lambda: _figura_residuos(x, y, z, c1, c2, c3))],
        crudo={"parcial": r})


# ============================================================

def _figura_dispersion(x, y, c1, c2, recta=False):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.5, 6))
    ax.scatter(x, y, alpha=0.55, c='#4f6ef7', edgecolors='white', s=45)
    if recta and np.ptp(x) > 0:
        b, a = np.polyfit(x, y, 1)
        xs = np.linspace(np.min(x), np.max(x), 100)
        ax.plot(xs, a + b * xs, color='#ef4444', lw=1.8, label="Recta de mínimos cuadrados")
        ax.legend(framealpha=0.9)
    ax.set_xlabel(str(c1))
    ax.set_ylabel(str(c2))
    ax.set_title(f"{c2} contra {c1}", fontweight='bold')
    fig.tight_layout()
    return fig


def _figura_residuos(x, y, z, c1, c2, c3):
    """La correlación parcial ES la correlación de estos residuos."""
    import matplotlib.pyplot as plt

    rx = x - np.polyval(np.polyfit(z, x, 1), z)
    ry = y - np.polyval(np.polyfit(z, y, 1), z)
    fig, ax = plt.subplots(figsize=(7.5, 6))
    ax.scatter(rx, ry, alpha=0.55, c='#4f6ef7', edgecolors='white', s=45)
    ax.axhline(0, color='#8892a4', lw=1, ls='--')
    ax.axvline(0, color='#8892a4', lw=1, ls='--')
    ax.set_xlabel(f"{c1} sin la parte de {c3}")
    ax.set_ylabel(f"{c2} sin la parte de {c3}")
    ax.set_title("Lo que queda después de controlar", fontweight='bold')
    fig.tight_layout()
    return fig
