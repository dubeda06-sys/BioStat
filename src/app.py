"""Aplicacion principal de BioStat."""
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.utils import errores, splash


class BioStatApp:
    def __init__(self, argv, progreso=None):
        self.app = QApplication(argv)
        self.app.setApplicationName("BioStat")
        self.app.setOrganizationName("BioStat")
        # PyQt aborta el proceso si una excepcion sale de un slot; con esto la
        # aplicacion avisa y sigue viva. Ver src/utils/errores.py.
        errores.instalar()
        # Barra del splash; si se construye la app sin una (tests, scripts),
        # una vacia que no hace nada alcanza.
        self.progreso = progreso or splash.Progreso()
        self.main_window = None

    def run(self):
        self.progreso.hito(0.85, "Construyendo paneles")
        self.main_window = MainWindow()
        self.progreso.hito(0.95, "Abriendo ventana")
        self.main_window.show()
        # La ventana ya esta pintada: recien ahi se completa la barra y se
        # retira el splash, para no dejar un hueco sin nada en pantalla.
        self.app.processEvents()
        self.progreso.terminar()
        return self.app.exec()
