"""BioStat - Software estadistico para laboratorio clinico."""
import sys
from src.app import BioStatApp

if __name__ == "__main__":
    app = BioStatApp(sys.argv)
    sys.exit(app.run())
