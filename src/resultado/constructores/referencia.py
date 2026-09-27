"""Valores de referencia: el intervalo de EP28-A3c y los intervalos por edad.

Los números salen de `src/core/reference.py`. Cambian a propósito, cada uno con
su test:

- El intervalo de referencia revisa los extremos con la regla de Dixon (la que
  cita EP28) y, si se cargan los límites de un intervalo publicado, lo verifica
  con la regla de transferencia de EP28: 20 sujetos, hasta 2 afuera. Su IC es
  del 90 % y el informe lo dice (antes la tabla no rotulaba el nivel).
- Los intervalos por edad salen por defecto de centiles por regresión (Altman
  1993): media y DE como funciones de la edad, con todos los datos juntos.
  Antes eran grupos de ancho fijo con los percentiles 5 y 95 lineales, un
  intervalo del 90 % con otra regla de rangos que el de EP28. Los grupos siguen
  como opción, con los percentiles 2,5 y 97,5 de EP28.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.core.reference import (
    N_MINIMO_EP28, age_related_reference, centiles_por_edad, dixon_reed, reference_interval,
    verificar_intervalo,
)
from src.resultado.citas import ficha
from src.resultado.datos import columnas_faltantes, filas_completas, una
from src.resultado.lenguaje import num, p_token
from src.resultado.modelo import Figura, Metodo, Resultado, Supuesto, Valor

MIN_REFERENCIA = 20      # lo que pide EP28 para verificar; para establecer, 120
FILAS_TABLA_EDAD = 7


def _armar(analisis, titulo, entrada, valores, metodo, supuestos, lectura, matiz,
           advertencias=(), figuras=(), crudo=None) -> Resultado:
    f = ficha(analisis)
    return Resultado(analisis=analisis, titulo=titulo, entrada=entrada, valores=valores,
                     metodo=metodo, supuestos=list(supuestos), formula=f.formula,
                     citas=list(f.citas), lectura=lectura, matiz=matiz,
                     advertencias=list(advertencias), figuras=list(figuras), crudo=crudo or {})


def _supuesto_n(n, que="el intervalo") -> Supuesto:
    ok = n >= N_MINIMO_EP28
    return Supuesto(
        f"¿Alcanza n para establecer {que} (EP28 pide {N_MINIMO_EP28})?", f"n = {n}",
        "Sí" if ok else "No",
        ("Los límites y su IC 90 % son los que define la norma." if ok else
         f"Con menos de {N_MINIMO_EP28} cada límite depende de pocos datos: sirve para "
         "explorar o para verificar un intervalo publicado (con 20 alcanza), no para "
         "establecer uno propio en una acreditación."), ok=ok)


# ============================================================
#  Intervalo de referencia (EP28-A3c)
# ============================================================

def intervalo_referencia(df, col, opciones=None) -> Resultado:
    """Una columna con los valores de los sujetos de referencia.

    `opciones["inferior"]`, `opciones["superior"]`: los límites de un intervalo
    publicado para verificar (None = no se declaró).
    """
    opciones = opciones or {}
    titulo = f"Intervalo de referencia — {col}"
    c = una(df, col)
    if c.motivo:
        return Resultado.rechazo("intervalo_referencia", titulo, c.motivo)
    x, entrada = c.valores, c.entrada
    if len(x) < MIN_REFERENCIA:
        return Resultado.rechazo("intervalo_referencia", titulo,
                                 f"Hacen falta al menos {MIN_REFERENCIA} datos; hay {len(x)}.",
                                 entrada)
    ri = reference_interval(x)
    falla = Resultado.rechazo_del_core("intervalo_referencia", titulo, ri, entrada)
    if falla is not None:
        return falla
    con_ic = ri["rangos_ic"] is not None
    a, b = ri["rangos_ic"] if con_ic else (None, None)
    n = ri["n"]
    valores = [
        Valor("n", n), Valor("Mediana", float(np.median(x))),
        Valor("Límite inferior (percentil 2,5)", ri["lower"],
              ic=(ri["ci_lower_low"], ri["ci_lower_high"]) if con_ic else None, nivel_ic="90 %",
              nota=f"IC por rangos {a} y {b} (EP28, tabla 8)" if con_ic else
              f"sin IC: EP28 lo da desde n = 119"),
        Valor("Límite superior (percentil 97,5)", ri["upper"],
              ic=(ri["ci_upper_low"], ri["ci_upper_high"]) if con_ic else None, nivel_ic="90 %",
              nota=f"IC por rangos {n + 1 - b} y {n + 1 - a}" if con_ic else ""),
    ]
    dx = dixon_reed(x)
    sospechosos = [(lado, d) for lado, d in (("bajo", dx["bajo"]), ("alto", dx["alto"]))
                   if d is not None and d["sospechoso"]]
    supuestos = [
        _supuesto_n(n),
        Supuesto(
            "¿Hay extremos sospechosos (Dixon: D/R > 1/3)?",
            ("; ".join(f"el más {lado}, {num(d['valor'])}: D/R = {d['d_r']:.2f}"
                       for lado, d in (("bajo", dx["bajo"]), ("alto", dx["alto"])))
             if dx["bajo"] is not None else "todos los datos iguales"),
            ("Sí: " + " y ".join(f"el más {lado} ({num(d['valor'])})" for lado, d in sospechosos)
             if sospechosos else "No"),
            ("EP28 pide revisar ese dato (¿un error preanalítico, un sujeto que no es sano?) y "
             "sacarlo solo con un motivo; después, repetir el análisis. Un solo extremo mueve el "
             "límite de su lado." if sospechosos else
             "Ningún extremo se separa del resto más de un tercio del rango. Con dos atípicos "
             "del mismo lado la regla no los ve: mirá el histograma."),
            ok=not sospechosos),
    ]
    advertencias = [a for a in ri["avisos"] if "se apoya en" in a]
    lectura = f"El 95 % central de estos sujetos va de {num(ri['lower'])} a {num(ri['upper'])}."
    verif = None
    li, ls = opciones.get("inferior"), opciones.get("superior")
    if li is not None or ls is not None:
        verif = verificar_intervalo(x, li, ls)
        falla = Resultado.rechazo_del_core("intervalo_referencia", titulo, verif, entrada)
        if falla is not None:
            return falla
        publicado = f"{num(li) if li is not None else '—'} a {num(ls) if ls is not None else '—'}"
        valores += [Valor("Intervalo publicado", publicado),
                    Valor("Fuera del publicado", verif["fuera"],
                          nota=f"{verif['debajo']} debajo, {verif['encima']} encima; "
                               f"la regla permite {verif['permitidos']}")]
        regla = ("EP28: con 20 sujetos, hasta 2 afuera." if n == 20 else
                 f"EP28 la define con 20 sujetos (hasta 2 afuera); con {n} se aplicó la misma "
                 f"proporción, hasta el 10 %: {verif['permitidos']}.")
        supuestos.append(Supuesto(
            "¿Se verifica el intervalo publicado?",
            f"{verif['fuera']} de {n} afuera. {regla}",
            "Se verifica" if verif["verificado"] else "No se verifica",
            ("El intervalo publicado vale para tu población y tu método: se puede adoptar." if
             verif["verificado"] else
             "EP28: medí otros 20 sujetos; si vuelven a caer 3 o más afuera, el intervalo "
             "publicado no corresponde a tu población o a tu método y hay que establecer uno "
             "propio (120 sujetos)."), ok=verif["verificado"]))
        lectura += (f" El intervalo publicado ({publicado}) "
                    + ("se verifica" if verif["verificado"] else "no se verifica")
                    + f": {verif['fuera']} de {n} quedan afuera.")
    return _armar(
        "intervalo_referencia", titulo, entrada, valores,
        Metodo("No paramétrico de EP28-A3c",
               "Los percentiles 2,5 y 97,5 de los sujetos de referencia, sin suponer ninguna "
               "distribución; cada límite con su IC 90 % por rangos de orden."),
        supuestos, lectura,
        "Un intervalo de referencia describe al 95 % central de los sanos medidos: por "
        "definición, 1 de cada 20 sanos cae afuera. Vale para la población y el método con que "
        "se midió, y los sujetos tienen que ser de referencia (los criterios de inclusión de "
        "EP28), cosa que el cálculo no puede verificar.",
        advertencias,
        [Figura("Distribución con los límites",
                lambda: _figura_intervalo(x, ri, li, ls, col))],
        crudo={"referencia": ri, "dixon": dx, "verificacion": verif})


# ============================================================
#  Intervalos por edad
# ============================================================

def _edades_tabla(e_min, e_max):
    edades = np.linspace(e_min, e_max, FILAS_TABLA_EDAD)
    return np.unique(np.round(edades, 0 if e_max - e_min >= 10 else 1))


def intervalos_por_edad(df, edad, valor, opciones=None) -> Resultado:
    """Variable 1 = edad, Variable 2 = el valor medido.

    `opciones["metodo"]`: "regresion" (centiles de Altman 1993, por defecto) o
    "grupos" (grupos de edad de ancho fijo, percentiles de EP28 en cada uno).
    `opciones["escala"]`: "lineal" | "log" (solo regresión).
    """
    opciones = opciones or {}
    metodo = opciones.get("metodo", "regresion")
    escala = opciones.get("escala", "lineal")
    titulo = f"Intervalos por edad — {valor} según {edad}"
    falta = columnas_faltantes(df, edad, valor)
    if falta:
        return Resultado.rechazo("intervalos_edad", titulo, falta)
    if edad == valor:
        return Resultado.rechazo("intervalos_edad", titulo, "La edad y el valor son la misma "
                                                            "columna.")
    filas, entrada = filas_completas(df, edad, valor)
    e = pd.to_numeric(filas[edad], errors="coerce")
    y = pd.to_numeric(filas[valor], errors="coerce")
    if e.isna().any() or y.isna().any():
        return Resultado.rechazo("intervalos_edad", titulo,
                                 "La edad y el valor tienen que ser números.", entrada)
    e, y = e.to_numpy(dtype=float), y.to_numpy(dtype=float)
    if len(y) < MIN_REFERENCIA:
        return Resultado.rechazo("intervalos_edad", titulo,
                                 f"Hacen falta al menos {MIN_REFERENCIA} sujetos; hay {len(y)}.",
                                 entrada)
    if metodo == "grupos":
        return _por_grupos(e, y, edad, valor, titulo, entrada)
    c = centiles_por_edad(e, y, escala=escala)
    falla = Resultado.rechazo_del_core("intervalos_edad", titulo, c, entrada)
    if falla is not None:
        return falla
    edades = _edades_tabla(c["edad_min"], c["edad_max"])
    lo, me, hi = c["centiles"](edades)
    valores = [Valor("n", c["n"]),
               Valor("Media según la edad", f"polinomio de grado {c['grado']}"),
               Valor("DE según la edad", "cambia en línea recta con la edad" if c["sd_lineal"]
                     else "constante")]
    valores += [Valor(f"Edad {num(a)}", f"{num(l)} a {num(h)}", nota=f"mediana {num(m)}")
                for a, l, m, h in zip(edades, lo, me, hi)]
    normales = not (c["shapiro_p"] < 0.05)
    supuestos = [
        Supuesto(
            "¿La media cambia en curva con la edad?",
            f"término de grado {c['grado']}: {p_token(c['p_grado'])}",
            {1: "No: en línea recta", 2: "Sí: una curva (cuadrática)",
             3: "Sí: una curva con dos codos (cúbica)"}[c["grado"]],
            "Se ajusta hasta grado 3 y se baja mientras el término más alto no aporte "
            "(p ≥ 0,05): la curva más simple que siguen los datos."),
        Supuesto(
            "¿La dispersión cambia con la edad?",
            f"pendiente de los residuos absolutos: {p_token(c['p_sd'])}",
            "Sí" if c["sd_lineal"] else "No",
            ("La DE se modela como una recta de la edad: los centiles se abren o se cierran "
             "con ella." if c["sd_lineal"] else
             "Se usa una sola DE para todas las edades.")),
        Supuesto(
            "¿Los desvíos estandarizados son normales?",
            f"Shapiro-Wilk {p_token(c['shapiro_p'])}; afuera de los centiles quedan "
            f"{100 * c['fuera']:.1f} % (se esperan 5 %)",
            "Sí" if normales else "No",
            ("Los centiles 2,5 y 97,5 cubren lo que dicen." if normales else
             "Los centiles suponen desvíos normales y estos no lo son: los extremos no cubren "
             "el 95 %." + (" Probá la escala log (analitos con cola a la derecha)."
                          if escala == "lineal" else " Mirá los datos en el gráfico.")),
            alternativa="en escala log, si todos los valores son positivos." if escala == "lineal"
            else "", ok=normales),
        _supuesto_n(c["n"], "los centiles"),
    ]
    return _armar(
        "intervalos_edad", titulo, entrada, valores,
        Metodo("Centiles por regresión (Altman 1993)" + (", escala log" if escala == "log" else ""),
               "La media y la DE del valor como funciones continuas de la edad, con todos los "
               "sujetos juntos; los centiles 2,5 y 97,5 son media ± 1,96·DE a cada edad."),
        supuestos,
        f"A los {num(edades[0])} el intervalo va de {num(lo[0])} a {num(hi[0])}; a los "
        f"{num(edades[-1])}, de {num(lo[-1])} a {num(hi[-1])}.",
        "Los centiles valen en el rango de edades medido: no se extrapolan. El modelo supone "
        "que los desvíos alrededor de la media son normales a toda edad; un cambio brusco (la "
        "pubertad, la menopausia) lo suaviza, y ahí conviene partir por grupos.",
        figuras=[Figura("Centiles 2,5, 50 y 97,5 según la edad",
                        lambda: _figura_centiles(e, y, c, edad, valor))],
        crudo={"centiles": c, "edades": edades})


def _por_grupos(e, y, edad, valor, titulo, entrada) -> Resultado:
    r = age_related_reference(e, y)
    grupos = r["groups"]
    valores = [Valor("n", r["n_total"]), Valor("Grupos", len(grupos))]
    for g in grupos:
        rango = (f"{num(g['p2_5'])} a {num(g['p97_5'])}" if np.isfinite(g["p2_5"])
                 else "sin percentiles 2,5 y 97,5")
        valores.append(Valor(f"Edad {g['age_group']}", rango,
                             nota=f"n = {g['n']}, mediana {num(g['median'])}"))
    chicos = [g for g in grupos if g["n"] < N_MINIMO_EP28]
    sin_limites = [g for g in grupos if not np.isfinite(g["p2_5"])]
    supuestos = [Supuesto(
        f"¿Cada grupo tiene los {N_MINIMO_EP28} sujetos de EP28?",
        f"el más chico tiene {min(g['n'] for g in grupos)}; {len(chicos)} de {len(grupos)} "
        f"grupos por debajo",
        "Sí" if not chicos else "No",
        ("Cada grupo tiene su intervalo con el n de la norma." if not chicos else
         "Con menos de 120 por grupo los límites dependen de pocos datos"
         + (f", y con menos de 39 no hay percentil 2,5 ({len(sin_limites)} grupo(s))"
            if sin_limites else "")
         + ". Con pocos datos por grupo, los centiles por regresión usan todos juntos."),
        alternativa="por regresión (Altman 1993), la opción por defecto.", ok=not chicos)]
    return _armar(
        "intervalos_edad", titulo, entrada, valores,
        Metodo("Percentiles de EP28 por grupos de edad",
               "Diez grupos de edad del mismo ancho; en cada uno, los percentiles 2,5 y 97,5 "
               "con el rango p(n + 1) de EP28."),
        supuestos,
        f"{len(grupos)} grupos de edad; {len(grupos) - len(sin_limites)} con intervalo "
        "estimable.",
        "Los grupos son de ancho fijo y no siguen cortes clínicos; si el analito cambia en una "
        "edad conocida, los cortes deberían ir ahí (EP28, partición). Los saltos entre grupos "
        "vecinos son en parte ruido.",
        figuras=[Figura("Límites por grupo de edad",
                        lambda: _figura_grupos(e, y, grupos, edad, valor))],
        crudo={"grupos": r})


# ============================================================
#  Figuras
# ============================================================

def _figura_intervalo(x, ri, li, ls, col):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 5))
    from src.utils.histograma import barras

    ax.hist(x, bins=barras(x, min(40, max(10, len(x) // 8))), color='#c7d2fe',
            edgecolor='#4f6ef7')
    for lim, lo, hi in ((ri["lower"], ri["ci_lower_low"], ri["ci_lower_high"]),
                        (ri["upper"], ri["ci_upper_low"], ri["ci_upper_high"])):
        ax.axvline(lim, color='#ef4444', lw=2)
        if np.isfinite(lo) and np.isfinite(hi):
            ax.axvspan(lo, hi, color='#ef4444', alpha=0.12)
    for lim in (li, ls):
        if lim is not None:
            ax.axvline(lim, color='#111827', ls='--', lw=1.5)
    ax.set_xlabel(col)
    ax.set_ylabel("Sujetos")
    ax.set_title("Límites de referencia (rojo, con su IC 90 %)"
                 + (" y publicados (negro)" if li is not None or ls is not None else ""),
                 fontweight='bold')
    fig.tight_layout()
    return fig


def _figura_centiles(e, y, c, edad, valor):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(e, y, s=10, color='#4f6ef7', alpha=0.4)
    grilla = np.linspace(c["edad_min"], c["edad_max"], 200)
    lo, me, hi = c["centiles"](grilla)
    ax.plot(grilla, me, color='#111827', lw=2, label="Mediana")
    ax.plot(grilla, lo, color='#ef4444', lw=2, label="Centiles 2,5 y 97,5")
    ax.plot(grilla, hi, color='#ef4444', lw=2)
    ax.set_xlabel(edad)
    ax.set_ylabel(valor)
    if c["escala"] == "log":
        ax.set_yscale('log')
    ax.set_title("Intervalo de referencia según la edad", fontweight='bold')
    ax.legend(framealpha=0.9)
    fig.tight_layout()
    return fig


def _figura_grupos(e, y, grupos, edad, valor):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(e, y, s=10, color='#4f6ef7', alpha=0.4)
    for g in grupos:
        for clave, color in (("p2_5", '#ef4444'), ("median", '#111827'), ("p97_5", '#ef4444')):
            if np.isfinite(g[clave]):
                ax.hlines(g[clave], g["desde"], g["hasta"], color=color, lw=2)
    ax.set_xlabel(edad)
    ax.set_ylabel(valor)
    ax.set_title("Percentiles 2,5, 50 y 97,5 por grupo de edad", fontweight='bold')
    fig.tight_layout()
    return fig
