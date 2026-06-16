"""Ventana principal de BioStat."""
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QMenuBar, QMenu,
    QToolBar, QStatusBar, QFileDialog, QMessageBox,
    QWidget, QLabel
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction

from src.ui.styles import MAIN_STYLE
from src.ui.icons import Icons
from src.ui.data_panel import DataPanel
from src.ui.analysis_panel import AnalysisPanel
from src.ui.graphs_panel import GraphsPanel
from src.ui.qc_panel import QCPanel


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
        a = QAction(f"{Icons.OPEN} Abrir", self)
        a.setShortcut("Ctrl+O")
        a.triggered.connect(self._open_file)
        fm.addAction(a)

        a = QAction(f"{Icons.SAVE} Guardar", self)
        a.setShortcut("Ctrl+S")
        a.triggered.connect(self._save_file)
        fm.addAction(a)
        fm.addSeparator()

        ex = fm.addMenu(f"{Icons.EXPORT} Exportar")
        ex.addAction(QAction("PDF", self))
        ex.addAction(QAction("Excel", self))
        ex.addAction(QAction("Word", self))
        fm.addSeparator()

        a = QAction("Salir", self)
        a.setShortcut("Ctrl+Q")
        a.triggered.connect(self.close)
        fm.addAction(a)

        mb.addMenu("  Edicion  ").addAction(QAction("Copiar", self))

        am = mb.addMenu("  Analisis  ")
        for n in ["Descriptivas", "ROC", "Bland-Altman", "Supervivencia"]:
            am.addAction(QAction(n, self))

        qm = mb.addMenu("  Control de Calidad  ")
        for n in ["Levey-Jennings", "Westgard", "Validacion"]:
            qm.addAction(QAction(n, self))

        hm = mb.addMenu("  Ayuda  ")
        about = QAction("Acerca de", self)
        about.triggered.connect(self._show_about)
        hm.addAction(about)

    def _create_toolbar(self):
        tb = QToolBar()
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(tb)

        for icon, text, tip, cb in [
            (Icons.OPEN, "Abrir", "Abrir archivo CSV o Excel", self._open_file),
            (Icons.SAVE, "Guardar", "Guardar datos en archivo", self._save_file),
        ]:
            a = QAction(f"{icon} {text}", self)
            a.setToolTip(tip)
            a.triggered.connect(cb)
            tb.addAction(a)

        tb.addSeparator()

        for icon, text in [(Icons.CSV, "CSV"), (Icons.EXCEL, "Excel")]:
            a = QAction(f"{icon} {text}", self)
            tb.addAction(a)

        tb.addSeparator()

        a = QAction(f"{Icons.RUN} Analizar", self)
        a.setToolTip("Ejecutar analisis estadistico")
        tb.addAction(a)

        a = QAction(f"{Icons.EXPORT} Exportar", self)
        a.setToolTip("Exportar resultados a PDF o Excel")
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

        tabs_config = [
            (self.data_panel, "Datos", Icons.OPEN),
            (self.analysis_panel, "Analisis", Icons.CHART),
            (self.graphs_panel, "Graficos", Icons.STATS),
            (self.qc_panel, "Control de Calidad", Icons.CHECK),
        ]
        for panel, name, icon in tabs_config:
            self.tabs.addTab(panel, f"  {icon} {name}  ")

        self.tabs.currentChanged.connect(self._on_tab_changed)

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
