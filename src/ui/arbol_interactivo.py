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

from src.analysis.omni_catalogo import POR_ID
from src.analysis.omni_formulas import ensayo_de_texto
from src.ui.formula_dialog import abrir_formula

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


class _Clicable:
    """Mezcla para nodos: un click sin arrastrar llama a `on_click(datos)`.

    Si el nodo no es clicable, el evento sigue de largo y la vista lo usa para
    desplazar (arrastre), así que pan y click no se pisan.
    """

    def _init_click(self, on_click):
        self._on_click = on_click
        self._press = None
        if on_click:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if self._on_click:
            self._press = event.screenPos()
            event.accept()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        if self._on_click and self._press is not None:
            d = event.screenPos() - self._press
            if abs(d.x()) + abs(d.y()) < 6:
                self._on_click(self._datos)
        self._press = None


class _Nodo(_Clicable, QGraphicsItem):
    """Un nodo del árbol: pinta su propia caja y texto, y avisa al hover."""

    def __init__(self, titulo, subtitulo, acento, datos, on_hover, on_click=None):
        super().__init__()
        self._datos = datos
        self._init_click(on_click)
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
    def mostrar_caso(self, caso, auditoria=None):
        """Dibuja el camino de decisión de un Caso.

        Con la `auditoria` de la corrida, los pasos que corresponden a un ensayo
        se vuelven clicables y abren su fórmula con los números de este caso.
        """
        self._escena.clear()
        self._caso = caso
        self._auditoria = auditoria or {}
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
            ensayo_id = ensayo_de_texto(p.medicion) or ensayo_de_texto(p.pregunta)
            nodos.append(_Nodo(
                f"{i}. {p.pregunta}", sub, acento,
                {"tipo": "paso", "pregunta": p.pregunta, "medicion": p.medicion,
                 "respuesta": p.respuesta, "consecuencia": p.consecuencia,
                 "alternativa": p.alternativa, "ok": p.ok, "ensayo_id": ensayo_id},
                self._on_hover, on_click=self._on_click if ensayo_id else None))
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

    def _on_click(self, datos):
        id_ = datos.get("ensayo_id")
        if not id_:
            return
        fila = next((f for f in self._auditoria.get("filas", []) if f["id"] == id_), {})
        todas = fila.get("ejecuciones") or []
        titulo = getattr(self._caso, "titulo", None)
        propias = [e for e in todas if e.get("ambito") == titulo]
        ens = POR_ID.get(id_)
        abrir_formula(self, id_, nombre=ens.nombre if ens else id_,
                      estado=fila.get("estado"), ejecuciones=propias or todas,
                      motivos=fila.get("motivos"), detalle_extra=datos.get("medicion"))

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
        if d.get("ensayo_id"):
            html.append("<p style='color:#2563eb; font-size:11px;'>&#128270; Hacé click en "
                        "el nodo para ver la fórmula y cómo se calculó con tus datos.</p>")
        return "".join(html)


# ======================================================================
#  Vista general: el árbol completo del motor, etapa por etapa
# ======================================================================
# Usa la misma topología que el dibujo estático (omni_arbol.LAYOUT) y colorea
# cada ensayo según la auditoría de la corrida. Al pasar el mouse por un ensayo
# se ve lo que calculó (los `detalle` que registra el motor), dónde corrió, por
# qué se descartó, cuándo corre y para qué sirve.

from src.analysis.omni_arbol import LAYOUT, DECISIONES  # noqa: E402
from src.analysis.omni_catalogo import ETAPAS, POR_ID  # noqa: E402
from src.analysis.omni_auditoria import EJECUTADO, DESCARTADO, NO_APLICA  # noqa: E402

# (fondo, borde, texto, punteado, grosor)
_EST_GENERAL = {
    EJECUTADO:  ("#dcfce7", "#15803d", "#14532d", False, 2.0),
    DESCARTADO: ("#f1f5f9", "#94a3b8", "#64748b", False, 1.2),
    NO_APLICA:  ("#ffffff", "#cbd5e1", "#94a3b8", True, 1.0),
}
_EST_DECISION = ("#e0f2fe", "#0e7490", "#0c4a6e", False, 1.6)
_EST_ETAPA = ("#e2e8f0", "#334155", "#0f172a", False, 1.6)

_W_NODO = 190      # ancho de cada ensayo/decisión
_DX = 245          # separación entre columnas
_DY = 74           # separación entre filas (unidad de `fila` del LAYOUT)
_GAP_ETAPA = 70    # aire entre etapas


class _NodoCompacto(_Clicable, QGraphicsItem):
    """Caja compacta con texto centrado; avisa al hover."""

    def __init__(self, texto, estilo, datos, on_hover, ancho=_W_NODO, negrita=False,
                 on_click=None):
        super().__init__()
        self._datos = datos
        self._init_click(on_click)
        self._texto = texto
        (self._fondo, self._borde, self._tinta,
         self._punteado, self._grosor) = estilo
        self._datos = datos
        self._on_hover = on_hover
        self._ancho = ancho
        self._negrita = negrita
        self._hover = False
        self.setAcceptHoverEvents(True)
        self._alto = self._medir()

    def _fuente(self):
        peso = QFont.Weight.DemiBold if self._negrita else QFont.Weight.Normal
        return QFont("Segoe UI", 9, peso)

    def _medir(self):
        from PyQt6.QtGui import QFontMetrics
        r = QFontMetrics(self._fuente()).boundingRect(
            0, 0, self._ancho - 16, 2000,
            int(Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter), self._texto)
        return max(40, r.height() + 16)

    def alto(self):
        return self._alto

    def boundingRect(self):
        return QRectF(0, 0, self._ancho, self._alto)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(1, 1, self._ancho - 2, self._alto - 2)
        path = QPainterPath()
        path.addRoundedRect(rect, 9, 9)
        fondo = QColor(self._fondo)
        if self._hover:
            fondo = fondo.darker(106)
        painter.fillPath(path, QBrush(fondo))
        pen = QPen(QColor(self._borde), self._grosor + (1.5 if self._hover else 0))
        if self._punteado:
            pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawPath(path)
        painter.setPen(QPen(QColor(self._tinta)))
        painter.setFont(self._fuente())
        painter.drawText(QRectF(8, 8, self._ancho - 16, self._alto - 16),
                         int(Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter),
                         self._texto)

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


class ArbolGeneralWidget(QWidget):
    """Árbol completo del motor (todas las etapas) en una escena interactiva,
    con panel de detalle al hover."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._escena = QGraphicsScene(self)
        self._vista = _Vista(self._escena)
        self._auditoria = {}

        self._detalle = QTextBrowser()
        self._detalle.setStyleSheet(
            "QTextBrowser { background:#ffffff; border:1px solid #e2e8f0; "
            "border-radius:8px; padding:10px; font-family:'Segoe UI'; font-size:12px; }")
        self._detalle.setHtml(self._vacio())

        barra = QHBoxLayout()
        barra.setContentsMargins(0, 0, 0, 0)
        leyenda = QLabel(
            "<span style='color:#15803d;'>&#9632;</span> ejecutado &nbsp; "
            "<span style='color:#94a3b8;'>&#9632;</span> descartado &nbsp; "
            "<span style='color:#cbd5e1;'>&#9633;</span> no aplica &nbsp; "
            "<span style='color:#0e7490;'>&#9632;</span> decisión &nbsp;&middot;&nbsp; "
            "<span style='color:#64748b;'>rueda = zoom, arrastrar = mover</span>")
        leyenda.setStyleSheet("font-size:11px;")
        barra.addWidget(leyenda, stretch=1)
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
        split.setSizes([620, 340])

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(split)

    # ---------- API ----------
    def mostrar_auditoria(self, auditoria):
        """Dibuja todas las etapas del motor coloreadas según la corrida."""
        self._auditoria = auditoria or {}
        self._escena.clear()
        filas_por_id = {f["id"]: f for f in self._auditoria.get("filas", [])}
        estados = self._auditoria.get("estado", {})
        por_etapa = self._auditoria.get("por_etapa", {})

        y_base = 0.0
        for etapa in ETAPAS:
            lay = LAYOUT.get(etapa)
            if not lay:
                continue
            nodos = lay["nodos"]
            max_col = max(c for _, c, _ in nodos)
            fila_max = max(f for _, _, f in nodos)
            fila_min = min(f for _, _, f in nodos)
            ancho_etapa = max_col * _DX + _W_NODO

            # Cabecera de etapa con conteos.
            cuentas = por_etapa.get(etapa, {})
            ej = cuentas.get(EJECUTADO, 0)
            de = cuentas.get(DESCARTADO, 0)
            na = cuentas.get(NO_APLICA, 0)
            tot = cuentas.get("total", ej + de + na)
            cab = _NodoCompacto(
                f"{etapa}   ·   {ej} ejecutado(s) · {de} descartado(s) · "
                f"{na} no aplica  (de {tot})",
                _EST_ETAPA,
                {"tipo": "etapa", "etapa": etapa, "ej": ej, "de": de, "na": na, "tot": tot},
                self._on_hover, ancho=ancho_etapa, negrita=True)
            cab.setPos(0, y_base)
            self._escena.addItem(cab)
            y0 = y_base + cab.alto() + 34

            # Nodos de la etapa.
            items = {}
            alto_max = 0.0
            for clave, col, fila in nodos:
                if clave.startswith("?"):
                    texto = DECISIONES.get(clave, clave)
                    estilo = _EST_DECISION
                    datos = {"tipo": "decision", "texto": texto.replace("\n", " ")}
                else:
                    ens = POR_ID.get(clave)
                    nombre = ens.nombre if ens else clave
                    est = estados.get(clave, NO_APLICA)
                    fila_aud = filas_por_id.get(clave, {})
                    sufijo = {EJECUTADO: f"×{fila_aud.get('veces', 1)}",
                              DESCARTADO: "descartado",
                              NO_APLICA: "no aplica"}[est]
                    texto = f"{nombre}\n{sufijo}"
                    estilo = _EST_GENERAL[est]
                    datos = {"tipo": "ensayo", "id": clave, "estado": est,
                             "fila": fila_aud, "ens": ens}
                clic = self._on_click if not clave.startswith("?") else None
                n = _NodoCompacto(texto, estilo, datos, self._on_hover, on_click=clic)
                n.setZValue(2)
                self._escena.addItem(n)
                items[clave] = (n, col, fila)
                alto_max = max(alto_max, n.alto())

            # Espaciado vertical: el LAYOUT usa filas fraccionarias pensadas para
            # cajas chicas. Se agranda la unidad hasta que ninguna caja pise a la
            # de abajo en su misma columna.
            dy = float(_DY)
            por_col = {}
            for n, col, fila in items.values():
                por_col.setdefault(col, []).append((fila, n))
            for lista in por_col.values():
                lista.sort(key=lambda t: -t[0])
                for (f1, a), (f2, b) in zip(lista, lista[1:]):
                    if f1 > f2:
                        dy = max(dy, (a.alto() / 2 + b.alto() / 2 + 16) / (f1 - f2))
            for n, col, fila in items.values():
                cy = y0 + (fila_max - fila) * dy
                n.setPos(col * _DX, cy - n.alto() / 2)
            items = {k: v[0] for k, v in items.items()}

            # Aristas: verdes y llenas si llevan a algo que corrió.
            for origen, destino, etiqueta in lay["aristas"]:
                a, b = items.get(origen), items.get(destino)
                if a is None or b is None:
                    continue
                activa = (estados.get(destino) == EJECUTADO
                          or destino.startswith("?"))
                self._arista(a, b, etiqueta, activa)

            y_base = y0 + (fila_max - fila_min) * dy + alto_max / 2 + _GAP_ETAPA

        margen = 40
        rect = self._escena.itemsBoundingRect()
        self._escena.setSceneRect(rect.adjusted(-margen, -margen, margen, margen))
        self._ajustar()
        self._detalle.setHtml(self._vacio())

    # ---------- dibujo ----------
    def _arista(self, a, b, etiqueta, activa):
        ra = a.sceneBoundingRect()
        rb = b.sceneBoundingRect()
        if rb.left() > ra.right():
            # columna siguiente: sale por la derecha, entra por la izquierda
            p0 = QPointF(ra.right(), ra.center().y())
            p1 = QPointF(rb.left(), rb.center().y())
            dx = (p1.x() - p0.x()) / 2
            c0 = QPointF(p0.x() + dx, p0.y())
            c1 = QPointF(p1.x() - dx, p1.y())
            tx, ty = -1.0, 0.0
        else:
            # misma columna: vertical
            abajo = rb.top() >= ra.bottom()
            p0 = QPointF(ra.center().x(), ra.bottom() if abajo else ra.top())
            p1 = QPointF(rb.center().x(), rb.top() if abajo else rb.bottom())
            dy = (p1.y() - p0.y()) / 2
            c0 = QPointF(p0.x(), p0.y() + dy)
            c1 = QPointF(p1.x(), p1.y() - dy)
            tx, ty = (0.0, -1.0) if abajo else (0.0, 1.0)
        path = QPainterPath(p0)
        path.cubicTo(c0, c1, p1)
        color = QColor("#15803d") if activa else QColor("#cbd5e1")
        pen = QPen(color, 2.0 if activa else 1.2)
        if not activa:
            pen.setStyle(Qt.PenStyle.DashLine)
        item = self._escena.addPath(path, pen)
        item.setZValue(1)
        # punta de flecha (t = dirección hacia atrás desde la punta)
        px, py = -ty, tx
        cab = QPolygonF([
            p1,
            QPointF(p1.x() + tx * 9 + px * 5, p1.y() + ty * 9 + py * 5),
            QPointF(p1.x() + tx * 9 - px * 5, p1.y() + ty * 9 - py * 5)])
        punta = self._escena.addPolygon(cab, QPen(color), QBrush(color))
        punta.setZValue(1)
        if etiqueta:
            mid = path.pointAtPercent(0.5)
            t = self._escena.addSimpleText(etiqueta, QFont("Segoe UI", 8, QFont.Weight.Bold))
            t.setBrush(QBrush(QColor("#1d4ed8") if activa else QColor("#94a3b8")))
            br = t.boundingRect()
            fondo = self._escena.addRect(
                mid.x() - br.width() / 2 - 4, mid.y() - br.height() / 2 - 2,
                br.width() + 8, br.height() + 4,
                QPen(Qt.PenStyle.NoPen), QBrush(QColor("#ffffff")))
            fondo.setZValue(1.5)
            t.setPos(mid.x() - br.width() / 2, mid.y() - br.height() / 2)
            t.setZValue(1.6)

    def _ajustar(self):
        self._vista.resetTransform()
        self._vista.fitInView(self._escena.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._vista._zoom = self._vista.transform().m11()

    def _reset_zoom(self):
        self._vista.resetTransform()
        self._vista._zoom = 1.0

    # ---------- detalle ----------
    @staticmethod
    def _vacio():
        return ("<div style='color:#64748b;'>Pasá el cursor por un ensayo para ver "
                "<b>qué calculó el motor</b>, sobre qué columnas, o por qué lo "
                "descartó; y para qué sirve y cuándo corre.</div>")

    @staticmethod
    def _esc(s):
        return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;"))

    def _on_hover(self, d):
        self._detalle.setHtml(self._html(d))

    def _on_click(self, d):
        if d.get("tipo") != "ensayo":
            return
        f = d.get("fila") or {}
        ens = d.get("ens")
        abrir_formula(self, d["id"], nombre=ens.nombre if ens else d["id"],
                      estado=d.get("estado"), ejecuciones=f.get("ejecuciones"),
                      motivos=f.get("motivos"))

    def _html(self, d):
        e = self._esc
        tipo = d.get("tipo")
        if tipo == "etapa":
            return (f"<h3 style='margin:0 0 6px; color:#0f172a;'>{e(d['etapa'])}</h3>"
                    f"<p><b style='color:#15803d;'>{d['ej']}</b> ejecutado(s), "
                    f"<b style='color:#64748b;'>{d['de']}</b> descartado(s) con motivo, "
                    f"<b style='color:#94a3b8;'>{d['na']}</b> no aplica, de "
                    f"{d['tot']} ensayos del catálogo en esta etapa.</p>")
        if tipo == "decision":
            return (f"<h3 style='margin:0 0 6px; color:#0e7490;'>Punto de decisión</h3>"
                    f"<p>{e(d['texto'])}</p><p style='color:#64748b;'>El motor "
                    f"bifurca aquí según los datos; las flechas verdes muestran la "
                    f"rama que se tomó.</p>")
        # ensayo
        f = d.get("fila") or {}
        ens = d.get("ens")
        est = d.get("estado")
        color = {EJECUTADO: "#15803d", DESCARTADO: "#64748b", NO_APLICA: "#94a3b8"}[est]
        rotulo = {EJECUTADO: "Ejecutado", DESCARTADO: "Descartado",
                  NO_APLICA: "No aplica"}[est]
        nombre = ens.nombre if ens else d.get("id")
        h = [f"<h3 style='margin:0 0 4px; color:{color};'>{e(nombre)}</h3>",
             f"<p style='margin:0 0 8px;'><span style='background:{color}; color:white; "
             f"padding:1px 6px; border-radius:4px; font-size:11px;'>{rotulo}</span>"]
        if est == EJECUTADO:
            h.append(f" &nbsp;×{f.get('veces', 1)}")
        h.append("</p>")

        if est == EJECUTADO:
            detalles = f.get("detalles") or []
            ambitos = f.get("ambitos") or []
            renglones = []
            for i, det in enumerate(detalles):
                donde = ambitos[i] if i < len(ambitos) else ""
                flecha = " &rarr; " if donde else ""
                renglones.append(
                    f"<div><span style='color:#64748b;'>{e(donde)}</span>"
                    f"{flecha}{e(det)}</div>")
            cuerpo = "".join(renglones) or (
                "<div>" + (", ".join(e(a) for a in ambitos) or "sin detalle registrado")
                + "</div>")
            h.append(
                "<div style='background:#f1f5f9; border:1px solid #e2e8f0; border-radius:6px; "
                "padding:8px 10px; margin:6px 0;'>"
                "<div style='font-size:10px; text-transform:uppercase; letter-spacing:.5px; "
                "color:#64748b;'>Cálculo realizado</div>"
                "<div style='font-family:Consolas,monospace; color:#0f172a; margin-top:2px;'>"
                f"{cuerpo}</div></div>")
        elif est == DESCARTADO:
            motivos = f.get("motivos") or []
            h.append("<p><b>Por qué se descartó:</b> "
                     + ("; ".join(e(m) for m in motivos) or "el motor eligió la otra rama")
                     + "</p>")
        else:
            h.append("<p style='color:#64748b;'>Los datos de esta corrida nunca "
                     "abrieron esta rama.</p>")

        if ens:
            if ens.gatillo:
                h.append(f"<p><b>Cuándo corre:</b> {e(ens.gatillo)}</p>")
            if ens.porque:
                h.append(f"<p><b>Para qué sirve:</b> {e(ens.porque)}</p>")
            if ens.alternativa:
                alt = POR_ID.get(ens.alternativa)
                h.append(f"<p style='color:#64748b;'><b>Alternativa:</b> "
                         f"{e(alt.nombre if alt else ens.alternativa)}</p>")
            if ens.norma:
                h.append(f"<p style='color:#64748b;'><b>Norma:</b> {e(ens.norma)}</p>")
        h.append("<p style='color:#2563eb; font-size:11px;'>&#128270; Hacé click en el "
                 "ensayo para ver su fórmula y cómo se calculó con tus datos.</p>")
        return "".join(h)
