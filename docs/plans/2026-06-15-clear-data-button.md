# Clear Data Button Implementation Plan

**Goal:** Add a "Clear Data" button to reset the data panel and disconnect all analysis panels.

**Architecture:** Add button to toolbar and data panel. When clicked, clear the DataFrame, reset table view, and notify all panels to clear their state.

**Tech Stack:** Python, PyQt6, pandas

---

## File Structure

- Modify: `src/ui/main_window.py` - Add button to toolbar
- Modify: `src/ui/data_panel.py` - Add clear method and button
- Modify: `src/ui/analysis_panel.py` - Add clear method
- Modify: `src/ui/graphs_panel.py` - Add clear method
- Modify: `src/ui/qc_panel.py` - Add clear method
- Create: `tests/test_clear_data.py` - Tests for clear functionality

---

### Task 1: Add clear method to DataPanel

**Files:**
- Modify: `src/ui/data_panel.py`
- Create: `tests/test_clear_data.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_clear_data.py
import pytest
from src.ui.data_panel import DataPanel
import pandas as pd

def test_data_panel_clear():
    panel = DataPanel()
    # Load some data first
    test_data = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
    panel.set_data(test_data)
    assert panel.get_data() is not None
    
    # Clear the data
    panel.clear_data()
    
    # Verify data is cleared
    assert panel.get_data() is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_clear_data.py::test_data_panel_clear -v`
Expected: FAIL with "AttributeError: 'DataPanel' object has no attribute 'clear_data'"

- [ ] **Step 3: Write minimal implementation**

```python
# In src/ui/data_panel.py, add method:
def clear_data(self):
    """Clear all data from the panel."""
    self._data = None
    self.table.clearContents()
    self.table.setRowCount(0)
    self.stats_label.setText("Sin datos cargados")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_clear_data.py::test_data_panel_clear -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ui/data_panel.py tests/test_clear_data.py
git commit -m "feat: add clear_data method to DataPanel"
```

---

### Task 2: Add clear methods to analysis panels

**Files:**
- Modify: `src/ui/analysis_panel.py`
- Modify: `src/ui/graphs_panel.py`
- Modify: `src/ui/qc_panel.py`

- [ ] **Step 1: Write the failing tests**

```python
# Add to tests/test_clear_data.py
def test_analysis_panel_clear():
    from src.ui.analysis_panel import AnalysisPanel
    panel = AnalysisPanel()
    # Panel should have clear method
    assert hasattr(panel, 'clear_results')
    # Should not raise
    panel.clear_results()

def test_graphs_panel_clear():
    from src.ui.graphs_panel import GraphsPanel
    panel = GraphsPanel()
    assert hasattr(panel, 'clear_graphs')
    panel.clear_graphs()

def test_qc_panel_clear():
    from src.ui.qc_panel import QCPanel
    panel = QCPanel()
    assert hasattr(panel, 'clear_qc')
    panel.clear_qc()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_clear_data.py -v`
Expected: FAIL with "AttributeError" for each panel

- [ ] **Step 3: Write minimal implementation**

```python
# In src/ui/analysis_panel.py:
def clear_results(self):
    """Clear analysis results."""
    self.results_text.clear()
    self.formula_text.clear()

# In src/ui/graphs_panel.py:
def clear_graphs(self):
    """Clear all graphs."""
    self.graph_area.clear()

# In src/ui/qc_panel.py:
def clear_qc(self):
    """Clear QC results."""
    self.qc_results.clear()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_clear_data.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/ui/analysis_panel.py src/ui/graphs_panel.py src/ui/qc_panel.py tests/test_clear_data.py
git commit -m "feat: add clear methods to all panels"
```

---

### Task 3: Add Clear button to toolbar and wire up

**Files:**
- Modify: `src/ui/main_window.py`

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/test_clear_data.py
def test_main_window_has_clear_button():
    from src.ui.main_window import MainWindow
    window = MainWindow()
    # Find clear button in toolbar
    toolbar = window.findChild(QToolBar)
    actions = toolbar.actions()
    clear_found = any("Limpiar" in (a.text() or "") for a in actions)
    assert clear_found, "Clear button not found in toolbar"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_clear_data.py::test_main_window_has_clear_button -v`
Expected: FAIL with "AssertionError: Clear button not found"

- [ ] **Step 3: Write minimal implementation**

```python
# In src/ui/main_window.py, in _create_toolbar method, add:
a = QAction(f"{Icons.CLEAR} Limpiar", self)
a.setToolTip("Limpiar todos los datos y resultados")
a.triggered.connect(self._clear_all)
tb.addAction(a)

# Add new method:
def _clear_all(self):
    """Clear all data and results from all panels."""
    self.data_panel.clear_data()
    self.analysis_panel.clear_results()
    self.graphs_panel.clear_graphs()
    self.qc_panel.clear_qc()
    self.statusBar().showMessage("Datos y resultados limpiados")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_clear_data.py::test_main_window_has_clear_button -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ui/main_window.py tests/test_clear_data.py
git commit -m "feat: add Clear button to toolbar, wire up to all panels"
```

---

## Self-Review

1. **Spec coverage:** ✅ Clear button added, all panels clear, tests verify
2. **Placeholder scan:** ✅ No TBD/TODO, all code complete
3. **Type consistency:** ✅ clear_data(), clear_results(), clear_graphs(), clear_qc() all consistent

## Verification

After all tasks:
```bash
pytest tests/test_clear_data.py -v
# Expected: 4/4 PASS

python src/main.py
# Manual: Click "Limpiar" button, verify all panels clear
```