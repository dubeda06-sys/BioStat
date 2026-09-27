"""`analysis_specs.VARIABLES` tiene que seguir a lo que cada análisis usa de verdad.

La tabla se generó leyendo el `dispatch` de `AnalysisPanel._run`. Desde el paso 5
(27 sep) ese dispatch es `src/ui/entradas.ENTRADAS`, y este test corre cada
entrada con una elección espía que anota qué variables lee (c1, c2, c3, alfa).
Si mañana alguien agrega un análisis o le cambia los argumentos y no toca la
tabla, el diálogo va a pedir las variables equivocadas — o no pedir ninguna —
sin que nada falle.
"""
import numpy as np
import pandas as pd

from src.ui.analysis_specs import VARIABLES, sobre_toda_la_hoja, variables
from src.ui.help_text import ANALYSIS_HELP

_ORDEN = ("c1", "c2", "c3", "alpha")


def _dispatch_real():
    """Qué variables lee cada entrada de `entradas.ENTRADAS`."""
    from src.ui import entradas

    class Espia(entradas.Eleccion):
        def __getattribute__(self, nombre):
            if nombre in _ORDEN:
                object.__getattribute__(self, "_leidas").add(nombre)
            return object.__getattribute__(self, nombre)

    rng = np.random.default_rng(0)
    hoja = pd.DataFrame({"A": rng.normal(10, 1, 30), "B": rng.normal(10, 1, 30),
                         "C": rng.integers(0, 2, 30).astype(float)})
    encontrado = {}
    for nombre, (_, armar) in entradas.ENTRADAS.items():
        e = Espia(hoja, "A", "B", "C")
        object.__setattr__(e, "_leidas", set())
        try:
            armar(e)
        except Exception:  # noqa: BLE001 — importa qué leyó, no si calculó
            pass
        leidas = object.__getattribute__(e, "_leidas")
        encontrado[nombre] = tuple(v for v in _ORDEN if v in leidas)
    return encontrado


def test_la_tabla_coincide_con_el_dispatch():
    real = _dispatch_real()

    faltan = sorted(set(real) - set(VARIABLES))
    sobran = sorted(set(VARIABLES) - set(real))
    assert faltan == [], f"analisis en el dispatch que la tabla no tiene: {faltan}"
    assert sobran == [], f"analisis en la tabla que ya no estan en el dispatch: {sobran}"

    distintos = {k: (VARIABLES[k], real[k]) for k in real if VARIABLES[k] != real[k]}
    assert distintos == {}, f"variables desincronizadas (tabla, dispatch): {distintos}"


def test_la_tabla_cubre_todos_los_analisis_del_combo():
    faltan = [k for k in ANALYSIS_HELP if k not in VARIABLES]
    assert faltan == [], f"analisis sin ficha de variables: {faltan}"


def test_solo_se_declaran_variables_conocidas():
    validas = {"c1", "c2", "c3", "alpha"}
    for analisis, vs in VARIABLES.items():
        assert set(vs) <= validas, f"{analisis} declara algo raro: {vs}"


def test_sobre_toda_la_hoja_ignora_el_alfa():
    # La ANOVA dejo de tomar toda la hoja: respuesta y grupo (auditoria K2).
    assert variables("ANOVA una via") == ("c1", "c2", "alpha")
    assert not sobre_toda_la_hoja("ANOVA una via")
    assert not sobre_toda_la_hoja("Bland-Altman")
    # CMH dejo de leer la hoja entera como tablas 2x2: exposicion, evento y estrato.
    assert variables("CMH test") == ("c1", "c2", "c3")


def test_las_listas_y_los_parametros_son_de_analisis_que_existen():
    from src.ui.analysis_specs import MULTI, PARAMETROS
    real = _dispatch_real()
    assert set(MULTI) <= set(real) and set(PARAMETROS) <= set(real)
    # Una lista o unos parametros no son "toda la hoja": el dialogo los pide.
    assert not any(sobre_toda_la_hoja(a) for a in list(MULTI) + list(PARAMETROS))


def test_un_analisis_desconocido_no_pide_nada():
    assert variables("no existe") == ()
    assert sobre_toda_la_hoja("no existe")
