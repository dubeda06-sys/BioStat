"""Vista previa: cada analisis tiene un dibujo, y el dibujo se puede dibujar.

Un analisis sin familia asignada caeria en la vista generica de tabla y el
usuario veria "salida numerica" para algo que si tiene grafico — un cartel
equivocado es peor que ninguno.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.ui import previews  # noqa: E402
from src.ui.help_text import ANALYSIS_HELP  # noqa: E402


def test_todos_los_analisis_tienen_una_familia_dibujable():
    sin_dibujo = [a for a in ANALYSIS_HELP if previews.familia(a) not in previews.DIBUJOS]
    assert sin_dibujo == [], f"analisis sin dibujo de vista previa: {sin_dibujo}"


def test_todas_las_familias_tienen_descripcion():
    faltan = [f for f in previews.DIBUJOS if f not in previews.DESCRIPCION]
    assert faltan == [], f"familias sin texto que explique el dibujo: {faltan}"


def test_no_hay_familias_declaradas_de_mas():
    sobran = [f for f in previews.DESCRIPCION if f not in previews.DIBUJOS]
    assert sobran == [], f"descripciones sin dibujo detras: {sobran}"


def test_las_familias_declaradas_por_grupo_existen():
    invalidas = [f for f in previews.POR_GRUPO.values() if f not in previews.DIBUJOS]
    invalidas += [f for f in previews.POR_ANALISIS.values() if f not in previews.DIBUJOS]
    assert invalidas == [], f"familias inventadas: {invalidas}"


def test_la_excepcion_gana_sobre_el_grupo():
    # Passing-Bablok esta en el grupo "Comparacion de metodos" (bland_altman),
    # pero su dibujo propio es la recta contra la identidad.
    assert previews.familia("Bland-Altman") == "bland_altman"
    assert previews.familia("Passing-Bablok") == "regresion_metodos"


def test_un_analisis_desconocido_cae_en_tabla():
    assert previews.familia("no existe") == "tabla"


def test_la_figura_se_dibuja():
    fig = previews.figura("Bland-Altman")
    try:
        assert fig.get_axes(), "la figura salio sin ejes"
    finally:
        plt.close(fig)


def test_el_png_se_escribe_y_se_cachea():
    ruta = previews.ruta_png("Curva ROC")
    assert os.path.exists(ruta) and os.path.getsize(ruta) > 0
    # Segunda llamada: misma familia, mismo archivo, sin volver a dibujar.
    assert previews.ruta_png("Comparar 2 AUC") == ruta


def test_analisis_de_la_misma_familia_comparten_dibujo():
    assert previews.ruta_png("Kaplan-Meier") == previews.ruta_png("Cox regression")


def test_el_tooltip_lleva_la_imagen_y_el_nombre():
    html = previews.tooltip("Bland-Altman", ANALYSIS_HELP["Bland-Altman"])
    assert "<img src='file:///" in html
    assert "bland_altman.png" in html
    assert "Bland-Altman" in html


def test_el_tooltip_recorta_la_ayuda_larga():
    html = previews.tooltip("Bland-Altman", "x" * 900)
    assert "…" in html
    assert "x" * 900 not in html
