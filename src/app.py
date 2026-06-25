"""Aplicacion principal de BioStat."""
from __future__ import annotations
from typing import Any
import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QCoreApplication
from src.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class BioStatApp:
    """Clase principal de la aplicacion BioStat."""
    
    def __init__(self, argv: list[str]) -> None:
        """Inicializa la aplicacion.
        
        Args:
            argv: Argumentos de linea de comandos.
        """
        self.app = QApplication(argv)
        self.app.setApplicationName("BioStat")
        self.app.setOrganizationName("BioStat")
        self.app.setApplicationVersion("0.1.0")
        self.main_window: MainWindow | None = None
        
    def run(self) -> int:
        """Ejecuta la aplicacion.
        
        Returns:
            Codigo de salida de la aplicacion.
        """
        try:
            self.main_window = MainWindow()
            self.main_window.show()
            return self.app.exec()
        except Exception as e:
            logger.error(f"Error al ejecutar la aplicacion: {e}", exc_info=True)
            return 1
        finally:
            self.cleanup()
    
    def cleanup(self) -> None:
        """Limpia recursos de la aplicacion."""
        if self.main_window is not None:
            try:
                self.main_window.close()
                self.main_window.deleteLater()
            except Exception as e:
                logger.warning(f"Error al limpiar ventana principal: {e}")
