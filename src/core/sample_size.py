"""Calculo de tamano muestral y poder estadistico."""
import numpy as np
from scipy import stats

# La prueba que se va a correr es una t, no una z: el valor critico depende de
# los grados de libertad, que dependen de n. La formula cerrada con z ignora
# eso y devuelve un n corto. Con n grande la diferencia es de 2 sujetos y no
# importa; con efecto grande importa mucho: para delta/sd = 2 la formula con z
# pedia n=2 cuando hacen falta 5, y el poder real de ese n=2 era 0.18, no 0.80.
# Aca se busca el n mas chico cuyo poder EXACTO (t no central) llega al pedido.


def _poder_una_muestra(n, tamano_efecto, alpha):
    """Poder exacto de la t de una muestra / pareada, a dos colas."""
    if n < 2:
        return 0.0
    df = n - 1
    ncp = tamano_efecto * np.sqrt(n)
    crit = stats.t.ppf(1 - alpha / 2, df)
    return float(stats.nct.sf(crit, df, ncp) + stats.nct.cdf(-crit, df, ncp))


def _poder_dos_muestras(n1, n2, tamano_efecto, alpha):
    """Poder exacto de la t de dos muestras independientes, a dos colas."""
    if n1 < 2 or n2 < 2:
        return 0.0
    df = n1 + n2 - 2
    ncp = tamano_efecto / np.sqrt(1 / n1 + 1 / n2)
    crit = stats.t.ppf(1 - alpha / 2, df)
    return float(stats.nct.sf(crit, df, ncp) + stats.nct.cdf(-crit, df, ncp))


def _n_minimo(poder_de, objetivo, n_tope=2_000_000):
    """El n mas chico con poder >= objetivo. El poder crece con n, asi que
    alcanza con acotar por duplicacion y despues buscar en binario."""
    n = 2
    while n < n_tope and poder_de(n) < objetivo:
        n *= 2
    if n >= n_tope:
        return None
    bajo, alto = n // 2, n
    while bajo < alto:
        medio = (bajo + alto) // 2
        if poder_de(medio) >= objetivo:
            alto = medio
        else:
            bajo = medio + 1
    return bajo


def sample_size_mean(delta, sd, alpha=0.05, power=0.80):
    """Tamano muestral para comparar una media con un valor conocido.

    Args:
        delta: Diferencia minima a detectar
        sd: Desviacion estandar esperada
        alpha: Nivel de significancia (default 0.05)
        power: Poder estadistico (default 0.80)

    Returns:
        dict con n requerido
    """
    if delta == 0 or sd == 0:
        return None
    if not 0 < power < 1 or not 0 < alpha < 1:
        return None

    efecto = abs(delta) / abs(sd)
    n = _n_minimo(lambda k: _poder_una_muestra(k, efecto, alpha), power)
    if n is None:
        return None

    return {
        "n_per_group": n,
        "n_total": n,
        "delta": delta,
        "sd": sd,
        "alpha": alpha,
        "power": power,
        "power_real": _poder_una_muestra(n, efecto, alpha),
        "effect_size": delta / sd,
    }


def sample_size_two_means(delta, sd, alpha=0.05, power=0.80, ratio=1):
    """Tamano muestral para comparar dos medias.

    Args:
        delta: Diferencia minima a detectar entre medias
        sd: DE comun esperada
        alpha: Nivel de significancia
        power: Poder estadistico
        ratio: Ratio n2/n1

    Returns:
        dict con n por grupo
    """
    if delta == 0 or sd == 0 or ratio <= 0:
        return None
    if not 0 < power < 1 or not 0 < alpha < 1:
        return None

    efecto = abs(delta) / abs(sd)
    n1 = _n_minimo(
        lambda k: _poder_dos_muestras(k, int(np.ceil(k * ratio)), efecto, alpha),
        power)
    if n1 is None:
        return None
    n2 = int(np.ceil(n1 * ratio))

    return {
        "n_group1": n1,
        "n_group2": n2,
        "n_total": n1 + n2,
        "delta": delta,
        "sd": sd,
        "alpha": alpha,
        "power": power,
        "effect_size": delta / sd,
        "ratio": ratio,
    }


def sample_size_proportions(p1, p2, alpha=0.05, power=0.80):
    """Tamano muestral para comparar dos proporciones.

    Args:
        p1: Proporcion esperada grupo 1
        p2: Proporcion esperada grupo 2
        alpha: Nivel de significancia
        power: Poder estadistico

    Returns:
        dict con n por grupo
    """
    if p1 == p2:
        return None
    
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)

    p_bar = (p1 + p2) / 2

    n = (z_alpha * np.sqrt(2 * p_bar * (1 - p_bar)) + z_beta * np.sqrt(p1*(1-p1) + p2*(1-p2)))**2 / (p1 - p2)**2
    n = int(np.ceil(n))

    return {
        "n_per_group": n,
        "n_total": 2 * n,
        "p1": p1,
        "p2": p2,
        "delta": abs(p1 - p2),
        "alpha": alpha,
        "power": power,
    }


def sample_size_correlation(r, alpha=0.05, power=0.80):
    """Tamano muestral para detectar una correlacion.

    Args:
        r: Correlacion esperada
        alpha: Nivel de significancia
        power: Poder estadistico

    Returns:
        dict con n requerido
    """
    if r == 0:
        return None
    
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)

    z_r = np.arctanh(r)
    n = ((z_alpha + z_beta) / z_r) ** 2 + 3
    n = int(np.ceil(n))

    return {
        "n": n,
        "r": r,
        "alpha": alpha,
        "power": power,
    }


def power_analysis(n, delta, sd, alpha=0.05):
    """Calcula el poder para un tamano muestral dado.

    Args:
        n: Tamano muestral
        delta: Diferencia a detectar
        sd: Desviacion estandar
        alpha: Nivel de significancia

    Returns:
        dict con poder calculado
    """
    if sd == 0 or n is None or n < 2:
        return None

    # Misma t no central que usa `sample_size_mean`. Antes las dos funciones
    # usaban z, asi que la ida y vuelta n -> poder -> n cerraba perfecto y
    # confirmaba su propio error: n=2 "tenia" poder 0.81 cuando el real era 0.18.
    efecto = abs(delta) / abs(sd)
    power = _poder_una_muestra(int(n), efecto, alpha)

    return {
        "n": int(n),
        "power": power,
        "delta": delta,
        "sd": sd,
        "alpha": alpha,
        "effect_size": delta / sd,
    }
