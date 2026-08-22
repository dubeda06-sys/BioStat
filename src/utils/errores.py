"""Red de seguridad para excepciones que escapan de un slot de Qt.

PyQt6 aborta el proceso (`qFatal`) cuando una excepcion de Python sale de un
slot sin atrapar: el usuario hace clic en una entrada de menu o en "Ejecutar" y
la aplicacion desaparece, sin dialogo y sin nada escrito. Con 76 analisis
accesibles desde el menu, cualquier combinacion rara de columnas puede llegar
ahi.

PyQt solo aborta cuando el `sys.excepthook` es el de fabrica. Instalando uno
propio, la excepcion se muestra y el programa sigue vivo: el usuario pierde el
analisis, no la sesion de trabajo.

Esto NO reemplaza a `src/core/guards.py`. Los guards son el contrato del core
(rechazar con motivo en vez de devolver basura); esto es el ultimo colchon para
lo que igual se escape.
"""
import sys
import traceback

# Ultimo error atrapado, util para tests y para el reporte de fallas.
ultimo_error = None


def _mostrar(titulo, resumen, detalle):
    """Muestra el error en un dialogo. Si no hay GUI viva, no hace nada."""
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        if QApplication.instance() is None:
            return
        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(titulo)
        box.setText(resumen)
        box.setDetailedText(detalle)
        box.exec()
    except Exception:
        # Si hasta el dialogo falla, el programa igual tiene que seguir.
        pass


def manejar(exc_type, exc_value, exc_tb, mostrar=True):
    """Reemplazo de sys.excepthook: registra, avisa y deja la app en pie."""
    global ultimo_error
    detalle = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    ultimo_error = (exc_type, exc_value, detalle)

    # Al stderr tambien, para que quede en la consola de quien depure.
    sys.stderr.write(detalle)

    if mostrar:
        _mostrar(
            "No se pudo completar la operacion",
            f"{exc_type.__name__}: {exc_value}\n\n"
            "El analisis se cancelo, pero los datos y el resto de la sesion "
            "siguen intactos. Revisa las columnas elegidas y volve a intentar.",
            detalle,
        )


def instalar():
    """Instala el manejador. Idempotente."""
    if sys.excepthook is not manejar:
        sys.excepthook = manejar
