"""Gráficos de comparación de métodos: mountain plot, Youden, polar y cascada.

Son gráficos antes que pruebas, pero pasan por `Resultado` igual: qué se
dibujó, con qué datos, cómo se lee y qué no dice.

Dos cambian a propósito: el gráfico de Youden es el interlaboratorio de MedCalc
(antes se dibujaba el índice J contra el umbral, que es de las curvas ROC y ya
está ahí), y la cascada es la de oncología, las barras ordenadas del cambio de
cada paciente (antes una cascada contable acumulada, que no es lo que decía su
ayuda).
"""
from __future__ import annotations

import numpy as np

from src.core.plots import mountain_plot_data, youden_interlaboratorio
from src.resultado.citas import ficha
from src.resultado.datos import columnas_faltantes, filas_completas, una
from src.resultado.modelo import Entrada, Figura, Metodo, Resultado, Supuesto, Valor


def _f(x, dec=4) -> str:
    return Valor("", x, decimales=dec).texto()


def _armar(analisis, titulo, entrada, valores, metodo, supuestos, lectura, matiz,
           figuras, advertencias=(), crudo=None) -> Resultado:
    f = ficha(analisis)
    return Resultado(analisis=analisis, titulo=titulo, entrada=entrada, valores=valores,
                     metodo=metodo, supuestos=list(supuestos), formula=f.formula,
                     citas=list(f.citas), lectura=lectura, matiz=matiz,
                     advertencias=list(advertencias), figuras=list(figuras), crudo=crudo or {})


def _par(analisis, titulo, df, c1, c2):
    falta = columnas_faltantes(df, c1, c2)
    if falta:
        return None, None, None, Resultado.rechazo(analisis, titulo, falta)
    if c1 == c2:
        return None, None, None, Resultado.rechazo(analisis, titulo, "Elegí dos columnas distintas.")
    pares, entrada = filas_completas(df, c1, c2)
    try:
        return (pares[c1].to_numpy(dtype=float), pares[c2].to_numpy(dtype=float), entrada, None)
    except (TypeError, ValueError):
        return None, None, None, Resultado.rechazo(analisis, titulo, "Alguna columna tiene texto.",
                                                   entrada)


# ============================================================

def mountain(df, c1, c2, opciones=None) -> Resultado:
    titulo = f"Mountain plot — {c1} − {c2}"
    x, y, entrada, rechazo = _par("mountain", titulo, df, c1, c2)
    if rechazo is not None:
        return rechazo
    r = mountain_plot_data(x, y)
    falla = Resultado.rechazo_del_core("mountain", titulo, r, entrada)
    if falla is not None:
        return falla
    entrada.n = r["n"]
    valores = [Valor("n", r["n"]), Valor("Mediana de las diferencias (pico)", r["mediana"]),
               Valor("Percentiles 25 a 75", f"{_f(r['p25'])} a {_f(r['p75'])}")]
    if np.isfinite(r["p2_5"]):
        valores.append(Valor("Percentiles 2,5 a 97,5", f"{_f(r['p2_5'])} a {_f(r['p97_5'])}"))
    supuestos = [Supuesto(
        "¿Alcanzan los datos para las colas?", f"n = {r['n']}",
        "Sí" if r["n"] >= 39 else "No",
        ("Con 39 pares o más se estiman los percentiles 2,5 y 97,5." if r["n"] >= 39 else
         "Con menos de 39 pares las colas del 2,5 y 97,5 % caerían fuera de los datos: solo se "
         "informan los cuartiles."), ok=r["n"] >= 39)]
    return _armar(
        "mountain", titulo, entrada, valores,
        Metodo("Mountain plot (distribución acumulada plegada)",
               "Muestra la distribución de las diferencias entre dos métodos sin suponer "
               "ninguna forma: el pico es la diferencia típica y el ancho, el desacuerdo."),
        supuestos,
        f"La diferencia típica ({c1} − {c2}) es {_f(r['mediana'])}; la mitad central de las "
        f"diferencias va de {_f(r['p25'])} a {_f(r['p75'])}.",
        "Dos métodos intercambiables dan una montaña angosta con el pico en 0; cuánto es "
        "«angosta» lo decide el requisito de calidad del analito.",
        [Figura("Mountain plot", lambda: _figura_mountain(r, c1, c2))], crudo={"mountain": r})


def youden(df, c1, c2, opciones=None) -> Resultado:
    """Variable 1 = muestra 1, Variable 2 = muestra 2; una fila por laboratorio."""
    titulo = f"Gráfico de Youden — {c1} y {c2}"
    x, y, entrada, rechazo = _par("youden", titulo, df, c1, c2)
    if rechazo is not None:
        return rechazo
    r = youden_interlaboratorio(x, y)
    falla = Resultado.rechazo_del_core("youden", titulo, r, entrada)
    if falla is not None:
        return falla
    fuera = int(r["fuera_del_circulo"].sum())
    lejanos = int(r["lejanos"].sum())
    sist = r["fuera_del_circulo"] & (np.abs(r["perpendicular"]) < r["s_aleatorio"] * 1.96)
    valores = [Valor("Laboratorios", r["n"]),
               Valor("Mediana de Manhattan", f"{_f(r['mediana_x'])}; {_f(r['mediana_y'])}"),
               Valor("Error aleatorio (s)", r["s_aleatorio"],
                     nota="DE de la distancia a la recta de 45°"),
               Valor("Radio del círculo del 95 %", r["radio_95"]),
               Valor("Fuera del círculo", fuera,
                     nota=f"{int(sist.sum())} de ellos cerca de la recta: error sistemático"),
               Valor("Valores muy lejanos (no entran en las medianas)", lejanos)]
    razon = r["mediana_y"] / r["mediana_x"] if r["mediana_x"] else np.nan
    parecidas = bool(0.5 <= razon <= 2)
    supuestos = [Supuesto(
        "¿Las dos muestras son parecidas en magnitud?",
        f"medianas {_f(r['mediana_x'])} y {_f(r['mediana_y'])}",
        "Sí" if parecidas else "No",
        ("El gráfico original de Youden pide dos muestras parecidas: los errores de un "
         "laboratorio se ven iguales en las dos." if parecidas else
         "Con muestras de magnitud muy distinta, el círculo y la recta de 45° no valen: "
         "MedCalc usa entonces ejes escalados por la DE de cada muestra."),
        ok=parecidas)]
    return _armar(
        "youden", titulo, entrada, valores,
        Metodo("Gráfico de Youden (interlaboratorio)",
               "Cada punto es un laboratorio que midió las mismas dos muestras. Separa el error "
               "sistemático de cada laboratorio (a lo largo de la recta de 45°) del aleatorio "
               "(lejos de la recta)."),
        supuestos,
        (f"{fuera} de {r['n']} laboratorios quedan fuera del círculo del 95 % (error total "
         f"grande); {int(sist.sum())} de ellos por error sistemático." if fuera else
         "Todos los laboratorios quedan dentro del círculo del 95 %."),
        "El círculo supone el mismo error aleatorio en los dos ejes; con muestras de magnitud "
        "muy distinta, esa suposición falla.",
        [Figura("Gráfico de Youden", lambda: _figura_youden(r, c1, c2))],
        crudo={"youden": r})


def polar(df, columnas, opciones=None) -> Resultado:
    if isinstance(columnas, str):
        columnas = [columnas]
    columnas = list(dict.fromkeys(columnas or []))
    titulo = "Gráfico polar"
    if len(columnas) < 3:
        return Resultado.rechazo("polar", titulo, "Hacen falta al menos 3 variables (ejes).")
    falta = columnas_faltantes(df, *columnas)
    if falta:
        return Resultado.rechazo("polar", titulo, falta)
    medias, des = [], []
    for c in columnas:
        col = una(df, c)
        if col.motivo:
            return Resultado.rechazo("polar", titulo, col.motivo)
        medias.append(float(np.mean(col.valores)) if col.entrada.n else np.nan)
        des.append(float(np.std(col.valores, ddof=1)) if col.entrada.n > 1 else np.nan)
    valores = [Valor(c, m, nota=f"DE {_f(d)}") for c, m, d in zip(columnas, medias, des)]
    escalas = [abs(m) for m in medias if np.isfinite(m) and m != 0]
    dispares = bool(escalas) and max(escalas) / min(escalas) > 10
    supuestos = [Supuesto(
        "¿Las variables están en escalas comparables?",
        f"medias de {_f(min(medias))} a {_f(max(medias))}", "No" if dispares else "Sí",
        ("Con escalas que difieren más de 10 veces, los ejes chicos quedan aplastados: "
         "conviene estandarizar las variables antes (por ejemplo, en % del valor de "
         "referencia)." if dispares else "Los ejes se pueden comparar a simple vista."),
        ok=not dispares)]
    entrada = Entrada(columnas=tuple(columnas), n=int(df[columnas].notna().any(axis=1).sum()))
    return _armar(
        "polar", titulo, entrada, valores,
        Metodo("Gráfico polar (radar) de las medias",
               "Un eje por variable; el polígono une las medias."),
        supuestos, "El polígono muestra el perfil de medias de las variables elegidas.",
        "Un radar no compara: el área depende del orden de los ejes.",
        [Figura("Gráfico polar", lambda: _figura_polar(columnas, medias))],
        crudo={"medias": dict(zip(columnas, medias))})


def cascada(df, col, opciones=None) -> Resultado:
    """Oncología: una barra por paciente, el cambio ordenado de mayor a menor."""
    titulo = f"Gráfico de cascada — {col}"
    c = una(df, col)
    if c.motivo:
        return Resultado.rechazo("cascada", titulo, c.motivo)
    v = c.valores
    if len(v) < 2:
        return Resultado.rechazo("cascada", titulo, "Hacen falta al menos 2 valores.", c.entrada)
    orden = np.sort(v)[::-1]
    sube, baja = int(np.sum(v > 0)), int(np.sum(v < 0))
    valores = [Valor("n", len(v)), Valor("Aumentan (> 0)", sube), Valor("Disminuyen (< 0)", baja),
               Valor("Sin cambio", len(v) - sube - baja), Valor("Mediana", float(np.median(v))),
               Valor("Máximo", float(orden[0])), Valor("Mínimo", float(orden[-1]))]
    parece_pct = np.all(v >= -100) and np.ptp(v) > 5
    supuestos = [Supuesto(
        "¿Los valores son cambios (por ejemplo, % respecto del basal)?",
        f"de {_f(orden[-1])} a {_f(orden[0])}", "Parece que sí" if parece_pct else "No está claro",
        ("Cada barra es el cambio de un sujeto, ordenadas de mayor a menor." if parece_pct else
         "El gráfico de cascada se lee como cambios: si la columna son valores absolutos, "
         "calculá antes el cambio respecto del basal."), ok=bool(parece_pct))]
    return _armar(
        "cascada", titulo, c.entrada, valores,
        Metodo("Gráfico de cascada (waterfall)",
               "Una barra por sujeto con su cambio, ordenadas de mayor a menor: se ve de un "
               "vistazo cuántos mejoran y cuánto."),
        supuestos, f"{baja} de {len(v)} disminuyen y {sube} aumentan; la mediana es "
                   f"{_f(np.median(v))}.",
        "En oncología los cortes de respuesta (por ejemplo, −30 % y +20 % de RECIST) se aplican "
        "a la suma de diámetros: si corresponden, marcalos con el editor del gráfico.",
        [Figura("Cascada", lambda: _figura_cascada(orden, col))],
        crudo={"valores_ordenados": orden})


# ============================================================

def _figura_mountain(r, c1, c2):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(r["diferencias"], r["percentil_plegado"], color='#4f6ef7', lw=1.8)
    ax.fill_between(r["diferencias"], r["percentil_plegado"], color='#4f6ef7', alpha=0.12)
    ax.axvline(0, color='#9ca3af', ls=':', lw=1.2, label="Diferencia 0")
    ax.axvline(r["mediana"], color='#ef4444', ls='--', lw=1.2, label=f"Mediana: {r['mediana']:.3f}")
    ax.set_xlabel(f"Diferencia ({c1} − {c2})")
    ax.set_ylabel("Percentil plegado")
    ax.set_ylim(0, 52)
    ax.set_title("Mountain plot", fontweight='bold')
    ax.legend(loc="upper right", framealpha=0.9)
    fig.tight_layout()
    return fig


def _figura_youden(r, c1, c2):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 7))
    x, y = r["x"], r["y"]
    lejos, fuera = r["lejanos"], r["fuera_del_circulo"]
    ax.scatter(x[~fuera], y[~fuera], color='#4f6ef7', s=40, edgecolors='white', label="Laboratorio")
    ax.scatter(x[fuera], y[fuera], color='#ef4444', s=55, edgecolors='white',
               label="Fuera del círculo del 95 %")
    if lejos.any():
        ax.scatter(x[lejos], y[lejos], facecolors='none', edgecolors='#2c3650', s=110,
                   label="Muy lejano (no entra en las medianas)")
    mx, my = r["mediana_x"], r["mediana_y"]
    ax.axvline(mx, color='#8892a4', lw=1)
    ax.axhline(my, color='#8892a4', lw=1)
    lim = max(np.ptp(x), np.ptp(y), 2.2 * r["radio_95"]) * 0.6
    t = np.linspace(-lim, lim, 2)
    ax.plot(mx + t, my + t, color='#d97706', ls='--', lw=1.2, label="Recta de 45°")
    ax.add_patch(plt.Circle((mx, my), r["radio_95"], fill=False, color='#ef4444', ls='--', lw=1.2))
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_xlabel(f"{c1} (muestra 1)")
    ax.set_ylabel(f"{c2} (muestra 2)")
    ax.set_title("Gráfico de Youden", fontweight='bold')
    ax.legend(framealpha=0.9, fontsize=9)
    fig.tight_layout()
    return fig


def _figura_polar(nombres, medias):
    import matplotlib.pyplot as plt

    angulos = np.linspace(0, 2 * np.pi, len(nombres), endpoint=False).tolist()
    vals = list(medias) + [medias[0]]
    angulos_c = angulos + [angulos[0]]
    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    ax.plot(angulos_c, vals, 'o-', lw=2, color='#4f6ef7')
    ax.fill(angulos_c, vals, alpha=0.25, color='#4f6ef7')
    ax.set_xticks(angulos, [str(n) for n in nombres])
    ax.set_title("Gráfico polar de las medias", fontweight='bold', pad=20)
    fig.tight_layout()
    return fig


def _figura_cascada(orden, col):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 5))
    colores = ['#ef4444' if v > 0 else '#22c55e' if v < 0 else '#8892a4' for v in orden]
    ax.bar(range(len(orden)), orden, color=colores, width=0.85)
    ax.axhline(0, color='black', lw=0.6)
    ax.set_xticks([])
    ax.set_xlabel("Sujetos, del mayor aumento a la mayor disminución")
    ax.set_ylabel(str(col))
    ax.set_title("Gráfico de cascada", fontweight='bold')
    fig.tight_layout()
    return fig
