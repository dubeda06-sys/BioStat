"""Árbol de decisión interactivo (QGraphicsView).

Dibuja el camino de un `Caso` (de src.analysis.omni_caso) como nodos gráficos
conectados por flechas, en vez de una imagen estática de matplotlib. Es
interactivo: zoom con la rueda, arrastre para desplazar, y al pasar el mouse por
un nodo se muestra en el panel lateral **el cálculo realizado** (la `medicion`
del paso: con qué se contestó y qué dio), además de la consecuencia y la
alternativa que el motor habría tomado.

No requiere QtWebEngine: todo es QGraphicsScene nativo.
"""
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsItem, QTextBrowser, QPushButton, QLabel, QSplitter,
)
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QPainterPath, QPolygonF
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal

# Paleta (coherente con el resto del panel: verde = supuesto cumplido,
# ámbar = no cumplido / se tomó la rama alternativa, azul = veredicto).
_OK = QColor("#16a34a")
_WARN = QColor("#d97706")
_HEAD = QColor("#0369a1")
_VERD = QColor("#1d4ed8")
_BG = QColor("#ffffff")
_BG_HOVER = QColor("#eff6ff")
_INK = QColor("#1e293b")
_SUB = QColor("#475569")
_EDGE = QColor("#94a3b8")

_ANCHO = 320
_PAD = 14
_GAP = 78  # espacio vertical entre nodos (flecha + etiqueta)


class _Nodo(QGraphicsItem):
    """Un nodo del árbol: pinta su propia caja y texto, y avisa al hover."""

    def __init__(self, titulo, subtitulo, acento, datos, on_hover):
        super().__init__()
        self._titulo = titulo
        self._subtitulo = subtitulo
        self._acento = acento
        self._datos = datos
        self._on_hover = on_hover
        self._hover = False
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self._alto = self._calcular_alto()

    # -- geometría --
    def _fuentes(self):
        ft = QFont("Segoe UI", 10, QFont.Weight.DemiBold)
        fs = QFont("Segoe UI", 9)
        return ft, fs

    def _calcular_alto(self):
        from PyQt6.QtGui import QFontMetrics
        ft, fs = self._fuentes()
        ancho_txt = _ANCHO - 2 * _PAD
        rt = QFontMetrics(ft).boundingRect(
            0, 0, ancho_txt, 1000,
            int(Qt.TextFlag.TextWordWrap), self._titulo)
        alto = _PAD + rt.height()
        if self._subtitulo:
            rs = QFontMetrics(fs).boundingRect(
                0, 0, ancho_txt, 1000,
                int(Qt.TextFlag.TextWordWrap), self._subtitulo)
            alto += 6 + rs.height()
        return max(54, alto + _PAD)

    def boundingRect(self):
        return QRectF(0, 0, _ANCHO, self._alto)

    # -- pintura --
    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(1, 1, _ANCHO - 2, self._alto - 2)
        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)
        painter.fillPath(path, QBrush(_BG_HOVER if self._hover else _BG))
        pen = QPen(self._acento, 3 if self._hover else 2)
        painter.setPen(pen)
        painter.drawPath(path)
        # franja de acento a la izquierda
        franja = QPainterPath()
        franja.addRoundedRect(QRectF(1, 1, 7, self._alto - 2), 3, 3)
        painter.fillPath(franja, QBrush(self._acento))

        ft, fs = self._fuentes()
        ancho_txt = _ANCHO - 2 * _PAD
        painter.setPen(QPen(_INK))
        painter.setFont(ft)
        rt = QRectF(_PAD, _PAD - 4, ancho_txt, self._alto)
        painter.drawText(rt, int(Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft),
                         self._titulo)
        if self._subtitulo:
            from PyQt6.QtGui import QFontMetrics
            h_t = QFontMetrics(ft).boundingRect(
                0, 0, ancho_txt, 1000, int(Qt.TextFlag.TextWordWrap), self._titulo).height()
            painter.setPen(QPen(_SUB))
            painter.setFont(fs)
            rs = QRectF(_PAD, _PAD - 4 + h_t + 6, ancho_txt, self._alto)
            painter.drawText(rs, int(Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft),
                             self._subtitulo)

    # -- interacción --
    def hoverEnterEvent(self, event):
        self._hover = True
        self.update()
        if self._on_hover and self._datos is not None:
            self._on_hover(self._datos)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hover = False
        self.update()
        super().hoverLeaveEvent(event)


class _Vista(QGraphicsView):
    """QGraphicsView con zoom por rueda y arrastre para desplazar."""

    def __init__(self, escena):
        super().__init__(escena)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setStyleSheet("QGraphicsView { background:#f8fafc; border:none; }")
        self._zoom = 1.0

    def wheelEvent(self, event):
        f = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        nuevo = self._zoom * f
        if 0.25 <= nuevo <= 3.0:
            self._zoom = nuevo
            self.scale(f, f)


class ArbolInteractivoWidget(QWidget):
    """Panel: a la izquierda el árbol interactivo, a la derecha el detalle del
    nodo bajo el mouse (con el cálculo realizado)."""

    seleccionado = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._escena = QGraphicsScene(self)
        self._vista = _Vista(self._escena)

        self._detalle = QTextBrowser()
        self._detalle.setOpenExternalLinks(False)
        self._detalle.setStyleSheet(
            "QTextBrowser { background:#ffffff; border:1px solid #e2e8f0; "
            "border-radius:8px; padding:10px; font-family:'Segoe UI'; font-size:12px; }")
        self._detalle.setHtml(self._detalle_vacio())

        barra = QHBoxLayout()
        barra.setContentsMargins(0, 0, 0, 0)
        self._lbl = QLabel("")
        self._lbl.setStyleSheet("font-size:12px; color:#0c4a6e; font-weight:bold;")
        barra.addWidget(self._lbl, stretch=1)
        btn_fit = QPushButton("Ajustar")
        btn_fit.setToolTip("Encuadra todo el árbol en la vista")
        btn_fit.clicked.connect(self._ajustar)
        barra.addWidget(btn_fit)
        btn_reset = QPushButton("100%")
        btn_reset.setToolTip("Zoom al 100 %")
        btn_reset.clicked.connect(self._reset_zoom)
        barra.addWidget(btn_reset)

        izq = QWidget()
        lv = QVBoxLayout(izq)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(4)
        lv.addLayout(barra)
        lv.addWidget(self._vista)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(izq)
        split.addWidget(self._detalle)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        split.setSizes([560, 360])

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(split)

    # ---------- API ----------
    def mostrar_caso(self, caso):
        """Dibuja el camino de decisión de un Caso."""
        self._escena.clear()
        self._lbl.setText(f"{caso.titulo}  ·  {caso.tipo}")

        nodos = []
        # Nodo cabecera: la pregunta del análisis.
        nodos.append((
            _Nodo("Pregunta del análisis", caso.pregunta or "—", _HEAD,
                  {"tipo": "cabecera", "pregunta": caso.pregunta,
                   "titulo": caso.titulo, "subtipo": caso.tipo}, self._on_hover)))
        # Un nodo por paso.
        for i, p in enumerate(caso.pasos, 1):
            acento = _OK if p.ok else _WARN
            sub = f"→ {p.respuesta}" if p.respuesta else ""
            nodos.append(_Nodo(
                f"{i}. {p.pregunta}", sub, acento,
                {"tipo": "paso", "pregunta": p.pregunta, "medicion": p.medicion,
                 "respuesta": p.respuesta, "consecuencia": p.consecuencia,
                 "alternativa": p.alternativa, "ok": p.ok}, self._on_hover))
        # Nodo veredicto.
        if caso.veredicto:
            nodos.append(_Nodo(
                "Veredicto", caso.veredicto, _VERD,
                {"tipo": "veredicto", "veredicto": caso.veredicto,
                 "matiz": caso.matiz}, self._on_hover))

        # Layout vertical centrado + flechas con la respuesta como etiqueta.
        y = 0.0
        x = 0.0
        centros = []
        for n in nodos:
            n.setPos(x, y)
            self._escena.addItem(n)
            centros.append((x + _ANCHO / 2, y, y + n.boundingRect().height()))
            y += n.boundingRect().height() + _GAP

        for i in range(len(nodos) - 1):
            cx, _, y0 = centros[i]
            _, y1, _ = centros[i + 1]
            self._flecha(cx, y0, y1)
            # etiqueta = respuesta del paso saliente
            datos = nodos[i]._datos
            etiqueta = datos.get("respuesta") if datos else ""
            if etiqueta:
                self._etiqueta_arista(cx, (y0 + y1) / 2, etiqueta)

        margen = 40
        rect = self._escena.itemsBoundingRect()
        self._escena.setSceneRect(rect.adjusted(-margen, -margen, margen, margen))
        self._ajustar()
        self._detalle.setHtml(self._detalle_vacio())

    # ---------- dibujo auxiliar ----------
    def _flecha(self, cx, y0, y1):
        pen = QPen(_EDGE, 2)
        self._escena.addLine(cx, y0, cx, y1, pen)
        cab = QPolygonF([
            QPointF(cx, y1), QPointF(cx - 6, y1 - 10), QPointF(cx + 6, y1 - 10)])
        item = self._escena.addPolygon(cab, QPen(_EDGE), QBrush(_EDGE))
        item.setZValue(1)

    def _etiqueta_arista(self, cx, y, texto):
        t = self._escena.addSimpleText(texto, QFont("Segoe UI", 8, QFont.Weight.Bold))
        t.setBrush(QBrush(QColor("#2563eb")))
        br = t.boundingRect()
        fondo = self._escena.addRect(
            cx + 10, y - br.height() / 2 - 2, br.width() + 10, br.height() + 4,
            QPen(Qt.PenStyle.NoPen), QBrush(QColor("#dbeafe")))
        fondo.setZValue(0.5)
        t.setPos(cx + 15, y - br.height() / 2)
        t.setZValue(0.6)

    def _ajustar(self):
        self._vista.resetTransform()
        self._vista._zoom = 1.0
        self._vista.fitInView(self._escena.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        # fitInView ya aplicó una escala; registrarla como zoom base aproximado
        self._vista._zoom = self._vista.transform().m11()

    def _reset_zoom(self):
        self._vista.resetTransform()
        self._vista._zoom = 1.0

    # ---------- detalle (hover) ----------
    def _on_hover(self, datos):
        self.seleccionado.emit(datos)
        self._detalle.setHtml(self._detalle_html(datos))

    @staticmethod
    def _detalle_vacio():
        return ("<div style='color:#64748b;'>Pasá el cursor por un nodo para ver "
                "<b>el cálculo que hizo el motor</b> en ese paso, qué decidió y qué "
                "habría hecho si el número daba distinto.</div>")

    @staticmethod
    def _esc(s):
        return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;"))

    def _detalle_html(self, d):
        e = self._esc
        tipo = d.get("tipo")
        if tipo == "cabecera":
            return (f"<h3 style='margin:0 0 6px; color:#0369a1;'>Análisis</h3>"
                    f"<p><b>{e(d.get('titulo'))}</b><br>"
                    f"<span style='color:#64748b;'>{e(d.get('subtipo'))}</span></p>"
                    f"<p><b>Pregunta:</b> {e(d.get('pregunta'))}</p>")
        if tipo == "veredicto":
            html = (f"<h3 style='margin:0 0 6px; color:#1d4ed8;'>Veredicto</h3>"
                    f"<p>{e(d.get('veredicto'))}</p>")
            if d.get("matiz"):
                html += (f"<p style='background:#fef9c3; border-left:4px solid #ca8a04; "
                         f"padding:6px 8px; color:#713f12;'><b>Qué NO prueba:</b> "
                         f"{e(d.get('matiz'))}</p>")
            return html
        # paso
        color = "#16a34a" if d.get("ok") else "#d97706"
        html = [f"<h3 style='margin:0 0 6px; color:{color};'>{e(d.get('pregunta'))}</h3>"]
        html.append(
            f"<div style='background:#f1f5f9; border:1px solid #e2e8f0; border-radius:6px; "
            f"padding:8px 10px; margin:6px 0;'>"
            f"<div style='font-size:10px; text-transform:uppercase; letter-spacing:.5px; "
            f"color:#64748b;'>Cálculo realizado</div>"
            f"<div style='font-family:Consolas,monospace; color:#0f172a; margin-top:2px;'>"
            f"{e(d.get('medicion')) or '—'}</div></div>")
        html.append(f"<p><b>Resultado:</b> {e(d.get('respuesta'))}</p>")
        if d.get("consecuencia"):
            html.append(f"<p><b>Por eso el motor:</b> {e(d.get('consecuencia'))}</p>")
        if d.get("alternativa"):
            html.append(
                f"<p style='color:#64748b;'><b>Si el número daba distinto:</b> "
                f"{e(d.get('alternativa'))}</p>")
        return "".join(html)
