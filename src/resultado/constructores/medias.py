"""Comparación de medias: t de una muestra, pareada e independiente (Welch),
comparación de dos medias resumidas y razón de varianzas (F).

Lo que cambia respecto del panel viejo: cada prueba informa la DIFERENCIA con
su IC 95 % (el p solo dice si se detectó, el IC dice cuánto), verifica la
normalidad que supone y dice qué usar si no se cumple; la t de una muestra
compara contra el valor que elige el usuario (antes, siempre contra 0).
"""
from __future__ import annotations

import numpy as np
from scipy import stats

from src.core.diagnostic_tests import compare_two_means
from src.core.statistics import (
    f_test_variances, normality_test, ttest_1sample, ttest_ind, ttest_paired,
)
from src.resultado.citas import ficha
from src.resultado.datos import columnas_faltantes, filas_completas, una
from src.resultado.lenguaje import fmt_p, p_token
from src.resultado.modelo import Entrada, Figura, Metodo, Resultado, Supuesto, Valor

# Valores de ejemplo de la calculadora de medias resumidas: los mismos que
# muestra el diálogo (analysis_specs.PARAMETROS) y los que usa el contrato.
EJEMPLOS = {"comparar_medias": {"m1": 5.2, "de1": 1.1, "n1": 30, "m2": 4.6, "de2": 1.3,
                                "n2": 28}}


def _f(x, dec=4) -> str:
    return Valor("", x, decimales=dec).texto()


def _alfa(opciones) -> float:
    try:
        a = float((opciones or {}).get("alpha", 0.05) or 0.05)
    except (TypeError, ValueError):
        a = 0.05
    return a if 0 < a < 1 else 0.05


def _paso_normal(valores, que, alternativa_np) -> Supuesto:
    t = normality_test(valores) if len(valores) >= 3 and np.ptp(valores) > 0 else None
    pregunta = f"¿{que} son normales?"
    if t is None:
        return Supuesto(pregunta, "no evaluable (menos de 3 datos o todos iguales)",
                        "No evaluable", "La t supone normalidad; no se pudo verificar.",
                        ok=False)
    n = len(valores)
    if t["normal"]:
        return Supuesto(pregunta, f"Shapiro-Wilk: {p_token(t['p'])}, n = {n}", "Sí",
                        "La t supone normalidad: se cumple.",
                        alternativa=f"si no lo fueran, convendría {alternativa_np}.")
    grande = n >= 30
    return Supuesto(
        pregunta, f"Shapiro-Wilk: {p_token(t['p'])}, n = {n}", "No",
        ("Con 30 datos o más la t tolera bien el apartamiento (teorema central del límite), "
         f"salvo colas muy largas. Para confirmar, {alternativa_np}." if grande else
         f"Con pocos datos y sin normalidad, la t puede fallar: usá {alternativa_np}."),
        ok=grande)


def _decision(p, alfa, ic, que) -> tuple[str, str]:
    """(respuesta, consecuencia) de la prueba, leída por el IC."""
    if p < alfa:
        return ("Se detectó diferencia",
                f"El IC 95 % de {que} ({_f(ic[0])} a {_f(ic[1])}) no incluye el 0.")
    return ("No se detectó diferencia",
            f"El IC 95 % de {que} ({_f(ic[0])} a {_f(ic[1])}) incluye el 0: con estos datos no "
            "se puede afirmar una diferencia — tampoco descartarla. El ancho del intervalo dice "
            "cuán grande podría ser.")


def _armar(analisis, titulo, entrada, valores, metodo, supuestos, lectura, matiz,
           advertencias=(), figuras=(), crudo=None) -> Resultado:
    f = ficha(analisis)
    return Resultado(analisis=analisis, titulo=titulo, entrada=entrada, valores=valores,
                     metodo=metodo, supuestos=list(supuestos), formula=f.formula,
                     citas=list(f.citas), lectura=lectura, matiz=matiz,
                     advertencias=list(advertencias), figuras=list(figuras), crudo=crudo or {})


_MATIZ_P = ("Que se detecte una diferencia no dice que importe: eso lo dice su tamaño (el IC) "
            "frente a lo que es relevante para el paciente o el analito.")


# ============================================================

def t_una_muestra(df, col, opciones=None) -> Resultado:
    """`opciones["mu"]`: el valor de referencia (antes era siempre 0)."""
    opciones = opciones or {}
    try:
        mu = float(opciones.get("mu", 0.0) or 0.0)
    except (TypeError, ValueError):
        return Resultado.rechazo("t_una_muestra", f"t de una muestra — {col}",
                                 "El valor de referencia tiene que ser un número.")
    alfa = _alfa(opciones)
    titulo = f"t de una muestra — {col} contra {_f(mu)}"
    c = una(df, col)
    if c.motivo:
        return Resultado.rechazo("t_una_muestra", titulo, c.motivo)
    r = ttest_1sample(c.valores, mu=mu)
    if r is None:
        return Resultado.rechazo("t_una_muestra", titulo,
                                 f"Hacen falta al menos 2 datos; hay {c.entrada.n}.", c.entrada)
    falla = Resultado.rechazo_del_core("t_una_muestra", titulo, r, c.entrada)
    if falla is not None:
        return falla
    dif_ic = (r["ci95"][0] - mu, r["ci95"][1] - mu)
    valores = [Valor("n", r["n"]), Valor("Media", r["mean"], ic=r["ci95"]),
               Valor("Valor de referencia (μ₀)", mu),
               Valor("Diferencia (media − μ₀)", r["mean"] - mu, ic=dif_ic),
               Valor("DE", r["sd"]),
               Valor("t", r["t"], nota=f"{r['df']} gl"), Valor("p", fmt_p(r["p"]))]
    respuesta, consecuencia = _decision(r["p"], alfa, dif_ic, "la diferencia")
    supuestos = [
        Supuesto(f"¿La media difiere de {_f(mu)}?",
                 f"t = {_f(r['t'], 3)}, {p_token(r['p'])} (α = {alfa:g})",
                 respuesta, consecuencia),
        _paso_normal(c.valores, "Los datos", "la prueba de Wilcoxon contra el mismo valor"),
    ]
    if mu == 0:
        supuestos.append(Supuesto(
            "¿Contra qué valor se compara?", "μ₀ = 0", "0",
            "Se compara contra 0. Si el valor de referencia es otro (el valor asignado de un "
            "control, un objetivo), cargalo en el diálogo.", ok=True))
    return _armar(
        "t_una_muestra", titulo, c.entrada, valores,
        Metodo("t de Student de una muestra",
               "Compara la media de los datos con un valor fijo: ¿el promedio está donde "
               "tendría que estar?"),
        supuestos,
        (f"La media, {_f(r['mean'])}, " +
         (f"difiere de {_f(mu)} en {_f(r['mean'] - mu)}." if r["p"] < alfa else
          f"no se distingue de {_f(mu)}.")),
        _MATIZ_P,
        figuras=[Figura("Datos y media", lambda: _figura_una(c.valores, r, mu, col))],
        crudo={"t": r, "alpha": alfa})


def t_pareada(df, c1, c2, opciones=None) -> Resultado:
    """Diferencia = Variable 1 − Variable 2, fila por fila."""
    alfa = _alfa(opciones)
    titulo = f"t pareada — {c1} − {c2}"
    falta = columnas_faltantes(df, c1, c2)
    if falta:
        return Resultado.rechazo("t_pareada", titulo, falta)
    if c1 == c2:
        return Resultado.rechazo("t_pareada", titulo, "Elegí dos columnas distintas.")
    pares, entrada = filas_completas(df, c1, c2)
    try:
        x, y = pares[c1].to_numpy(dtype=float), pares[c2].to_numpy(dtype=float)
    except (TypeError, ValueError):
        return Resultado.rechazo("t_pareada", titulo, "Alguna columna tiene texto.", entrada)
    r = ttest_paired(x, y)
    if r is None:
        return Resultado.rechazo("t_pareada", titulo,
                                 f"Hacen falta al menos 2 pares; hay {entrada.n}.", entrada)
    falla = Resultado.rechazo_del_core("t_pareada", titulo, r, entrada)
    if falla is not None:
        return falla
    entrada.n = r["n"]
    valores = [Valor("Pares (n)", r["n"]),
               Valor(f"Media de {c1}", float(np.mean(x))), Valor(f"Media de {c2}", float(np.mean(y))),
               Valor("Diferencia media", r["mean_diff"], ic=r["ci95"],
                     nota=f"diferencia = {c1} − {c2}"),
               Valor("DE de las diferencias", r["sd_diff"]),
               Valor("t", r["t"], nota=f"{r['df']} gl"), Valor("p", fmt_p(r["p"]))]
    respuesta, consecuencia = _decision(r["p"], alfa, r["ci95"], "la diferencia media")
    supuestos = [
        Supuesto("¿Los dos valores de cada fila difieren en promedio?",
                 f"t = {_f(r['t'], 3)}, {p_token(r['p'])} (α = {alfa:g})",
                 respuesta, consecuencia),
        _paso_normal(r["diffs"], "Las diferencias", "Wilcoxon pareado"),
    ]
    return _armar(
        "t_pareada", titulo, entrada, valores,
        Metodo("t de Student pareada",
               "Compara dos mediciones del mismo sujeto: trabaja con la diferencia de cada "
               "fila, así la variación entre sujetos no tapa el efecto."),
        supuestos,
        (f"En promedio, {c1} supera a {c2} en {_f(r['mean_diff'])}" if r["mean_diff"] > 0 else
         f"En promedio, {c1} queda {_f(-r['mean_diff'])} por debajo de {c2}")
        + (" (se detectó diferencia)." if r["p"] < alfa else "; no se detectó diferencia."),
        _MATIZ_P + " Para comparar dos métodos de medición no alcanza: está Bland-Altman.",
        figuras=[Figura("Diferencias", lambda: _figura_diferencias(r["diffs"], r, c1, c2))],
        crudo={"t": r, "alpha": alfa})


def t_independiente(df, c1, c2, opciones=None) -> Resultado:
    """Cada columna es un grupo (Welch: sin suponer varianzas iguales)."""
    alfa = _alfa(opciones)
    titulo = f"t de dos grupos independientes (Welch) — {c1} y {c2}"
    g1, g2 = una(df, c1), una(df, c2)
    for g in (g1, g2):
        if g.motivo:
            return Resultado.rechazo("t_independiente", titulo, g.motivo)
    entrada = Entrada(columnas=(c1, c2), n=g1.entrada.n + g2.entrada.n)
    r = ttest_ind(g1.valores, g2.valores)
    if r is None:
        return Resultado.rechazo("t_independiente", titulo,
                                 "Hacen falta al menos 2 datos en cada grupo.", entrada)
    falla = Resultado.rechazo_del_core("t_independiente", titulo, r, entrada)
    if falla is not None:
        return falla
    valores = [Valor(f"n {c1}", r["n1"]), Valor(f"n {c2}", r["n2"]),
               Valor(f"Media {c1}", r["mean1"]), Valor(f"Media {c2}", r["mean2"]),
               Valor(f"DE {c1}", r["sd1"]), Valor(f"DE {c2}", r["sd2"]),
               Valor("Diferencia de medias", r["diff"], ic=r["ci95"], nota=f"{c1} − {c2}"),
               Valor("t", r["t"], nota=f"{r['df']:.1f} gl (Welch)"), Valor("p", fmt_p(r["p"]))]
    respuesta, consecuencia = _decision(r["p"], alfa, r["ci95"], "la diferencia")
    razon = max(r["sd1"], r["sd2"]) / min(r["sd1"], r["sd2"]) if min(r["sd1"], r["sd2"]) > 0 \
        else np.inf
    supuestos = [
        Supuesto("¿Las medias de los dos grupos difieren?",
                 f"t = {_f(r['t'], 3)}, {p_token(r['p'])} (α = {alfa:g})", respuesta,
                 consecuencia),
        _paso_normal(g1.valores, f"Los datos de {c1}", "Mann-Whitney"),
        _paso_normal(g2.valores, f"Los datos de {c2}", "Mann-Whitney"),
        Supuesto("¿Hace falta que las varianzas sean iguales?",
                 f"razón de DE = {_f(razon, 2)}", "No",
                 "Se usa la t de Welch, que no lo supone: con varianzas iguales rinde igual que "
                 "la de Student, y con distintas no se equivoca (Delacre et al. 2017). Por eso "
                 "no se prueba la igualdad de varianzas antes.", ok=True),
    ]
    return _armar(
        "t_independiente", titulo, entrada, valores,
        Metodo("t de Welch",
               "Compara las medias de dos grupos de sujetos distintos, sin suponer que tienen "
               "la misma dispersión."),
        supuestos,
        (f"La media de {c1} es {_f(r['mean1'])} y la de {c2}, {_f(r['mean2'])}: " +
         (f"difieren en {_f(r['diff'])}." if r["p"] < alfa else
          "no se detectó diferencia.")),
        _MATIZ_P,
        figuras=[Figura("Grupos", lambda: _figura_grupos(
            [g1.valores, g2.valores], [c1, c2]))],
        crudo={"t": r, "alpha": alfa})


def comparar_medias(opciones) -> Resultado:
    """Calculadora: dos medias con su DE y su n, sin los datos (Welch)."""
    titulo = "Comparar dos medias (datos resumidos)"
    try:
        m1, de1, n1, m2, de2, n2 = (float(opciones[k]) for k in
                                    ("m1", "de1", "n1", "m2", "de2", "n2"))
    except KeyError as e:
        return Resultado.rechazo("comparar_medias", titulo, f"Falta el dato {e.args[0]}.")
    except (TypeError, ValueError):
        return Resultado.rechazo("comparar_medias", titulo, "Los seis datos tienen que ser números.")
    if n1 != int(n1) or n2 != int(n2):
        return Resultado.rechazo("comparar_medias", titulo, "Los n tienen que ser enteros.")
    r = compare_two_means(m1, de1, int(n1), m2, de2, int(n2))
    falla = Resultado.rechazo_del_core("comparar_medias", titulo, r)
    if falla is not None:
        return falla
    valores = [Valor("Grupo 1", f"media {_f(m1)}, DE {_f(de1)}, n = {int(n1)}"),
               Valor("Grupo 2", f"media {_f(m2)}, DE {_f(de2)}, n = {int(n2)}"),
               Valor("Diferencia (1 − 2)", r["diff"], ic=r["ci95"]),
               Valor("t", r["t"], nota=f"{r['df']:.1f} gl (Welch)"), Valor("p", fmt_p(r["p"]))]
    respuesta, consecuencia = _decision(r["p"], 0.05, r["ci95"], "la diferencia")
    supuestos = [
        Supuesto("¿Las medias difieren?", f"t = {_f(r['t'], 3)}, {p_token(r['p'])}",
                 respuesta, consecuencia),
        Supuesto("¿Se puede verificar la normalidad?", "solo hay medias, DE y n", "No",
                 "Sin los datos no hay forma de ver la forma de la distribución: el resultado "
                 "vale si cada grupo es aproximadamente normal o tiene 30 o más sujetos.",
                 ok=False),
    ]
    return _armar(
        "comparar_medias", titulo, None, valores,
        Metodo("t de Welch con datos resumidos",
               "La misma t de dos grupos, cuando solo se tienen la media, la DE y el n de "
               "cada uno (por ejemplo, de un trabajo publicado)."),
        supuestos,
        (f"La diferencia es {_f(r['diff'])} (IC 95 % {_f(r['ci95'][0])} a {_f(r['ci95'][1])}): "
         + ("se detectó." if r["p"] < 0.05 else "no se detectó.")),
        _MATIZ_P, crudo={"comparacion": r})


def f_varianzas(df, c1, c2, opciones=None) -> Resultado:
    titulo = f"Razón de varianzas (F) — {c1} y {c2}"
    g1, g2 = una(df, c1), una(df, c2)
    for g in (g1, g2):
        if g.motivo:
            return Resultado.rechazo("f_varianzas", titulo, g.motivo)
    entrada = Entrada(columnas=(c1, c2), n=g1.entrada.n + g2.entrada.n)
    r = f_test_variances(g1.valores, g2.valores)
    if r is None:
        return Resultado.rechazo("f_varianzas", titulo,
                                 "Hacen falta al menos 3 datos en cada grupo.", entrada)
    falla = Resultado.rechazo_del_core("f_varianzas", titulo, r, entrada)
    if falla is not None:
        return falla
    bf = stats.levene(g1.valores, g2.valores, center="median")
    valores = [Valor(f"DE {c1}", r["sd1"]), Valor(f"DE {c2}", r["sd2"]),
               Valor("F (mayor / menor)", r["f"], nota=f"{r['df1']} y {r['df2']} gl"),
               Valor("p (F)", fmt_p(r["p"])),
               Valor("p (Brown-Forsythe)", fmt_p(bf.pvalue),
                     nota="no supone normalidad")]
    difiere = r["p"] < 0.05
    no_normales = [c for c, g in ((c1, g1), (c2, g2))
                   if (t := normality_test(g.valores)) is not None and not t["normal"]]
    supuestos = [
        Supuesto("¿Las varianzas difieren?", f"F = {_f(r['f'], 3)}, {p_token(r['p'])}",
                 "Se detectó diferencia" if difiere else "No se detectó diferencia",
                 ("Una de las dos dispersiones es mayor de lo que explica el azar." if difiere
                  else "Con estos datos no se puede afirmar que las dispersiones difieran.")),
        Supuesto("¿Los dos grupos son normales?",
                 "Shapiro-Wilk en cada grupo",
                 "Sí" if not no_normales else "No: " + ", ".join(no_normales),
                 ("La F vale." if not no_normales else
                  "La F es muy sensible a la falta de normalidad: puede detectar «diferencias» "
                  "que son colas largas. Mirá la prueba de Brown-Forsythe, que no la supone."),
                 ok=not no_normales),
    ]
    return _armar(
        "f_varianzas", titulo, entrada, valores,
        Metodo("Prueba F de razón de varianzas, con Brown-Forsythe al lado",
               "Compara las dispersiones de dos grupos. En el laboratorio: ¿un método es más "
               "impreciso que otro con el mismo material?"),
        supuestos,
        (f"La DE de {c1} es {_f(r['sd1'])} y la de {c2}, {_f(r['sd2'])}: "
         + ("se detectó que difieren." if difiere else "no se detectó que difieran.")),
        ("Para elegir entre la t de Student y la de Welch no hace falta esta prueba: la de "
         "Welch vale en los dos casos."),
        figuras=[Figura("Grupos", lambda: _figura_grupos([g1.valores, g2.valores], [c1, c2]))],
        crudo={"f": r, "brown_forsythe": {"w": float(bf.statistic), "p": float(bf.pvalue)}})


# ============================================================
#  Figuras
# ============================================================

def _figura_una(v, r, mu, col):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4.5))
    rng = np.random.default_rng(0)
    ax.scatter(v, rng.uniform(-0.2, 0.2, len(v)), alpha=0.5, c='#4f6ef7', edgecolors='white', s=40)
    ax.errorbar([r["mean"]], [0.55], xerr=[[r["mean"] - r["ci95"][0]], [r["ci95"][1] - r["mean"]]],
                fmt='o', color='#2c3650', capsize=6, label="Media e IC 95 %")
    ax.axvline(mu, color='#ef4444', ls='--', lw=1.5, label=f"μ₀ = {mu:g}")
    ax.set_yticks([])
    ax.set_ylim(-0.6, 1)
    ax.set_xlabel(str(col))
    ax.set_title(f"{col}: datos y media contra el valor de referencia", fontweight='bold')
    ax.legend(framealpha=0.9)
    fig.tight_layout()
    return fig


def _figura_diferencias(d, r, c1, c2):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4.5))
    rng = np.random.default_rng(0)
    ax.scatter(d, rng.uniform(-0.2, 0.2, len(d)), alpha=0.5, c='#4f6ef7', edgecolors='white', s=40)
    m = r["mean_diff"]
    ax.errorbar([m], [0.55], xerr=[[m - r["ci95"][0]], [r["ci95"][1] - m]], fmt='o',
                color='#2c3650', capsize=6, label="Diferencia media e IC 95 %")
    ax.axvline(0, color='#ef4444', ls='--', lw=1.5, label="Sin diferencia")
    ax.set_yticks([])
    ax.set_ylim(-0.6, 1)
    ax.set_xlabel(f"{c1} − {c2}")
    ax.set_title("Diferencia de cada fila", fontweight='bold')
    ax.legend(framealpha=0.9)
    fig.tight_layout()
    return fig


def _figura_grupos(grupos, nombres):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 5.5))
    ax.boxplot(grupos, widths=0.45, showfliers=False)
    rng = np.random.default_rng(0)
    for i, g in enumerate(grupos, start=1):
        ax.scatter(i + rng.uniform(-0.12, 0.12, len(g)), g, alpha=0.5, c='#4f6ef7',
                   edgecolors='white', s=35, zorder=3)
        ax.plot([i - 0.25, i + 0.25], [np.mean(g)] * 2, color='#ef4444', lw=2)
    ax.set_xticks(range(1, len(nombres) + 1), [str(n) for n in nombres])
    ax.set_title("Cada punto es un dato; la línea roja, la media", fontweight='bold')
    fig.tight_layout()
    return fig
