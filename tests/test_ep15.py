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
