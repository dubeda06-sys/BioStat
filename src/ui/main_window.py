"""Ventana principal de BioStat."""
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget,
    QToolBar, QStatusBar, QFileDialog, QMessageBox, QApplication,
    QLabel, QWidget, QSizePolicy,
)
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QAction

from src.ui.styles import MAIN_STYLE
from src.ui.icons import Icons
from src.ui.data_panel import DataPanel
from src.ui.analysis_panel import AnalysisPanel
from src.ui.graphs_panel import GraphsPanel
from src.ui.qc_panel import QCPanel
from src.ui.omni_panel import OmniPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BioStat")
        self.setMinimumSize(1200, 750)
        self.resize(1350, 850)
        self.setStyleSheet(MAIN_STYLE)
        self._create_menu_bar()
        self._create_toolbar()
        self._create_status_bar()
        self._create_central_widget()

    def _create_menu_bar(self):
        mb = self.menuBar()

        fm = mb.addMenu("  Archivo  ")
        a = QAction("Abrir", self)
        a.setIcon(Icons.OPEN())
        a.setShortcut("Ctrl+O")
        a.triggered.connect(self._open_file)
        fm.addAction(a)

        a = QAction("Guardar", self)
        a.setIcon(Icons.SAVE())
        a.setShortcut("Ctrl+S")
        a.triggered.connect(self._save_file)
        fm.addAction(a)
        fm.addSeparator()

        ex = fm.addMenu("Exportar")
        a = QAction("CSV", self)
        a.triggered.connect(self._export_csv)
        ex.addAction(a)
        a = QAction("Excel", self)
        a.triggered.connect(self._export_excel)
        ex.addAction(a)
        a = QAction("HTML (Resultados)", self)
        a.triggered.connect(self._export_html)
        ex.addAction(a)
        fm.addSeparator()

        a = QAction("Salir", self)
        a.setShortcut("Ctrl+Q")
        a.triggered.connect(self.close)
        fm.addAction(a)

        em = mb.addMenu("Edicion")
        copy = QAction("Copiar resultados", self)
        copy.setShortcut("Ctrl+C")
        copy.triggered.connect(self._copy_results)
        em.addAction(copy)

        am = mb.addMenu("Analisis")
        analisis_map = {
            "Descriptivas": "Estadisticas descriptivas",
            "ROC": "Curva ROC",
            "Bland-Altman": "Bland-Altman",
            "Supervivencia": "Kaplan-Meier",
        }
        for label, combo_text in analisis_map.items():
            act = QAction(label, self)
            act.triggered.connect(lambda _checked, t=combo_text: self._goto_analysis(t))
            am.addAction(act)

        qm = mb.addMenu("Control de Calidad")
        for n in ["Levey-Jennings", "Westgard", "Validacion"]:
            act = QAction(n, self)
            act.triggered.connect(lambda _checked, t=n: self._goto_qc(t))
            qm.addAction(act)

        hm = mb.addMenu("Ayuda")
        about = QAction("Acerca de", self)
        about.triggered.connect(self._show_about)
        hm.addAction(about)

    def _create_toolbar(self):
        tb = QToolBar()
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(tb)

        # Marca de la app a la izquierda de la toolbar
        brand = QLabel("  BioStat ")
        brand.setStyleSheet("font-size:15px; font-weight:800; color:#0e7490; padding:0 8px;")
        tb.addWidget(brand)
        tag = QLabel("Lab Statistics ")
        tag.setStyleSheet("font-size:11px; color:#94a3b8; padding-top:3px;")
        tb.addWidget(tag)
        tb.addSeparator()

        # Open button with SVG icon
        a = QAction(Icons.OPEN(), "Abrir", self)
        a.setToolTip("Abrir archivo CSV o Excel (Ctrl+O)")
        a.setShortcut("Ctrl+O")
        a.triggered.connect(self._open_file)
        tb.addAction(a)

        # Save button with SVG icon
        a = QAction(Icons.SAVE(), "Guardar", self)
        a.setToolTip("Guardar datos en archivo (Ctrl+S)")
        a.setShortcut("Ctrl+S")
        a.triggered.connect(self._save_file)
        tb.addAction(a)

        tb.addSeparator()

        # CSV button with SVG icon
        a = QAction(Icons.CSV(), "CSV", self)
        a.setToolTip("Exportar datos a CSV (Ctrl+E)")
        a.setShortcut("Ctrl+E")
        a.triggered.connect(self._export_csv)
        tb.addAction(a)

        # Excel button with SVG icon
        a = QAction(Icons.EXCEL(), "Excel", self)
        a.setToolTip("Exportar datos a Excel (Ctrl+Shift+E)")
        a.setShortcut("Ctrl+Shift+E")
        a.triggered.connect(self._export_excel)
        tb.addAction(a)

        tb.addSeparator()

        # Run button with SVG icon
        a = QAction(Icons.RUN(), "Analizar", self)
        a.setToolTip("Ejecutar análisis estadístico (Ctrl+R)")
        a.setShortcut("Ctrl+R")
        a.triggered.connect(self._run_analysis)
        tb.addAction(a)

        # Export button with SVG icon
        a = QAction(Icons.EXPORT(), "Exportar", self)
        a.setToolTip("Exportar resultados a HTML (Ctrl+Shift+X)")
        a.setShortcut("Ctrl+Shift+X")
        a.triggered.connect(self._export_html)
        tb.addAction(a)

    def _create_status_bar(self):
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("BioStat listo — Importa datos o ingresa manualmente para comenzar")

    def _create_central_widget(self):
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.setCentralWidget(self.tabs)

        self.data_panel = DataPanel()
        self.analysis_panel = AnalysisPanel()
        self.graphs_panel = GraphsPanel()
        self.qc_panel = QCPanel()
        self.omni_panel = OmniPanel()

        tabs_config = [
            (self.data_panel, "Datos"),
            (self.analysis_panel, "Analisis"),
            (self.graphs_panel, "Graficos"),
            (self.qc_panel, "Control de Calidad"),
            (self.omni_panel, "Omnianálisis"),
        ]
        for panel, name in tabs_config:
            self.tabs.addTab(panel, name)

        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.data_panel.dataChanged.connect(self._on_data_changed)

    def _on_data_changed(self, data):
        """Propaga los datos a todos los paneles al importar/limpiar, sin esperar
        a cambiar de pestaña."""
        if data is None:
            return
        self.analysis_panel.set_data(data)
        self.graphs_panel.set_data(data)
        self.qc_panel.set_data(data)

    def _on_tab_changed(self, index):
        data = self.data_panel.get_data()
        if data is None:
            return
        if index == 1:
            self.analysis_panel.set_data(data)
        elif index == 2:
            self.graphs_panel.set_data(data)
        elif index == 3:
            self.qc_panel.set_data(data)
        elif index == 4:
            self.omni_panel.set_data(data)

    def _run_analysis(self):
        """Ejecuta el analisis seleccionado: empuja datos y cambia a la pestaña Análisis."""
        data = self.data_panel.get_data()
        if data is None:
            QMessageBox.warning(self, "Sin datos", "Importa o ingresa datos antes de analizar.")
            self.tabs.setCurrentIndex(0)
            return
        self.analysis_panel.set_data(data)
        self.tabs.setCurrentIndex(1)
        self.analysis_panel._run()

    def _goto_analysis(self, combo_text):
        """Va al panel Análisis, selecciona el análisis y lo ejecuta."""
        data = self.data_panel.get_data()
        if data is None:
            QMessageBox.warning(self, "Sin datos", "Importa o ingresa datos antes de analizar.")
            self.tabs.setCurrentIndex(0)
            return
        self.analysis_panel.set_data(data)
        self.tabs.setCurrentIndex(1)
        idx = self.analysis_panel.combo_analysis.findText(combo_text)
        if idx >= 0:
            self.analysis_panel.combo_analysis.setCurrentIndex(idx)
        self.analysis_panel._run()

    def _goto_qc(self, combo_text):
        """Va al panel Control de Calidad y selecciona el análisis QC."""
        data = self.data_panel.get_data()
        if data is not None:
            self.qc_panel.set_data(data)
        self.tabs.setCurrentIndex(3)
        idx = self.qc_panel.combo_qc.findText(combo_text)
        if idx >= 0:
            self.qc_panel.combo_qc.setCurrentIndex(idx)

    def _copy_results(self):
        """Copia el texto de resultados del análisis al portapapeles."""
        txt = self.analysis_panel.txt_results.toPlainText()
        if txt.strip():
            QApplication.clipboard().setText(txt)
            self.statusBar().showMessage("Resultados copiados al portapapeles")
        else:
            self.statusBar().showMessage("No hay resultados para copiar")

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir", "", "Datos (*.csv *.xlsx *.xls);;Todos (*)"
        )
        if path:
            self.data_panel.load_file(path)
            name = path.split("/")[-1].split("\\")[-1]
            self.statusBar().showMessage(f"Cargado: {name}")
            self.tabs.setCurrentIndex(0)

    def _save_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar", "", "CSV (*.csv);;Excel (*.xlsx);;Todos (*)"
        )
        if path:
            data = self.data_panel.get_data()
            if data is not None:
                if path.endswith(".csv"):
                    data.to_csv(path, index=False)
                else:
                    data.to_excel(path, index=False)
                self.statusBar().showMessage(f"Guardado: {path.split('/')[-1]}")

    def _show_about(self):
        QMessageBox.about(
            self, "Acerca de BioStat",
            "<h2>BioStat v0.1.0</h2>"
            "<p>Software estadistico para laboratorio clinico.</p>"
            "<p>Permite importar datos, realizar analisis estadisticos, "
            "generar graficos y control de calidad.</p>"
        )

    def _export_csv(self):
        """Export data to CSV."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar CSV", "", "CSV (*.csv)"
        )
        if path:
            data = self.data_panel.get_data()
            if data is not None:
                data.to_csv(path, index=False)
                self.statusBar().showMessage(f"CSV exportado: {path.split('/')[-1]}")
            else:
                QMessageBox.warning(self, "Error", "No hay datos para exportar.")

    def _export_excel(self):
        """Export data to Excel."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Excel", "", "Excel (*.xlsx)"
        )
        if path:
            data = self.data_panel.get_data()
            if data is not None:
                data.to_excel(path, index=False, engine='openpyxl')
                self.statusBar().showMessage(f"Excel exportado: {path.split('/')[-1]}")
            else:
                QMessageBox.warning(self, "Error", "No hay datos para exportar.")

    def _export_html(self):
        """Export results to HTML."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar HTML", "", "HTML (*.html)"
        )
        if path:
            from src.core.export import export_results_to_html
            results = self.analysis_panel.txt_results.toHtml()
            html = export_results_to_html({'Resultados': results}, "Informe BioStat")
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)
            self.statusBar().showMessage(f"HTML exportado: {path.split('/')[-1]}")
