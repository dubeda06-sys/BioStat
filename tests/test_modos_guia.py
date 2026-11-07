"""Modos guía: Asistente (dónde va cada dato), Docencia (para qué sirve cada
prueba) y Rueditas (preguntas y respuestas sin jerga)."""
import os

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QSettings  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from src.ui.guia import modos  # noqa: E402
from src.ui.guia.analisis_datos import a_formato_largo, diagnosticar  # noqa: E402
from src.ui.guia.contenido import explicar_ensayo, pasos_asistente  # noqa: E402
from src.ui.guia.ejemplos import COLUMNAS_EJEMPLO, OBJETIVOS, dataset  # noqa: E402
from src.ui.guia.respuestas import responder, validar  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ajustes_temporales(tmp_path, monkeypatch):
    """El modo se guarda en QSettings: en los tests, a un .ini descartable."""
    ruta = str(tmp_path / "guia.ini")
    monkeypatch.setattr(modos, "_ajustes", lambda: QSettings(ruta, QSettings.Format.IniFormat))
    return ruta


# ------------------------------------------------------------------ diagnóstico
def test_el_diagnostico_reconoce_cada_columna_del_ejemplo():
    d = diagnosticar(dataset("grupos"))
    roles = {c.nombre: c.rol for c in d.columnas}
    assert roles == {"paciente": "identificador", "tratamiento": "categoria",
                     "glucosa_mg_dl": "numero"}
    assert "grupos" in d.posibles
    assert d.listo


def test_una_fila_de_totales_es_un_error():
    df = pd.DataFrame({"grupo": ["A", "A", "B", "B", "Total"],
                       "valor": [1.0, 2.0, 3.0, 4.0, 10.0]})
    d = diagnosticar(df)
    assert not d.listo
    assert any(a.gravedad == "error" and "total" in a.texto for a in d.avisos)


def test_los_grupos_en_columnas_separadas_se_detectan_y_se_convierten():
    # Una planilla real: con muy pocas filas el motor ve "códigos", no mediciones.
    rng = np.random.default_rng(0)
    tratado = np.round(rng.normal(90, 6, 20), 1)
    tratado[-3:] = np.nan                        # grupos de distinto tamaño
    df = pd.DataFrame({"control": np.round(rng.normal(102, 7, 20), 1), "tratado": tratado})
    d = diagnosticar(df)
    assert d.formato_ancho == ["control", "tratado"]
    largo = a_formato_largo(df, d.formato_ancho)
    assert list(largo.columns) == ["grupo", "valor"]
    assert len(largo) == 37                     # los vacíos no son casos
    assert set(largo["grupo"]) == {"control", "tratado"}


def test_una_categoria_de_un_solo_valor_se_avisa():
    df = pd.DataFrame({"sexo": ["F"] * 6, "edad": [30.0, 41, 52, 28, 60, 45]})
    d = diagnosticar(df)
    assert any("un solo valor" in a.texto for a in d.avisos)


def test_tabla_vacia():
    d = diagnosticar(pd.DataFrame())
    assert d.filas == 0 and not d.listo


# ------------------------------------------------------------------ rueditas
@pytest.mark.parametrize("clave", list(OBJETIVOS))
def test_cada_ejemplo_tiene_respuesta(clave):
    r = responder(dataset(clave), clave, COLUMNAS_EJEMPLO[clave])
    assert r.color != "gris", r.explicacion
    assert r.titular
    assert r.columnas


def test_la_decision_es_la_del_motor():
    assert responder(dataset("grupos"), "grupos", COLUMNAS_EJEMPLO["grupos"]).color == "verde"
    # El ejemplo de asociación queda cerca del umbral y no alcanza: se dice así.
    r = responder(dataset("asociacion"), "asociacion", COLUMNAS_EJEMPLO["asociacion"])
    assert r.color == "ambar"
    assert "No se encontró" in r.titular


@pytest.mark.parametrize("clave", list(OBJETIVOS))
def test_rueditas_no_habla_en_jerga(clave):
    r = responder(dataset(clave), clave, COLUMNAS_EJEMPLO[clave])
    texto = " ".join([r.titular, r.explicacion, r.p_llano] + list(r.advertencias))
    for jerga in ("OLS", "CCC", "IC95", "Shapiro", "DS)", "p=", "Lin)"):
        assert jerga not in texto, f"{clave}: «{jerga}» en {texto!r}"


def test_metodos_dice_cuanto_mas_da_uno_que_otro():
    r = responder(dataset("metodos"), "metodos", COLUMNAS_EJEMPLO["metodos"])
    assert "glucosa_equipo_nuevo" in r.explicacion
    assert "más" in r.explicacion


def test_la_misma_columna_dos_veces_no_se_acepta():
    df = dataset("relacion")
    problemas = validar(df, "relacion", {"x": "edad_anios", "y": "edad_anios"})
    assert any("misma columna" in p for p in problemas)
    assert responder(df, "relacion", {"x": "edad_anios", "y": "edad_anios"}).color == "gris"


# ------------------------------------------------------------------ contenido
def test_hay_un_solo_paso_actual():
    for estado in [(False, False, False), (True, False, False), (True, True, False),
                   (True, True, True)]:
        pasos = pasos_asistente(*estado, pestana="datos")
        assert sum(p["actual"] for p in pasos) <= 1


def test_docencia_explica_para_que_sirve_cada_prueba():
    e = explicar_ensayo("shapiro")
    assert e["nombre"] and e["para_que"] and e["que"]
    assert e["iterativo"] is True


# ------------------------------------------------------------------ interfaz
def test_el_panel_dibuja_cada_modo(qt_app):
    from src.ui.guia.panel_guia import PanelGuia
    p = PanelGuia()
    p.set_modo("normal")
    assert "¿Cómo querés trabajar?" in p.textos()
    p.set_modo("asistente")
    assert "Usar este ejemplo" in p.textos()          # sin datos: plantillas
    p.set_datos(dataset("grupos"))
    assert "Tu tabla: 60 filas" in p.textos()
    p.set_modo("docencia")
    assert "Glosario" in p.textos()
    p.set_modo("rueditas")
    assert "Hacerle una pregunta a mis datos" in p.textos()


def test_rueditas_de_punta_a_punta(qt_app):
    from src.ui.guia.rueditas import AsistenteRueditas
    r = AsistenteRueditas(dataset("grupos"))
    assert r._pila.currentIndex() == 1               # con datos, arranca en la pregunta
    r._elegir_objetivo("grupos")
    assert r._siguiente.isEnabled()
    r._avanzar()
    assert r._pila.currentIndex() == 3
    assert r.respuesta.color == "verde"


def test_la_ventana_cambia_de_modo_y_lo_recuerda(qt_app, ajustes_temporales):
    from src.ui.main_window import MainWindow
    w = MainWindow()
    w._aplicar_modo("docencia", abrir=False)
    assert w.panel_guia.modo.value == "docencia"
    assert not w.dock_guia.isHidden()
    assert modos.modo_guardado() == modos.Modo.DOCENCIA
    w._aplicar_modo("normal")
    assert w.dock_guia.isHidden()


def test_cargar_un_ejemplo_llena_la_tabla(qt_app, ajustes_temporales):
    from src.ui.main_window import MainWindow
    w = MainWindow()
    w._cargar_ejemplo("metodos")
    assert list(w.data_panel.get_data().columns) == list(dataset("metodos").columns)
    assert w.panel_guia.diagnostico is not None
