"""Comparación de métodos (CLSI EP09): el primer ciclo de «MedCalc pero guiado».

La familia de validación completa: Bland-Altman (con el CCC), Passing-Bablok,
Deming (con y sin ponderar), imprecisión desde duplicados, ICC y Bland-Altman
de varios métodos contra una referencia.
"""
from __future__ import annotations

import numpy as np

from src.core.agreement import (
    cv_duplicados as cv_duplicados_core, deming_ponderado as deming_ponderado_core,
    deming_regression as deming_regression_core, intraclass_correlation,
)
from src.core.bland_altman import (
    CV_CONSTANTE, DE_CONSTANTE, bland_altman_analysis, concordance_correlation,
    variabilidad_diferencias,
)
from src.core.passing_bablok import N_RECOMENDADO, passing_bablok as passing_bablok_core
from src.resultado.citas import ficha
from src.resultado.datos import columnas_faltantes, filas_completas
from src.resultado.lenguaje import (
    donde_falla_ccc, fmt_p, p_token, pendiente_concluyente, texto_descartes,
)
from src.resultado.modelo import Entrada, Figura, Metodo, Resultado, Supuesto, Valor

PARAMETRICO = "parametrico"
NO_PARAMETRICO = "no_parametrico"

_LIMITES = {
    PARAMETRICO: ("Límites de acuerdo (± 1,96·DE)", "Sesgo (media de las diferencias)"),
    NO_PARAMETRICO: ("Límites de acuerdo (percentiles 2,5 y 97,5)",
                     "Sesgo (mediana de las diferencias)"),
}


def _f(x) -> str:
    """Una cifra de un paso, con el mismo formato que en la tabla: si el mismo
    número sale -0.0706 arriba y -0.07062 abajo, parecen dos números."""
    return Valor("", x).texto()


def _fic(ic) -> str:
    return Valor("", 0, ic=ic).texto_ic() or "—"


def _nombre_modo(modo: str) -> str:
    return "paramétrico" if modo == PARAMETRICO else "no paramétrico"


def _detecta_pendiente(pendiente: dict | None) -> bool | None:
    """True si el IC 95 % de la pendiente excluye el 0; None si no hay IC.

    Misma regla que `omni_analyzer._detecta_pendiente`: se decide por el
    intervalo y no por el p, así un IC no finito cuenta como «no evaluable» en
    vez de propagar una comparación contra NaN en silencio.
    """
    if not pendiente:
        return None
    lo, hi = pendiente.get("ci", (np.nan, np.nan))
    if not (np.isfinite(lo) and np.isfinite(hi)):
        return None
    return bool(lo > 0 or hi < 0)


def bland_altman(df, c1, c2, opciones=None) -> Resultado:
    """Bland-Altman con las tres variantes que admite el método, más el CCC.

    `opciones` (de `analysis_specs.OPCIONES`):
      limites:    "auto" | "parametrico" | "no_parametrico"
      referencia: "promedio" | "x" | "y"
      escala:     "auto" | "unidades" | "porcentaje"

    La resta es candidato − referencia cuando se declara una (CLSI EP09c,
    tabla 1); sin referencia, Variable 1 − Variable 2. Antes era siempre
    Variable 1 − Variable 2, aunque la referencia fuera la Variable 1.

    La escala la decide la variabilidad de las diferencias (EP09c §5.4): si la
    dispersión crece con la concentración y en % queda pareja (CV constante),
    las diferencias van en porcentaje; si no, en unidades.

    El eje X importa más de lo que parece: si uno de los dos métodos es de
    referencia o un valor asignado, graficar y regresar contra el promedio mete
    la referencia en los dos ejes y distorsiona la pendiente de las diferencias
    (Krouwer JS, 2008, Stat Med 27:778-780; CLSI EP09).

    El programa no dictamina «concordantes»: el límite tolerable lo pone el
    requisito de calidad del analito. Informa el margen y deja la decisión a
    quien sabe qué diferencia cambia una conducta.
    """
    opciones = opciones or {}
    modo = opciones.get("limites", "auto")
    eje = opciones.get("referencia", "promedio")
    escala_pedida = opciones.get("escala", "auto")
    nombre_eje = {"x": c1, "y": c2}.get(eje)
    # (candidato, comparativo): d = candidato − comparativo.
    cand, comp = (c2, c1) if eje == "x" else (c1, c2)
    referencia = "y" if nombre_eje else None

    titulo_base = f"Bland-Altman — {c1} vs {c2}"
    falta = columnas_faltantes(df, c1, c2)
    if falta:
        return Resultado.rechazo("bland_altman", titulo_base, falta)

    pares, entrada = filas_completas(df, c1, c2)
    x1, x2 = pares[c1].to_numpy(dtype=float), pares[c2].to_numpy(dtype=float)
    y_cand, x_comp = pares[cand].to_numpy(dtype=float), pares[comp].to_numpy(dtype=float)
    res = bland_altman_analysis(y_cand, x_comp, reference=referencia)
    rechazo = Resultado.rechazo_del_core("bland_altman", titulo_base, res, entrada)
    if rechazo is not None:
        return rechazo

    # La variabilidad se mide en unidades, sobre el mismo eje del gráfico.
    var = variabilidad_diferencias(res["x_axis"], res["diffs"])
    if escala_pedida == "auto":
        escala = "porcentaje" if var["clase"] == CV_CONSTANTE else "unidades"
    else:
        escala = escala_pedida
    if escala == "porcentaje":
        res = bland_altman_analysis(y_cand, x_comp, reference=referencia, escala="porcentaje")
        rechazo = Resultado.rechazo_del_core("bland_altman", titulo_base, res, entrada)
        if rechazo is not None:
            return rechazo
    en_pct = escala == "porcentaje"
    u = "%" if en_pct else ""

    advertencias = []
    if res["n"] < entrada.n:
        advertencias.append(
            f"Se descartaron {entrada.n - res['n']} pares con valores no finitos (±∞).")
    entrada.n = res["n"]

    # En automático decide la normalidad de las DIFERENCIAS, no la de los datos
    # crudos. Si Shapiro no se pudo correr, se cae a paramétrico y se dice.
    normales = res["normal_diffs"]
    automatico = PARAMETRICO if normales in (True, None) else NO_PARAMETRICO
    elegido = automatico if modo == "auto" else modo
    rotulo_lim, rotulo_centro = _LIMITES[elegido]

    if elegido == PARAMETRICO:
        lim_inf, lim_sup = res["loa_lower"], res["loa_upper"]
        centro = res["mean_difference"]
        ic_centro, ic_sup, ic_inf = res["ci_mean"], res["ci_upper"], res["ci_lower"]
    else:
        lim_inf, lim_sup = res["loa_np_lower"], res["loa_np_upper"]
        centro = float(np.median(res["diffs"]))
        ic_centro = ic_sup = ic_inf = None

    pend_prom = res["slope_vs_mean"]
    pend_ref = res.get("slope_vs_reference")

    medias = {cand: res["mean_method1"], comp: res["mean_method2"]}
    valores = [
        Valor(f"Media {c1}", medias[c1]),
        Valor(f"Media {c2}", medias[c2]),
        Valor(rotulo_centro, centro, ic=ic_centro, unidad=u,
              nota=f"diferencia = {cand} − {comp}"),
    ]
    if not en_pct:
        # En porcentaje el sesgo ya ES el sesgo %: repetirlo sería el mismo número.
        valores.append(Valor("Sesgo %", res["bias_pct"], decimales=2, unidad="%",
                             nota=f"sobre {nombre_eje}" if nombre_eje
                             else "sobre el promedio de los dos métodos"))
    valores += [
        Valor("DE de las diferencias", res["sd_difference"], unidad=u),
        Valor(f"{rotulo_lim} — superior", lim_sup, ic=ic_sup, unidad=u),
        Valor(f"{rotulo_lim} — inferior", lim_inf, ic=ic_inf, unidad=u),
        Valor("Pendiente contra el promedio", pend_prom["slope"], ic=pend_prom["ci"],
              nota=f"({p_token(pend_prom['p'])})"),
    ]
    if pend_ref is not None:
        valores.append(Valor(f"Pendiente contra {nombre_eje} (referencia)",
                             pend_ref["slope"], ic=pend_ref["ci"],
                             nota=f"({p_token(pend_ref['p'])})"))

    supuestos = [
        _supuesto_variabilidad(var, escala_pedida, escala, nombre_eje or "el promedio"),
        _supuesto_normalidad(res, modo, elegido, automatico),
        _supuesto_referencia(nombre_eje),
        _supuesto_proporcional(pend_ref if pend_ref is not None else pend_prom,
                               nombre_eje or "el promedio"),
    ]
    if elegido == PARAMETRICO and normales is False:
        advertencias.append("Las diferencias no son normales: estos límites paramétricos "
                            "no son los que corresponden. Los no paramétricos no exigen "
                            "normalidad.")
    if pend_ref is not None:
        det_prom, det_ref = _detecta_pendiente(pend_prom), _detecta_pendiente(pend_ref)
        if None not in (det_prom, det_ref) and det_prom != det_ref:
            advertencias.append(
                "Contra el promedio y contra la referencia la pendiente no concluye lo "
                "mismo. Vale la de la referencia: el promedio pone el ruido del método "
                "en prueba de los dos lados de la cuenta, y eso puede inventar un desvío "
                "proporcional que no existe o esconder uno que sí (Krouwer 2008).")

    # El CCC resume el acuerdo en una cifra y la parte en precisión × veracidad.
    ccc = concordance_correlation(x1, x2)
    matiz = ("El programa no sabe qué diferencia tolera este analito: el límite tolerable "
             "lo fija el requisito de calidad del analito, no el programa.")
    figuras = [Figura("Bland-Altman", lambda: _figura_bland(
        res, centro, lim_inf, lim_sup, rotulo_centro, elegido, cand, comp, nombre_eje))]
    if ccc.get("error"):
        advertencias.append(f"No se pudo calcular el CCC de Lin: {ccc['error']}")
    else:
        valores.extend(_valores_ccc(ccc))
        supuestos.append(_supuesto_ccc(ccc))
        matiz += (" Y un CCC alto tampoco prueba que sean intercambiables: sube con el "
                  "rango de concentraciones aunque las diferencias no cambien.")
        if all(np.isfinite(ccc[k]) for k in ("ccc", "rho", "cb")):
            figuras.append(Figura("CCC de Lin descompuesto",
                                  lambda: _figura_ccc(ccc, c1, c2)))

    nombre_modo = _nombre_modo(elegido)
    titulo_eje = f" · eje X = {nombre_eje} (Krouwer)" if nombre_eje else ""
    titulo_eje += " · en %" if en_pct else ""
    f = ficha("bland_altman")
    return Resultado(
        analisis="bland_altman",
        titulo=f"Bland-Altman {nombre_modo}{titulo_eje} — {c1} vs {c2}",
        entrada=entrada,
        valores=valores,
        metodo=Metodo(
            f"Bland-Altman {nombre_modo}",
            "Mide cuánto difieren los dos métodos en el mismo paciente: el sesgo es "
            "la diferencia típica y los límites de acuerdo, el rango donde cae el "
            "95 % de las diferencias."),
        supuestos=supuestos,
        formula=f.formula,
        citas=list(f.citas),
        lectura=(f"El 95 % de las diferencias ({cand} − {comp}) cae entre "
                 f"{lim_inf:.4f}{u} y {lim_sup:.4f}{u}. Si una diferencia de ese tamaño en "
                 "un paciente concreto te cambiaría una conducta, los métodos no son "
                 "intercambiables — por chico que sea el sesgo promedio."),
        matiz=matiz,
        advertencias=advertencias,
        figuras=figuras,
        crudo={"bland_altman": res, "ccc": ccc, "variabilidad": var,
               "diferencia": f"{cand} − {comp}"},
    )


# ---------------- Supuestos ----------------

def _supuesto_variabilidad(var, pedida, escala, eje_texto) -> Supuesto:
    """EP09c §5.4: antes de dar límites, ¿la dispersión es pareja en todo el rango?"""
    medicion = (f"tamaño de las diferencias contra {eje_texto}: {p_token(var['p_de'])} "
                f"en unidades"
                + (f", {p_token(var['p_cv'])} en %" if var.get("p_cv") is not None else ""))
    clase = var["clase"]
    respuesta = {DE_CONSTANTE: "Pareja (DE constante)",
                 CV_CONSTANTE: "Crece con la concentración (CV constante)"}.get(
        clase, "Ni pareja ni proporcional (mixta)")
    en_pct = escala == "porcentaje"
    if pedida == "auto":
        if clase == CV_CONSTANTE:
            consecuencia = ("Las diferencias van en porcentaje: en unidades, un solo par "
                            "de límites sería demasiado ancho en los valores bajos y "
                            "demasiado angosto en los altos (CLSI EP09c §5.4.2).")
        elif clase == DE_CONSTANTE:
            consecuencia = "Las diferencias van en unidades del analito."
        else:
            consecuencia = ("Ninguna escala sirve para todo el rango (EP09c §5.4.3): se "
                            "informa en unidades, pero los límites exageran el margen en "
                            "un tramo y lo achican en otro. Conviene mirar el gráfico por "
                            "tramos de concentración.")
        alternativa = ("si la dispersión fuera pareja, se informaría en unidades."
                       if en_pct else
                       "si la dispersión creciera con la concentración y en % quedara "
                       "pareja, se informaría en porcentaje.")
    else:
        consecuencia = (f"Escala elegida a mano: {'porcentaje' if en_pct else 'unidades'}.")
        automatica = "porcentaje" if clase == CV_CONSTANTE else "unidades"
        alternativa = ("" if automatica == escala else
                       f"en automático se habría usado {automatica}.")
    return Supuesto(
        pregunta="¿La dispersión de las diferencias es pareja en todo el rango?",
        medicion=medicion, respuesta=respuesta, consecuencia=consecuencia,
        alternativa=alternativa, ok=(clase != "mixta"))


def _supuesto_normalidad(res, modo, elegido, automatico) -> Supuesto:
    normales = res["normal_diffs"]
    sw_p = res["shapiro_p"]
    if sw_p is not None and np.isfinite(sw_p):
        medicion = f"Shapiro-Wilk: W={res['shapiro_w']:.4f}, {p_token(sw_p)}"
        respuesta = "Sí" if normales else "No"
    else:
        medicion = "; ".join(res.get("avisos") or []) or "no se pudo evaluar"
        respuesta = "No evaluable"

    nombre = _nombre_modo(elegido)
    otro = NO_PARAMETRICO if elegido == PARAMETRICO else PARAMETRICO
    if modo == "auto":
        if normales is None:
            consecuencia = ("Sin poder probarla, se usaron los límites paramétricos "
                            "(± 1,96·DE).")
            alternativa = ""
        elif elegido == PARAMETRICO:
            consecuencia = ("Se eligieron los límites paramétricos por ese resultado: "
                            "d̄ ± 1,96·DE, que además traen su intervalo de confianza.")
            alternativa = ("se habrían usado los percentiles 2,5 y 97,5 de las "
                           "diferencias, que no exigen normalidad.")
        else:
            consecuencia = ("Se eligieron los límites no paramétricos por ese resultado: "
                            "los percentiles 2,5 y 97,5 de las diferencias, que no exigen "
                            "normalidad.")
            alternativa = "se habrían usado los límites paramétricos, d̄ ± 1,96·DE."
    else:
        consecuencia = f"Límites {nombre}s elegidos a mano."
        alternativa = ("" if automatico == elegido else
                       f"en automático se habrían usado los {_nombre_modo(otro)}s.")
    return Supuesto(
        pregunta="¿Las diferencias siguen una distribución normal?",
        medicion=medicion, respuesta=respuesta, consecuencia=consecuencia,
        alternativa=alternativa, ok=bool(normales))


def _supuesto_referencia(nombre_eje) -> Supuesto:
    if nombre_eje:
        return Supuesto(
            pregunta="¿Alguno de los dos es un método de referencia?",
            medicion="declarado al elegir el análisis", respuesta=f"Sí: {nombre_eje}",
            consecuencia=(f"La resta es método en prueba − {nombre_eje} (CLSI EP09c, "
                          f"tabla 1), y las diferencias se grafican y se regresan contra "
                          f"{nombre_eje}. Contra el promedio, la referencia entraría en los "
                          "dos ejes y distorsionaría la pendiente (Krouwer 2008)."),
            alternativa=("sin referencia declarada se usaría el promedio de los dos "
                         "métodos (Bland-Altman clásico)."))
    return Supuesto(
        pregunta="¿Alguno de los dos es un método de referencia?",
        medicion="no se declaró ninguno", respuesta="No",
        consecuencia=("Las diferencias se grafican y se regresan contra el promedio de "
                      "los dos métodos (Bland-Altman clásico)."),
        alternativa=("si uno de los dos fuera un método de referencia o un valor "
                     "asignado, habría que declararlo: el eje X pasaría a ser ese "
                     "método (Krouwer 2008)."))


def _supuesto_proporcional(pendiente, eje_texto) -> Supuesto:
    detecta = _detecta_pendiente(pendiente)
    medicion = (f"pendiente contra {eje_texto} = {_f(pendiente['slope'])}, "
                f"IC 95 % {_fic(pendiente['ci'])}, {p_token(pendiente['p'])}")
    pregunta = "¿La diferencia cambia con la magnitud? (sesgo proporcional)"
    if detecta is None:
        return Supuesto(pregunta, medicion, "No evaluable",
                        "No se pudo estimar la pendiente: el eje X no varía.", ok=False)
    if detecta:
        return Supuesto(
            pregunta, medicion, "Sí",
            "El intervalo de la pendiente no incluye el 0: la diferencia entre los "
            "métodos crece o decrece con la concentración. Un sesgo único y unos "
            "límites fijos describen mal los extremos del rango; conviene mirar la "
            "regresión (Passing-Bablok o Deming).",
            alternativa="si el intervalo incluyera el 0, no se podría afirmar que el "
                        "sesgo dependa de la magnitud.",
            ok=False)
    return Supuesto(
        pregunta, medicion, "No se detectó",
        "El intervalo de la pendiente incluye el 0: con estos datos no se puede "
        "afirmar que la diferencia cambie con la magnitud — tampoco descartarlo.",
        alternativa="si el intervalo excluyera el 0, el sesgo dependería de la "
                    "concentración y unos límites fijos no alcanzarían.")


def _valores_ccc(ccc) -> list[Valor]:
    ic = ((ccc["ci_low"], ccc["ci_high"])
          if np.isfinite(ccc["ci_low"]) and np.isfinite(ccc["ci_high"]) else None)
    nota = f"concordancia {ccc['strength'].lower()} según McBride"
    if ccc.get("ci_nota"):
        nota += f". {ccc['ci_nota']}"
    return [Valor("CCC de Lin (ρc)", ccc["ccc"], ic=ic, nota=nota),
            Valor("Precisión: ρ de Pearson", ccc["rho"]),
            Valor("Veracidad: Cb", ccc["cb"])]


def _supuesto_ccc(ccc) -> Supuesto:
    rho, cb = ccc["rho"], ccc["cb"]
    return Supuesto(
        pregunta="En una sola cifra, ¿cuánto concuerdan?",
        medicion=(f"CCC de Lin = {_f(ccc['ccc'])} (precisión ρ {_f(rho)} × "
                  f"veracidad Cb {_f(cb)})"),
        respuesta=ccc["strength"],
        consecuencia=donde_falla_ccc(rho, cb),
        ok=bool(np.isfinite(ccc["ccc"]) and ccc["ccc"] >= 0.90))


# ---------------- Figuras ----------------

def _figura_bland(res, centro, lim_inf, lim_sup, rotulo_centro, elegido, c1, c2, nombre_eje):
    """c1 − c2 es la resta que usó el core: candidato − comparativo."""
    import matplotlib.pyplot as plt

    eje_x, diffs = res["x_axis"], res["diffs"]
    etiqueta_x = (f"{nombre_eje} (método de referencia)" if nombre_eje
                  else "Promedio de ambos métodos")
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(eje_x, diffs, alpha=0.5, c='#4f6ef7', edgecolors='white', s=50)
    ax.axhline(centro, color='#22c55e', lw=2,
               label=f'{rotulo_centro.split("(")[0].strip()}: {centro:.3f}')
    ax.axhline(lim_sup, color='#ef4444', ls='--', lw=1.5, label=f'Límite superior: {lim_sup:.3f}')
    ax.axhline(lim_inf, color='#ef4444', ls='--', lw=1.5, label=f'Límite inferior: {lim_inf:.3f}')
    ax.fill_between([float(np.min(eje_x)), float(np.max(eje_x))], lim_inf, lim_sup,
                    alpha=0.08, color='#22c55e')
    ax.set_xlabel(etiqueta_x)
    if res.get("escala") == "porcentaje":
        base = nombre_eje or "promedio"
        ax.set_ylabel(f'Diferencia %  100·({c1} − {c2}) / {base}')
    else:
        ax.set_ylabel(f'Diferencia ({c1} − {c2})')
    ax.set_title(f'Bland-Altman {_nombre_modo(elegido)} — {c1} vs {c2}', fontweight='bold')
    ax.legend(loc='upper right', framealpha=0.9)
    fig.tight_layout()
    return fig


def _figura_ccc(ccc, c1, c2):
    # La figura es la misma del Omnianálisis: una sola forma de dibujar el CCC.
    # Import tardío: omni_plots fija el backend de matplotlib al importarse.
    from src.analysis.omni_plots import ccc_decomposition_figure

    ic = ((ccc["ci_low"], ccc["ci_high"])
          if np.isfinite(ccc["ci_low"]) and np.isfinite(ccc["ci_high"]) else None)
    return ccc_decomposition_figure({
        "nombre_x": c1, "nombre_y": c2,
        "ccc": float(ccc["ccc"]), "ccc_rho": float(ccc["rho"]), "ccc_cb": float(ccc["cb"]),
        "ccc_fuerza": ccc["strength"], "ccc_ic95": ic,
    })


# ============================================================
#  Rectas de comparación: Passing-Bablok y Deming (EP09c §6.2)
# ============================================================
# Las dos comparten cómo se leen: Y = candidato, X = comparativo, y la recta se
# juzga por los intervalos de la pendiente (¿incluye el 1?) y del intercepto
# (¿incluye el 0?). Un intervalo que incluye el 1 solo dice algo si es angosto:
# `pendiente_concluyente`. El panel viejo declaraba «Métodos concordantes» con
# el IC de la pendiente y un intercepto menor que el 10 % de la media; ese 10 %
# no sale de ninguna norma (decisión 3 de la propuesta de `Resultado`).

def _finito(ic) -> bool:
    return ic is not None and len(ic) == 2 and all(np.isfinite(v) for v in ic)


def _pasos_recta(b, ic_b, a, ic_a, nx, ny):
    """(supuestos, lectura) de una recta de comparación."""
    concluyente, nota_ancho = pendiente_concluyente(ic_b)
    fin_b, fin_a = _finito(ic_b), _finito(ic_a)
    escala = fin_b and not (ic_b[0] <= 1 <= ic_b[1])
    corrimiento = fin_a and not (ic_a[0] <= 0 <= ic_a[1])

    p_pend = "¿La pendiente se aparta de 1? (error de escala, o sesgo proporcional)"
    m_pend = f"pendiente = {_f(b)}, IC 95 % {_fic(ic_b)}"
    if not fin_b:
        pendiente = Supuesto(p_pend, m_pend, "No evaluable",
                             "El intervalo de la pendiente no está acotado: no se puede decidir.",
                             ok=False)
    elif escala:
        pendiente = Supuesto(
            p_pend, m_pend, "Sí",
            f"El intervalo no incluye el 1: por cada unidad de {nx}, {ny} se mueve "
            f"{_f(b)}. El desvío crece con la concentración: es un error de escala, y "
            "apunta a calibración, no a ruido.",
            alternativa="si el intervalo incluyera el 1 y fuera angosto, no se detectaría "
                        "error de escala.",
            ok=False)
    elif concluyente:
        pendiente = Supuesto(
            p_pend, m_pend, "No se detectó",
            "El intervalo incluye el 1 y es lo bastante angosto para que eso diga algo: no "
            "se detecta error de escala.",
            alternativa="si excluyera el 1, el desvío crecería con la concentración.")
    else:
        pendiente = Supuesto(
            p_pend, m_pend, "No concluyente", nota_ancho,
            alternativa="con más muestras o un rango de concentraciones más amplio, el "
                        "intervalo se cerraría lo suficiente para decidir.",
            ok=False)

    p_int = "¿El intercepto se aparta de 0? (corrimiento constante)"
    m_int = f"intercepto = {_f(a)}, IC 95 % {_fic(ic_a)}"
    if not fin_a:
        intercepto = Supuesto(p_int, m_int, "No evaluable",
                              "El intervalo del intercepto no está acotado.", ok=False)
    elif corrimiento:
        intercepto = Supuesto(
            p_int, m_int, "Sí",
            f"El intervalo no incluye el 0: {ny} está corrido unas {_f(a)} unidades de "
            f"{nx} en todo el rango, y ese corrimiento pesa más en los valores bajos.",
            alternativa="si el intervalo incluyera el 0, no se detectaría corrimiento "
                        "constante.",
            ok=False)
    else:
        intercepto = Supuesto(
            p_int, m_int, "No se detectó",
            "El intervalo incluye el 0: no se detecta un corrimiento constante.",
            alternativa="si excluyera el 0, habría un corrimiento constante entre los "
                        "métodos.")

    if escala or corrimiento:
        que = " y ".join(t for t, hay in (("un error de escala", escala),
                                          ("un corrimiento constante", corrimiento)) if hay)
        lectura = (f"Se detecta desvío sistemático de {ny} respecto de {nx}: {que}. "
                   "Apunta a recalibración, no a ruido de la medición. Cuánto pesa en la "
                   "práctica lo dice el sesgo en los niveles de decisión.")
    elif not fin_b:
        lectura = "La recta no se pudo acotar: con estos datos no hay conclusión posible."
    elif concluyente:
        lectura = (f"La recta de {ny} contra {nx} no se aparta de la identidad "
                   "(pendiente 1, intercepto 0): no se detecta corrimiento ni error de "
                   "escala.")
    else:
        lectura = ("Con estos datos la recta no permite afirmar ni descartar un desvío: el "
                   "intervalo de la pendiente es demasiado ancho.")
    return [pendiente, intercepto], lectura


def _sesgos_en_niveles(b, a, x, nx) -> list[Valor]:
    """Sesgo desde la recta en P25, P50 y P75 del comparativo (EP09c §6.3).

    Sin niveles de decisión declarados, los cuartiles del comparativo: los mismos
    que usa el Omnianálisis.
    """
    valores = []
    for q in (25, 50, 75):
        nivel = float(np.percentile(x, q))
        sesgo = (a + b * nivel) - nivel
        pct = f"{100 * sesgo / nivel:.2f} %" if nivel != 0 else "—"
        valores.append(Valor(f"Sesgo en {nx} = {_f(nivel)} (P{q})", sesgo,
                             nota=f"({pct}) desde la recta"))
    return valores


_MATIZ_RECTA = ("Que la recta no se aparte de la identidad no prueba que los métodos sean "
                "intercambiables: eso lo decide cuánto difieren en un paciente "
                "(Bland-Altman) frente al requisito de calidad del analito. Y con pocas "
                "muestras los intervalos se abren y la conclusión se inclina a «sin "
                "desvío» (Mayer et al. 2016).")


def _figura_recta(x, y, b, a, nx, ny, metodo):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(x, y, alpha=0.5, c='#4f6ef7', edgecolors='white', s=50)
    lo, hi = float(min(np.min(x), np.min(y))), float(max(np.max(x), np.max(y)))
    xl = np.linspace(lo, hi, 100)
    ax.plot(xl, b * xl + a, color='#ef4444', lw=2, label=f'{metodo}: y = {b:.3f}·x + {a:.3f}')
    ax.plot(xl, xl, color='#8892a4', ls='--', lw=1, label='Identidad (y = x)')
    ax.set_xlabel(f'{nx} (comparativo)')
    ax.set_ylabel(f'{ny} (en prueba)')
    ax.set_title(f'{metodo} — {ny} contra {nx}', fontweight='bold')
    ax.legend(framealpha=0.9)
    fig.tight_layout()
    return fig


def passing_bablok(df, c1, c2, opciones=None) -> Resultado:
    """Passing-Bablok: Variable 1 = comparativo (X), Variable 2 = en prueba (Y)."""
    titulo = f"Passing-Bablok — {c2} contra {c1}"
    falta = columnas_faltantes(df, c1, c2)
    if falta:
        return Resultado.rechazo("passing_bablok", titulo, falta)
    pares, entrada = filas_completas(df, c1, c2)
    res = passing_bablok_core(pares[c1].to_numpy(dtype=float), pares[c2].to_numpy(dtype=float))
    rechazo = Resultado.rechazo_del_core("passing_bablok", titulo, res, entrada)
    if rechazo is not None:
        return rechazo
    advertencias = list(res.get("avisos") or [])
    if res["n"] < entrada.n:
        advertencias.append(
            f"Se descartaron {entrada.n - res['n']} pares con valores no finitos (±∞).")
    entrada.n = res["n"]
    x, y = res["method1"], res["method2"]
    b, a = res["slope"], res["intercept"]
    rsd = res["se_residuals"]

    valores = [
        Valor("Pendiente (B)", b, ic=res["ci_slope"]),
        Valor("Intercepto (A)", a, ic=res["ci_intercept"]),
        Valor("DE residual (RSD)", rsd,
              nota=f"el 95 % de las diferencias aleatorias, entre {_f(-1.96 * rsd)} y "
                   f"{_f(1.96 * rsd)}"),
        *_sesgos_en_niveles(b, a, x, c1),
        Valor(f"Media {c1}", res["method1_mean"]),
        Valor(f"Media {c2}", res["method2_mean"]),
        Valor("r de Pearson", res["correlation_r"],
              nota="no mide acuerdo: sirve para ver si la recta tiene sentido"),
    ]
    pasos, lectura = _pasos_recta(b, res["ci_slope"], a, res["ci_intercept"], c1, c2)
    lineal = _paso_cusum(res["cusum"])
    cusum = res["cusum"]
    if not cusum.get("error"):
        valores.insert(3, Valor("Cusum de linealidad (H)", cusum["h"],
                                nota=f"({p_token(cusum['p'])}; crítico al 5 %: 1,36)"))
    if not lineal.ok and not cusum.get("error"):
        lectura = ("La prueba Cusum detectó que la relación no es lineal: la recta de "
                   "Passing-Bablok no describe estos datos y su pendiente y su intercepto no "
                   "se deben leer. Mirá el gráfico de residuos: si forman una curva, conviene "
                   "comparar por tramos de concentración. " + lectura)
        advertencias.append("Cusum: se detectó desvío de la linealidad. Passing-Bablok supone "
                            "una relación lineal entre los métodos.")
    n = res["n"]
    suficiente = Supuesto(
        pregunta="¿Hay muestras suficientes para que la recta discrimine?",
        medicion=f"n = {n}; se recomiendan al menos {N_RECOMENDADO} (Bablok y Passing "
                 f"1985) y 50 según Ludbrook (2010)",
        respuesta="Sí" if n >= N_RECOMENDADO else "No",
        consecuencia=("Con este n los intervalos pueden decidir." if n >= N_RECOMENDADO else
                      "Con pocos pares los intervalos se abren: un «no se detectó» vale "
                      "poco."),
        ok=n >= N_RECOMENDADO)
    f = ficha("passing_bablok")
    return Resultado(
        analisis="passing_bablok", titulo=titulo, entrada=entrada, valores=valores,
        metodo=Metodo("Passing-Bablok",
                      "Recta no paramétrica: no supone ninguna distribución de los errores "
                      "y aguanta valores atípicos. Supone relación lineal entre los dos "
                      "métodos y correlación alta (Passing y Bablok 1983)."),
        supuestos=[suficiente, lineal, *pasos], formula=f.formula, citas=list(f.citas),
        lectura=lectura,
        matiz=_MATIZ_RECTA + (" La prueba Cusum solo dice si la recta es aplicable: que no "
                              "detecte curvatura no dice nada sobre si los métodos "
                              "concuerdan."),
        advertencias=advertencias,
        figuras=[Figura("Passing-Bablok", lambda: _figura_recta(x, y, b, a, c1, c2,
                                                                "Passing-Bablok")),
                 Figura("Residuos", lambda: _figura_residuos(x, res["residuals"], rsd, c1))],
        crudo={"passing_bablok": res})


def _paso_cusum(cusum) -> Supuesto:
    """Passing y Bablok (1983): ¿los residuos se alternan al azar a lo largo de la recta?"""
    pregunta = "¿La relación entre los dos métodos es lineal?"
    if cusum.get("error"):
        return Supuesto(pregunta, "prueba Cusum", "No evaluable", cusum["error"], ok=False)
    medicion = (f"Cusum: H = {_f(cusum['h'])}, {p_token(cusum['p'])} "
                f"({cusum['n_pos']} residuos arriba de la recta, {cusum['n_neg']} abajo)")
    if cusum["p"] < 0.05:
        return Supuesto(
            pregunta, medicion, "Se detectó desvío",
            "Los residuos de un mismo signo se agrupan a lo largo de la recta en vez de "
            "alternarse: la relación es curva y Passing-Bablok no aplica (Passing y Bablok "
            "1983). La prueba es algo liberal: con datos lineales rechaza hasta un 9 % de "
            "las veces, así que un p apenas debajo de 0,05 es evidencia débil.",
            alternativa="si los residuos se alternaran al azar, la recta sería aplicable.",
            ok=False)
    return Supuesto(
        pregunta, medicion, "No se detectó desvío",
        "Los residuos se alternan a los dos lados de la recta sin agruparse: la recta es "
        "aplicable.",
        alternativa="si se agruparan (arriba en los extremos y abajo en el medio, o al "
                    "revés), la relación sería curva y la recta no aplicaría.")


def _figura_residuos(x, residuos, rsd, nx):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.scatter(x, residuos, alpha=0.5, c='#4f6ef7', edgecolors='white', s=50)
    ax.axhline(0, color='#ef4444', ls='--', lw=1.5)
    for s in (-1.96, 1.96):
        ax.axhline(s * rsd, color='#8892a4', ls=':', lw=1.2)
    ax.set_xlabel(nx)
    ax.set_ylabel('Residuo')
    ax.set_title('Residuos (±1,96·RSD)', fontweight='bold')
    fig.tight_layout()
    return fig


def deming(df, c1, c2, opciones=None) -> Resultado:
    """Deming: Variable 1 = comparativo (X), Variable 2 = en prueba (Y).

    `opciones`:
      tipo:   "auto" | "constante" | "ponderado"  (auto: por la variabilidad)
      lambda: var_error(X) / var_error(Y); 1 si no se conoce (EP09c §6.2.2)
    """
    opciones = opciones or {}
    tipo = opciones.get("tipo", "auto")
    titulo = f"Deming — {c2} contra {c1}"
    try:
        lam = float(opciones.get("lambda", 1.0) or 1.0)
    except (TypeError, ValueError):
        return Resultado.rechazo("deming", titulo, "λ tiene que ser un número positivo.")
    if not lam > 0:
        return Resultado.rechazo("deming", titulo, "λ tiene que ser un número positivo.")
    falta = columnas_faltantes(df, c1, c2)
    if falta:
        return Resultado.rechazo("deming", titulo, falta)
    pares, entrada = filas_completas(df, c1, c2)
    x, y = pares[c1].to_numpy(dtype=float), pares[c2].to_numpy(dtype=float)
    finitos = np.isfinite(x) & np.isfinite(y)
    advertencias = []
    if finitos.sum() >= 3:
        var = variabilidad_diferencias(x[finitos], (y - x)[finitos])
    else:
        var = None

    if tipo == "auto":
        ponderar = bool(var and var["clase"] == CV_CONSTANTE)
    else:
        ponderar = tipo == "ponderado"
    res = (deming_ponderado_core if ponderar else deming_regression_core)(x, y, lambda_ratio=lam)
    if ponderar and tipo == "auto" and isinstance(res, dict) and res.get("error"):
        advertencias.append(f"Deming ponderado no se pudo calcular ({res['error']}): se usó "
                            "Deming sin ponderar.")
        ponderar = False
        res = deming_regression_core(x, y, lambda_ratio=lam)
    rechazo = Resultado.rechazo_del_core("deming", titulo, res, entrada)
    if rechazo is not None:
        return rechazo
    entrada.n = res["n"]
    xf, yf = x[finitos], y[finitos]
    b, a = res["slope"], res["intercept"]
    nombre = "Deming ponderado (CV constante)" if ponderar else "Deming"

    valores = [
        Valor("Pendiente", b, ic=res["ci_slope"]),
        Valor("Intercepto", a, ic=res["ci_intercept"]),
        Valor("λ (var. error X / var. error Y)", lam),
        Valor("R²", res["r2"]),
        *_sesgos_en_niveles(b, a, xf, c1),
        Valor(f"Media {c1}", res["x_mean"]),
        Valor(f"Media {c2}", res["y_mean"]),
    ]
    supuestos = []
    if var is not None:
        supuestos.append(_paso_variabilidad_recta(var, ponderar, tipo, c1))
        if var["clase"] == "mixta":
            advertencias.append("La dispersión de las diferencias es mixta: EP09c (§6.2.3) "
                                "recomienda Passing-Bablok para estos datos.")
    supuestos.append(_paso_normalidad_recta(yf - xf if not ponderar else 100 * (yf - xf) / xf,
                                            ponderar))
    supuestos.append(Supuesto(
        pregunta="¿Cuánto error de medición se supuso en cada método?",
        medicion=f"λ = {_f(lam)} (varianza del error de {c1} / la de {c2})",
        respuesta="Iguales" if lam == 1 else f"λ = {_f(lam)}",
        consecuencia=("Se supuso la misma imprecisión en los dos: es el valor por defecto "
                      "de EP09c cuando no hay estudios de precisión (EP05)." if lam == 1 else
                      "Se usó el cociente declarado."),
        alternativa=(f"si se conocen los CV de cada método, λ = CV²({c1}) / CV²({c2}); "
                     "con λ mal puesto la pendiente se sesga.")))
    pasos, lectura = _pasos_recta(b, res["ci_slope"], a, res["ci_intercept"], c1, c2)
    supuestos += pasos
    f = ficha("deming")
    return Resultado(
        analisis="deming", titulo=f"{nombre} — {c2} contra {c1}", entrada=entrada,
        valores=valores,
        metodo=Metodo(nombre,
                      "Recta con error en los dos ejes: a diferencia de mínimos cuadrados, "
                      "no supone que el comparativo mide sin error. Ponderada, cada punto "
                      "pesa 1/concentración², porque los altos son más ruidosos "
                      "(EP09c §6.2)."),
        supuestos=supuestos, formula=f.formula, citas=list(f.citas),
        lectura=lectura, matiz=_MATIZ_RECTA, advertencias=advertencias,
        figuras=[Figura(nombre, lambda: _figura_recta(xf, yf, b, a, c1, c2, nombre))],
        crudo={"deming": res, "variabilidad": var, "ponderado": ponderar})


def _paso_variabilidad_recta(var, ponderar, tipo, nx) -> Supuesto:
    medicion = (f"tamaño de las diferencias contra {nx}: {p_token(var['p_de'])} en unidades"
                + (f", {p_token(var['p_cv'])} en %" if var.get("p_cv") is not None else ""))
    respuesta = {DE_CONSTANTE: "Pareja (DE constante)",
                 CV_CONSTANTE: "Crece con la concentración (CV constante)"}.get(
        var["clase"], "Ni pareja ni proporcional (mixta)")
    if tipo != "auto":
        consecuencia = f"Tipo elegido a mano: {'ponderado' if ponderar else 'sin ponderar'}."
    elif ponderar:
        consecuencia = ("Se pondera cada punto por 1/concentración²: sin eso, los puntos "
                        "altos, más ruidosos, arrastrarían la recta (EP09c §6.2.2).")
    else:
        consecuencia = "Deming sin ponderar, la recta por defecto con DE constante (EP09c §6.2.1)."
    return Supuesto(
        pregunta="¿La dispersión de las diferencias es pareja en todo el rango?",
        medicion=medicion, respuesta=respuesta, consecuencia=consecuencia,
        alternativa=("con DE constante se usaría Deming sin ponderar." if ponderar else
                     "con CV constante se ponderaría cada punto por 1/concentración²."),
        ok=var["clase"] != "mixta")


def _paso_normalidad_recta(d, en_pct) -> Supuesto:
    from scipy import stats

    d = np.asarray(d, dtype=float)
    d = d[np.isfinite(d)]
    pregunta = "¿Las diferencias entre los métodos se reparten en forma de campana?"
    if len(d) < 3 or np.ptp(d) == 0:
        return Supuesto(pregunta, "no se pudo evaluar", "No evaluable",
                        "Deming supone errores normales; no se pudo verificar.", ok=False)
    w, p = stats.shapiro(d)
    normales = p >= 0.05
    return Supuesto(
        pregunta=pregunta,
        medicion=f"Shapiro-Wilk{' (en %)' if en_pct else ''}: W={w:.4f}, {p_token(p)}",
        respuesta="Sí" if normales else "No",
        consecuencia=("Compatible con los errores normales que supone Deming." if normales else
                      "Hay diferencias aberrantes o asimétricas: Deming es sensible a ellas "
                      "y EP09c (§6.2.4) recomienda Passing-Bablok."),
        alternativa=("si no lo fueran, correspondería Passing-Bablok." if normales else ""),
        ok=bool(normales))


# ============================================================
#  Imprecisión desde duplicados
# ============================================================

def cv_duplicados(df, c1, c2, opciones=None) -> Resultado:
    """CV intraserie desde duplicados: los tres métodos de MedCalc, y cuál leer.

    Cuál vale lo decide la variabilidad: con DE constante, la DE intrasujeto (un
    CV único exagera abajo y achica arriba); con CV constante, el de la raíz
    cuadrática media (Hyslop y White 2009), o el logarítmico.
    """
    titulo = f"Imprecisión desde duplicados — {c1} y {c2}"
    falta = columnas_faltantes(df, c1, c2)
    if falta:
        return Resultado.rechazo("cv_duplicados", titulo, falta)
    pares, entrada = filas_completas(df, c1, c2)
    x1, x2 = pares[c1].to_numpy(dtype=float), pares[c2].to_numpy(dtype=float)
    res = cv_duplicados_core(x1, x2)
    rechazo = Resultado.rechazo_del_core("cv_duplicados", titulo, res, entrada)
    if rechazo is not None:
        return rechazo
    entrada.n = res["n"]
    finitos = np.isfinite(x1) & np.isfinite(x2)
    x1, x2 = x1[finitos], x2[finitos]
    var = variabilidad_diferencias((x1 + x2) / 2, x1 - x2) if len(x1) >= 3 else None
    clase = var["clase"] if var else DE_CONSTANTE

    notas = res.get("notas") or {}
    valores = [
        Valor("Media global", res["media"]),
        Valor("DE intrasujeto", res["de_intra"], ic=res["ic_de_intra"],
              nota="√(Σd²/2n); vale con DE constante"),
        Valor("CV desde la DE intrasujeto", res["cv_de"], ic=res["ic_cv_de"], decimales=2,
              unidad="%", nota=notas.get("cv_de", "DE intrasujeto / media global")),
        Valor("CV, raíz cuadrática media", res["cv_rms"], ic=res["ic_cv_rms"], decimales=2,
              unidad="%", nota=notas.get("cv_rms", "√(Σ(d/m)²/2n); vale con CV constante")),
        Valor("CV, método logarítmico", res["cv_log"], ic=res["ic_cv_log"], decimales=2,
              unidad="%", nota=notas.get("cv_log", "vale con CV constante")),
        Valor(f"Diferencia media ({c1} − {c2})", res["sesgo_replicas"]),
    ]
    supuestos = []
    if var is not None:
        respuesta = {DE_CONSTANTE: "Pareja (DE constante)",
                     CV_CONSTANTE: "Crece con la concentración (CV constante)"}.get(
            clase, "Ni pareja ni proporcional (mixta)")
        supuestos.append(Supuesto(
            pregunta="¿La diferencia entre duplicados es pareja en todo el rango?",
            medicion=(f"tamaño de las diferencias contra la media de cada par: "
                      f"{p_token(var['p_de'])} en unidades"
                      + (f", {p_token(var['p_cv'])} en %" if var.get("p_cv") is not None
                         else "")),
            respuesta=respuesta,
            consecuencia={
                DE_CONSTANTE: "La imprecisión es la misma en unidades en todo el rango: la "
                              "cifra que vale es la DE intrasujeto. Un CV único exageraría "
                              "abajo y achicaría arriba.",
                CV_CONSTANTE: "La imprecisión crece con la concentración y en % queda "
                              "pareja: la cifra que vale es el CV de la raíz cuadrática "
                              "media (o el logarítmico). El CV desde la DE queda sesgado.",
            }.get(clase, "Ni la DE ni el CV son constantes: una sola cifra no describe todo "
                         "el rango. Conviene estimar la imprecisión por tramos de "
                         "concentración."),
            alternativa=("con CV constante valdría el CV de la raíz cuadrática media."
                         if clase == DE_CONSTANTE else
                         "con DE constante valdría la DE intrasujeto."),
            ok=clase != "mixta"))
    supuestos.append(_paso_orden_replicas(x1 - x2, c1, c2))

    if clase == CV_CONSTANTE and res["cv_rms"] is not None:
        lectura = (f"La imprecisión intraserie es un CV de {res['cv_rms']:.2f} % "
                   f"(IC 95 %: {res['ic_cv_rms'][0]:.2f} a {res['ic_cv_rms'][1]:.2f} %), "
                   "parejo en todo el rango.")
    elif clase == DE_CONSTANTE:
        lectura = (f"La imprecisión intraserie es una DE de {_f(res['de_intra'])} unidades "
                   f"(IC 95 %: {_fic(res['ic_de_intra'])}), pareja en todo el rango.")
    else:
        lectura = ("La imprecisión cambia a lo largo del rango sin seguir ni una DE ni un CV "
                   "constante: las cifras de la tabla son promedios que no valen para cada "
                   "tramo.")
    f = ficha("cv_duplicados")
    return Resultado(
        analisis="cv_duplicados", titulo=titulo, entrada=entrada, valores=valores,
        metodo=Metodo("Imprecisión desde duplicados",
                      "Cada muestra medida dos veces: la diferencia entre las dos réplicas "
                      "mide la imprecisión, sin necesitar muchas repeticiones de una sola "
                      "muestra (Jones y Payne 1997)."),
        supuestos=supuestos, formula=f.formula, citas=list(f.citas), lectura=lectura,
        matiz=("Duplicados de una misma corrida miden repetibilidad (intraserie), no la "
               "imprecisión entre días ni entre lotes: para eso está el diseño de CLSI "
               "EP05/EP15."),
        crudo={"cv_duplicados": res, "variabilidad": var})


def _paso_orden_replicas(d, c1, c2) -> Supuesto:
    from scipy import stats

    pregunta = "¿La primera y la segunda réplica leen lo mismo en promedio?"
    d = np.asarray(d, dtype=float)
    if len(d) < 3 or np.ptp(d) == 0:
        return Supuesto(pregunta, "no se pudo evaluar", "No evaluable",
                        "Sin variación en las diferencias no hay nada que probar.", ok=True)
    t, p = stats.ttest_1samp(d, 0.0)
    corrida = p < 0.05
    return Supuesto(
        pregunta=pregunta,
        medicion=f"diferencia media {c1} − {c2} = {_f(np.mean(d))}, t de una muestra, "
                 f"{p_token(p)}",
        respuesta="No: se detectó una diferencia" if corrida else "Sí",
        consecuencia=("Se detectó una diferencia sistemática entre réplicas (¿deriva, "
                      "arrastre, orden de medición?). La DE intrasujeto la incluye y "
                      "sobreestima la imprecisión." if corrida else
                      "No se detectó diferencia sistemática entre la primera y la segunda "
                      "réplica."),
        alternativa=("" if corrida else
                     "si la hubiera, la DE intrasujeto sobreestimaría la imprecisión."),
        ok=not corrida)


# ============================================================
#  Correlación intraclase
# ============================================================

def _koo_li(v) -> str:
    """Koo y Li (2016): < 0,5 pobre; 0,5-0,75 moderada; 0,75-0,9 buena; > 0,9 excelente."""
    if v < 0.5:
        return "pobre"
    if v < 0.75:
        return "moderada"
    if v < 0.9:
        return "buena"
    return "excelente"


def icc(df, c1, c2, opciones=None) -> Resultado:
    """ICC de dos vías con dos métodos: acuerdo absoluto ICC(A,1) y consistencia ICC(C,1)."""
    from scipy import stats

    titulo = f"Correlación intraclase — {c1} y {c2}"
    falta = columnas_faltantes(df, c1, c2)
    if falta:
        return Resultado.rechazo("icc", titulo, falta)
    pares, entrada = filas_completas(df, c1, c2)
    datos = np.column_stack([pares[c1].to_numpy(dtype=float), pares[c2].to_numpy(dtype=float)])
    datos = datos[np.all(np.isfinite(datos), axis=1)]
    if len(datos) < 3:
        return Resultado.rechazo("icc", titulo, f"Se necesitan al menos 3 pares completos; "
                                                f"hay {len(datos)}.", entrada)
    r = intraclass_correlation(datos, model="two-way-random")
    rc = intraclass_correlation(datos, model="two-way-mixed")
    rechazo = Resultado.rechazo_del_core("icc", titulo, r, entrada)
    if rechazo is not None:
        return rechazo
    entrada.n = len(datos)
    ic_a = (r["ci_low"], r["ci_high"])
    valores = [
        Valor("ICC(A,1) — acuerdo absoluto", r["icc"], ic=ic_a),
        Valor("ICC(C,1) — consistencia", rc["icc"] if rc else None,
              ic=(rc["ci_low"], rc["ci_high"]) if rc else None),
        Valor("F", r["f"], nota=f"gl {r['df1']} y {r['df2']}"),
        Valor("p (ICC = 0)", fmt_p(r["p"]), nota="casi nunca interesa: nadie espera ICC = 0"),
    ]
    d = datos[:, 1] - datos[:, 0]
    supuestos = []
    if np.ptp(d) > 0:
        t, p = stats.ttest_1samp(d, 0.0)
        sesgo = p < 0.05
        supuestos.append(Supuesto(
            pregunta="¿Un método lee sistemáticamente distinto del otro?",
            medicion=f"diferencia media {c2} − {c1} = {_f(np.mean(d))}, t pareada, "
                     f"{p_token(p)}",
            respuesta="Sí" if sesgo else "No se detectó",
            consecuencia=("Hay sesgo entre los métodos: por eso el ICC de acuerdo absoluto "
                          "queda por debajo del de consistencia. El de acuerdo es el que "
                          "cuenta para intercambiar métodos." if sesgo else
                          "Sin sesgo detectado, los dos ICC quedan parecidos."),
            alternativa=("sin sesgo, los dos ICC coincidirían." if sesgo else
                         "con sesgo, el ICC de acuerdo absoluto caería por debajo del de "
                         "consistencia."),
            ok=not sesgo))
    lo, hi = ic_a
    rango = (_koo_li(lo) if _koo_li(lo) == _koo_li(hi)
             else f"entre {_koo_li(lo)} y {_koo_li(hi)}")
    supuestos.append(Supuesto(
        pregunta="¿Qué tan fiable es el acuerdo, según su intervalo?",
        medicion=f"IC 95 % del ICC(A,1): {_fic(ic_a)}",
        respuesta=rango.capitalize(),
        consecuencia=("Se juzga por el intervalo y no por el valor puntual, como piden Koo y "
                      "Li (2016): < 0,5 pobre, 0,5 a 0,75 moderada, 0,75 a 0,9 buena, "
                      "> 0,9 excelente."),
        ok=lo >= 0.75))
    f = ficha("icc")
    return Resultado(
        analisis="icc", titulo=titulo, entrada=entrada, valores=valores,
        metodo=Metodo("ICC(A,1), dos vías, acuerdo absoluto",
                      "Con dos métodos que miden a todos los sujetos el modelo es de dos "
                      "vías, y para concordancia interesa el acuerdo absoluto: un sesgo "
                      "entre métodos baja el ICC (McGraw y Wong 1996)."),
        supuestos=supuestos, formula=f.formula, citas=list(f.citas),
        lectura=(f"Fiabilidad {rango} según el intervalo del ICC de acuerdo absoluto "
                 f"({_fic(ic_a)})."),
        matiz=("El ICC depende del rango de los sujetos: una muestra muy heterogénea lo "
               "infla sin que los métodos concuerden mejor. No dice cuánto difieren en un "
               "paciente; para eso está Bland-Altman."),
        crudo={"icc_a": r, "icc_c": rc})


# ============================================================
#  Bland-Altman de varios métodos contra una referencia
# ============================================================

def bland_altman_multiple(df, referencia, metodos, opciones=None) -> Resultado:
    """Cada método contra la referencia (MedCalc; Krouwer 2008): d = método − referencia."""
    if isinstance(metodos, str):
        metodos = [metodos]
    metodos = [m for m in dict.fromkeys(metodos) if m != referencia]
    titulo = f"Bland-Altman múltiple — referencia: {referencia}"
    if not metodos:
        return Resultado.rechazo("bland_altman_multiple", titulo,
                                 "Hace falta al menos un método para comparar con la referencia.")
    falta = columnas_faltantes(df, referencia, *metodos)
    if falta:
        return Resultado.rechazo("bland_altman_multiple", titulo, falta)

    resultados, advertencias, valores = {}, [], []
    n_max = 0
    for m in metodos:
        pares, entrada_m = filas_completas(df, referencia, m)
        r = bland_altman_analysis(pares[m].to_numpy(dtype=float),
                                  pares[referencia].to_numpy(dtype=float), reference="y")
        if isinstance(r, dict) and r.get("error"):
            advertencias.append(f"{m}: {r['error']}")
            continue
        if entrada_m.descartadas:
            advertencias.append(f"{m}: {texto_descartes(entrada_m.descartadas)}")
        resultados[m] = r
        n_max = max(n_max, r["n"])
        valores += [
            Valor(f"{m} − {referencia}: sesgo", r["mean_difference"], ic=r["ci_mean"],
                  nota=f"n = {r['n']}; {r['bias_pct']:.2f} % de la referencia"),
            Valor(f"{m} − {referencia}: límite inferior", r["loa_lower"], ic=r["ci_lower"]),
            Valor(f"{m} − {referencia}: límite superior", r["loa_upper"], ic=r["ci_upper"]),
        ]
    if not resultados:
        return Resultado.rechazo("bland_altman_multiple", titulo,
                                 "Ningún método se pudo comparar: " + " ".join(advertencias))

    no_normales = [m for m, r in resultados.items() if r["normal_diffs"] is False]
    detalle = "; ".join(
        f"{m}: {p_token(r['shapiro_p'])}" if np.isfinite(r["shapiro_p"]) else f"{m}: no evaluable"
        for m, r in resultados.items())
    supuestos = [Supuesto(
        pregunta="¿Las diferencias de cada método con la referencia son normales?",
        medicion=f"Shapiro-Wilk — {detalle}",
        respuesta="Sí, en todos" if not no_normales else "No en " + ", ".join(no_normales),
        consecuencia=("Los límites paramétricos (± 1,96·DE) valen para todos." if not no_normales
                      else "Para " + ", ".join(no_normales) + " los límites paramétricos no "
                      "corresponden: mirá su Bland-Altman individual, que ofrece los no "
                      "paramétricos."),
        ok=not no_normales)]
    clases = {m: variabilidad_diferencias(r["x_axis"], r["diffs"])["clase"]
              for m, r in resultados.items() if r["n"] >= 3}
    en_pct = [m for m, c in clases.items() if c == CV_CONSTANTE]
    mixtas = [m for m, c in clases.items() if c == "mixta"]
    supuestos.append(Supuesto(
        pregunta="¿La dispersión de las diferencias es pareja en todo el rango?",
        medicion="; ".join(f"{m}: {c}" for m, c in clases.items()),
        respuesta="Sí, en todos" if not (en_pct or mixtas) else "No en todos",
        consecuencia=("Los límites en unidades valen para todo el rango." if not (en_pct or mixtas)
                      else ("Para " + ", ".join(en_pct + mixtas) + " un solo par de límites en "
                            "unidades no sirve para todo el rango: su Bland-Altman individual "
                            "los da en porcentaje (EP09c §5.4).")),
        ok=not (en_pct or mixtas)))
    f = ficha("bland_altman_multiple")
    return Resultado(
        analisis="bland_altman_multiple", titulo=titulo,
        entrada=Entrada(columnas=(referencia, *metodos), n=n_max),
        valores=valores,
        metodo=Metodo("Bland-Altman contra una referencia",
                      "Cada método se compara con la misma referencia: diferencia = método − "
                      "referencia, graficada contra la referencia (Krouwer 2008), con el IC "
                      "de cada límite."),
        supuestos=supuestos, formula=f.formula, citas=list(f.citas),
        lectura=("Cada fila dice cuánto se aparta ese método de la referencia en un paciente: "
                 "el 95 % de sus diferencias cae entre sus dos límites."),
        matiz=("Comparar dos métodos entre sí a través de la referencia no es lo mismo que "
               "compararlos directamente. Y el límite tolerable lo pone el requisito de "
               "calidad del analito, no el programa."),
        advertencias=advertencias,
        figuras=[Figura("Bland-Altman contra la referencia",
                        lambda: _figura_multiple(resultados, referencia))],
        crudo={"por_metodo": resultados})


def _figura_multiple(resultados, referencia):
    import matplotlib.pyplot as plt

    k = len(resultados)
    fig, ejes = plt.subplots(1, k, figsize=(5 * k, 4.5), squeeze=False, sharey=True)
    for ax, (m, r) in zip(ejes[0], resultados.items()):
        ax.scatter(r["x_axis"], r["diffs"], alpha=0.5, c='#4f6ef7', edgecolors='white', s=40)
        ax.axhline(r["mean_difference"], color='#22c55e', lw=2)
        ax.axhline(r["loa_upper"], color='#ef4444', ls='--', lw=1.3)
        ax.axhline(r["loa_lower"], color='#ef4444', ls='--', lw=1.3)
        ax.set_title(f'{m} − {referencia}', fontweight='bold')
        ax.set_xlabel(f'{referencia} (referencia)')
    ejes[0][0].set_ylabel('Diferencia (método − referencia)')
    fig.tight_layout()
    return fig
