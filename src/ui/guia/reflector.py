"""Reflector: oscurece la ventana y deja iluminado un control, con una burbuja.

Sirve para "mostrame dónde": en vez de describir dónde está un botón, se lo
señala. Un click en cualquier lugar (o Esc) lo cierra.
"""
from PyQt6.QtCore import QEvent, QPoint, QRect, QRectF, Qt, QVariantAnimation
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

_ANCHO_BURBUJA = 320


class Reflector(QWidget):
    def __init__(self, ventana: QWidget):
        super().__init__(ventana)
        self._ventana = ventana
        self._hueco = QRect()
        self._titulo = ""
        self._texto = ""
        self._color = QColor("#0e7490")
        self._pulso = 0.0
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.hide()
        ventana.installEventFilter(self)

        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(1100)
        self._anim.setLoopCount(-1)
        self._anim.valueChanged.connect(self._latir)

    # ---------- API ----------
    def mostrar(self, objetivo, titulo: str, texto: str, color: str = "#0e7490"):
        """`objetivo` es un QWidget (o un QRect en coordenadas de la ventana)."""
        if isinstance(objetivo, QWidget):
            if not objetivo.isVisible():
                return False
            origen = objetivo.mapTo(self._ventana, QPoint(0, 0))
            rect = QRect(origen, objetivo.size())
        else:
            rect = QRect(objetivo)
        self._hueco = rect.adjusted(-6, -6, 6, 6)
        self._titulo, self._texto = titulo, texto
        self._color = QColor(color)
        self.setGeometry(self._ventana.rect())
        self.show()
        self.raise_()
        self.setFocus()
        self._anim.start()
        return True

    def ocultar(self):
        self._anim.stop()
        self.hide()

    # ---------- eventos ----------
    def eventFilter(self, obj, ev):
        if obj is self._ventana and ev.type() == QEvent.Type.Resize and self.isVisible():
            self.ocultar()  # el control cambió de lugar: mejor cerrar que señalar mal
        return False

    def mousePressEvent(self, ev):
        self.ocultar()

    def keyPressEvent(self, ev):
        self.ocultar()

    def _latir(self, v):
        self._pulso = float(v)
        self.update()

    # ---------- dibujo ----------
    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        hueco = QRectF(self._hueco)

        velo = QPainterPath()
        velo.addRect(QRectF(self.rect()))
        agujero = QPainterPath()
        agujero.addRoundedRect(hueco, 10, 10)
        p.fillPath(velo.subtracted(agujero), QColor(15, 23, 42, 155))

        # anillo que late
        for i, alfa in ((0, 255), (1, 90)):
            c = QColor(self._color)
            c.setAlpha(int(alfa * (1 - 0.6 * self._pulso)) if i else alfa)
            p.setPen(QPen(c, 3 if i == 0 else 3 + 8 * self._pulso))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(hueco.adjusted(-i * 4 * self._pulso, -i * 4 * self._pulso,
                                             i * 4 * self._pulso, i * 4 * self._pulso), 10, 10)
        self._burbuja(p, hueco)

    def _burbuja(self, p, hueco):
        ft = QFont("Segoe UI", 11, QFont.Weight.Bold)
        fx = QFont("Segoe UI", 10)
        fp = QFont("Segoe UI", 8)
        ancho_txt = _ANCHO_BURBUJA - 28
        h_t = QFontMetrics(ft).boundingRect(0, 0, ancho_txt, 400,
                                            int(Qt.TextFlag.TextWordWrap), self._titulo).height()
        h_x = QFontMetrics(fx).boundingRect(0, 0, ancho_txt, 800,
                                            int(Qt.TextFlag.TextWordWrap), self._texto).height()
        alto = 16 + h_t + 6 + h_x + 10 + 14 + 14

        # debajo del hueco si entra; si no, arriba; alineada y dentro de la ventana
        x = max(12, min(hueco.left(), self.width() - _ANCHO_BURBUJA - 12))
        y = hueco.bottom() + 14
        if y + alto > self.height() - 12:
            y = max(12, hueco.top() - 14 - alto)
        caja = QRectF(x, y, _ANCHO_BURBUJA, alto)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 60))
        p.drawRoundedRect(caja.translated(0, 3), 12, 12)
        p.setBrush(QColor("#ffffff"))
        p.setPen(QPen(self._color, 2))
        p.drawRoundedRect(caja, 12, 12)

        p.setPen(QColor("#0f172a"))
        p.setFont(ft)
        p.drawText(QRectF(x + 14, y + 14, ancho_txt, h_t), int(Qt.TextFlag.TextWordWrap),
                   self._titulo)
        p.setPen(QColor("#334155"))
        p.setFont(fx)
        p.drawText(QRectF(x + 14, y + 14 + h_t + 6, ancho_txt, h_x),
                   int(Qt.TextFlag.TextWordWrap), self._texto)
        p.setPen(QColor("#94a3b8"))
        p.setFont(fp)
        p.drawText(QRectF(x + 14, caja.bottom() - 22, ancho_txt, 14),
                   int(Qt.AlignmentFlag.AlignLeft), "Click en cualquier lugar para seguir")
