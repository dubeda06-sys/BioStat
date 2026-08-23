"""Los casos son lo que lee alguien que NO sabe estadística.

Por eso lo que se testea acá no es "que no rompa": es que el texto **no
engañe**. Las tres formas de engañar sin mentir son:

  - decir "no se detectó" cuando el intervalo era tan ancho que no podía
    detectar nada (ausencia de evidencia ≠ evidencia de ausencia);
  - contradecirse entre dos pasos sin explicar por qué;
  - dejar que un `repr` de numpy se filtre al texto y parezca un dato.
"""
import numpy as np
import pandas as pd
import pytest

from src.analysis.omni_analyzer import run_omnianalysis
from src.analysis.omni_caso import (
    _ic, _num, _regresion_concluyente, caso_de_bloque, casos,
    probabilidad_en_palabras,
)


@pytest.fixture(scope="module")
def informe():
    rng = np.random.default_rng(7)
    n = 60
    df = pd.DataFrame({
        "Metodo_A": rng.normal(100, 15, n),
        "Grupo": rng.choice(["control", "caso", "dudoso"], n),
        "Sexo": rng.choice(["F", "M"], n),
    })
    df["Metodo_B"] = df["Metodo_A"] * 1.02 + rng.normal(0, 4, n)
    df["Edad"] = rng.integers(20, 80, n).astype(float)
    return run_omnianalysis(df, list(df.columns),
                            confirmed_comparisons=[("Metodo_A", "Metodo_B")])


@pytest.fixture(scope="module")
def todos(informe):
    return casos(informe)


def test_cada_bloque_con_resultados_produce_un_caso(informe):
    bloques = [b for b in informe["blocks"] if b.get("pruebas") or b.get("resultados")]
    assert len(casos(informe)) >= len(bloques) - 1  # el bloque no soportado no cuenta


def test_todo_caso_tiene_pregunta_pasos_y_veredicto(todos):
    mudos = [c.titulo for c in todos if not c.pregunta or not c.pasos]
    assert mudos == [], f"casos sin pregunta o sin pasos: {mudos}"


def test_todo_paso_dice_que_midio_y_que_decidio(todos):
    incompletos = [(c.titulo, p.pregunta) for c in todos for p in c.pasos
                   if not p.pregunta.strip() or not p.medicion.strip()
                   or not p.consecuencia.strip()]
    assert incompletos == [], f"pasos sin medicion o sin consecuencia: {incompletos}"


def test_todo_caso_dice_que_NO_prueba(todos):
    # El matiz es la parte que evita que el usuario sobre-interprete.
    sin_matiz = [c.titulo for c in todos if not c.matiz.strip()]
    assert sin_matiz == [], f"casos sin el 'lo que esto NO dice': {sin_matiz}"


def test_no_se_filtra_el_repr_de_numpy(todos):
    # `np.float64(1.23)` en pantalla parece un dato y no lo es.
    sucios = [(c.titulo, p.medicion) for c in todos for p in c.pasos
              if "np.float64" in p.medicion or "np.float64" in p.consecuencia]
    sucios += [(c.titulo, c.veredicto) for c in todos if "np.float64" in c.veredicto]
    assert sucios == [], f"repr de numpy visible: {sucios}"


def test_no_se_usa_la_palabra_significativo_en_las_explicaciones(todos):
    # Es el termino que mas se malinterpreta: se lee como "importante".
    usos = [(c.titulo, p.consecuencia) for c in todos for p in c.pasos
            if "significativ" in p.consecuencia.lower()]
    assert usos == [], f"'significativo' sin traducir: {usos}"


# ---------------- Probabilidad en palabras ----------------

def test_un_p_alto_aclara_que_no_prueba_ausencia():
    texto = probabilidad_en_palabras(0.59)
    assert "tampoco prueba que no la haya" in texto


def test_un_p_bajo_no_dice_que_algo_quedo_probado():
    texto = probabilidad_en_palabras(0.0001)
    assert "probado" not in texto.lower()
    assert "azar" in texto


def test_un_p_ausente_no_revienta():
    assert "No se pudo" in probabilidad_en_palabras(None)
    assert "No se pudo" in probabilidad_en_palabras(float("nan"))


# ---------------- Intervalos que no concluyen ----------------

def test_un_ic_de_pendiente_ancho_se_declara_no_concluyente():
    """El caso peligroso: el IC incluye el 1, así que la regla mecánica diría
    'no hay sesgo proporcional'. Con un IC de −3 a 5 eso es falso."""
    concluyente, nota = _regresion_concluyente({"ic_pendiente": (-3.06, 5.25)})
    assert concluyente is False
    assert "NO significa que no exista" in nota


def test_un_ic_de_pendiente_angosto_si_concluye():
    concluyente, nota = _regresion_concluyente({"ic_pendiente": (0.96, 1.05)})
    assert concluyente is True
    assert nota == ""


def test_sin_ic_no_se_inventa_una_advertencia():
    assert _regresion_concluyente({})[0] is True


@pytest.fixture(scope="module")
def caso_rango_angosto():
    """Doce pares en un rango de concentración angosto (90 a 110).

    Es un defecto de diseño clásico de EP09: con poco recorrido en X, el IC de
    la pendiente de la regresión de comparación se abre tanto que no puede ni
    afirmar ni descartar un desvío. Este juego de datos dispara a la vez las dos
    protecciones que se prueban abajo.

    Antes las probaba el fixture general por accidente, porque un bug metía el
    error estándar en lugar del p y el motor elegía mal la rama. Arreglado el
    bug hacen falta datos que produzcan la condición de verdad.
    """
    rng = np.random.default_rng(5)
    x = rng.uniform(90, 110, 12)
    df = pd.DataFrame({"Metodo_A": x, "Metodo_B": x + rng.normal(0, 3, 12)})
    informe = run_omnianalysis(df, list(df.columns),
                               confirmed_comparisons=[("Metodo_A", "Metodo_B")])
    return next(c for c in casos(informe) if c.tipo.startswith("¿Los dos métodos"))


def test_la_concordancia_avisa_cuando_la_regresion_no_concluye(caso_rango_angosto):
    paso = next((p for p in caso_rango_angosto.pasos
                 if "corrimiento parejo" in p.pregunta), None)
    assert paso is not None
    # IC de la pendiente enorme: el metodo no puede concluir, y hay que decirlo.
    assert paso.respuesta == "no concluyente"
    assert not paso.ok


def test_si_dos_pasos_se_contradicen_se_explica(caso_rango_angosto):
    """El paso 1 detecta desvío proporcional y la regresión no. Para el lector
    es una contradicción; sin explicarla, el informe pierde credibilidad."""
    paso = next(p for p in caso_rango_angosto.pasos
                if "corrimiento parejo" in p.pregunta)
    assert "paso 1" in paso.consecuencia


# ---------------- Matices que se adaptan al resultado ----------------

def test_el_matiz_de_un_no_hallazgo_habla_de_falta_de_potencia(todos):
    negativos = [c for c in todos
                 if c.veredicto.startswith("No hay evidencia")]
    assert negativos, "el juego de datos no produjo ningun no-hallazgo"
    for c in negativos:
        assert "no" in c.matiz.lower()
        assert "real" not in c.matiz.split(".")[0].lower() or "no prueba" in c.matiz.lower(), (
            f"el matiz de '{c.titulo}' habla de una diferencia que no se encontro: {c.matiz}"
        )


# ---------------- Formato ----------------

def test_los_numeros_se_formatean_sin_ruido():
    assert _num(np.float64(1.23456789)) == "1.235"
    assert _num(None) == "—"
    assert _num(float("nan")) == "—"


def test_los_intervalos_se_muestran_como_rango():
    assert _ic((np.float64(-3.0609), np.float64(5.2452))) == "-3.061 a 5.245"
    assert _ic(None) == "—"


def test_un_bloque_desconocido_no_produce_caso():
    assert caso_de_bloque({"titulo": "otra cosa", "tipo": "no soportado"}) is None


def test_un_informe_con_error_devuelve_lista_vacia():
    assert casos({"error": "sin columnas"}) == []
