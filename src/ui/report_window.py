"""Ventana de informe: un analisis, una ventana que queda abierta.

En MedCalc cada procedimiento abre su propia ventana de resultados y las
ventanas se acumulan, asi se comparan dos analisis lado a lado y se imprime
cada uno por separado. El panel Analisis, en cambio, sobrescribe el resultado
anterior en cuanto se corre otra cosa.

La ventana recibe el HTML ya armado y, si lo hubo, el grafico. No calcula nada:
`AnalysisPanel` sigue siendo quien corre el analisis.
"""
from PyQt6.QtGui import QTextDocument
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QMainWindow, QMessageBox,
    QPushButton, QScrollArea, QSplitter, QTextEdit, QVBoxLayout, QWidget,
)
from PyQt6.QtCore import Qt

# Las ventanas se guardan aca para que no las junte el recolector de basura
# apenas la funcion que las creo termina.
_abiertas = []


class VentanaInforme(QMainWindow):
    def __init__(self, titulo, html, canvas=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{titulo} — BioStat")
        self.resize(860, 620)
        self._html = html

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        divisor = QSplitter(Qt.Orientation.Vertical)

        self.txt = QTextEdit()
        self.txt.setReadOnly(True)
        self.txt.setHtml(html)
        divisor.addWidget(self.txt)

        if canvas is not None:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            canvas.setParent(None)
            scroll.setWidget(canvas)
            divisor.addWidget(scroll)
            divisor.setStretchFactor(0, 2)
            divisor.setStretchFactor(1, 3)
            # Reparto inicial: el informe necesita alto para leerse sin scroll.
            divisor.setSizes([300, 340])

        layout.addWidget(divisor)

        barra = QHBoxLayout()
        barra.setSpacing(6)
        for texto, slot in [("Copiar", self._copiar), ("Guardar...", self._guardar),
                            ("Imprimir...", self._imprimir), ("Cerrar", self.close)]:
            boton = QPushButton(texto)
            boton.clicked.connect(slot)
            barra.addWidget(boton)
        barra.addStretch()
        layout.addLayout(barra)

        self.setCentralWidget(central)

    def _copiar(self):
        QApplication.clipboard().setText(self.txt.toPlainText())
        self.statusBar().showMessage("Informe copiado al portapapeles", 3000)

    def _guardar(self):
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar informe", "", "HTML (*.html);;Texto (*.txt)")
        if not ruta:
            return
        contenido = self._html if ruta.lower().endswith(".html") else self.txt.toPlainText()
        try:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(contenido)
        except OSError as e:
            QMessageBox.warning(self, "No se pudo guardar", str(e))
            return
        self.statusBar().showMessage(f"Guardado en {ruta}", 5000)

    def _imprimir(self):
        impresora = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialogo = QPrintDialog(impresora, self)
        if dialogo.exec() != QPrintDialog.DialogCode.Accepted:
            return
        documento = QTextDocument()
        documento.setHtml(self._html)
        documento.print(impresora)

    def closeEvent(self, evento):
        if self in _abiertas:
            _abiertas.remove(self)
        super().closeEvent(evento)


def abrir(titulo, html, canvas=None, parent=None):
    """Abre una ventana de informe y la deja viva."""
    ventana = VentanaInforme(titulo, html, canvas, parent)
    _abiertas.append(ventana)
    ventana.show()
    return ventana


def abiertas():
    """Ventanas de informe vivas. Para el menu Ventana y para los tests."""
    return list(_abiertas)


def cerrar_todas():
    for ventana in list(_abiertas):
        ventana.close()
