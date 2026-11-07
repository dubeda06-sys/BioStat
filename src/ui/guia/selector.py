"""Selector de modo para la barra de herramientas (botones tipo píldora)."""
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout, QLabel, QToolButton, QWidget

from src.ui.guia.modos import INFO_MODOS, Modo


class SelectorModo(QWidget):
    modoCambiado = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 0, 6, 0)
        lay.setSpacing(0)
        rot = QLabel("Modo:")
        rot.setStyleSheet("color:#5b6573; font-size:12px; padding-right:6px;")
        lay.addWidget(rot)
        self._grupo = QButtonGroup(self)
        self._grupo.setExclusive(True)
        self._botones = {}
        modos = list(INFO_MODOS)
        for i, modo in enumerate(modos):
            info = INFO_MODOS[modo]
            b = QToolButton()
            b.setText(info["nombre"])
            b.setCheckable(True)
            b.setToolTip(f"{info['lema']}\nIdeal si: {info['para']}")
            izq = "8px" if i == 0 else "0"
            der = "8px" if i == len(modos) - 1 else "0"
            b.setStyleSheet(
                f"QToolButton {{ background:white; color:#334155; border:1px solid #c3cad3; "
                f"border-left:{'1px solid #c3cad3' if i == 0 else 'none'}; padding:4px 12px; "
                f"font-size:12px; border-top-left-radius:{izq}; border-bottom-left-radius:{izq}; "
                f"border-top-right-radius:{der}; border-bottom-right-radius:{der}; }}"
                f"QToolButton:hover {{ background:{info['suave']}; }}"
                f"QToolButton:checked {{ background:{info['color']}; color:white; "
                f"font-weight:bold; border-color:{info['color']}; }}")
            self._grupo.addButton(b)
            self._botones[modo] = b
            b.clicked.connect(lambda _=False, m=modo: self.modoCambiado.emit(m.value))
            lay.addWidget(b)

    def set_modo(self, modo):
        b = self._botones.get(Modo(modo))
        if b is not None and not b.isChecked():
            b.setChecked(True)

    def boton(self, modo) -> QToolButton:
        return self._botones[Modo(modo)]
