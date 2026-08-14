"""Guardas de entrada para las funciones del core.

Motivo: una auditoria de robustez sobre datos degenerados (n<3, columnas
constantes, NaN, infinitos, ceros) encontro que el core devolvia valores NO
FINITOS en silencio en 16 de 72 combinaciones, y crasheaba en 2. Devolver NaN
sin avisar es peor que rechazar: el numero llega al informe y se reporta.

Criterio, tomado de como se comporta MedCalc: **nunca crashear, nunca devolver
un numero no finito en silencio, y cuando se rechaza decir por que**. Sus
mensajes son especificos y accionables ("No se pueden manejar valores cero en un
diagrama de Bland-Altman para razones"), no un "datos invalidos" generico.

Contrato: las funciones que usan estas guardas devuelven ``{"error": <motivo>}``
en lugar de ``None`` cuando los datos no sirven. La UI y el Omnianalisis leen esa
clave y la muestran.
"""
import numpy as np

__all__ = ["finite_pair", "finite_one", "ERROR_KEY"]

ERROR_KEY = "error"


def finite_pair(x, y, min_n=3, need_variance=None, positive=False, nombre_metodo=""):
    """Limpia y valida un par de series apareadas.

    Args:
        x, y: secuencias numericas de igual longitud.
        min_n: n minimo DESPUES de descartar los no finitos.
        need_variance: None | "x" | "y" | "both" — exige varianza no nula,
            para metodos que dividen por la dispersion o regresan contra x.
        positive: exige que todos los valores sean > 0 (log, CV, razones).
        nombre_metodo: se inserta en el mensaje para que sea accionable.

    Returns:
        (x_limpio, y_limpio, motivo) — `motivo` es None si los datos sirven.
    """
    suf = f" para {nombre_metodo}" if nombre_metodo else ""
    try:
        x = np.asarray(x, dtype=float).ravel()
        y = np.asarray(y, dtype=float).ravel()
    except (TypeError, ValueError):
        return None, None, f"Los datos no son numericos{suf}."

    if x.size != y.size:
        return None, None, (f"Las dos series deben tener el mismo numero de "
                            f"observaciones{suf} (recibidas {x.size} y {y.size}).")

    n_bruto = x.size
    # isfinite descarta NaN Y +-inf. El core solo miraba isnan, asi que los
    # infinitos se colaban y contaminaban medias, varianzas e IC.
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    n = x.size

    descartados = n_bruto - n
    if n < min_n:
        if n_bruto >= min_n and descartados:
            return None, None, (
                f"Quedan {n} pares utilizables de {n_bruto}{suf}: se descartaron "
                f"{descartados} con valores ausentes o no finitos. Se necesitan al "
                f"menos {min_n}.")
        return None, None, (f"Se necesitan al menos {min_n} pares de datos{suf}; "
                            f"hay {n}.")

    if need_variance in ("x", "both") and np.ptp(x) == 0:
        return None, None, (f"La primera variable es constante (todos los valores "
                            f"iguales a {x[0]:g}){suf}: no se puede estimar una "
                            f"relacion con ella.")
    if need_variance in ("y", "both") and np.ptp(y) == 0:
        return None, None, (f"La segunda variable es constante (todos los valores "
                            f"iguales a {y[0]:g}){suf}.")

    if positive:
        if np.any(x <= 0) or np.any(y <= 0):
            return None, None, (f"Hay valores cero o negativos{suf}, que este "
                                f"metodo no admite (usa cocientes o logaritmos).")

    return x, y, None


def finite_one(x, min_n=3, need_variance=False, nombre_metodo=""):
    """Version de una sola serie. Mismo contrato que `finite_pair`."""
    suf = f" para {nombre_metodo}" if nombre_metodo else ""
    try:
        x = np.asarray(x, dtype=float).ravel()
    except (TypeError, ValueError):
        return None, f"Los datos no son numericos{suf}."
    n_bruto = x.size
    x = x[np.isfinite(x)]
    n = x.size
    if n < min_n:
        descartados = n_bruto - n
        if descartados:
            return None, (f"Quedan {n} valores utilizables de {n_bruto}{suf}; se "
                          f"necesitan al menos {min_n}.")
        return None, f"Se necesitan al menos {min_n} valores{suf}; hay {n}."
    if need_variance and np.ptp(x) == 0:
        return None, (f"Todos los valores son iguales a {x[0]:g}{suf}: la "
                      f"dispersion es cero.")
    return x, None
