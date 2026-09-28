"""Verificación de precisión y estimación del sesgo, CLSI EP15-A3 (2014).

El protocolo de 5 días: cada día una corrida con 5 réplicas de cada material.
De ahí salen la repetibilidad (dentro de la corrida) y la precisión
intralaboratorio (repetibilidad + entre corridas), que se comparan con lo que
declara el fabricante; y, si el material tiene un valor asignado, el sesgo con
su intervalo de verificación.

Con las dos fe de erratas de la norma (22 oct 2015 y 23 may 2017): el ejemplo
de ferritina de la tabla 10 y el ejemplo resuelto 1A traían mal s_R (1,18 en
vez de 1,78) y todo lo que se calculaba con él. `tests/test_ep15.py` reproduce
los valores corregidos.

Nombres de la norma: MS1 = cuadrado medio ENTRE corridas, MS2 = DENTRO.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import stats

CORRIDAS_NORMA = 5      # EP15-A3: 5 días, una corrida por día
REPLICAS_NORMA = 5      # y 5 réplicas por corrida


# EP15-A3, tabla B4 (y su recorte, la tabla 3): factor G de Grubbs con 99 % de
# confianza, por N total de resultados. Hasta el 28 sep BioStat usaba el 95 %
# (G = 2,82 con N = 25 contra el 3,135 de la norma) y marcaba como atípicos
# resultados que la norma no marca. Cada valor es la fórmula de Grubbs de dos
# colas con α = 0,01, redondeada a tres decimales (test_ep15 lo comprueba).
TABLA_B4 = {
    3: 1.155, 4: 1.496, 5: 1.764, 6: 1.973, 7: 2.139, 8: 2.274, 9: 2.387, 10: 2.482,
    11: 2.564, 12: 2.636, 13: 2.699, 14: 2.755, 15: 2.806, 16: 2.852, 17: 2.894, 18: 2.932,
    19: 2.968, 20: 3.001, 21: 3.031, 22: 3.060, 23: 3.087, 24: 3.112, 25: 3.135, 26: 3.158,
    27: 3.179, 28: 3.199, 29: 3.218, 30: 3.236, 31: 3.253, 32: 3.270, 33: 3.286, 34: 3.301,
    35: 3.316, 36: 3.330, 37: 3.343, 38: 3.356, 39: 3.369, 40: 3.381, 41: 3.392, 42: 3.404,
    43: 3.415, 44: 3.425, 45: 3.435, 46: 3.445, 47: 3.455, 48: 3.464, 49: 3.474, 50: 3.482,
    51: 3.491, 52: 3.500, 53: 3.508, 54: 3.516, 55: 3.524, 56: 3.531, 57: 3.539, 58: 3.546,
    59: 3.553, 60: 3.560, 61: 3.567, 62: 3.573, 63: 3.580, 64: 3.586, 65: 3.592, 66: 3.598,
    67: 3.604, 68: 3.610, 69: 3.616, 70: 3.622, 71: 3.627, 72: 3.633, 73: 3.638, 74: 3.643,
    75: 3.648, 76: 3.653, 77: 3.658, 78: 3.663, 79: 3.668, 80: 3.673, 81: 3.678, 82: 3.682,
    83: 3.687, 84: 3.691, 85: 3.695, 86: 3.700, 87: 3.704, 88: 3.708, 89: 3.712, 90: 3.716,
    91: 3.720, 92: 3.724, 93: 3.728, 94: 3.732, 95: 3.736, 96: 3.740, 97: 3.743, 98: 3.747,
    99: 3.750, 100: 3.754,
}


def g_grubbs_formula(n: int, alpha: float = 0.01) -> float:
    """G crítico de Grubbs, dos colas: (n−1)/√n · √(t²/(n−2+t²)), t = t(1−α/2n; n−2)."""
    t = stats.t.ppf(1 - alpha / (2 * n), n - 2)
    return (n - 1) / math.sqrt(n) * math.sqrt(t ** 2 / (n - 2 + t ** 2))


def _grubbs(valores, alpha=0.01):
    """El valor más alejado de la media y si pasa el límite de Grubbs (dos
    colas). G de la tabla B4 de EP15-A3 (99 %) para N de 3 a 100; fuera de
    ella, o con otro α, la fórmula de la que sale la tabla."""
    v = np.asarray(valores, dtype=float)
    n = len(v)
    de = float(np.std(v, ddof=1)) if n > 2 else 0.0
    if n < 3 or de == 0:
        return None
    z = np.abs(v - v.mean()) / de
    i = int(np.argmax(z))
    tabla = alpha == 0.01 and n in TABLA_B4
    g_crit = TABLA_B4[n] if tabla else g_grubbs_formula(n, alpha)
    return {"indice": i, "valor": float(v[i]), "g": float(z[i]), "g_critico": float(g_crit),
            "fuente": "tabla B4 de EP15-A3 (99 %)" if tabla else f"fórmula de Grubbs (α = {alpha:g})",
            "atipico": bool(z[i] > g_crit)}


def componentes(ms1: float, ms2: float, n0: float) -> dict:
    """De los cuadrados medios a los componentes de varianza (EP15-A3, tabla 10).

    V_B = (MS1 − MS2)/n0, y 0 si sale negativa; V_W = MS2;
    s_R = √V_W; s_WL = √(V_W + V_B).
    """
    vb_crudo = (ms1 - ms2) / n0
    vb = max(vb_crudo, 0.0)
    return {"v_entre": vb, "v_entre_negativa": vb_crudo < 0, "v_dentro": ms2,
            "s_r": math.sqrt(ms2), "s_b": math.sqrt(vb), "s_wl": math.sqrt(ms2 + vb)}


def precision_ep15(corridas, alpha_grubbs=0.01) -> dict:
    """ANOVA de un factor (la corrida) y los componentes de varianza.

    `corridas`: una secuencia de arreglos, uno por corrida, con sus réplicas.
    Admite corridas de distinto tamaño (una réplica excluida): n0 corrige el
    desbalance, como en la tabla 10 de la norma (muestra 1*, N = 24, n0 = 4,79).

    Si la varianza entre corridas sale negativa (MS1 < MS2), se toma 0: la
    precisión intralaboratorio queda igual a la repetibilidad. Tomar el valor
    absoluto, como hace alguna implementación, inventa una varianza que los
    datos no muestran.
    """
    limpias = []
    for c in corridas:
        a = np.asarray(c, dtype=float)
        a = a[np.isfinite(a)]
        if len(a):
            limpias.append(a)
    D = len(limpias)
    if D < 2:
        return {"error": f"Hacen falta al menos 2 corridas con datos; hay {D}."}
    n_i = np.array([len(a) for a in limpias])
    N = int(n_i.sum())
    if N - D < 1:
        return {"error": "Cada corrida tiene una sola réplica: sin réplicas no hay "
                         "repetibilidad que estimar."}
    todos = np.concatenate(limpias)
    media = float(todos.mean())
    medias = np.array([a.mean() for a in limpias])

    ss_entre = float(np.sum(n_i * (medias - media) ** 2))
    ss_dentro = float(sum(np.sum((a - a.mean()) ** 2) for a in limpias))
    df_entre, df_dentro = D - 1, N - D
    ms1, ms2 = ss_entre / df_entre, ss_dentro / df_dentro
    n0 = (N - float(np.sum(n_i ** 2)) / N) / df_entre

    comp = componentes(ms1, ms2, n0)
    s_r, s_b, s_wl = comp["s_r"], comp["s_b"], comp["s_wl"]
    cv = (lambda s: 100 * s / media) if media != 0 else (lambda s: None)

    avisos = []
    if D < CORRIDAS_NORMA or n_i.min() < REPLICAS_NORMA:
        avisos.append(f"El diseño de EP15-A3 es de {CORRIDAS_NORMA} corridas con "
                      f"{REPLICAS_NORMA} réplicas cada una; acá hay {D} corridas con "
                      f"{n_i.min()} a {n_i.max()} réplicas. Con menos datos los "
                      f"estimadores son más inciertos y el límite de verificación, más alto.")
    if comp["v_entre_negativa"]:
        avisos.append("La variación entre corridas salió menor que la esperable por la "
                      "repetibilidad sola (MS entre < MS dentro): se tomó 0 como varianza "
                      "entre corridas.")

    return {
        "n": N, "corridas": D, "replicas": n_i.tolist(), "n0": n0,
        "media": media, "medias_corrida": medias.tolist(),
        "ss_entre": ss_entre, "ss_dentro": ss_dentro,
        "df_entre": df_entre, "df_dentro": df_dentro,
        "ms_entre": ms1, "ms_dentro": ms2,
        "v_entre": comp["v_entre"], "v_entre_negativa": comp["v_entre_negativa"],
        "v_dentro": comp["v_dentro"],
        "s_r": s_r, "s_b": s_b, "s_wl": s_wl,
        "cv_r": cv(s_r), "cv_b": cv(s_b), "cv_wl": cv(s_wl),
        "grubbs": _grubbs(todos, alpha_grubbs),
        "valores": [a.tolist() for a in limpias],
        "avisos": avisos,
    }


def df_intralab(rho: float, corridas: int, n0: float, n: int) -> float:
    """Grados de libertad de s_WL, de la declaración del fabricante (EP15-A3, ap. B).

    Satterthwaite sobre los cuadrados medios que se ESPERAN si la declaración es
    cierta, con ρ = σ_WL/σ_R declarados: así el límite de verificación no
    depende del ruido del propio estudio. Redondeado al entero, como las tablas
    de la norma. Con ρ = 1 (sin variación entre corridas) da N − 1; con ρ
    grande tiende a D − 1.
    """
    vw = 1.0
    vb = max(rho ** 2 - 1.0, 0.0)
    ms1, ms2 = vw + n0 * vb, vw
    a1, a2 = 1 / n0, (n0 - 1) / n0
    num = (a1 * ms1 + a2 * ms2) ** 2
    den = (a1 * ms1) ** 2 / (corridas - 1) + (a2 * ms2) ** 2 / (n - corridas)
    return float(round(num / den))


# EP15-A3, tabla 6: gl de s_WL según la ρ = σWL/σR declarada, para 5, 6 y 7
# corridas con 5 réplicas. La norma manda buscar la fila con la ρ más cercana
# (§2.3.6.2 y la tabla 12 del ejemplo de ferritina); en cada ρ impresa,
# `df_intralab` da exactamente el gl de la tabla, pero entre filas la búsqueda
# y el redondeo de la fórmula difieren en un gl en el 6 al 15 % de los casos.
TABLA_6 = {
    5: ((2.74, 5), (2.06, 6), (1.78, 7), (1.62, 8), (1.51, 9), (1.43, 10), (1.37, 11),
        (1.32, 12), (1.28, 13), (1.24, 14), (1.21, 15), (1.19, 16), (1.16, 17), (1.14, 18),
        (1.12, 19), (1.10, 20), (1.08, 21), (1.05, 22), (1.03, 23), (1.00, 24)),
    6: ((3.02, 6), (2.25, 7), (1.93, 8), (1.74, 9), (1.62, 10), (1.52, 11), (1.46, 12),
        (1.40, 13), (1.35, 14), (1.32, 15), (1.28, 16), (1.25, 17), (1.23, 18), (1.20, 19),
        (1.18, 20), (1.16, 21), (1.14, 22), (1.12, 23), (1.11, 24), (1.09, 25), (1.07, 26),
        (1.05, 27), (1.03, 28), (1.00, 29)),
    7: ((3.27, 7), (2.42, 8), (2.06, 9), (1.85, 10), (1.71, 11), (1.61, 12), (1.54, 13),
        (1.48, 14), (1.42, 15), (1.38, 16), (1.35, 17), (1.31, 18), (1.29, 19), (1.26, 20),
        (1.24, 21), (1.22, 22), (1.20, 23), (1.18, 24), (1.16, 25), (1.14, 26), (1.13, 27),
        (1.11, 28), (1.10, 29), (1.08, 30), (1.07, 31), (1.05, 32), (1.03, 33), (1.00, 34)),
}


def gl_intralab(rho: float, corridas: int, replicas: int, n0: float, n: int):
    """(gl de s_WL, de dónde salen). De la tabla 6 si el diseño es el de la
    tabla (5 a 7 corridas de 5 réplicas; una réplica perdida no cambia el
    diseño): la fila con la ρ más cercana, recorriendo desde arriba como dice
    la norma (en un empate gana la primera, la de ρ mayor). Si no, la fórmula
    del apéndice B4 con n0 y N reales."""
    filas = TABLA_6.get(corridas)
    if filas is not None and replicas == 5:
        return float(min(filas, key=lambda f: abs(f[0] - rho))[1]), "tabla 6 de EP15-A3"
    return df_intralab(rho, corridas, n0, n), "fórmula del ap. B4 (diseño fuera de la tabla 6)"


# CLSI EP15-A3 (2014), tabla 7: factor F del límite superior de verificación
# (UVL = F · σ declarada), por grados de libertad (filas, 5 a 34) y número de
# muestras (columnas, 1 a 6), α = 0,05. Cada celda es la fórmula del ap. B5
# redondeada a dos decimales (test_ep15 lo comprueba celda por celda). Se usa
# el valor impreso, no la fórmula, a pedido del usuario (experto en EP15, 27
# sep): el UVL tiene que ser el mismo que calcula a mano quien sigue la norma,
# y en un caso al límite el tercer decimal de la fórmula podía dar vuelta el
# veredicto.
TABLA_7 = {
    5: (1.49, 1.60, 1.66, 1.71, 1.74, 1.76),
    6: (1.45, 1.55, 1.61, 1.65, 1.67, 1.70),
    7: (1.42, 1.51, 1.56, 1.60, 1.62, 1.65),
    8: (1.39, 1.48, 1.53, 1.56, 1.58, 1.60),
    9: (1.37, 1.45, 1.50, 1.53, 1.55, 1.57),
    10: (1.35, 1.43, 1.47, 1.50, 1.52, 1.54),
    11: (1.34, 1.41, 1.45, 1.48, 1.50, 1.52),
    12: (1.32, 1.39, 1.43, 1.46, 1.48, 1.49),
    13: (1.31, 1.38, 1.42, 1.44, 1.46, 1.47),
    14: (1.30, 1.37, 1.40, 1.42, 1.44, 1.46),
    15: (1.29, 1.35, 1.39, 1.41, 1.43, 1.44),
    16: (1.28, 1.34, 1.38, 1.40, 1.41, 1.43),
    17: (1.27, 1.33, 1.36, 1.39, 1.40, 1.41),
    18: (1.27, 1.32, 1.35, 1.37, 1.39, 1.40),
    19: (1.26, 1.31, 1.34, 1.36, 1.38, 1.39),
    20: (1.25, 1.31, 1.34, 1.36, 1.37, 1.38),
    21: (1.25, 1.30, 1.33, 1.35, 1.36, 1.37),
    22: (1.24, 1.29, 1.32, 1.34, 1.35, 1.36),
    23: (1.24, 1.29, 1.31, 1.33, 1.35, 1.36),
    24: (1.23, 1.28, 1.31, 1.32, 1.34, 1.35),
    25: (1.23, 1.28, 1.30, 1.32, 1.33, 1.34),
    26: (1.22, 1.27, 1.30, 1.31, 1.32, 1.34),
    27: (1.22, 1.26, 1.29, 1.31, 1.32, 1.33),
    28: (1.22, 1.26, 1.28, 1.30, 1.31, 1.32),
    29: (1.21, 1.26, 1.28, 1.30, 1.31, 1.32),
    30: (1.21, 1.25, 1.27, 1.29, 1.30, 1.31),
    31: (1.20, 1.25, 1.27, 1.29, 1.30, 1.31),
    32: (1.20, 1.24, 1.27, 1.28, 1.29, 1.30),
    33: (1.20, 1.24, 1.26, 1.28, 1.29, 1.30),
    34: (1.20, 1.24, 1.26, 1.27, 1.28, 1.29),
}


def factor_uvl_formula(df: float, n_muestras: int = 1, alpha: float = 0.05) -> float:
    """F = √(χ²(1 − α/nMuestras; df) / df)  (EP15-A3, ap. B5).

    Ejemplo de la norma: dos muestras, df = 20 → χ² = 34,17.
    """
    return math.sqrt(stats.chi2.ppf(1 - alpha / n_muestras, df) / df)


def _celda_tabla_7(df: float, n_muestras: int, alpha: float):
    """El F impreso en la tabla 7, o None si el caso no está en la tabla."""
    if alpha != 0.05 or float(df) != int(df):
        return None
    fila = TABLA_7.get(int(df))
    if fila is None or not 1 <= n_muestras <= len(fila):
        return None
    return fila[n_muestras - 1]


def factor_uvl(df: float, n_muestras: int = 1, alpha: float = 0.05) -> float:
    """El F del UVL: el de la tabla 7 de EP15-A3 si gl y muestras están en ella
    (gl 5 a 34, 1 a 6 muestras, α = 0,05); fuera de la tabla, la fórmula del
    ap. B5, de la que la tabla sale."""
    celda = _celda_tabla_7(df, n_muestras, alpha)
    return celda if celda is not None else factor_uvl_formula(df, n_muestras, alpha)


def verificar(s_obs: float, declarado: float, df: float, n_muestras: int = 1,
              alpha: float = 0.05) -> dict:
    """¿La imprecisión observada es compatible con la declarada? (EP15-A3 §2.3.6)

    Si no la supera, está verificada sin más. Si la supera, todavía puede ser
    azar: se compara con el límite superior de verificación, UVL = F·declarado,
    el percentil 95 de lo que daría un estudio de este tamaño si la declaración
    fuera cierta. `fuente` dice de dónde salió F: la tabla 7 o, fuera de ella,
    la fórmula.
    """
    tabla = _celda_tabla_7(df, n_muestras, alpha) is not None
    f = factor_uvl(df, n_muestras, alpha)
    uvl = f * declarado
    return {"declarado": declarado, "df": df, "factor": f, "uvl": uvl,
            "fuente": "tabla 7 de EP15-A3" if tabla else "fórmula del ap. B5 (fuera de la tabla 7)",
            "n_muestras": n_muestras,
            "debajo": s_obs <= declarado, "verificado": s_obs <= uvl}


def veracidad(media: float, s_r: float, s_wl: float, corridas: int, n_rep: float,
              valor_asignado: float, se_rm: float = 0.0, df_rm: float = math.inf,
              n_muestras: int = 1, alpha: float = 0.05) -> dict:
    """Sesgo contra un valor asignado y su intervalo de verificación (EP15-A3 §3).

    se(x̿) = √((s_WL² − ((n−1)/n)·s_R²) / corridas), con corridas − 1 gl;
    se_c = √(se_RM² + se(x̿)²), gl combinados por Satterthwaite y redondeados
    como en las tablas 15A-C; m = t(1 − α/(2·nMuestras); gl);
    intervalo = VA ± m·se_c. La media observada adentro: el sesgo no se
    distingue del azar.

    `se_rm`: incertidumbre estándar del valor asignado. 0 si no se conoce
    (escenarios D y E de la norma); con un grupo de pares, DE/√(laboratorios)
    y `df_rm` = laboratorios − 1.
    """
    var_x = (s_wl ** 2 - ((n_rep - 1) / n_rep) * s_r ** 2) / corridas
    se_x = math.sqrt(max(var_x, 0.0))
    df_x = corridas - 1
    se_c = math.sqrt(se_rm ** 2 + se_x ** 2)
    den = se_x ** 4 / df_x + (se_rm ** 4 / df_rm if math.isfinite(df_rm) else 0.0)
    df_c = float(round(se_c ** 4 / den)) if den > 0 else float(df_x)
    df_c = max(df_c, 1.0)
    m = float(stats.t.ppf(1 - alpha / (2 * n_muestras), df_c))
    medio = m * se_c
    sesgo = media - valor_asignado
    return {
        "valor_asignado": valor_asignado, "media": media,
        "sesgo": sesgo,
        "sesgo_pct": 100 * sesgo / valor_asignado if valor_asignado else None,
        "se_media": se_x, "df_media": df_x, "se_rm": se_rm, "se_c": se_c,
        "df_c": df_c, "m": m,
        "intervalo": (valor_asignado - medio, valor_asignado + medio),
        "dentro": abs(sesgo) <= medio,
    }
