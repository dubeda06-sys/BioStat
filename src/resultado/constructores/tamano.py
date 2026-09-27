"""Tamaño de muestra y poder: cinco calculadoras, sin hoja.

Los números salen de `src/core/sample_size.py` (t no central exacta para las
medias, verificada contra statsmodels). Cada informe trae la curva de poder
según n, para ver cuánto se gana o se pierde alrededor del n pedido.

Cambia a propósito: el tamaño muestral para una correlación pide la r esperada
en el diálogo. Antes calculaba el n necesario para «detectar» la r observada en
la misma hoja, que es poder post hoc (Hoenig y Heisey 2001): no dice nada que
el p de esa correlación no diga.
"""
from __future__ import annotations

import numpy as np

from src.core.sample_size import (
    power_analysis, power_correlation, power_proportions, power_two_means,
    sample_size_correlation, sample_size_mean, sample_size_proportions, sample_size_two_means,
)
from src.resultado.citas import ficha
from src.resultado.lenguaje import num
from src.resultado.modelo import Figura, Metodo, Resultado, Supuesto, Valor

EJEMPLOS = {
    "tam_una_media": {"delta": 5.0, "sd": 10.0, "alpha": 0.05, "poder": 0.80},
    "tam_dos_medias": {"delta": 5.0, "sd": 10.0, "ratio": 1.0, "alpha": 0.05, "poder": 0.80},
    "tam_dos_proporciones": {"p1": 0.30, "p2": 0.50, "alpha": 0.05, "poder": 0.80},
    "tam_correlacion": {"r": 0.30, "alpha": 0.05, "poder": 0.80},
    "poder_t": {"n": 100, "delta": 5.0, "sd": 10.0, "alpha": 0.05, "diseno": "una"},
}

PERDIDAS = ("El n es de sujetos analizables: si esperás perder un 10 % en el camino, reclutá "
            "n / 0,9.")


def _armar(analisis, titulo, valores, metodo, supuestos, lectura, matiz, figuras,
           crudo) -> Resultado:
    f = ficha(analisis)
    return Resultado(analisis=analisis, titulo=titulo, entrada=None, valores=valores,
                     metodo=metodo, supuestos=list(supuestos), formula=f.formula,
                     citas=list(f.citas), lectura=lectura, matiz=matiz,
                     figuras=list(figuras), crudo=crudo)


def _leer(analisis, titulo, opciones, claves):
    """({clave: float}, None) o (None, rechazo)."""
    try:
        return {k: float(opciones[k]) for k in claves}, None
    except KeyError as e:
        return None, Resultado.rechazo(analisis, titulo, f"Falta el dato {e.args[0]}.")
    except (TypeError, ValueError):
        return None, Resultado.rechazo(analisis, titulo, "Los datos tienen que ser números.")


def _v_pct(nombre, p, nota="") -> Valor:
    return Valor(nombre, 100 * p, decimales=1, unidad="%", nota=nota)


def _supuesto_de(sd) -> Supuesto:
    return Supuesto(
        "¿De dónde sale la DE esperada?", f"DE = {num(sd)}, declarada", "Se supone",
        "El n crece con el cuadrado de la DE: si la real es un 20 % mayor, hacen falta un 44 % "
        "más de sujetos. Sacala de un piloto o de la literatura, y si dudás, usá la mayor.")


def _supuesto_t(prueba) -> Supuesto:
    return Supuesto(
        "¿La prueba que se va a correr es esta?", f"{prueba}, a dos colas", "Se supone",
        "Si los datos no van a ser normales y se usa una no paramétrica (Mann-Whitney, "
        "Wilcoxon), sumá un 15 %: su eficiencia frente a la t nunca baja de 0,864 (Hodges y "
        "Lehmann 1956).")


def _curva(poder_de, n_marcado, poder_marcado, objetivo=None, etiqueta_n="n"):
    """Figura: poder según n, con el n calculado marcado."""
    import matplotlib.pyplot as plt

    tope = max(10, int(2.5 * n_marcado))
    ns = np.unique(np.linspace(2, tope, 120).astype(int))
    ns = ns[ns >= 2]
    poderes = np.array([poder_de(int(k)) for k in ns])
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(ns, 100 * poderes, color='#4f6ef7', lw=2)
    ax.scatter([n_marcado], [100 * poder_marcado], color='#ef4444', s=60, zorder=5)
    if objetivo is not None:
        ax.axhline(100 * objetivo, color='#9ca3af', ls='--', lw=1)
    ax.set_xlabel(etiqueta_n)
    ax.set_ylabel("Poder (%)")
    ax.set_ylim(0, 102)
    ax.set_title("Poder según el tamaño de muestra", fontweight='bold')
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    return fig


# ============================================================
#  Medias
# ============================================================

def tam_una_media(opciones) -> Resultado:
    """n para comparar una media con un valor, o para datos pareados."""
    titulo = "Tamaño muestral — 1 media o datos pareados"
    d, rechazo = _leer("tam_una_media", titulo, opciones, ("delta", "sd", "alpha", "poder"))
    if rechazo is not None:
        return rechazo
    r = sample_size_mean(d["delta"], d["sd"], d["alpha"], d["poder"])
    if r is None:
        return Resultado.rechazo("tam_una_media", titulo,
                                 "La diferencia a detectar y la DE no pueden ser 0.")
    n = r["n_per_group"]
    efecto = abs(d["delta"] / d["sd"])
    valores = [Valor("Diferencia a detectar (Δ)", d["delta"]), Valor("DE esperada", d["sd"]),
               Valor("Alfa (dos colas)", d["alpha"]), _v_pct("Poder buscado", d["poder"]),
               Valor("Tamaño del efecto (Δ/DE)", efecto, decimales=3),
               Valor("n necesario", n), _v_pct("Poder real con ese n", r["power_real"])]
    return _armar(
        "tam_una_media", titulo, valores,
        Metodo("Poder exacto de la t (t no central)",
               "El n más chico con el que la t de una muestra detecta la diferencia pedida "
               "con el poder pedido."),
        [_supuesto_de(d["sd"]), _supuesto_t("t de una muestra o pareada")],
        f"Hacen falta {n} sujetos: con ese n la t detecta una diferencia de {num(d['delta'])} "
        f"el {100 * r['power_real']:.0f} % de las veces.",
        "Para datos pareados, la DE es la de las diferencias, no la de cada medición. " + PERDIDAS,
        [Figura("Poder según n", lambda: _curva(
            lambda k: power_analysis(k, d["delta"], d["sd"], d["alpha"])["power"],
            n, r["power_real"], d["poder"]))],
        {"tamano": r})


def tam_dos_medias(opciones) -> Resultado:
    """n por grupo para comparar dos medias independientes."""
    titulo = "Tamaño muestral — 2 medias"
    d, rechazo = _leer("tam_dos_medias", titulo, opciones,
                       ("delta", "sd", "ratio", "alpha", "poder"))
    if rechazo is not None:
        return rechazo
    r = sample_size_two_means(d["delta"], d["sd"], d["alpha"], d["poder"], d["ratio"])
    if r is None:
        return Resultado.rechazo("tam_dos_medias", titulo,
                                 "La diferencia a detectar, la DE y la razón n2/n1 no pueden "
                                 "ser 0.")
    n1, n2 = r["n_group1"], r["n_group2"]
    valores = [Valor("Diferencia entre medias (Δ)", d["delta"]), Valor("DE común", d["sd"]),
               Valor("Razón n2/n1", d["ratio"], decimales=2), Valor("Alfa (dos colas)", d["alpha"]),
               _v_pct("Poder buscado", d["poder"]),
               Valor("Tamaño del efecto (Δ/DE)", abs(d["delta"] / d["sd"]), decimales=3),
               Valor("n grupo 1", n1), Valor("n grupo 2", n2), Valor("n total", n1 + n2),
               _v_pct("Poder real con ese n", r["power_real"])]
    supuestos = [_supuesto_de(d["sd"]), _supuesto_t("t de dos muestras")]
    if d["ratio"] != 1:
        supuestos.append(Supuesto(
            "¿Conviene que los grupos sean desiguales?", f"n2/n1 = {num(d['ratio'])}", "Se eligió",
            "Con el mismo n total, los grupos iguales dan el mayor poder. Desiguales solo se "
            "justifican si un grupo es más barato o más fácil de reclutar."))
    return _armar(
        "tam_dos_medias", titulo, valores,
        Metodo("Poder exacto de la t de dos muestras (t no central)",
               "El n más chico por grupo con el que la t detecta la diferencia pedida con el "
               "poder pedido."),
        supuestos,
        f"Hacen falta {n1} + {n2} = {n1 + n2} sujetos: con eso la t detecta una diferencia de "
        f"{num(d['delta'])} el {100 * r['power_real']:.0f} % de las veces.",
        "Supone la misma DE en los dos grupos. " + PERDIDAS,
        [Figura("Poder según n", lambda: _curva(
            lambda k: power_two_means(k, d["delta"], d["sd"], d["alpha"], d["ratio"])["power"],
            n1, r["power_real"], d["poder"],
            "n del grupo 1" + (f" (el 2 es {num(d['ratio'])} veces)" if d["ratio"] != 1 else "")))],
        {"tamano": r})


def poder_t(opciones) -> Resultado:
    """Poder de una t con un n dado; `diseno`: "una" (o pareada) | "dos"."""
    dos = opciones.get("diseno", "una") == "dos"
    titulo = "Poder de la t — " + ("dos grupos independientes" if dos else
                                   "una muestra o datos pareados")
    d, rechazo = _leer("poder_t", titulo, opciones, ("n", "delta", "sd", "alpha"))
    if rechazo is not None:
        return rechazo
    n = int(d["n"])
    r = (power_two_means(n, d["delta"], d["sd"], d["alpha"]) if dos else
         power_analysis(n, d["delta"], d["sd"], d["alpha"]))
    if r is None:
        return Resultado.rechazo("poder_t", titulo, "Hacen falta n ≥ 2 y una DE distinta de 0.")
    poder = r["power"]
    nombre_n = "n por grupo" if dos else "n"
    valores = [Valor(nombre_n, n), Valor("Diferencia (Δ)", d["delta"]), Valor("DE", d["sd"]),
               Valor("Alfa (dos colas)", d["alpha"]),
               Valor("Tamaño del efecto (Δ/DE)", r["effect_size"], decimales=3),
               _v_pct("Poder", poder)]
    lectura = (f"Con {nombre_n} = {n}, la t detecta una diferencia de {num(d['delta'])} el "
               f"{100 * poder:.0f} % de las veces.")
    if poder < 0.80 and d["delta"] != 0:
        req = (sample_size_two_means(d["delta"], d["sd"], d["alpha"], 0.80) if dos else
               sample_size_mean(d["delta"], d["sd"], d["alpha"], 0.80))
        if req is not None:
            n80 = req["n_group1"] if dos else req["n_per_group"]
            valores.append(Valor(f"{nombre_n} para 80 % de poder", n80))
            lectura += f" Para llegar al 80 % hacen falta {n80}."
    supuestos = [
        Supuesto("¿El poder se calcula antes del estudio?",
                 f"con la diferencia declarada, Δ = {num(d['delta'])}", "Se supone",
                 "El poder sirve para planear: con la diferencia que importa clínicamente. "
                 "Calcularlo después con la diferencia observada (poder post hoc) no agrega "
                 "nada al p (Hoenig y Heisey 2001)."),
        _supuesto_de(d["sd"]),
    ]
    return _armar(
        "poder_t", titulo, valores,
        Metodo("Poder exacto de la t (t no central)",
               "La probabilidad de que la t salga con p < α si la diferencia real es Δ."),
        supuestos, lectura,
        "Un poder bajo no hace falso un resultado positivo, pero hace que un «no se detectó» "
        "diga poco: con poco poder, una diferencia real pasa inadvertida seguido.",
        [Figura("Poder según n", lambda: _curva(
            (lambda k: power_two_means(k, d["delta"], d["sd"], d["alpha"])["power"]) if dos else
            (lambda k: power_analysis(k, d["delta"], d["sd"], d["alpha"])["power"]),
            n, poder, 0.80, nombre_n))],
        {"poder": r, "diseno": "dos" if dos else "una"})


# ============================================================
#  Proporciones y correlación
# ============================================================

def tam_dos_proporciones(opciones) -> Resultado:
    titulo = "Tamaño muestral — 2 proporciones"
    d, rechazo = _leer("tam_dos_proporciones", titulo, opciones, ("p1", "p2", "alpha", "poder"))
    if rechazo is not None:
        return rechazo
    r = sample_size_proportions(d["p1"], d["p2"], d["alpha"], d["poder"])
    if r is None:
        return Resultado.rechazo("tam_dos_proporciones", titulo,
                                 "Las dos proporciones no pueden ser iguales.")
    falla = Resultado.rechazo_del_core("tam_dos_proporciones", titulo, r)
    if falla is not None:
        return falla
    n = r["n_per_group"]
    menor = min(n * d["p1"], n * (1 - d["p1"]), n * d["p2"], n * (1 - d["p2"]))
    valores = [Valor("Proporción esperada, grupo 1", d["p1"], decimales=3),
               Valor("Proporción esperada, grupo 2", d["p2"], decimales=3),
               Valor("Diferencia a detectar", abs(d["p1"] - d["p2"]), decimales=3),
               Valor("Alfa (dos colas)", d["alpha"]), _v_pct("Poder buscado", d["poder"]),
               Valor("n por grupo", n), Valor("n total", 2 * n),
               _v_pct("Poder real con ese n", r["power_real"])]
    supuestos = [
        Supuesto("¿Alcanza la aproximación normal?",
                 f"el menor conteo esperado por celda es {menor:.1f}",
                 "Sí" if menor >= 5 else "No",
                 ("Con 5 o más esperados en cada celda la z de dos proporciones funciona." if
                  menor >= 5 else
                  "Con menos de 5 esperados en alguna celda la aproximación falla: el análisis "
                  "va a ser un Fisher exacto, que pide más sujetos que esto."), ok=menor >= 5),
        Supuesto("¿La prueba lleva corrección de continuidad?", "este cálculo, no", "Se supone",
                 "Si el análisis va a ser el χ² con corrección de Yates o un Fisher exacto, el "
                 "poder real es algo menor: sumá unos sujetos (Fleiss et al. 2003)."),
    ]
    return _armar(
        "tam_dos_proporciones", titulo, valores,
        Metodo("Fórmula de Fleiss para dos proporciones",
               "El n por grupo con el que la z de dos proporciones detecta la diferencia entre "
               "p1 y p2 con el poder pedido."),
        supuestos,
        f"Hacen falta {n} por grupo ({2 * n} en total) para detectar {num(d['p1'])} contra "
        f"{num(d['p2'])}.",
        "La diferencia que importa es la absoluta: pasar de 0,30 a 0,50 pide menos sujetos que "
        "de 0,05 a 0,10, aunque la segunda duplique el riesgo. " + PERDIDAS,
        [Figura("Poder según n", lambda: _curva(
            lambda k: power_proportions(k, d["p1"], d["p2"], d["alpha"]), n, r["power_real"],
            d["poder"], "n por grupo"))],
        {"tamano": r})


def tam_correlacion(opciones) -> Resultado:
    """n para detectar una correlación r esperada (z de Fisher)."""
    titulo = "Tamaño muestral — correlación"
    d, rechazo = _leer("tam_correlacion", titulo, opciones, ("r", "alpha", "poder"))
    if rechazo is not None:
        return rechazo
    r = sample_size_correlation(d["r"], d["alpha"], d["poder"])
    if r is None:
        return Resultado.rechazo("tam_correlacion", titulo, "La r esperada no puede ser 0.")
    falla = Resultado.rechazo_del_core("tam_correlacion", titulo, r)
    if falla is not None:
        return falla
    n = r["n"]
    valores = [Valor("r esperada", d["r"], decimales=3), Valor("Alfa (dos colas)", d["alpha"]),
               _v_pct("Poder buscado", d["poder"]), Valor("n necesario", n),
               _v_pct("Poder real con ese n", r["power_real"])]
    supuestos = [
        Supuesto("¿La r esperada sale de antes del estudio?", f"r = {num(d['r'])}, declarada",
                 "Se supone",
                 "De un piloto o de la literatura. Calcular el n con la r observada en los "
                 "mismos datos es poder post hoc: no dice nada que el p no diga (Hoenig y "
                 "Heisey 2001)."),
        Supuesto("¿La relación es lineal y los datos, normales bivariados?", "lo supone la "
                 "fórmula", "Se supone",
                 "La z de Fisher es para la r de Pearson. Con relación monótona pero no lineal, "
                 "o con atípicos, se usa Spearman y hace falta algo más de n."),
    ]
    return _armar(
        "tam_correlacion", titulo, valores,
        Metodo("z de Fisher", "El n con el que la prueba de r = 0 detecta la r esperada con el "
                              "poder pedido."),
        supuestos,
        f"Hacen falta {n} sujetos para detectar una correlación de {num(d['r'])}.",
        "Detectar que r no es 0 no dice que la relación sirva para predecir: una r de 0,3 "
        "explica el 9 % de la variación. " + PERDIDAS,
        [Figura("Poder según n", lambda: _curva(
            lambda k: power_correlation(k, d["r"], d["alpha"]), n, r["power_real"],
            d["poder"]))],
        {"tamano": r})
