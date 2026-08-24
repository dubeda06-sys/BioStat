"""Infinitos y datos constantes en toda la superficie de calculo.

Dos clases de defecto, encontradas barriendo 3.990 llamadas contra entradas
hostiles sobre las ~100 funciones publicas de src/core:

1. **El filtro dejaba pasar los infinitos.** El core limpiaba con
   `~np.isnan(x)`, que descarta NaN pero NO +-inf. Un inf entra solo en datos
   de laboratorio: un `#¡DIV/0!` de Excel, un log(0), un codigo de desborde del
   analizador. `ttest_ind` devolvia t, p, media y sd en NaN, en silencio.
   `guards.py` ya usaba `isfinite` y hasta lo explicaba en un comentario, pero
   nunca se habia propagado: 44 sitios en 13 archivos seguian con `isnan`.

2. **Datos constantes.** Todo lo que divide por la dispersion daba NaN sin
   decir por que. Pasa de verdad: un analizador trabado, un nivel de QC sin
   variacion.

El criterio es el que fija `guards.py`: puede RECHAZAR, no puede REVENTAR, y
nunca devolver un numero no finito sin explicarlo.
"""
import inspect
import importlib
import warnings

import numpy as np
import pytest

MODULOS = ["statistics", "outliers", "reference", "bootstrap", "bland_altman",
           "passing_bablok", "agreement", "regression", "roc",
           "diagnostic_tests", "sample_size", "survival", "cox_regression",
           "meta_analysis", "cmh", "ancova", "repeated_measures",
           "two_way_anova", "serial_measurements", "validation", "plots"]

CTE = np.full(12, 5.0)
OTRO_CTE = np.full(12, 7.0)


def _no_finitos(res, ignorar=()):
    """Claves escalares no finitas que el resultado no explica."""
    if not isinstance(res, dict) or "error" in res:
        return []
    if res.get("avisos") or res.get("aviso") or res.get("ci_nota") or res.get("nota"):
        return []
    malos = []
    for k, v in res.items():
        if k in ignorar or not isinstance(v, (int, float, np.floating)):
            continue
        if isinstance(v, bool):
            continue
        if not np.isfinite(v):
            malos.append(k)
    return malos


# ---------------- Ya no queda ningun filtro con isnan ----------------

def test_ningun_filtro_de_datos_usa_isnan():
    """`isnan` deja pasar +-inf. Un solo sitio olvidado reintroduce la clase
    entera de defecto, asi que se verifica sobre el codigo fuente."""
    import pathlib
    raiz = pathlib.Path(__file__).resolve().parent.parent / "src"
    culpables = []
    for archivo in list(raiz.glob("core/*.py")) + list(raiz.glob("analysis/*.py")):
        if archivo.name == "guards.py":
            continue
        for i, linea in enumerate(archivo.read_text(encoding="utf-8").splitlines(), 1):
            if "isnan" in linea and not linea.strip().startswith("#"):
                culpables.append(f"{archivo.name}:{i}: {linea.strip()}")
    assert not culpables, "filtros con isnan:\n" + "\n".join(culpables)


# ---------------- Los infinitos no se cuelan ----------------

CON_INF = np.array([1.0, 2.0, np.inf, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
LIMPIO = np.array([1.0, 2.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])


def test_un_infinito_se_descarta_como_un_nan():
    """El resultado con inf tiene que ser igual al del mismo dato sin ese punto."""
    from src.core.statistics import descriptive_stats, ttest_1sample, pearson_r
    assert descriptive_stats(CON_INF)["mean"] == pytest.approx(
        descriptive_stats(LIMPIO)["mean"])
    assert ttest_1sample(CON_INF, 5.0)["t"] == pytest.approx(
        ttest_1sample(LIMPIO, 5.0)["t"])
    x = np.arange(10.0)
    r_inf = pearson_r(CON_INF, x)
    r_lim = pearson_r(LIMPIO, np.delete(x, 2))
    assert r_inf["r"] == pytest.approx(r_lim["r"])


def test_los_validadores_rechazan_los_infinitos():
    """Un validador que valida NaN pero no inf da un falso 'datos correctos'."""
    from src.core.validation import validate_numeric_data
    ok, arr, _ = validate_numeric_data([1.0, 2.0, np.inf, 4.0])
    assert ok and np.all(np.isfinite(arr))
    assert len(arr) == 3


@pytest.mark.parametrize("valor", [np.inf, -np.inf, np.nan])
def test_ninguna_funcion_devuelve_no_finito_por_un_valor_hostil(valor):
    """Barrido: cada funcion de una serie recibe datos con un valor hostil."""
    datos = np.array([10.0, 12.0, 11.0, valor, 13.0, 9.0, 14.0, 10.5, 11.5, 12.5])
    fallos = []
    for mod_nombre in MODULOS:
        mod = importlib.import_module(f"src.core.{mod_nombre}")
        for fn_nombre, fn in inspect.getmembers(mod, inspect.isfunction):
            if fn_nombre.startswith("_") or fn.__module__ != mod.__name__:
                continue
            firma = inspect.signature(fn)
            obligatorios = [p for p in firma.parameters.values()
                            if p.default is inspect.Parameter.empty
                            and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)]
            if len(obligatorios) != 1 or obligatorios[0].name not in ("data", "x"):
                continue
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    res = fn(datos)
                except (ValueError, TypeError):
                    continue
                except Exception as e:
                    fallos.append(f"{mod_nombre}.{fn_nombre}: {type(e).__name__}")
                    continue
            malos = _no_finitos(res)
            if malos:
                fallos.append(f"{mod_nombre}.{fn_nombre}: no finito en {malos}")
    assert not fallos, "\n".join(fallos)


# ---------------- Datos constantes ----------------

@pytest.mark.parametrize("nombre", ["skewness_test", "kurtosis_test",
                                    "ttest_1sample", "pearson_r",
                                    "spearman_rho", "f_test_variances"])
def test_los_datos_constantes_se_rechazan_con_motivo(nombre):
    """Devolver NaN sin avisar es peor que rechazar: el numero llega al informe
    y se reporta. Es el criterio que fija guards.py."""
    import src.core.statistics as st
    fn = getattr(st, nombre)
    firma = inspect.signature(fn)
    n_series = sum(1 for p in firma.parameters.values()
                   if p.default is inspect.Parameter.empty)
    res = fn(CTE, OTRO_CTE) if n_series == 2 else fn(CTE)
    assert isinstance(res, dict) and "error" in res, res
    assert len(res["error"]) > 25, "el motivo tiene que ser accionable"


def test_los_descriptivos_de_datos_constantes_conservan_lo_que_si_vale():
    """La media, la mediana y los extremos de datos constantes son correctos.
    Rechazar el bloque entero perderia informacion util; lo indefinido es solo
    lo que divide por la dispersion."""
    from src.core.statistics import descriptive_stats
    r = descriptive_stats(CTE)
    assert r["mean"] == 5.0 and r["median"] == 5.0 and r["std"] == 0.0
    assert r["min"] == 5.0 and r["max"] == 5.0
    assert any("iguales" in a for a in r["avisos"])


def test_ttest_ind_con_los_dos_grupos_constantes():
    from src.core.statistics import ttest_ind
    assert "error" in ttest_ind(CTE, OTRO_CTE)


# ---------------- Nada revienta ----------------

HOSTILES = {
    "vacio": np.array([]),
    "un dato": np.array([5.0]),
    "dos datos": np.array([5.0, 7.0]),
    "constante": CTE,
    "todo NaN": np.full(6, np.nan),
    "todo inf": np.full(6, np.inf),
    "gigante": np.array([1e300, 2e300, 3e300, 1e300, 2e300, 3e300]),
    "diminuto": np.array([1e-300, 2e-300, 3e-300, 1e-300, 2e-300, 3e-300]),
    "negativos": np.array([-5.0, -3.0, -8.0, -1.0, -9.0, -2.0]),
}

REVIENTAN = (IndexError, ZeroDivisionError, KeyError, StopIteration,
             np.linalg.LinAlgError, AttributeError, UnboundLocalError,
             RecursionError)


@pytest.mark.parametrize("escenario", list(HOSTILES))
def test_ninguna_funcion_de_una_serie_revienta(escenario):
    datos = HOSTILES[escenario]
    fallos = []
    for mod_nombre in MODULOS:
        mod = importlib.import_module(f"src.core.{mod_nombre}")
        for fn_nombre, fn in inspect.getmembers(mod, inspect.isfunction):
            if fn_nombre.startswith("_") or fn.__module__ != mod.__name__:
                continue
            obligatorios = [p for p in inspect.signature(fn).parameters.values()
                            if p.default is inspect.Parameter.empty
                            and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)]
            if len(obligatorios) != 1 or obligatorios[0].name not in ("data", "x"):
                continue
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    fn(datos)
                except ValueError:
                    pass
                except REVIENTAN as e:
                    fallos.append(f"{mod_nombre}.{fn_nombre}: "
                                  f"{type(e).__name__}: {str(e)[:60]}")
                except TypeError:
                    pass
    assert not fallos, f"con datos '{escenario}':\n" + "\n".join(fallos)
