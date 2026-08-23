"""Panel de Omnianálisis — motor de decisión determinista + ventana de confirmación.

El panel esta partido en pestanas porque el informe tecnico solo no alcanzaba:

  Resumen            que se analizo, que decidio el motor, que encontro.
  Arbol de decision  el arbol dibujado, con el camino que recorrio la corrida.
  Auditoria          los 40 ensayos del catalogo, uno por uno, con su estado.
  Informe            el informe tecnico completo (el de siempre).
  Graficos           Bland-Altman y regresion de comparacion.
"""
import csv

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QTextEdit,
    QGroupBox, QSplitter, QAbstractItemView, QComboBox,
    QDialog, QDialogButtonBox, QCheckBox, QScrollArea,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
import pandas as pd
import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

from src.analysis.omni_analyzer import run_omnianalysis
from src.analysis.omni_plots import comparison_figures
from src.analysis import omni_arbol
from src.analysis.omni_caso import casos as construir_casos
from src.analysis.omni_auditoria import (
    DESCARTADO, EJECUTADO, NO_APLICA, auditar, resumen_en_una_linea,
)
from src.ui import omni_render

# Colores de fila por estado en la tabla de auditoria.
_FONDO_ESTADO = {
    EJECUTADO: QColor("#dcfce7"),
    DESCARTADO: QColor("#f1f5f9"),
    NO_APLICA: QColor("#ffffff"),
}
_FILTROS = ("Todos", "Solo ejecutados", "Solo descartados", "Solo no aplican")
_ESTADO_DE_FILTRO = {
    "Solo ejecutados": EJECUTADO,
    "Solo descartados": DESCARTADO,
    "Solo no aplican": NO_APLICA,
}


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

            pregunta = QLabel(
                "¿Alguna de las dos es el <b>método de referencia</b>? "
                "(valor asignado, consenso, material de control)"
            )
            pregunta.setStyleSheet("font-weight:normal; color:#555; font-size:12px;")
            pregunta.setWordWrap(True)
            bl.addWidget(pregunta)

            ref = QComboBox()
            ref.addItem("Ninguna — los dos son métodos pares (Bland-Altman clásico)", None)
            ref.addItem(f"{cand['col1']} es el método de referencia", cand["col1"])
            ref.addItem(f"{cand['col2']} es el método de referencia", cand["col2"])
            ref.setToolTip(
                "Con una referencia, graficar contra el promedio la mete en los dos ejes "
                "y atenúa el sesgo proporcional: el método parece mejor calibrado de lo "
                "que está (Krouwer 2008). Declarándola, el eje X pasa a ser la referencia "
                "y el informe muestra las dos pendientes para que se vea la diferencia."
            )
            bl.addWidget(ref)

            self._checks.append((cand, chk, ref))
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
        return [(c["col1"], c["col2"]) for c, chk, _ in self._checks if chk.isChecked()]

    def referencias(self) -> dict[tuple[str, str], str]:
        """{par ordenado -> columna de referencia} solo para los pares confirmados.

        La clave va ordenada porque el analizador ordena el par; el valor es el
        nombre de la columna, no "x"/"y", para que el orden no la mueva de lugar.
        """
        elegidas = {}
        for cand, chk, ref in self._checks:
            if not chk.isChecked():
                continue
            elegida = ref.currentData()
            if elegida:
                elegidas[tuple(sorted((cand["col1"], cand["col2"])))] = elegida
        return elegidas


class OmniPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._df: pd.DataFrame | None = None
        self._manual_pairs: list[tuple[str, str]] = []
        self._auditoria: dict = {}
        self._casos: list = []
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
        btn_clear.clicked.connect(self._clear)
        ll.addWidget(btn_clear)

        splitter.addWidget(left)

        # --- Derecha: pestañas ---
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            "QTabBar::tab { padding: 6px 12px; font-size: 12px; }"
            "QTabBar::tab:selected { color: #0e7490; font-weight: bold; }"
        )
        self.tabs.addTab(self._tab_resumen(), "Resumen")
        self.tabs.addTab(self._tab_arbol(), "Árbol de decisión")
        self.tabs.addTab(self._tab_auditoria(), "Auditoría")
        self.tabs.addTab(self._tab_informe(), "Informe")
        self.tabs.addTab(self._tab_graficos(), "Gráficos")
        splitter.addWidget(self.tabs)

        splitter.setSizes([260, 780])
        main.addWidget(splitter)

    # ---------- Construcción de pestañas ----------
    def _tab_resumen(self):
        self.txt_resumen = QTextEdit()
        self.txt_resumen.setReadOnly(True)
        self.txt_resumen.setStyleSheet(
            "QTextEdit { background:#ffffff; border:none; padding:10px; }"
        )
        self.txt_resumen.setPlaceholderText(
            "Cargá datos, elegí columnas y pulsá 'Ejecutar Omnianálisis'."
        )
        return self.txt_resumen

    def _tab_arbol(self):
        cont = QWidget()
        v = QVBoxLayout(cont)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)

        # Selector de vista. La vista por caso es la que sirve para confiar sin
        # saber estadistica: la general dice que corrio, la de caso dice que dio.
        barra = QHBoxLayout()
        barra.setContentsMargins(8, 6, 8, 0)
        barra.addWidget(QLabel("Ver:"))
        self.cmb_vista = QComboBox()
        self.cmb_vista.setMinimumWidth(340)
        self.cmb_vista.currentIndexChanged.connect(self._cambiar_vista)
        barra.addWidget(self.cmb_vista, stretch=1)
        v.addLayout(barra)

        self.lbl_leyenda = QLabel(omni_render.leyenda_arbol())
        self.lbl_leyenda.setWordWrap(True)
        self.lbl_leyenda.setStyleSheet(
            "padding:6px 10px; background:#f8fafc; border-bottom:1px solid #e2e8f0;")
        v.addWidget(self.lbl_leyenda)

        self.arbol_scroll = QScrollArea()
        self.arbol_scroll.setWidgetResizable(True)
        self.arbol_scroll.setStyleSheet("QScrollArea { border:none; background:#ffffff; }")
        v.addWidget(self.arbol_scroll)
        self._poner_arbol([QLabel("El árbol se dibuja al ejecutar el Omnianálisis.")])
        return cont

    def _tab_auditoria(self):
        cont = QWidget()
        v = QVBoxLayout(cont)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)

        barra = QHBoxLayout()
        barra.setContentsMargins(8, 6, 8, 0)
        self.lbl_auditoria = QLabel("Sin corrida que auditar.")
        self.lbl_auditoria.setWordWrap(True)
        self.lbl_auditoria.setStyleSheet("font-size:12px; color:#334155;")
        barra.addWidget(self.lbl_auditoria, stretch=1)

        self.cmb_filtro = QComboBox()
        self.cmb_filtro.addItems(_FILTROS)
        self.cmb_filtro.currentTextChanged.connect(self._aplicar_filtro)
        barra.addWidget(self.cmb_filtro)

        btn_csv = QPushButton("Exportar CSV")
        btn_csv.setStyleSheet(
            "QPushButton { background:#f3f5f9; border:1px solid #d8dbe3; border-radius:5px; padding:4px 10px; font-size:12px; }"
            "QPushButton:hover { background:#e8eef6; }"
        )
        btn_csv.clicked.connect(self._exportar_auditoria)
        barra.addWidget(btn_csv)
        v.addLayout(barra)

        self.tbl_auditoria = QTableWidget(0, 6)
        self.tbl_auditoria.setHorizontalHeaderLabels(
            ["Ensayo", "Etapa", "Estado", "Veces", "Dónde / por qué", "Norma"]
        )
        self.tbl_auditoria.verticalHeader().setVisible(False)
        self.tbl_auditoria.setAlternatingRowColors(False)
        self.tbl_auditoria.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_auditoria.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        cab = self.tbl_auditoria.horizontalHeader()
        cab.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        cab.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        cab.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        cab.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        cab.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.tbl_auditoria.setStyleSheet(
            "QTableWidget { font-size:12px; gridline-color:#e2e8f0; }"
            "QHeaderView::section { background:#e0f2fe; color:#0c4a6e; padding:4px; border:none; }"
        )
        v.addWidget(self.tbl_auditoria)

        pie = QLabel(
            "Pasá el cursor por el nombre de un ensayo para ver qué hace y cuándo "
            "corresponde. Descartado = el motor lo evaluó y eligió la otra rama; "
            "No aplica = los datos nunca abrieron esa rama."
        )
        pie.setWordWrap(True)
        pie.setStyleSheet("font-size:11px; color:#64748b; padding:4px 8px;")
        v.addWidget(pie)
        return cont

    def _tab_informe(self):
        self.txt_report = QTextEdit()
        self.txt_report.setReadOnly(True)
        self.txt_report.setStyleSheet(
            "QTextEdit { background: #ffffff; border: none; font-family: 'Segoe UI', sans-serif; font-size: 13px; color: #2c3e50; padding: 8px; }"
        )
        self.txt_report.setPlaceholderText(
            "Carga datos, selecciona columnas y pulsa 'Ejecutar Omnianálisis'."
        )
        return self.txt_report

    def _tab_graficos(self):
        self.plot_scroll = QScrollArea()
        self.plot_scroll.setWidgetResizable(True)
        self.plot_scroll.setStyleSheet("QScrollArea { border:none; background:#ffffff; }")
        self.plot_container = QWidget()
        self.plot_layout = QVBoxLayout(self.plot_container)
        self.plot_layout.setContentsMargins(4, 4, 4, 4)
        self.plot_scroll.setWidget(self.plot_container)
        return self.plot_scroll

    def _poner_arbol(self, widgets):
        """Reemplaza el contenido del scroll del árbol.

        `QScrollArea.setWidget` toma la propiedad y DESTRUYE el widget anterior:
        hay que sacarlo con `takeWidget` antes, o Qt revienta al tocar
        referencias viejas.
        """
        viejo = self.arbol_scroll.takeWidget()
        if viejo is not None:
            viejo.deleteLater()
        cont = QWidget()
        v = QVBoxLayout(cont)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(10)
        for w in widgets:
            v.addWidget(w)
        v.addStretch()
        self.arbol_scroll.setWidget(cont)

    # ---------- Datos ----------
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

    def _clear(self):
        self.txt_report.clear()
        self.txt_resumen.clear()
        self.tbl_auditoria.setRowCount(0)
        self.lbl_auditoria.setText("Sin corrida que auditar.")
        self._auditoria = {}
        self._casos = []
        self.cmb_vista.clear()
        self._poner_arbol([QLabel("El árbol se dibuja al ejecutar el Omnianálisis.")])

    def _run(self):
        if self._df is None:
            return
        selected = self._selected_cols()
        if not selected:
            self.txt_resumen.setHtml("<p style='color:#c0392b;'>Selecciona al menos una variable.</p>")
            self.tabs.setCurrentIndex(0)
            return

        # Primera pasada: detectar candidatos (sin concordancia)
        report = run_omnianalysis(self._df, selected, confirmed_comparisons=self._manual_pairs,
                                  target=self._target())

        # Ventana de confirmación si hay candidatos
        candidates = report.get("comparison_candidates", [])
        confirmed = list(self._manual_pairs)
        referencias = {}
        if candidates:
            dlg = ComparisonConfirmDialog(candidates, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                confirmed += dlg.confirmed_pairs()
                referencias = dlg.referencias()
            # re-correr con confirmados (aunque se cancele, corre sin concordancia)
            report = run_omnianalysis(self._df, selected, confirmed_comparisons=confirmed,
                                      target=self._target(), referencias=referencias)

        self._auditoria = auditar(report)
        self._casos = construir_casos(report)
        self.txt_resumen.setHtml(omni_render.resumen_html(report, self._auditoria))
        self.txt_report.setHtml(self._render(report))
        self._poblar_vistas()
        self._render_arbol()
        self._render_auditoria()
        self._render_plots(report)
        self.tabs.setCurrentIndex(0)

    # ---------- Árbol ----------
    VISTA_GENERAL = "Vista general — qué ensayos corrió el motor"
    VISTA_TODOS = "Todos los casos, uno tras otro"

    def _poblar_vistas(self):
        """Llena el selector: la general, todos, y después uno por caso."""
        self.cmb_vista.blockSignals(True)
        self.cmb_vista.clear()
        self.cmb_vista.addItem(self.VISTA_GENERAL)
        if self._casos:
            self.cmb_vista.addItem(self.VISTA_TODOS)
            for c in self._casos:
                self.cmb_vista.addItem(f"{c.titulo}  ·  {c.tipo}")
        self.cmb_vista.setCurrentIndex(0)
        self.cmb_vista.blockSignals(False)

    def _cambiar_vista(self, indice):
        if not self._auditoria:
            return
        if indice <= 0:
            self._render_arbol()
        elif indice == 1 and self._casos:
            self._render_casos(self._casos)
        else:
            self._render_casos([self._casos[indice - 2]])

    def _render_arbol(self):
        self.lbl_leyenda.setText(omni_render.leyenda_arbol())
        widgets = []
        resumen = QLabel(resumen_en_una_linea(self._auditoria))
        resumen.setWordWrap(True)
        resumen.setStyleSheet("font-size:12px; color:#0c4a6e; font-weight:bold;")
        widgets.append(resumen)

        pista = QLabel(
            "Para ver qué dio cada análisis y por qué se decidió así, elegí un "
            "caso en el selector de arriba."
        )
        pista.setWordWrap(True)
        pista.setStyleSheet("font-size:11px; color:#64748b;")
        widgets.append(pista)

        fig = omni_arbol.figura_resumen(self._auditoria)
        widgets.append(self._lienzo(fig, alto=int(46 * 5 + 90)))

        for _etapa, f in omni_arbol.figuras(self._auditoria):
            # Sin QLabel de titulo: la figura ya lleva el nombre de la etapa
            # dibujado, y el rotulo duplicado quedaba dos veces seguidas.
            # El alto de la figura ya viene proporcionado al layout de la etapa.
            widgets.append(self._lienzo(f, alto=int(f.get_size_inches()[1] * 96)))
        self._poner_arbol(widgets)

    def _render_casos(self, casos_a_dibujar):
        self.lbl_leyenda.setText(omni_render.leyenda_caso())
        widgets = []
        for c in casos_a_dibujar:
            f = omni_arbol.figura_caso(c)
            widgets.append(self._lienzo(f, alto=int(f.get_size_inches()[1] * 96)))
            for a in c.advertencias:
                aviso = QLabel("⚠ " + a)
                aviso.setWordWrap(True)
                aviso.setStyleSheet(
                    "background:#fef3c7; border-left:4px solid #d97706; "
                    "padding:6px 10px; color:#78350f; font-size:11px;")
                widgets.append(aviso)
        self._poner_arbol(widgets)

    @staticmethod
    def _lienzo(fig, alto):
        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(max(160, alto))
        plt.close(fig)
        return canvas

    # ---------- Auditoría ----------
    def _render_auditoria(self):
        self.lbl_auditoria.setText(resumen_en_una_linea(self._auditoria))
        self._aplicar_filtro(self.cmb_filtro.currentText())

    def _aplicar_filtro(self, texto):
        filas = (self._auditoria or {}).get("filas", [])
        estado = _ESTADO_DE_FILTRO.get(texto)
        if estado:
            filas = [f for f in filas if f["estado"] == estado]

        self.tbl_auditoria.setRowCount(len(filas))
        for i, f in enumerate(filas):
            if f["estado"] == EJECUTADO:
                donde = "; ".join(f["detalles"]) or "; ".join(f["ambitos"])
            elif f["estado"] == DESCARTADO:
                donde = "; ".join(f["motivos"])
            else:
                donde = f"Se corre cuando: {f['gatillo']}"

            celdas = [
                f["nombre"], f["etapa"], f["estado"],
                str(f["veces"]) if f["veces"] else "—",
                donde, f["norma"] or "—",
            ]
            for j, valor in enumerate(celdas):
                item = QTableWidgetItem(valor)
                item.setBackground(_FONDO_ESTADO.get(f["estado"], QColor("#ffffff")))
                if j == 0:
                    # La explicación didáctica vive en el tooltip del nombre.
                    item.setToolTip(
                        f"<b>{f['nombre']}</b><br>{f['porque']}<br><br>"
                        f"<i>Se gatilla: {f['gatillo']}</i>"
                        + (f"<br><i>Alternativa: {f['alternativa']}</i>" if f["alternativa"] else "")
                    )
                self.tbl_auditoria.setItem(i, j, item)

    def _exportar_auditoria(self):
        filas = (self._auditoria or {}).get("filas", [])
        if not filas:
            self.lbl_auditoria.setText("No hay auditoría para exportar: ejecutá el Omnianálisis primero.")
            return
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar auditoría", "auditoria_omnianalisis.csv", "CSV (*.csv)"
        )
        if not ruta:
            return
        # utf-8-sig para que Excel en Windows no rompa los acentos.
        with open(ruta, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(["id", "ensayo", "etapa", "estado", "veces",
                        "detalles", "motivos", "ambitos", "gatillo", "norma"])
            for f in filas:
                w.writerow([f["id"], f["nombre"], f["etapa"], f["estado"], f["veces"],
                            " | ".join(f["detalles"]), " | ".join(f["motivos"]),
                            " | ".join(f["ambitos"]), f["gatillo"], f["norma"]])
        self.lbl_auditoria.setText(f"Auditoría exportada a {ruta}")

    # ---------- Gráficos ----------
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
            self.txt_resumen.setHtml(
                "<p style='color:#c0392b;'>Selecciona exactamente 2 columnas para marcarlas como comparables.</p>"
            )
            self.tabs.setCurrentIndex(0)
            return
        pair = (sel[0], sel[1])
        if pair not in self._manual_pairs:
            self._manual_pairs.append(pair)
        self.txt_resumen.setHtml(
            f"<p style='color:#27ae60;'>Par marcado como comparable: "
            f"<b>{sel[0]} ↔ {sel[1]}</b>. Pulsa 'Ejecutar Omnianálisis'.</p>"
        )
        self.tabs.setCurrentIndex(0)

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
                ic = res.get("ccc_ic95")
                ic_txt = f" &nbsp;IC 95%: {ic[0]} a {ic[1]}" if ic else ""
                fuerza = res.get("ccc_fuerza")
                h += (f"<div class='result'><b>CCC (Lin):</b> {res['ccc']}{ic_txt}"
                      + (f" &nbsp;<i>({fuerza}, McBride 2005)</i>" if fuerza else "") + "</div>")
                if "ccc_rho" in res and "ccc_cb" in res:
                    h += ("<div class='result'><b>Descomposición CCC = rho &times; Cb:</b>"
                          "<table><tr><th>Componente</th><th>Valor</th><th>Qué mide</th></tr>"
                          f"<tr><td>rho</td><td>{res['ccc_rho']}</td>"
                          "<td>Precisión — dispersión frente al comparador</td></tr>"
                          f"<tr><td>Cb</td><td>{res['ccc_cb']}</td>"
                          "<td>Veracidad — componente de sesgo</td></tr>"
                          "</table></div>")
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
