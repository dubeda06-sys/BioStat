"""Aplicacion principal de BioStat."""
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow


class BioStatApp:
    def __init__(self, argv):
        self.app = QApplication(argv)
        self.app.setApplicationName("BioStat")
        self.app.setOrganizationName("BioStat")
        self.main_window = None

    def run(self):
        self.main_window = MainWindow()
        self.main_window.show()
        return self.app.exec()
