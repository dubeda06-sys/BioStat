"""Panel de graficos."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QPushButton, QLabel, QGroupBox, QFormLayout,
    QFileDialog, QScrollArea, QSplitter
)
from PyQt6.QtCore import Qt
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import numpy as np

from src.ui.icons import Icons

COLORS = ['#4f6ef7', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']
plt.rcParams.update({
    'figure.facecolor': 'white', 'axes.facecolor': '#fafbfd',
    'axes.edgecolor': '#d8dbe3', 'axes.grid': True,
    'grid.alpha': 0.25, 'grid.color': '#d8dbe3',
    'font.size': 11, 'axes.titlesize': 13, 'axes.labelsize': 12,
})

GRAPH_HELP = {
    "Histograma": "Muestra la distribucion de frecuencias de una variable. La linea roja es la media y la verde la mediana. Util para ver si los datos son normales.",
    "Diagrama de caja": "Muestra la mediana, cuartiles y valores atipicos (outliers). Util para comparar distribuciones y detectar datos anomalos.",
    "Dispersion": "Grafica dos variables una contra otra. Muestra si hay relacion entre ellas. La linea punteada es la tendencia lineal.",
    "Barras": "Muestra la frecuencia de cada categoria. Util para variables categoricas o conteos.",
    "Serie temporal": "Muestra como cambia una variable a lo largo del tiempo o secuencia. La linea punteada es la media movil.",
}


class GraphsPanel(QWidget):
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

        cfg = QGroupBox(f"    Configuracion")
        cl = QFormLayout()
        cl.setSpacing(4)
        cl.setContentsMargins(6, 6, 6, 6)

        self.combo_graph = QComboBox()
        self.combo_graph.addItems(list(GRAPH_HELP.keys()))
        self.combo_graph.currentIndexChanged.connect(self._on_type)
        self.combo_graph.setMinimumHeight(28)
        cl.addRow("Tipo:", self.combo_graph)

        self.lbl_help = QLabel(GRAPH_HELP["Histograma"])
        self.lbl_help.setObjectName("subtitle")
        self.lbl_help.setWordWrap(True)
        self.lbl_help.setStyleSheet("color: #6b7280; font-style: italic; padding: 1px 0; font-size: 10px;")
        cl.addRow("", self.lbl_help)

        self.combo_col1 = QComboBox()
        self.combo_col1.setMinimumHeight(28)
        cl.addRow("Var X:", self.combo_col1)

        self.combo_col2 = QComboBox()
        self.combo_col2.setMinimumHeight(28)
        self.combo_col2.setEnabled(False)
        cl.addRow("Var Y:", self.combo_col2)

        cfg.setLayout(cl)
        left_l.addWidget(cfg)

        br = QHBoxLayout()
        br.setSpacing(4)
        self.btn_plot = QPushButton(f" Generar")
        self.btn_plot.setMinimumHeight(30)
        self.btn_plot.clicked.connect(self._plot)
        br.addWidget(self.btn_plot)
        self.btn_save = QPushButton(f"")
        self.btn_save.setObjectName("secondary")
        self.btn_save.setMinimumHeight(30)
        self.btn_save.clicked.connect(self._save)
        br.addWidget(self.btn_save)
        left_l.addLayout(br)

        left_l.addStretch()
        left.setMaximumWidth(260)
        left.setMinimumWidth(220)
        splitter.addWidget(left)

        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(4)

        gb = QGroupBox(f"    Vista previa")
        gl = QVBoxLayout()
        gl.setContentsMargins(4, 2, 4, 2)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.ph = QLabel(f"<div style='text-align:center;color:#a0a8b8;padding:40px;'> Selecciona tipo y haz clic en Generar</div>")
        self.ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setWidget(self.ph)
        gl.addWidget(self.scroll)
        gb.setLayout(gl)
        right_l.addWidget(gb)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    def _on_type(self, i):
        t = self.combo_graph.currentText()
        self.lbl_help.setText(GRAPH_HELP.get(t, ""))
        self.combo_col2.setEnabled(t in ("Dispersion",))

    def set_data(self, data):
        self.data = data
        if data is not None:
            self.combo_col1.clear()
            self.combo_col2.clear()
            self.combo_col1.addItems(data.columns.tolist())
            self.combo_col2.addItems(data.columns.tolist())

    def _plot(self):
        if self.data is None:
            return
        t = self.combo_graph.currentText()
        c1, c2 = self.combo_col1.currentText(), self.combo_col2.currentText()
        fig = {"Histograma": self._hist, "Diagrama de caja": self._box,
               "Dispersion": self._scatter, "Barras": self._bar,
               "Serie temporal": self._ts}.get(t)
        if fig:
            result = fig(c1, c2)
            if result:
                self.canvas = FigureCanvas(result)
                self.scroll.setWidget(self.canvas)
                plt.close(result)

    def _hist(self, col, _=None):
        if col not in self.data.columns:
            return None
        d = self.data[col].dropna()
        if not np.issubdtype(d.dtype, np.number):
            return None
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.hist(d, bins=30, edgecolor='white', alpha=0.85, color=COLORS[0])
        ax.axvline(d.mean(), color=COLORS[3], ls='--', lw=1.5, label=f'Media {d.mean():.2f}')
        ax.axvline(d.median(), color=COLORS[1], ls='--', lw=1.5, label=f'Mediana {d.median():.2f}')
        ax.set_title(col, fontweight='bold')
        ax.legend(framealpha=0.9)
        fig.tight_layout()
        return fig

    def _box(self, col, _=None):
        if col not in self.data.columns:
            return None
        d = self.data[col].dropna()
        if not np.issubdtype(d.dtype, np.number):
            return None
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.boxplot(d, vert=True, patch_artist=True,
                   boxprops=dict(facecolor=COLORS[0], alpha=0.6),
                   medianprops=dict(color=COLORS[3], lw=2))
        ax.set_title(col, fontweight='bold')
        ax.set_xticklabels([col])
        txt = f"Media: {d.mean():.2f}\nDE: {d.std():.2f}\nn: {len(d)}"
        ax.text(0.98, 0.98, txt, transform=ax.transAxes, va='top', ha='right',
               bbox=dict(boxstyle='round', fc='white', alpha=0.9), fontsize=10, family='monospace')
        fig.tight_layout()
        return fig

    def _scatter(self, c1, c2):
        if c1 not in self.data.columns or c2 not in self.data.columns:
            return None
        d1, d2 = self.data[c1].dropna(), self.data[c2].dropna()
        n = min(len(d1), len(d2))
        if n < 2:
            return None
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.scatter(d1[:n], d2[:n], alpha=0.5, c=COLORS[0], edgecolors='white', s=50)
        z = np.polyfit(d1[:n], d2[:n], 1)
        xl = np.linspace(d1[:n].min(), d1[:n].max(), 100)
        ax.plot(xl, np.poly1d(z)(xl), color=COLORS[3], ls='--', lw=1.5)
        r = np.corrcoef(d1[:n], d2[:n])[0, 1]
        ax.text(0.02, 0.98, f'r = {r:.3f}', transform=ax.transAxes, va='top',
               bbox=dict(boxstyle='round', fc='white', alpha=0.9))
        ax.set_title(f'{c1} vs {c2}', fontweight='bold')
        ax.set_xlabel(c1)
        ax.set_ylabel(c2)
        fig.tight_layout()
        return fig

    def _bar(self, col, _=None):
        if col not in self.data.columns:
            return None
        d = self.data[col].dropna()
        fig, ax = plt.subplots(figsize=(9, 5))
        counts = d.value_counts().head(15)
        bars = ax.bar(range(len(counts)), counts.values,
                     color=[COLORS[i % len(COLORS)] for i in range(len(counts))], edgecolor='white')
        ax.set_xticks(range(len(counts)))
        ax.set_xticklabels(counts.index, rotation=45, ha='right')
        for b, v in zip(bars, counts.values):
            ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.5, str(v),
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        ax.set_title(col, fontweight='bold')
        fig.tight_layout()
        return fig

    def _ts(self, col, _=None):
        if col not in self.data.columns:
            return None
        d = self.data[col].dropna()
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.plot(range(1, len(d)+1), d.values, color=COLORS[0], marker='o', ms=4, lw=1.5)
        w = min(5, len(d))
        if w > 1:
            rm = d.rolling(w).mean()
            ax.plot(range(1, len(d)+1), rm.values, color=COLORS[3], ls='--', lw=1.5, label=f'MM({w})')
            ax.legend()
        ax.set_title(col, fontweight='bold')
        ax.set_xlabel('Observacion')
        fig.tight_layout()
        return fig

    def _save(self):
        if self.canvas is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Guardar", "", "PNG (*.png);;PDF (*.pdf);;SVG (*.svg)")
        if path:
            self.canvas.figure.savefig(path, dpi=300, bbox_inches='tight', facecolor='white')
