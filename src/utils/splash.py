"""Ventana de carga del ejecutable (PyInstaller splash), con barra de progreso.

En el .exe onefile el arranque tiene dos tramos bien distintos:

1. **Descompresion (~10 s).** El bootloader de PyInstaller saca ~150 MB a una
   carpeta temporal. Todavia no corre una sola linea de Python, asi que esta
   parte no es nuestra: el propio bootloader escribe en la linea de estado el
   nombre del archivo que esta extrayendo.
2. **Arranque de Python (~6 s).** Importar numpy/scipy/pandas/statsmodels/
   sklearn y construir los paneles de Qt. Este tramo si es nuestro, y es el que
   dibuja la barra.

La barra se arma con caracteres de bloque en la unica linea de texto que expone
el splash de PyInstaller — no hay widget de progreso disponible. Un hilo de
fondo la hace avanzar de a poco hacia el proximo hito, para que se mueva sola
mientras un import largo tiene tomado el hilo principal.

Fuera del .exe (`python main.py`) el modulo `pyi_splash` no existe: todo esto
queda en nada y nadie tiene que envolver las llamadas en try/except.
"""
import threading
import time

from src.utils import frases

try:  # pragma: no cover - solo existe dentro del ejecutable
    import pyi_splash as _splash
except ImportError:  # corriendo desde el codigo fuente
    _splash = None

# Ancho de la barra en caracteres. Medido, no estimado: con la fuente por
# defecto del splash (Arial 11, porque el spec no fija text_font) cada bloque
# ocupa 11 px, asi que 12 bloques son 132 px. La linea entera con la frase mas
# larga mide 582 px contra los 646 utiles de assets/splash.png (700 px menos el
# margen). Con 24 bloques el texto se cortaba contra el borde derecho.
ANCHO = 12

# Largo maximo del texto que acompana a la barra. Lo que no entra se recorta
# aca y no contra el borde de la ventana. Ligado a frases.LARGO_MAXIMO por
# tests/test_frases.py: si una crece sin la otra, las frases salen con "…".
MAX_MENSAJE = 62
LLENO = "█"   # bloque solido
VACIO = "░"   # bloque punteado

# Cuanto se muestra el nombre de la etapa despues de un hito, antes de volver a
# las frases. Sin esto las frases tapan la unica pista de donde se colgo el
# arranque si algo falla.
MOSTRAR_ETAPA = 0.9

# Cada cuanto cambia la frase. El tramo que dibujamos dura ~6 s, asi que con
# 1,6 s entran unas cuatro: suficiente para que se note que rota, sin que
# parpadee.
ROTACION = 1.6

_lock = threading.Lock()


def activo():
    """True si hay una ventana de carga viva."""
    return _splash is not None and _splash.is_alive()


def texto(mensaje):
    """Escribe una linea suelta en el splash. No falla si no hay splash."""
    if not activo():
        return
    try:
        with _lock:
            _splash.update_text(mensaje)
    except Exception:
        # Un splash que se rompe no puede impedir que arranque la aplicacion.
        pass


def dibujar(fraccion, mensaje=""):
    """Devuelve la barra ya renderizada. Pura: se puede probar sin GUI."""
    fraccion = min(1.0, max(0.0, float(fraccion)))
    if len(mensaje) > MAX_MENSAJE:
        mensaje = mensaje[:MAX_MENSAJE - 1] + "…"
    llenos = int(round(ANCHO * fraccion))
    barra = LLENO * llenos + VACIO * (ANCHO - llenos)
    pct = f"{int(round(fraccion * 100)):3d} %"
    return f"{barra}  {pct}  {mensaje}".rstrip()


def siguiente(actual, objetivo, cierre=0.15, paso_minimo=0.004):
    """Proximo valor de la barra: cierra una fraccion de lo que falta.

    Con paso fijo la barra no alcanzaba al hito antes de que la etapa
    terminara —quedaba en 46 % y saltaba a 100 %—. Cerrando un porcentaje de
    la distancia restante llega en algo mas de un segundo y despues se queda
    quieta, que es justo lo que se quiere: moverse mientras se espera, sin
    prometer un avance que no ocurrio.
    """
    if actual >= objetivo:
        return objetivo
    return min(objetivo, actual + max(paso_minimo, (objetivo - actual) * cierre))


class Progreso:
    """Barra que avanza sola hacia el proximo hito.

    Los hitos reales son pocos y los tramos entre ellos son largos (importar
    scipy son varios segundos con el hilo principal bloqueado). Sin el hilo de
    fondo la barra quedaria congelada justo cuando mas importa que se vea viva.
    """

    def __init__(self, cierre=0.15, paso_minimo=0.004, intervalo=0.08,
                 semilla_frases=None):
        self.actual = 0.0
        self.objetivo = 0.0
        self.mensaje = ""
        self._cierre = cierre
        self._paso_minimo = paso_minimo
        self._intervalo = intervalo
        self._fin = threading.Event()
        self._hilo = None
        # Frases barajadas al arrancar: la semilla queda expuesta para que el
        # test pueda fijar el orden.
        self._frases = frases.secuencia(semilla=semilla_frases)
        self._i_frase = 0
        self._t_frase = 0.0
        self._t_hito = 0.0

    def frase_actual(self):
        return self._frases[self._i_frase % len(self._frases)] if self._frases else ""

    def acompanamiento(self, ahora=None):
        """Que va al lado de la barra: la etapa recien marcada, o una frase.

        Justo despues de un hito manda el nombre de la etapa —es la pista de
        donde quedo si el arranque se cuelga—; pasados MOSTRAR_ETAPA segundos
        entran las frases y van rotando.
        """
        ahora = time.monotonic() if ahora is None else ahora
        if self._t_hito and ahora - self._t_hito < MOSTRAR_ETAPA:
            return self.mensaje
        if not self._frases:
            return self.mensaje
        if ahora - self._t_frase >= ROTACION:
            self._t_frase = ahora
            self._i_frase += 1
        return self.frase_actual()

    def arrancar(self):
        if not activo() or self._hilo is not None:
            return self
        self._hilo = threading.Thread(target=self._correr, daemon=True)
        self._hilo.start()
        return self

    def _correr(self):
        while not self._fin.is_set():
            # Redibuja aunque la barra no se mueva: las frases rotan solas, y
            # si solo se refrescara al avanzar, un import largo dejaria la
            # misma frase congelada varios segundos.
            if self.actual < self.objetivo:
                self.actual = siguiente(self.actual, self.objetivo,
                                        self._cierre, self._paso_minimo)
            texto(dibujar(self.actual, self.acompanamiento()))
            self._fin.wait(self._intervalo)

    def hito(self, objetivo, mensaje):
        """Marca un avance real. El hilo se encarga de llegar caminando."""
        self.mensaje = mensaje
        self.objetivo = max(self.objetivo, min(1.0, objetivo))
        self._t_hito = time.monotonic()
        if not activo():
            return
        # Un primer refresco inmediato para que el mensaje cambie ya.
        texto(dibujar(self.actual, self.mensaje))

    def terminar(self, mensaje="Listo"):
        """Completa la barra, la deja ver un instante y cierra el splash."""
        self._fin.set()
        if activo():
            self.actual = self.objetivo = 1.0
            texto(dibujar(1.0, mensaje))
            time.sleep(0.25)
        cerrar()


def cerrar():
    """Cierra el splash. Idempotente."""
    if not activo():
        return
    try:
        with _lock:
            _splash.close()
    except Exception:
        pass
