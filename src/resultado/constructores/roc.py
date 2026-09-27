"""Curvas ROC: la curva de una prueba y la comparación de dos AUC.

La curva trae el gráfico de sensibilidad y especificidad según el umbral (el
índice de Youden), que antes vivía mal nombrado como «Youden plot» en el menú de
comparación de métodos.
"""
from __future__ import annotations

import numpy as np
from scipy import stats

from src.core.diagnostic_tests import compare_two_auc, diagnostic_test
from src.core.roc import auc, auc_delong, optimal_threshold, roc_curve
from src.resultado.citas import ficha
from src.resultado.datos import columnas_faltantes, filas_completas
from src.resultado.lenguaje import fmt_p, p_token
from src.resultado.modelo import Figura, Metodo, Resultado, Supuesto, Valor

EJEMPLOS = {"comparar_auc": {"auc1": 0.82, "ee1": 0.04, "n1": 120,
                             "auc2": 0.74, "ee2": 0.05, "n2": 110}}


def _f(x, dec=4) -> str:
    return Valor("", x, decimales=dec).texto()


def _armar(analisis, titulo, entrada, valores, metodo, supuestos, lectura, matiz,
           advertencias=(), figuras=(), crudo=None) -> Resultado:
    f = ficha(analisis)
    return Resultado(analisis=analisis, titulo=titulo, entrada=entrada, valores=valores,
                     metodo=metodo, supuestos=list(supuestos), formula=f.formula,
                     citas=list(f.citas), lectura=lectura, matiz=matiz,
                     advertencias=list(advertencias), figuras=list(figuras), crudo=crudo or {})


def escala_auc(a) -> str:
    """Hosmer y Lemeshow (2000): < 0,7 pobre; 0,7-0,8 aceptable; 0,8-0,9 excelente."""
    return ("pobre" if a < 0.7 else "aceptable" if a < 0.8 else "excelente" if a < 0.9
            else "sobresaliente")


def curva_roc(df, score, etiqueta, opciones=None) -> Resultado:
    """Variable 1 = el resultado de la prueba; Variable 3 = la verdad (1 enfermo, 0 sano)."""
    titulo = f"Curva ROC — {score}"
    falta = columnas_faltantes(df, score, etiqueta)
    if falta:
        return Resultado.rechazo("curva_roc", titulo, falta)
    if score == etiqueta:
        return Resultado.rechazo("curva_roc", titulo, "La prueba y la etiqueta son la misma "
                                                      "columna.")
    pares, entrada = filas_completas(df, score, etiqueta)
    try:
        s = pares[score].to_numpy(dtype=float)
        y = pares[etiqueta].to_numpy(dtype=float)
    except (TypeError, ValueError):
        return Resultado.rechazo("curva_roc", titulo, "La prueba y la etiqueta tienen que ser "
                                                      "números (la etiqueta, 0/1).", entrada)
    clases = sorted(set(y.tolist()))
    if not set(clases) <= {0.0, 1.0}:
        return Resultado.rechazo("curva_roc", titulo,
                                 f"La etiqueta «{etiqueta}» tiene que ser 0/1; tiene "
                                 + ", ".join(f"{v:g}" for v in clases[:6]) + ".", entrada)
    if len(clases) < 2:
        return Resultado.rechazo("curva_roc", titulo,
                                 "La etiqueta tiene una sola clase: una curva ROC compara "
                                 "enfermos contra sanos.", entrada)
    fpr, tpr, umbrales = roc_curve(y, s)
    area = float(auc(fpr, tpr))
    dl = auc_delong(y, s)
    corte, j, sens, fpr_opt = optimal_threshold(fpr, tpr, umbrales)
    pred = s >= corte
    vp, fp = int(np.sum(pred & (y == 1))), int(np.sum(pred & (y == 0)))
    fn, vn = int(np.sum(~pred & (y == 1))), int(np.sum(~pred & (y == 0)))
    d = diagnostic_test(vp, fp, fn, vn)
    valores = [Valor("Enfermos (1)", int(np.sum(y == 1))), Valor("Sanos (0)", int(np.sum(y == 0))),
               Valor("AUC", area, ic=dl["ci"] if "ci" in dl else None,
                     nota=f"EE de DeLong {_f(dl['se'])}" if "se" in dl else "")]
    advertencias = []
    if "se" in dl:
        z = (area - 0.5) / dl["se"] if dl["se"] > 0 else np.inf
        p = float(2 * stats.norm.sf(abs(z)))
        valores.append(Valor("p (AUC = 0,5)", fmt_p(p)))
    else:
        p = np.nan
        advertencias.append(dl["error"])
    valores += [Valor("Umbral óptimo (Youden)", float(corte), nota=f"J = {_f(j, 3)}; positivo si ≥ umbral"),
                Valor("Sensibilidad en el umbral", d["sens"], ic=d.get("ci_sens"), decimales=3),
                Valor("Especificidad en el umbral", d["spec"], ic=d.get("ci_spec"), decimales=3),
                Valor("Tabla en el umbral", f"VP {vp}, FP {fp}, FN {fn}, VN {vn}")]
    invertida = area < 0.5
    supuestos = [
        Supuesto("¿La prueba discrimina mejor que el azar?",
                 f"AUC {_f(area, 3)}" + (f", IC 95 % {_f(dl['ci'][0], 3)} a {_f(dl['ci'][1], 3)}, "
                                         f"{p_token(p)}" if "ci" in dl else ""),
                 ("Sí, pero al revés" if invertida and p < 0.05 else "Sí" if p < 0.05
                  else "No se detectó"),
                 ("Los valores ALTOS corresponden a los sanos: leída al revés el AUC sería "
                  f"{_f(1 - area, 3)}. Revisá si 1 es de verdad el enfermo, o si la prueba baja con "
                  "la enfermedad." if invertida else
                  f"Discriminación {escala_auc(area)} (Hosmer y Lemeshow 2000). Mirá el IC: con "
                  "pocos casos puede ir de pobre a excelente." if p < 0.05 else
                  "El intervalo incluye 0,5: con estos datos la prueba no se distingue de tirar "
                  "una moneda."),
                 ok=bool(p < 0.05 and not invertida)),
        Supuesto("¿Qué criterio eligió el umbral?", "índice de Youden máximo",
                 "Youden", "Maximiza sensibilidad + especificidad, pesando igual un falso positivo "
                           "que un falso negativo. Si un error cuesta más que el otro (tamizaje "
                           "vs confirmación), el umbral clínico es otro.", ok=True),
    ]
    return _armar(
        "curva_roc", titulo, entrada, valores,
        Metodo("Curva ROC con IC de DeLong",
               "Cuánto separa la prueba a enfermos de sanos en todos los umbrales a la vez: el "
               "AUC es la probabilidad de que un enfermo al azar dé más alto que un sano."),
        supuestos,
        (f"AUC = {_f(area, 3)}: discriminación {escala_auc(area)}. En el umbral {_f(corte)} la "
         f"sensibilidad es {d['sens']:.3f} y la especificidad {d['spec']:.3f}." if not invertida
         else f"La curva sale invertida (AUC = {_f(area, 3)})."),
        "El umbral óptimo y su sensibilidad salen de los mismos datos: en pacientes nuevos rinden "
        "algo menos. Y la sensibilidad y la especificidad no son los valores predictivos: esos "
        "dependen de la prevalencia.",
        advertencias,
        [Figura("Curva ROC", lambda: _figura_roc(fpr, tpr, area, 1 - fpr_opt, sens)),
         Figura("Sensibilidad y especificidad según el umbral",
                lambda: _figura_umbral(fpr, tpr, umbrales, corte))],
        crudo={"auc": area, "delong": dl, "umbral": float(corte), "diagnostico": d})


def comparar_auc(opciones) -> Resultado:
    """Calculadora: dos AUC de curvas independientes, con su EE y su n."""
    titulo = "Comparar dos AUC (curvas independientes)"
    try:
        a1, e1, n1, a2, e2, n2 = (float(opciones[k]) for k in
                                  ("auc1", "ee1", "n1", "auc2", "ee2", "n2"))
    except KeyError as e:
        return Resultado.rechazo("comparar_auc", titulo, f"Falta el dato {e.args[0]}.")
    except (TypeError, ValueError):
        return Resultado.rechazo("comparar_auc", titulo, "Los seis datos tienen que ser números.")
    if not (0 <= a1 <= 1 and 0 <= a2 <= 1):
        return Resultado.rechazo("comparar_auc", titulo, "Un AUC va de 0 a 1.")
    r = compare_two_auc(a1, e1, int(n1), a2, e2, int(n2))
    falla = Resultado.rechazo_del_core("comparar_auc", titulo, r)
    if falla is not None:
        return falla
    valores = [Valor("AUC 1", a1, nota=f"EE {_f(e1)}, n = {int(n1)}"),
               Valor("AUC 2", a2, nota=f"EE {_f(e2)}, n = {int(n2)}"),
               Valor("Diferencia", r["diff"], ic=r["ci95"]), Valor("z", r["z"]),
               Valor("p", fmt_p(r["p"]))]
    supuestos = [
        Supuesto("¿Las AUC difieren?", f"z = {_f(r['z'], 3)}, {p_token(r['p'])}",
                 "Se detectó diferencia" if r["p"] < 0.05 else "No se detectó diferencia",
                 "Compara las dos áreas con sus errores estándar."),
        Supuesto("¿Las dos curvas son de pacientes distintos?", "lo supone la fórmula", "Se supone",
                 "Si las dos pruebas se midieron en los mismos pacientes (lo habitual al comparar "
                 "un método nuevo con el viejo), las AUC están correlacionadas y este p es "
                 "conservador: corresponde la prueba pareada de DeLong.", ok=False),
    ]
    return _armar(
        "comparar_auc", titulo, None, valores,
        Metodo("Prueba z de dos AUC independientes",
               "Compara dos AUC publicadas o calculadas en muestras distintas."),
        supuestos,
        f"Diferencia {_f(r['diff'], 3)}: " + ("se detectó." if r["p"] < 0.05 else "no se detectó."),
        "Dos AUC parecidas pueden esconder curvas que se cruzan: una mejor en sensibilidad alta y "
        "otra en especificidad alta.", crudo={"comparacion": r})


def _figura_roc(fpr, tpr, area, spec, sens):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(fpr, tpr, color='#4f6ef7', lw=2, label=f"ROC (AUC = {area:.3f})")
    ax.plot([0, 1], [0, 1], color='#d1d5e0', lw=1, ls='--', label="Azar")
    ax.scatter([1 - spec], [sens], color='#ef4444', s=80, zorder=5, label="Umbral de Youden")
    ax.set_xlabel("1 − especificidad")
    ax.set_ylabel("Sensibilidad")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_title("Curva ROC", fontweight='bold')
    ax.legend(loc="lower right", framealpha=0.9)
    fig.tight_layout()
    return fig


def _figura_umbral(fpr, tpr, umbrales, corte):
    import matplotlib.pyplot as plt

    finitos = np.isfinite(umbrales)
    u, sens, espec = np.asarray(umbrales)[finitos], np.asarray(tpr)[finitos], 1 - np.asarray(fpr)[finitos]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(u, sens, color='#4f6ef7', lw=2, label="Sensibilidad")
    ax.plot(u, espec, color='#22c55e', lw=2, label="Especificidad")
    ax.plot(u, sens + espec - 1, color='#d97706', lw=1.8, ls='--', label="J de Youden")
    ax.axvline(corte, color='#ef4444', ls=':', lw=1.4, label=f"Umbral {corte:.3g}")
    ax.set_xlabel("Umbral (positivo si ≥)")
    ax.set_ylim(0, 1.05)
    ax.set_title("Sensibilidad y especificidad según el umbral", fontweight='bold')
    ax.legend(framealpha=0.9)
    fig.tight_layout()
    return fig
