"""La auditoria tiene que separar tres cosas que se parecen y no son iguales:

  ejecutado   corrio
  descartado  el motor lo evaluo y eligio la otra rama, con motivo
  no aplica   nunca se llego a ese nodo

Confundir "descartado" con "no aplica" es exactamente lo que hace imposible
auditar el motor: la primera es una decision defendible, la segunda es una rama
que los datos no abrieron.
"""
import numpy as np
import pandas as pd
import pytest

from src.analysis.omni_analyzer import _fmt_p, _p, run_omnianalysis
from src.analysis.omni_auditoria import (
    DESCARTADO, EJECUTADO, NO_APLICA, auditar, resumen_en_una_linea,
)
from src.analysis.omni_catalogo import ENSAYOS


@pytest.fixture(scope="module")
def informe_completo():
    """Dataset que abre casi todas las ramas: numericas, categoricas y un par
    de metodos confirmado."""
    rng = np.random.default_rng(7)
    n = 60
    df = pd.DataFrame({
        "MetodoA": rng.normal(100, 15, n),
        "Grupo": rng.choice(["ctrl", "caso", "otro"], n),
        "Sexo": rng.choice(["F", "M"], n),
    })
    df["MetodoB"] = df["MetodoA"] * 1.02 + rng.normal(0, 4, n)
    df["Edad"] = rng.integers(20, 80, n).astype(float)
    return run_omnianalysis(df, list(df.columns),
                            confirmed_comparisons=[("MetodoA", "MetodoB")])


@pytest.fixture(scope="module")
def auditoria(informe_completo):
    return auditar(informe_completo)


def test_cada_ensayo_del_catalogo_aparece_una_vez(auditoria):
    ids = [f["id"] for f in auditoria["filas"]]
    assert len(ids) == len(ENSAYOS)
    assert len(set(ids)) == len(ids)


def test_todo_estado_es_uno_de_los_tres(auditoria):
    validos = {EJECUTADO, DESCARTADO, NO_APLICA}
    raros = {f["estado"] for f in auditoria["filas"]} - validos
    assert raros == set(), f"estados inventados: {raros}"


def test_el_perfilado_siempre_corre(auditoria):
    # El nodo raiz no depende de nada: si no corrio, no hubo analisis.
    assert auditoria["estado"]["perfil_tipos"] == EJECUTADO
    assert auditoria["estado"]["perfil_estructura"] == EJECUTADO


def test_ejecutar_gana_sobre_descartar():
    """Un ensayo que corre en una columna y se descarta en otra queda EJECUTADO.

    Con varias columnas, Shapiro decide normal en una y no normal en otra: la
    media se marca ejecutada en la primera y descartada en la segunda. La fila
    tiene que decir "ejecutado", con el descarte contado aparte.
    """
    rng = np.random.default_rng(3)
    df = pd.DataFrame({
        "normal": rng.normal(50, 5, 80),
        "sesgada": rng.exponential(3, 80),
    })
    aud = auditar(run_omnianalysis(df, list(df.columns)))
    fila = next(f for f in aud["filas"] if f["id"] == "central_media")
    assert fila["estado"] == EJECUTADO
    assert fila["veces"] >= 1
    assert fila["descartes"] >= 1


def test_los_descartados_traen_motivo(auditoria):
    sin_motivo = [f["id"] for f in auditoria["por_estado"][DESCARTADO] if not f["motivos"]]
    assert sin_motivo == [], (
        f"descartados sin explicacion: {sin_motivo}. Un descarte sin motivo no "
        "se puede auditar."
    )


def test_anderson_se_descarta_por_el_n(auditoria):
    # Con n=60 corresponde Shapiro; Anderson-Darling no se descarto por olvido.
    fila = next(f for f in auditoria["filas"] if f["id"] == "anderson")
    assert fila["estado"] == DESCARTADO
    assert any("SHAPIRO_MAX" in m for m in fila["motivos"])


def test_las_ejecuciones_superan_a_los_tipos(auditoria):
    """Con varias columnas, el univariado corre una vez por columna.

    Es la distincion que confunde a cualquiera que mire el numero: 'ensayos
    hechos' (ejecuciones) no es 'tipos de ensayo tocados'.
    """
    r = auditoria["resumen"]
    assert r["ejecuciones"] > r["tipos_ejecutados"]
    assert r["catalogo"] == len(ENSAYOS)
    assert r["decisiones"] >= r["ejecuciones"]


def test_los_conteos_por_etapa_cierran(auditoria):
    for etapa, cuentas in auditoria["por_etapa"].items():
        suma = cuentas[EJECUTADO] + cuentas[DESCARTADO] + cuentas[NO_APLICA]
        assert suma == cuentas["total"], f"la etapa {etapa} no cierra"


def test_rama_a_deja_el_bivariado_sin_aplicar():
    """Una sola columna: los ensayos bivariados no se descartaron, no aplican."""
    df = pd.DataFrame({"unica": np.random.default_rng(1).normal(10, 2, 40)})
    aud = auditar(run_omnianalysis(df, ["unica"]))
    assert aud["estado"]["pearson"] == NO_APLICA
    assert aud["estado"]["chi2"] == NO_APLICA
    assert aud["resumen"]["rama"] == "A"


def test_un_informe_con_error_no_revienta():
    aud = auditar({"error": "Selecciona al menos una columna."})
    assert aud["filas"] == []
    assert "error" in aud
    assert resumen_en_una_linea(aud) == "Sin corrida que auditar."


def test_el_resumen_de_una_linea_nombra_los_dos_conteos(auditoria):
    texto = resumen_en_una_linea(auditoria)
    r = auditoria["resumen"]
    assert str(r["ejecuciones"]) in texto
    assert str(r["catalogo"]) in texto


# ---------------- Formato de p ----------------
# Un p impreso como "0.0" se lee como "p exactamente cero", que no existe.

def test_un_p_muy_chico_se_informa_como_desigualdad():
    assert _fmt_p(3e-9) == "<0.0001"
    assert _fmt_p(0.0) == "<0.0001"
    assert _p(3e-9) == "p<0.0001"


def test_un_p_normal_se_informa_con_igual():
    assert _fmt_p(0.0345) == "0.0345"
    assert _p(0.0345) == "p=0.0345"


def test_el_token_no_junta_el_igual_con_el_menor():
    # `p=<0.0001` es lo que salia al concatenar el `=` a mano.
    assert "=<" not in _p(1e-12)


def test_un_p_ausente_o_nan_no_revienta():
    assert _fmt_p(None) == "n/d"
    assert _fmt_p(float("nan")) == "n/d"
    assert _p(None) == "p=n/d"


def test_ningun_detalle_de_la_auditoria_dice_p_igual_cero(auditoria):
    sospechosos = [(f["id"], d) for f in auditoria["filas"] for d in f["detalles"]
                   if "p=0.0 " in d or d.endswith("p=0.0")]
    assert sospechosos == [], f"p redondeado a cero sin marcar: {sospechosos}"
