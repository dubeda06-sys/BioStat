"""BioStat - Software estadistico para laboratorio clinico."""
from __future__ import annotations
import sys
import logging
from src.app import BioStatApp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

if __name__ == "__main__":
    app = BioStatApp(sys.argv)
    sys.exit(app.run())
