"""Aplicacion principal de BioStat."""
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.utils import splash


class BioStatApp:
    def __init__(self, argv):
        self.app = QApplication(argv)
        self.app.setApplicationName("BioStat")
        self.app.setOrganizationName("BioStat")
        self.main_window = None

    def run(self):
        splash.texto("Construyendo los paneles...")
        self.main_window = MainWindow()
        self.main_window.show()
        # La ventana ya esta pintada: recien ahi se retira el splash, para que
        # no quede un hueco sin nada en pantalla.
        self.app.processEvents()
        splash.cerrar()
        return self.app.exec()
