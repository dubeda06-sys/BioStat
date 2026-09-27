"""Bootstrap: IC de la media, la mediana, una diferencia, una correlación y una recta.

Los números salen de `src/core/bootstrap.py`, verificado contra
`scipy.stats.bootstrap`. Cambian a propósito, cada uno con su test:

- El IC es BCa por defecto (corrige sesgo y asimetría); el percentil queda como
  opción. Antes era siempre el percentil.
- La mediana trae además su IC exacto por rangos, sin remuestreo, como control:
  con muchos empates la distribución bootstrap de la mediana va a saltos.
- La correlación puede ser de Spearman; la regresión informa también el IC del
  intercepto (antes solo lo calculaba).
"""
from __future__ import annotations

import numpy as np

from src.core.bootstrap import (
    bootstrap_correlation, bootstrap_difference, bootstrap_mean, bootstrap_median,
    bootstrap_regression,
)
from src.resultado.citas import ficha
from src.resultado.datos import columnas_faltantes, filas_completas, una
from src.resultado.lenguaje import num
from src.resultado.modelo import Entrada, Figura, Metodo, Resultado, Supuesto, Valor

MIN_BOOT = 5
N_CONFIABLE = 20


def _armar(analisis, titulo, entrada, valores, metodo, supuestos, lectura, matiz,
           advertencias=(), figuras=(), crudo=None) -> Resultado:
    f = ficha(analisis)
    return Resultado(analisis=analisis, titulo=titulo, entrada=entrada, valores=valores,
                     metodo=metodo, supuestos=list(supuestos), formula=f.formula,
                     citas=list(f.citas), lectura=lectura, matiz=matiz,
                     advertencias=list(advertencias), figuras=list(figuras), crudo=crudo or {})


def _metodo_ic(opciones) -> str:
    return "percentil" if (opciones or {}).get("metodo_ic") == "percentil" else "bca"


def _metodo(r, que) -> Metodo:
    usado = r["metodo_ic"]
    return Metodo(f"Bootstrap, {r['n_bootstrap']} remuestreos, IC {usado}",
                  f"Remuestrea los datos con reposición y calcula {que} en cada remuestreo: el IC "
                  "sale de esa distribución, sin suponer que sea normal"
                  + (", corregida por sesgo y asimetría (BCa)." if usado == "BCa" else "."))


def _supuestos_comunes(n, que="datos") -> list[Supuesto]:
    ok = n >= N_CONFIABLE
    return [
        Supuesto(f"¿Alcanzan los {que} para remuestrear?", f"n = {n}", "Sí" if ok else "No",
                 ("Con 20 o más, la muestra representa razonablemente la forma de la población."
                  if ok else
                  "Con menos de 20 el remuestreo repite los mismos pocos valores: el IC sale "
                  "más angosto de lo que debería (Efron y Tibshirani 1993)."), ok=ok),
        Supuesto("¿Las observaciones son independientes?", "lo supone el remuestreo", "Se supone",
                 "Se remuestrean de a una: con mediciones repetidas del mismo sujeto o series en "
                 "el tiempo, el IC sale angosto de más."),
    ]


def _usado(r) -> str:
    return f"IC {int(round(100 * r['ci_level']))} % {r['metodo_ic']}"


def _advertencia_bca(r, pedido) -> list[str]:
    if pedido == "bca" and r["metodo_ic"] != "BCa":
        return ["El BCa no se pudo calcular (la distribución bootstrap queda toda de un lado del "
                "estimado): se informa el IC percentil."]
    return []


MATIZ = ("El bootstrap no agrega información: si la muestra no representa a la población, el IC "
         "tampoco. La semilla es fija, así que el resultado se repite; con otra semilla cambia "
         "en el último decimal.")


# ============================================================
#  Una columna: media y mediana
# ============================================================

def _una(analisis, titulo, df, col):
    c = una(df, col)
    if c.motivo:
        return None, None, Resultado.rechazo(analisis, titulo, c.motivo)
    if len(c.valores) < MIN_BOOT:
        return None, None, Resultado.rechazo(analisis, titulo, f"Hacen falta al menos {MIN_BOOT} "
                                             f"datos; hay {len(c.valores)}.", c.entrada)
    return c.valores, c.entrada, None


def boot_media(df, col, opciones=None) -> Resultado:
    titulo = f"Bootstrap de la media — {col}"
    x, entrada, rechazo = _una("boot_media", titulo, df, col)
    if rechazo is not None:
        return rechazo
    pedido = _metodo_ic(opciones)
    r = bootstrap_mean(x, metodo=pedido)
    valores = [Valor("n", len(x)),
               Valor("Media", r["original_mean"], ic=(r["ci_lower"], r["ci_upper"]),
                     nota=_usado(r)),
               Valor("Error estándar bootstrap", r["bootstrap_se"]),
               Valor("Sesgo bootstrap", r["bias"])]
    return _armar(
        "boot_media", titulo, entrada, valores, _metodo(r, "la media"),
        _supuestos_comunes(len(x)),
        f"Media {num(r['original_mean'])}, {_usado(r)} de {num(r['ci_lower'])} a "
        f"{num(r['ci_upper'])}.",
        "Con datos simétricos y n moderado, el IC t de siempre da casi lo mismo. " + MATIZ,
        _advertencia_bca(r, pedido),
        [Figura("Distribución bootstrap de la media",
                lambda: _figura_dist(r["bootstrap_distribution"], r["original_mean"], r, "Media"))],
        {"bootstrap": r})


def boot_mediana(df, col, opciones=None) -> Resultado:
    titulo = f"Bootstrap de la mediana — {col}"
    x, entrada, rechazo = _una("boot_mediana", titulo, df, col)
    if rechazo is not None:
        return rechazo
    pedido = _metodo_ic(opciones)
    r = bootstrap_median(x, metodo=pedido)
    ex = r["exacto"]
    valores = [Valor("n", len(x)),
               Valor("Mediana", r["original_median"], ic=(r["ci_lower"], r["ci_upper"]),
                     nota=_usado(r)),
               Valor("IC exacto por rangos", f"{num(ex['inferior'])} a {num(ex['superior'])}"
                     if ex else "no hay con n tan chico",
                     nota=(f"rangos {ex['rangos'][0]} y {ex['rangos'][1]}, cobertura "
                           f"{100 * ex['cobertura']:.1f} %") if ex else "")]
    supuestos = _supuestos_comunes(len(x))
    distintos = r["distintos"]
    pocos = distintos < 0.5 * len(x)
    supuestos.append(Supuesto(
        "¿Hay muchos valores repetidos?", f"{distintos} valores distintos en {len(x)} datos",
        "Sí" if pocos else "No",
        ("Con muchos empates la mediana remuestreada toma pocos valores y el IC bootstrap va a "
         "saltos: preferí el IC exacto por rangos." if pocos else
         "La distribución bootstrap de la mediana es razonablemente continua."), ok=not pocos))
    return _armar(
        "boot_mediana", titulo, entrada, valores, _metodo(r, "la mediana"), supuestos,
        f"Mediana {num(r['original_median'])}, {_usado(r)} de {num(r['ci_lower'])} a "
        f"{num(r['ci_upper'])}"
        + (f"; por rangos, de {num(ex['inferior'])} a {num(ex['superior'])}." if ex else "."),
        "El IC exacto por rangos no remuestrea y cubre al menos el 95 %; si los dos IC difieren "
        "mucho, confiá en el exacto. " + MATIZ,
        _advertencia_bca(r, pedido),
        [Figura("Distribución bootstrap de la mediana",
                lambda: _figura_dist(r["bootstrap_distribution"], r["original_median"], r,
                                     "Mediana"))],
        {"bootstrap": r})


# ============================================================
#  Dos columnas: diferencia, correlación, recta
# ============================================================

def boot_diferencia(df, c1, c2, opciones=None) -> Resultado:
    """Dos grupos independientes, uno por columna."""
    titulo = f"Bootstrap de la diferencia de medias — {c1} − {c2}"
    if c1 == c2:
        return Resultado.rechazo("boot_diferencia", titulo, "Elegí dos columnas distintas.")
    a, b = una(df, c1), una(df, c2)
    for c in (a, b):
        if c.motivo:
            return Resultado.rechazo("boot_diferencia", titulo, c.motivo)
    x, y = a.valores, b.valores
    entrada = Entrada(columnas=(c1, c2), n=len(x) + len(y))
    if min(len(x), len(y)) < MIN_BOOT:
        return Resultado.rechazo("boot_diferencia", titulo,
                                 f"Hacen falta al menos {MIN_BOOT} datos por grupo; hay "
                                 f"{len(x)} y {len(y)}.", entrada)
    pedido = _metodo_ic(opciones)
    r = bootstrap_difference(x, y, metodo=pedido)
    incluye = r["ci_lower"] <= 0 <= r["ci_upper"]
    valores = [Valor(f"n — {c1}", len(x)), Valor(f"n — {c2}", len(y)),
               Valor(f"Media — {c1}", float(np.mean(x))), Valor(f"Media — {c2}", float(np.mean(y))),
               Valor("Diferencia", r["original_diff"], ic=(r["ci_lower"], r["ci_upper"]),
                     nota=_usado(r)),
               Valor("Error estándar bootstrap", r["bootstrap_se"])]
    supuestos = _supuestos_comunes(min(len(x), len(y)), "datos de cada grupo") + [Supuesto(
        "¿El IC incluye el 0?", f"{num(r['ci_lower'])} a {num(r['ci_upper'])}",
        "Sí: no se detectó diferencia" if incluye else "No: se detectó diferencia",
        ("No detectarla no prueba que no exista: mirá el ancho del IC." if incluye else
         "Las medias difieren más de lo que explica el remuestreo."))]
    return _armar(
        "boot_diferencia", titulo, entrada, valores, _metodo(r, "la diferencia de medias"),
        supuestos,
        f"Diferencia {num(r['original_diff'])}, {_usado(r)} de {num(r['ci_lower'])} a "
        f"{num(r['ci_upper'])}: " + ("no se detectó diferencia." if incluye else
                                     "se detectó diferencia."),
        "Cada grupo se remuestrea por separado: supone grupos independientes (para pares, la "
        "media de las diferencias). " + MATIZ,
        _advertencia_bca(r, pedido),
        [Figura("Distribución bootstrap de la diferencia",
                lambda: _figura_dist(r["bootstrap_distribution"], r["original_diff"], r,
                                     "Diferencia", cero=True))],
        {"bootstrap": r})


def _pares(analisis, titulo, df, c1, c2):
    falta = columnas_faltantes(df, c1, c2)
    if falta:
        return None, None, None, Resultado.rechazo(analisis, titulo, falta)
    if c1 == c2:
        return None, None, None, Resultado.rechazo(analisis, titulo, "Elegí dos columnas distintas.")
    filas, entrada = filas_completas(df, c1, c2)
    try:
        x, y = filas[c1].to_numpy(dtype=float), filas[c2].to_numpy(dtype=float)
    except (TypeError, ValueError):
        return None, None, None, Resultado.rechazo(analisis, titulo, "Las dos columnas tienen que "
                                                   "ser números.", entrada)
    if len(x) < MIN_BOOT:
        return None, None, None, Resultado.rechazo(analisis, titulo, f"Hacen falta al menos "
                                                   f"{MIN_BOOT} pares; hay {len(x)}.", entrada)
    return x, y, entrada, None


def boot_correlacion(df, c1, c2, opciones=None) -> Resultado:
    """`opciones["coeficiente"]`: "pearson" | "spearman"."""
    opciones = opciones or {}
    coef = "spearman" if opciones.get("coeficiente") == "spearman" else "pearson"
    nombre = "ρ de Spearman" if coef == "spearman" else "r de Pearson"
    titulo = f"Bootstrap de la correlación — {c1} y {c2}"
    x, y, entrada, rechazo = _pares("boot_correlacion", titulo, df, c1, c2)
    if rechazo is not None:
        return rechazo
    pedido = _metodo_ic(opciones)
    r = bootstrap_correlation(x, y, method=coef, metodo=pedido)
    falla = Resultado.rechazo_del_core("boot_correlacion", titulo, r, entrada)
    if falla is not None:
        return falla
    incluye = r["ci_lower"] <= 0 <= r["ci_upper"]
    valores = [Valor("n (pares)", len(x)),
               Valor(nombre, r["original_r"], ic=(r["ci_lower"], r["ci_upper"]), nota=_usado(r)),
               Valor("Error estándar bootstrap", r["bootstrap_se"])]
    supuestos = _supuestos_comunes(len(x), "pares") + [Supuesto(
        "¿El IC incluye el 0?", f"{num(r['ci_lower'])} a {num(r['ci_upper'])}",
        "Sí: no se detectó correlación" if incluye else "No: se detectó correlación",
        ("No detectarla no prueba que no exista." if incluye else
         "La asociación se sostiene en los remuestreos."))]
    return _armar(
        "boot_correlacion", titulo, entrada, valores,
        _metodo(r, f"la {nombre}"), supuestos,
        f"{nombre} = {num(r['original_r'])}, {_usado(r)} de {num(r['ci_lower'])} a "
        f"{num(r['ci_upper'])}.",
        "Se remuestrean los pares juntos. Correlación no es acuerdo ni causa. " + MATIZ,
        list(r["avisos"]) + _advertencia_bca(r, pedido),
        [Figura("Distribución bootstrap de la correlación",
                lambda: _figura_dist(r["bootstrap_distribution"], r["original_r"], r, nombre,
                                     cero=True))],
        {"bootstrap": r})


def boot_regresion(df, c1, c2, opciones=None) -> Resultado:
    """Variable 1 = X, Variable 2 = Y."""
    titulo = f"Bootstrap de la recta — {c2} según {c1}"
    x, y, entrada, rechazo = _pares("boot_regresion", titulo, df, c1, c2)
    if rechazo is not None:
        return rechazo
    pedido = _metodo_ic(opciones)
    r = bootstrap_regression(x, y, metodo=pedido)
    falla = Resultado.rechazo_del_core("boot_regresion", titulo, r, entrada)
    if falla is not None:
        return falla
    usado = f"IC 95 % {r['metodo_ic']}"
    valores = [Valor("n (pares)", len(x)),
               Valor("Pendiente", r["original_slope"], ic=r["ci_slope"], nota=usado),
               Valor("Intercepto", r["original_intercept"], ic=r["ci_intercept"], nota=usado),
               Valor("EE bootstrap de la pendiente", r["se_slope"]),
               Valor("EE bootstrap del intercepto", r["se_intercept"])]
    incluye = r["ci_slope"][0] <= 0 <= r["ci_slope"][1]
    supuestos = _supuestos_comunes(len(x), "pares") + [Supuesto(
        "¿El IC de la pendiente incluye el 0?",
        f"{num(r['ci_slope'][0])} a {num(r['ci_slope'][1])}",
        "Sí: no se detectó pendiente" if incluye else "No: se detectó pendiente",
        ("Con estos datos Y no cambia con X más de lo que explica el remuestreo." if incluye
         else "Y cambia con X."))]
    advertencias = []
    if r["n_invalidos"]:
        advertencias.append(f"{r['n_invalidos']} de {r['n_bootstrap']} remuestreos salieron con X "
                            "constante y no definen recta: se descartaron.")
    if pedido == "bca" and r["metodo_ic"] != "BCa":
        advertencias += _advertencia_bca({"metodo_ic": r["metodo_ic"]}, pedido)
    return _armar(
        "boot_regresion", titulo, entrada, valores, _metodo(r, "la recta"), supuestos,
        f"Pendiente {num(r['original_slope'])} ({usado} {num(r['ci_slope'][0])} a "
        f"{num(r['ci_slope'][1])}).",
        "Remuestrear pares no supone varianza constante ni residuos normales, pero sí que la "
        "relación es una recta. Para comparar métodos, la recta es Deming o Passing-Bablok, no "
        "esta. " + MATIZ,
        advertencias,
        [Figura("Distribución bootstrap de la pendiente",
                lambda: _figura_dist(r["distribucion_pendiente"], r["original_slope"],
                                     {"ci_lower": r["ci_slope"][0], "ci_upper": r["ci_slope"][1]},
                                     "Pendiente", cero=True))],
        {"bootstrap": r})


def _figura_dist(dist, estimado, r, nombre, cero=False):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4.5))
    from src.utils.histograma import barras

    ax.hist(dist, bins=barras(dist, 60), color='#c7d2fe', edgecolor='#4f6ef7')
    ax.axvline(estimado, color='#111827', lw=2, label=f"{nombre} = {estimado:.4g}")
    ax.axvline(r["ci_lower"], color='#ef4444', ls='--', lw=1.5, label="IC")
    ax.axvline(r["ci_upper"], color='#ef4444', ls='--', lw=1.5)
    if cero:
        ax.axvline(0, color='#9ca3af', ls=':', lw=1.5)
    ax.set_xlabel(nombre)
    ax.set_ylabel("Remuestreos")
    ax.set_title(f"Distribución bootstrap — {nombre}", fontweight='bold')
    ax.legend(framealpha=0.9)
    fig.tight_layout()
    return fig
