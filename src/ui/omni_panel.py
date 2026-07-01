"""Panel de Omnianálisis — sistema experto estadístico automático."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QTextEdit,
    QGroupBox, QSplitter, QAbstractItemView,
)
from PyQt6.QtCore import Qt
import pandas as pd

from src.analysis.omni_analyzer import run_omnianalysis


class OmniPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._df: pd.DataFrame | None = None
        self._build_ui()

    def _build_ui(self):
        main = QHBoxLayout(self)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- Panel izquierdo: selector de variables ---
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        lbl = QLabel("Variables a analizar:")
        lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #2c3e50;")
        left_layout.addWidget(lbl)

        hint = QLabel("Ctrl+clic para selección múltiple")
        hint.setStyleSheet("font-size: 11px; color: #7f8c8d;")
        left_layout.addWidget(hint)

        self.list_vars = QListWidget()
        self.list_vars.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_vars.setStyleSheet(
            "QListWidget { border: 1px solid #d8dbe3; border-radius: 6px; "
            "background: #ffffff; font-size: 13px; }"
            "QListWidget::item:selected { background: #2b579a; color: white; }"
            "QListWidget::item:hover { background: #e8eef6; }"
        )
        left_layout.addWidget(self.list_vars)

        self.btn_run = QPushButton("Ejecutar Omnianálisis")
        self.btn_run.setEnabled(False)
        self.btn_run.setMinimumHeight(38)
        self.btn_run.setStyleSheet(
            "QPushButton { background-color: #2b579a; color: white; border-radius: 6px; "
            "font-size: 13px; font-weight: bold; }"
            "QPushButton:hover { background-color: #1e3f73; }"
            "QPushButton:disabled { background-color: #b0bec5; }"
        )
        self.btn_run.clicked.connect(self._run)
        left_layout.addWidget(self.btn_run)

        btn_clear = QPushButton("Limpiar informe")
        btn_clear.setMinimumHeight(32)
        btn_clear.setStyleSheet(
            "QPushButton { background-color: #f3f5f9; color: #2c3e50; border: 1px solid #d8dbe3; "
            "border-radius: 6px; font-size: 12px; }"
            "QPushButton:hover { background-color: #e8eef6; }"
        )
        btn_clear.clicked.connect(self._clear)
        left_layout.addWidget(btn_clear)

        splitter.addWidget(left)

        # --- Panel derecho: informe ---
        right = QGroupBox("Informe de Omnianálisis")
        right.setStyleSheet(
            "QGroupBox { font-weight: bold; font-size: 13px; color: #2c3e50; "
            "border: 1px solid #d8dbe3; border-radius: 8px; margin-top: 6px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }"
        )
        right_layout = QVBoxLayout(right)
        self.txt_report = QTextEdit()
        self.txt_report.setReadOnly(True)
        self.txt_report.setStyleSheet(
            "QTextEdit { background: #ffffff; border: none; font-family: 'Segoe UI', sans-serif; "
            "font-size: 13px; color: #2c3e50; padding: 8px; }"
        )
        self.txt_report.setPlaceholderText(
            "Carga datos, selecciona columnas y pulsa 'Ejecutar Omnianálisis'."
        )
        right_layout.addWidget(self.txt_report)
        splitter.addWidget(right)

        splitter.setSizes([260, 740])
        main.addWidget(splitter)

    def set_data(self, df: pd.DataFrame):
        self._df = df
        self.list_vars.clear()
        for col in df.columns:
            self.list_vars.addItem(QListWidgetItem(col))
        self.btn_run.setEnabled(True)

    def _run(self):
        if self._df is None:
            return
        selected = [item.text() for item in self.list_vars.selectedItems()]
        if not selected:
            self.txt_report.setHtml(
                "<p style='color:#c0392b;'>Selecciona al menos una variable.</p>"
            )
            return

        results = run_omnianalysis(self._df, selected)
        self.txt_report.setHtml(self._render_html(results))

    def _render_html(self, results: list[dict]) -> str:
        css = (
            "<style>"
            "body { font-family: 'Segoe UI', sans-serif; color: #2c3e50; }"
            "h2 { color: #2b579a; border-bottom: 2px solid #2b579a; padding-bottom: 4px; }"
            "h3 { color: #34495e; margin-bottom: 4px; }"
            ".badge { display:inline-block; padding:2px 8px; border-radius:10px; "
            "font-size:11px; font-weight:bold; }"
            ".num { background:#e8f4fd; color:#2b579a; }"
            ".cat { background:#fef9e7; color:#b7950b; }"
            ".cmp { background:#eafaf1; color:#1e8449; }"
            ".step { color:#7f8c8d; font-size:12px; margin:2px 0; }"
            ".result { background:#f3f5f9; border-left:4px solid #2b579a; "
            "padding:8px 12px; margin:8px 0; border-radius:0 6px 6px 0; }"
            ".sig { color:#27ae60; font-weight:bold; }"
            ".nosig { color:#c0392b; }"
            "table { border-collapse:collapse; width:100%; margin:8px 0; }"
            "th { background:#2b579a; color:white; padding:4px 8px; }"
            "td { padding:4px 8px; border-bottom:1px solid #e0e0e0; }"
            "tr:nth-child(even) { background:#f3f5f9; }"
            "</style>"
        )
        body = ""

        for r in results:
            if "error" in r:
                body += f"<p style='color:#c0392b;'>{r['error']}</p>"
                continue

            tipo = r.get("tipo", "")
            col = r.get("columna", "")

            if tipo == "numérica continua" or tipo == "prueba 1 grupo":
                badge = f"<span class='badge num'>Numérica</span>"
                body += f"<h2>{col} {badge}</h2>"
                if "descriptivos" in r:
                    d = r["descriptivos"]
                    body += (
                        f"<table><tr><th>n</th><th>Media</th><th>DE</th><th>Mediana</th>"
                        f"<th>Min</th><th>Max</th><th>IC 95%</th></tr>"
                        f"<tr><td>{d.get('n','')}</td><td>{d.get('media','')}</td>"
                        f"<td>{d.get('DE','')}</td><td>{d.get('mediana','')}</td>"
                        f"<td>{d.get('min','')}</td><td>{d.get('max','')}</td>"
                        f"<td>{d.get('IC95','')}</td></tr></table>"
                    )

            elif tipo == "categórica":
                badge = f"<span class='badge cat'>Categórica</span>"
                body += f"<h2>{col} {badge}</h2>"
                if "frecuencias" in r:
                    body += "<table><tr><th>Categoría</th><th>n</th><th>%</th></tr>"
                    for cat, vals in r["frecuencias"].items():
                        body += f"<tr><td>{cat}</td><td>{vals['n']}</td><td>{vals['%']}%</td></tr>"
                    body += "</table>"

            elif tipo in ("comparación 2 grupos", "tabla de contingencia"):
                badge = f"<span class='badge cmp'>Comparación</span>"
                body += f"<h2>{tipo.title()} {badge}</h2>"

            # Pasos del árbol de decisión
            if r.get("pasos"):
                body += "<h3>Árbol de decisión:</h3>"
                for step in r["pasos"]:
                    body += f"<p class='step'>▶ {step}</p>"

            # Pruebas realizadas
            for pr in r.get("pruebas", []):
                sig_class = "sig" if pr.get("significativo") else "nosig"
                sig_text = "Significativo ✓" if pr.get("significativo") else "No significativo ✗"
                est = pr.get("estadístico", "")
                p_val = pr.get("p", "")
                gl = f", gl={pr['gl']}" if "gl" in pr else ""
                body += (
                    f"<div class='result'>"
                    f"<b>{pr['prueba']}</b>{f': estadístico={est}' if est != '' else ''}"
                    f"{gl}, p={p_val} — "
                    f"<span class='{sig_class}'>{sig_text}</span></div>"
                )

            # Conclusión
            if r.get("conclusion"):
                body += f"<p><b>Conclusión:</b> {r['conclusion']}</p>"

            body += "<hr style='border:none;border-top:1px solid #e0e0e0;margin:16px 0;'>"

        return css + body

    def _clear(self):
        self.txt_report.clear()
