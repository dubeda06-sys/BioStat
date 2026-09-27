"""El asistente B, «Validar un método»: CLSI EP09c + EP15-A3 en un veredicto.

Corre lo que un laboratorio corre a mano cuando verifica un método nuevo contra
el que ya usa: Bland-Altman con el CCC, la recta que corresponde según EP09c
§6.2 (y la otra, para comparar), el sesgo en los niveles de decisión médica
con su intervalo y, si se cargaron corridas, la precisión por EP15-A3 y el
sesgo contra el valor asignado del material. Después compara el sesgo con el
sesgo permitido, y/o el error total con el TEa, y da un solo veredicto.

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
      tea:              error total permitido (misma escala que el sesgo
                        permitido), o None; criterio alternativo o adicional
      corridas:         columnas de EP15 (una por día); vacío = sin precisión
      declaracion, sigma_r, sigma_wl, n_muestras: lo declarado por el fabricante
      valor_asignado, incertidumbre, u, k, n_lab: el material de las corridas,
                        para el sesgo de EP15-A3 §3 (como en «Precisión EP15»)
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
        tea = _numero(opciones.get("tea"))
        lam = _numero(opciones.get("lambda")) or 1.0
        niveles = [float(v) for v in (opciones.get("niveles") or []) if _numero(v) is not None]
    except (TypeError, ValueError):
        return Resultado.rechazo(ANALISIS, titulo,
                                 "El sesgo permitido, el TEa, los niveles y λ tienen que "
                                 "ser números.")
    if permitido is not None and permitido <= 0:
        return Resultado.rechazo(ANALISIS, titulo, "El sesgo permitido tiene que ser positivo.")
    if tea is not None and tea <= 0:
        return Resultado.rechazo(ANALISIS, titulo, "El TEa tiene que ser positivo.")
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
        # Sin los vacíos: una clave presente con None le gana al valor por
        # defecto del constructor de EP15 («incertidumbre» = "ninguna").
        prec = precision_ep15(df, corridas, {k: opciones[k] for k in (
            "declaracion", "sigma_r", "sigma_wl", "n_muestras", "valor_asignado",
            "incertidumbre", "u", "k", "n_lab") if opciones.get(k) is not None})
        if not prec.ok:
            advertencias.append(f"La precisión (EP15) no se pudo calcular: {prec.error}")
            prec = None

    elegido, otro = (pb, dem) if metodo == PASSING_BABLOK else (dem, pb)
    partes += [p for p in (elegido, otro) if p.ok]
    if prec is not None:
        partes.append(prec)

    # 6) El error total contra el TEa, y el sesgo contra el valor asignado.
    error_total = None if tea is None else _error_total(filas, prec, tea, en_pct)
    verac = prec.crudo.get("veracidad") if prec is not None else None

    final, motivos = _veredicto_final(filas, prec, no_lineal, permitido, error_total, verac,
                                      en_pct)
    valores = _valores(final, filas, metodo, sesgos, ba, prec, comparativo, len(x), de_cuartiles,
                       en_pct, permitido, error_total, verac)
    supuestos = [
        _paso_n(len(x)),
        _paso_recta(eleccion, metodo, comparativo),
        _paso_linealidad(cusum),
        _paso_criterio(permitido, en_pct, de_cuartiles, comparativo, tea),
    ]
    if error_total is not None:
        supuestos.append(_paso_error_total(error_total, tea, en_pct))
    if prec is not None:
        supuestos.append(_paso_precision(prec))
    if verac is not None:
        supuestos.append(_paso_veracidad(verac, permitido, en_pct))

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
        lectura=_lectura(final, motivos, prec, permitido, tea, verac),
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
               "veredicto": final, "motivos": motivos, "cusum": cusum,
               "error_total": error_total, "veracidad": verac},
        partes=partes)


# ---------------- El veredicto ----------------

Z_ERROR_TOTAL = 1.65


def _error_total(filas, prec, tea, en_pct):
    """Error total en cada nivel: |sesgo| + 1,65·s_WL (Westgard, Carey y Wold 1974).

    La imprecisión es la intralaboratorio de EP15, la que ve un paciente de un
    día a otro. EP15 la mide en un solo nivel; para llevarla a los demás se
    supone lo mismo que dice la escala del TEa: CV constante si viene en %, DE
    constante si viene en unidades. El veredicto sigue la lógica del sesgo:
    con el extremo del IC del sesgo más lejos de cero el error total queda
    dentro del TEa → cumple; con el más cerca ya lo pasa → no cumple; si no,
    no concluyente. La incertidumbre de s_WL no entra, y se dice.
    """
    if prec is None:
        return {"error": "el error total necesita la imprecisión intralaboratorio: "
                         "tildá las corridas de EP15"}
    e = prec.crudo["ep15"]
    if en_pct and e["cv_wl"] is None:
        return {"error": "la media de las corridas es 0: no hay CV para llevar la "
                         "imprecisión a cada nivel"}
    z = Z_ERROR_TOTAL
    niveles = []
    for f in filas:
        s = abs(e["cv_wl"] * f["nivel"] / 100) if en_pct else e["s_wl"]
        tea_u = abs(tea * f["nivel"] / 100) if en_pct else tea
        lo, hi = f["ic"]
        te = abs(f["sesgo"]) + z * s
        if not (np.isfinite(lo) and np.isfinite(hi)) or tea_u <= 0:
            estado, rango = NO_EVALUABLE, (math.nan, math.nan)
        else:
            cerca = (0.0 if lo <= 0 <= hi else min(abs(lo), abs(hi))) + z * s
            lejos = max(abs(lo), abs(hi)) + z * s
            estado = (CUMPLE if lejos <= tea_u else
                      NO_CUMPLE if cerca > tea_u else NO_CONCLUYENTE)
            rango = (cerca, lejos)
        niveles.append({"nivel": f["nivel"], "s": s, "te": te, "te_rango": rango,
                        "tea": tea_u, "estado": estado})
    return {"z": z, "s_wl": e["s_wl"], "cv_wl": e["cv_wl"], "niveles": niveles}


def _estado_veracidad(verac, permitido, en_pct):
    """EP15-A3 §3.6: dentro del intervalo de verificación, el sesgo no se
    distingue del azar. Fuera, se compara con el sesgo permitido: puede ser real
    y aun así aceptable."""
    if verac["dentro"]:
        return CUMPLE
    if permitido is None:
        return NO_CONCLUYENTE
    perm = abs(permitido * verac["valor_asignado"] / 100) if en_pct else permitido
    return CUMPLE if abs(verac["sesgo"]) <= perm else NO_CUMPLE


def _veredicto_final(filas, prec, no_lineal, permitido, error_total=None, verac=None,
                     en_pct=True):
    """(veredicto, motivos). Sin sesgo permitido ni TEa no hay veredicto."""
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
    if error_total is not None:
        if error_total.get("error"):
            estados.append(NO_EVALUABLE)
            motivos.append(error_total["error"])
        else:
            for t in error_total["niveles"]:
                estados.append(t["estado"])
                if t["estado"] == NO_CUMPLE:
                    motivos.append(f"el error total en {num(t['nivel'])} supera el TEa")
                elif t["estado"] == NO_CONCLUYENTE:
                    motivos.append(f"en {num(t['nivel'])} el error total puede quedar de "
                                   "cualquiera de los dos lados del TEa")
                elif t["estado"] == NO_EVALUABLE:
                    motivos.append(f"en {num(t['nivel'])} el error total no se pudo evaluar")
    if verac is not None:
        estado = _estado_veracidad(verac, permitido, en_pct)
        estados.append(estado)
        if estado == NO_CUMPLE:
            motivos.append("el sesgo contra el valor asignado del material (EP15) supera "
                           "el permitido")
        elif estado == NO_CONCLUYENTE:
            motivos.append("el sesgo contra el valor asignado del material (EP15) se "
                           "distingue del azar, y sin sesgo permitido no se puede juzgar")
    if no_lineal:
        motivos.append("la relación entre los métodos no parece lineal (Cusum), y el sesgo "
                       "que da una recta no vale en todo el rango")
    if (permitido is None and error_total is None) or not estados:
        return None, motivos
    if NO_CUMPLE in estados:
        return NO_CUMPLE, motivos
    if NO_CONCLUYENTE in estados or NO_EVALUABLE in estados or no_lineal:
        return NO_CONCLUYENTE, motivos
    return CUMPLE, motivos


def _lectura(final, motivos, prec, permitido=None, tea=None, verac=None) -> str:
    if final is None:
        return ("Sin sesgo permitido ni error total permitido (TEa) no hay veredicto: el "
                "programa no sabe qué diferencia tolera este analito. Arriba está el sesgo "
                "en cada nivel con su intervalo; cargá el sesgo permitido (por ejemplo, el "
                "deseable por variabilidad biológica) o el TEa para compararlos.")
    if final == CUMPLE:
        verificada = prec is not None and any(
            prec.crudo.get(k) is not None for k in ("repetibilidad", "intralaboratorio"))
        partes = []
        if permitido is not None:
            partes.append("el intervalo de confianza del sesgo queda entero dentro del "
                          "sesgo permitido")
        if tea is not None:
            partes.append("el error total, aun con el extremo del intervalo del sesgo más "
                          "alejado, queda dentro del TEa")
        extra = ""
        if verificada:
            extra += ", y la precisión verificó lo que declara el fabricante"
        if verac is not None:
            extra += ("; el sesgo contra el valor asignado del material no se distingue "
                      "del azar" if verac["dentro"] else
                      "; el sesgo contra el valor asignado del material es real pero "
                      "queda dentro del permitido")
        return ("El método CUMPLE: en todos los niveles evaluados "
                + "; y ".join(partes) + extra + ".")
    detalle = "; ".join(motivos)
    if final == NO_CUMPLE:
        return f"El método NO CUMPLE: {detalle}."
    return (f"NO CONCLUYENTE: {detalle}. Con estos datos el sesgo real puede estar de "
            "cualquiera de los dos lados del límite; hacen falta más muestras cerca de ese "
            "nivel para decidir.")


# ---------------- Valores y pasos ----------------

def _valores(final, filas, metodo, sesgos, ba, prec, comp, n, de_cuartiles, en_pct,
             permitido, error_total=None, verac=None):
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
    if error_total is not None and not error_total.get("error"):
        for t in error_total["niveles"]:
            valores.append(Valor(
                f"Error total en {comp} = {num(t['nivel'])}", t["te"],
                nota=(f"|sesgo| + 1,65·s_WL, con s_WL = {num(t['s'])}; TEa "
                      f"±{num(t['tea'])} → {t['estado']}")))
    if verac is not None:
        lo_v, hi_v = verac["intervalo"]
        pct_v = (f" ({verac['sesgo_pct']:.2f} %)" if verac.get("sesgo_pct") is not None
                 else "")
        valores.append(Valor(
            "Sesgo contra el valor asignado (EP15)", verac["sesgo"],
            nota=(f"{pct_v.strip()} media {num(verac['media'])}, valor asignado "
                  f"{num(verac['valor_asignado'])}, intervalo de verificación "
                  f"{num(lo_v)} a {num(hi_v)}").strip()))
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


def _paso_criterio(permitido, en_pct, de_cuartiles, comp, tea=None) -> Supuesto:
    niveles = (f"los cuartiles de {comp} (no se cargaron niveles de decisión)" if de_cuartiles
               else "los niveles de decisión cargados")
    u = " %" if en_pct else " unidades"
    if permitido is None and tea is not None:
        return Supuesto(
            pregunta="¿Contra qué se juzga el sesgo?",
            medicion=f"error total permitido (TEa) ±{num(tea)}{u}; niveles: {niveles}",
            respuesta="Error total (TEa)",
            consecuencia=("Se juzga el error total, sesgo más imprecisión, en vez del "
                          "sesgo solo: es el criterio de Westgard, Carey y Wold (1974)."),
            alternativa="con un sesgo permitido, se juzgaría además el sesgo solo.",
            ok=not de_cuartiles)
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
        medicion=(f"sesgo permitido ±{num(permitido)}{u}"
                  + (f" y error total permitido (TEa) ±{num(tea)}{u}" if tea is not None
                     else "") + f"; niveles: {niveles}"),
        respuesta="Criterio cargado",
        consecuencia=("Cumple si todo el IC 95 % del sesgo cae dentro de ± el permitido; no "
                      "cumple si cae todo afuera; no concluyente si lo cruza."),
        ok=not de_cuartiles)


def _paso_error_total(error_total, tea, en_pct) -> Supuesto:
    pregunta = "¿El error total queda dentro del TEa?"
    if error_total.get("error"):
        return Supuesto(pregunta, "sin imprecisión de EP15", "No evaluable",
                        f"No se puede: {error_total['error']}.",
                        alternativa="con corridas de EP15, TE = |sesgo| + 1,65·s_WL en cada "
                                    "nivel.", ok=False)
    cv = error_total["cv_wl"]
    medicion = (f"TE = |sesgo| + 1,65·s_WL; s_WL de EP15 = {_f(error_total['s_wl'])}"
                + (f" (CV {cv:.2f} %)" if cv is not None else "")
                + f", llevada a cada nivel con {'CV' if en_pct else 'DE'} constante")
    malos = [t for t in error_total["niveles"] if t["estado"] != CUMPLE]
    return Supuesto(
        pregunta, medicion,
        "Sí, en todos los niveles" if not malos else
        "No en " + ", ".join(f"{num(t['nivel'])} ({t['estado']})" for t in malos),
        ("Cumple si el error total, calculado con el extremo del intervalo del sesgo más "
         "lejos de cero, queda dentro del TEa; no cumple si ya lo pasa con el extremo más "
         "cercano. 1,65 es el cuantil del 95 % a una cola (Westgard, Carey y Wold 1974). "
         "No suma la incertidumbre de s_WL, que sale de 5 corridas."),
        alternativa="con el sesgo solo, el criterio sería el sesgo permitido.",
        ok=not malos)


def _paso_veracidad(verac, permitido, en_pct) -> Supuesto:
    lo, hi = verac["intervalo"]
    estado = _estado_veracidad(verac, permitido, en_pct)
    if verac["dentro"]:
        consecuencia = ("La media de las corridas cae dentro del intervalo de "
                        "verificación: el sesgo no se distingue del azar (EP15-A3 §3).")
    elif estado == CUMPLE:
        consecuencia = ("La media cae fuera del intervalo: el sesgo es real, pero queda "
                        "dentro del sesgo permitido (EP15-A3 §3.6).")
    elif estado == NO_CUMPLE:
        consecuencia = ("La media cae fuera del intervalo y el sesgo supera el permitido: "
                        "el método no reproduce el valor asignado del material.")
    else:
        consecuencia = ("La media cae fuera del intervalo: el sesgo es real, y sin sesgo "
                        "permitido no se puede decir si importa.")
    return Supuesto(
        pregunta="¿El sesgo contra el valor asignado del material es aceptable? (EP15-A3)",
        medicion=(f"media {_f(verac['media'])} contra el valor asignado "
                  f"{_f(verac['valor_asignado'])}; intervalo de verificación {_f(lo)} a "
                  f"{_f(hi)}"),
        respuesta={CUMPLE: "Sí", NO_CUMPLE: "No"}.get(estado, "No se puede juzgar"),
        consecuencia=consecuencia,
        alternativa=("fuera del intervalo, se compararía el sesgo con el permitido."
                     if verac["dentro"] else
                     "dentro del intervalo, no se distinguiría del azar."),
        ok=estado == CUMPLE)


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
