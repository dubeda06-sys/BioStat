"""Prueba Cusum de linealidad de Passing y Bablok (1983).

MedCalc la informa junto a la recta y el panel no la tenía: la ficha decía «el
programa no corre la prueba Cusum». Los pasos siguen a NCSS (cap. 313) y al
paquete `mcr` de R (`MCResult.calcCUSUM`), que coinciden entre sí.
"""
import numpy as np
import pandas as pd
import pytest
from scipy import stats

from src.core.passing_bablok import cusum_linealidad, passing_bablok
from src.resultado.constructores import passing_bablok as passing_bablok_resultado
from src.resultado.render_html import render_html


def test_ejemplo_calculado_a_mano():
    """Recta y = x, seis puntos: 4 residuos arriba, 2 abajo.

    r = +√(2/4) = 0,7071 arriba y −√(4/2) = −1,4142 abajo. El orden por D es el
    de las filas, así que la suma acumulada es 0,707, −0,707, 0, −1,414,
    −0,707, 0: máximo 1,4142 y H = 1,4142/√(2 + 1) = 0,8165.
    """
    x = np.array([1, 2, 3, 4, 5, 6], dtype=float)
    y = np.array([1.5, 1.8, 3.2, 3.5, 5.4, 6.3])
    r = cusum_linealidad(x, y, pendiente=1.0, intercepto=0.0)
    assert (r["n_pos"], r["n_neg"]) == (4, 2)
    np.testing.assert_allclose(
        r["cusum"], [0.70711, -0.70711, 0.0, -1.41421, -0.70711, 0.0], atol=1e-5)
    assert r["max_cusum"] == pytest.approx(np.sqrt(2))
    assert r["h"] == pytest.approx(np.sqrt(2) / np.sqrt(3))
    assert r["p"] == pytest.approx(stats.kstwobign.sf(np.sqrt(2 / 3)))


def test_la_suma_de_los_puntajes_cierra_en_cero():
    """Los puntajes están elegidos para que la suma total sea cero: la cusum es
    un puente, que es lo que la vuelve comparable con Kolmogorov-Smirnov."""
    rng = np.random.default_rng(3)
    x = rng.uniform(10, 100, 40)
    y = x + rng.normal(0, 3, 40)
    res = passing_bablok(x, y)
    assert res["cusum"]["cusum"][-1] == pytest.approx(0, abs=1e-9)


def test_los_criticos_son_los_publicados():
    """NCSS y Passing y Bablok (1983): 1,36 al 5 % y 1,63 al 1 %."""
    assert stats.kstwobign.isf(0.05) == pytest.approx(1.36, abs=0.005)
    assert stats.kstwobign.isf(0.01) == pytest.approx(1.63, abs=0.005)


def _datos(rng, n, curva):
    v = rng.uniform(10, 100, n)
    x = v + rng.normal(0, 2, n)
    y = v + curva * (v - 55) ** 2 / 55 + rng.normal(0, 2, n)
    return x, y


def test_con_datos_lineales_rechaza_cerca_del_nominal():
    """Tasa de falsos positivos medida, no supuesta. La prueba publicada es algo
    liberal (4 a 9 % en simulaciones de n = 30 a 100); si pasara del 12 %, el
    estadístico estaría mal armado."""
    rng = np.random.default_rng(11)
    rechazos = [passing_bablok(*_datos(rng, 40, 0.0))["cusum"]["p"] < 0.05
                for _ in range(300)]
    assert np.mean(rechazos) < 0.12


def test_detecta_una_curva():
    rng = np.random.default_rng(12)
    rechazos = [passing_bablok(*_datos(rng, 50, 0.3))["cusum"]["p"] < 0.05
                for _ in range(100)]
    assert np.mean(rechazos) > 0.9


def test_pendiente_no_positiva_se_rechaza_con_motivo():
    r = cusum_linealidad([1, 2, 3], [3, 2, 1], pendiente=-1.0, intercepto=4.0)
    assert "no es positiva" in r["error"]


def test_el_informe_lo_muestra_y_la_curva_invalida_la_recta():
    rng = np.random.default_rng(12)
    x, y = _datos(rng, 60, 0.3)
    res = passing_bablok_resultado(pd.DataFrame({"X": x, "Y": y}), "X", "Y")
    paso = next(s for s in res.supuestos if "lineal" in s.pregunta)
    assert paso.respuesta == "Se detectó desvío" and not paso.ok
    assert res.lectura.startswith("La prueba Cusum detectó")
    html = render_html(res)
    assert "Cusum" in html and "no corre la prueba Cusum" not in html


def test_con_datos_lineales_no_cambia_la_lectura():
    rng = np.random.default_rng(5)
    x, y = _datos(rng, 60, 0.0)
    res = passing_bablok_resultado(pd.DataFrame({"X": x, "Y": y}), "X", "Y")
    paso = next(s for s in res.supuestos if "lineal" in s.pregunta)
    # Con esta semilla p = 0,40.
    assert paso.ok and paso.respuesta == "No se detectó desvío"
    assert not res.lectura.startswith("La prueba Cusum")
    assert not any("Cusum" in a for a in res.advertencias)
