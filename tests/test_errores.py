"""Un fallo de un analisis no puede llevarse puesta la aplicacion.

PyQt6 aborta el proceso cuando una excepcion sale de un slot. Con 76 analisis
colgados del menu, eso convertia cualquier eleccion rara de columnas en un
cierre instantaneo, sin mensaje. Estos tests cubren el colchon (`errores`) y el
caso concreto que lo destapo: el histograma del bootstrap con una distribucion
de rango practicamente nulo.
"""
import numpy as np

from src.utils import errores
from src.utils.histograma import barras as _bins


def test_el_manejador_no_relanza_la_excepcion():
    try:
        raise ValueError("prueba")
    except ValueError:
        import sys
        tipo, valor, tb = sys.exc_info()
        errores.manejar(tipo, valor, tb, mostrar=False)  # no debe propagar

    assert errores.ultimo_error is not None
    assert errores.ultimo_error[0] is ValueError
    assert "prueba" in errores.ultimo_error[2]


def test_instalar_es_idempotente():
    import sys
    original = sys.excepthook
    try:
        errores.instalar()
        errores.instalar()
        assert sys.excepthook is errores.manejar
    finally:
        sys.excepthook = original


def test_bins_con_datos_normales():
    v = np.random.RandomState(0).normal(0, 1, 200)
    n = _bins(v)
    assert 1 < n <= 50


def test_bins_con_valores_identicos():
    # El bootstrap de la correlacion de una columna consigo misma da 1,0 en
    # cada remuestreo: rango cero.
    assert _bins(np.ones(500)) == 1


def test_bins_con_rango_infinitesimal():
    # Rango real pero mas chico que la resolucion del punto flotante: numpy
    # tira "Too many bins for data range" si se le piden 50 barras.
    v = 0.9999999 + np.arange(500) * np.spacing(1.0)
    n = _bins(v)
    assert np.histogram(v, bins=n)  # no debe levantar ValueError


def test_bins_sin_datos_finitos():
    assert _bins(np.array([np.nan, np.inf, -np.inf])) == 1
    assert _bins(np.array([])) == 1


def test_el_histograma_del_bootstrap_no_revienta():
    """La combinacion exacta que mataba la app al elegirla desde el menu."""
    valores = np.full(1000, 0.9999999) + np.arange(1000) * np.spacing(1.0)
    np.histogram(valores, bins=_bins(valores))


def test_los_histogramas_de_los_constructores_no_revientan_con_rango_minimo():
    """Al migrar a `Resultado` el bootstrap volvió a `bins=60` fijo, y con una
    distribución de rango mínimo matplotlib reventaba (27 sep). Los tres
    histogramas de los constructores usan ahora `barras`."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from src.resultado.constructores.bootstrap import _figura_dist
    from src.resultado.constructores.referencia import _figura_intervalo
    from src.resultado.constructores.resumen import _figura_histograma

    v = np.array([0.9999999999999998, 1.0, 0.9999999999999999] * 40)
    fig = _figura_dist(v, 1.0, {"ci_lower": 1.0, "ci_upper": 1.0}, "r")
    plt.close(fig)
    fig = _figura_histograma(v, "X", 1.0, 0.0)
    plt.close(fig)
    ri = {"lower": 1.0, "upper": 1.0, "ci_lower_low": 1.0, "ci_lower_high": 1.0,
          "ci_upper_low": 1.0, "ci_upper_high": 1.0}
    fig = _figura_intervalo(v, ri, None, None, "X")
    plt.close(fig)
