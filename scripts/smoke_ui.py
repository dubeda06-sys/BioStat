"""Smoke harness: ejecuta cada entrada del dispatch de AnalysisPanel con datos
de ejemplo y reporta excepciones, clasificando bug-de-codigo vs forma-de-datos."""
import os, sys, traceback
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import numpy as np
import pandas as pd

# Raiz del repo: argv[1] o el directorio padre de scripts/
REPO = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO)

from PyQt6.QtWidgets import QApplication
from src.ui.analysis_panel import AnalysisPanel

app = QApplication([])

rng = np.random.RandomState(0)
n = 40
df = pd.DataFrame({
    "A": rng.normal(10, 2, n),
    "B": rng.normal(11, 2, n),
    "C": rng.normal(9, 3, n),
    "bin01": rng.randint(0, 2, n).astype(float),
    "grp": rng.randint(0, 3, n).astype(float),
    "pos": rng.uniform(1, 5, n),
})

panel = AnalysisPanel()
panel.set_data(df)

# obtener las claves del dispatch sin ejecutar: parsear desde _run via introspeccion
# Ejecutamos _run para cada texto del combo.
keys = [panel.combo_analysis.itemText(i) for i in range(panel.combo_analysis.count())]

CODE_BUGS = (KeyError, AttributeError, NameError, TypeError, IndexError, UnboundLocalError)

results = []
for k in keys:
    panel.combo_analysis.setCurrentText(k)
    # set sensible column defaults
    try:
        panel.combo_col1.setCurrentText("A")
        panel.combo_col2.setCurrentText("B")
        panel.combo_col3.setCurrentText("bin01")
    except Exception:
        pass
    try:
        panel.txt_results.clear()
        panel._run()
        h = panel.txt_results.toPlainText() or ""
        if "Error en " in h:
            # _run_core swallowed exception
            results.append((k, "CODE_BUG:swallowed", h.replace("\n", " ")[:200]))
        else:
            results.append((k, "OK", ""))
    except Exception as e:
        cls = type(e).__name__
        kind = "CODE_BUG" if isinstance(e, CODE_BUGS) else "data/other"
        tb = traceback.format_exc().splitlines()
        loc = next((l.strip() for l in reversed(tb) if "analysis_panel" in l or "/core/" in l or "\\core\\" in l), "")
        results.append((k, f"{kind}:{cls}", f"{e} | {loc}"))

print(f"total={len(keys)}")
bugs = [r for r in results if r[1].startswith("CODE_BUG")]
data = [r for r in results if r[1].startswith("data")]
ok = [r for r in results if r[1] == "OK"]
print(f"OK={len(ok)}  CODE_BUG={len(bugs)}  data/other={len(data)}")
print("\n=== CODE BUGS ===")
for k, s, m in bugs:
    print(f"  [{s}] {k}\n      {m}")
print("\n=== data/other (revisar manualmente) ===")
for k, s, m in data:
    print(f"  [{s}] {k}: {m[:120]}")
