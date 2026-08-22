"""`analysis_specs.VARIABLES` tiene que seguir al dispatch real.

La tabla se genero leyendo el `dispatch` de `AnalysisPanel._run`. Si manana
alguien agrega un analisis o le cambia los argumentos y no toca la tabla, el
dialogo va a pedir las variables equivocadas — o no pedir ninguna — sin que
nada falle. Este test vuelve a leer el dispatch del archivo fuente y compara.
"""
import io
import re
from pathlib import Path

from src.ui.analysis_specs import VARIABLES, sobre_toda_la_hoja, variables
from src.ui.help_text import ANALYSIS_HELP

FUENTE = Path(__file__).resolve().parents[1] / "src" / "ui" / "analysis_panel.py"


def _dispatch_real():
    """Relee el dispatch de AnalysisPanel._run y deduce que usa cada analisis."""
    s = io.open(FUENTE, encoding="utf-8").read()
    i = s.index("dispatch = {")
    j = s.index("}\n        fn = dispatch.get(at)")
    cuerpo = s[i:j]

    encontrado = {}
    for nombre, expr in re.findall(r'"([^"]+)":\s*lambda:\s*(.+?),\n', cuerpo):
        usadas = tuple(v for v in ("c1", "c2", "c3", "alpha")
                       if re.search(r"\b" + v + r"\b", expr))
        encontrado[nombre] = usadas
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
    # ANOVA una via solo consume alpha: sigue trabajando sobre toda la hoja.
    assert variables("ANOVA una via") == ("alpha",)
    assert sobre_toda_la_hoja("ANOVA una via")
    assert not sobre_toda_la_hoja("Bland-Altman")


def test_un_analisis_desconocido_no_pide_nada():
    assert variables("no existe") == ()
    assert sobre_toda_la_hoja("no existe")
