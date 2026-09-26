"""Comparación de métodos (CLSI EP09): el primer ciclo de «MedCalc pero guiado».

Bland-Altman primero. Passing-Bablok, Deming, CV de duplicados e ICC vienen
detrás, en este mismo archivo.
"""
from __future__ import annotations

import numpy as np

from src.core.bland_altman import (
    CV_CONSTANTE, DE_CONSTANTE, bland_altman_analysis, concordance_correlation,
    variabilidad_diferencias,
)
from src.resultado.citas import ficha
from src.resultado.datos import columnas_faltantes, filas_completas
from src.resultado.lenguaje import donde_falla_ccc, p_token
from src.resultado.modelo import Figura, Metodo, Resultado, Supuesto, Valor

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
