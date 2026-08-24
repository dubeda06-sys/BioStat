"""Passing-Bablok, verificado por sus propiedades y no por sus numeros.

Los tests que habia solo pedian que el IC existiera. Existia, y estaba mal: era
el percentil empirico 2.5/97.5 de las pendientes por pares, entre 26 y 83 veces
mas ancho que el intervalo que corresponde. Cubria el 100% de las veces y no
detectaba NUNCA un sesgo proporcional del 10%, en 900 corridas. Un laboratorio
habria concluido que los metodos eran intercambiables.

Estos tests miran lo que un numero suelto no puede mostrar: simetria, cobertura
y potencia. Son mas lentos que un assert de igualdad, y son los que atajan la
clase de error que se nos paso.

Referencia: Passing H, Bablok W (1983) J Clin Chem Clin Biochem 21:709-720.
"""
import numpy as np
import pytest

from src.core.passing_bablok import passing_bablok


# ---------------- Simetria: la propiedad que define al metodo ----------------

@pytest.mark.parametrize("nombre,sx,sy,n", [
    ("lab tipico", 0, 4, 40),
    ("ruido medio", 0, 25, 60),
    ("ruido alto", 0, 60, 60),
    ("rango angosto", 0, 3, 50),
    ("error en ambos", 10, 10, 50),
])
def test_es_simetrico_al_dar_vuelta_los_ejes(nombre, sx, sy, n):
    """b(x,y) * b(y,x) == 1 exacto.

    En comparacion de metodos ninguno de los dos es la verdad, asi que el
    resultado no puede depender de cual se grafica en cada eje. Esto es lo que
    aporta el desplazamiento K = #{Sij < -1}: sin K esto es Theil-Sen, que da
    0.994 en datos limpios y 0.04 con ruido.
    """
    r = np.random.default_rng(11)
    base = r.uniform(50, 200, n)
    x = base + r.normal(0, sx, n)
    y = base + r.normal(0, sy, n)
    ida = passing_bablok(x, y)["slope"]
    vuelta = passing_bablok(y, x)["slope"]
    assert ida * vuelta == pytest.approx(1.0, abs=1e-5), (
        f"{nombre}: el resultado cambia segun que columna va en cada eje")


def test_el_desplazamiento_k_queda_a_la_vista():
    """K explica por que la pendiente no es la mediana cruda. Si no se expone,
    nadie puede auditar el numero."""
    r = np.random.default_rng(3)
    x = r.uniform(50, 200, 40)
    res = passing_bablok(x, x + r.normal(0, 20, 40))
    assert "k_desplazamiento" in res and "n_pendientes" in res
    assert 0 <= res["k_desplazamiento"] <= res["n_pendientes"]


# ---------------- Cobertura y potencia del intervalo ----------------

def _corridas(pendiente_real, n, sd, reps, semilla):
    """Devuelve la lista de IC de la pendiente sobre `reps` datasets."""
    out = []
    for s in range(reps):
        r = np.random.default_rng(semilla + s)
        base = r.uniform(50, 200, n)
        # Error en ambos metodos: es lo que Passing-Bablok supone. Con el error
        # concentrado en un solo metodo el IC sub-cubre, y eso es limitacion
        # del metodo, no de esta implementacion.
        x = base + r.normal(0, sd, n)
        y = pendiente_real * base + r.normal(0, sd * pendiente_real, n)
        out.append(passing_bablok(x, y)["ci_slope"])
    return out


def test_el_ic95_cubre_cerca_del_95_por_ciento():
    """Un IC del 95% que cubre el 100% no discrimina nada: nunca va a decir que
    hay sesgo. El defecto original daba exactamente 100%."""
    ics = _corridas(1.0, n=50, sd=8, reps=200, semilla=90000)
    cobertura = np.mean([lo <= 1.0 <= hi for lo, hi in ics])
    assert 0.88 <= cobertura <= 0.99, (
        f"cobertura {cobertura:.1%}: un IC del 95% no puede cubrir esto")


def test_detecta_un_sesgo_proporcional_del_10_por_ciento():
    """Lo que el usuario necesita que funcione. El defecto original detectaba
    0 de 900."""
    ics = _corridas(1.10, n=50, sd=4, reps=100, semilla=70000)
    detectados = np.mean([not (lo <= 1.0 <= hi) for lo, hi in ics])
    assert detectados > 0.90, (
        f"solo detecta el sesgo en {detectados:.1%} de las corridas")


def test_el_ic_se_angosta_al_crecer_n():
    """Propiedad basica de cualquier intervalo de confianza. El percentil
    empirico de las pendientes no la cumplia: se quedaba en ~2.4 sin importar n."""
    anchos = []
    for n in (30, 60, 120, 240):
        r = np.random.default_rng(5)
        base = r.uniform(50, 200, n)
        res = passing_bablok(base + r.normal(0, 5, n), base + r.normal(0, 5, n))
        anchos.append(res["ci_slope"][1] - res["ci_slope"][0])
    assert anchos == sorted(anchos, reverse=True), f"no se angosta: {anchos}"
    # C ~ n^1.5 sobre N ~ n^2 deja el semiancho en n^-0.5: de 30 a 240 son 8x
    # en n, o sea sqrt(8) = 2.83x mas angosto. Se pide 2x para dejar margen.
    assert anchos[0] > 2 * anchos[-1], f"se angosta demasiado poco: {anchos}"


def test_el_ic_contiene_a_la_pendiente():
    """Invariante barato que atrapa desalineaciones de indice entre el
    estimador (desplazado por K) y los limites (que tambien deben estarlo)."""
    for s in range(30):
        r = np.random.default_rng(600 + s)
        base = r.uniform(20, 300, 45)
        res = passing_bablok(base + r.normal(0, 12, 45), base + r.normal(0, 12, 45))
        lo, hi = res["ci_slope"]
        assert lo <= res["slope"] <= hi, f"semilla {s}: pendiente fuera de su IC"


# ---------------- Bordes ----------------

def test_relacion_negativa_se_rechaza_con_motivo():
    """Passing-Bablok supone que los dos metodos crecen juntos. Con relacion
    inversa el estimador queda indefinido; antes esto devolvia un numero."""
    r = np.random.default_rng(4)
    x = r.uniform(50, 200, 40)
    res = passing_bablok(x, -1.2 * x + 300 + r.normal(0, 5, 40))
    assert "error" in res
    assert "negativas" in res["error"] or "invertidas" in res["error"]


def test_n_minimo_avisa_que_no_discrimina():
    """Con n=3 el intervalo cubre todas las pendientes. Devolverlo sin aviso
    invita a leer 'no hay sesgo' donde dice 'no hay informacion'."""
    res = passing_bablok([1.0, 2.0, 3.0], [1.1, 2.0, 3.2])
    assert "error" not in res
    assert any("no hay informacion" in a or "no discrimina" in a
               for a in res["avisos"]), res["avisos"]


def test_pares_con_x_repetida_no_rompen():
    """dx == 0 da pendiente infinita: el par se descarta, no se propaga inf."""
    x = [10.0, 10.0, 10.0, 20.0, 20.0, 30.0, 40.0, 50.0]
    y = [11.0, 12.0, 10.5, 21.0, 19.0, 31.0, 39.0, 51.0]
    res = passing_bablok(x, y)
    assert "error" not in res
    assert np.isfinite(res["slope"]) and np.isfinite(res["intercept"])
    assert all(np.isfinite(v) for v in res["ci_slope"])
