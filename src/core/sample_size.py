"""Calculo de tamano muestral y poder estadistico."""
import numpy as np
from scipy import stats


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
    
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)

    n = ((z_alpha + z_beta) * sd / delta) ** 2
    n = int(np.ceil(n))

    return {
        "n_per_group": n,
        "n_total": n,
        "delta": delta,
        "sd": sd,
        "alpha": alpha,
        "power": power,
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
    if delta == 0 or sd == 0:
        return None
    
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)

    n1 = ((z_alpha + z_beta) * sd / delta) ** 2 * (1 + 1/ratio)
    n1 = int(np.ceil(n1))
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
    if sd == 0:
        return None
    
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    ncp = delta * np.sqrt(n) / sd
    power = 1 - stats.norm.cdf(z_alpha - ncp) + stats.norm.cdf(-z_alpha - ncp)

    return {
        "n": n,
        "power": power,
        "delta": delta,
        "sd": sd,
        "effect_size": delta / sd,
    }
