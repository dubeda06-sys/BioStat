"""Declarar un metodo de referencia tiene que cambiar lo que hace el Omnianalisis.

El analisis manual ya dejaba elegir Krouwer, pero el Omnianalisis corria siempre
Bland-Altman clasico contra el promedio: dos numeros distintos para el mismo par
de columnas, y nada en el informe que lo explicara.

El riesgo propio de esta capa es que la referencia se cuelgue de la columna
equivocada. El par viaja ordenado alfabeticamente hacia el analizador, asi que si
la referencia se guardara como "x"/"y" en vez de por nombre, un par cuyo orden
alfabetico difiere del orden del DataFrame quedaria midiendo el desvio contra el
metodo que NO es la referencia — en silencio, con el informe igual de prolijo.
Por eso las columnas de las pruebas se llaman `Zeta_*` y `Alfa_*`: los dos ordenes
no coinciden.
"""
import os

import numpy as np
import pandas as pd
import pytest
from scipy import stats

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.analysis.omni_analyzer import run_omnianalysis  # noqa: E402
from src.analysis.omni_auditoria import DESCARTADO, EJECUTADO, auditar  # noqa: E402
from src.analysis.omni_caso import casos  # noqa: E402

PAR = ("Zeta_referencia", "Alfa_prueba")


@pytest.fixture(scope="module")
def datos():
    """Un metodo que lee 8 % alto contra una referencia: sesgo proporcional real.

    El orden del DataFrame (Zeta primero) es el inverso del alfabetico.
    """
    rng = np.random.default_rng(11)
    ref = rng.uniform(20, 200, 50)
    return pd.DataFrame({
        "Zeta_referencia": ref,
        "Alfa_prueba": ref * 1.08 + rng.normal(0, 3, 50),
    })


@pytest.fixture(scope="module")
def datos_flip():
    """Sin sesgo proporcional real, pero con mucho ruido en el método en prueba.

    Parámetros elegidos por búsqueda (n=30, factor=1.00, sigma=30, semilla=5):
    el IC de la pendiente contra el promedio excluye el 0 y el de la pendiente
    contra la referencia lo incluye. O sea, los dos ejes NO concluyen lo mismo.
    """
    rng = np.random.default_rng(5)
    ref = rng.uniform(20, 200, 30)
    return pd.DataFrame({
        "Zeta_referencia": ref,
        "Alfa_prueba": ref * 1.00 + rng.normal(0, 30, 30),
    })


def _correr(df, referencias=None, par=PAR):
    return run_omnianalysis(df, list(df.columns), confirmed_comparisons=[par],
                            referencias=referencias)


def _bloque(report):
    return next(b for b in report["blocks"] if b.get("tipo") == "concordancia")


def _ba(report):
    return _bloque(report)["resultados"]["bland_altman"]


# ---------------- Sin referencia: el clasico, y dicho ----------------

def test_sin_referencia_el_eje_es_el_promedio(datos):
    assert _ba(_correr(datos))["eje_x"] == "promedio de ambos métodos"


def test_sin_referencia_no_se_inventan_pendientes(datos):
    ba = _ba(_correr(datos))
    assert "pendiente_vs_referencia" not in ba
    assert "pendiente_vs_promedio" not in ba


def test_sin_referencia_el_ensayo_queda_descartado_con_motivo(datos):
    """Descartado, no ausente: la diferencia entre 'no lo corri porque no
    correspondia' y 'me lo olvide' es todo el punto de la auditoria."""
    aud = auditar(_correr(datos))
    fila = next(f for f in aud["filas"] if f["id"] == "ba_eje_referencia")
    assert fila["estado"] == DESCARTADO
    assert fila["motivos"], "un descarte sin motivo no se puede auditar"
    assert "referencia" in fila["motivos"][0]


# ---------------- Con referencia: Krouwer ----------------

def test_con_referencia_el_eje_es_la_columna_declarada(datos):
    ba = _ba(_correr(datos, {PAR: "Zeta_referencia"}))
    assert ba["eje_x"] == "Zeta_referencia (método de referencia)"


def test_con_referencia_el_ensayo_queda_ejecutado(datos):
    aud = auditar(_correr(datos, {PAR: "Zeta_referencia"}))
    assert aud["estado"]["ba_eje_referencia"] == EJECUTADO


def test_se_informan_las_dos_pendientes(datos):
    """Con una sola no se ve la atenuacion, que es el motivo de todo esto."""
    ba = _ba(_correr(datos, {PAR: "Zeta_referencia"}))
    assert ba["pendiente_vs_referencia"] is not None
    assert ba["pendiente_vs_promedio"] is not None
    assert ba["pendiente_vs_referencia"] != ba["pendiente_vs_promedio"]


def test_el_promedio_atenua_y_queda_registrado(datos):
    ba = _ba(_correr(datos, {PAR: "Zeta_referencia"}))
    assert ba["promedio_atenua"] is True
    assert abs(ba["pendiente_vs_promedio"]) < abs(ba["pendiente_vs_referencia"])


def test_si_los_dos_ejes_coinciden_no_se_avisa_nada(datos):
    """La atenuación existe casi siempre, pero suele ser de centésimas.

    Avisar cada vez convierte la advertencia en ruido y entrena al usuario a
    saltearla — que es justo lo que no queremos cuando el caso importe.
    """
    rep = _correr(datos, {PAR: "Zeta_referencia"})
    assert _ba(rep)["cambia_la_conclusion"] is False
    avisos = " ".join(_bloque(rep)["advertencias"])
    assert "Krouwer" not in avisos


def test_si_el_eje_cambia_la_conclusion_se_avisa(datos_flip):
    """El artefacto grande de Krouwer, y va en la dirección contraintuitiva.

    Acá NO hay sesgo proporcional real (el método en prueba lee igual que la
    referencia, solo con mucho ruido). Pero el error del método entra en el
    promedio — mean = ref + eps/2 — y correlaciona con la diferencia, así que
    la regresión contra el promedio INVENTA una pendiente. Contra la
    referencia no aparece. Si el informe se callara esto, el laboratorio
    saldría a recalibrar un método que no tiene nada.
    """
    rep = _correr(datos_flip, {PAR: "Zeta_referencia"})
    assert _ba(rep)["cambia_la_conclusion"] is True
    avisos = " ".join(_bloque(rep)["advertencias"])
    assert "cambia la conclusión" in avisos
    assert "el promedio lo inventa" in avisos
    assert "Krouwer" in avisos


def test_el_texto_del_paso_coincide_con_los_numeros_que_muestra(datos_flip):
    """El promedio distorsiona en las dos direcciones y el texto tiene que decir
    cuál, porque la medición está a la vista en la línea de arriba.

    La primera versión de este paso decía siempre "más cerca de cero", incluso
    acá, donde la pendiente contra el promedio (-0,1849) es MAYOR en magnitud
    que la de la referencia (-0,0733). Un texto que contradice el número que
    tiene al lado es peor que no decir nada: el lector que sí mira el número
    deja de creerle al resto del informe.
    """
    rep = _correr(datos_flip, {PAR: "Zeta_referencia"})
    ba = _ba(rep)
    assert abs(ba["pendiente_vs_promedio"]) > abs(ba["pendiente_vs_referencia"]), \
        "este fixture es el caso en que el promedio INFLA la pendiente"
    paso = next(p for p in _caso_concordancia(rep).pasos if "método bueno" in p.pregunta)
    assert "más cerca de cero" not in paso.consecuencia
    assert "más grande" in paso.consecuencia
    assert "inventado" in paso.consecuencia


def test_el_p_de_la_estructura_es_un_p_y_no_el_error_estandar(datos_flip):
    """Regresión de un bug encontrado acá: `slope, intercept, _, _, p_slope`.

    `stats.linregress` devuelve (slope, intercept, rvalue, pvalue, stderr), así
    que ese desempaquetado guardaba el STDERR en `p_slope`. Con estos datos el
    stderr (0,0860) y el p (0,0405) caen a lados distintos de 0,05: el bug no
    mostraba solo un número equivocado, daba vuelta la conclusión sobre si el
    desacuerdo crece con la concentración — y con ella la elección entre Deming
    y Passing-Bablok, que se decide por `resid_homoced = not proporcional`.
    """
    rep = _correr(datos_flip)  # sin referencia: el eje es el promedio
    sup = _bloque(rep)["resultados"]["supuestos"]
    a = datos_flip["Zeta_referencia"].to_numpy()
    b = datos_flip["Alfa_prueba"].to_numpy()
    lr = stats.linregress((a + b) / 2, a - b)
    assert sup["eje_estructura"] == "el promedio"
    assert sup["p_pendiente"] == round(float(lr.pvalue), 4)
    assert sup["p_pendiente"] != round(float(lr.stderr), 4)
    assert sup["proporcional"] is True, "p=0,0405 < 0,05: la diferencia SÍ es proporcional"


def test_con_referencia_la_estructura_tambien_va_contra_la_referencia(datos_flip):
    """Los dos nodos tienen que mirar el mismo eje, o el informe se contradice.

    Cuando la estructura de la diferencia se medía siempre contra el promedio,
    el paso 1 afirmaba exactamente el desvío que el nodo del eje X señalaba como
    artefacto de ese promedio: dos afirmaciones opuestas en el mismo informe,
    las dos con el mismo aplomo. El p es invariante al signo de la diferencia,
    así que se compara contra él y no contra la pendiente, que depende del orden
    en que llegue el par.
    """
    rep = _correr(datos_flip, {PAR: "Zeta_referencia"})
    sup = _bloque(rep)["resultados"]["supuestos"]
    a = datos_flip["Zeta_referencia"].to_numpy()
    b = datos_flip["Alfa_prueba"].to_numpy()
    contra_ref = stats.linregress(a, a - b)
    contra_prom = stats.linregress((a + b) / 2, a - b)
    assert sup["eje_estructura"] == "Zeta_referencia"
    assert sup["p_pendiente"] == round(float(contra_ref.pvalue), 4)
    assert sup["p_pendiente"] != round(float(contra_prom.pvalue), 4)


def test_el_paso_uno_dice_contra_que_eje_midio(datos_flip):
    """Si no nombra el eje, el lector asume el promedio — y con una referencia
    declarada esa suposición es justo la equivocada."""
    caso = _caso_concordancia(_correr(datos_flip, {PAR: "Zeta_referencia"}))
    paso = next(p for p in caso.pasos if "crece cuando sube" in p.pregunta)
    assert "Zeta_referencia" in paso.medicion
    assert "contra el promedio" not in paso.medicion


def test_el_caso_del_flip_dice_que_la_lectura_se_da_vuelta(datos_flip):
    caso = _caso_concordancia(_correr(datos_flip, {PAR: "Zeta_referencia"}))
    paso = next(p for p in caso.pasos if "método bueno" in p.pregunta)
    assert paso.ok is False, "un paso donde la elección del eje decide no puede salir limpio"
    assert "da vuelta" in paso.consecuencia


# ---------------- El orden del par no puede mover la referencia ----------------

def test_la_referencia_no_se_muda_si_el_par_llega_al_reves(datos):
    """Mismo dato, par declarado en los dos ordenes: mismo eje X.

    Si la referencia se guardara por posicion, uno de los dos saldria midiendo
    el desvio contra el metodo en prueba.
    """
    derecho = _ba(_correr(datos, {PAR: "Zeta_referencia"}, par=PAR))
    revez = _ba(_correr(datos, {PAR[::-1]: "Zeta_referencia"}, par=PAR[::-1]))
    assert derecho["eje_x"] == revez["eje_x"] == "Zeta_referencia (método de referencia)"
    assert derecho["pendiente_vs_referencia"] == revez["pendiente_vs_referencia"]


def test_declarar_la_otra_columna_da_otro_resultado(datos):
    """Que la eleccion no sea decorativa."""
    una = _ba(_correr(datos, {PAR: "Zeta_referencia"}))
    otra = _ba(_correr(datos, {PAR: "Alfa_prueba"}))
    assert una["eje_x"] != otra["eje_x"]
    assert una["pendiente_vs_referencia"] != otra["pendiente_vs_referencia"]


def test_una_referencia_que_no_es_del_par_se_ignora(datos):
    """Nombre que no corresponde a ninguna de las dos columnas: cae al clasico,
    no revienta ni elige una al azar."""
    ba = _ba(_correr(datos, {PAR: "Columna_inexistente"}))
    assert ba["eje_x"] == "promedio de ambos métodos"


# ---------------- El caso, que es lo que lee el usuario ----------------

def _caso_concordancia(report):
    return next(c for c in casos(report) if "Concordancia" in c.titulo)


def test_el_caso_explica_contra_que_se_midio(datos):
    caso = _caso_concordancia(_correr(datos, {PAR: "Zeta_referencia"}))
    paso = next((p for p in caso.pasos if "método bueno" in p.pregunta), None)
    assert paso is not None, "el caso no dice contra que se midio el desvio"
    assert "Zeta_referencia" in paso.respuesta
    assert "Zeta_referencia" in paso.medicion and "promedio" in paso.medicion
    assert paso.alternativa, "sin la alternativa no se entiende por que se eligio"


@pytest.mark.parametrize("fixture", ["datos", "datos_flip"])
def test_el_caso_no_habla_de_estadistica_para_explicarlo(fixture, request):
    """Lo tiene que entender alguien que no sabe estadistica.

    Las dos ramas del texto (el eje no cambió nada / el eje dio vuelta la
    lectura) se revisan por separado: la jerga se cuela justo en la rama que
    menos se mira.
    """
    df = request.getfixturevalue(fixture)
    caso = _caso_concordancia(_correr(df, {PAR: "Zeta_referencia"}))
    paso = next(p for p in caso.pasos if "método bueno" in p.pregunta)
    texto = f"{paso.pregunta} {paso.consecuencia} {paso.alternativa}"
    for jerga in ("atenu", "regresión", "significativo", "Krouwer", "IC 95"):
        assert jerga not in texto, f"jerga en el texto del caso: {jerga}"


def test_sin_referencia_el_caso_no_agrega_el_paso(datos):
    """Un paso que en todos los casos dice lo mismo es ruido."""
    caso = _caso_concordancia(_correr(datos))
    assert not [p for p in caso.pasos if "método bueno" in p.pregunta]


def test_ningun_repr_de_numpy_en_el_paso(datos):
    caso = _caso_concordancia(_correr(datos, {PAR: "Zeta_referencia"}))
    paso = next(p for p in caso.pasos if "método bueno" in p.pregunta)
    for campo in (paso.medicion, paso.respuesta, paso.consecuencia):
        assert "np.float" not in campo and "np.int" not in campo


# ---------------- El dialogo ----------------

@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def dialogo(qt_app):
    from src.ui.omni_panel import ComparisonConfirmDialog
    cand = {"col1": "Zeta_referencia", "col2": "Alfa_prueba",
            "score": 5.0, "corr": 0.99, "reasons": ["mismo rango"]}
    return ComparisonConfirmDialog([cand])


def test_por_defecto_no_hay_referencia(dialogo):
    """El clasico es el default: declarar una referencia es afirmar algo sobre
    el metodo, y eso lo tiene que poner el usuario."""
    assert dialogo.referencias() == {}


def test_el_combo_devuelve_el_nombre_de_columna(dialogo):
    _, _, ref = dialogo._checks[0]
    ref.setCurrentIndex(1)
    assert dialogo.referencias() == {("Alfa_prueba", "Zeta_referencia"): "Zeta_referencia"}


def test_la_clave_sale_ordenada_para_que_el_analizador_la_encuentre(dialogo):
    _, _, ref = dialogo._checks[0]
    ref.setCurrentIndex(2)
    (clave, valor), = dialogo.referencias().items()
    assert clave == tuple(sorted(clave))
    assert valor == "Alfa_prueba"


def test_un_par_destildado_no_aporta_referencia(dialogo):
    _, chk, ref = dialogo._checks[0]
    ref.setCurrentIndex(1)
    chk.setChecked(False)
    assert dialogo.referencias() == {}
    assert dialogo.confirmed_pairs() == []
