"""Correcciones de la auditoria de octubre: conteos 2x2, exportacion y `__all__`."""
import numpy as np
import pandas as pd
import pytest

from src.core import diagnostic_tests as D
from src.core import statistics as S
from src.core.export import (export_data_to_csv, export_results_to_html,
                             neutralizar_celda, neutralizar_formulas)


# --- Tablas 2x2: conteos enteros y no negativos -----------------------------

@pytest.mark.parametrize("celdas", [(-1, 2, 3, 4), (1.5, 2, 3, 4), (1, 2, 3, np.nan),
                                    (1, np.inf, 3, 4)])
@pytest.mark.parametrize("funcion", [D.diagnostic_test, D.odds_ratio])
def test_conteos_invalidos_se_rechazan(funcion, celdas):
    with pytest.raises(ValueError, match="enteros no negativos"):
        funcion(*celdas)


def test_conteos_validos_siguen_calculando():
    r = D.diagnostic_test(80, 20, 10, 90)
    assert r["sens"] == pytest.approx(80 / 90)
    assert D.diagnostic_test(np.int64(8), 2, 1, 9)["n"] == 20
    assert D.odds_ratio(0, 5, 3, 4)["or"] > 0  # celda en cero: correccion, no error
    assert D.diagnostic_test(10.0, 0, 0, 10.0)["spec"] == 1.0  # 10.0 es entero


# --- Etiquetas y grupos de distinto largo ------------------------------------

def test_posthoc_con_etiquetas_de_menos_no_recorta_en_silencio():
    grupos = [[1.0, 2, 3, 4], [2.0, 3, 4, 5], [5.0, 6, 7, 8]]
    with pytest.raises(ValueError):
        S.games_howell(grupos, labels=["a", "b"])
    with pytest.raises(ValueError):
        S.dunn_test(grupos, labels=["a", "b"])


# --- Exportacion: HTML ------------------------------------------------------

def test_html_incluye_el_resultado_ya_renderizado():
    html = export_results_to_html({"Resultados": "<p>Media = 12,3</p>"}, "Informe")
    assert "Media = 12,3" in html


def test_html_escapa_titulo_secciones_y_celdas():
    html = export_results_to_html(
        {"<script>x</script>": {"k<b>": "<img src=x onerror=alert(1)>"},
         "tabla": [{"<i>": "<u>v</u>"}]}, "<i>t</i>")
    for peligroso in ("<script>", "<img", "<u>v", "<i>t</i>"):
        assert peligroso not in html
    assert "&lt;script&gt;" in html


# --- Exportacion: formulas en CSV/Excel ---------------------------------------

def test_texto_que_parece_formula_se_neutraliza():
    assert neutralizar_celda("=1+1") == "'=1+1"
    assert neutralizar_celda("@SUM(A1)") == "'@SUM(A1)"
    assert neutralizar_celda("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
    assert neutralizar_celda("\t=1") == "'\t=1"


def test_numeros_y_texto_normal_no_se_tocan():
    for v in ("-5", "+3,2", "-0.5", "1e-3", "Positivo", "", 12, 3.5, None):
        assert neutralizar_celda(v) == v


def test_dataframe_neutralizado_no_muta_el_original():
    df = pd.DataFrame({"a": ["=1+1", "ok"], "b": [-1.0, 2.0]})
    limpio = neutralizar_formulas(df)
    assert list(limpio["a"]) == ["'=1+1", "ok"]
    assert list(limpio["b"]) == [-1.0, 2.0]
    assert df["a"][0] == "=1+1"


def test_csv_exportado_no_lleva_formulas(tmp_path):
    ruta = tmp_path / "x.csv"
    assert export_data_to_csv(pd.DataFrame({"a": ["=HYPERLINK(\"http://x\")", "-7"]}), str(ruta))
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    assert lineas[1].startswith("\"'=HYPERLINK")
    assert lineas[2] == "-7"


# --- `import *` del paquete de constructores ------------------------------------

def test_import_estrella_de_constructores_no_falla():
    ns = {}
    exec("from src.resultado.constructores import *", ns)  # noqa: S102
    assert "CONSTRUCTORES" in ns and "intervalos_por_edad" in ns
