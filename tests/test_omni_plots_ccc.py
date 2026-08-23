"""El CCC descompuesto, dibujado.

Un grafico de descomposicion solo sirve si el reparto es exacto. Si los pedazos
no suman el total, el lector ve dos barras que "explican" el desacuerdo y en
realidad falta o sobra un cacho sin nombre. La identidad que sostiene el dibujo:

    1 - rho_c = (1 - rho) + rho * (1 - Cb)

Se prueba sobre los numeros, no sobre los pixeles: los pixeles cambian con
cualquier retoque de estilo y no dicen nada sobre si el reparto cierra.
"""
import os

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.analysis.omni_analyzer import run_omnianalysis  # noqa: E402
from src.analysis.omni_plots import (  # noqa: E402
    ccc_decomposition_figure, comparison_figures,
)
from src.core.bland_altman import concordance_correlation  # noqa: E402

PAR = ("Metodo_A", "Metodo_B")


def _correr(b_de, semilla=3, n=60):
    rng = np.random.default_rng(semilla)
    a = rng.uniform(40, 180, n)
    df = pd.DataFrame({"Metodo_A": a, "Metodo_B": b_de(a, rng)})
    rep = run_omnianalysis(df, list(df.columns), confirmed_comparisons=[PAR])
    return next(b for b in rep["blocks"] if b.get("tipo") == "concordancia")


@pytest.fixture(scope="module")
def bloque_sesgo():
    """Preciso pero descalibrado: rho alto, Cb bajo."""
    return _correr(lambda a, r: a * 1.12 + 6 + r.normal(0, 1.5, len(a)))


@pytest.fixture(scope="module")
def bloque_dispersion():
    """Centrado pero disperso: rho bajo, Cb alto."""
    return _correr(lambda a, r: a + r.normal(0, 22, len(a)))


# ---------------- La identidad que sostiene el dibujo ----------------

@pytest.mark.parametrize("nombre", ["bloque_sesgo", "bloque_dispersion"])
def test_el_reparto_suma_exactamente_uno(nombre, request):
    res = request.getfixturevalue(nombre)["resultados"]
    ccc, rho, cb = res["ccc"], res["ccc_rho"], res["ccc_cb"]
    total = ccc + (1 - rho) + rho * (1 - cb)
    assert total == pytest.approx(1.0, abs=1e-3), (
        "los pedazos de la barra no cubren el total: quedaria un cacho del "
        "desacuerdo sin explicar"
    )


def test_la_descomposicion_es_la_del_core():
    """Que el grafico no recalcule rho y Cb por su cuenta."""
    rng = np.random.default_rng(9)
    a = rng.uniform(40, 180, 50)
    b = a * 1.05 + rng.normal(0, 4, 50)
    r = concordance_correlation(a, b)
    assert r["ccc"] == pytest.approx(r["rho"] * r["cb"], rel=1e-9)


# ---------------- Los dos escenarios tienen que distinguirse ----------------

def test_el_sesgo_puro_pierde_por_sesgo(bloque_sesgo):
    res = bloque_sesgo["resultados"]
    perdida_disp = 1 - res["ccc_rho"]
    perdida_sesgo = res["ccc_rho"] * (1 - res["ccc_cb"])
    assert perdida_sesgo > perdida_disp * 10


def test_la_imprecision_pura_pierde_por_dispersion(bloque_dispersion):
    res = bloque_dispersion["resultados"]
    perdida_disp = 1 - res["ccc_rho"]
    perdida_sesgo = res["ccc_rho"] * (1 - res["ccc_cb"])
    assert perdida_disp > perdida_sesgo


# ---------------- Los datos llegan al grafico ----------------

def test_el_plot_lleva_los_componentes(bloque_sesgo):
    """`_plot` se arma antes de calcular el CCC; si no se completa despues, el
    grafico queda sin rho ni Cb y `comparison_figures` lo saltea en silencio."""
    plot = bloque_sesgo["resultados"]["_plot"]
    for clave in ("ccc", "ccc_rho", "ccc_cb", "ccc_fuerza"):
        assert clave in plot, f"falta {clave} en los datos de gráfico"


def test_el_grafico_entra_en_la_lista_de_figuras(bloque_sesgo):
    figs = comparison_figures(bloque_sesgo["resultados"]["_plot"])
    titulos = [t for t, _ in figs]
    assert "CCC de Lin descompuesto" in titulos
    for _, f in figs:
        plt.close(f)


def test_sin_componentes_no_rompe_las_otras_figuras(bloque_sesgo):
    """`comparison_figures` traga la excepcion: hay que verificar que las otras
    dos sigan saliendo, no solo que no reviente."""
    plot = dict(bloque_sesgo["resultados"]["_plot"])
    for clave in ("ccc", "ccc_rho", "ccc_cb"):
        plot.pop(clave, None)
    titulos = [t for t, _ in comparison_figures(plot)]
    assert "CCC de Lin descompuesto" not in titulos
    assert "Bland-Altman" in titulos and "Regresión de comparación" in titulos


# ---------------- La figura ----------------

def test_la_barra_tiene_los_tres_pedazos(bloque_sesgo):
    fig = ccc_decomposition_figure(bloque_sesgo["resultados"]["_plot"])
    ax_barra = fig.axes[1]
    anchos = [p.get_width() for p in ax_barra.patches]
    assert len(anchos) == 3, "tienen que ser logrado + dispersión + sesgo"
    assert sum(anchos) == pytest.approx(1.0, abs=1e-3)
    assert all(w >= 0 for w in anchos), "un pedazo negativo se dibuja hacia atrás"
    plt.close(fig)


def test_el_panel_izquierdo_lleva_identidad_y_recta_de_cb(bloque_sesgo):
    fig = ccc_decomposition_figure(bloque_sesgo["resultados"]["_plot"])
    etiquetas = [ln.get_label() for ln in fig.axes[0].lines]
    assert any("Identidad" in e for e in etiquetas)
    assert any("Cb compara" in e for e in etiquetas)
    plt.close(fig)


def test_el_texto_no_afirma_descalibracion_por_la_inclinacion(bloque_dispersion):
    """La recta ámbar se inclina por el cociente de dispersiones, no solo por
    descalibración: con ruido grande se inclina sola. Decir "ámbar lejos de la
    gris = mal calibrado" sería falso justo en el caso de imprecisión pura."""
    fig = ccc_decomposition_figure(bloque_dispersion["resultados"]["_plot"])
    textos = " ".join(t.get_text() for t in fig.axes[0].texts)
    assert "calibr" not in textos.lower()
    assert "veracidad (Cb)" in textos
    plt.close(fig)


def test_con_correlacion_negativa_no_se_dibuja_un_reparto_falso():
    """Con rho<=0 los pedazos saldrían negativos. Mejor decirlo que dibujarlo."""
    rng = np.random.default_rng(4)
    a = rng.uniform(40, 180, 40)
    b = -a + rng.normal(0, 5, 40)
    r = concordance_correlation(a, b)
    assert r["rho"] < 0
    fig = ccc_decomposition_figure({
        "x": a, "y": b, "nombre_x": "A", "nombre_y": "B",
        "ccc": r["ccc"], "ccc_rho": r["rho"], "ccc_cb": r["cb"],
        "ccc_fuerza": r["strength"], "ccc_ic95": None,
    })
    ax_barra = fig.axes[1]
    assert len(ax_barra.patches) == 0, "no tiene que haber barra"
    assert "No se puede repartir" in " ".join(t.get_text() for t in ax_barra.texts)
    plt.close(fig)


def test_sin_ic_lo_dice_en_vez_de_dejar_el_hueco(bloque_sesgo):
    plot = dict(bloque_sesgo["resultados"]["_plot"])
    plot["ccc_ic95"] = None
    fig = ccc_decomposition_figure(plot)
    textos = " ".join(t.get_text() for t in fig.axes[1].texts)
    assert "no definido" in textos
    plt.close(fig)
