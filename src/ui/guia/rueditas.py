"""Modo Rueditas: asistente de cuatro pantallas, sin jerga.

Datos → Pregunta → Columnas → Respuesta. Cada pantalla pide una sola cosa,
con letra grande y ejemplos. La respuesta sale del mismo motor que el
Omnianálisis (`respuestas.responder`) y se muestra con un semáforo.
"""
from html import escape

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

from src.ui.guia.analisis_datos import diagnosticar
from src.ui.guia.ejemplos import COLUMNAS_EJEMPLO, OBJETIVOS
from src.ui.guia.modos import INFO_MODOS, Modo
from src.ui.guia.respuestas import responder, validar

_C = INFO_MODOS[Modo.RUEDITAS]["color"]
_SUAVE = INFO_MODOS[Modo.RUEDITAS]["suave"]
_PASOS = ["Tus datos", "Tu pregunta", "Tus columnas", "Tu respuesta"]


def _txt(html, tam=14, color="#1e293b", negrita=False):
    lbl = QLabel(html)
    lbl.setTextFormat(Qt.TextFormat.RichText)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(f"font-size:{tam}px; color:{color}; background:transparent; "
                      f"{'font-weight:bold;' if negrita else ''}")
    return lbl


def _boton_grande(titulo, subtitulo="", primario=False):
    b = QPushButton()
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    alto = 64 if subtitulo else 48
    b.setMinimumHeight(alto)
    lay = QVBoxLayout(b)
    lay.setContentsMargins(16, 8, 16, 8)
    t = QLabel(titulo)
    t.setStyleSheet(f"font-size:16px; font-weight:bold; background:transparent; "
                    f"color:{'white' if primario else '#0f172a'};")
    t.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    lay.addWidget(t)
    if subtitulo:
        s = QLabel(subtitulo)
        s.setWordWrap(True)
        s.setStyleSheet(f"font-size:12px; background:transparent; "
                        f"color:{'#ffffffdd' if primario else '#64748b'};")
        s.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        lay.addWidget(s)
    if primario:
        b.setStyleSheet(f"QPushButton {{ background:{_C}; border:none; border-radius:12px; "
                        f"min-height:{alto}px; }}"
                        f"QPushButton:hover {{ background:#c2410c; }}")
    else:
        b.setStyleSheet(f"QPushButton {{ background:white; border:2px solid #e2e8f0; "
                        f"border-radius:12px; text-align:left; min-height:{alto}px; }}"
                        f"QPushButton:hover {{ border-color:{_C}; background:{_SUAVE}; }}")
    return b


class AsistenteRueditas(QDialog):
    pedirEjemplo = pyqtSignal(str)
    pedirArchivo = pyqtSignal()
    verDetalle = pyqtSignal(list, list)      # columnas, pares de comparación de métodos

    def __init__(self, df=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rueditas — hacele una pregunta a tus datos")
        self.resize(760, 640)
        self.setStyleSheet(f"QDialog {{ background:#fffaf5; }}")
        self.df = df
        self.objetivo = None
        self.eleccion = {}
        self.respuesta = None
        self._combos = {}
        self._ejemplo = None

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)
        self._barra = QLabel()
        self._barra.setTextFormat(Qt.TextFormat.RichText)
        self._barra.setStyleSheet(f"background:{_C}; padding:14px 20px;")
        raiz.addWidget(self._barra)

        self._pila = QStackedWidget()
        raiz.addWidget(self._pila, stretch=1)

        pie = QHBoxLayout()
        pie.setContentsMargins(20, 10, 20, 16)
        self._atras = QPushButton("← Atrás")
        self._atras.clicked.connect(self._volver)
        self._siguiente = QPushButton("Siguiente →")
        self._siguiente.clicked.connect(self._avanzar)
        for b in (self._atras, self._siguiente):
            b.setMinimumHeight(40)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
        self._atras.setStyleSheet("QPushButton { font-size:14px; padding:0 18px; min-height:38px; }")
        self._siguiente.setStyleSheet(
            f"QPushButton {{ font-size:14px; padding:0 22px; min-height:38px; background:{_C}; color:white; "
            f"border:none; border-radius:8px; font-weight:bold; }}"
            f"QPushButton:disabled {{ background:#fdba74; }}")
        pie.addWidget(self._atras)
        pie.addStretch()
        pie.addWidget(self._siguiente)
        raiz.addLayout(pie)

        for _ in _PASOS:
            self._pila.addWidget(QWidget())
        self._ir(0 if df is None else 1)

    # ---------- navegación ----------
    def _ir(self, i):
        viejo = self._pila.widget(i)
        nuevo = [self._pagina_datos, self._pagina_pregunta,
                 self._pagina_columnas, self._pagina_respuesta][i]()
        self._pila.insertWidget(i, nuevo)
        self._pila.removeWidget(viejo)
        viejo.deleteLater()
        self._pila.setCurrentIndex(i)
        self._pintar_barra(i)
        self._atras.setVisible(i > 0)
        self._siguiente.setVisible(i in (0, 2))
        if i == 0:
            self._siguiente.setEnabled(self.df is not None)
        if i == 2:
            self._validar()

    def _volver(self):
        self._ir(max(0, self._pila.currentIndex() - 1))

    def _avanzar(self):
        i = self._pila.currentIndex()
        if i == 2:
            self._calcular()
        self._ir(min(3, i + 1))

    def _pintar_barra(self, actual):
        partes = []
        for i, nombre in enumerate(_PASOS):
            if i < actual:
                estilo, marca = "color:#ffffffbb;", "&#10004;"
            elif i == actual:
                estilo, marca = "color:white; font-weight:bold;", str(i + 1)
            else:
                estilo, marca = "color:#ffffff88;", str(i + 1)
            partes.append(f"<span style='{estilo} font-size:13px;'>"
                          f"<span style='font-size:15px;'>{marca}</span>&nbsp;{nombre}</span>")
        self._barra.setText("&nbsp;&nbsp;&nbsp;&#8250;&nbsp;&nbsp;&nbsp;".join(partes))

    def _envolver(self, contenido: QWidget) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        contenido.setStyleSheet("background:transparent;")
        scroll.setWidget(contenido)
        return scroll

    # ---------- 1. datos ----------
    def set_datos(self, df, ejemplo=None):
        """Lo llama la ventana principal después de cargar un archivo o un ejemplo."""
        self.df = df
        self._ejemplo = ejemplo
        if ejemplo in OBJETIVOS:
            self.objetivo = ejemplo
            self.eleccion = dict(COLUMNAS_EJEMPLO[ejemplo])
            self._ir(2)
        elif df is not None:
            self._ir(1)

    def _pagina_datos(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(28, 24, 28, 12)
        v.setSpacing(12)
        if self.df is None:
            v.addWidget(_txt("Primero, tus datos", 22, negrita=True))
            v.addWidget(_txt("Necesito una tabla: una fila por paciente (o muestra) y una "
                             "columna por cada cosa que mediste.", 15, "#475569"))
            b = _boton_grande("Abrir mi archivo", "Un Excel o un CSV que ya tengas.", True)
            b.clicked.connect(self.pedirArchivo.emit)
            v.addWidget(b)
            v.addWidget(_txt("…o probá con un ejemplo, para ver cómo funciona:", 14, "#475569"))
            for clave, obj in OBJETIVOS.items():
                b = _boton_grande(obj.titulo, obj.ejemplo)
                b.clicked.connect(lambda _=False, k=clave: self.pedirEjemplo.emit(k))
                v.addWidget(b)
        else:
            v.addWidget(_txt("Tus datos ya están cargados", 22, negrita=True))
            v.addWidget(_txt(f"Tenés <b>{len(self.df)}</b> filas y <b>{len(self.df.columns)}"
                             f"</b> columnas. Seguí cuando quieras.", 15, "#475569"))
        v.addStretch()
        return self._envolver(w)

    # ---------- 2. pregunta ----------
    def _pagina_pregunta(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(28, 24, 28, 12)
        v.setSpacing(12)
        v.addWidget(_txt("¿Qué querés averiguar?", 22, negrita=True))
        v.addWidget(_txt("Elegí la pregunta que más se parezca a la tuya.", 15, "#475569"))
        posibles = diagnosticar(self.df).posibles if self.df is not None else {}
        for clave, obj in OBJETIVOS.items():
            sirve = clave in posibles
            sub = obj.ejemplo if sirve else (obj.ejemplo + "  ·  Tu tabla no tiene las columnas "
                                                           "que hacen falta para esta.")
            b = _boton_grande(obj.titulo, sub)
            b.setEnabled(sirve)
            b.clicked.connect(lambda _=False, k=clave: self._elegir_objetivo(k))
            v.addWidget(b)
        v.addStretch()
        return self._envolver(w)

    def _elegir_objetivo(self, clave):
        if clave != self.objetivo:
            self.eleccion = {}
        self.objetivo = clave
        self._ir(2)

    # ---------- 3. columnas ----------
    def _pagina_columnas(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(28, 24, 28, 12)
        v.setSpacing(10)
        obj = OBJETIVOS[self.objetivo]
        v.addWidget(_txt(obj.titulo, 22, negrita=True))
        v.addWidget(_txt("Decime qué columna es cada cosa.", 15, "#475569"))
        d = diagnosticar(self.df)
        candidatas = d.posibles.get(self.objetivo, {})
        self._combos = {}
        self._estados = {}
        usados = set()
        for rol in obj.roles:
            caja = QFrame()
            caja.setStyleSheet("QFrame { background:white; border:1px solid #fed7aa; "
                               "border-radius:12px; } QLabel { border:none; }")
            g = QVBoxLayout(caja)
            g.setContentsMargins(16, 12, 16, 12)
            g.addWidget(_txt(rol.pregunta, 16, negrita=True))
            g.addWidget(_txt(rol.ayuda, 12, "#64748b"))
            cmb = QComboBox()
            cmb.setMinimumHeight(36)
            cmb.setStyleSheet("QComboBox { font-size:14px; padding:4px 8px; }")
            opciones = candidatas.get(rol.clave, [])
            cmb.addItems(opciones)
            preferida = self.eleccion.get(rol.clave)
            if preferida not in opciones:
                preferida = next((o for o in opciones if o not in usados), None)
            if preferida:
                cmb.setCurrentText(preferida)
                usados.add(preferida)
            cmb.currentTextChanged.connect(self._validar)
            g.addWidget(cmb)
            estado = _txt("", 13)
            g.addWidget(estado)
            self._combos[rol.clave] = cmb
            self._estados[rol.clave] = (estado, rol)
            v.addWidget(caja)
        v.addStretch()
        return self._envolver(w)

    def _validar(self, *_):
        if not self._combos:
            return
        self.eleccion = {k: c.currentText() for k, c in self._combos.items()}
        tipos = {c.nombre: c.rol for c in diagnosticar(self.df).columnas}
        for clave, (lbl, rol) in self._estados.items():
            col = self.eleccion.get(clave)
            if not col:
                lbl.setText("<span style='color:#dc2626;'>&#10006; Tu tabla no tiene una columna "
                            f"de {'números' if rol.tipo == 'numero' else 'categorías'}.</span>")
            elif tipos.get(col) == ("numero" if rol.tipo == "numero" else "categoria"):
                que = "números" if rol.tipo == "numero" else "categorías"
                lbl.setText(f"<span style='color:#16a34a;'>&#10004; «{escape(col)}» tiene "
                            f"{que}: sirve.</span>")
        problemas = validar(self.df, self.objetivo, self.eleccion)
        if any("misma columna" in p for p in problemas):
            for lbl, _rol in self._estados.values():
                lbl.setText("<span style='color:#dc2626;'>&#10006; Elegiste la misma columna "
                            "dos veces: cada pregunta va con una distinta.</span>")
        self._siguiente.setEnabled(not problemas)
        self._siguiente.setText("Ver la respuesta →")

    # ---------- 4. respuesta ----------
    def _calcular(self):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.respuesta = responder(self.df, self.objetivo, self.eleccion)
        finally:
            QApplication.restoreOverrideCursor()

    def _pagina_respuesta(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(28, 22, 28, 12)
        v.setSpacing(12)
        r = self.respuesta
        if r is None:
            v.addWidget(_txt("Todavía no hay respuesta.", 18))
            return self._envolver(w)

        fila = QHBoxLayout()
        luz = QLabel()
        luz.setFixedSize(54, 54)
        luz.setStyleSheet(f"background:{r.color_hex}; border-radius:27px; "
                          f"border:5px solid {r.color_hex}44;")
        fila.addWidget(luz, alignment=Qt.AlignmentFlag.AlignTop)
        fila.addSpacing(10)
        fila.addWidget(_txt(escape(r.titular), 22, r.color_hex, negrita=True), stretch=1)
        v.addLayout(fila)

        def bloque(titulo, html, fondo="white", borde="#e2e8f0"):
            caja = QFrame()
            caja.setStyleSheet(f"QFrame {{ background:{fondo}; border:1px solid {borde}; "
                               f"border-radius:12px; }} QLabel {{ border:none; }}")
            g = QVBoxLayout(caja)
            g.setContentsMargins(16, 12, 16, 12)
            g.addWidget(_txt(titulo, 13, "#64748b", negrita=True))
            g.addWidget(_txt(html, 15))
            v.addWidget(caja)

        if r.explicacion:
            bloque("¿QUÉ QUIERE DECIR?", escape(r.explicacion))
        if r.p_llano:
            bloque("¿QUÉ TAN SEGURO ES?", escape(r.p_llano))
        if r.ojo:
            bloque("OJO", escape(r.ojo), "#fffbeb", "#fde68a")
        if r.advertencias:
            bloque("PARA REVISAR", "<br>".join("• " + escape(a) for a in r.advertencias),
                   "#fff7ed", "#fed7aa")
        if r.siguiente:
            bloque("¿Y AHORA?", "<br>".join("• " + escape(s) for s in r.siguiente))

        botones = QGridLayout()
        b1 = _boton_grande("Ver cómo lo calculé", "Abre el detalle con el árbol y las fórmulas.")
        b1.clicked.connect(self._ver_detalle)
        b2 = _boton_grande("Hacer otra pregunta")
        b2.clicked.connect(lambda: self._ir(1))
        botones.addWidget(b1, 0, 0)
        botones.addWidget(b2, 0, 1)
        v.addLayout(botones)
        v.addStretch()
        return self._envolver(w)

    def _ver_detalle(self):
        if not self.respuesta or not self.respuesta.columnas:
            return
        cols = self.respuesta.columnas
        pares = [cols[:2]] if self.objetivo == "metodos" else []
        self.verDetalle.emit(list(cols), [list(p) for p in pares])
        self.close()
