"""La tabla que reemplazó al mixin del panel (paso 5, 27 sep).

`src/ui/entradas.py` no importa Qt: de lo elegido en el diálogo a cada
constructor. Estos tests cierran que la tabla cubra los 78 análisis y que un
parámetro mal escrito salga como rechazo, no como excepción ni como HTML.
"""
import numpy as np
import pandas as pd
import pytest

from src.resultado.constructores import CONSTRUCTORES
from src.ui import entradas
from src.ui.help_text import ANALYSIS_HELP


def test_la_tabla_cubre_todos_los_analisis_del_combo():
    assert set(entradas.ENTRADAS) == set(ANALYSIS_HELP)


def test_cada_entrada_apunta_a_un_constructor_registrado():
    ids = {analisis for analisis, _ in entradas.ENTRADAS.values()}
    assert ids <= set(CONSTRUCTORES)
    assert set(CONSTRUCTORES) <= ids, "hay constructores sin entrada en el panel"


def test_no_importa_qt():
    fuente = open(entradas.__file__, encoding="utf-8").read()
    assert "PyQt6" not in fuente


def _eleccion(**kw):
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"A": rng.normal(10, 1, 30), "B": rng.normal(10, 1, 30)})
    return entradas.Eleccion(df, **kw)


def test_un_parametro_mal_escrito_es_un_rechazo_con_su_nombre():
    res = entradas.correr("t-test 1 muestra", _eleccion(c1="A", parametros={"mu": "diez"}))
    assert not res.ok
    assert "tiene que ser un número" in res.error and "diez" in res.error


def test_un_parametro_fuera_de_rango_es_un_rechazo():
    res = entradas.correr("Diagnostic test", _eleccion(c1="A", c2="B",
                                                       parametros={"prevalencia": "150"}))
    assert not res.ok and "fuera de rango" in res.error


def test_falta_la_variable_3_se_dice_cual():
    res = entradas.correr("ANCOVA", _eleccion(c1="A", c2="B"))
    assert not res.ok and "covariable" in res.error


def test_un_error_de_calculo_no_se_disfraza_de_rechazo(monkeypatch):
    """Solo `ParametroInvalido` se convierte en rechazo: un ValueError de un
    constructor es un defecto y tiene que verse."""
    def roto(e):
        raise ValueError("defecto")
    monkeypatch.setitem(entradas.ENTRADAS, "Kappa", ("kappa", roto))
    with pytest.raises(ValueError, match="defecto"):
        entradas.correr("Kappa", _eleccion(c1="A", c2="B"))


@pytest.mark.parametrize("nombre", sorted(ANALYSIS_HELP))
def test_todos_corren_sin_dialogo_y_devuelven_un_resultado(nombre):
    """Con una hoja cualquiera, cada análisis devuelve un Resultado (ok o
    rechazo con motivo): ninguno revienta ni devuelve texto suelto."""
    from src.resultado.modelo import Resultado
    rng = np.random.default_rng(1)
    n = 40
    df = pd.DataFrame({"A": rng.normal(50, 5, n), "B": rng.normal(52, 5, n),
                       "C": rng.integers(0, 2, n).astype(float),
                       "D": rng.normal(1, 0.2, n)})
    res = entradas.correr(nombre, entradas.Eleccion(df, "A", "B", "C"))
    assert isinstance(res, Resultado)
    assert res.ok or res.error
