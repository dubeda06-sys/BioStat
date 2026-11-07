"""Panel lateral de los modos guía.

Se redibuja con el contexto de la app (modo, pestaña, datos, última corrida) y
no ejecuta nada por su cuenta: todo lo que hace pasa por señales que conecta
la ventana principal (ir a una pestaña, señalar un control, cargar un ejemplo,
abrir Rueditas, ver una fórmula).
"""
from html import escape

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from src.ui.guia.analisis_datos import diagnosticar
from src.ui.guia.contenido import (
    COMO_LEER_P, GLOSARIO, LECCIONES, narrar_caso, pasos_asistente,
)
from src.ui.guia.ejemplos import COLUMNAS_EJEMPLO, OBJETIVOS, dataset
from src.ui.guia.modos import INFO_MODOS, Modo

PESTANAS = {0: "datos", 1: "analisis", 2: "graficos", 3: "omni"}
_GRAVEDAD = {"error": ("#dc2626", "#fef2f2", "&#10006;"),
             "atencion": ("#d97706", "#fffbeb", "&#9888;"),
             "ok": ("#16a34a", "#f0fdf4", "&#10004;")}


# ------------------------------------------------------------------ piezas
def _lbl(html, estilo="", wrap=True):
    lbl = QLabel(html)
    lbl.setTextFormat(Qt.TextFormat.RichText)
    lbl.setWordWrap(wrap)
    lbl.setOpenExternalLinks(False)
    lbl.setStyleSheet("background:transparent; border:none; font-size:12px; "
                      "color:#1e293b;" + estilo)
    return lbl


def _boton(texto, color, primario=False):
    b = QPushButton(texto)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if primario:
        b.setStyleSheet(
            f"QPushButton {{ background:{color}; color:white; border:none; border-radius:7px; "
            f"padding:7px 12px; font-weight:bold; min-height:22px; }}"
            f"QPushButton:hover {{ background:{color}; opacity:.9; border:2px solid #0f172a33; }}")
    else:
        b.setStyleSheet(
            f"QPushButton {{ background:white; color:{color}; border:1px solid {color}; "
            f"border-radius:7px; padding:5px 10px; min-height:22px; }}"
            f"QPushButton:hover {{ background:{color}14; }}")
    return b


class _Tarjeta(QFrame):
    def __init__(self, acento="#0e7490", fondo="#ffffff"):
        super().__init__()
        self.setStyleSheet(
            f"_Tarjeta {{ background:{fondo}; border:1px solid #e2e8f0; "
            f"border-left:4px solid {acento}; border-radius:9px; }}")
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(12, 10, 12, 10)
        self.v.setSpacing(6)


def _titulo(texto, color):
    return _lbl(f"<span style='font-size:14px; font-weight:bold; color:{color};'>"
                f"{texto}</span>")


def _mini_tabla(df, filas=4):
    cab = "".join(f"<th style='background:#f1f5f9; padding:3px 6px; text-align:left;'>"
                  f"{escape(str(c))}</th>" for c in df.columns)
    cuerpo = ""
    for _, fila in df.head(filas).iterrows():
        cuerpo += "<tr>" + "".join(
            f"<td style='padding:3px 6px; border-top:1px solid #e2e8f0;'>{escape(str(v))}</td>"
            for v in fila) + "</tr>"
    return (f"<table cellspacing='0' style='font-size:11px; border:1px solid #e2e8f0;'>"
            f"<tr>{cab}</tr>{cuerpo}<tr><td colspan='{len(df.columns)}' "
            f"style='padding:2px 6px; color:#94a3b8;'>…</td></tr></table>")


# ------------------------------------------------------------------ panel
class PanelGuia(QWidget):
    irAPestana = pyqtSignal(int)
    resaltar = pyqtSignal(str, str, str)          # clave del control, título, texto
    cargarEjemplo = pyqtSignal(str)               # clave del objetivo
    abrirRueditas = pyqtSignal()
    cambiarModo = pyqtSignal(str)
    abrirFormula = pyqtSignal(str)                # id del ensayo
    convertirLargo = pyqtSignal(list)             # columnas a apilar

    def __init__(self, parent=None):
        super().__init__(parent)
        self.modo = Modo.NORMAL
        self.eligiendo = False
        self.pestana = 0
        self.df = None
        self.diagnostico = None
        self.casos = []
        self.analizado = False
        self.setMinimumWidth(330)

        self._cab = QLabel()
        self._cab.setTextFormat(Qt.TextFormat.RichText)
        self._cab.setWordWrap(True)

        self._cuerpo = QWidget()
        self._v = QVBoxLayout(self._cuerpo)
        self._v.setContentsMargins(12, 12, 12, 12)
        self._v.setSpacing(10)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._cuerpo)
        scroll.setStyleSheet("QScrollArea { border:none; background:#f8fafc; }"
                             "QScrollArea > QWidget > QWidget { background:#f8fafc; }")

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)
        raiz.addWidget(self._cab)
        raiz.addWidget(scroll, stretch=1)

    # ---------- entradas de estado ----------
    def set_modo(self, modo, eligiendo=False):
        self.modo = Modo(modo)
        self.eligiendo = eligiendo
        self.redibujar()

    def set_pestana(self, indice):
        self.pestana = indice
        self.redibujar()

    def set_datos(self, df):
        self.df = df
        self.diagnostico = diagnosticar(df) if df is not None else None
        self.analizado = False
        self.casos = []
        self.redibujar()

    def set_analisis(self, casos):
        self.casos = list(casos or [])
        self.analizado = True
        self.redibujar()

    # ---------- dibujo ----------
    def _limpiar(self):
        # Sacarlos de la jerarquía YA: deleteLater solo borra cuando vuelve el
        # bucle de eventos, y mientras tanto el widget viejo se seguiría pintando
        # encima del nuevo.
        while self._v.count():
            item = self._v.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()

    def redibujar(self):
        info = INFO_MODOS[self.modo]
        self._cab.setText(
            f"<div style='padding:12px 14px;'>"
            f"<div style='font-size:11px; letter-spacing:1px; color:#ffffffcc;'>MODO</div>"
            f"<div style='font-size:18px; font-weight:bold; color:white;'>{info['nombre']}</div>"
            f"<div style='font-size:12px; color:#ffffffdd;'>{info['lema']}</div></div>")
        self._cab.setStyleSheet(f"background:{info['color']};")
        self._limpiar()
        if self.eligiendo or self.modo == Modo.NORMAL:
            self._elegir_modo()
        elif self.modo == Modo.ASISTENTE:
            self._asistente()
        elif self.modo == Modo.DOCENCIA:
            self._docencia()
        else:
            self._rueditas()
        self._v.addStretch()

    # ---------- elegir modo ----------
    def _elegir_modo(self):
        self._v.addWidget(_lbl("<span style='font-size:15px; font-weight:bold;'>¿Cómo querés "
                               "trabajar?</span><br><span style='color:#64748b;'>Podés cambiarlo "
                               "cuando quieras desde la barra de arriba.</span>"))
        for modo, info in INFO_MODOS.items():
            t = _Tarjeta(info["color"], info["suave"])
            t.v.addWidget(_lbl(f"<span style='font-size:14px; font-weight:bold; "
                               f"color:{info['color']};'>{info['nombre']}</span><br>"
                               f"{info['lema']}<br><span style='color:#64748b;'>Ideal si: "
                               f"{info['para']}</span>"))
            b = _boton(f"Usar modo {info['nombre']}", info["color"], primario=True)
            b.clicked.connect(lambda _=False, m=modo: self.cambiarModo.emit(m.value))
            t.v.addWidget(b)
            self._v.addWidget(t)

    # ---------- asistente ----------
    def _asistente(self):
        color = INFO_MODOS[Modo.ASISTENTE]["color"]
        listo = bool(self.diagnostico and self.diagnostico.listo)
        pasos = pasos_asistente(self.df is not None, listo, self.analizado,
                                PESTANAS.get(self.pestana, ""))
        t = _Tarjeta(color)
        t.v.addWidget(_titulo("Tus pasos", color))
        for p in pasos:
            if p["hecho"]:
                icono, tono = "<span style='color:#16a34a;'>&#10004;</span>", "#64748b"
            elif p["actual"]:
                icono, tono = f"<span style='color:{color};'>&#9679;</span>", "#0f172a"
            else:
                icono, tono = "<span style='color:#cbd5e1;'>&#9675;</span>", "#94a3b8"
            peso = "bold" if p["actual"] else "normal"
            t.v.addWidget(_lbl(f"{icono}&nbsp; <span style='color:{tono}; font-weight:{peso};'>"
                               f"{p['titulo']}</span>"))
            if p["actual"]:
                t.v.addWidget(_lbl(p["texto"], "color:#334155; margin-left:18px;"))
                fila = QHBoxLayout()
                fila.setContentsMargins(18, 0, 0, 0)
                b1 = _boton("Mostrame dónde", color, primario=True)
                b1.clicked.connect(lambda _=False, q=p: self._mostrar(q))
                fila.addWidget(b1)
                fila.addStretch()
                t.v.addLayout(fila)
        self._v.addWidget(t)

        if self.df is None:
            self._plantillas(color)
        else:
            self._diagnostico(color)

    def _mostrar(self, paso):
        self.irAPestana.emit(paso["pestana"])
        self.resaltar.emit(paso["resaltar"], paso["titulo"], paso["texto"])

    def _plantillas(self, color):
        self._v.addWidget(_lbl("<span style='font-size:14px; font-weight:bold;'>¿Cómo armo la "
                               "tabla?</span><br><span style='color:#64748b;'>Depende de qué "
                               "querés averiguar. Elegí uno y mirá el ejemplo:</span>"))
        for clave, obj in OBJETIVOS.items():
            t = _Tarjeta(color)
            t.v.addWidget(_lbl(f"<b>{obj.titulo}</b><br><i style='color:#64748b;'>"
                               f"{obj.ejemplo}</i>"))
            t.v.addWidget(_lbl(obj.como_armar, "color:#334155;"))
            t.v.addWidget(_lbl(_mini_tabla(dataset(clave))))
            b = _boton("Usar este ejemplo", color)
            b.clicked.connect(lambda _=False, k=clave: self.cargarEjemplo.emit(k))
            t.v.addWidget(b)
            self._v.addWidget(t)

    def _diagnostico(self, color):
        d = self.diagnostico
        t = _Tarjeta(color)
        t.v.addWidget(_titulo(f"Tu tabla: {d.filas} filas", color))
        chips = {"numero": "#0e7490", "categoria": "#7c3aed", "fecha": "#0369a1",
                 "identificador": "#94a3b8", "vacia": "#cbd5e1", "dudosa": "#d97706"}
        filas = "".join(
            f"<tr><td style='padding:2px 8px 2px 0;'>{escape(c.nombre)}</td>"
            f"<td><span style='background:{chips[c.rol]}; color:white; padding:1px 6px; "
            f"border-radius:4px; font-size:10px;'>{c.rol_llano}</span></td></tr>"
            for c in d.columnas)
        t.v.addWidget(_lbl(f"<table>{filas}</table>"))
        self._v.addWidget(t)

        for a in d.avisos:
            borde, fondo, icono = _GRAVEDAD[a.gravedad]
            ta = _Tarjeta(borde, fondo)
            ta.v.addWidget(_lbl(f"<span style='color:{borde};'>{icono}</span>&nbsp; "
                                f"{escape(a.texto)}"))
            if a.gravedad == "atencion" and d.formato_ancho and "formato ancho" in a.texto:
                b = _boton("Convertir a una columna de grupo y una de valor", borde)
                b.clicked.connect(lambda _=False, cols=list(d.formato_ancho):
                                  self.convertirLargo.emit(cols))
                ta.v.addWidget(b)
            self._v.addWidget(ta)

        if d.posibles:
            t2 = _Tarjeta(color)
            t2.v.addWidget(_titulo("Con esta tabla podés averiguar", color))
            for clave in d.posibles:
                obj = OBJETIVOS[clave]
                t2.v.addWidget(_lbl(f"&#10148; <b>{obj.titulo}</b><br>"
                                    f"<span style='color:#64748b;'>{obj.ejemplo}</span>"))
            b = _boton("Ir al Omnianálisis", color, primario=True)
            b.clicked.connect(lambda: self.irAPestana.emit(3))
            t2.v.addWidget(b)
            self._v.addWidget(t2)

    # ---------- docencia ----------
    def _docencia(self):
        color = INFO_MODOS[Modo.DOCENCIA]["color"]
        suave = INFO_MODOS[Modo.DOCENCIA]["suave"]
        clave = PESTANAS.get(self.pestana, "datos")
        titulo, html = LECCIONES[clave]
        t = _Tarjeta(color)
        t.v.addWidget(_titulo(f"Lección: {titulo}", color))
        t.v.addWidget(_lbl(html))
        self._v.addWidget(t)

        if self.analizado and self.casos:
            self._v.addWidget(_lbl("<span style='font-size:14px; font-weight:bold;'>Lo que hizo "
                                   "el motor, paso a paso</span>"))
            for caso in self.casos:
                tc = _Tarjeta(color)
                tc.v.addWidget(_lbl(f"<b style='color:{color};'>{escape(caso.titulo)}</b><br>"
                                    f"<i>{escape(caso.pregunta or '')}</i>"))
                for paso in narrar_caso(caso):
                    marca = "#16a34a" if paso["ok"] else "#d97706"
                    html_p = (f"<p style='margin:6px 0 2px;'><b style='color:{marca};'>"
                              f"{paso['n']}.</b> <b>{escape(paso['pregunta'])}</b></p>")
                    ens = paso["ensayo"]
                    if ens and ens["para_que"]:
                        html_p += (f"<p style='margin:0 0 2px; color:#475569;'><i>Por qué se "
                                   f"pregunta:</i> {escape(ens['para_que'])}</p>")
                    html_p += (f"<p style='margin:0 0 2px;'><i>Qué dio:</i> "
                               f"{escape(paso['medicion'])} → <b>{escape(paso['respuesta'])}</b></p>"
                               f"<p style='margin:0 0 2px;'><i>Qué decidió:</i> "
                               f"{escape(paso['consecuencia'])}</p>")
                    if paso["alternativa"]:
                        html_p += (f"<p style='margin:0; color:#64748b;'><i>Si daba distinto:</i> "
                                   f"{escape(paso['alternativa'])}</p>")
                    tc.v.addWidget(_lbl(html_p))
                    if ens:
                        b = _boton(f"Ver fórmula de {ens['nombre']}", color)
                        b.clicked.connect(lambda _=False, i=ens["id"]: self.abrirFormula.emit(i))
                        tc.v.addWidget(b)
                if caso.veredicto:
                    tc.v.addWidget(_lbl(f"<p style='background:{suave}; padding:6px;'>"
                                        f"<b>Conclusión:</b> {escape(caso.veredicto)}</p>"))
                self._v.addWidget(tc)
        elif self.pestana == 3:
            self._v.addWidget(_lbl("<i style='color:#64748b;'>Ejecutá el Omnianálisis y acá te "
                                   "cuento cada decisión del motor y para qué sirve cada "
                                   "prueba.</i>"))

        tp = _Tarjeta(color, suave)
        tp.v.addWidget(_lbl(COMO_LEER_P))
        self._v.addWidget(tp)

        tg = _Tarjeta(color)
        tg.v.addWidget(_titulo("Glosario", color))
        for termino, (defi, ej) in GLOSARIO.items():
            tg.v.addWidget(_lbl(f"<b>{termino}.</b> {defi}<br>"
                                f"<span style='color:#64748b;'><i>Ej.: {ej}</i></span>"))
        self._v.addWidget(tg)

    # ---------- rueditas ----------
    def _rueditas(self):
        color = INFO_MODOS[Modo.RUEDITAS]["color"]
        suave = INFO_MODOS[Modo.RUEDITAS]["suave"]
        t = _Tarjeta(color, suave)
        t.v.addWidget(_lbl("<span style='font-size:17px; font-weight:bold;'>Vamos de a un "
                           "paso.</span><br><span style='font-size:13px;'>No necesitás saber "
                           "estadística. Yo te pregunto y vos elegís.</span>"))
        b = _boton("Hacerle una pregunta a mis datos", color, primario=True)
        b.setMinimumHeight(44)
        b.setStyleSheet(b.styleSheet() + "QPushButton { font-size:14px; }")
        b.clicked.connect(self.abrirRueditas.emit)
        t.v.addWidget(b)
        self._v.addWidget(t)

        hay = self.df is not None
        pasos = [("1", "Tus datos", "Ya están cargados." if hay
                  else "Cargá tu archivo o usá uno de ejemplo.", hay),
                 ("2", "Tu pregunta", "Elegís qué querés averiguar, con ejemplos.", False),
                 ("3", "Tu respuesta", "Te la doy con un semáforo y en palabras simples.", False)]
        for num, tit, txt, hecho in pasos:
            tp = _Tarjeta(color)
            marca = "&#10004;" if hecho else num
            tp.v.addWidget(_lbl(
                f"<table><tr><td style='padding-right:10px;'><span style='font-size:20px; "
                f"font-weight:bold; color:{'#16a34a' if hecho else color};'>{marca}</span></td>"
                f"<td><span style='font-size:14px; font-weight:bold;'>{tit}</span><br>"
                f"<span style='font-size:12px; color:#475569;'>{txt}</span></td></tr></table>"))
            self._v.addWidget(tp)
        if not hay:
            te = _Tarjeta(color)
            te.v.addWidget(_lbl("<b>¿No tenés datos?</b> Probá con un ejemplo:"))
            for clave, obj in OBJETIVOS.items():
                b = _boton(obj.titulo, color)
                b.clicked.connect(lambda _=False, k=clave: self.cargarEjemplo.emit(k))
                te.v.addWidget(b)
            self._v.addWidget(te)

    # ---------- utilidades para tests ----------
    def textos(self) -> str:
        """Todo el texto visible del panel (para verificar contenido)."""
        partes = [self._cab.text()]
        for lbl in self._cuerpo.findChildren(QLabel):
            partes.append(lbl.text())
        for b in self._cuerpo.findChildren(QPushButton):
            partes.append(b.text())
        return "\n".join(partes)


_ = COLUMNAS_EJEMPLO  # reexportado para quien arme un ejemplo con columnas sugeridas
