"""Contrato de robustez del core frente a datos degenerados.

Una auditoria sobre 12 casos degenerados x 6 funciones encontro 16 salidas con
valores NO FINITOS devueltos en silencio y 2 excepciones no controladas. Un NaN
mudo es peor que un rechazo: el numero llega al informe y se reporta.

El contrato que fija este modulo, tomado de como se comporta MedCalc:

  1. NUNCA lanzar una excepcion por culpa de los datos.
  2. NUNCA devolver un numero no finito sin una nota que lo explique.
  3. Al rechazar, decir POR QUE, con un mensaje accionable.

Si algun dia una funcion vuelve a devolver un NaN mudo, estos tests fallan.
"""
import numpy as np
import pytest

from src.core.agreement import cv_from_duplicates, deming_regression
from src.core.bland_altman import bland_altman_analysis, concordance_correlation
from src.core.guards import finite_pair
from src.core.passing_bablok import passing_bablok
from src.core.regression import linear_regression

FUNCS = [
    ("bland_altman_analysis", bland_altman_analysis),
    ("concordance_correlation", concordance_correlation),
    ("deming_regression", deming_regression),
    ("cv_from_duplicates", cv_from_duplicates),
    ("passing_bablok", passing_bablok),
    ("linear_regression", linear_regression),
]

CASOS = {
    "n=2":         (np.array([1.0, 2.0]), np.array([1.1, 2.2])),
    "n=1":         (np.array([1.0]), np.array([1.1])),
    "n=0":         (np.array([]), np.array([])),
    "constante":   (np.array([5.0] * 10), np.array([5.0] * 10)),
    "x constante": (np.array([5.0] * 10), np.arange(10.0)),
    "con NaN":     (np.array([1, 2, np.nan, 4, 5.0]), np.array([1, 2, 3, np.nan, 5.0])),
    "todo NaN":    (np.full(6, np.nan), np.full(6, np.nan)),
    "con inf":     (np.array([1, 2, np.inf, 4, 5.0]), np.array([1, 2, 3, 4, 5.0])),
    "con ceros":   (np.array([0, 0, 1, 2, 3.0]), np.array([0, 1, 2, 3, 4.0])),
    "negativos":   (np.array([-3, -2, -1, 1, 2.0]), np.array([-3, -1, 0, 1, 3.0])),
    "identicos":   (np.arange(1, 11.0), np.arange(1, 11.0)),
    "normal":      (np.arange(1, 11.0), np.arange(1, 11.0) * 1.1 + 0.3),
}


def _no_finitos(res):
    malos = []
    for k, v in res.items():
        if isinstance(v, (int, float, np.floating, np.integer)):
            if not np.isfinite(float(v)):
                malos.append(k)
        elif isinstance(v, tuple):
            if any(isinstance(x, (int, float, np.floating)) and not np.isfinite(float(x))
                   for x in v):
                malos.append(k)
    return malos


@pytest.mark.parametrize("nombre,fn", FUNCS)
@pytest.mark.parametrize("caso", list(CASOS))
def test_nunca_crashea(nombre, fn, caso):
    """Regla 1: ninguna entrada degenerada puede lanzar excepcion."""
    x, y = CASOS[caso]
    try:
        fn(x, y)
    except Exception as e:                                    # noqa: BLE001
        pytest.fail(f"{nombre} crasheo con '{caso}': {type(e).__name__}: {e}")


@pytest.mark.parametrize("nombre,fn", FUNCS)
@pytest.mark.parametrize("caso", list(CASOS))
def test_nunca_devuelve_no_finito_sin_explicarlo(nombre, fn, caso):
    """Regla 2: si sale un NaN/inf, tiene que venir con nota que lo justifique."""
    x, y = CASOS[caso]
    res = fn(x, y)
    if res is None or not isinstance(res, dict):
        return
    if res.get("error"):
        return                                                # rechazo explicito
    malos = _no_finitos(res)
    if malos:
        notas = res.get("avisos") or ([res["ci_nota"]] if res.get("ci_nota") else [])
        assert notas, (f"{nombre} con '{caso}' devolvio no finito en {malos} "
                       f"sin ninguna nota que lo explique")


@pytest.mark.parametrize("nombre,fn", FUNCS)
@pytest.mark.parametrize("caso", ["n=1", "n=0", "todo NaN"])
def test_rechazo_trae_motivo_accionable(nombre, fn, caso):
    """Regla 3: el rechazo dice por que, no un 'no se pudo calcular'."""
    x, y = CASOS[caso]
    res = fn(x, y)
    assert isinstance(res, dict) and res.get("error"), (
        f"{nombre} con '{caso}' deberia rechazar con motivo")
    motivo = res["error"]
    assert len(motivo) > 25, f"motivo demasiado escueto: {motivo!r}"
    assert any(t in motivo.lower() for t in ("necesitan", "utilizables", "constante",
                                             "numeric", "cero")), motivo


# --------------------------------------------------------------------------
# La guarda en si
# --------------------------------------------------------------------------

def test_guard_descarta_infinitos_no_solo_nan():
    """El core solo miraba isnan; los infinitos se colaban y contaminaban todo."""
    x, y, motivo = finite_pair([1, 2, np.inf, 4, 5], [1, 2, 3, 4, 5], min_n=3)
    assert motivo is None
    assert len(x) == 4 and np.all(np.isfinite(x))


def test_guard_exige_n_despues_de_filtrar():
    x, y, motivo = finite_pair([1, np.nan, np.nan, np.nan], [1, 2, 3, 4], min_n=3)
    assert x is None
    assert "utilizables" in motivo and "descartaron" in motivo


def test_guard_detecta_longitudes_distintas():
    x, y, motivo = finite_pair([1, 2, 3], [1, 2], min_n=2)
    assert x is None and "mismo numero" in motivo


def test_guard_varianza_nula():
    x, y, motivo = finite_pair([5, 5, 5, 5], [1, 2, 3, 4], min_n=3, need_variance="x")
    assert x is None and "constante" in motivo


def test_guard_valores_positivos():
    x, y, motivo = finite_pair([0, 1, 2, 3], [1, 2, 3, 4], min_n=3, positive=True)
    assert x is None and "cero o negativos" in motivo


# --------------------------------------------------------------------------
# Avisos que no son rechazos (se calcula igual, pero se advierte)
# --------------------------------------------------------------------------

def test_passing_bablok_avisa_si_n_es_bajo():
    """MedCalc recomienda n>=30 (Bablok & Passing 1985) / n>=50 (Ludbrook 2010).

    No es motivo para negarse: se calcula y se avisa.
    """
    rng = np.random.default_rng(7)
    x = np.linspace(1, 10, 12)
    y = 1.05 * x + 0.2 + rng.normal(0, 0.1, 12)
    res = passing_bablok(x, y)
    assert "error" not in res
    assert res["avisos"], "deberia avisar que n=12 esta por debajo del recomendado"
    assert "30" in res["avisos"][0]


def test_passing_bablok_no_avisa_con_n_suficiente():
    rng = np.random.default_rng(7)
    x = np.linspace(1, 10, 40)
    y = 1.05 * x + 0.2 + rng.normal(0, 0.1, 40)
    res = passing_bablok(x, y)
    assert not res["avisos"]


def test_cv_duplicados_rechaza_media_cero():
    """El CV es un cociente: con media cero no esta definido."""
    res = cv_from_duplicates([-1, -2, 3, 0], [1, 2, -3, 0])
    assert res.get("error") and "cero" in res["error"]
