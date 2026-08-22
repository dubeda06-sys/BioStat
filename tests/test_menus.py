"""La barra de menus tiene que apuntar a analisis que existan.

El menu selecciona el analisis buscandolo por texto en el combo
(`findText`). Si el texto no coincide exacto, `findText` devuelve -1 y la
accion no hace nada — sin excepcion, sin mensaje, sin nada. Un acento perdido
deja una entrada de menu muerta que nadie nota hasta que un usuario la usa.

Estos tests cierran las dos direcciones: ningun menu apunta al vacio, y ningun
analisis queda sin entrada de menu.
"""
import pytest

from src.ui.help_text import ANALYSIS_HELP
from src.ui.menus import (
    ESTADISTICAS_SUELTAS,
    MENU_ESTADISTICAS,
    MENU_GRAFICOS,
    MENU_PRUEBAS,
    MENU_QC,
    analisis_referenciados,
)


def test_todo_menu_apunta_a_un_analisis_que_existe():
    faltan = [n for n in analisis_referenciados() if n not in ANALYSIS_HELP]
    assert faltan == [], f"entradas de menu sin analisis detras: {faltan}"


def test_ningun_analisis_queda_fuera_del_menu():
    referenciados = set(analisis_referenciados())
    huerfanos = [k for k in ANALYSIS_HELP if k not in referenciados]
    assert huerfanos == [], f"analisis sin entrada de menu: {huerfanos}"


def test_ningun_analisis_aparece_dos_veces():
    nombres = analisis_referenciados()
    repetidos = sorted({n for n in nombres if nombres.count(n) > 1})
    assert repetidos == [], f"analisis en dos menus a la vez: {repetidos}"


def test_menu_de_graficos_coincide_con_el_panel():
    from src.ui.graphs_panel import GRAPH_HELP
    faltan = [c for _, c in MENU_GRAFICOS if c not in GRAPH_HELP]
    assert faltan == [], f"entradas de Graficos sin grafico detras: {faltan}"


def test_menu_de_qc_coincide_con_el_panel():
    from src.ui.qc_panel import QC_HELP
    faltan = [c for _, c in MENU_QC if c not in QC_HELP]
    assert faltan == [], f"entradas de Control de Calidad sin analisis detras: {faltan}"


def test_no_hay_grupos_vacios():
    vacios = [grupo for grupo, items in MENU_ESTADISTICAS if not items]
    assert vacios == [], f"submenus sin items: {vacios}"
    assert ESTADISTICAS_SUELTAS, "el menu Estadisticas perdio sus items sueltos"
    assert MENU_PRUEBAS, "el menu Pruebas diagnosticas quedo vacio"


@pytest.mark.parametrize("grupo,items", MENU_ESTADISTICAS)
def test_etiquetas_no_vacias(grupo, items):
    assert grupo.strip(), "submenu sin nombre"
    for label, combo in items:
        assert label.strip(), f"item sin etiqueta en {grupo} (apunta a {combo})"
