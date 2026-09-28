"""CLSI EP15-A3 contra los ejemplos publicados de la norma.

Fuentes: tabla 10 y ejemplos resueltos de EP15-A3 (2014), con las fe de erratas
de CLSI del 22 oct 2015 y del 23 may 2017. Los datos de ferritina (muestra 2,
5 corridas × 5 réplicas) son los del paquete de R `CLSIEP15`, que los toma de
la norma; reproducen MS1 y MS2 de la tabla 10 al último decimal.
"""
import math

import numpy as np
import pytest
from scipy import stats

from src.core.ep15 import (
    componentes, df_intralab, factor_uvl, precision_ep15, verificar, veracidad,
)

# filas = réplicas, columnas = corridas (Run_1 ... Run_5)
FERRITINA = [[140, 140, 140, 141, 139],
             [139, 143, 138, 144, 140],
             [138, 141, 136, 142, 141],
             [138, 143, 141, 143, 138],
             [140, 137, 136, 144, 141]]
CORRIDAS = [[fila[j] for fila in FERRITINA] for j in range(5)]


def test_tabla_10_muestra_2_desde_los_datos():
    r = precision_ep15(CORRIDAS)
    assert (r["n"], r["corridas"], r["n0"]) == (25, 5, 5)
    assert r["media"] == pytest.approx(140.1, abs=0.05)
    assert r["ms_entre"] == pytest.approx(15.86, abs=1e-9)
    assert r["ms_dentro"] == pytest.approx(3.16, abs=1e-9)
    assert r["v_entre"] == pytest.approx(2.54, abs=1e-9)
    assert r["s_r"] == pytest.approx(1.78, abs=0.005)
    assert r["cv_r"] == pytest.approx(1.3, abs=0.05)
    assert r["cv_wl"] == pytest.approx(1.7, abs=0.05)
    # La tabla imprime s_WL = 2,40 (la errata de 2015 solo le agregó el cero),
    # pero con sus propios MS1 y MS2 da √(3,16 + 2,54) = 2,387. Las otras tres
    # columnas cierran con la misma fórmula (test siguiente): es redondeo de la
    # tabla, no otra fórmula.
    assert r["s_wl"] == pytest.approx(math.sqrt(3.16 + 2.54), abs=1e-12)


@pytest.mark.parametrize("ms1, ms2, n0, vb, s_r, s_wl, media_cifra", [
    (4.238, 1.3284, 5, 0.58192, 1.15, 1.38, 0.005),       # muestra 1
    (2.0851, 0.74137, 4.79, 0.28052, 0.86, 1.01, 0.005),  # 1*, una réplica excluida
    (626.56, 113.52, 5, 102.61, 10.7, 14.7, 0.05),        # muestra 3
])
def test_tabla_10_las_otras_columnas(ms1, ms2, n0, vb, s_r, s_wl, media_cifra):
    """Hasta la última cifra que imprime la tabla (media unidad de esa cifra)."""
    c = componentes(ms1, ms2, n0)
    assert c["v_entre"] == pytest.approx(vb, rel=2e-3)
    assert c["s_r"] == pytest.approx(s_r, abs=media_cifra)
    assert c["s_wl"] == pytest.approx(s_wl, abs=media_cifra)


def test_n0_con_una_replica_excluida():
    """Muestra 1* de la tabla 10: N = 24, n0 = 4,79."""
    corridas = [c[:] for c in CORRIDAS]
    corridas[2] = corridas[2][:4]
    r = precision_ep15(corridas)
    assert r["n"] == 24
    assert r["n0"] == pytest.approx(4.79, abs=0.005)


def test_la_anova_coincide_con_scipy():
    rng = np.random.default_rng(2)
    corridas = [rng.normal(100 + rng.normal(0, 2), 3, size=k) for k in (5, 4, 5, 3, 5, 5)]
    r = precision_ep15(corridas)
    f, _ = stats.f_oneway(*corridas)
    assert r["ms_entre"] / r["ms_dentro"] == pytest.approx(f, rel=1e-10)


def test_apendice_b5_factor_uvl():
    """«En un estudio con dos muestras, si df = 20, entonces X² = 34,17.»"""
    from src.core.ep15 import factor_uvl_formula
    f = factor_uvl_formula(20, n_muestras=2)
    assert f * f * 20 == pytest.approx(34.17, abs=0.005)


def test_la_tabla_7_es_la_formula_redondeada():
    """Las 180 celdas transcritas de la tabla 7 (EP15-A3, 2014): si una no
    coincide con la fórmula del ap. B5 a dos decimales, está mal copiada."""
    from src.core.ep15 import TABLA_7, factor_uvl_formula
    assert sorted(TABLA_7) == list(range(5, 35))
    for gl, fila in TABLA_7.items():
        assert len(fila) == 6
        for m, impreso in enumerate(fila, start=1):
            assert round(factor_uvl_formula(gl, m), 2) == impreso, (gl, m)


def test_la_tabla_b4_es_grubbs_al_99_por_ciento():
    """Las 98 filas de la tabla B4 (N = 3 a 100) son la fórmula de Grubbs de dos
    colas con α = 0,01 a tres decimales. Con α = 0,05, como usaba BioStat hasta
    el 28 sep, no coincide ninguna."""
    from src.core.ep15 import TABLA_B4, g_grubbs_formula
    assert sorted(TABLA_B4) == list(range(3, 101))
    for n, g in TABLA_B4.items():
        assert round(g_grubbs_formula(n, 0.01), 3) == g, n
    assert all(round(g_grubbs_formula(n, 0.05), 3) != g for n, g in TABLA_B4.items())


def test_grubbs_del_ejemplo_de_ferritina():
    """§2.3.4.2: N = 25, G = 3,135; límites 140,1 ± 3,135 · 2,30 = 132,9 y 147,3."""
    from src.core.ep15 import _grubbs
    rng = np.random.default_rng(0)
    g = _grubbs(rng.normal(140.1, 2.3, 25))
    assert g["g_critico"] == 3.135 and g["fuente"].startswith("tabla B4")
    assert round(140.1 - 3.135 * 2.30, 1) == 132.9 and round(140.1 + 3.135 * 2.30, 1) == 147.3


def test_un_resultado_entre_el_g_del_95_y_el_del_99_ya_no_es_atipico():
    """Con N = 25, G = 3,0 pasaba el 2,82 del 95 % pero no el 3,135 de la norma."""
    from src.core.ep15 import _grubbs
    base = np.array([-1.0, 1.0] * 12)
    # un valor extremo tal que su G quede en ~3,0
    for extra in np.linspace(3, 8, 2001):
        v = np.r_[base, extra]
        z = abs(extra - v.mean()) / v.std(ddof=1)
        if 2.95 < z < 3.05:
            break
    g = _grubbs(v)
    assert 2.95 < g["g"] < 3.05 and not g["atipico"]
    assert _grubbs(v, alpha=0.05)["atipico"]


def test_las_filas_de_la_tabla_6_son_la_formula_del_apendice_b4():
    from src.core.ep15 import TABLA_6
    for corridas, filas in TABLA_6.items():
        for rho, gl in filas:
            assert df_intralab(rho, corridas, 5, 5 * corridas) == gl, (corridas, rho)


def test_la_tabla_12_del_ejemplo_de_ferritina():
    """Tabla 12 de EP15-A3: 5 corridas × 5 réplicas, 3 muestras. gl_R = 20 → F
    = 1,34; gl_WL de la tabla 6 con la ρ de lo declarado, F de la tabla 7."""
    from decimal import ROUND_HALF_UP, Decimal
    from src.core.ep15 import gl_intralab

    def como_la_norma(x, dec):
        """Redondeo hacia arriba en el 5, como la tabla (1,50 · 23,7 = 35,55 → 35,6;
        el round de Python da 35,5 porque 35,55 no es exacto en binario)."""
        return float(Decimal(str(x)).quantize(Decimal(1).scaleb(-dec), ROUND_HALF_UP))

    declarados = [(0.43, 0.70), (2.0, 3.5), (2.9, 5.1), (6.9, 12.0), (15.8, 23.7)]
    esperado_gl, esperado_f = [8, 7, 7, 7, 9], [1.53, 1.56, 1.56, 1.56, 1.50]
    uvl_r, uvl_wl = [0.58, 2.7, 3.9, 9.2, 21.2], [1.07, 5.5, 8.0, 18.7, 35.6]
    for i, (s_r, s_wl) in enumerate(declarados):
        assert factor_uvl(20, n_muestras=3) == 1.34
        assert como_la_norma(Decimal("1.34") * Decimal(str(s_r)), 2 if s_r < 1 else 1) == uvl_r[i]
        gl, fuente = gl_intralab(round(s_wl / s_r, 2), 5, 5, 5, 25)
        assert gl == esperado_gl[i] and fuente.startswith("tabla 6")
        f = factor_uvl(gl, n_muestras=3)
        assert f == esperado_f[i]
        assert como_la_norma(Decimal(str(f)) * Decimal(str(s_wl)),
                             2 if s_wl < 1.5 else 1) == uvl_wl[i]


@pytest.mark.parametrize("rho, corridas, replicas, esperado", [
    (4.0, 5, 5, 5),        # por encima de la tabla: la fila más cercana (2,74)
    (1.30, 5, 5, 12),      # empate entre 1,32 (12) y 1,28 (13): gana la primera
    (1.0, 7, 5, 34),
])
def test_la_busqueda_en_la_tabla_6(rho, corridas, replicas, esperado):
    from src.core.ep15 import gl_intralab
    assert gl_intralab(rho, corridas, replicas, 5, corridas * 5)[0] == esperado


@pytest.mark.parametrize("corridas, replicas", [(4, 5), (8, 5), (5, 3), (5, 6)])
def test_fuera_de_la_tabla_6_se_usa_la_formula(corridas, replicas):
    from src.core.ep15 import gl_intralab
    n = corridas * replicas
    gl, fuente = gl_intralab(1.6, corridas, replicas, replicas, n)
    assert gl == df_intralab(1.6, corridas, replicas, n) and fuente.startswith("fórmula")


def test_el_factor_sale_de_la_tabla_7():
    """A pedido del usuario: el F es el impreso en la tabla, no la fórmula."""
    assert factor_uvl(20, n_muestras=2) == 1.31
    assert factor_uvl(20.0, n_muestras=1) == 1.25
    assert factor_uvl(5, n_muestras=6) == 1.76
    assert verificar(1.0, 1.0, 20, 2)["fuente"] == "tabla 7 de EP15-A3"


def test_en_el_limite_manda_la_tabla():
    """Con 20 gl y 2 muestras la fórmula da F = 1,3071 y la tabla 1,31: una
    observada de 1,308 × lo declarado se verifica con la tabla y no con la
    fórmula. Quien sigue la norma a mano la da por verificada."""
    from src.core.ep15 import factor_uvl_formula
    assert factor_uvl_formula(20, 2) < 1.308 < 1.31
    assert verificar(1.308, 1.0, 20, n_muestras=2)["verificado"]


@pytest.mark.parametrize("df, muestras", [(4, 1), (35, 2), (60, 1), (20, 7), (20.5, 1)])
def test_fuera_de_la_tabla_7_se_usa_la_formula(df, muestras):
    from src.core.ep15 import factor_uvl_formula
    v = verificar(1.0, 1.0, df, n_muestras=muestras)
    assert v["factor"] == factor_uvl_formula(df, muestras)
    assert v["fuente"].startswith("fórmula")


def test_df_intralab_en_los_extremos():
    """ρ = 1: sin variación entre corridas, s_WL tiene los gl de todo el
    estudio (N − 1). ρ grande: la manda la variación entre corridas (D − 1)."""
    assert df_intralab(1.0, 5, 5, 25) == 24
    assert df_intralab(50.0, 5, 5, 25) == 4


def test_el_uvl_rechaza_un_5_por_ciento_si_la_declaracion_es_cierta():
    """Para eso existe el UVL: que un laboratorio que funciona bien no rechace
    la declaración más del 5 % de las veces (EP15-A3 §2.3.6)."""
    rng = np.random.default_rng(7)
    sigma_r, sigma_b = 2.0, 1.5
    rho = math.sqrt(sigma_r ** 2 + sigma_b ** 2) / sigma_r
    df_wl = df_intralab(rho, 5, 5, 25)
    rech_r = rech_wl = 0
    for _ in range(2000):
        corr = [rng.normal(rng.normal(0, sigma_b), sigma_r, 5) for _ in range(5)]
        r = precision_ep15(corr)
        rech_r += not verificar(r["s_r"], sigma_r, 20)["verificado"]
        rech_wl += not verificar(r["s_wl"], sigma_r * rho, df_wl)["verificado"]
    assert rech_r / 2000 == pytest.approx(0.05, abs=0.015)
    assert rech_wl / 2000 < 0.08


def test_ejemplo_1a_sesgo_contra_grupo_de_pares():
    """Ferritina contra un grupo de pares: media 142,5, DE 4,5, 43 laboratorios,
    tres muestras. Valores corregidos por la errata de 2015: se(x̿) = 0,80,
    τ = 0,86, se_c = 1,06; con gl = 12, m = 2,78 e intervalo 139,6 a 145,4.
    """
    se_rm = 4.5 / math.sqrt(43)
    v = veracidad(140.1, 1.78, 2.40, 5, 5, 142.5, se_rm=se_rm, df_rm=42, n_muestras=3)
    assert v["se_media"] == pytest.approx(0.80, abs=0.005)
    # La norma divide los valores ya redondeados: 0,69/0,80 = 0,86.
    assert se_rm / v["se_media"] == pytest.approx(0.86, abs=0.01)
    assert v["se_c"] == pytest.approx(1.06, abs=0.005)
    # La norma lee gl = 12 en la tabla 15A, en la fila de 50 laboratorios (no hay
    # de 43). Con esos gl, lo publicado:
    m12 = stats.t.ppf(1 - 0.05 / 6, 12)
    assert m12 == pytest.approx(2.78, abs=0.005)
    assert 142.5 - m12 * v["se_c"] == pytest.approx(139.6, abs=0.05)
    assert 142.5 + m12 * v["se_c"] == pytest.approx(145.4, abs=0.05)
    # Satterthwaite con los 43 laboratorios reales da 11,4: el intervalo sale
    # apenas más ancho que el publicado y la conclusión es la misma.
    assert v["df_c"] == 11
    assert v["intervalo"][0] == pytest.approx(139.6, abs=0.1)
    assert v["dentro"] and v["sesgo"] == pytest.approx(-2.4)


def test_ejemplo_3a_sin_incertidumbre_del_valor_asignado():
    """Digoxina, 5 corridas, dos muestras: se(x̿) = √(1/5·[0,04² − (4/5)·0,01²])
    = 0,0174; m = t(0,9875; 4) = 3,50; intervalo 2,00 ± 0,061."""
    v = veracidad(1.97, 0.01, 0.04, 5, 5, 2.00, n_muestras=2)
    assert v["se_media"] == pytest.approx(0.0174, abs=5e-5)
    assert v["m"] == pytest.approx(3.50, abs=0.005)
    assert v["intervalo"][1] - 2.00 == pytest.approx(0.061, abs=5e-4)
    assert v["dentro"]


def test_ejemplo_4_la_media_queda_afuera():
    """7 corridas, dos muestras: se(x̿) = 0,012, m = t(0,9875; 6) = 2,97; la media
    0,94 no está en el intervalo y el sesgo, −0,06, se distingue del azar."""
    v = veracidad(0.94, 0.032, 0.042, 7, 5, 1.00, n_muestras=2)
    assert v["se_media"] == pytest.approx(0.012, abs=5e-4)
    assert v["m"] == pytest.approx(2.97, abs=0.005)
    assert not v["dentro"]
    assert v["sesgo"] == pytest.approx(-0.06)


def test_rechazos_con_motivo():
    assert "al menos 2 corridas" in precision_ep15([[1, 2, 3]])["error"]
    assert "una sola réplica" in precision_ep15([[1], [2], [3]])["error"]


def test_varianza_entre_corridas_negativa_se_toma_cero():
    corr = [[10, 12, 11, 13, 9], [11, 11, 12, 10, 11]]
    r = precision_ep15(corr)
    assert r["v_entre_negativa"] and r["v_entre"] == 0
    assert r["s_wl"] == pytest.approx(r["s_r"])
    assert any("se tomó 0" in a for a in r["avisos"])


def test_grubbs_marca_un_atipico_sin_sacarlo():
    corr = [c[:] for c in CORRIDAS]
    corr[1][2] = 170
    r = precision_ep15(corr)
    assert r["grubbs"]["atipico"] and r["grubbs"]["valor"] == 170
    assert r["n"] == 25
