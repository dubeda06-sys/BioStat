"""Panel de control de calidad."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QPushButton, QLabel, QGroupBox, QFormLayout,
    QTextEdit, QFileDialog, QScrollArea, QLineEdit,
    QSplitter
)
from PyQt6.QtCore import Qt
from scipy import stats
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas  # noqa: E402
import matplotlib.pyplot as plt
import numpy as np

from src.ui.icons import Icons

COLORS = ['#4f6ef7', '#22c55e', '#f59e0b', '#ef4444']
plt.rcParams.update({
    'figure.facecolor': 'white', 'axes.facecolor': '#fafbfd',
    'axes.edgecolor': '#d8dbe3', 'axes.grid': True,
    'grid.alpha': 0.25, 'grid.color': '#d8dbe3', 'font.size': 11,
})

QC_HELP = {
    "Levey-Jennings": "Genera el gráfico clásico de control estadístico de la calidad. Muestra cada medición del material de control (eje Y) a lo largo del tiempo (eje X) frente a su media esperada y las desviaciones estándar (±1SD, ±2SD, ±3SD). Úselo diariamente para monitorear visualmente si el método analítico se mantiene estable o si hay desplazamientos repentinos (shifts) que sugieran un problema.",
    "Westgard": "Aplica automáticamente las reglas múltiples de Westgard (ej. 1-3s, 2-2s, 4-1s, 10x) para detectar errores aleatorios o sistemáticos en el control de calidad interno. Úselo para decidir objetivamente si un lote analítico debe ser aceptado o rechazado antes de reportar resultados de pacientes.",
    "Estadisticas": "Proporciona el resumen numérico del control interno: media observada, desviación estándar (DE), coeficiente de variación (CV%) y Z-scores. Úselo mensualmente para verificar la precisión a largo plazo; idealmente, el CV% debe ser menor al límite aceptable para el analito.",
    "Tendencias": "Realiza un análisis de regresión lineal sobre los datos del control para detectar tendencias significativas (drifts) a lo largo del tiempo. Úselo para anticipar problemas de calibración, degradación de reactivos o envejecimiento de la lámpara antes de que las reglas de Westgard fallen.",
}


class QCPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.data = None
        self.canvas = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(10, 4, 10, 4)

        vsplitter = QSplitter(Qt.Orientation.Vertical)

        top = QWidget()
        top_l = QVBoxLayout(top)
        top_l.setContentsMargins(0, 0, 0, 0)
        top_l.setSpacing(4)

        cfg = QGroupBox(f"  {Icons.GEAR}  Parametros")
        cl = QFormLayout()
        cl.setSpacing(6)
        cl.setContentsMargins(8, 8, 8, 8)

        self.combo_qc = QComboBox()
        self.combo_qc.addItems(list(QC_HELP.keys()))
        self.combo_qc.setMinimumHeight(30)
        self.combo_qc.currentTextChanged.connect(self._on_qc_changed)
        cl.addRow("Analisis:", self.combo_qc)

        self.lbl_help = QLabel(QC_HELP["Levey-Jennings"])
        self.lbl_help.setObjectName("subtitle")
        self.lbl_help.setWordWrap(True)
        self.lbl_help.setStyleSheet("color: #6b7280; font-style: italic; padding: 2px 0; font-size: 11px;")
        cl.addRow("", self.lbl_help)

        self.combo_analyte = QComboBox()
        self.combo_analyte.setMinimumHeight(30)
        cl.addRow("Analyto:", self.combo_analyte)

        self.input_mean = QLineEdit()
        self.input_mean.setPlaceholderText("Auto")
        self.input_mean.setMaximumWidth(120)
        self.input_mean.setMinimumHeight(30)
        cl.addRow("Media:", self.input_mean)

        self.input_sd = QLineEdit()
        self.input_sd.setPlaceholderText("Auto")
        self.input_sd.setMaximumWidth(120)
        self.input_sd.setMinimumHeight(30)
        cl.addRow("SD:", self.input_sd)

        cfg.setLayout(cl)
        top_l.addWidget(cfg)

        br = QHBoxLayout()
        br.setSpacing(4)
        self.btn_run = QPushButton(f"{Icons.RUN} Ejecutar")
        self.btn_run.setMinimumHeight(32)
        self.btn_run.clicked.connect(self._run)
        br.addWidget(self.btn_run)
        self.btn_save = QPushButton(f"{Icons.SAVE} Guardar")
        self.btn_save.setObjectName("secondary")
        self.btn_save.setMinimumHeight(32)
        self.btn_save.clicked.connect(self._save)
        br.addWidget(self.btn_save)
        top_l.addLayout(br)

        top.setMaximumHeight(220)
        vsplitter.addWidget(top)

        bottom = QWidget()
        bottom_l = QVBoxLayout(bottom)
        bottom_l.setContentsMargins(0, 0, 0, 0)
        bottom_l.setSpacing(4)

        hsplitter = QSplitter(Qt.Orientation.Horizontal)

        gb = QGroupBox(f"  {Icons.CHART}  Grafico")
        gl = QVBoxLayout()
        gl.setContentsMargins(6, 4, 6, 4)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.ph = QLabel(f"<div style='text-align:center;color:#a0a8b8;padding:30px;'>{Icons.CHART} Grafico de control</div>")
        self.ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setWidget(self.ph)
        gl.addWidget(self.scroll)
        gb.setLayout(gl)
        hsplitter.addWidget(gb)

        rb = QGroupBox(f"  {Icons.DOC}  Resultados")
        rl = QVBoxLayout()
        rl.setContentsMargins(6, 4, 6, 4)
        self.txt = QTextEdit()
        self.txt.setReadOnly(True)
        self.txt.setPlaceholderText("Resultados del control de calidad...")
        rl.addWidget(self.txt)
        rb.setLayout(rl)
        hsplitter.addWidget(rb)

        hsplitter.setStretchFactor(0, 3)
        hsplitter.setStretchFactor(1, 1)
        bottom_l.addWidget(hsplitter)

        vsplitter.addWidget(bottom)
        vsplitter.setStretchFactor(0, 0)
        vsplitter.setStretchFactor(1, 1)
        layout.addWidget(vsplitter)

    def _on_qc_changed(self, text):
        self.lbl_help.setText(QC_HELP.get(text, ""))

    def set_data(self, data):
        self.data = data
        if data is not None:
            self.combo_analyte.clear()
            self.combo_analyte.addItems(data.columns.tolist())

    def _params(self, col):
        d = self.data[col].dropna()
        try:
            m = float(self.input_mean.text()) if self.input_mean.text() else d.mean()
        except ValueError:
            m = d.mean()
        try:
            s = float(self.input_sd.text()) if self.input_sd.text() else d.std()
        except ValueError:
            s = d.std()
        return d, m, s

    def _run(self):
        if self.data is None:
            self.txt.setHtml(f"<div style='color:#d97706;padding:12px;'>{Icons.WARN} <b>Sin datos.</b> Ve a la pestaña <b>Datos</b> para importar o escribir datos de control.</div>")
            return
        a = self.combo_analyte.currentText()
        t = self.combo_qc.currentText()
        {"Levey-Jennings": self._lj, "Westgard": self._wj,
         "Estadisticas": self._st, "Tendencias": self._tr}.get(t, lambda x: None)(a)

    def _r(self, label, v):
        return f"<tr><td style='padding:2px 12px 2px 0;color:#8892a4;'>{label}</td><td style='padding:2px 0;font-weight:600;'>{v}</td></tr>"

    def _wj_rules(self, data, m, s):
        if s == 0:
            return []
        z = (data - m) / s
        v = []
        for i in range(len(z)):
            if abs(z[i]) > 3:
                v.append(f"1-3s en punto #{i+1} (z={z[i]:.2f})")
        for i in range(len(z)-1):
            if abs(z[i]) > 2 and abs(z[i+1]) > 2 and np.sign(z[i]) == np.sign(z[i+1]):
                v.append(f"2-2s en puntos #{i+1}-#{i+2}")
        for i in range(len(z)-3):
            if all(abs(z[i:i+4]) > 1):
                v.append(f"4-1s en puntos #{i+1}-#{i+4}")
        for i in range(len(z)-9):
            if all(z[i:i+10] > 0) or all(z[i:i+10] < 0):
                v.append(f"10x en puntos #{i+1}-#{i+10}")
        return v

    def _show(self, fig):
        self.canvas = FigureCanvas(fig)
        self.scroll.setWidget(self.canvas)
        plt.close(fig)

    def _lj(self, a):
        if a not in self.data.columns:
            return
        d, m, s = self._params(a)
        if len(d) < 2:
            return
        fig, ax = plt.subplots(figsize=(11, 5))
        x = range(1, len(d)+1)
        ax.plot(x, d.values, color=COLORS[0], marker='o', ms=3, lw=1.5)
        ax.axhline(m, color=COLORS[1], lw=2, label=f'Media {m:.2f}')
        for i, c in [(1, COLORS[2]), (2, COLORS[2]), (3, COLORS[3])]:
            ax.axhline(m+i*s, color=c, ls='--', alpha=0.6, label=f'±{i}SD')
            ax.axhline(m-i*s, color=c, ls='--', alpha=0.6)
        ax.fill_between(x, m-2*s, m+2*s, alpha=0.08, color=COLORS[1])
        ax.set_title(f'Levey-Jennings — {a}', fontweight='bold')
        ax.legend(loc='upper right', fontsize=8, framealpha=0.9)
        fig.tight_layout()
        self._show(fig)

        v = self._wj_rules(d.values, m, s)
        o2 = int(np.sum(np.abs(d.values - m) > 2*s))
        o3 = int(np.sum(np.abs(d.values - m) > 3*s))
        cv = (s/m)*100 if m != 0 else 0

        h = f"<b>{Icons.CHECK} Levey-Jennings — {a}</b><table style='font-size:12px;'>"
        for label, v2 in [("Media del control", f"{m:.4f}"), ("SD", f"{s:.4f}"), ("CV%", f"{cv:.2f}%"),
                           ("Mediciones (n)", len(d)), (">2SD (alerta)", o2), (">3SD (rechazo)", o3)]:
            h += self._r(label, v2)
        h += "</table>"
        if v:
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#fef2f2;border-left:3px solid #ef4444;'><b style='color:#dc2626;'>{Icons.WARN} Violaciones detectadas:</b><br>" + "<br>".join(v) + "<br><br><i>Se recomienda repetir el analisis.</i></div>"
        else:
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#ecfdf5;border-left:3px solid #22c55e;'><b style='color:#16a34a;'>{Icons.CHECK} Sin violaciones</b> — El control esta dentro de los limites aceptables.</div>"
        self.txt.setHtml(h)

    def _wj(self, a):
        self._lj(a)

    def _st(self, a):
        if a not in self.data.columns:
            return
        d, m, s = self._params(a)
        z = (d.values - m) / s if s > 0 else np.zeros(len(d))
        h = f"<b>{Icons.STATS} Estadisticas de Control — {a}</b><table style='font-size:12px;'>"
        for label, v in [("Mediciones (n)", len(d)), ("Media", f"{d.mean():.4f}"), ("Media del control", f"{m:.4f}"),
                          ("Desviacion estandar", f"{d.std():.4f}"), ("CV%", f"{(d.std()/d.mean())*100:.2f}%"),
                          ("Minimo", f"{d.min():.4f}"), ("Maximo", f"{d.max():.4f}")]:
            h += self._r(label, v)
        h += "</table><b>Distribucion de Z-scores:</b><table style='font-size:12px;'>"
        ins = int(np.sum(np.abs(z) <= 1))
        h += self._r("Dentro de 1SD", f"{ins} ({ins/len(z)*100:.0f}%) — Se esperaba ~68%")
        h += self._r("Entre 1-2SD", f"{int(np.sum((np.abs(z) > 1) & (np.abs(z) <= 2)))} — Zona de alerta")
        h += self._r("Entre 2-3SD", f"{int(np.sum((np.abs(z) > 2) & (np.abs(z) <= 3)))} — Precaucion")
        h += self._r("Fuera de 3SD", f"{int(np.sum(np.abs(z) > 3))} — Rechazo")
        h += "</table>"
        h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#eef2ff;font-size:12px;'>{Icons.INFO} <b>Interpretacion:</b> Un CV% < 5% indica buena precision. Los z-scores deben distribuirse normalmente dentro de ±2SD.</div>"
        self.txt.setHtml(h)

    def _tr(self, a):
        if a not in self.data.columns:
            return
        d, m, s = self._params(a)
        x = np.arange(len(d))
        result = stats.linregress(x, d.values)
        slope, intercept, r, p = result.slope, result.intercept, result.rvalue, result.pvalue
        h = f"<b>{Icons.CHART} Analisis de Tendencia — {a}</b><table style='font-size:12px;'>"
        for label, v in [("Pendiente", f"{slope:.6f}"), ("R-cuadrado", f"{r**2:.6f}"), ("Valor p", f"{p:.6f}")]:
            h += self._r(label, v)
        h += "</table>"
        if p < 0.05:
            dd = "creciente" if slope > 0 else "decreciente"
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#fef9ee;border-left:3px solid #f59e0b;'><b style='color:#d97706;'>{Icons.WARN} Tendencia {dd} significativa (p < 0.05)</b><br>Los valores del control estan cambiando sistematicamente. Se recomienda recalibrar el metodo.</div>"
        else:
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#ecfdf5;border-left:3px solid #22c55e;'><b style='color:#16a34a;'>{Icons.CHECK} Sin tendencia significativa</b><br>Los valores del control son estables.</div>"
        self.txt.setHtml(h)

        fig, ax = plt.subplots(figsize=(9, 5))
        ax.plot(range(1, len(d)+1), d.values, color=COLORS[0], marker='o', ms=3, lw=1.5)
        ax.plot(range(1, len(d)+1), slope*x+intercept, color=COLORS[3], ls='--', lw=1.5, label='Tendencia')
        ax.axhline(m, color=COLORS[1], alpha=0.5, label='Media')
        ax.set_title(f'Tendencia — {a}', fontweight='bold')
        ax.legend()
        fig.tight_layout()
        self._show(fig)

    def _save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar", "", "Texto (*.txt);;HTML (*.html)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.txt.toPlainText())
