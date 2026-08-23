"""El catalogo de ensayos tiene que describir al motor real, no a uno imaginario.

La auditoria promete algo fuerte: "estos son todos los ensayos que el motor
puede correr, y este es el estado de cada uno". Esa promesa se rompe en
silencio de dos maneras:

  - se agrega un ensayo al motor y no al catalogo → invisible en la auditoria;
  - se saca un ensayo del motor y queda en el catalogo → figura como "no aplica"
    para siempre, sin que nadie note que ya no existe.

Ninguna de las dos tira excepcion. Por eso estos tests leen el codigo fuente
del analizador y lo comparan contra el catalogo, en las dos direcciones.
"""
import re
from pathlib import Path

from src.analysis import omni_catalogo
from src.analysis.omni_catalogo import ENSAYOS, ETAPAS, POR_ID

ANALIZADOR = Path(omni_catalogo.__file__).with_name("omni_analyzer.py")

# _marcar(block, "id", ...) / _descartar(report, "id", ...)
_MARCA = re.compile(r'_(?:marcar|descartar)\(\s*\w+\s*,\s*"([^"]+)"')


def ids_marcados_en_el_motor() -> set[str]:
    fuente = ANALIZADOR.read_text(encoding="utf-8")
    return set(_MARCA.findall(fuente))


def test_todo_id_marcado_en_el_motor_existe_en_el_catalogo():
    huerfanos = sorted(ids_marcados_en_el_motor() - set(POR_ID))
    assert huerfanos == [], (
        f"el motor marca ensayos que el catalogo no conoce: {huerfanos}. "
        "La auditoria los descarta en silencio."
    )


def test_todo_ensayo_del_catalogo_lo_marca_el_motor():
    sin_marcar = sorted(set(POR_ID) - ids_marcados_en_el_motor())
    assert sin_marcar == [], (
        f"ensayos del catalogo que el motor nunca marca: {sin_marcar}. "
        "Saldrian como 'no aplica' aunque hayan corrido."
    )


def test_los_ids_son_unicos():
    ids = [e.id for e in ENSAYOS]
    assert len(ids) == len(set(ids)), "hay ids repetidos en el catalogo"


def test_las_etapas_son_validas():
    invalidas = sorted({e.etapa for e in ENSAYOS} - set(ETAPAS))
    assert invalidas == [], f"etapas fuera de ETAPAS: {invalidas}"


def test_toda_alternativa_apunta_a_un_ensayo_real():
    rotas = [(e.id, e.alternativa) for e in ENSAYOS
             if e.alternativa and e.alternativa not in POR_ID]
    assert rotas == [], f"alternativas que no existen: {rotas}"


def test_ningun_ensayo_es_su_propia_alternativa():
    bucles = [e.id for e in ENSAYOS if e.alternativa == e.id]
    assert bucles == [], f"ensayos que se listan como su propia alternativa: {bucles}"


def test_todos_tienen_texto_didactico():
    # El "porque" es lo que ve el usuario en el tooltip: si esta vacio, la
    # pestana de auditoria deja de explicar y pasa a ser una lista de nombres.
    mudos = [e.id for e in ENSAYOS if not e.porque.strip() or not e.gatillo.strip()]
    assert mudos == [], f"ensayos sin gatillo o sin explicacion: {mudos}"


def test_un_incondicional_no_declara_alternativa():
    # Si corre siempre que su etapa se activa, no compite con nadie.
    contradictorios = [e.id for e in ENSAYOS if e.incondicional and e.alternativa]
    assert contradictorios == [], (
        f"marcados incondicionales pero con alternativa: {contradictorios}"
    )


def test_por_etapa_cubre_todo_el_catalogo():
    suma = sum(len(omni_catalogo.por_etapa(e)) for e in ETAPAS)
    assert suma == omni_catalogo.total() == len(ENSAYOS)
