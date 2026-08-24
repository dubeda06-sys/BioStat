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
import matplotlib.colors  # noqa: E402
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

_RIEL = matplotlib.colors.to_rgba("#f1f5f9")
_FILA_REPARTO = 0.55


def _segmentos_del_reparto(fig):
    """Los pedazos de colores de la barra de reparto, sin el riel de fondo.

    El panel derecho tiene tres filas: el riel de rho, el de Cb y el del
    reparto. Hay que quedarse con la fila del reparto y descartar su riel, que
    es el rectangulo gris que llega a 1 y solo sirve de referencia.
    """
    ax = fig.axes[1]
    fila = [q for q in ax.patches
            if abs(q.get_y() + q.get_height() / 2 - _FILA_REPARTO) < 0.02]
    return [q for q in fila if tuple(q.get_facecolor()[:3]) != _RIEL[:3]]


def test_la_barra_del_reparto_tiene_los_tres_pedazos(bloque_sesgo):
    fig = ccc_decomposition_figure(bloque_sesgo["resultados"]["_plot"])
    anchos = [q.get_width() for q in _segmentos_del_reparto(fig)]
    assert len(anchos) == 3, "tienen que ser logrado + dispersión + sesgo"
    assert sum(anchos) == pytest.approx(1.0, abs=1e-3)
    assert all(w >= 0 for w in anchos), "un pedazo negativo se dibuja hacia atrás"
    plt.close(fig)


def test_el_panel_izquierdo_no_repite_el_grafico_de_regresion(bloque_sesgo):
    """La version anterior ponia a la izquierda un diagrama de dispersion de
    los datos crudos con la identidad y una recta inclinada — o sea, el mismo
    grafico de regresion de comparacion que ya esta dos pestanas antes.
    Repetirlo no agregaba una vista: gastaba medio grafico.

    El panel izquierdo ahora ubica UN punto, el par (Cb, rho), en el plano de
    la descomposicion. Si alguna vez vuelve a dibujar los n datos, este test
    cae.
    """
    plot = bloque_sesgo["resultados"]["_plot"]
    n_datos = len(plot["x"])
    fig = ccc_decomposition_figure(plot)
    ax = fig.axes[0]
    grandes = [c.get_offsets().shape[0] for c in ax.collections
               if c.get_gid() != "ccc_punto"
               and getattr(c, "get_offsets", None)
               and getattr(c.get_offsets(), "ndim", 0) == 2
               and c.get_offsets().shape[0] > 5]
    assert not grandes, (
        f"el panel dibuja nubes de {grandes} puntos: volvió a ser un diagrama "
        f"de dispersión de los datos ({n_datos} observaciones)")
    plt.close(fig)


def test_el_mapa_ubica_el_punto_en_las_coordenadas_cb_rho(bloque_sesgo):
    """El punto ES la descomposicion: su abscisa es Cb y su ordenada rho."""
    # Contra `_plot` y no contra `resultados`: ahi los valores van redondeados
    # a 4 decimales para mostrar, y el punto se dibuja con el valor completo.
    plot = bloque_sesgo["resultados"]["_plot"]
    fig = ccc_decomposition_figure(plot)
    ax = fig.axes[0]
    marcas = [c.get_offsets() for c in ax.collections
              if c.get_gid() == "ccc_punto"]
    assert marcas, "no se dibujó el punto"
    x_pt, y_pt = float(marcas[0][0][0]), float(marcas[0][0][1])
    assert x_pt == pytest.approx(plot["ccc_cb"], abs=1e-12)
    assert y_pt == pytest.approx(plot["ccc_rho"], abs=1e-12)
    plt.close(fig)


def test_el_punto_entra_entero_en_el_mapa(bloque_sesgo):
    """Con datos buenos rho ronda 0,999: con el limite superior justo en 1 el
    punto quedaba partido por el borde."""
    for nombre in ("bloque_sesgo",):
        res = bloque_sesgo["resultados"]
        fig = ccc_decomposition_figure(res["_plot"])
        ax = fig.axes[0]
        (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
        assert x0 < res["ccc_cb"] < x1
        assert y0 < res["ccc_rho"] < y1
        assert y1 > 1.0, "el techo tiene que pasar de 1 para no cortar el punto"
        plt.close(fig)


def test_los_dos_escenarios_caen_en_lugares_distintos_del_mapa(
        bloque_sesgo, bloque_dispersion):
    """La razon de ser de la figura: el mismo rho_c bajo puede venir de
    descalibracion o de imprecision, y se arreglan por vias distintas. En el
    mapa eso son dos esquinas opuestas."""
    s = bloque_sesgo["resultados"]
    d = bloque_dispersion["resultados"]
    assert s["ccc_cb"] < s["ccc_rho"], "sesgo puro: arriba a la izquierda"
    assert d["ccc_rho"] < d["ccc_cb"], "imprecisión pura: abajo a la derecha"


def test_el_texto_no_afirma_descalibracion(bloque_dispersion):
    """Cb tambien baja por un cociente de dispersiones distinto de 1, no solo
    por descalibracion. Decir "Cb bajo = mal calibrado" seria falso justo en el
    caso de imprecision pura, que es uno de los dos que el grafico existe para
    distinguir."""
    fig = ccc_decomposition_figure(bloque_dispersion["resultados"]["_plot"])
    textos = " ".join(t.get_text() for ax in fig.axes for t in ax.texts)
    textos += " " + " ".join(ax.get_xlabel() + " " + ax.get_ylabel()
                             for ax in fig.axes)
    assert "calibr" not in textos.lower()
    assert "veracidad" in textos.lower() and "precisión" in textos.lower()
    plt.close(fig)


def test_las_zonas_de_mcbride_estan_nombradas(bloque_sesgo):
    """Sin leyenda, las bandas de color son manchas."""
    fig = ccc_decomposition_figure(bloque_sesgo["resultados"]["_plot"])
    leyenda = fig.axes[0].get_legend()
    assert leyenda is not None, "el mapa no tiene leyenda de zonas"
    etiquetas = [t.get_text().lower() for t in leyenda.get_texts()]
    for zona in ("pobre", "moderada", "sustancial", "casi perfecta"):
        assert zona in etiquetas, f"falta la zona '{zona}'"
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
