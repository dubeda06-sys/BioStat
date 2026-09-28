"""Panel de analisis estadistico."""
from html import escape

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QPushButton, QLabel, QTextEdit, QGroupBox,
    QLineEdit, QFormLayout, QScrollArea, QSplitter
)
from PyQt6.QtCore import Qt
import matplotlib
matplotlib.use('QtAgg')
from src.ui.grafico_editable import GraficoEditable
import matplotlib.pyplot as plt

from src.ui.icons import Icons
from src.resultado import render_html

plt.rcParams.update({
    'figure.facecolor': 'white', 'axes.facecolor': '#fafbfd',
    'axes.edgecolor': '#d8dbe3', 'axes.grid': True,
    'grid.alpha': 0.25, 'grid.color': '#d8dbe3',
    'font.size': 11, 'axes.titlesize': 13,
})

from src.ui.help_text import ANALYSIS_HELP
from src.ui import entradas
from src.ui.combos import rellenar



class AnalysisPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.data = None
        self.canvas = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(10, 4, 10, 4)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)
        left_l.setSpacing(4)

        cfg = QGroupBox("    Configuración")
        cl = QFormLayout()
        cl.setSpacing(4)
        cl.setContentsMargins(6, 6, 6, 6)

        self.combo_analysis = QComboBox()
        self.combo_analysis.addItems(list(ANALYSIS_HELP.keys()))
        self.combo_analysis.setMinimumHeight(28)
        self.combo_analysis.currentTextChanged.connect(self._on_analysis_changed)
        cl.addRow("Análisis:", self.combo_analysis)

        self.lbl_help = QLabel(ANALYSIS_HELP["Estadisticas descriptivas"])
        self.lbl_help.setObjectName("subtitle")
        self.lbl_help.setWordWrap(True)
        self.lbl_help.setStyleSheet("color: #6b7280; font-style: italic; padding: 1px 0; font-size: 10px;")
        
        # Antes había debajo una «Descripción» que repetía esta misma ayuda y
        # una fórmula escrita a mano, anterior a las auditorías, que podía no
        # ser la que se calcula. La fórmula de verdad, con sus citas, la trae
        # el Resultado al ejecutar (recuadro «Fórmula»).
        cl.addRow("", self.lbl_help)

        self.combo_col1 = QComboBox()
        self.combo_col1.setMinimumHeight(28)
        cl.addRow("Var 1:", self.combo_col1)

        self.combo_col2 = QComboBox()
        self.combo_col2.setMinimumHeight(28)
        cl.addRow("Var 2:", self.combo_col2)

        self.combo_col3 = QComboBox()
        self.combo_col3.setMinimumHeight(28)
        cl.addRow("Var 3:", self.combo_col3)

        self.input_alpha = QLineEdit("0.05")
        self.input_alpha.setMaximumWidth(60)
        self.input_alpha.setMinimumHeight(28)
        cl.addRow("Alpha:", self.input_alpha)

        cfg.setLayout(cl)
        left_l.addWidget(cfg)

        br = QHBoxLayout()
        br.setSpacing(4)
        self.btn_run = QPushButton("Ejecutar")
        self.btn_run.setIcon(Icons.RUN())
        self.btn_run.setMinimumHeight(30)
        self.btn_run.clicked.connect(self._run)
        br.addWidget(self.btn_run)
        btn_clr = QPushButton("Limpiar")
        btn_clr.setIcon(Icons.CLEAR())
        btn_clr.setObjectName("secondary")
        btn_clr.setMinimumHeight(30)
        btn_clr.clicked.connect(self._clear)
        br.addWidget(btn_clr)
        left_l.addLayout(br)

        fg = QGroupBox("Fórmula")
        fl = QVBoxLayout()
        fl.setContentsMargins(4, 2, 4, 2)
        self.txt_formula = QTextEdit()
        self.txt_formula.setReadOnly(True)
        self.txt_formula.setMinimumHeight(140)
        self.txt_formula.setPlaceholderText("La fórmula aparece al ejecutar, con sus citas.")
        self.txt_formula.setStyleSheet("QTextEdit { font-family: Consolas, monospace; font-size: 10px; background: #f8f9fa; border: 1px solid #e8eaf0; border-radius: 4px; padding: 3px; }")
        fl.addWidget(self.txt_formula)
        fg.setLayout(fl)
        left_l.addWidget(fg)

        left.setMaximumWidth(300)
        left.setMinimumWidth(260)
        splitter.addWidget(left)

        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(4)

        rg = QGroupBox(f"    Resultados")
        rl = QVBoxLayout()
        rl.setContentsMargins(4, 2, 4, 2)
        self.txt_results = QTextEdit()
        self.txt_results.setReadOnly(True)
        self.txt_results.setPlaceholderText("Resultados...")
        rl.addWidget(self.txt_results)
        rg.setLayout(rl)
        right_l.addWidget(rg, stretch=2)

        pg = QGroupBox("    Gráfico")
        pl = QVBoxLayout()
        pl.setContentsMargins(4, 2, 4, 2)
        self.graph_scroll = QScrollArea()
        self.graph_scroll.setWidgetResizable(True)
        self.graph_ph = QLabel("<div style='text-align:center;color:#a0a8b8;padding:20px;'> El gráfico aparece acá</div>")
        self.graph_ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.graph_scroll.setWidget(self.graph_ph)
        pl.addWidget(self.graph_scroll)
        pg.setLayout(pl)
        right_l.addWidget(pg, stretch=3)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    def _on_analysis_changed(self, text):
        self.lbl_help.setText(ANALYSIS_HELP.get(text, ""))
        # Lo que dejo el dialogo es de UN analisis: al cambiar de analisis no
        # puede quedar colgado para el siguiente.
        self.opciones_metodo = {}
        self.columnas_elegidas = None
        self.parametros = {}

    def set_data(self, data):
        """Carga las columnas sin perder lo elegido: se llama cada vez que se
        entra a la pestaña. La Variable 2 arranca en la segunda columna; si
        arrancaba en la primera, igual que la 1, un Bland-Altman salía de una
        columna contra sí misma."""
        self.data = data
        if data is not None:
            cols = data.columns.tolist()
            rellenar(self.combo_col1, cols, 0)
            rellenar(self.combo_col2, cols, 1)
            rellenar(self.combo_col3, ["(ninguna)"] + cols, 0)

    # Decisiones de metodo que deja el dialogo (ver analysis_specs.OPCIONES).
    # Vacio = cada analisis usa sus valores por defecto.
    opciones_metodo: dict = {}
    # Columnas tildadas en el dialogo (analysis_specs.MULTI). None = no hubo
    # dialogo: se usan todas las numericas y el informe las nombra.
    columnas_elegidas = None
    # Parametros numericos del dialogo (analysis_specs.PARAMETROS), como texto.
    parametros: dict = {}

    def _run(self):
        if self.data is None:
            self.txt_results.setHtml(f"<div style='color:#d97706;padding:12px;'> <b>Sin datos.</b> Importa un archivo en la pestaña Datos.</div>")
            return

        at = self.combo_analysis.currentText()
        if at not in entradas.ENTRADAS:
            return
        c3 = self.combo_col3.currentText()
        try:
            alpha = float(self.input_alpha.text())
        except ValueError:
            alpha = 0.05
        self._mostrar_resultado(self.correr(
            at, self.combo_col1.currentText() or None, self.combo_col2.currentText() or None,
            None if c3 in ("", "(ninguna)") else c3, alpha))

    def correr(self, nombre, c1=None, c2=None, c3=None, alpha=0.05):
        """El análisis `nombre` con estas variables y lo que dejó el diálogo.

        Lo arma `src/ui/entradas.py`; acá solo se junta el estado del panel.
        Devuelve el `Resultado` sin mostrarlo.
        """
        return entradas.correr(nombre, entradas.Eleccion(
            self.data, c1, c2, c3, alpha, dict(self.opciones_metodo or {}),
            self.columnas_elegidas, dict(self.parametros or {})))

    def _mostrar_resultado(self, res):
        self.txt_results.setHtml(render_html(res))
        if not res.ok:
            return
        if res.formula:
            titulo = res.metodo.nombre if res.metodo else res.titulo
            self._set_formula(f"Fórmula: {titulo}", res.formula)
        if res.figuras:
            self._mostrar_figuras(res.figuras)

    def _mostrar_figuras(self, figuras):
        """Una figura va sola, como siempre. Varias se apilan con su titulo, igual
        que en la pestaña Graficos del Omnianalisis: se ven todas sin tener que
        elegir, y la ventana de informe se lleva el bloque entero."""
        if len(figuras) == 1:
            self._show_fig(figuras[0].dibujar())
            return
        anterior = self._vaciar_grafico()
        if anterior is not None:
            anterior.deleteLater()
        bloque = QWidget()
        caja = QVBoxLayout(bloque)
        caja.setContentsMargins(0, 0, 0, 0)
        for figura in figuras:
            fig = figura.dibujar()
            titulo = QLabel(figura.titulo)
            titulo.setStyleSheet("font-weight:bold; color:#2c3650; padding:8px 2px 2px;")
            caja.addWidget(titulo)
            grafico = GraficoEditable(fig)
            grafico.setMinimumHeight(380)
            caja.addWidget(grafico)
            plt.close(fig)
        self.canvas = bloque
        self.graph_scroll.setWidget(bloque)

    def _vaciar_grafico(self):
        """Saca lo que haya en el area de grafico y lo devuelve.

        `QScrollArea.setWidget` se queda con la propiedad del widget y destruye
        el anterior: poner un grafico borraba el cartel de "aparecera aqui", y
        el siguiente `_clear` reventaba con "wrapped C/C++ object of type QLabel
        has been deleted". `takeWidget` devuelve la propiedad primero.
        """
        actual = self.graph_scroll.takeWidget()
        return None if actual is self.graph_ph else actual

    def _show_fig(self, fig):
        anterior = self._vaciar_grafico()
        if anterior is not None:
            anterior.deleteLater()
        # GraficoEditable y no FigureCanvas pelado: agrega la barra de
        # matplotlib (zoom, desplazamiento, guardar) y el dialogo de estilo.
        # Expone .figure y .draw(), asi que la ventana de informe lo sigue
        # tratando igual que antes.
        self.canvas = GraficoEditable(fig)
        self.graph_scroll.setWidget(self.canvas)
        plt.close(fig)

    def tomar_grafico(self):
        """Entrega el grafico actual (para la ventana de informe) y repone el cartel."""
        canvas = self._vaciar_grafico()
        self.canvas = None
        self.graph_scroll.setWidget(self.graph_ph)
        return canvas

    def _clear(self):
        self.txt_results.clear()
        self.txt_formula.clear()
        anterior = self._vaciar_grafico()
        if anterior is not None:
            anterior.deleteLater()
        self.graph_scroll.setWidget(self.graph_ph)

    def _set_formula(self, title, formula_text):
        """La fórmula en el recuadro de la izquierda, una línea por renglón.

        Antes se pegaba sin convertir los saltos de línea y las ocho o diez
        líneas de una fórmula salían como un solo párrafo corrido.
        """
        cuerpo = escape(formula_text).replace("\n", "<br>")
        self.txt_formula.setHtml(
            f"<p style='margin:0 0 6px 0;font-weight:700;color:#0e7490;'>{escape(title)}</p>"
            f"<p style='margin:0;font-family:Consolas,monospace;color:#1a1a1a;'>{cuerpo}</p>")

    # --- Estadisticas descriptivas ---
