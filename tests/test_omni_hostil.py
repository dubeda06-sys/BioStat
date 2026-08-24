"""El Omnianalisis contra datasets que un usuario real carga por error.

Tres de estos crashes aparecieron como CONSECUENCIA de endurecer el core:
`pearson_r` paso de devolver r=NaN en silencio a devolver {"error": ...} con
datos constantes, y el analizador hacia `pearson_r(a, b)["r"]` sin mirar. O sea
que la falla se mudo de "numero mudo en el informe" a "excepcion". Las dos son
inaceptables, y arreglar la primera sin cubrir la segunda habria empeorado la
app. Por eso el criterio se prueba de punta a punta y no funcion por funcion.
"""
import numpy as np
import pandas as pd
import pytest

from src.analysis.omni_analyzer import run_omnianalysis
from src.analysis.omni_caso import casos


def _hostiles():
    r = np.random.default_rng(11)
    return {
        "una sola fila": pd.DataFrame({"A": [1.0], "B": [2.0]}),
        "dos filas": pd.DataFrame({"A": [1.0, 2.0], "B": [2.0, 3.0]}),
        "una columna constante": pd.DataFrame({"A": [5.0] * 30,
                                               "B": r.normal(5, 1, 30)}),
        "las dos constantes": pd.DataFrame({"A": [5.0] * 30, "B": [7.0] * 30}),
        "todo cero": pd.DataFrame({"A": np.zeros(30), "B": np.zeros(30)}),
        "90% faltantes": pd.DataFrame(
            {"A": np.where(r.random(50) < .9, np.nan, r.normal(0, 1, 50)),
             "B": np.where(r.random(50) < .9, np.nan, r.normal(0, 1, 50))}),
        "columna de texto": pd.DataFrame({"A": ["x"] * 20,
                                          "B": list(r.normal(0, 1, 20))}),
        "con infinitos": pd.DataFrame(
            {"A": np.where(r.random(40) < .1, np.inf, r.normal(50, 5, 40)),
             "B": r.normal(50, 5, 40)}),
        "acentos y unidades": pd.DataFrame({"Glucosa (mg/dL)": r.normal(90, 8, 40),
                                            "Método nuevo µ": r.normal(90, 8, 40)}),
        "fechas": pd.DataFrame({"A": pd.date_range("2024-01-01", periods=30),
                                "B": r.normal(0, 1, 30)}),
        "todo negativo": pd.DataFrame({"A": -r.uniform(1, 100, 40),
                                       "B": -r.uniform(1, 100, 40)}),
        "escala 1e12": pd.DataFrame({"A": r.uniform(1e12, 2e12, 40),
                                     "B": r.uniform(1e12, 2e12, 40)}),
        "escala 1e-9": pd.DataFrame({"A": r.uniform(1e-9, 2e-9, 40),
                                     "B": r.uniform(1e-9, 2e-9, 40)}),
        "un solo valor distinto": pd.DataFrame({"A": [3.0] * 29 + [99.0],
                                                "B": [3.0] * 29 + [99.0]}),
    }


HOSTILES = _hostiles()


@pytest.mark.parametrize("etiqueta", list(HOSTILES))
def test_el_omnianalisis_no_revienta(etiqueta):
    """Puede decir 'no puedo analizar esto y este es el motivo'. No puede tirar
    una traza."""
    informe = run_omnianalysis(HOSTILES[etiqueta].copy(),
                               list(HOSTILES[etiqueta].columns))
    assert isinstance(informe, dict) and "blocks" in informe


@pytest.mark.parametrize("etiqueta", list(HOSTILES))
def test_los_casos_narrados_tampoco_revientan(etiqueta):
    """`casos()` recorre los bloques y arma la narrativa: es una segunda pasada
    sobre los mismos resultados y puede fallar donde el analizador no fallo."""
    informe = run_omnianalysis(HOSTILES[etiqueta].copy(),
                               list(HOSTILES[etiqueta].columns))
    for c in casos(informe):
        assert getattr(c, "tipo", None)


@pytest.mark.parametrize("etiqueta", ["una columna constante", "las dos constantes",
                                      "todo cero"])
def test_la_correlacion_indefinida_se_explica_y_no_tumba_el_informe(etiqueta):
    """Con una columna constante la correlacion no existe. El informe tiene que
    seguir entregando los demas bloques y decir por que falta este."""
    informe = run_omnianalysis(HOSTILES[etiqueta].copy(),
                               list(HOSTILES[etiqueta].columns))
    assert len(informe["blocks"]) >= 2, "se perdieron bloques que si se podian calcular"
    textos = []
    for b in informe["blocks"]:
        textos += list(b.get("advertencias", []))
        if b.get("conclusion"):
            textos.append(b["conclusion"])
    assert any("constante" in t.lower() or "no se puede" in t.lower()
               for t in textos), textos


def test_la_matriz_de_correlaciones_no_mete_un_p_inventado_en_el_fdr():
    """Un par indefinido no puede entrar en la correccion de Benjamini-Hochberg
    con un p fabricado: correria el umbral de todos los demas pares."""
    r = np.random.default_rng(3)
    df = pd.DataFrame({"cte": [5.0] * 40, "a": r.normal(0, 1, 40),
                       "b": r.normal(0, 1, 40), "c": r.normal(0, 1, 40)})
    informe = run_omnianalysis(df, list(df.columns))
    for b in informe["blocks"]:
        celdas = b.get("resultados", {}).get("celdas") or b.get("celdas") or []
        for celda in celdas:
            if celda.get("p") is None:
                assert "p_adj" not in celda, "un par sin p recibio un p ajustado"
            else:
                assert 0 <= celda["p"] <= 1


def test_los_pares_validos_sobreviven_a_un_par_invalido():
    """El caso que importa: una sola columna rota no puede borrar el analisis
    de las columnas sanas."""
    r = np.random.default_rng(4)
    x = r.normal(50, 8, 60)
    df = pd.DataFrame({"rota": [1.0] * 60, "buena_1": x, "buena_2": x * 1.1 + r.normal(0, 2, 60)})
    informe = run_omnianalysis(df, list(df.columns),
                               confirmed_comparisons=[("buena_1", "buena_2")])
    bloque = next((b for b in informe["blocks"] if b.get("tipo") == "concordancia"), None)
    assert bloque is not None, "se perdio la concordancia del par sano"
    assert bloque["resultados"].get("regresion", {}).get("metodo")
