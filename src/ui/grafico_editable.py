"""Gráficos que se pueden retocar sin volver a correr el análisis.

Hasta ahora las figuras se pintaban en un `FigureCanvas` pelado: no había zoom,
ni desplazamiento, ni forma de guardarlas, ni de cambiar un color para que
entren en un póster. Este módulo envuelve cualquier `Figure` y le agrega las
dos capas que faltaban:

1. La **barra de matplotlib** (`NavigationToolbar2QT`), que ya trae zoom,
   desplazamiento, volver al inicio, guardar, y el editor de ejes y curvas que
   matplotlib incluye detrás del ícono de la llave.
2. Un **diálogo propio** con lo que esa barra no cubre: tamaño de letra de toda
   la figura, tamaño y color de los puntos, grilla, leyenda, título y rótulos,
   tamaño de la figura, y líneas de tendencia.

El núcleo son funciones puras sobre `Figure`, sin nada de Qt: así se prueban
sin levantar una ventana, que es donde los tests de interfaz se vuelven lentos
y frágiles.

Dos decisiones que valen la pena explicar:

**Los tamaños originales se guardan la primera vez que se tocan.** Sin eso,
mover el control de fuente tres veces multiplicaría por el factor tres veces y
la letra crecería sin control. Guardando la base, cada cambio se calcula
siempre contra el original y el control es reversible.

**La tendencia se marca con `gid` y se puede sacar.** Es un artista agregado
por quien mira, no un resultado del análisis, así que tiene que poder quitarse
sin dejar rastro, y no debe volver a entrar como dato en un ajuste posterior.
"""
import numpy as np
from matplotlib.collections import PathCollection
from matplotlib.lines import Line2D
from matplotlib.text import Text

GID_TENDENCIA = "biostat_tendencia"
_BASE_FUENTE = "_biostat_fuente_base"
_BASE_TAMANO = "_biostat_tamano_base"

# Menos de esto no es una nube: es un punto de referencia o una marca suelta,
# y ajustarle una recta no significa nada.
MIN_PUNTOS_TENDENCIA = 3


# --------------------------------------------------------------------------
# Núcleo puro: opera sobre Figure. Sin Qt, para que se pueda probar.
# --------------------------------------------------------------------------

def series_de_datos(fig):
    """Las nubes de puntos a las que tiene sentido ajustarles algo.

    Devuelve [(ax, artista, x, y), ...]. Excluye lo que este módulo mismo
    agregó: una tendencia no puede alimentar la siguiente tendencia.
    """
    encontradas = []
    for ax in fig.axes:
        for col in ax.collections:
            if col.get_gid() == GID_TENDENCIA:
                continue
            puntos = getattr(col, "get_offsets", None)
            if not callable(puntos):
                continue
            datos = np.asarray(col.get_offsets())
            if datos.ndim == 2 and datos.shape[0] >= MIN_PUNTOS_TENDENCIA:
                encontradas.append((ax, col, datos[:, 0], datos[:, 1]))
        for linea in ax.lines:
            if linea.get_gid() == GID_TENDENCIA:
                continue
            # Solo las que dibujan marcadores: las rectas de referencia
            # (identidad, límites de acuerdo) son resultados del análisis, no
            # datos que se puedan reajustar.
            if linea.get_marker() in ("", "None", None):
                continue
            x, y = np.asarray(linea.get_xdata()), np.asarray(linea.get_ydata())
            if len(x) >= MIN_PUNTOS_TENDENCIA:
                encontradas.append((ax, linea, x, y))
    return encontradas


def hay_datos_ajustables(fig):
    return bool(series_de_datos(fig))


def escalar_fuentes(fig, factor):
    """Multiplica el tamaño de TODO el texto por `factor`.

    Contra el tamaño original, no contra el actual: si no, llamar dos veces con
    1,2 daría 1,44 y el control dejaría de ser reversible.
    """
    factor = max(0.4, min(4.0, float(factor)))
    for texto in fig.findobj(Text):
        base = getattr(texto, _BASE_FUENTE, None)
        if base is None:
            base = texto.get_fontsize()
            setattr(texto, _BASE_FUENTE, base)
        texto.set_fontsize(base * factor)
    return factor


FAMILIAS = ["(sin cambiar)", "DejaVu Sans", "Arial", "Calibri",
            "Times New Roman", "Georgia", "Courier New", "Consolas"]


def cambiar_fuente(fig, familia):
    """Cambia la familia tipografica de todo el texto.

    Si la familia no esta instalada matplotlib avisa y cae a la de por
    defecto, asi que el peor caso es que no cambie nada; no rompe la figura.
    """
    if not familia or familia == FAMILIAS[0]:
        return None
    for texto in fig.findobj(Text):
        texto.set_fontfamily(familia)
    return familia


def escalar_puntos(fig, factor):
    """Multiplica el tamaño de los marcadores por `factor`, contra el original."""
    factor = max(0.1, min(6.0, float(factor)))
    for ax, artista, _x, _y in series_de_datos(fig):
        if isinstance(artista, PathCollection):
            base = getattr(artista, _BASE_TAMANO, None)
            if base is None:
                base = np.array(artista.get_sizes(), dtype=float)
                setattr(artista, _BASE_TAMANO, base)
            if base.size:
                artista.set_sizes(base * factor)
        elif isinstance(artista, Line2D):
            base = getattr(artista, _BASE_TAMANO, None)
            if base is None:
                base = artista.get_markersize()
                setattr(artista, _BASE_TAMANO, base)
            artista.set_markersize(base * factor)
    return factor


def pintar_puntos(fig, color):
    """Cambia el color de las nubes de puntos."""
    for _ax, artista, _x, _y in series_de_datos(fig):
        if isinstance(artista, PathCollection):
            artista.set_facecolor(color)
        elif isinstance(artista, Line2D):
            artista.set_markerfacecolor(color)
            artista.set_color(color)
    return color


def opacidad_puntos(fig, alfa):
    alfa = max(0.05, min(1.0, float(alfa)))
    for _ax, artista, _x, _y in series_de_datos(fig):
        artista.set_alpha(alfa)
    return alfa


def mostrar_grilla(fig, visible):
    """Prende o apaga la grilla.

    Ojo con `ax.grid(False, alpha=...)`: matplotlib avisa "First parameter to
    grid() is false, but line properties are supplied. The grid will be
    enabled" y la ENCIENDE. O sea que pasar propiedades de linea junto al
    False invierte lo que se pidio. Hay que separar los dos casos.
    """
    visible = bool(visible)
    for ax in fig.axes:
        if visible:
            ax.grid(True, alpha=0.3)
        else:
            ax.grid(False)
    return visible


def mostrar_leyenda(fig, visible, posicion="best"):
    """Muestra u oculta la leyenda de cada eje.

    Un eje sin artistas rotulados no puede tener leyenda: pedirla igual deja un
    recuadro vacío y matplotlib avisa por consola. Se saltean esos ejes.
    """
    for ax in fig.axes:
        leyenda = ax.get_legend()
        if not visible:
            if leyenda is not None:
                leyenda.set_visible(False)
            continue
        etiquetados = [h for h in (ax.get_legend_handles_labels()[1] or [])
                       if h and not h.startswith("_")]
        if not etiquetados:
            continue
        ax.legend(loc=posicion, fontsize=None, framealpha=0.95)
        ax.get_legend().set_visible(True)
    return bool(visible)


def rotular(fig, titulo=None, etiqueta_x=None, etiqueta_y=None):
    """Cambia título y rótulos del primer eje, que es el que el usuario ve."""
    if not fig.axes:
        return
    ax = fig.axes[0]
    if titulo is not None:
        ax.set_title(titulo)
    if etiqueta_x is not None:
        ax.set_xlabel(etiqueta_x)
    if etiqueta_y is not None:
        ax.set_ylabel(etiqueta_y)


def quitar_tendencia(fig):
    """Saca todas las tendencias agregadas. Devuelve cuántas sacó."""
    quitadas = 0
    for ax in fig.axes:
        for artista in list(ax.lines):
            if artista.get_gid() == GID_TENDENCIA:
                artista.remove()
                quitadas += 1
        for col in list(ax.collections):
            if col.get_gid() == GID_TENDENCIA:
                col.remove()
                quitadas += 1
        leyenda = ax.get_legend()
        if leyenda is not None and quitadas:
            etiquetas = [t for t in ax.get_legend_handles_labels()[1]
                         if t and not t.startswith("_")]
            if etiquetas:
                ax.legend(fontsize=None, framealpha=0.95)
            else:
                leyenda.remove()
    return quitadas


def ajustar_tendencia(x, y, grado=1):
    """Ajusta un polinomio y devuelve (coeficientes, r2, texto).

    R² es 1 − SC_residual/SC_total, la definición de siempre. Se informa junto
    a la ecuación porque una recta dibujada sin decir qué tan bien ajusta
    invita a leer una tendencia donde no la hay.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    finito = np.isfinite(x) & np.isfinite(y)
    x, y = x[finito], y[finito]
    grado = int(max(1, min(4, grado)))
    if len(x) < grado + 2:
        return None, None, (f"Hacen falta al menos {grado + 2} puntos para un "
                            f"polinomio de grado {grado}; hay {len(x)}.")
    if np.ptp(x) == 0:
        return None, None, "Todos los valores de X son iguales: no hay pendiente."

    coef = np.polyfit(x, y, grado)
    pred = np.polyval(coef, x)
    sc_res = float(np.sum((y - pred) ** 2))
    sc_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - sc_res / sc_tot if sc_tot > 0 else float("nan")

    if grado == 1:
        ecuacion = f"y = {coef[0]:.4g}·x + {coef[1]:.4g}"
    else:
        partes = []
        for i, c in enumerate(coef):
            p = grado - i
            if p == 0:
                partes.append(f"{c:+.4g}")
            elif p == 1:
                partes.append(f"{c:+.4g}·x")
            else:
                partes.append(f"{c:+.4g}·x^{p}")
        ecuacion = "y = " + " ".join(partes).lstrip("+")
    return coef, r2, f"{ecuacion}   (R² = {r2:.4f})"


def agregar_tendencia(fig, grado=1, color="#7c3aed"):
    """Dibuja una tendencia sobre cada nube de puntos. Devuelve los textos.

    Reemplaza cualquier tendencia anterior: dos ajustes superpuestos sobre los
    mismos datos no se distinguen entre sí.
    """
    quitar_tendencia(fig)
    descripciones = []
    for ax, _artista, x, y in series_de_datos(fig):
        coef, _r2, texto = ajustar_tendencia(x, y, grado)
        if coef is None:
            descripciones.append(texto)
            continue
        x_finito = np.asarray(x, dtype=float)
        x_finito = x_finito[np.isfinite(x_finito)]
        xr = np.linspace(x_finito.min(), x_finito.max(), 200)
        linea, = ax.plot(xr, np.polyval(coef, xr), color=color, lw=2.0,
                         ls="-", zorder=6,
                         label=f"Tendencia (grado {grado}): {texto}")
        linea.set_gid(GID_TENDENCIA)
        descripciones.append(texto)
        etiquetas = [t for t in ax.get_legend_handles_labels()[1]
                     if t and not t.startswith("_")]
        if etiquetas:
            ax.legend(fontsize=None, framealpha=0.95)
    return descripciones


def redimensionar(fig, ancho, alto):
    ancho = max(3.0, min(24.0, float(ancho)))
    alto = max(2.0, min(18.0, float(alto)))
    fig.set_size_inches(ancho, alto)
    return ancho, alto


# --------------------------------------------------------------------------
# Capa Qt: el lienzo con barra, y el diálogo de edición.
# --------------------------------------------------------------------------
from matplotlib.backends.backend_qtagg import (  # noqa: E402
    FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT)
from matplotlib.colors import to_hex  # noqa: E402
from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtGui import QColor  # noqa: E402
from PyQt6.QtWidgets import (  # noqa: E402
    QCheckBox, QColorDialog, QComboBox, QDialog, QDoubleSpinBox, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSlider, QVBoxLayout, QWidget)

POSICIONES = ["best", "upper right", "upper left", "lower left",
              "lower right", "center left", "center right",
              "upper center", "lower center"]

GRADOS = [("Ninguna", 0), ("Lineal", 1), ("Cuadrática", 2), ("Cúbica", 3)]


def _color_actual(fig):
    """El color de la primera nube de puntos, para arrancar el selector ahí."""
    for _ax, artista, _x, _y in series_de_datos(fig):
        try:
            if isinstance(artista, PathCollection):
                caras = artista.get_facecolor()
                if len(caras):
                    return to_hex(caras[0])
            else:
                return to_hex(artista.get_color())
        except (ValueError, TypeError):
            break
    return "#0e7490"


def _alfa_actual(fig):
    for _ax, artista, _x, _y in series_de_datos(fig):
        a = artista.get_alpha()
        if a is not None:
            return float(a)
    return 1.0


class GraficoEditable(QWidget):
    """Un `Figure` con barra de herramientas y botón de edición.

    Se comporta como un `FigureCanvas` para quien lo consuma: expone `figure`
    y `draw`, así el resto de la interfaz (la ventana de informe, por ejemplo)
    lo puede tratar como antes.
    """

    def __init__(self, fig, parent=None):
        super().__init__(parent)
        self.figure = fig
        self.canvas = FigureCanvas(fig)
        self._dialogo = None

        self.barra = NavigationToolbar2QT(self.canvas, self)
        self.barra.setIconSize(self.barra.iconSize() * 0.8)

        boton = QPushButton("Editar…")
        boton.setToolTip("Colores, tamaños, fuente, leyenda y líneas de tendencia")
        boton.clicked.connect(self.abrir_editor)

        fila = QHBoxLayout()
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(4)
        fila.addWidget(self.barra)
        fila.addStretch()
        fila.addWidget(boton)

        caja = QVBoxLayout(self)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.setSpacing(2)
        caja.addLayout(fila)
        caja.addWidget(self.canvas)

    def draw(self):
        self.canvas.draw_idle()

    def abrir_editor(self):
        # Modeless y reutilizado: abrir y cerrar creando uno nuevo cada vez
        # perdería los valores que el usuario ya movió.
        if self._dialogo is None:
            self._dialogo = DialogoEditor(self, self)
        self._dialogo.show()
        self._dialogo.raise_()
        self._dialogo.activateWindow()


class DialogoEditor(QDialog):
    """Controles de estilo, aplicados en vivo sobre la figura."""

    def __init__(self, grafico, parent=None):
        super().__init__(parent)
        self.grafico = grafico
        self.fig = grafico.figure
        self.setWindowTitle("Editar gráfico")
        self.setMinimumWidth(360)

        ax = self.fig.axes[0] if self.fig.axes else None
        ancho, alto = self.fig.get_size_inches()

        # Estado inicial, para que "Restablecer" tenga a dónde volver.
        self._inicial = {
            "titulo": ax.get_title() if ax else "",
            "x": ax.get_xlabel() if ax else "",
            "y": ax.get_ylabel() if ax else "",
            "color": _color_actual(self.fig),
            "alfa": _alfa_actual(self.fig),
            "ancho": float(ancho), "alto": float(alto),
        }
        self._color = self._inicial["color"]

        caja = QVBoxLayout(self)
        caja.setSpacing(8)

        # ---- Rótulos ----
        grupo_txt = QGroupBox("Títulos")
        f1 = QFormLayout(grupo_txt)
        self.ed_titulo = QLineEdit(self._inicial["titulo"])
        self.ed_x = QLineEdit(self._inicial["x"])
        self.ed_y = QLineEdit(self._inicial["y"])
        for campo in (self.ed_titulo, self.ed_x, self.ed_y):
            campo.textChanged.connect(self._aplicar)
        f1.addRow("Título:", self.ed_titulo)
        f1.addRow("Eje X:", self.ed_x)
        f1.addRow("Eje Y:", self.ed_y)
        caja.addWidget(grupo_txt)

        # ---- Estilo ----
        grupo_est = QGroupBox("Estilo")
        f2 = QFormLayout(grupo_est)

        self.sp_fuente = QDoubleSpinBox()
        self.sp_fuente.setRange(0.5, 3.0)
        self.sp_fuente.setSingleStep(0.1)
        self.sp_fuente.setValue(1.0)
        self.sp_fuente.valueChanged.connect(self._aplicar)
        f2.addRow("Tamaño de letra (×):", self.sp_fuente)

        self.cb_fuente = QComboBox()
        self.cb_fuente.addItems(FAMILIAS)
        self.cb_fuente.currentTextChanged.connect(self._aplicar)
        f2.addRow("Tipografía:", self.cb_fuente)

        self.sp_puntos = QDoubleSpinBox()
        self.sp_puntos.setRange(0.2, 5.0)
        self.sp_puntos.setSingleStep(0.1)
        self.sp_puntos.setValue(1.0)
        self.sp_puntos.valueChanged.connect(self._aplicar)
        f2.addRow("Tamaño de puntos (×):", self.sp_puntos)

        self.bt_color = QPushButton()
        self.bt_color.clicked.connect(self._elegir_color)
        self._pintar_boton()
        f2.addRow("Color de puntos:", self.bt_color)

        self.sl_alfa = QSlider(Qt.Orientation.Horizontal)
        self.sl_alfa.setRange(5, 100)
        self.sl_alfa.setValue(int(self._inicial["alfa"] * 100))
        self.sl_alfa.valueChanged.connect(self._aplicar)
        f2.addRow("Opacidad:", self.sl_alfa)

        self.ck_grilla = QCheckBox("Mostrar grilla")
        self.ck_grilla.setChecked(True)
        self.ck_grilla.stateChanged.connect(self._aplicar)
        f2.addRow(self.ck_grilla)

        self.ck_leyenda = QCheckBox("Mostrar leyenda")
        self.ck_leyenda.setChecked(True)
        self.ck_leyenda.stateChanged.connect(self._aplicar)
        self.cb_pos = QComboBox()
        self.cb_pos.addItems(POSICIONES)
        self.cb_pos.currentTextChanged.connect(self._aplicar)
        f2.addRow(self.ck_leyenda, self.cb_pos)
        caja.addWidget(grupo_est)

        # ---- Tendencia ----
        grupo_tend = QGroupBox("Línea de tendencia")
        f3 = QVBoxLayout(grupo_tend)
        self.cb_tend = QComboBox()
        for nombre, _g in GRADOS:
            self.cb_tend.addItem(nombre)
        self.cb_tend.currentIndexChanged.connect(self._aplicar)
        f3.addWidget(self.cb_tend)
        self.lbl_tend = QLabel("")
        self.lbl_tend.setWordWrap(True)
        self.lbl_tend.setStyleSheet("color:#475569; font-size:11px;")
        f3.addWidget(self.lbl_tend)
        if not hay_datos_ajustables(self.fig):
            self.cb_tend.setEnabled(False)
            # Decir por qué está apagado: un control gris sin motivo se lee
            # como una falla de la aplicación.
            self.lbl_tend.setText(
                "Este gráfico no tiene una nube de puntos a la que ajustarle "
                "una tendencia.")
        caja.addWidget(grupo_tend)

        # ---- Tamaño y exportación ----
        grupo_exp = QGroupBox("Tamaño y exportación")
        f4 = QFormLayout(grupo_exp)
        self.sp_ancho = QDoubleSpinBox()
        self.sp_ancho.setRange(3.0, 24.0)
        self.sp_ancho.setSingleStep(0.5)
        self.sp_ancho.setValue(self._inicial["ancho"])
        self.sp_ancho.valueChanged.connect(self._aplicar)
        self.sp_alto = QDoubleSpinBox()
        self.sp_alto.setRange(2.0, 18.0)
        self.sp_alto.setSingleStep(0.5)
        self.sp_alto.setValue(self._inicial["alto"])
        self.sp_alto.valueChanged.connect(self._aplicar)
        medidas = QHBoxLayout()
        medidas.addWidget(self.sp_ancho)
        medidas.addWidget(QLabel("×"))
        medidas.addWidget(self.sp_alto)
        f4.addRow("Pulgadas:", medidas)

        self.sp_dpi = QDoubleSpinBox()
        self.sp_dpi.setRange(72, 600)
        self.sp_dpi.setSingleStep(50)
        self.sp_dpi.setValue(300)
        self.sp_dpi.setDecimals(0)
        f4.addRow("Resolución (ppp):", self.sp_dpi)
        caja.addWidget(grupo_exp)

        # ---- Botones ----
        botones = QHBoxLayout()
        bt_reset = QPushButton("Restablecer")
        bt_reset.clicked.connect(self._restablecer)
        bt_guardar = QPushButton("Guardar imagen…")
        bt_guardar.clicked.connect(self._guardar)
        bt_cerrar = QPushButton("Cerrar")
        bt_cerrar.clicked.connect(self.close)
        botones.addWidget(bt_reset)
        botones.addStretch()
        botones.addWidget(bt_guardar)
        botones.addWidget(bt_cerrar)
        caja.addLayout(botones)

    # ------------------------------------------------------------------
    def _pintar_boton(self):
        self.bt_color.setText(self._color)
        self.bt_color.setStyleSheet(
            f"background:{self._color}; color:white; padding:4px;")

    def _elegir_color(self):
        elegido = QColorDialog.getColor(QColor(self._color), self,
                                        "Color de los puntos")
        if elegido.isValid():
            self._color = elegido.name()
            self._pintar_boton()
            self._aplicar()

    def _aplicar(self):
        rotular(self.fig, self.ed_titulo.text(), self.ed_x.text(),
                self.ed_y.text())
        escalar_fuentes(self.fig, self.sp_fuente.value())
        cambiar_fuente(self.fig, self.cb_fuente.currentText())
        escalar_puntos(self.fig, self.sp_puntos.value())
        pintar_puntos(self.fig, self._color)
        opacidad_puntos(self.fig, self.sl_alfa.value() / 100.0)
        mostrar_grilla(self.fig, self.ck_grilla.isChecked())

        grado = GRADOS[self.cb_tend.currentIndex()][1]
        if grado == 0:
            quitar_tendencia(self.fig)
            if self.cb_tend.isEnabled():
                self.lbl_tend.setText("")
        else:
            textos = agregar_tendencia(self.fig, grado)
            self.lbl_tend.setText("\n".join(textos))

        # La leyenda va DESPUÉS de la tendencia: agregarla o sacarla cambia las
        # entradas, y una leyenda armada antes quedaría desactualizada.
        mostrar_leyenda(self.fig, self.ck_leyenda.isChecked(),
                        self.cb_pos.currentText())
        redimensionar(self.fig, self.sp_ancho.value(), self.sp_alto.value())
        self.grafico.draw()

    def _restablecer(self):
        for control, valor in ((self.sp_fuente, 1.0), (self.sp_puntos, 1.0),
                               (self.sp_ancho, self._inicial["ancho"]),
                               (self.sp_alto, self._inicial["alto"])):
            control.blockSignals(True)
            control.setValue(valor)
            control.blockSignals(False)
        for campo, clave in ((self.ed_titulo, "titulo"), (self.ed_x, "x"),
                             (self.ed_y, "y")):
            campo.blockSignals(True)
            campo.setText(self._inicial[clave])
            campo.blockSignals(False)
        self.sl_alfa.blockSignals(True)
        self.sl_alfa.setValue(int(self._inicial["alfa"] * 100))
        self.sl_alfa.blockSignals(False)
        self.cb_tend.blockSignals(True)
        self.cb_tend.setCurrentIndex(0)
        self.cb_tend.blockSignals(False)
        self.cb_fuente.blockSignals(True)
        self.cb_fuente.setCurrentIndex(0)
        self.cb_fuente.blockSignals(False)
        self.ck_grilla.blockSignals(True)
        self.ck_grilla.setChecked(True)
        self.ck_grilla.blockSignals(False)
        self.ck_leyenda.blockSignals(True)
        self.ck_leyenda.setChecked(True)
        self.ck_leyenda.blockSignals(False)
        self._color = self._inicial["color"]
        self._pintar_boton()
        self._aplicar()

    def _guardar(self):
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar gráfico", "grafico.png",
            "PNG (*.png);;SVG (*.svg);;PDF (*.pdf);;TIFF (*.tif)")
        if not ruta:
            return
        try:
            self.fig.savefig(ruta, dpi=int(self.sp_dpi.value()),
                             bbox_inches="tight")
        except Exception as e:  # noqa: BLE001 - se le muestra al usuario
            self.lbl_tend.setText(f"No se pudo guardar: {e}")
