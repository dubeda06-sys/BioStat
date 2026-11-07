"""Mini ventana: cómo se calcula un ensayo y cómo se hizo con los datos.

Las ecuaciones se dibujan con el mathtext de matplotlib (tipografía Computer
Modern, sin LaTeX instalado): raíces con su línea, raya de fracción, sumatorias
con sus límites. Si el método es iterativo no se vuelcan las iteraciones (sería
ilegible): se muestran los pasos del algoritmo y el resultado final.
"""
import io
from functools import lru_cache

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from src.analysis.omni_formulas import FORMULAS

_ESCALA = 2.0          # se dibuja al doble y se muestra a tamaño lógico: nítido en HiDPI
_TINTA = "#0f172a"


@lru_cache(maxsize=512)
def _png(latex: str, tam: int) -> bytes | None:
    """PNG transparente de una ecuación, o None si mathtext no la entiende."""
    try:
        fig = Figure(figsize=(0.01, 0.01))
        FigureCanvasAgg(fig)
        fig.text(0, 0, f"${latex}$", fontsize=tam, color=_TINTA, math_fontfamily="cm")
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=72 * _ESCALA, transparent=True,
                    bbox_inches="tight", pad_inches=0.05)
        return buf.getvalue()
    except Exception:  # noqa: BLE001 — una fórmula rota no debe tumbar la ventana
        return None


def ecuacion(latex: str, tam: int = 15) -> QLabel:
    """QLabel con la ecuación dibujada (o el LaTeX crudo si no se pudo)."""
    lbl = QLabel()
    datos = _png(latex, tam)
    pm = QPixmap()
    if datos and pm.loadFromData(datos):
        pm.setDevicePixelRatio(_ESCALA)
        lbl.setPixmap(pm)
        lbl.setMinimumSize(int(pm.width() / _ESCALA), int(pm.height() / _ESCALA))
    else:
        lbl.setText(latex)
        lbl.setStyleSheet("font-family:Consolas,monospace; color:#b91c1c;")
    lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    return lbl


def _seccion(titulo: str) -> QLabel:
    t = QLabel(titulo)
    t.setStyleSheet("font-size:11px; font-weight:bold; letter-spacing:.6px; "
                    "text-transform:uppercase; color:#475569; margin-top:10px;")
    return t


def _texto(html: str, estilo: str = "") -> QLabel:
    lbl = QLabel(html)
    lbl.setWordWrap(True)
    lbl.setTextFormat(Qt.TextFormat.RichText)
    lbl.setStyleSheet("font-size:12px; color:#1e293b;" + estilo)
    return lbl


def _caja() -> tuple[QFrame, QVBoxLayout]:
    f = QFrame()
    f.setStyleSheet("QFrame { background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; }"
                    "QLabel { border:none; background:transparent; }")
    v = QVBoxLayout(f)
    v.setContentsMargins(12, 10, 12, 10)
    v.setSpacing(6)
    return f, v


class FormulaDialog(QDialog):
    """Ventana no modal con la fórmula y la sustitución de un ensayo."""

    _ESTADOS = {"ejecutado": ("#15803d", "Ejecutado"),
                "descartado": ("#64748b", "Descartado"),
                "no aplica": ("#94a3b8", "No aplica")}

    def __init__(self, ensayo_id, *, nombre=None, estado=None, ejecuciones=None,
                 motivos=None, detalle_extra=None, parent=None):
        super().__init__(parent)
        self._f = FORMULAS.get(ensayo_id)
        self._ejecuciones = [e for e in (ejecuciones or [])]
        self._detalle_extra = detalle_extra
        self.setWindowTitle(nombre or ensayo_id)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.resize(680, 640)
        self.setStyleSheet("QDialog { background:#ffffff; }")

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)

        # Cabecera
        cab = QWidget()
        cab.setStyleSheet("background:#f1f5f9; border-bottom:1px solid #e2e8f0;")
        hc = QHBoxLayout(cab)
        hc.setContentsMargins(16, 12, 16, 12)
        tit = QLabel(nombre or ensayo_id)
        tit.setStyleSheet("font-size:16px; font-weight:bold; color:#0f172a;")
        tit.setWordWrap(True)
        hc.addWidget(tit, stretch=1)
        if estado in self._ESTADOS:
            color, rot = self._ESTADOS[estado]
            badge = QLabel(rot)
            badge.setStyleSheet(f"background:{color}; color:white; padding:3px 9px; "
                                f"border-radius:5px; font-size:11px; font-weight:bold;")
            hc.addWidget(badge)
        raiz.addWidget(cab)

        # Cuerpo con scroll (horizontal también: una sustitución larga no se achica)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { border:none; background:#ffffff; }")
        cuerpo = QWidget()
        self._v = QVBoxLayout(cuerpo)
        self._v.setContentsMargins(18, 8, 18, 16)
        self._v.setSpacing(6)
        self._scroll.setWidget(cuerpo)
        raiz.addWidget(self._scroll, stretch=1)

        if self._f is None:
            self._v.addWidget(_texto("No hay fórmula registrada para este ensayo."))
        else:
            self._construir(estado, motivos)
        self._v.addStretch()

        pie = QHBoxLayout()
        pie.setContentsMargins(16, 8, 16, 12)
        pie.addStretch()
        cerrar = QPushButton("Cerrar")
        cerrar.clicked.connect(self.close)
        pie.addWidget(cerrar)
        raiz.addLayout(pie)

    # ------------------------------------------------------------------
    def _construir(self, estado, motivos):
        f = self._f
        self._v.addWidget(_seccion("Qué calcula"))
        self._v.addWidget(_texto(f.que))

        if f.general:
            self._v.addWidget(_seccion("Cómo se calcula"))
            for rotulo, latex in f.general:
                self._v.addWidget(_texto(f"<i>{rotulo}</i>", "color:#475569;"))
                self._v.addWidget(ecuacion(latex, 16))

        if f.simbolos:
            grid_w = QWidget()
            g = QGridLayout(grid_w)
            g.setContentsMargins(4, 4, 0, 0)
            g.setHorizontalSpacing(12)
            g.setVerticalSpacing(2)
            for i, (latex, significado) in enumerate(f.simbolos):
                g.addWidget(ecuacion(latex, 12), i, 0)
                g.addWidget(_texto(significado, "color:#475569;"), i, 1)
            g.setColumnStretch(1, 1)
            self._v.addWidget(_texto("<i>donde</i>", "color:#475569;"))
            self._v.addWidget(grid_w)

        if f.iterativo and f.pasos:
            self._v.addWidget(_seccion("Método iterativo"))
            caja, cv = _caja()
            items = "".join(f"<li style='margin-bottom:3px;'>{p}</li>" for p in f.pasos)
            cv.addWidget(_texto(f"<ol style='margin:0; padding-left:18px;'>{items}</ol>"))
            cv.addWidget(_texto(
                "No se muestran las iteraciones intermedias, que serían ilegibles: "
                "el algoritmo se resume en estos pasos y abajo está el resultado final.",
                "color:#64748b; font-size:11px;"))
            self._v.addWidget(caja)

        self._v.addWidget(_seccion("Cómo se hizo con tus datos"))
        if self._ejecuciones and len(self._ejecuciones) > 1:
            fila = QHBoxLayout()
            fila.addWidget(_texto("Corrida:", "color:#475569;"))
            self._cmb = QComboBox()
            for ex in self._ejecuciones:
                self._cmb.addItem(ex.get("ambito") or "(sin ámbito)")
            self._cmb.currentIndexChanged.connect(self._mostrar_ejecucion)
            fila.addWidget(self._cmb, stretch=1)
            self._v.addLayout(fila)

        self._zona = QWidget()
        self._zv = QVBoxLayout(self._zona)
        self._zv.setContentsMargins(0, 0, 0, 0)
        self._zv.setSpacing(6)
        self._v.addWidget(self._zona)

        if self._ejecuciones:
            self._mostrar_ejecucion(0)
        elif estado == "descartado":
            txt = "; ".join(motivos or []) or "el motor eligió la otra rama"
            self._zv.addWidget(_texto(f"No se calculó: <b>se descartó</b> porque {txt}."))
        elif estado == "no aplica":
            self._zv.addWidget(_texto("No se calculó: los datos de esta corrida nunca "
                                      "abrieron esta rama del árbol."))
        elif self._detalle_extra:
            self._zv.addWidget(self._resultado_texto(self._detalle_extra))
        else:
            self._zv.addWidget(_texto("Sin datos de esta corrida.", "color:#64748b;"))

    def _limpiar_zona(self):
        while self._zv.count():
            w = self._zv.takeAt(0).widget()
            if w is not None:
                w.deleteLater()

    def _mostrar_ejecucion(self, i):
        self._limpiar_zona()
        ex = self._ejecuciones[i]
        if ex.get("ambito"):
            self._zv.addWidget(_texto(f"Sobre: <b>{ex['ambito']}</b>", "color:#475569;"))
        valores = ex.get("valores")
        if valores and self._f.sustituir:
            try:
                lineas = self._f.sustituir(valores)
            except Exception:  # noqa: BLE001 — valores incompletos: cae al texto
                lineas = []
            if lineas:
                caja, cv = _caja()
                for rotulo, latex in lineas:
                    cv.addWidget(_texto(f"<i>{rotulo}</i>", "color:#475569;"))
                    cv.addWidget(ecuacion(latex, 15))
                self._zv.addWidget(caja)
                return
        detalle = ex.get("detalle") or self._detalle_extra
        if detalle:
            self._zv.addWidget(self._resultado_texto(detalle))
        else:
            self._zv.addWidget(_texto("El motor no registró números para esta corrida.",
                                      "color:#64748b;"))

    @staticmethod
    def _resultado_texto(detalle):
        caja, cv = _caja()
        cv.addWidget(_texto("Resultado registrado por el motor:", "color:#475569;"))
        lbl = QLabel(detalle)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-family:Consolas,monospace; font-size:13px; color:#0f172a;")
        cv.addWidget(lbl)
        return caja


def abrir_formula(parent, ensayo_id, **kw):
    """Abre la mini ventana (no modal) y la retiene para que no la recolecte el GC."""
    dlg = FormulaDialog(ensayo_id, parent=parent, **kw)
    dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
    abiertas = getattr(parent, "_ventanas_formula", None)
    if abiertas is None:
        abiertas = []
        setattr(parent, "_ventanas_formula", abiertas)
    abiertas.append(dlg)
    dlg.destroyed.connect(lambda *_: abiertas.remove(dlg) if dlg in abiertas else None)
    dlg.show()
    return dlg
