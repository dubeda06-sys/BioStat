"""Ventana principal de BioStat."""
from __future__ import annotations
from typing import Any, TYPE_CHECKING
import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget,
    QToolBar, QStatusBar, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import QSize, pyqtSlot
from PyQt6.QtGui import QAction

from src.ui.styles import MAIN_STYLE
from src.ui.icons import Icons
from src.ui.data_panel import DataPanel
from src.ui.analysis_panel import AnalysisPanel
from src.ui.graphs_panel import GraphsPanel
from src.ui.qc_panel import QCPanel

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Ventana principal de la aplicacion BioStat."""
    
    def __init__(self) -> None:
        """Inicializa la ventana principal."""
        super().__init__()
        self.setWindowTitle("BioStat")
        self.setMinimumSize(1200, 750)
        self.resize(1350, 850)
        self.setStyleSheet(MAIN_STYLE)
        
        # Paneles principales
        self.data_panel: DataPanel | None = None
        self.analysis_panel: AnalysisPanel | None = None
        self.graphs_panel: GraphsPanel | None = None
        self.qc_panel: QCPanel | None = None
        self.tabs: QTabWidget | None = None
        
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

        mb.addMenu("Edicion").addAction(QAction("Copiar", self))

        am = mb.addMenu("Analisis")
        for n in ["Descriptivas", "ROC", "Bland-Altman", "Supervivencia"]:
            am.addAction(QAction(n, self))

        qm = mb.addMenu("Control de Calidad")
        for n in ["Levey-Jennings", "Westgard", "Validacion"]:
            qm.addAction(QAction(n, self))

        hm = mb.addMenu("Ayuda")
        about = QAction("Acerca de", self)
        about.triggered.connect(self._show_about)
        hm.addAction(about)

    def _create_toolbar(self):
        tb = QToolBar()
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(tb)

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
        tb.addAction(a)

        # Excel button with SVG icon
        a = QAction(Icons.EXCEL(), "Excel", self)
        a.setToolTip("Exportar datos a Excel (Ctrl+Shift+E)")
        a.setShortcut("Ctrl+Shift+E")
        tb.addAction(a)

        tb.addSeparator()

        # Run button with SVG icon
        a = QAction(Icons.RUN(), "Analizar", self)
        a.setToolTip("Ejecutar análisis estadístico (Ctrl+R)")
        a.setShortcut("Ctrl+R")
        tb.addAction(a)

        # Export button with SVG icon
        a = QAction(Icons.EXPORT(), "Exportar", self)
        a.setToolTip("Exportar resultados (Ctrl+Shift+X)")
        a.setShortcut("Ctrl+Shift+X")
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
            (self.data_panel, "Datos"),
            (self.analysis_panel, "Analisis"),
            (self.graphs_panel, "Graficos"),
            (self.qc_panel, "Control de Calidad"),
        ]
        for panel, name in tabs_config:
            self.tabs.addTab(panel, name)

        self.tabs.currentChanged.connect(self._on_tab_changed)

    @pyqtSlot(int)
    def _on_tab_changed(self, index: int) -> None:
        """Maneja el cambio de tab en la interfaz.
        
        Args:
            index: Indice del tab seleccionado.
        """
        if self.data_panel is None:
            return
            
        data = self.data_panel.get_data()
        if data is None:
            return
            
        if index == 1 and self.analysis_panel is not None:
            self.analysis_panel.set_data(data)
        elif index == 2 and self.graphs_panel is not None:
            self.graphs_panel.set_data(data)
        elif index == 3 and self.qc_panel is not None:
            self.qc_panel.set_data(data)

    def _open_file(self) -> None:
        """Abre un archivo de datos (CSV o Excel)."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir", "", "Datos (*.csv *.xlsx *.xls);;Todos (*)"
        )
        if path and self.data_panel is not None:
            self.data_panel.load_file(path)
            name = Path(path).name
            self.statusBar().showMessage(f"Cargado: {name}")
            if self.tabs is not None:
                self.tabs.setCurrentIndex(0)

    def _save_file(self) -> None:
        """Guarda los datos actuales en un archivo."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar", "", "CSV (*.csv);;Excel (*.xlsx);;Todos (*)"
        )
        if path and self.data_panel is not None:
            data = self.data_panel.get_data()
            if data is not None:
                try:
                    if path.endswith(".csv"):
                        data.to_csv(path, index=False)
                    else:
                        data.to_excel(path, index=False)
                    self.statusBar().showMessage(f"Guardado: {Path(path).name}")
                except Exception as e:
                    logger.error(f"Error al guardar archivo: {e}")
                    QMessageBox.critical(self, "Error", f"No se pudo guardar el archivo: {e}")

    def _show_about(self) -> None:
        """Muestra el dialogo Acerca de."""
        QMessageBox.about(
            self, "Acerca de BioStat",
            "<h2>BioStat v0.1.0</h2>"
            "<p>Software estadistico para laboratorio clinico.</p>"
            "<p>Permite importar datos, realizar analisis estadisticos, "
            "generar graficos y control de calidad.</p>"
        )

    def _export_csv(self) -> None:
        """Exporta los datos a formato CSV."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar CSV", "", "CSV (*.csv)"
        )
        if path and self.data_panel is not None:
            data = self.data_panel.get_data()
            if data is not None:
                try:
                    data.to_csv(path, index=False)
                    self.statusBar().showMessage(f"CSV exportado: {Path(path).name}")
                except Exception as e:
                    logger.error(f"Error al exportar CSV: {e}")
                    QMessageBox.critical(self, "Error", f"No se pudo exportar el archivo: {e}")
            else:
                QMessageBox.warning(self, "Error", "No hay datos para exportar.")

    def _export_excel(self) -> None:
        """Exporta los datos a formato Excel."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Excel", "", "Excel (*.xlsx)"
        )
        if path and self.data_panel is not None:
            data = self.data_panel.get_data()
            if data is not None:
                try:
                    data.to_excel(path, index=False, engine='openpyxl')
                    self.statusBar().showMessage(f"Excel exportado: {Path(path).name}")
                except Exception as e:
                    logger.error(f"Error al exportar Excel: {e}")
                    QMessageBox.critical(self, "Error", f"No se pudo exportar el archivo: {e}")
            else:
                QMessageBox.warning(self, "Error", "No hay datos para exportar.")

    def _export_html(self) -> None:
        """Exporta los resultados a formato HTML."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar HTML", "", "HTML (*.html)"
        )
        if path and self.analysis_panel is not None:
            try:
                from src.core.export import export_results_to_html
                results = self.analysis_panel.txt_results.toHtml()
                html = export_results_to_html({'Resultados': results}, "Informe BioStat")
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(html)
                self.statusBar().showMessage(f"HTML exportado: {Path(path).name}")
            except Exception as e:
                logger.error(f"Error al exportar HTML: {e}")
                QMessageBox.critical(self, "Error", f"No se pudo exportar el archivo HTML: {e}")
