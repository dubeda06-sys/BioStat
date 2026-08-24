"""ROC, pruebas diagnosticas y tamano muestral contra sklearn y statsmodels.

Tres defectos aparecieron aca, y ninguno se veia mirando un resultado suelto:

1. El AUC subestimaba cuando el score tenia empates: la curva no arrancaba en
   (0,0) y el trapecio se comia el triangulo inicial. Con score binario el
   error medio era -0.095. En laboratorio los scores empatan todo el tiempo
   (escalas semicuantitativas, resultados redondeados, ordinales).
2. `diagnostic_test` no devolvia ningun intervalo de confianza. CLSI EP12 los
   exige, y sin ellos 20/20 se lee como "sensibilidad 100%" a secas.
3. El tamano muestral usaba z donde va t. Con efecto grande pedia n=2 para un
   poder de 0.80 cuando el poder real de ese n era 0.18. Y `power_analysis`
   usaba z tambien, asi que la app confirmaba su propio error.
"""
import numpy as np
import pytest
from sklearn.metrics import roc_auc_score
from statsmodels.stats.power import TTestPower, TTestIndPower
from statsmodels.stats.proportion import proportion_confint

from src.core.roc import roc_curve, auc, optimal_threshold
from src.core.diagnostic_tests import diagnostic_test, relative_risk, wilson_ci
from src.core import sample_size as ss


def _datos(semilla, n=200, niveles=None):
    r = np.random.default_rng(semilla)
    y = r.integers(0, 2, n)
    sc = y * 1.2 + r.normal(0, 1, n)
    if niveles:
        bordes = np.quantile(sc, np.linspace(0, 1, niveles + 1)[1:-1])
        sc = np.digitize(sc, bordes).astype(float)
    return y, sc


# ---------------- AUC contra sklearn, sobre todo con empates ----------------

@pytest.mark.parametrize("niveles", [None, 20, 10, 5, 3, 2])
def test_el_auc_coincide_con_sklearn(niveles):
    """`niveles=2` es un score binario: todos empatados en dos valores. Ahi es
    donde el calculo viejo se desviaba 0.11."""
    for s in range(20):
        y, sc = _datos(s, niveles=niveles)
        f, t, _ = roc_curve(y, sc)
        assert auc(f, t) == pytest.approx(roc_auc_score(y, sc), abs=1e-12)


def test_la_curva_arranca_en_el_origen():
    """Sin el (0,0) el area del primer tramo no se cuenta."""
    for s in range(10):
        y, sc = _datos(s, niveles=4)
        f, t, _ = roc_curve(y, sc)
        assert f[0] == 0.0 and t[0] == 0.0


def test_la_curva_termina_en_uno_uno():
    for s in range(10):
        y, sc = _datos(s, niveles=4)
        f, t, _ = roc_curve(y, sc)
        assert f[-1] == pytest.approx(1.0) and t[-1] == pytest.approx(1.0)


def test_la_curva_es_monotona():
    for s in range(10):
        y, sc = _datos(s, niveles=6)
        f, t, _ = roc_curve(y, sc)
        assert np.all(np.diff(f) >= -1e-12) and np.all(np.diff(t) >= -1e-12)


def test_una_sola_clase_no_devuelve_un_auc_falso():
    """Devolver 0.0 se lee como 'prueba pesima'. Es 'no se puede calcular'."""
    f, t, _ = roc_curve(np.zeros(10, dtype=int), np.arange(10.0))
    assert np.isnan(auc(f, t))


def test_el_umbral_optimo_no_es_el_punto_de_no_diagnosticar():
    """El (0,0) lleva umbral +inf. Si el argmax cae ahi se muestra 'inf'."""
    for s in range(20):
        y, sc = _datos(s + 100, niveles=5)
        f, t, th = roc_curve(y, sc)
        umbral, j, sens, fpr = optimal_threshold(f, t, th)
        assert np.isfinite(umbral), "umbral infinito: es 'no diagnosticar a nadie'"
        assert np.isfinite(j)


# ---------------- Wilson ----------------

@pytest.mark.parametrize("exitos,total", [(20, 20), (0, 20), (1, 30), (19, 20), (50, 100)])
def test_wilson_coincide_con_statsmodels(exitos, total):
    got = wilson_ci(exitos, total)
    esperado = proportion_confint(exitos, total, method="wilson")
    assert got[0] == pytest.approx(esperado[0], abs=1e-10)
    assert got[1] == pytest.approx(esperado[1], abs=1e-10)


def test_sensibilidad_perfecta_no_da_un_intervalo_de_ancho_cero():
    """20 de 20 no es certeza absoluta. Wald diria (1.0, 1.0)."""
    r = diagnostic_test(20, 0, 0, 20)
    lo, hi = r["ci_sens"]
    assert hi == pytest.approx(1.0)
    assert lo < 0.90, f"IC demasiado angosto para n=20: ({lo}, {hi})"


def test_diagnostic_test_trae_los_intervalos_que_pide_ep12():
    r = diagnostic_test(45, 5, 8, 42)
    for clave in ("ci_sens", "ci_spec", "ci_ppv", "ci_npv"):
        lo, hi = r[clave]
        assert 0 <= lo <= hi <= 1
    assert r["ci_sens"][0] <= r["sens"] <= r["ci_sens"][1]


def test_sin_enfermos_la_sensibilidad_no_es_cero_sino_indefinida():
    r = diagnostic_test(0, 10, 0, 30)
    assert np.isnan(r["sens"])
    assert any("enfermos" in a for a in r["avisos"])


# ---------------- Riesgo relativo ----------------

def test_una_celda_en_cero_no_invalida_un_riesgo_relativo_calculable():
    """b=0 significa que todos los expuestos tuvieron el evento. El RR sigue
    definido; antes devolvia None y la UI decia 'No se pudo calcular'."""
    r = relative_risk(10, 0, 5, 15)
    assert "error" not in r
    assert r["rr"] == pytest.approx((10 / 10) / (5 / 20))


def test_sin_eventos_en_el_grupo_de_referencia_se_explica_el_motivo():
    r = relative_risk(10, 5, 0, 15)
    assert "error" in r and "referencia" in r["error"]


def test_el_ic_del_rr_no_tiene_ancho_cero_con_a_igual_a_cero():
    """Sin correccion, se_ln quedaba en 0 y el IC salia (rr, rr): precision
    absoluta a partir de cero eventos."""
    r = relative_risk(0, 20, 5, 15)
    assert "error" not in r
    assert r["ci_upper"] > r["ci_lower"], "IC de ancho cero"
    assert r["haldane"] is True


def test_cuando_la_exposicion_daña_se_informa_nnh_y_no_infinito():
    """arr < 0 significa que la exposicion aumenta el riesgo. Devolver inf
    decia 'no hay efecto' justo donde el efecto es dañino."""
    r = relative_risk(15, 5, 5, 15)   # riesgo expuestos 0.75 vs 0.25
    assert np.isfinite(r["nnt"])
    assert r["nnt_tipo"] == "NNH"


# ---------------- Tamano muestral ----------------

@pytest.mark.parametrize("delta,sd", [(2.0, 5.0), (5.0, 5.0), (10.0, 5.0),
                                      (5.0, 12.0), (10.0, 12.0)])
@pytest.mark.parametrize("poder", [0.80, 0.90, 0.95])
def test_n_de_una_media_coincide_con_statsmodels(delta, sd, poder):
    got = ss.sample_size_mean(delta, sd, alpha=0.05, power=poder)["n_per_group"]
    esperado = TTestPower().solve_power(effect_size=delta / sd, alpha=0.05,
                                        power=poder, alternative="two-sided")
    assert got == int(np.ceil(esperado))


@pytest.mark.parametrize("delta,sd", [(5.0, 10.0), (10.0, 10.0), (5.0, 20.0)])
def test_n_de_dos_medias_coincide_con_statsmodels(delta, sd):
    got = ss.sample_size_two_means(delta, sd, alpha=0.05, power=0.80)["n_group1"]
    esperado = TTestIndPower().solve_power(effect_size=delta / sd, alpha=0.05,
                                           power=0.80, ratio=1,
                                           alternative="two-sided")
    assert got == int(np.ceil(esperado))


@pytest.mark.parametrize("delta,sd", [(2.0, 5.0), (5.0, 5.0), (10.0, 5.0), (10.0, 12.0)])
@pytest.mark.parametrize("poder", [0.80, 0.90])
def test_el_n_entregado_alcanza_de_verdad_el_poder_pedido(delta, sd, poder):
    """La prueba que importa: no que el numero coincida con otra libreria, sino
    que ese n tenga el poder que se pidio. Con z daba 0.18 para un 0.80 pedido."""
    n = ss.sample_size_mean(delta, sd, alpha=0.05, power=poder)["n_per_group"]
    real = TTestPower().power(effect_size=delta / sd, nobs=n, alpha=0.05,
                              alternative="two-sided")
    assert real >= poder - 1e-6, f"n={n} da poder {real:.4f}, se pidio {poder}"


def test_la_ida_y_vuelta_no_se_confirma_a_si_misma_con_la_formula_equivocada():
    """n -> poder tiene que cerrar Y coincidir con statsmodels. Antes cerraba
    usando z de los dos lados, que es consistente y erroneo."""
    for delta, sd in [(2.0, 5.0), (5.0, 5.0), (10.0, 5.0)]:
        n = ss.sample_size_mean(delta, sd, 0.05, 0.80)["n_per_group"]
        propio = ss.power_analysis(n, delta, sd, 0.05)["power"]
        externo = TTestPower().power(effect_size=delta / sd, nobs=n, alpha=0.05,
                                     alternative="two-sided")
        assert propio == pytest.approx(externo, abs=1e-6)
        assert propio >= 0.80


def test_n_uno_no_es_una_respuesta_valida():
    """Con efecto enorme la formula con z devolvia n=2, y con efectos mayores
    habria devuelto n=1: una t con 0 grados de libertad."""
    for efecto in (2.0, 3.0, 5.0, 10.0):
        n = ss.sample_size_mean(efecto, 1.0, 0.05, 0.80)["n_per_group"]
        assert n >= 2, f"efecto {efecto} -> n={n}"
