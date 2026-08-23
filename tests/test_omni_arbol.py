"""El arbol dibujado tiene que mostrar TODO el catalogo.

Un ensayo que existe en el motor pero no esta en el layout desaparece del
dibujo sin avisar: el usuario ve un arbol que parece completo y no lo esta.
Es la misma clase de falla silenciosa que los menus por texto.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from src.analysis import omni_arbol  # noqa: E402
from src.analysis.omni_analyzer import run_omnianalysis  # noqa: E402
from src.analysis.omni_auditoria import EJECUTADO, auditar  # noqa: E402
from src.analysis.omni_catalogo import ETAPAS, POR_ID  # noqa: E402


def claves_del_layout():
    for etapa, layout in omni_arbol.LAYOUT.items():
        for clave, _col, _fila in layout["nodos"]:
            yield etapa, clave


@pytest.fixture(scope="module")
def auditoria():
    rng = np.random.default_rng(11)
    n = 50
    df = pd.DataFrame({
        "A": rng.normal(20, 3, n),
        "Grupo": rng.choice(["x", "y"], n),
    })
    df["B"] = df["A"] + rng.normal(0, 1, n)
    return auditar(run_omnianalysis(df, list(df.columns),
                                    confirmed_comparisons=[("A", "B")]))


def test_todo_ensayo_del_catalogo_esta_dibujado():
    dibujados = {clave for _etapa, clave in claves_del_layout()
                 if not clave.startswith("?")}
    faltan = sorted(set(POR_ID) - dibujados)
    assert faltan == [], f"ensayos que no aparecen en ningun arbol: {faltan}"


def test_no_hay_cajas_que_no_sean_ensayos_ni_decisiones():
    invalidas = [clave for _etapa, clave in claves_del_layout()
                 if not clave.startswith("?") and clave not in POR_ID]
    assert invalidas == [], f"cajas sin respaldo en el catalogo: {invalidas}"


def test_toda_decision_tiene_texto():
    sin_texto = [clave for _etapa, clave in claves_del_layout()
                 if clave.startswith("?") and clave not in omni_arbol.DECISIONES]
    assert sin_texto == [], f"nodos de decision sin etiqueta: {sin_texto}"


def test_cada_ensayo_se_dibuja_en_su_propia_etapa():
    mal_ubicados = [(clave, etapa, POR_ID[clave].etapa)
                    for etapa, clave in claves_del_layout()
                    if not clave.startswith("?") and POR_ID[clave].etapa != etapa]
    assert mal_ubicados == [], f"(ensayo, etapa dibujada, etapa real): {mal_ubicados}"


def test_ningun_ensayo_se_dibuja_dos_veces():
    dibujados = [clave for _etapa, clave in claves_del_layout()
                 if not clave.startswith("?")]
    repetidos = sorted({c for c in dibujados if dibujados.count(c) > 1})
    assert repetidos == [], f"ensayos dibujados mas de una vez: {repetidos}"


def test_las_aristas_conectan_nodos_que_existen():
    rotas = []
    for etapa, layout in omni_arbol.LAYOUT.items():
        presentes = {clave for clave, _c, _f in layout["nodos"]}
        for origen, destino, _etq in layout["aristas"]:
            if origen not in presentes or destino not in presentes:
                rotas.append((etapa, origen, destino))
    assert rotas == [], f"aristas colgadas: {rotas}"


def test_el_layout_cubre_las_cinco_etapas():
    assert set(omni_arbol.LAYOUT) == set(ETAPAS)


def test_las_figuras_se_dibujan_sin_auditoria():
    # Sin corrida el arbol sigue sirviendo como mapa del motor.
    figs = omni_arbol.figuras(None)
    try:
        assert len(figs) == len(ETAPAS)
        for _etapa, fig in figs:
            assert fig.get_axes()
    finally:
        for _etapa, fig in figs:
            plt.close(fig)


def test_las_figuras_se_dibujan_con_auditoria(auditoria):
    figs = omni_arbol.figuras(auditoria)
    try:
        for _etapa, fig in figs:
            assert fig.get_axes()
    finally:
        for _etapa, fig in figs:
            plt.close(fig)


def test_la_etiqueta_de_un_ejecutado_lleva_el_conteo(auditoria):
    assert auditoria["estado"]["perfil_tipos"] == EJECUTADO
    etiqueta = omni_arbol._etiqueta("perfil_tipos", auditoria)
    assert "×" in etiqueta


def test_la_etiqueta_distingue_descartado_de_no_aplica(auditoria):
    # El color solo no alcanza para distinguirlos; la palabra si.
    descartado = next(f["id"] for f in auditoria["filas"] if f["estado"] == "descartado")
    assert "descartado" in omni_arbol._etiqueta(descartado, auditoria)
    no_aplica = next((f["id"] for f in auditoria["filas"] if f["estado"] == "no aplica"), None)
    if no_aplica:
        assert "no aplica" in omni_arbol._etiqueta(no_aplica, auditoria)


def test_el_resumen_se_dibuja(auditoria):
    fig = omni_arbol.figura_resumen(auditoria)
    try:
        assert fig.get_axes()
    finally:
        plt.close(fig)
