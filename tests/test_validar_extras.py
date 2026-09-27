"""El asistente B, dos criterios más (27 sep).

1. **Error total contra el TEa** (Westgard, Carey y Wold 1974): en cada nivel,
   TE = |sesgo| + 1,65·s_WL, con s_WL de EP15 llevada al nivel con CV
   constante (TEa en %) o DE constante (en unidades). Misma lógica de
   equivalencia que el sesgo: con el extremo del IC del sesgo más lejos de
   cero cumple; con el más cerca ya no cumple; si no, no concluyente.
2. **El sesgo de EP15 contra el valor asignado del material**, dentro del
   asistente: fuera del intervalo de verificación se juzga con el sesgo
   permitido (EP15-A3 §3.6). Los números son los del constructor de «Precisión
   EP15», no una copia.
"""
import numpy as np
import pytest

from src.core.ep09 import CUMPLE, NO_CONCLUYENTE, NO_CUMPLE
from src.resultado.constructores import precision_ep15, validar_metodo
from tests.test_validar_metodo import NIVELES, _hoja, _hoja_con_corridas, _paso

DIAS = [f"Día {j}" for j in range(1, 6)]


def _validar(**opciones):
    base = {"niveles": NIVELES, "corridas": DIAS}
    base.update(opciones)
    return validar_metodo(_hoja_con_corridas(), "Viejo", "Nuevo", base)


# ---------------- Error total ----------------

def test_error_total_es_sesgo_mas_1_65_s_wl_en_cada_nivel():
    res = _validar(tea=20)
    cv_wl = precision_ep15(_hoja_con_corridas(), DIAS).crudo["ep15"]["cv_wl"]
    for t, f in zip(res.crudo["error_total"]["niveles"], res.crudo["niveles"]):
        s = cv_wl * f["nivel"] / 100
        assert t["s"] == pytest.approx(s)
        assert t["te"] == pytest.approx(abs(f["sesgo"]) + 1.65 * s)
        lo, hi = f["ic"]
        lejos = max(abs(lo), abs(hi)) + 1.65 * s
        cerca = (0 if lo <= 0 <= hi else min(abs(lo), abs(hi))) + 1.65 * s
        assert t["te_rango"] == pytest.approx((cerca, lejos))
        assert t["tea"] == pytest.approx(20 * f["nivel"] / 100)


@pytest.mark.parametrize("tea, esperado", [
    (20, CUMPLE), (4.5, NO_CONCLUYENTE), (2, NO_CUMPLE),
])
def test_el_tea_solo_alcanza_para_un_veredicto(tea, esperado):
    res = _validar(tea=tea)
    assert res.crudo["veredicto"] == esperado
    assert _paso(res, "Contra qué").respuesta == "Error total (TEa)"
    assert _paso(res, "error total queda dentro").ok is (esperado == CUMPLE)
    if esperado == CUMPLE:
        assert "queda dentro del TEa" in res.lectura


def test_en_unidades_la_imprecision_es_la_misma_en_todos_los_niveles():
    res = _validar(tea=6, escala_permitido="unidades")
    s_wl = precision_ep15(_hoja_con_corridas(), DIAS).crudo["ep15"]["s_wl"]
    assert {round(t["s"], 12) for t in res.crudo["error_total"]["niveles"]} == {round(s_wl, 12)}
    assert all(t["tea"] == 6 for t in res.crudo["error_total"]["niveles"])


def test_sin_corridas_el_error_total_no_se_puede_evaluar_y_lo_dice():
    res = validar_metodo(_hoja(), "Viejo", "Nuevo", {"tea": 20, "niveles": NIVELES})
    assert res.crudo["veredicto"] == NO_CONCLUYENTE
    assert "tildá las corridas de EP15" in res.lectura
    assert _paso(res, "error total queda dentro").respuesta == "No evaluable"


def test_sesgo_y_tea_juntos_deciden_por_el_peor():
    # el sesgo solo cumple con 5 %; el error total con TEa 3,5 % no
    res = _validar(sesgo_permitido=5.0, tea=3.5)
    assert res.crudo["veredicto"] == NO_CUMPLE
    assert any("error total" in m for m in res.crudo["motivos"])
    assert not any("sesgo en" in m and "supera" in m for m in res.crudo["motivos"])


def test_tea_no_positivo_se_rechaza():
    res = validar_metodo(_hoja(), "Viejo", "Nuevo", {"tea": 0})
    assert not res.ok and "TEa" in res.error


# ---------------- Sesgo contra el valor asignado ----------------

def _media_corridas():
    return precision_ep15(_hoja_con_corridas(), DIAS).crudo["ep15"]["media"]


def test_la_veracidad_es_la_del_constructor_de_ep15():
    opciones = {"valor_asignado": 138.0, "incertidumbre": "u", "u": 0.5}
    res = _validar(sesgo_permitido=5.0, **opciones)
    solo = precision_ep15(_hoja_con_corridas(), DIAS, opciones).crudo["veracidad"]
    v = res.crudo["veracidad"]
    assert v["sesgo"] == pytest.approx(solo["sesgo"])
    assert v["intervalo"] == pytest.approx(solo["intervalo"])
    assert v["dentro"] == solo["dentro"]


def test_valor_asignado_igual_a_la_media_cumple():
    res = _validar(sesgo_permitido=5.0, valor_asignado=_media_corridas())
    assert res.crudo["veracidad"]["dentro"] is True
    assert res.crudo["veredicto"] == CUMPLE
    assert "no se distingue del azar" in res.lectura


@pytest.mark.parametrize("permitido, esperado", [(5.0, NO_CUMPLE), (10.0, CUMPLE)])
def test_sesgo_real_se_juzga_con_el_permitido(permitido, esperado):
    """Media 140,1 contra un valor asignado de 130: 7,8 % de sesgo, real. Con 5 %
    permitido no cumple; con 10 %, es real pero aceptable (EP15-A3 §3.6)."""
    res = _validar(sesgo_permitido=permitido, valor_asignado=130.0)
    assert res.crudo["veracidad"]["dentro"] is False
    assert res.crudo["veredicto"] == esperado
    paso = _paso(res, "valor asignado del material es aceptable")
    assert paso.ok is (esperado == CUMPLE)
    if esperado == CUMPLE:
        assert "real pero queda dentro del permitido" in res.lectura


def test_sesgo_real_sin_permitido_no_se_puede_juzgar():
    res = _validar(tea=20, valor_asignado=130.0)
    assert res.crudo["veredicto"] == NO_CONCLUYENTE
    assert any("valor asignado" in m for m in res.crudo["motivos"])


def test_el_informe_muestra_el_error_total_y_la_veracidad():
    from tests.test_validar_metodo import _texto
    texto = _texto(_validar(sesgo_permitido=5.0, tea=20, valor_asignado=_media_corridas()))
    assert "Error total en Viejo = 50" in texto
    assert "Sesgo contra el valor asignado (EP15)" in texto
    assert "Westgard" in texto
    assert np.isfinite(_media_corridas())
