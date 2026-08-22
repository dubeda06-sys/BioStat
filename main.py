"""BioStat - Software estadistico para laboratorio clinico."""
import sys

from src.utils import splash

# La barra arranca apenas corre Python, o sea recien terminada la
# descompresion del onefile. Los imports cientificos son el tramo mas largo que
# queda, asi que el hilo la hace avanzar mientras se cargan.
progreso = splash.Progreso().arrancar()
progreso.hito(0.55, "Cargando modulos")

from src.app import BioStatApp  # noqa: E402  (despues de arrancar la barra)

if __name__ == "__main__":
    progreso.hito(0.70, "Preparando interfaz")
    app = BioStatApp(sys.argv, progreso)
    sys.exit(app.run())
