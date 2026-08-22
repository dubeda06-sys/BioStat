"""Ventana de carga del ejecutable (PyInstaller splash).

En el .exe onefile el arranque tarda porque hay que descomprimir ~150 MB antes
de que corra una sola linea de Python. El splash de PyInstaller aparece durante
esa descompresion, asi que es lo unico que se ve en ese hueco.

Fuera del .exe (`python main.py`) el modulo `pyi_splash` no existe: las tres
funciones no hacen nada y nadie tiene que envolverlas en try/except.
"""

try:  # pragma: no cover - solo existe dentro del ejecutable
    import pyi_splash as _splash
except ImportError:  # corriendo desde el codigo fuente
    _splash = None


def activo():
    """True si hay una ventana de carga viva."""
    return _splash is not None and _splash.is_alive()


def texto(mensaje):
    """Cambia la linea de estado del splash. No falla si no hay splash."""
    if not activo():
        return
    try:
        _splash.update_text(mensaje)
    except Exception:
        # Un splash que se rompe no puede impedir que arranque la aplicacion.
        pass


def cerrar():
    """Cierra el splash. Idempotente."""
    if not activo():
        return
    try:
        _splash.close()
    except Exception:
        pass
