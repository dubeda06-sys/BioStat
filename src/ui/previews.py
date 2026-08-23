"""Vista previa de cada analisis: un mini grafico con datos de ejemplo.

Elegir entre 76 rutinas por su nombre exige saber de antemano que hace cada
una. Un dibujo chico de la salida tipica resuelve eso antes de correr nada:
"Passing-Bablok" no dice mucho, pero una nube de puntos con su recta de ajuste
y la identidad punteada, si.

Los dibujos se generan con matplotlib sobre datos sinteticos fijos (semilla
constante, asi la vista previa no cambia entre aperturas) y se guardan en
memoria y en un PNG temporal — el archivo hace falta porque los tooltips de Qt
solo aceptan imagenes por ruta, no incrustadas.

No son los datos del usuario: son la *forma* del resultado. El pie de la vista
previa lo aclara para que nadie lea numeros de ahi.
"""
import os
import tempfile

import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ANCHO, ALTO = 3.0, 1.75   # pulgadas
DPI = 100

AZUL = "#0e7490"
GRIS = "#94a3b8"
ROJO = "#dc2626"
VERDE = "#16a34a"

_rng = lambda: np.random.RandomState(7)  # noqa: E731 - semilla fija a proposito

_cache_png = {}


# --------------------------------------------------------------------------
# Que muestra cada familia, en una linea
# --------------------------------------------------------------------------
DESCRIPCION = {
    "histograma": "Distribucion de una variable, con su media.",
    "caja": "Comparacion de la dispersion entre grupos.",
    "pares": "Cada sujeto medido dos veces: se mira el cambio.",
    "dispersion": "Relacion entre dos variables.",
    "ajuste": "Nube de puntos con la recta ajustada y su banda.",
    "bland_altman": "Diferencia contra promedio, con sesgo y limites de acuerdo.",
    "regresion_metodos": "Recta de un metodo contra el otro, frente a la identidad.",
    "mountain": "Distribucion acumulada plegada de las diferencias.",
    "youden": "Un punto por laboratorio: sesgo en los dos niveles a la vez.",
    "polar": "Diferencias en coordenadas polares.",
    "waterfall": "Un caso por barra, ordenados de mayor a menor.",
    "roc": "Sensibilidad contra 1-especificidad; el area es el rendimiento.",
    "supervivencia": "Proporcion que sigue libre de evento a lo largo del tiempo.",
    "contingencia": "Frecuencias por categoria en dos grupos.",
    "cuadricula": "Tabla 2x2 de acuerdo entre dos clasificaciones.",
    "bosque": "Un estudio por linea, con su IC y el resumen combinado.",
    "bootstrap": "Distribucion de la remuestra, con el IC del percentil.",
    "tamano": "Cuanto n hace falta segun el tamano del efecto.",
    "importancia": "Peso de cada variable en el modelo.",
    "serie": "Mediciones repetidas en el tiempo.",
    "tabla": "Salida numerica: este analisis no dibuja un grafico.",
}


# --------------------------------------------------------------------------
# Dibujos
# --------------------------------------------------------------------------
def _lienzo():
    fig, ax = plt.subplots(figsize=(ANCHO, ALTO), dpi=DPI)
    ax.tick_params(labelsize=6, length=2, pad=1)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color("#c8c8c8")
    ax.set_xticks([])
    ax.set_yticks([])
    return fig, ax


def _histograma(ax, r):
    d = r.normal(0, 1, 400)
    ax.hist(d, bins=18, color=AZUL, alpha=0.75, edgecolor="white", linewidth=0.5)
    ax.axvline(d.mean(), color=ROJO, ls="--", lw=1.2)


def _caja(ax, r):
    grupos = [r.normal(m, s, 40) for m, s in ((0, 1), (0.9, 1.2), (0.3, 0.8))]
    caja = ax.boxplot(grupos, patch_artist=True, widths=0.5)
    for parche in caja["boxes"]:
        parche.set(facecolor="#cfe8ee", edgecolor=AZUL, linewidth=1)
    for elemento in ("whiskers", "caps", "medians"):
        for linea in caja[elemento]:
            linea.set(color=AZUL, linewidth=1)


def _pares(ax, r):
    antes = r.normal(5, 1, 9)
    despues = antes + r.normal(0.9, 0.5, 9)
    for a, d in zip(antes, despues):
        ax.plot([0, 1], [a, d], color=GRIS, lw=0.8, marker="o", ms=2.5,
                markerfacecolor=AZUL, markeredgecolor=AZUL)
    ax.set_xlim(-0.3, 1.3)


def _dispersion(ax, r):
    x = r.normal(0, 1, 60)
    y = 0.8 * x + r.normal(0, 0.55, 60)
    ax.scatter(x, y, s=7, color=AZUL, alpha=0.75)


def _ajuste(ax, r):
    x = np.sort(r.uniform(0, 10, 50))
    y = 1.4 * x + 2 + r.normal(0, 1.4, 50)
    ax.scatter(x, y, s=7, color=AZUL, alpha=0.7)
    coef = np.polyfit(x, y, 1)
    ajuste = np.polyval(coef, x)
    residuo = np.std(y - ajuste)
    ax.plot(x, ajuste, color=ROJO, lw=1.3)
    ax.fill_between(x, ajuste - 1.96 * residuo, ajuste + 1.96 * residuo,
                    color=ROJO, alpha=0.10)


def _bland_altman(ax, r):
    a = r.normal(100, 12, 45)
    b = a + r.normal(2.5, 5, 45)
    promedio, diferencia = (a + b) / 2, a - b
    sesgo, de = diferencia.mean(), diferencia.std()
    ax.scatter(promedio, diferencia, s=8, color=AZUL, alpha=0.75)
    ax.axhline(sesgo, color=VERDE, lw=1.3)
    for signo in (1, -1):
        ax.axhline(sesgo + signo * 1.96 * de, color=ROJO, ls="--", lw=1)
    ax.fill_between([promedio.min(), promedio.max()], sesgo - 1.96 * de,
                    sesgo + 1.96 * de, color=VERDE, alpha=0.06)


def _regresion_metodos(ax, r):
    x = np.sort(r.uniform(2, 10, 40))
    y = 1.08 * x - 0.3 + r.normal(0, 0.45, 40)
    ax.scatter(x, y, s=8, color=AZUL, alpha=0.75)
    ax.plot([x.min(), x.max()], [x.min(), x.max()], color=GRIS, ls=":", lw=1)
    coef = np.polyfit(x, y, 1)
    ax.plot(x, np.polyval(coef, x), color=ROJO, lw=1.3)


def _mountain(ax, r):
    d = np.sort(r.normal(1.5, 4, 300))
    p = np.arange(1, len(d) + 1) / len(d)
    plegada = np.where(p <= 0.5, p, 1 - p)
    ax.plot(d, plegada, color=AZUL, lw=1.4)
    ax.fill_between(d, plegada, color=AZUL, alpha=0.15)
    ax.axvline(0, color=GRIS, ls=":", lw=1)


def _youden(ax, r):
    x = r.normal(0, 1, 30)
    y = 0.55 * x + r.normal(0, 0.85, 30)
    ax.scatter(x, y, s=9, color=AZUL, alpha=0.75)
    ax.axhline(0, color=GRIS, lw=0.8)
    ax.axvline(0, color=GRIS, lw=0.8)
    circulo = plt.Circle((0, 0), 2.0, fill=False, color=ROJO, ls="--", lw=1)
    ax.add_patch(circulo)
    ax.set_aspect("equal")


def _polar(ax_no_usado, r):
    # El polar necesita su propio eje: se descarta el cartesiano recibido.
    fig = ax_no_usado.figure
    fig.clf()
    ax = fig.add_subplot(projection="polar")
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.tick_params(length=0)
    angulo = r.uniform(-0.5, 0.5, 40)
    radio = r.uniform(0.2, 1.0, 40)
    ax.scatter(angulo, radio, s=8, color=AZUL, alpha=0.8)
    ax.set_thetamin(-45)
    ax.set_thetamax(45)


def _waterfall(ax, r):
    v = np.sort(r.normal(0, 30, 22))[::-1]
    ax.bar(range(len(v)), v, color=[VERDE if x > 0 else ROJO for x in v], width=0.75)
    ax.axhline(0, color="#404040", lw=0.8)


def _roc(ax, r):
    fpr = np.linspace(0, 1, 60)
    tpr = fpr ** 0.35
    ax.plot(fpr, tpr, color=AZUL, lw=1.6)
    ax.fill_between(fpr, tpr, alpha=0.12, color=AZUL)
    ax.plot([0, 1], [0, 1], color=GRIS, ls="--", lw=1)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)


def _supervivencia(ax, r):
    t = np.arange(0, 12)
    for caida, color in ((0.88, AZUL), (0.78, ROJO)):
        s = caida ** t
        ax.step(t, s, where="post", color=color, lw=1.4)
    ax.set_ylim(0, 1.05)


def _contingencia(ax, r):
    x = np.arange(3)
    ax.bar(x - 0.18, [22, 15, 9], width=0.34, color=AZUL)
    ax.bar(x + 0.18, [12, 19, 17], width=0.34, color="#7dd3d8")


def _cuadricula(ax, r):
    tabla = np.array([[41, 6], [8, 35]])
    ax.imshow(tabla, cmap="Blues", vmin=0, vmax=50)
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(tabla[i, j]), ha="center", va="center",
                    fontsize=8, color="#1a1a1a")
    ax.set_xticks([])
    ax.set_yticks([])


def _bosque(ax, r):
    efectos = [0.8, 1.15, 0.95, 1.4, 1.05]
    for i, e in enumerate(efectos):
        ancho = 0.18 + 0.06 * i
        ax.plot([e - ancho, e + ancho], [i, i], color=GRIS, lw=1)
        ax.plot(e, i, marker="s", ms=4, color=AZUL)
    ax.plot(1.05, -1, marker="D", ms=7, color=ROJO)
    ax.axvline(1, color=GRIS, ls=":", lw=1)
    ax.set_ylim(-1.8, len(efectos))


def _bootstrap(ax, r):
    d = r.normal(0, 1, 2000)
    ax.hist(d, bins=30, color=AZUL, alpha=0.75, edgecolor="white", linewidth=0.4)
    for q in np.percentile(d, [2.5, 97.5]):
        ax.axvline(q, color=ROJO, ls="--", lw=1.1)


def _tamano(ax, r):
    efecto = np.linspace(0.2, 1.2, 60)
    n = 16 / efecto ** 2
    ax.plot(efecto, n, color=AZUL, lw=1.6)
    ax.fill_between(efecto, n, alpha=0.12, color=AZUL)


def _importancia(ax, r):
    valores = [0.34, 0.26, 0.18, 0.12, 0.07]
    ax.barh(range(len(valores)), valores[::-1], color=AZUL, height=0.6)


def _serie(ax, r):
    t = np.arange(24)
    y = 100 + np.cumsum(r.normal(0, 1.1, 24))
    ax.plot(t, y, color=AZUL, lw=1.3, marker="o", ms=2.5)
    ax.axhline(y.mean(), color=GRIS, ls="--", lw=1)


def _tabla(ax, r):
    ax.axis("off")
    filas = ["n            48", "Media    3.82", "DE         0.55", "IC 95%  ±0.16"]
    for i, texto in enumerate(filas):
        ax.text(0.06, 0.82 - i * 0.22, texto, fontsize=7.5, family="monospace",
                color="#1a1a1a", transform=ax.transAxes)
    ax.add_patch(plt.Rectangle((0.02, 0.05), 0.96, 0.9, fill=False,
                               edgecolor="#c8c8c8", lw=1,
                               transform=ax.transAxes))


DIBUJOS = {
    "histograma": _histograma, "caja": _caja, "pares": _pares,
    "dispersion": _dispersion, "ajuste": _ajuste, "bland_altman": _bland_altman,
    "regresion_metodos": _regresion_metodos, "mountain": _mountain,
    "youden": _youden, "polar": _polar, "waterfall": _waterfall, "roc": _roc,
    "supervivencia": _supervivencia, "contingencia": _contingencia,
    "cuadricula": _cuadricula, "bosque": _bosque, "bootstrap": _bootstrap,
    "tamano": _tamano, "importancia": _importancia, "serie": _serie,
    "tabla": _tabla,
}


# --------------------------------------------------------------------------
# Que familia le toca a cada analisis
# --------------------------------------------------------------------------
# Por grupo del menu (src/ui/menus.py); las excepciones van en POR_ANALISIS.
POR_GRUPO = {
    "Resumen y distribucion": "histograma",
    "Correlacion": "dispersion",
    "Regresion": "ajuste",
    "Comparacion de medias": "caja",
    "ANOVA": "caja",
    "Pruebas no parametricas": "caja",
    "Proporciones y tablas de contingencia": "contingencia",
    "Concordancia y confiabilidad": "cuadricula",
    "Comparacion de metodos": "bland_altman",
    "Curvas ROC": "roc",
    "Analisis de supervivencia": "supervivencia",
    "Valores de referencia": "histograma",
    "Tamano de muestra y poder": "tamano",
    "Remuestreo (bootstrap)": "bootstrap",
    "Machine learning": "importancia",
}

POR_ANALISIS = {
    # Resumen: los atipicos se ven en una caja, no en un histograma.
    "Outliers (Grubbs)": "caja",
    "Outliers (Tukey)": "caja",
    "Outliers (ESD)": "caja",
    "Tabla de percentiles": "tabla",
    "Media geometrica": "tabla",
    "Media armonica": "tabla",
    "Media recortada": "tabla",
    "Asimetria y curtosis": "histograma",
    # Pruebas sobre el mismo sujeto medido dos veces.
    "t-test pareado": "pares",
    "Wilcoxon pareado": "pares",
    "Sign test": "pares",
    "Friedman": "pares",
    "Medidas repetidas": "pares",
    "McNemar": "cuadricula",
    "Cochran Q": "pares",
    # Comparacion de metodos: cada una tiene su dibujo propio.
    "Passing-Bablok": "regresion_metodos",
    "Deming regression": "regresion_metodos",
    "Mountain plot": "mountain",
    "Youden plot": "youden",
    "Polar plot": "polar",
    "Waterfall chart": "waterfall",
    # Concordancia numerica: pares, no cuadricula de categorias.
    "ICC": "pares",
    "Cronbach alfa": "tabla",
    "CV duplicatas": "pares",
    # Sin grafico propio: la salida es numerica.
    "Comparar 2 medias": "tabla",
    "Comparar 2 proporciones": "tabla",
    "Poder estadistico": "tamano",
    "Regresion logistica": "roc",
    "Probit regression": "ajuste",
    "Cox regression": "supervivencia",
    "Meta-analisis": "bosque",
    "Mediciones seriales": "serie",
    "Diagnostic test": "cuadricula",
    "Likelihood Ratios": "cuadricula",
    "Comparar 2 AUC": "roc",
    "Edad-relacionada": "ajuste",
    "F-test (varianzas)": "caja",
}


def familia(analisis):
    """Familia de vista previa de un analisis."""
    if analisis in POR_ANALISIS:
        return POR_ANALISIS[analisis]
    from src.ui.menus import MENU_ESTADISTICAS
    for grupo, items in MENU_ESTADISTICAS:
        if any(combo == analisis for _, combo in items):
            return POR_GRUPO.get(grupo, "tabla")
    return "tabla"


def descripcion(analisis):
    """Una linea sobre que muestra el grafico del analisis."""
    return DESCRIPCION.get(familia(analisis), DESCRIPCION["tabla"])


def figura(analisis):
    """Figura de matplotlib con la vista previa. El que llama la cierra."""
    fig, ax = _lienzo()
    DIBUJOS.get(familia(analisis), _tabla)(ax, _rng())
    fig.tight_layout(pad=0.3)
    return fig


def ruta_png(analisis):
    """PNG de la vista previa en disco temporal, cacheado por familia.

    Los tooltips de Qt piden la imagen por ruta (`<img src=...>`), de ahi el
    archivo. Se dibuja una sola vez por familia y sesion.
    """
    clave = familia(analisis)
    if clave in _cache_png and os.path.exists(_cache_png[clave]):
        return _cache_png[clave]

    carpeta = os.path.join(tempfile.gettempdir(), "biostat-vistas-previas")
    os.makedirs(carpeta, exist_ok=True)
    destino = os.path.join(carpeta, f"{clave}.png")

    fig = figura(analisis)
    fig.savefig(destino, dpi=DPI, facecolor="white")
    plt.close(fig)

    _cache_png[clave] = destino
    return destino


def pixmap(analisis):
    """QPixmap de la vista previa, listo para un QLabel."""
    from PyQt6.QtGui import QPixmap
    return QPixmap(ruta_png(analisis))


def tooltip(analisis, ayuda=""):
    """Tooltip enriquecido: la miniatura arriba y el texto abajo."""
    ruta = ruta_png(analisis).replace("\\", "/")
    texto = ayuda or ""
    if len(texto) > 260:
        texto = texto[:259] + "…"
    return (f"<div style='max-width:320px'><img src='file:///{ruta}'><br>"
            f"<b>{analisis}</b><br>{texto}</div>")
