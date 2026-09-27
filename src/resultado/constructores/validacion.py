"""El asistente B, «Validar un método»: CLSI EP09c + EP15-A3 en un veredicto.

Corre lo que un laboratorio corre a mano cuando verifica un método nuevo contra
el que ya usa: Bland-Altman con el CCC, la recta que corresponde según EP09c
§6.2 (y la otra, para comparar), el sesgo en los niveles de decisión médica
con su intervalo y, si se cargaron corridas, la precisión por EP15-A3. Después
compara el sesgo con el sesgo permitido y da un solo veredicto.

El veredicto lo arma este archivo y nada más: cada análisis que corre trae su
propio informe (`Resultado.partes`) y no se reescribe ninguna de sus lecturas.
Si el asistente escribiera su propia versión de un Bland-Altman, habría dos
verdades (la decisión de hacer primero la envoltura A y después este B).
"""
from __future__ import annotations

import math

import numpy as np

from src.core.bland_altman import CV_CONSTANTE, DE_CONSTANTE
from src.core.ep09 import (
    CUMPLE, DEMING, N_EP09, NO_CONCLUYENTE, NO_CUMPLE, NO_EVALUABLE, NOMBRES,
    PASSING_BABLOK, elegir_regresion, sesgo_en_niveles, veredicto,
)
from src.resultado.citas import ficha
from src.resultado.constructores.comparacion import bland_altman, deming, passing_bablok
from src.resultado.constructores.precision import precision_ep15
from src.resultado.datos import columnas_faltantes, filas_completas
from src.resultado.lenguaje import num, p_token
from src.resultado.modelo import Figura, Metodo, Resultado, Supuesto, Valor

ANALISIS = "validar_metodo"


def _f(x, dec=4) -> str:
    return Valor("", x, decimales=dec).texto()


def _numero(v):
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    v = float(v)
    return None if math.isnan(v) else v


def validar_metodo(df, comparativo, candidato, opciones=None) -> Resultado:
    """Variable 1 = comparativo (X, el método en uso); Variable 2 = candidato (Y).

    `opciones`:
      sesgo_permitido:  número, o None si no hay criterio (no hay veredicto)
      escala_permitido: "porcentaje" | "unidades"
      niveles:          niveles de decisión médica, en unidades de X; vacío =
                        los cuartiles del comparativo
      lambda:           λ de Deming, var. del error de X / de Y (1 si no se sabe)
      corridas:         columnas de EP15 (una por día); vacío = sin precisión
      declaracion, sigma_r, sigma_wl, n_muestras: lo declarado por el fabricante
    """
    opciones = opciones or {}
    titulo = f"Validar un método — {candidato} contra {comparativo}"
    if comparativo == candidato:
        return Resultado.rechazo(ANALISIS, titulo,
                                 "El método en prueba y el comparativo son la misma columna.")
    falta = columnas_faltantes(df, comparativo, candidato)
    if falta:
        return Resultado.rechazo(ANALISIS, titulo, falta)
    try:
        permitido = _numero(opciones.get("sesgo_permitido"))
        lam = _numero(opciones.get("lambda")) or 1.0
        niveles = [float(v) for v in (opciones.get("niveles") or []) if _numero(v) is not None]
    except (TypeError, ValueError):
        return Resultado.rechazo(ANALISIS, titulo,
                                 "El sesgo permitido, los niveles y λ tienen que ser números.")
    if permitido is not None and permitido <= 0:
        return Resultado.rechazo(ANALISIS, titulo, "El sesgo permitido tiene que ser positivo.")
    if lam <= 0:
        return Resultado.rechazo(ANALISIS, titulo, "λ tiene que ser positivo.")
    en_pct = opciones.get("escala_permitido", "porcentaje") == "porcentaje"

    pares, entrada = filas_completas(df, comparativo, candidato)
    x = pares[comparativo].to_numpy(dtype=float)
    y = pares[candidato].to_numpy(dtype=float)
    finitos = np.isfinite(x) & np.isfinite(y)
    x, y = x[finitos], y[finitos]

    # 1) Bland-Altman con el comparativo como eje (Krouwer) y d = candidato − comparativo.
    ba = bland_altman(df, comparativo, candidato, {"referencia": "x"})
    if not ba.ok:
        return Resultado.rechazo(ANALISIS, titulo, ba.error, entrada)
    entrada.n = len(x)

    # 2) La recta que corresponde (EP09c §6.2), y las dos para mostrarlas.
    eleccion = elegir_regresion(x, y)
    metodo = eleccion["metodo"]
    pb = passing_bablok(df, comparativo, candidato)
    dem = deming(df, comparativo, candidato, {"tipo": "auto", "lambda": lam})
    advertencias = []
    if metodo != PASSING_BABLOK and not dem.ok:
        advertencias.append(f"Deming no se pudo calcular ({dem.error}): se usa Passing-Bablok.")
        metodo = PASSING_BABLOK
    if metodo == PASSING_BABLOK and not pb.ok:
        return Resultado.rechazo(ANALISIS, titulo, f"Passing-Bablok: {pb.error}", entrada)

    # 3) Sesgo en los niveles de decisión, con su IC (EP09c §6.3).
    de_cuartiles = not niveles
    if de_cuartiles:
        niveles = [float(np.percentile(x, q)) for q in (25, 50, 75)]
    sesgos = sesgo_en_niveles(x, y, metodo, niveles, lam)
    if "error" in sesgos and metodo != PASSING_BABLOK:
        advertencias.append(f"{sesgos['error']} Se usa Passing-Bablok.")
        metodo = PASSING_BABLOK
        sesgos = sesgo_en_niveles(x, y, metodo, niveles, lam)
    if "error" in sesgos:
        return Resultado.rechazo(ANALISIS, titulo, sesgos["error"], entrada)

    cusum = pb.crudo["passing_bablok"]["cusum"] if pb.ok else {"error": "sin Passing-Bablok"}
    no_lineal = not cusum.get("error") and cusum["p"] < 0.05

    # 4) Cada nivel contra el sesgo permitido.
    filas = []
    for xc, s, lo, hi in zip(sesgos["niveles"], sesgos["sesgo"], sesgos["ic_inf"],
                             sesgos["ic_sup"]):
        perm_u = None if permitido is None else (permitido * xc / 100 if en_pct else permitido)
        estado = None if perm_u is None else veredicto(lo, hi, perm_u)
        filas.append({"nivel": xc, "sesgo": s, "ic": (lo, hi), "permitido": perm_u,
                      "estado": estado})

    # 5) Precisión por EP15-A3, si se cargaron corridas.
    partes = [ba]
    corridas = [c for c in (opciones.get("corridas") or []) if c not in (comparativo, candidato)]
    prec = None
    if corridas:
        prec = precision_ep15(df, corridas, {k: opciones.get(k) for k in (
            "declaracion", "sigma_r", "sigma_wl", "n_muestras")})
        if not prec.ok:
            advertencias.append(f"La precisión (EP15) no se pudo calcular: {prec.error}")
            prec = None

    elegido, otro = (pb, dem) if metodo == PASSING_BABLOK else (dem, pb)
    partes += [p for p in (elegido, otro) if p.ok]
    if prec is not None:
        partes.append(prec)

    final, motivos = _veredicto_final(filas, prec, no_lineal, permitido)
    valores = _valores(final, filas, metodo, sesgos, ba, prec, comparativo, len(x), de_cuartiles,
                       en_pct, permitido)
    supuestos = [
        _paso_n(len(x)),
        _paso_recta(eleccion, metodo, comparativo),
        _paso_linealidad(cusum),
        _paso_criterio(permitido, en_pct, de_cuartiles, comparativo),
    ]
    if prec is not None:
        supuestos.append(_paso_precision(prec))

    f = ficha(ANALISIS)
    return Resultado(
        analisis=ANALISIS, titulo=titulo, entrada=entrada, valores=valores,
        metodo=Metodo(
            "Verificación guiada: CLSI EP09c + EP15-A3",
            "Compara el sesgo del método en prueba en cada nivel de decisión médica, con "
            "su intervalo de confianza, contra el sesgo permitido; la recta la elige la "
            "forma de los datos (EP09c §6.2) y la precisión, si hay corridas, se verifica "
            "contra lo que declara el fabricante (EP15-A3)."),
        supuestos=supuestos, formula=f.formula, citas=list(f.citas),
        lectura=_lectura(final, motivos, prec),
        matiz=("El veredicto vale para los niveles evaluados y el sesgo permitido que se "
               "cargó: el requisito de calidad no lo elige el programa (sale de la "
               "variabilidad biológica, de la regulación o del uso clínico). Un «cumple» "
               "sobre el sesgo no dice nada de la imprecisión si no se cargaron corridas de "
               "EP15, y un «no concluyente» no es un «no cumple»: suele pedir más muestras "
               "en el nivel que quedó en duda."),
        advertencias=advertencias,
        figuras=[Figura("Sesgo en los niveles de decisión",
                        lambda: _figura_sesgo(x, sesgos, filas, permitido, en_pct,
                                              comparativo, candidato)),
                 *ba.figuras[:1], *elegido.figuras[:1]],
        crudo={"eleccion": eleccion, "sesgos": sesgos, "niveles": filas,
               "veredicto": final, "motivos": motivos, "cusum": cusum},
        partes=partes)


# ---------------- El veredicto ----------------

def _veredicto_final(filas, prec, no_lineal, permitido):
    """(veredicto, motivos). Sin sesgo permitido no hay veredicto."""
    motivos = []
    estados = []
    if permitido is not None:
        for f in filas:
            estados.append(f["estado"])
            if f["estado"] == NO_CUMPLE:
                motivos.append(f"el sesgo en {num(f['nivel'])} supera el permitido")
            elif f["estado"] == NO_CONCLUYENTE:
                motivos.append(f"en {num(f['nivel'])} el intervalo del sesgo cruza el "
                               "límite permitido")
            elif f["estado"] == NO_EVALUABLE:
                motivos.append(f"en {num(f['nivel'])} el sesgo no se pudo evaluar")
    if prec is not None:
        for clave, nombre in (("repetibilidad", "la repetibilidad"),
                              ("intralaboratorio", "la precisión intralaboratorio")):
            ver = prec.crudo.get(clave)
            if ver is None:
                continue
            estados.append(CUMPLE if ver["verificado"] else NO_CUMPLE)
            if not ver["verificado"]:
                motivos.append(f"{nombre} no se verificó contra lo declarado")
    if no_lineal:
        motivos.append("la relación entre los métodos no parece lineal (Cusum), y el sesgo "
                       "que da una recta no vale en todo el rango")
    if permitido is None or not estados:
        return None, motivos
    if NO_CUMPLE in estados:
        return NO_CUMPLE, motivos
    if NO_CONCLUYENTE in estados or NO_EVALUABLE in estados or no_lineal:
        return NO_CONCLUYENTE, motivos
    return CUMPLE, motivos


def _lectura(final, motivos, prec) -> str:
    if final is None:
        return ("Sin sesgo permitido no hay veredicto: el programa no sabe qué diferencia "
                "tolera este analito. Arriba está el sesgo en cada nivel con su intervalo; "
                "cargá el sesgo permitido (por ejemplo, el deseable por variabilidad "
                "biológica) para compararlos.")
    if final == CUMPLE:
        verificada = prec is not None and any(
            prec.crudo.get(k) is not None for k in ("repetibilidad", "intralaboratorio"))
        return ("El método CUMPLE: en todos los niveles evaluados el intervalo de confianza "
                "del sesgo queda entero dentro del sesgo permitido"
                + (", y la precisión verificó lo que declara el fabricante." if verificada
                   else "."))
    detalle = "; ".join(motivos)
    if final == NO_CUMPLE:
        return f"El método NO CUMPLE: {detalle}."
    return (f"NO CONCLUYENTE: {detalle}. Con estos datos el sesgo real puede estar de "
            "cualquiera de los dos lados del límite; hacen falta más muestras cerca de ese "
            "nivel para decidir.")


# ---------------- Valores y pasos ----------------

def _valores(final, filas, metodo, sesgos, ba, prec, comp, n, de_cuartiles, en_pct,
             permitido):
    valores = [
        Valor("Veredicto", final or "Sin criterio: no hay veredicto"),
        Valor("Pares usados", n),
        Valor("Recta (EP09c §6.2)", f"{NOMBRES[metodo]}: y = {_f(sesgos['intercepto'])} + "
                                    f"{_f(sesgos['pendiente'])}·x"),
    ]
    for i, fila in enumerate(filas):
        rotulo = f"Sesgo en {comp} = {num(fila['nivel'])}"
        if de_cuartiles:
            rotulo += f" (P{(25, 50, 75)[i]})"
        pct = (f" ({100 * fila['sesgo'] / fila['nivel']:.2f} %)" if fila["nivel"] else "")
        nota = pct.strip()
        if fila["permitido"] is not None:
            nota += (f"; permitido ±{num(fila['permitido'])}"
                     + (f" ({num(permitido)} %)" if en_pct else "") + f" → {fila['estado']}")
        valores.append(Valor(rotulo, fila["sesgo"], ic=fila["ic"], nota=nota))
    b = ba.crudo["bland_altman"]
    valores.append(Valor("Sesgo medio (Bland-Altman)", b["mean_difference"], ic=b["ci_mean"],
                         nota=f"diferencia = {ba.crudo['diferencia']}"))
    valores.append(Valor("Límites de acuerdo (Bland-Altman)",
                         f"{_f(b['loa_lower'])} a {_f(b['loa_upper'])}"))
    ccc = ba.crudo.get("ccc") or {}
    if not ccc.get("error") and "ccc" in ccc:
        valores.append(Valor("CCC de Lin", ccc["ccc"], nota=ccc["strength"].lower()))
    if prec is not None:
        e = prec.crudo["ep15"]
        valores.append(Valor("Repetibilidad (EP15)", e["s_r"],
                             nota="" if e["cv_r"] is None else f"CV = {e['cv_r']:.2f} %"))
        valores.append(Valor("Intralaboratorio (EP15)", e["s_wl"],
                             nota="" if e["cv_wl"] is None else f"CV = {e['cv_wl']:.2f} %"))
    return valores


def _paso_n(n) -> Supuesto:
    ok = n >= N_EP09
    return Supuesto(
        pregunta="¿Hay muestras suficientes?",
        medicion=f"{n} pares; EP09c pide al menos {N_EP09}",
        respuesta="Sí" if ok else "No",
        consecuencia=("Con este n los intervalos del sesgo pueden decidir." if ok else
                      "Con menos muestras los intervalos se abren y el veredicto tiende a "
                      "«no concluyente»: el cálculo es válido, pero discrimina menos."),
        ok=ok)


def _paso_recta(eleccion, metodo, comp) -> Supuesto:
    var = eleccion["variabilidad"]
    clase = var["clase"]
    norm = eleccion["normalidad"]
    medicion = (f"dispersión de las diferencias contra {comp}: {p_token(var['p_de'])} en "
                "unidades" + (f", {p_token(var['p_cv'])} en %" if var.get("p_cv") is not None
                              else "")
                + (f"; Shapiro-Wilk de las diferencias{' en %' if eleccion['en_pct'] else ''}: "
                   f"{p_token(norm['p'])}" if norm else ""))
    forma = {DE_CONSTANTE: "DE constante", CV_CONSTANTE: "CV constante"}.get(clase, "mixta")
    normales = "normales" if eleccion["normales"] else "no normales"
    porque = {
        DEMING: "Deming: diferencias normales con dispersión pareja (EP09c §6.2.1).",
        "deming_ponderado": "Deming ponderado: diferencias normales cuya dispersión crece "
                            "con la concentración (EP09c §6.2.2, apéndice B).",
        PASSING_BABLOK: "Passing-Bablok: sin suponer distribución, porque la dispersión es "
                        "mixta o las diferencias no son normales (EP09c §6.2.3 y §6.2.4).",
    }[metodo]
    return Supuesto(
        pregunta="¿Qué recta corresponde a estos datos?",
        medicion=medicion, respuesta=f"{forma}, diferencias {normales}",
        consecuencia=porque + " La otra recta se muestra abajo para comparar.",
        alternativa=("con diferencias normales y dispersión pareja o proporcional, "
                     "correspondería Deming." if metodo == PASSING_BABLOK else
                     "con dispersión mixta o diferencias no normales, correspondería "
                     "Passing-Bablok."))


def _paso_linealidad(cusum) -> Supuesto:
    pregunta = "¿La relación entre los métodos es lineal?"
    if cusum.get("error"):
        return Supuesto(pregunta, "prueba Cusum", "No evaluable", cusum["error"], ok=False)
    medicion = f"Cusum de Passing-Bablok: H = {_f(cusum['h'])}, {p_token(cusum['p'])}"
    if cusum["p"] < 0.05:
        return Supuesto(
            pregunta, medicion, "Se detectó desvío",
            "Los residuos se agrupan a lo largo de la recta: el sesgo que predice una recta "
            "no vale en todo el rango, y el veredicto no puede ser «cumple». Conviene "
            "evaluar por tramos de concentración.",
            alternativa="sin desvío, el sesgo de la recta valdría en todo el rango.", ok=False)
    return Supuesto(pregunta, medicion, "No se detectó desvío",
                    "El sesgo que predice la recta vale en todo el rango medido.",
                    alternativa="con desvío, la recta no describiría los datos.")


def _paso_criterio(permitido, en_pct, de_cuartiles, comp) -> Supuesto:
    niveles = (f"los cuartiles de {comp} (no se cargaron niveles de decisión)" if de_cuartiles
               else "los niveles de decisión cargados")
    if permitido is None:
        return Supuesto(
            pregunta="¿Contra qué se juzga el sesgo?",
            medicion=f"sin sesgo permitido; niveles: {niveles}",
            respuesta="Sin criterio",
            consecuencia="Se informa el sesgo en cada nivel, pero no hay veredicto.",
            alternativa="con un sesgo permitido, cada nivel se declararía cumple, no cumple "
                        "o no concluyente.", ok=False)
    return Supuesto(
        pregunta="¿Contra qué se juzga el sesgo?",
        medicion=(f"sesgo permitido ±{num(permitido)}{' %' if en_pct else ' unidades'}; "
                  f"niveles: {niveles}"),
        respuesta="Criterio cargado",
        consecuencia=("Cumple si todo el IC 95 % del sesgo cae dentro de ± el permitido; no "
                      "cumple si cae todo afuera; no concluyente si lo cruza."),
        ok=not de_cuartiles)


def _paso_precision(prec) -> Supuesto:
    ver_r, ver_wl = prec.crudo.get("repetibilidad"), prec.crudo.get("intralaboratorio")
    e = prec.crudo["ep15"]
    medicion = (f"s_R = {_f(e['s_r'])}, s_WL = {_f(e['s_wl'])} ({e['corridas']} corridas, "
                f"N = {e['n']})")
    if ver_r is None and ver_wl is None:
        return Supuesto("¿La precisión verifica lo declarado? (EP15-A3)", medicion,
                        "Sin declaración",
                        "Se estimó la precisión, pero sin lo que declara el fabricante no "
                        "entra en el veredicto.", ok=False)
    fallas = [n for n, v in (("repetibilidad", ver_r), ("intralaboratorio", ver_wl))
              if v is not None and not v["verificado"]]
    return Supuesto(
        "¿La precisión verifica lo declarado? (EP15-A3)", medicion,
        "Sí" if not fallas else "No: " + " y ".join(fallas),
        ("Dentro de los límites de verificación." if not fallas else
         "Supera el límite de verificación: el método no rinde la precisión que declara el "
         "fabricante."),
        ok=not fallas)


def _figura_sesgo(x, sesgos, filas, permitido, en_pct, comp, cand):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 5.5))
    xs = np.linspace(float(np.min(x)), float(np.max(x)), 200)
    b, a = sesgos["pendiente"], sesgos["intercepto"]
    ax.plot(xs, a + (b - 1) * xs, color='#4f6ef7', lw=2,
            label=f"Sesgo según {NOMBRES[sesgos['metodo']]}")
    if permitido is not None:
        banda = permitido * xs / 100 if en_pct else np.full_like(xs, permitido)
        ax.fill_between(xs, -banda, banda, color='#22c55e', alpha=0.12,
                        label=f"Sesgo permitido ±{permitido:g}{' %' if en_pct else ''}")
    colores = {CUMPLE: '#16a34a', NO_CUMPLE: '#dc2626', NO_CONCLUYENTE: '#d97706'}
    for fila in filas:
        c = colores.get(fila["estado"], '#2c3650')
        lo, hi = fila["ic"]
        ax.errorbar([fila["nivel"]], [fila["sesgo"]],
                    yerr=[[fila["sesgo"] - lo], [hi - fila["sesgo"]]],
                    fmt='o', color=c, capsize=5, ms=7, zorder=3)
    ax.axhline(0, color='#8892a4', lw=1, ls='--')
    ax.set_xlabel(f"{comp} (comparativo)")
    ax.set_ylabel(f"Sesgo ({cand} − {comp})")
    ax.set_title("Sesgo en los niveles de decisión, con su IC 95 %", fontweight='bold')
    ax.legend(framealpha=0.9)
    fig.tight_layout()
    return fig
