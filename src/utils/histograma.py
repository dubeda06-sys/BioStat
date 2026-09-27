"""Cuántas barras puede tener un histograma sin que matplotlib reviente."""
import numpy as np


def barras(valores, maximo=50):
    """Numero de barras seguro para un histograma.

    matplotlib revienta con "Too many bins for data range" cuando todos los
    valores son iguales (por ejemplo, el bootstrap de la correlacion de una
    columna consigo misma: siempre 1,0). Con rango cero, una sola barra.

    Vivía en el mixin del panel (`_bins`); al migrar a `Resultado` los
    constructores volvieron a poner un número fijo de barras y el defecto
    volvió con ellos (27 sep). Ahora lo usan todos los histogramas.
    """
    v = np.asarray(valores, dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return 1
    rango = float(np.ptp(v))
    if rango == 0:
        return 1
    # numpy tambien falla cuando el rango existe pero es tan chico que el ancho
    # de barra no se puede representar en punto flotante (p.ej. remuestreos de
    # una correlacion de 0,9999999 que solo difieren en el ultimo bit).
    minimo_representable = float(np.spacing(float(np.max(np.abs(v))))) * 4
    n = min(maximo, max(1, v.size))
    while n > 1 and rango / n <= minimo_representable:
        n //= 2
    return max(1, n)
