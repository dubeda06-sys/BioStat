"""Concordancia y confiabilidad: kappa, kappa ponderado y alfa de Cronbach.

(El ICC y el CV de duplicados, que también están en este menú, viven en
`comparacion.py` con el resto de la familia de validación.)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.core.agreement import cohens_kappa, cronbach_alpha, weighted_kappa
from src.resultado.citas import ficha
from src.resultado.datos import columnas_faltantes, filas_completas
from src.resultado.lenguaje import fmt_p
from src.resultado.modelo import Metodo, Resultado, Supuesto, Valor


def _f(x, dec=4) -> str:
    return Valor("", x, decimales=dec).texto()


def _armar(analisis, titulo, entrada, valores, metodo, supuestos, lectura, matiz,
           advertencias=(), crudo=None) -> Resultado:
    f = ficha(analisis)
    return Resultado(analisis=analisis, titulo=titulo, entrada=entrada, valores=valores,
                     metodo=metodo, supuestos=list(supuestos), formula=f.formula,
                     citas=list(f.citas), lectura=lectura, matiz=matiz,
                     advertencias=list(advertencias), crudo=crudo or {})


def _orden(valores):
    """Las categorías en orden: numérico si todas son números, alfabético si no."""
    unicas = list(dict.fromkeys(valores))
    try:
        return sorted(unicas, key=float)
    except (TypeError, ValueError):
        return sorted(unicas, key=str)


def _tabla(analisis, titulo, df, c1, c2, max_cat=20):
    falta = columnas_faltantes(df, c1, c2)
    if falta:
        return None, None, None, Resultado.rechazo(analisis, titulo, falta)
    if c1 == c2:
        return None, None, None, Resultado.rechazo(analisis, titulo,
                                                   "Elegí las dos clasificaciones en columnas "
                                                   "distintas.")
    pares, entrada = filas_completas(df, c1, c2)
    cats = _orden(list(pares[c1]) + list(pares[c2]))
    if len(cats) > max_cat:
        return None, None, None, Resultado.rechazo(
            analisis, titulo, f"Hay {len(cats)} categorías distintas: kappa es para "
                              "clasificaciones categóricas.", entrada)
    tabla = pd.crosstab(pares[c1], pares[c2]).reindex(index=cats, columns=cats, fill_value=0)
    return tabla, cats, entrada, None


def _celdas(tabla, c1, c2) -> list[Valor]:
    return [Valor(f"{c1} = {f} · {c2} = {c}", int(tabla.loc[f, c]))
            for f in tabla.index for c in tabla.columns if tabla.loc[f, c]]


_MATIZ_KAPPA = ("Kappa depende de la prevalencia: con una categoría muy frecuente puede salir "
                "bajo aunque el acuerdo observado sea alto (Feinstein y Cicchetti 1990). Mirá "
                "también el acuerdo observado.")


def _escala_altman(k) -> str:
    return ("pobre" if k < 0.2 else "débil" if k < 0.4 else "moderada" if k < 0.6 else
            "buena" if k < 0.8 else "muy buena")


def kappa(df, c1, c2, opciones=None) -> Resultado:
    """Dos evaluadores o métodos que clasifican a los mismos sujetos."""
    titulo = f"Kappa de Cohen — {c1} y {c2}"
    tabla, cats, entrada, rechazo = _tabla("kappa", titulo, df, c1, c2)
    if rechazo is not None:
        return rechazo
    r = cohens_kappa(tabla.values)
    falla = Resultado.rechazo_del_core("kappa", titulo, r, entrada)
    if falla is not None:
        return falla
    valores = [*_celdas(tabla, c1, c2), Valor("n", r["n"]),
               Valor("Acuerdo observado", r["po"], decimales=3),
               Valor("Acuerdo esperado por azar", r["pe"], decimales=3),
               Valor("Kappa", r["kappa"], ic=tuple(r["ci"]),
                     nota=f"concordancia {r['strength'].lower()} (Altman 1991)"),
               Valor("p (κ = 0)", fmt_p(r["p"]))]
    lo = r["ci"][0]
    supuestos = [Supuesto(
        "¿El acuerdo supera al del azar?", f"κ = {_f(r['kappa'], 3)}, IC 95 % {_f(r['ci'][0], 3)} "
        f"a {_f(r['ci'][1], 3)}", "Sí" if lo > 0 else "No se detectó",
        (f"El intervalo excluye el 0. Por su límite inferior, la concordancia es al menos "
         f"{_escala_altman(lo)}." if lo > 0 else
         "El intervalo incluye el 0: con estos datos el acuerdo no se distingue del azar."))]
    return _armar(
        "kappa", titulo, entrada, valores,
        Metodo("Kappa de Cohen", "Cuánto concuerdan dos clasificaciones más allá de lo que "
                                 "concordarían por azar."),
        supuestos,
        f"κ = {_f(r['kappa'], 3)}: concordancia {r['strength'].lower()}.",
        _MATIZ_KAPPA + " Para categorías ordenadas (leve, moderado, grave), el kappa ponderado.",
        crudo={"kappa": r, "categorias": cats})


def kappa_ponderado(df, c1, c2, opciones=None) -> Resultado:
    """`opciones["pesos"]`: "linear" | "quadratic"."""
    pesos = (opciones or {}).get("pesos", "linear")
    titulo = f"Kappa ponderado ({'lineal' if pesos == 'linear' else 'cuadrático'}) — {c1} y {c2}"
    tabla, cats, entrada, rechazo = _tabla("kappa_ponderado", titulo, df, c1, c2)
    if rechazo is not None:
        return rechazo
    r = weighted_kappa(tabla.values, pesos)
    if r is None:
        return Resultado.rechazo("kappa_ponderado", titulo, "Hacen falta al menos 2 categorías.",
                                 entrada)
    falla = Resultado.rechazo_del_core("kappa_ponderado", titulo, r, entrada)
    if falla is not None:
        return falla
    ic_ok = all(np.isfinite(r["ci"]))
    valores = [*_celdas(tabla, c1, c2), Valor("n", r["n"]),
               Valor("Categorías, en orden", ", ".join(str(c) for c in cats)),
               Valor("Kappa ponderado", r["kappa"], ic=tuple(r["ci"]) if ic_ok else None,
                     nota=f"concordancia {_escala_altman(r['kappa'])} (Altman 1991)"),
               Valor("p (κ = 0)", fmt_p(r["p"]))]
    supuestos = [
        Supuesto("¿En qué orden van las categorías?", ", ".join(str(c) for c in cats),
                 "Numérico" if all(_es_num(c) for c in cats) else "Alfabético",
                 ("El orden define qué desacuerdos son grandes: con números es el natural." if
                  all(_es_num(c) for c in cats) else
                  "Con texto el orden es alfabético, que puede no ser el clínico (grave antes que "
                  "leve). Si importa, codificá las categorías como 1, 2, 3."),
                 ok=all(_es_num(c) for c in cats)),
        Supuesto("¿Qué pesos?", "lineales" if pesos == "linear" else "cuadráticos",
                 "Lineales" if pesos == "linear" else "Cuadráticos",
                 ("Un desacuerdo de dos categorías pesa el doble que uno de una." if
                  pesos == "linear" else
                  "Un desacuerdo de dos categorías pesa cuatro veces uno de una; con estos pesos "
                  "el kappa se acerca al ICC."), ok=True),
    ]
    return _armar(
        "kappa_ponderado", titulo, entrada, valores,
        Metodo("Kappa ponderado de Cohen", "Kappa para categorías ordenadas: confundir leve con "
                                           "grave cuenta más que confundir leve con moderado."),
        supuestos, f"κ ponderado = {_f(r['kappa'], 3)}.", _MATIZ_KAPPA,
        crudo={"kappa": r, "categorias": cats})


def _es_num(c) -> bool:
    try:
        float(c)
        return True
    except (TypeError, ValueError):
        return False


def cronbach(df, columnas, opciones=None) -> Resultado:
    if isinstance(columnas, str):
        columnas = [columnas]
    columnas = list(dict.fromkeys(columnas or []))
    titulo = "Alfa de Cronbach"
    if len(columnas) < 2:
        return Resultado.rechazo("cronbach", titulo, "Hacen falta al menos 2 ítems.")
    falta = columnas_faltantes(df, *columnas)
    if falta:
        return Resultado.rechazo("cronbach", titulo, falta)
    filas, entrada = filas_completas(df, *columnas)
    try:
        datos = filas[columnas].to_numpy(dtype=float)
    except (TypeError, ValueError):
        return Resultado.rechazo("cronbach", titulo, "Algún ítem tiene texto.", entrada)
    r = cronbach_alpha(datos)
    if r is None:
        return Resultado.rechazo("cronbach", titulo, "Hacen falta al menos 2 sujetos completos.",
                                 entrada)
    falla = Resultado.rechazo_del_core("cronbach", titulo, r, entrada)
    if falla is not None:
        return falla
    valores = [Valor("α de Cronbach", r["alpha"], ic=r["ci"], nota="IC de Feldt"),
               Valor("Ítems", r["n_items"]), Valor("Sujetos completos", r["n_subjects"])]
    invertidos = []
    total = datos.sum(axis=1)
    for i, c in enumerate(columnas):
        resto = total - datos[:, i]
        r_it = float(np.corrcoef(datos[:, i], resto)[0, 1]) if np.ptp(datos[:, i]) > 0 else np.nan
        sin = cronbach_alpha(np.delete(datos, i, axis=1)) if len(columnas) > 2 else None
        a_sin = sin["alpha"] if isinstance(sin, dict) and "alpha" in sin else None
        valores.append(Valor(f"Ítem {c}", r_it, nota=("correlación con el resto"
                                                      + (f"; α sin él = {_f(a_sin, 3)}"
                                                         if a_sin is not None else ""))))
        if np.isfinite(r_it) and r_it < 0:
            invertidos.append(c)
    supuestos = [Supuesto(
        "¿Todos los ítems van en el mismo sentido?",
        "correlación de cada ítem con la suma de los demás",
        "Sí" if not invertidos else "No: " + ", ".join(invertidos),
        ("Ningún ítem va a contramano del resto." if not invertidos else
         "Un ítem con correlación negativa suele estar redactado al revés: hay que invertir su "
         "puntaje antes de sumar, o el alfa sale subestimado."),
        ok=not invertidos)]
    a = r["alpha"]
    return _armar(
        "cronbach", titulo, entrada, valores,
        Metodo("Alfa de Cronbach, IC de Feldt",
               "Cuánto miden lo mismo los ítems de una escala (consistencia interna)."),
        supuestos,
        f"α = {_f(a, 3)}: " + ("consistencia alta." if a >= 0.8 else "consistencia aceptable."
                               if a >= 0.7 else "consistencia baja."),
        "Un alfa alto no prueba que la escala mida un solo constructo, y sube con la cantidad de "
        "ítems aunque no mejore la escala. Por encima de 0,95 suele haber ítems redundantes.",
        crudo={"cronbach": r})
