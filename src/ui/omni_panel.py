"""Panel de Omnianálisis — motor de decisión determinista + ventana de confirmación."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QTextEdit,
    QGroupBox, QSplitter, QAbstractItemView, QComboBox,
    QDialog, QDialogButtonBox, QCheckBox, QScrollArea,
)
from PyQt6.QtCore import Qt
import pandas as pd
import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

from src.analysis.omni_analyzer import run_omnianalysis
from src.analysis.omni_plots import comparison_figures


class ComparisonConfirmDialog(QDialog):
    """Ventana de confirmación de comparación de métodos (spec §6.2)."""

    def __init__(self, candidates: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("¿Estas columnas son mediciones de lo mismo?")
        self.setMinimumWidth(560)
        self._checks = []

        layout = QVBoxLayout(self)
        intro = QLabel(
            "El motor detectó pares que <b>podrían</b> ser mediciones comparables "
            "(dos métodos/equipos/observadores del mismo mensurando).<br>"
            "Confirmá cuáles lo son. En los confirmados corro <b>Bland-Altman, "
            "Passing-Bablok/Deming y CCC</b>. Los demás se tratan solo como correlación."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#2c3e50; font-size:13px;")
        layout.addWidget(intro)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)

        for cand in candidates:
            box = QGroupBox(f"{cand['col1']}  ↔  {cand['col2']}")
            box.setStyleSheet("QGroupBox { font-weight:bold; color:#2b579a; margin-top:6px; }")
            bl = QVBoxLayout(box)
            reasons = "<br>".join(f"• {r}" for r in cand.get("reasons", []))
            lbl = QLabel(f"Puntaje={cand['score']} | r={cand.get('corr')}<br>{reasons}")
            lbl.setStyleSheet("font-weight:normal; color:#555; font-size:12px;")
            lbl.setWordWrap(True)
            bl.addWidget(lbl)
            chk = QCheckBox("Sí, son mediciones comparables")
            chk.setChecked(True)
            bl.addWidget(chk)
            self._checks.append((cand, chk))
            inner_layout.addWidget(box)

        inner_layout.addStretch()
        scroll.setWidget(inner)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def confirmed_pairs(self) -> list[tuple[str, str]]:
        return [(c["col1"], c["col2"]) for c, chk in self._checks if chk.isChecked()]


class OmniPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._df: pd.DataFrame | None = None
        self._manual_pairs: list[tuple[str, str]] = []
        self._build_ui()

    def _build_ui(self):
        main = QHBoxLayout(self)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- Izquierda: selector ---
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(8)

        lbl = QLabel("Variables a analizar:")
        lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #2c3e50;")
        ll.addWidget(lbl)
        hint = QLabel("Ctrl+clic para selección múltiple")
        hint.setStyleSheet("font-size: 11px; color: #7f8c8d;")
        ll.addWidget(hint)

        self.list_vars = QListWidget()
        self.list_vars.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_vars.setStyleSheet(
            "QListWidget { border: 1px solid #d8dbe3; border-radius: 6px; background: #ffffff; font-size: 13px; }"
            "QListWidget::item:selected { background: #2b579a; color: white; }"
            "QListWidget::item:hover { background: #e8eef6; }"
        )
        ll.addWidget(self.list_vars)

        ll.addWidget(QLabel("Variable objetivo (regresión múltiple, opcional):"))
        self.cmb_target = QComboBox()
        self.cmb_target.setStyleSheet("QComboBox { padding:4px; border:1px solid #d8dbe3; border-radius:5px; }")
        ll.addWidget(self.cmb_target)

        self.btn_run = QPushButton("Ejecutar Omnianálisis")
        self.btn_run.setEnabled(False)
        self.btn_run.setMinimumHeight(38)
        self.btn_run.setStyleSheet(
            "QPushButton { background-color: #2b579a; color: white; border-radius: 6px; font-size: 13px; font-weight: bold; }"
            "QPushButton:hover { background-color: #1e3f73; }"
            "QPushButton:disabled { background-color: #b0bec5; }"
        )
        self.btn_run.clicked.connect(self._run)
        ll.addWidget(self.btn_run)

        self.btn_manual = QPushButton("Marcar par como comparable…")
        self.btn_manual.setMinimumHeight(32)
        self.btn_manual.setStyleSheet(
            "QPushButton { background-color: #f3f5f9; color: #2c3e50; border: 1px solid #d8dbe3; border-radius: 6px; font-size: 12px; }"
            "QPushButton:hover { background-color: #e8eef6; }"
        )
        self.btn_manual.clicked.connect(self._mark_manual)
        ll.addWidget(self.btn_manual)

        btn_clear = QPushButton("Limpiar informe")
        btn_clear.setMinimumHeight(32)
        btn_clear.setStyleSheet(self.btn_manual.styleSheet())
        btn_clear.clicked.connect(lambda: self.txt_report.clear())
        ll.addWidget(btn_clear)

        splitter.addWidget(left)

        # --- Derecha: informe ---
        right = QGroupBox("Informe de Omnianálisis")
        right.setStyleSheet(
            "QGroupBox { font-weight: bold; font-size: 13px; color: #2c3e50; border: 1px solid #d8dbe3; border-radius: 8px; margin-top: 6px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }"
        )
        rl = QVBoxLayout(right)
        self.txt_report = QTextEdit()
        self.txt_report.setReadOnly(True)
        self.txt_report.setStyleSheet(
            "QTextEdit { background: #ffffff; border: none; font-family: 'Segoe UI', sans-serif; font-size: 13px; color: #2c3e50; padding: 8px; }"
        )
        self.txt_report.setPlaceholderText(
            "Carga datos, selecciona columnas y pulsa 'Ejecutar Omnianálisis'."
        )
        rl_split = QSplitter(Qt.Orientation.Vertical)
        rl_split.addWidget(self.txt_report)
        # Área de gráficos de comparación (Bland-Altman / Passing-Bablok / Deming)
        self.plot_scroll = QScrollArea()
        self.plot_scroll.setWidgetResizable(True)
        self.plot_container = QWidget()
        self.plot_layout = QVBoxLayout(self.plot_container)
        self.plot_layout.setContentsMargins(4, 4, 4, 4)
        self.plot_scroll.setWidget(self.plot_container)
        rl_split.addWidget(self.plot_scroll)
        rl_split.setSizes([520, 360])
        rl.addWidget(rl_split)
        splitter.addWidget(right)

        splitter.setSizes([280, 720])
        main.addWidget(splitter)

    def set_data(self, df: pd.DataFrame):
        self._df = df
        self._manual_pairs = []
        self.list_vars.clear()
        self.cmb_target.clear()
        self.cmb_target.addItem("(ninguna)")
        for col in df.columns:
            self.list_vars.addItem(QListWidgetItem(col))
            self.cmb_target.addItem(col)
        self.btn_run.setEnabled(True)

    def _selected_cols(self) -> list[str]:
        return [item.text() for item in self.list_vars.selectedItems()]

    def _target(self):
        t = self.cmb_target.currentText()
        return None if t == "(ninguna)" else t

    def _run(self):
        if self._df is None:
            return
        selected = self._selected_cols()
        if not selected:
            self.txt_report.setHtml("<p style='color:#c0392b;'>Selecciona al menos una variable.</p>")
            return

        # Primera pasada: detectar candidatos (sin concordancia)
        report = run_omnianalysis(self._df, selected, confirmed_comparisons=self._manual_pairs,
                                  target=self._target())

        # Ventana de confirmación si hay candidatos
        candidates = report.get("comparison_candidates", [])
        confirmed = list(self._manual_pairs)
        if candidates:
            dlg = ComparisonConfirmDialog(candidates, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                confirmed += dlg.confirmed_pairs()
            # re-correr con confirmados (aunque se cancele, corre sin concordancia)
            report = run_omnianalysis(self._df, selected, confirmed_comparisons=confirmed,
                                      target=self._target())

        self.txt_report.setHtml(self._render(report))
        self._render_plots(report)

    def _render_plots(self, report):
        """Pinta los gráficos de comparación (Bland-Altman + regresión) por cada
        bloque de concordancia con datos de plot."""
        while self.plot_layout.count():
            item = self.plot_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
        n_plots = 0
        for b in report.get("blocks", []):
            if b.get("tipo") != "concordancia":
                continue
            pdata = b.get("resultados", {}).get("_plot")
            if not pdata:
                continue
            title = QLabel(b.get("titulo", ""))
            title.setStyleSheet("font-weight:bold; color:#0e7490; padding:8px 2px 2px;")
            self.plot_layout.addWidget(title)
            for _name, fig in comparison_figures(pdata):
                canvas = FigureCanvas(fig)
                canvas.setMinimumHeight(330)
                self.plot_layout.addWidget(canvas)
                plt.close(fig)
                n_plots += 1
        if n_plots == 0:
            hint = QLabel("Los gráficos de comparación (Bland-Altman / Passing-Bablok / "
                          "Deming) aparecen aquí al confirmar un par de métodos comparables.")
            hint.setWordWrap(True)
            hint.setStyleSheet("color:#64748b; padding:10px;")
            self.plot_layout.addWidget(hint)
        self.plot_layout.addStretch()

    def _mark_manual(self):
        """Marca manualmente 2 columnas seleccionadas como comparables."""
        sel = self._selected_cols()
        if len(sel) != 2:
            self.txt_report.setHtml(
                "<p style='color:#c0392b;'>Selecciona exactamente 2 columnas para marcarlas como comparables.</p>"
            )
            return
        pair = (sel[0], sel[1])
        if pair not in self._manual_pairs:
            self._manual_pairs.append(pair)
        self.txt_report.setHtml(
            f"<p style='color:#27ae60;'>Par marcado como comparable: "
            f"<b>{sel[0]} ↔ {sel[1]}</b>. Pulsa 'Ejecutar Omnianálisis'.</p>"
        )

    # ---------- Render HTML ----------
    def _render(self, report: dict) -> str:
        if "error" in report:
            return f"<p style='color:#c0392b;'>{report['error']}</p>"

        css = (
            "<style>"
            "body{font-family:'Segoe UI',sans-serif;color:#2c3e50;}"
            "h2{color:#2b579a;border-bottom:2px solid #2b579a;padding-bottom:4px;}"
            "h3{color:#34495e;margin:6px 0 2px;}"
            ".badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:bold;}"
            ".num{background:#e8f4fd;color:#2b579a;}.cat{background:#fef9e7;color:#b7950b;}"
            ".cmp{background:#eafaf1;color:#1e8449;}.conc{background:#fdedec;color:#c0392b;}"
            ".step{color:#7f8c8d;font-size:12px;margin:1px 0;}"
            ".warn{background:#fef5e7;border-left:4px solid #e67e22;padding:6px 10px;margin:4px 0;color:#8a5a00;border-radius:0 4px 4px 0;}"
            ".result{background:#f3f5f9;border-left:4px solid #2b579a;padding:6px 10px;margin:6px 0;border-radius:0 6px 6px 0;}"
            ".sig{color:#27ae60;font-weight:bold;}.nosig{color:#c0392b;}"
            "table{border-collapse:collapse;width:100%;margin:6px 0;font-size:12px;}"
            "th{background:#2b579a;color:white;padding:4px 8px;}td{padding:4px 8px;border-bottom:1px solid #e0e0e0;}"
            "tr:nth-child(even){background:#f3f5f9;}"
            "</style>"
        )
        h = css

        # --- Perfilado ---
        p = report["profile"]
        h += f"<h2>Perfilado (Rama {report['branch']})</h2>"
        h += (f"<p>{p['n_rows']} filas · {p['n_columns']} columnas · "
              f"estructura: {p['shape']} · duplicados: {p['full_duplicates']}</p>")
        h += "<table><tr><th>Columna</th><th>Tipo</th><th>n válidos</th><th>Únicos</th><th>% nulos</th></tr>"
        for c, info in p["col_types"].items():
            nota = f" <span style='color:#e67e22;'>({info['nota']})</span>" if info.get("nota") else ""
            h += (f"<tr><td>{c}{nota}</td><td>{info['tipo']}</td><td>{info['n_valid']}</td>"
                  f"<td>{info['n_unique']}</td><td>{info['pct_null']}%</td></tr>")
        h += "</table>"

        for w in report.get("warnings_globales", []):
            h += f"<div class='warn'>⚠ {w}</div>"

        # --- Bloques ---
        for b in report["blocks"]:
            tipo = b.get("tipo", "")
            badge_cls = ("conc" if tipo == "concordancia" else
                         "cmp" if tipo in ("comparación de grupos", "correlación", "tabla de contingencia") else
                         "cat" if "categórica" in tipo else "num")
            h += f"<h2>{b['titulo']} <span class='badge {badge_cls}'>{tipo}</span></h2>"

            res = b.get("resultados", {})
            if "descriptivos" in res:
                d = res["descriptivos"]
                h += (f"<table><tr><th>n</th><th>Media</th><th>DS</th><th>Mediana</th>"
                      f"<th>Min</th><th>Max</th><th>IC95%</th></tr>"
                      f"<tr><td>{d.get('n')}</td><td>{d.get('mean')}</td><td>{d.get('std')}</td>"
                      f"<td>{d.get('median')}</td><td>{d.get('min')}</td><td>{d.get('max')}</td>"
                      f"<td>{d.get('ci95')}</td></tr></table>")
            if "tendencia_central" in res:
                h += f"<div class='result'><b>Tendencia central:</b> {res['tendencia_central']}</div>"
            if "frecuencias" in res:
                h += "<table><tr><th>Categoría</th><th>n</th><th>%</th></tr>"
                for cat, v in res["frecuencias"].items():
                    h += f"<tr><td>{cat}</td><td>{v['n']}</td><td>{v['%']}%</td></tr>"
                h += "</table>"

            if b.get("traza"):
                h += "<h3>Árbol de decisión (trazabilidad):</h3>"
                for step in b["traza"]:
                    h += f"<p class='step'>▶ {step}</p>"

            for pr in b.get("pruebas", []):
                sig_cls = "sig" if pr.get("significativo") else "nosig"
                sig_txt = "Significativo ✓" if pr.get("significativo") else "No significativo ✗"
                extras = " ".join(f"{k}={v}" for k, v in pr.items()
                                  if k not in ("prueba", "significativo"))
                h += f"<div class='result'><b>{pr['prueba']}</b> — {extras} — <span class='{sig_cls}'>{sig_txt}</span></div>"

            # Concordancia — sub-resultados
            if "bland_altman" in res:
                h += f"<div class='result'><b>Bland-Altman ({res['bland_altman']['tipo']}):</b> {res['bland_altman']}</div>"
            if "regresion" in res:
                h += f"<div class='result'><b>Regresión de comparación:</b> {res['regresion']}</div>"
            if "sesgo_en_niveles" in res:
                h += ("<div class='result'><b>Sesgo en niveles de decisión (CLSI EP09):</b>"
                      "<table><tr><th>Nivel (X)</th><th>Sesgo absoluto</th><th>Sesgo %</th></tr>")
                for s in res["sesgo_en_niveles"]:
                    h += (f"<tr><td>{s['nivel']}</td><td>{s['sesgo_abs']}</td>"
                          f"<td>{s['sesgo_pct'] if s['sesgo_pct'] is not None else '—'}</td></tr>")
                h += "</table></div>"
            if "ccc" in res:
                h += f"<div class='result'><b>CCC (Lin):</b> {res['ccc']}</div>"
            if "posthoc" in res:
                ph = res["posthoc"]
                h += f"<div class='result'><b>Post-hoc {ph.get('metodo','')}:</b> "
                if "comparaciones" in ph:
                    for cmp_ in ph["comparaciones"]:
                        cls = "sig" if cmp_["significativo"] else "nosig"
                        h += f"<br><span class='{cls}'>{cmp_['par']}: p_adj={cmp_['p_adj']}</span>"
                elif "resumen" in ph:
                    h += f"<pre style='font-size:11px;'>{ph['resumen']}</pre>"
                h += "</div>"

            for w in b.get("advertencias", []):
                h += f"<div class='warn'>⚠ {w}</div>"

            if b.get("conclusion"):
                h += f"<p><b>Conclusión:</b> {b['conclusion']}</p>"
            h += "<hr style='border:none;border-top:1px solid #e0e0e0;margin:12px 0;'>"

        # --- Matriz de correlación (Rama C) ---
        if "correlation_matrix" in report:
            cm = report["correlation_matrix"]
            h += "<h2>Matriz de correlación (método por celda + FDR)</h2>"
            h += "<table><tr><th>Par</th><th>Método</th><th>Coef</th><th>p</th><th>p ajustado (BH)</th></tr>"
            for c in cm["celdas"]:
                cls = "sig" if c.get("significativo_adj") else "nosig"
                h += (f"<tr><td>{c['par']}</td><td>{c['metodo']}</td><td>{c['coef']}</td>"
                      f"<td>{c['p']}</td><td class='{cls}'>{c.get('p_adj')}</td></tr>")
            h += "</table>"

        # --- PCA / clustering exploratorio ---
        if "pca_clustering" in report:
            pc = report["pca_clustering"]
            h += "<h2>PCA + Clustering (exploratorio)</h2>"
            if "error" in pc:
                h += f"<div class='warn'>⚠ {pc['error']}</div>"
            else:
                h += (f"<div class='result'><b>PCA:</b> componentes para 90% varianza = "
                      f"{pc['pca']['componentes_para_90pct']}<br>"
                      f"Varianza explicada (5 primeras): {pc['pca']['varianza_explicada']}<br>"
                      f"Acumulada: {pc['pca']['varianza_acumulada']}</div>")
                cl = pc["clustering"]
                h += (f"<div class='result'><b>{cl['metodo']}:</b> k óptimo={cl['k_optimo']}, "
                      f"silueta={cl['silhouette']}<br><i>{cl['nota']}</i></div>")

        # --- Regresión múltiple ---
        if "multiple_regression" in report:
            mr = report["multiple_regression"]
            h += "<h2>Regresión múltiple</h2>"
            if "error" in mr:
                h += f"<div class='warn'>⚠ {mr['error']}</div>"
            else:
                h += (f"<div class='result'>Objetivo: <b>{mr['target']}</b> · R²={mr['r2']} "
                      f"(ajustado {mr['r2_adj']}) · p(F)={mr['f_p']}<br>"
                      f"Coeficientes: {mr['coef']}<br>p-valores: {mr['coef_p']}<br>"
                      f"VIF: {mr['vif']}<br>{mr['diagnostico']}</div>")

        return h
