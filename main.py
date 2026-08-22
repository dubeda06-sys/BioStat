"""BioStat - Software estadistico para laboratorio clinico."""
import sys

from src.utils import splash

splash.texto("Cargando modulos cientificos...")
from src.app import BioStatApp  # noqa: E402  (despues del aviso al splash)

if __name__ == "__main__":
    splash.texto("Preparando la interfaz...")
    app = BioStatApp(sys.argv)
    sys.exit(app.run())
