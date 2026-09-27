"""Precisión y veracidad por CLSI EP15-A3: la repetibilidad del asistente B.

Cada columna de la hoja es una corrida (un día) y sus filas, las réplicas de
esa corrida. Las celdas vacías son réplicas que faltan, no pares rotos: una
corrida con 4 réplicas entra igual (la norma lo contempla con n0).
"""
from __future__ import annotations

import math

import numpy as np

from src.core.ep15 import (
    CORRIDAS_NORMA, REPLICAS_NORMA, df_intralab, precision_ep15 as precision_core,
    verificar, veracidad,
)
from src.resultado.citas import ficha
from src.resultado.datos import columnas_faltantes
from src.resultado.modelo import Entrada, Figura, Metodo, Resultado, Supuesto, Valor

INCERTIDUMBRES = ("ninguna", "u", "U", "pares")


def _f(x, dec=4) -> str:
    return Valor("", x, decimales=dec).texto()


def _numero(opciones, clave):
    """Un número opcional de las opciones: None si no se declaró."""
    v = opciones.get(clave)
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    v = float(v)
    return None if math.isnan(v) else v


def precision_ep15(df, corridas, opciones=None) -> Resultado:
    """EP15-A3: repetibilidad, intralaboratorio y, si hay valor asignado, sesgo.

    `opciones`:
      declaracion:    "de" | "cv" — en qué vienen σR y σWL del fabricante
      sigma_r, sigma_wl: lo declarado (None = no se declaró)
      n_muestras:     materiales en el estudio (corrige α por multiplicidad)
      valor_asignado: None si no hay
      incertidumbre:  "ninguna" | "u" | "U" | "pares" (escenarios de §3.3)
      u:              u estándar, U expandida o DE del grupo de pares
      k:              factor de cobertura de U
      n_lab:          laboratorios del grupo de pares
    """
    opciones = opciones or {}
    if isinstance(corridas, str):
        corridas = [corridas]
    corridas = list(dict.fromkeys(corridas))
    titulo = "Precisión y veracidad (CLSI EP15-A3)"
    if len(corridas) < 2:
        return Resultado.rechazo("precision_ep15", titulo,
                                 "Hacen falta al menos 2 corridas: una columna por día, con "
                                 "las réplicas de ese día en las filas.")
    falta = columnas_faltantes(df, *corridas)
    if falta:
        return Resultado.rechazo("precision_ep15", titulo, falta)
    try:
        sigma_r = _numero(opciones, "sigma_r")
        sigma_wl = _numero(opciones, "sigma_wl")
        va = _numero(opciones, "valor_asignado")
        n_muestras = int(opciones.get("n_muestras") or 1)
    except (TypeError, ValueError):
        return Resultado.rechazo("precision_ep15", titulo,
                                 "Lo declarado y el valor asignado tienen que ser números.")
    if n_muestras < 1:
        return Resultado.rechazo("precision_ep15", titulo,
                                 "El número de muestras del estudio tiene que ser al menos 1.")
    for nombre, v in (("σR", sigma_r), ("σWL", sigma_wl)):
        if v is not None and v <= 0:
            return Resultado.rechazo("precision_ep15", titulo,
                                     f"{nombre} declarado tiene que ser positivo.")

    datos = [df[c].to_numpy(dtype=float) for c in corridas]
    res = precision_core(datos)
    entrada = Entrada(columnas=tuple(corridas), n=res.get("n", 0) if isinstance(res, dict) else 0)
    rechazo = Resultado.rechazo_del_core("precision_ep15", titulo, res, entrada)
    if rechazo is not None:
        return rechazo

    en_cv = opciones.get("declaracion", "de") == "cv"
    u = "%" if en_cv else ""
    obs_r = res["cv_r"] if en_cv else res["s_r"]
    obs_wl = res["cv_wl"] if en_cv else res["s_wl"]
    if en_cv and obs_r is None:
        return Resultado.rechazo("precision_ep15", titulo,
                                 "La media es 0: el CV no está definido. Declará en DE.")
    advertencias = list(res["avisos"])
    D, N = res["corridas"], res["n"]

    valores = [
        Valor("Media", res["media"]),
        Valor("Corridas × réplicas", f"{D} × {_rango(res['replicas'])} (N = {N})"),
        Valor("Repetibilidad (s_R)", res["s_r"], nota=_cv(res["cv_r"])),
        Valor("Entre corridas (s_B)", res["s_b"], nota=_cv(res["cv_b"])),
        Valor("Intralaboratorio (s_WL)", res["s_wl"], nota=_cv(res["cv_wl"])),
        Valor("MS entre corridas", res["ms_entre"], nota=f"{res['df_entre']} gl"),
        Valor("MS dentro de la corrida", res["ms_dentro"], nota=f"{res['df_dentro']} gl"),
    ]

    supuestos = [_paso_diseno(res), _paso_grubbs(res)]
    lecturas = []
    ver_r = ver_wl = None
    if sigma_r is not None:
        ver_r = verificar(obs_r, sigma_r, res["df_dentro"], n_muestras)
        valores += [Valor("Repetibilidad declarada", sigma_r, unidad=u),
                    Valor("Límite de verificación (UVL) de la repetibilidad", ver_r["uvl"],
                          unidad=u, nota=f"F = {_f(ver_r['factor'])}, {ver_r['df']:g} gl")]
        supuestos.append(_paso_verificacion("repetibilidad", obs_r, ver_r, u))
    if sigma_wl is not None:
        if sigma_r is not None:
            rho, de_donde = sigma_wl / sigma_r, "de lo declarado"
        else:
            rho, de_donde = res["s_wl"] / res["s_r"], "de lo observado (no se declaró σR)"
        df_wl = df_intralab(max(rho, 1.0), D, res["n0"], N)
        ver_wl = verificar(obs_wl, sigma_wl, df_wl, n_muestras)
        valores += [Valor("Intralaboratorio declarada", sigma_wl, unidad=u),
                    Valor("Límite de verificación (UVL) intralaboratorio", ver_wl["uvl"],
                          unidad=u, nota=f"F = {_f(ver_wl['factor'])}, {df_wl:g} gl "
                                         f"(ρ = σWL/σR {de_donde})")]
        supuestos.append(_paso_verificacion("precisión intralaboratorio", obs_wl, ver_wl, u))
    for nombre, ver in (("repetibilidad", ver_r), ("precisión intralaboratorio", ver_wl)):
        if ver is None:
            continue
        if ver["verificado"]:
            lecturas.append(f"La {nombre} declarada por el fabricante quedó verificada.")
        else:
            lecturas.append(f"La {nombre} NO se verificó: supera el límite de verificación, "
                            "más de lo que explica el azar en un estudio de este tamaño.")
    if sigma_r is None and sigma_wl is None:
        lecturas.append("Sin imprecisión declarada no hay nada que verificar: los números "
                        "de arriba son la estimación del laboratorio.")

    verac = None
    if va is not None:
        verac, error = _veracidad(res, va, opciones, n_muestras)
        if error:
            return Resultado.rechazo("precision_ep15", titulo, error, entrada)
        valores += [
            Valor("Valor asignado", va),
            Valor("Sesgo (media − valor asignado)", verac["sesgo"],
                  nota=(f"({verac['sesgo_pct']:.2f} %)" if verac["sesgo_pct"] is not None
                        else "")),
            Valor("Intervalo de verificación",
                  f"{_f(verac['intervalo'][0])} a {_f(verac['intervalo'][1])}",
                  nota=f"valor asignado ± {_f(verac['m'], 3)} · {_f(verac['se_c'])}, "
                       f"{verac['df_c']:g} gl"),
        ]
        supuestos.append(_paso_veracidad(verac))
        if verac["dentro"]:
            lecturas.append(f"La media ({_f(verac['media'])}) cae dentro del intervalo de "
                            "verificación: el sesgo no se distingue del azar.")
        else:
            lecturas.append(f"La media ({_f(verac['media'])}) cae fuera del intervalo de "
                            f"verificación: el sesgo de {_f(verac['sesgo'])} no se explica "
                            "por el azar. Compararlo con el sesgo permitido del analito.")

    f = ficha("precision_ep15")
    return Resultado(
        analisis="precision_ep15",
        titulo=f"{titulo} — {D} corridas",
        entrada=entrada, valores=valores,
        metodo=Metodo("ANOVA de un factor (la corrida), EP15-A3",
                      "Separa la variación dentro de cada corrida (repetibilidad) de la "
                      "variación entre corridas; las dos juntas son la precisión "
                      "intralaboratorio, la que ve un paciente medido en días distintos."),
        supuestos=supuestos, formula=f.formula, citas=list(f.citas),
        lectura=" ".join(lecturas),
        matiz=("Verificar no es validar: el protocolo de 5 días tiene poca potencia para "
               "rechazar una declaración (lo dice la propia norma), y que se verifique no "
               "prueba que la precisión alcance para el uso clínico: eso lo decide el "
               "requisito de calidad del analito. Lo mismo el sesgo: que no se distinga del "
               "azar no quiere decir que sea chico."),
        advertencias=advertencias,
        figuras=[Figura("Corridas", lambda: _figura_corridas(res, corridas))],
        crudo={"ep15": res, "repetibilidad": ver_r, "intralaboratorio": ver_wl,
               "veracidad": verac})


def _rango(replicas) -> str:
    lo, hi = min(replicas), max(replicas)
    return str(lo) if lo == hi else f"{lo}-{hi}"


def _cv(cv) -> str:
    return "" if cv is None else f"CV = {cv:.2f} %"


def _veracidad(res, va, opciones, n_muestras):
    tipo = opciones.get("incertidumbre", "ninguna")
    if tipo not in INCERTIDUMBRES:
        return None, f"Tipo de incertidumbre desconocido: «{tipo}»."
    try:
        u = _numero(opciones, "u")
        k = _numero(opciones, "k") or 2.0
        n_lab = int(opciones.get("n_lab") or 0)
    except (TypeError, ValueError):
        return None, "La incertidumbre del valor asignado tiene que ser un número."
    se_rm, df_rm = 0.0, math.inf
    if tipo != "ninguna":
        if u is None or u < 0:
            return None, "Falta la incertidumbre del valor asignado (o es negativa)."
        if tipo == "u":
            se_rm = u
        elif tipo == "U":
            if k <= 0:
                return None, "El factor de cobertura k tiene que ser positivo."
            se_rm = u / k
        else:
            if n_lab < 2:
                return None, "Con un grupo de pares hacen falta al menos 2 laboratorios."
            se_rm, df_rm = u / math.sqrt(n_lab), n_lab - 1
    v = veracidad(res["media"], res["s_r"], res["s_wl"], res["corridas"], res["n0"], va,
                  se_rm=se_rm, df_rm=df_rm, n_muestras=n_muestras)
    v["escenario"] = tipo
    return v, None


def _paso_diseno(res) -> Supuesto:
    D, rep = res["corridas"], res["replicas"]
    ok = D >= CORRIDAS_NORMA and min(rep) >= REPLICAS_NORMA
    return Supuesto(
        pregunta="¿El diseño es el de la norma?",
        medicion=f"{D} corridas, {_rango(rep)} réplicas por corrida",
        respuesta="Sí" if ok else "No",
        consecuencia=("5 corridas con 5 réplicas: el diseño para el que están hechos los "
                      "límites de verificación." if ok else
                      f"EP15-A3 pide al menos {CORRIDAS_NORMA} corridas con "
                      f"{REPLICAS_NORMA} réplicas. Se calcula igual, pero con menos datos los "
                      "límites de verificación suben y el estudio discrimina menos."),
        ok=ok)


def _paso_grubbs(res) -> Supuesto:
    g = res["grubbs"]
    pregunta = "¿Hay un resultado atípico?"
    if g is None:
        return Supuesto(pregunta, "Grubbs: no evaluable (sin dispersión)", "No evaluable",
                        "No se pudo buscar atípicos.", ok=False)
    medicion = (f"Grubbs sobre los {res['n']} resultados: G = {_f(g['g'], 3)} para "
                f"{_f(g['valor'])}, crítico {_f(g['g_critico'], 3)}")
    if g["atipico"]:
        return Supuesto(
            pregunta, medicion, "Sí",
            f"{_f(g['valor'])} pasa el límite de Grubbs. No se sacó: la norma pide "
            "investigar la causa (error de pipeteo, burbuja, alarma del equipo) y excluirlo "
            "solo si se la encuentra. Si se excluye, se borra la celda y se vuelve a correr.",
            alternativa="sin atípicos, los estimadores no dependerían de un solo resultado.",
            ok=False)
    return Supuesto(pregunta, medicion, "No",
                    "Ningún resultado pasa el límite de Grubbs.",
                    alternativa="uno que lo pasara habría que investigarlo antes de seguir.")


def _paso_verificacion(nombre, obs, ver, u) -> Supuesto:
    medicion = (f"observada {_f(obs)}{u}, declarada {_f(ver['declarado'])}{u}, "
                f"UVL {_f(ver['uvl'])}{u}")
    pregunta = f"¿La {nombre} observada es compatible con la declarada?"
    if ver["debajo"]:
        return Supuesto(pregunta, medicion, "Sí",
                        "No supera lo declarado: verificada sin necesitar el límite.",
                        alternativa="si la superara, todavía podría ser azar: se compararía "
                                    "con el UVL.")
    if ver["verificado"]:
        return Supuesto(pregunta, medicion, "Sí",
                        "Supera lo declarado pero no el límite de verificación: la diferencia "
                        "está dentro de lo que da el azar en un estudio de este tamaño.",
                        alternativa="si superara el UVL, no se verificaría.")
    return Supuesto(pregunta, medicion, "No",
                    "Supera el límite de verificación: el 95 % de los estudios de este tamaño "
                    "darían menos si la declaración fuera cierta. Revisar el procedimiento "
                    "o consultar al fabricante (EP15-A3 §2.3.6).",
                    alternativa="debajo del UVL, se habría verificado.", ok=False)


def _paso_veracidad(v) -> Supuesto:
    escenarios = {"ninguna": "sin incertidumbre del valor asignado (escenarios D y E)",
                  "u": "incertidumbre estándar u (escenario A)",
                  "U": "incertidumbre expandida U/k (escenario A)",
                  "pares": "grupo de pares, DE/√laboratorios (escenarios B y C)"}
    lo, hi = v["intervalo"]
    return Supuesto(
        pregunta="¿El sesgo se distingue del azar?",
        medicion=(f"media {_f(v['media'])} contra el intervalo {_f(lo)} a {_f(hi)} "
                  f"({escenarios[v['escenario']]})"),
        respuesta="No" if v["dentro"] else "Sí",
        consecuencia=("La media cae dentro del intervalo de verificación." if v["dentro"] else
                      "La media cae fuera del intervalo: hay sesgo. Si importa o no, lo dice "
                      "el sesgo permitido del analito (EP15-A3 §3.6)."),
        alternativa=("fuera del intervalo, el sesgo no se explicaría por el azar."
                     if v["dentro"] else "dentro del intervalo, no se distinguiría del azar."),
        ok=v["dentro"])


def _figura_corridas(res, nombres):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5))
    for i, (vals, media) in enumerate(zip(res["valores"], res["medias_corrida"]), start=1):
        ax.scatter(np.full(len(vals), i), vals, alpha=0.6, c='#4f6ef7',
                   edgecolors='white', s=50, zorder=3)
        ax.plot([i - 0.25, i + 0.25], [media, media], color='#2c3650', lw=2)
    ax.axhline(res["media"], color='#22c55e', lw=1.5, ls='--',
               label=f"Media general: {res['media']:.3f}")
    ax.set_xticks(range(1, len(nombres) + 1), [str(n) for n in nombres])
    ax.set_xlabel("Corrida")
    ax.set_ylabel("Resultado")
    ax.set_title(f"Réplicas por corrida — s_R = {res['s_r']:.3g}, s_WL = {res['s_wl']:.3g}",
                 fontweight='bold')
    ax.legend(framealpha=0.9)
    fig.tight_layout()
    return fig
