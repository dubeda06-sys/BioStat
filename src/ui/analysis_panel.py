"""Panel de analisis estadistico."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QPushButton, QLabel, QTextEdit, QGroupBox,
    QLineEdit, QFormLayout, QScrollArea, QSplitter
)
from PyQt6.QtCore import Qt
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

from src.ui.icons import Icons
from src.core.roc import roc_curve, auc, optimal_threshold, diagnostic_stats
from src.core.bland_altman import bland_altman_analysis, concordance_correlation, bland_altman_multiple
from src.core.passing_bablok import passing_bablok
from src.core.survival import kaplan_meier, log_rank_test
from src.core.meta_analysis import meta_analysis
from src.core.sample_size import (
    sample_size_mean, sample_size_two_means,
    sample_size_proportions, sample_size_correlation, power_analysis
)
from src.core.bootstrap import (
    bootstrap_mean, bootstrap_median, bootstrap_correlation,
    bootstrap_difference, bootstrap_regression
)
from src.core.random_forest import RandomForestClassifier, RandomForestRegressor
from src.core.statistics import (
    mannwhitneyu, wilcoxon_signed_rank, chi_square_test, fisher_exact_test,
    mcnemar_test, kruskal_wallis, friedman_test,
    f_test_variances, ttest_1sample, trimmed_mean, skewness_test, kurtosis_test,
    partial_correlation, descriptive_stats, geometric_mean, harmonic_mean,
    anova_oneway, sign_test, cochran_q, pearson_r, spearman_rho, normality_test
)
from src.core.agreement import (
    cohens_kappa, intraclass_correlation, cronbach_alpha,
    weighted_kappa, deming_regression, cv_from_duplicates
)
from src.core.regression import linear_regression, multiple_regression, logistic_regression
from src.core.diagnostic_tests import (
    odds_ratio, relative_risk, diagnostic_test,
    likelihood_ratios, compare_two_means, compare_two_proportions, compare_two_auc
)
from src.core.outliers import grubbs_test, tukey_outliers, generalized_esd
from src.core.reference import reference_interval, percentile_table, age_related_reference
from src.core.two_way_anova import two_way_anova
from src.core.ancova import ancova
from src.core.repeated_measures import repeated_measures_anova
from src.core.cox_regression import cox_regression
from src.core.probit import probit_regression
from src.core.cmh import cmh_test
from src.core.serial_measurements import serial_measurements_summary
from src.core.plots import youden_data, polar_plot_data, waterfall_data, mountain_plot_data

plt.rcParams.update({
    'figure.facecolor': 'white', 'axes.facecolor': '#fafbfd',
    'axes.edgecolor': '#d8dbe3', 'axes.grid': True,
    'grid.alpha': 0.25, 'grid.color': '#d8dbe3',
    'font.size': 11, 'axes.titlesize': 13,
})

ANALYSIS_HELP = {
    "Estadisticas descriptivas": "Media, mediana, DE, varianza, min, max, IC95%, CV%, sesgo, curtosis.",
    "t-test pareado": "Compara medias de dos variables relacionadas (antes/despues).",
    "t-test independiente": "Compara medias de dos grupos independientes.",
    "ANOVA una via": "Compara medias de 3 o mas grupos.",
    "Correlacion de Pearson": "Relacion lineal entre dos variables (requiere normalidad).",
    "Correlacion de Spearman": "Relacion por rangos (no requiere normalidad).",
    "Shapiro-Wilk": "Prueba de normalidad. p<0.05 = no normal.",
    "Curva ROC": "Evaluacion de prueba diagnostica. Grafica sensibilidad vs 1-especificidad.",
    "Bland-Altman": "Concordancia entre dos metodos de medicion.",
    "Passing-Bablok": "Regresion robusta para comparar dos metodos.",
    "Kaplan-Meier": "Curva de supervivencia no parametrica.",
    "Log-rank test": "Compara dos curvas de supervivencia.",
    "Meta-analisis": "Combina resultados de multiples estudios.",
    "Tamano muestral (1 media)": "Calcula n para comparar una media con un valor.",
    "Tamano muestral (2 medias)": "Calcula n para comparar dos medias.",
    "Tamano muestral (2 proporciones)": "Calcula n para comparar dos proporciones.",
    "Poder estadistico": "Calcula el poder para un n dado.",
    "Bootstrap (media)": "IC bootstrap para la media.",
    "Bootstrap (diferencia)": "IC bootstrap para diferencia de medias.",
    "Bootstrap (correlacion)": "IC bootstrap para correlacion.",
    "Random Forest (clasificacion)": "Clasificacion con arboles aleatorios.",
    "Random Forest (regresion)": "Regresion con arboles aleatorios.",
    "Mann-Whitney U": "Prueba no parametrica para comparar dos grupos independientes.",
    "Wilcoxon pareado": "Prueba no parametrica para datos pareados.",
    "Chi-cuadrado": "Prueba de independencia en tablas de contingencia.",
    "Fisher exact": "Para tablas 2x2 con muestras pequenas.",
    "McNemar": "Proporciones apareadas (antes/despues en datos categoricos).",
    "Kruskal-Wallis": "ANOVA no parametrico para 3+ grupos.",
    "Friedman": "Medidas repetidas no parametrico.",
    "F-test (varianzas)": "Compara dos varianzas/de.",
    "Kappa": "Concordancia entre dos evaluadores (datos categoricos).",
    "ICC": "Coef. correlacion intraclase (confiabilidad).",
    "Cronbach alfa": "Consistencia interna de una escala.",
    "Regresion lineal": "Prediccion con una variable independiente.",
    "Regresion multiple": "Prediccion con multiples variables.",
    "Regresion logistica": "Prediccion de resultado binario (0/1).",
    "Odds Ratio": "Medida de asociacion entre exposicion y resultado.",
    "Riesgo Relativo": "Comparacion de riesgos entre dos grupos.",
    "Diagnostic test": "Sensibilidad, especificidad, PPV, NPV de una prueba.",
    "Outliers (Grubbs)": "Deteccion de valores atipicos individuales.",
    "Outliers (Tukey)": "Deteccion por metodo de Tukey (IQR).",
    "Intervalos de referencia": "Percentiles y rangos de referencia.",
    "Asimetria y curtosis": "Forma de la distribucion.",
    "Media recortada": "Media robusta eliminando extremos.",
    "Correlacion parcial": "Correlacion controlando una variable.",
    "Media geometrica": "Media geométrica de datos positivos.",
    "Media armonica": "Media armónica de datos positivos.",
    "t-test 1 muestra": "t-test para una muestra vs valor conocido.",
    "ANOVA una via (core)": "ANOVA una vía usando módulo core.",
    "Sign test": "Test de signos para datos pareados.",
    "Cochran Q": "Test Q de Cochran para proporciones.",
    "Kappa ponderado": "Kappa ponderado (lineal o cuadrático).",
    "Deming regression": "Regresión Deming para métodos comparados.",
    "CV duplicatas": "CV a partir de mediciones duplicadas.",
    "Likelihood Ratios": "Razones de verimilitud positiva y negativa.",
    "Comparar 2 medias": "Comparar 2 medias desde datos resumen.",
    "Comparar 2 proporciones": "Comparar 2 proporciones desde datos resumen.",
    "Comparar 2 AUC": "Comparar 2 curvas ROC independientes.",
    "Tabla de percentiles": "Tabla completa de percentiles con IC.",
    "Edad-relacionada": "Intervalos de referencia por edad.",
    "Outliers (ESD)": "Test ESD generalizado para múltiples outliers.",
    "Bootstrap (mediana)": "IC bootstrap para la mediana.",
    "Bootstrap (regresion)": "IC bootstrap para regresión lineal.",
    "Tamaño muestral (correlacion)": "Tamaño muestral para detectar correlación.",
    "ANOVA dos vias": "ANOVA factorial (2 factores).",
    "ANCOVA": "ANOVA con covariable continua.",
    "Medidas repetidas": "ANOVA para medidas repetidas con corrección Greenhouse-Geisser.",
    "Cox regression": "Regresión de riesgos proporcionales de Cox.",
    "Probit regression": "Regresión probit para datos binarios.",
    "CMH test": "Cochran-Mantel-Haenszel para tablas estratificadas.",
    "Mediciones seriales": "Resumen de mediciones repetidas por sujeto.",
    "Youden plot": "Gráfico de Youden (sensibilidad vs especificidad por umbral).",
    "Polar plot": "Gráfico polar (radar) para múltiples variables.",
    "Waterfall chart": "Gráfico de cascada para efectos acumulados.",
    "Mountain plot": "Gráfico de montaña (distribución plegada).",
    "Bland-Altman múltiple": "Bland-Altman para múltiples métodos/mediciones.",
}


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

        cfg = QGroupBox(f"  {Icons.GEAR}  Configuracion")
        cl = QFormLayout()
        cl.setSpacing(4)
        cl.setContentsMargins(6, 6, 6, 6)

        self.combo_analysis = QComboBox()
        self.combo_analysis.addItems(list(ANALYSIS_HELP.keys()))
        self.combo_analysis.setMinimumHeight(28)
        self.combo_analysis.currentTextChanged.connect(self._on_analysis_changed)
        cl.addRow("Analisis:", self.combo_analysis)

        self.lbl_help = QLabel(ANALYSIS_HELP["Estadisticas descriptivas"])
        self.lbl_help.setObjectName("subtitle")
        self.lbl_help.setWordWrap(True)
        self.lbl_help.setStyleSheet("color: #6b7280; font-style: italic; padding: 1px 0; font-size: 10px;")
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
        self.btn_run = QPushButton(f"{Icons.RUN} Ejecutar")
        self.btn_run.setMinimumHeight(30)
        self.btn_run.clicked.connect(self._run)
        br.addWidget(self.btn_run)
        btn_clr = QPushButton(f"{Icons.CLEAR}")
        btn_clr.setObjectName("secondary")
        btn_clr.setMinimumHeight(30)
        btn_clr.clicked.connect(self._clear)
        br.addWidget(btn_clr)
        left_l.addLayout(br)

        fg = QGroupBox(f"  {Icons.INFO}  Formula")
        fl = QVBoxLayout()
        fl.setContentsMargins(4, 2, 4, 2)
        self.txt_formula = QTextEdit()
        self.txt_formula.setReadOnly(True)
        self.txt_formula.setMaximumHeight(80)
        self.txt_formula.setPlaceholderText("Formula...")
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

        rg = QGroupBox(f"  {Icons.DOC}  Resultados")
        rl = QVBoxLayout()
        rl.setContentsMargins(4, 2, 4, 2)
        self.txt_results = QTextEdit()
        self.txt_results.setReadOnly(True)
        self.txt_results.setPlaceholderText("Resultados...")
        rl.addWidget(self.txt_results)
        rg.setLayout(rl)
        right_l.addWidget(rg, stretch=2)

        pg = QGroupBox(f"  {Icons.CHART}  Grafico")
        pl = QVBoxLayout()
        pl.setContentsMargins(4, 2, 4, 2)
        self.graph_scroll = QScrollArea()
        self.graph_scroll.setWidgetResizable(True)
        self.graph_ph = QLabel(f"<div style='text-align:center;color:#a0a8b8;padding:20px;'>{Icons.CHART} El grafico aparecera aqui</div>")
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

    def set_data(self, data):
        self.data = data
        if data is not None:
            cols = data.columns.tolist()
            self.combo_col1.clear()
            self.combo_col2.clear()
            self.combo_col3.clear()
            self.combo_col1.addItems(cols)
            self.combo_col2.addItems(cols)
            self.combo_col3.addItems(["(ninguna)"] + cols)

    def _run(self):
        if self.data is None:
            self.txt_results.setHtml(f"<div style='color:#d97706;padding:12px;'>{Icons.WARN} <b>Sin datos.</b> Importa un archivo en la pestaña Datos.</div>")
            return

        at = self.combo_analysis.currentText()
        c1 = self.combo_col1.currentText()
        c2 = self.combo_col2.currentText()
        c3 = self.combo_col3.currentText()
        try:
            alpha = float(self.input_alpha.text())
        except ValueError:
            alpha = 0.05

        dispatch = {
            "Estadisticas descriptivas": lambda: self._desc(c1),
            "t-test pareado": lambda: self._t_paired(c1, c2, alpha),
            "t-test independiente": lambda: self._t_ind(c1, c2, alpha),
            "ANOVA una via": lambda: self._anova(alpha),
            "Correlacion de Pearson": lambda: self._corr_p(c1, c2),
            "Correlacion de Spearman": lambda: self._corr_s(c1, c2),
            "Shapiro-Wilk": lambda: self._shapiro(c1),
            "Curva ROC": lambda: self._roc(c1, c3),
            "Bland-Altman": lambda: self._bland(c1, c2),
            "Passing-Bablok": lambda: self._passing(c1, c2),
            "Kaplan-Meier": lambda: self._kaplan_meier(c1, c2),
            "Log-rank test": lambda: self._log_rank(c1, c2, c3),
            "Meta-analisis": lambda: self._meta(c1, c2),
            "Tamano muestral (1 media)": lambda: self._ss_mean(),
            "Tamano muestral (2 medias)": lambda: self._ss_two_means(),
            "Tamano muestral (2 proporciones)": lambda: self._ss_prop(),
            "Poder estadistico": lambda: self._power(),
            "Bootstrap (media)": lambda: self._boot_mean(c1),
            "Bootstrap (diferencia)": lambda: self._boot_diff(c1, c2),
            "Bootstrap (correlacion)": lambda: self._boot_corr(c1, c2),
            "Random Forest (clasificacion)": lambda: self._rf_class(c1, c2),
            "Random Forest (regresion)": lambda: self._rf_regress(c1, c2),
            "Mann-Whitney U": lambda: self._mannwhitney(c1, c2),
            "Wilcoxon pareado": lambda: self._wilcoxon(c1, c2),
            "Chi-cuadrado": lambda: self._chi2(),
            "Fisher exact": lambda: self._fisher(),
            "McNemar": lambda: self._mcnemar(),
            "Kruskal-Wallis": lambda: self._kruskal(),
            "Friedman": lambda: self._friedman(),
            "F-test (varianzas)": lambda: self._ftest(c1, c2),
            "Kappa": lambda: self._kappa(),
            "ICC": lambda: self._icc(c1, c2),
            "Cronbach alfa": lambda: self._cronbach(),
            "Regresion lineal": lambda: self._reg_lineal(c1, c2),
            "Regresion multiple": lambda: self._reg_multiple(),
            "Regresion logistica": lambda: self._reg_logistica(),
            "Odds Ratio": lambda: self._odds_ratio(),
            "Riesgo Relativo": lambda: self._riesgo_relativo(),
            "Diagnostic test": lambda: self._diag_test(),
            "Outliers (Grubbs)": lambda: self._outliers_grubbs(c1),
            "Outliers (Tukey)": lambda: self._outliers_tukey(c1),
            "Intervalos de referencia": lambda: self._ref_interval(c1),
            "Asimetria y curtosis": lambda: self._skew_kurt(c1),
            "Media recortada": lambda: self._trimmed(c1),
            "Correlacion parcial": lambda: self._partial_corr(c1, c2, c3),
            "Media geometrica": lambda: self._run_core("geometric_mean", c1),
            "Media armonica": lambda: self._run_core("harmonic_mean", c1),
            "t-test 1 muestra": lambda: self._run_core("ttest_1sample", c1),
            "ANOVA una via (core)": lambda: self._run_core("anova_oneway"),
            "Sign test": lambda: self._run_core("sign_test", c1, c2),
            "Cochran Q": lambda: self._run_core("cochran_q"),
            "Kappa ponderado": lambda: self._run_core("weighted_kappa"),
            "Deming regression": lambda: self._run_core("deming", c1, c2),
            "CV duplicatas": lambda: self._run_core("cv_duplicates", c1, c2),
            "Likelihood Ratios": lambda: self._run_core("likelihood_ratios"),
            "Comparar 2 medias": lambda: self._run_core("compare_means"),
            "Comparar 2 proporciones": lambda: self._run_core("compare_props"),
            "Comparar 2 AUC": lambda: self._run_core("compare_auc"),
            "Tabla de percentiles": lambda: self._run_core("percentile_table", c1),
            "Edad-relacionada": lambda: self._run_core("age_related"),
            "Outliers (ESD)": lambda: self._run_core("generalized_esd", c1),
            "Bootstrap (mediana)": lambda: self._run_core("bootstrap_median", c1),
            "Bootstrap (regresion)": lambda: self._run_core("bootstrap_regression", c1, c2),
            "Tamaño muestral (correlacion)": lambda: self._run_core("sample_size_corr", c1, c2),
            "ANOVA dos vias": lambda: self._run_two_way_anova(),
            "ANCOVA": lambda: self._run_ancova(c1, c2, c3),
            "Medidas repetidas": lambda: self._run_repeated_measures(),
            "Cox regression": lambda: self._run_cox(c1, c2),
            "Probit regression": lambda: self._run_probit(c1, c2),
            "CMH test": lambda: self._run_cmh(),
            "Mediciones seriales": lambda: self._run_serial(),
            "Youden plot": lambda: self._run_youden(c1, c3),
            "Polar plot": lambda: self._run_polar(),
            "Waterfall chart": lambda: self._run_waterfall(c1),
            "Mountain plot": lambda: self._run_mountain(c1),
            "Bland-Altman múltiple": lambda: self._run_bland_multi(),
        }
        fn = dispatch.get(at)
        if fn:
            self.txt_results.setHtml(fn())

    def _show_fig(self, fig):
        self.canvas = FigureCanvas(fig)
        self.graph_scroll.setWidget(self.canvas)
        plt.close(fig)

    def _clear(self):
        self.txt_results.clear()
        self.txt_formula.clear()
        self.graph_scroll.setWidget(self.graph_ph)

    def _h(self, t):
        return f"<div style='border-bottom:2px solid #4f6ef7;padding-bottom:5px;margin-bottom:10px;'><b style='color:#2c3650;font-size:14px;'>{t}</b></div>"

    def _r(self, l, v):
        return f"<tr><td style='padding:2px 12px 2px 0;color:#8892a4;'>{l}</td><td style='padding:2px 0;font-weight:600;'>{v}</td></tr>"

    def _ok(self, yes, msg_yes="SIGNIFICATIVO", msg_no="NO SIGNIFICATIVO"):
        if yes:
            return f"<div style='margin-top:10px;padding:8px;border-radius:6px;background:#ecfdf5;border-left:3px solid #22c55e;'><b style='color:#16a34a;'>{Icons.CHECK} {msg_yes}</b></div>"
        return f"<div style='margin-top:10px;padding:8px;border-radius:6px;background:#fef9ee;border-left:3px solid #f59e0b;'><b style='color:#d97706;'>{Icons.WARN} {msg_no}</b></div>"

    def _set_formula(self, title, formula_text, steps=None):
        """Muestra formula y pasos en el recuadro de auditoria."""
        html = f"<b style='color:#2c3650;'>{title}</b><br><br>"
        html += f"<span style='font-family:Consolas,monospace; color:#4f6ef7;'>{formula_text}</span>"
        if steps:
            html += "<br><br><b>Pasos:</b><br>"
            html += "<span style='font-family:Consolas,monospace; font-size:11px;'>"
            html += steps.replace("\n", "<br>")
            html += "</span>"
        self.txt_formula.setText(html)

    # --- Estadisticas descriptivas ---
    def _desc(self, col):
        if col not in self.data.columns:
            return f"<b>Error:</b> '{col}' no encontrada."
        d = self.data[col].dropna()
        if not np.issubdtype(d.dtype, np.number):
            return f"<b>Error:</b> '{col}' no es numerica."
        
        result = descriptive_stats(d)
        self._set_formula(
            "Formula: Estadisticas Descriptivas",
            "Media: x̄ = Σxi / n\nDE: s = √(Σ(xi - x̄)² / (n-1))\nSE: SE = s / √n\nIC95%: x̄ ± 1.96 × SE\nCV%: (s / x̄) × 100"
        )
        
        h = self._h(f"{Icons.STATS} Descriptivas — {col}")
        h += "<table style='font-size:12px;'>"
        for l, v in [("n", result['n']), ("Media", f"{result['mean']:.4f}"), ("Mediana", f"{result['median']:.4f}"),
                      ("DE", f"{result['std']:.4f}"), ("Varianza", f"{result['var']:.4f}"),
                      ("Error estandar", f"{result['sem']:.4f}"),
                      ("Minimo", f"{result['min']:.4f}"), ("Maximo", f"{result['max']:.4f}"),
                      ("IC 95%", f"[{result['ci95'][0]:.4f}, {result['ci95'][1]:.4f}]"),
                      ("CV%", f"{result['cv']:.2f}%"),
                      ("Q25", f"{result['q25']:.4f}"), ("Q75", f"{result['q75']:.4f}"),
                      ("IQR", f"{result['iqr']:.4f}")]:
            h += self._r(l, v)
        return h + "</table>"

    # --- t-test pareado ---
    def _t_paired(self, c1, c2, a):
        if c1 not in self.data.columns or c2 not in self.data.columns:
            return "<b>Error:</b> Columnas no encontradas."
        d1, d2 = self.data[c1].dropna(), self.data[c2].dropna()
        n = min(len(d1), len(d2))
        if n < 2:
            return "<b>Error:</b> Minimo 2 pares."
        
        result = ttest_paired(d1[:n], d2[:n])
        if result is None:
            return "<b>Error:</b> No se pudo calcular."
        
        self._set_formula(
            "Formula: t-test Pareado",
            "t = (d̄ - μ₀) / (sd / √n)\ndonde d̄ = media de diferencias\nsd = DE de diferencias\nμ₀ = 0 (hipotesis nula)"
        )
        
        h = self._h(f"{Icons.RUN} t-test Pareado")
        h += "<table style='font-size:12px;'>"
        for l, v in [("Var 1", c1), ("Var 2", c2), ("Pares (n)", result['n']),
                      ("Media diff", f"{result['mean_diff']:.4f}"), ("DE diff", f"{result['sd_diff']:.4f}"),
                      ("t", f"{result['t']:.4f}"), ("p", f"{result['p']:.6f}"), ("Alpha", a)]:
            h += self._r(l, v)
        return h + "</table>" + self._ok(result['p'] < a)

    # --- t-test independiente ---
    def _t_ind(self, c1, c2, a):
        if c1 not in self.data.columns or c2 not in self.data.columns:
            return "<b>Error:</b> Columnas no encontradas."
        d1, d2 = self.data[c1].dropna(), self.data[c2].dropna()
        if len(d1) < 2 or len(d2) < 2:
            return "<b>Error:</b> Minimo 2 obs por grupo."
        
        result = ttest_ind(d1, d2)
        if result is None:
            return "<b>Error:</b> No se pudo calcular."
        
        self._set_formula(
            "Formula: t-test Independiente (Welch)",
            "t = (x̄₁ - x̄₂) / √(s₁²/n₁ + s₂²/n₂)\ndonde x̄ = media, s = DE, n = tamano"
        )
        
        h = self._h(f"{Icons.RUN} t-test Independiente")
        h += "<table style='font-size:12px;'>"
        for l, v in [("Grupo 1", c1), ("Grupo 2", c2),
                      ("n1", result['n1']), ("n2", result['n2']),
                      ("Media 1", f"{result['mean1']:.4f}"), ("Media 2", f"{result['mean2']:.4f}"),
                      ("t", f"{result['t']:.4f}"), ("p", f"{result['p']:.6f}"), ("Alpha", a)]:
            h += self._r(l, v)
        return h + "</table>" + self._ok(result['p'] < a)

    # --- ANOVA ---
    def _anova(self, a):
        nums = self.data.select_dtypes(include="number").columns
        groups = [self.data[c].dropna().values for c in nums if len(self.data[c].dropna()) > 0]
        names = [c for c in nums if len(self.data[c].dropna()) > 0]
        if len(groups) < 2:
            return "<b>Error:</b> >= 2 grupos numericos requeridos."
        
        result = anova_oneway(groups)
        self._set_formula("Formula: ANOVA Una Vía", "F = MS_between / MS_within")
        
        h = self._h(f"{Icons.RUN} ANOVA una via")
        h += "<table style='font-size:12px;'>"
        for l, v in [("Grupos", ", ".join(names)), ("F", f"{result['F']:.4f}"), ("p", f"{result['p']:.6f}"), ("Alpha", a)]:
            h += self._r(l, v)
        return h + "</table>" + self._ok(result['p'] < a)

    # --- Pearson ---
    def _corr_p(self, c1, c2):
        if c1 not in self.data.columns or c2 not in self.data.columns:
            return "<b>Error:</b> Columnas no encontradas."
        df = self.data[[c1, c2]].dropna()
        if len(df) < 3:
            return "<b>Error:</b> Minimo 3 pares."
        
        result = pearson_r(df[c1].values, df[c2].values)
        if result is None:
            return "<b>Error:</b> No se pudo calcular."
        
        ar = abs(result['r'])
        s = "Muy fuerte" if ar >= .9 else "Fuerte" if ar >= .7 else "Moderada" if ar >= .5 else "Debil"
        
        self._set_formula(
            "Formula: Correlacion de Pearson",
            "r = Sum(xi - xbar)(yi - ybar) / Sqrt[Sum(xi - xbar)^2 x Sum(yi - ybar)^2]"
        )
        
        h = self._h(f"{Icons.CHART} Pearson")
        h += "<table style='font-size:12px;'>"
        for l, v in [("Var 1", c1), ("Var 2", c2), ("n", result['n']),
                      ("r", f"{result['r']:.4f}"), ("R2", f"{result['r2']:.4f}"),
                      ("p", f"{result['p']:.6f}"), ("Fuerza", s)]:
            h += self._r(l, v)
        return h + "</table>" + self._ok(result['p'] < 0.05)

    # --- Spearman ---
    def _corr_s(self, c1, c2):
        if c1 not in self.data.columns or c2 not in self.data.columns:
            return "<b>Error:</b> Columnas no encontradas."
        df = self.data[[c1, c2]].dropna()
        if len(df) < 3:
            return "<b>Error:</b> Minimo 3 pares."
        
        result = spearman_rho(df[c1].values, df[c2].values)
        if result is None:
            return "<b>Error:</b> No se pudo calcular."
        
        self._set_formula("Formula: Spearman", "rho = 1 - (6 × Σd²) / (n × (n² - 1))")
        
        h = self._h(f"{Icons.CHART} Spearman")
        h += "<table style='font-size:12px;'>"
        for l, v in [("Var 1", c1), ("Var 2", c2), ("n", result['n']), ("rho", f"{result['rho']:.4f}"), ("p", f"{result['p']:.6f}")]:
            h += self._r(l, v)
        return h + "</table>" + self._ok(result['p'] < 0.05)

    # --- Shapiro-Wilk ---
    def _shapiro(self, col):
        if col not in self.data.columns:
            return f"<b>Error:</b> '{col}' no encontrada."
        d = self.data[col].dropna()
        if len(d) < 3:
            return "<b>Error:</b> Minimo 3 datos."
        if len(d) > 5000:
            d = d.sample(5000, random_state=42)
        
        result = normality_test(d)
        if result is None:
            return "<b>Error:</b> No se pudo calcular."
        
        self._set_formula("Formula: Shapiro-Wilk", "W = (Σa_i x_i)² / Σ(x_i - x̄)²")
        
        h = self._h(f"{Icons.CHECK} Shapiro-Wilk — {col}")
        h += "<table style='font-size:12px;'>"
        for l, v in [("n", result['n']), ("W", f"{result['statistic']:.4f}"), ("p", f"{result['p']:.6f}")]:
            h += self._r(l, v)
        h += "</table>"
        if result['p'] < 0.05:
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#fef2f2;border-left:3px solid #ef4444;'><b style='color:#dc2626;'>{Icons.WARN} NO es normal (p<0.05)</b><br>Usa pruebas no parametricas.</div>"
        else:
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#ecfdf5;border-left:3px solid #22c55e;'><b style='color:#16a34a;'>{Icons.CHECK} Es normal (p>=0.05)</b><br>Puedes usar pruebas parametricas.</div>"
        return h

    # --- Curva ROC ---
    def _roc(self, score_col, label_col):
        if label_col == "(ninguna)" or label_col not in self.data.columns:
            return f"<b>Error:</b> Selecciona la columna de etiquetas en Variable 3 (0=negativo, 1=positivo)."
        if score_col not in self.data.columns:
            return f"<b>Error:</b> '{score_col}' no encontrada."

        y_true = self.data[label_col].dropna()
        y_score = self.data[score_col].dropna()
        n = min(len(y_true), len(y_score))
        y_true, y_score = y_true.values[:n], y_score.values[:n]

        unique = np.unique(y_true)
        if not all(u in [0, 1] for u in unique):
            return f"<b>Error:</b> Variable 3 debe contener solo 0 y 1. Valores encontrados: {unique.tolist()}"

        fpr, tpr, thresh = roc_curve(y_true, y_score)
        a = auc(fpr, tpr)
        opt_t, youden, sens, fpr_opt = optimal_threshold(fpr, tpr, thresh)
        spec_opt = 1 - fpr_opt
        stats_diag = diagnostic_stats(y_true, y_score, opt_t)

        h = self._h(f"{Icons.CHART} Curva ROC — {score_col}")
        h += "<table style='font-size:12px;'>"
        for l, v in [("Variable (score)", score_col), ("Variable (etiqueta)", label_col),
                      ("Observaciones", n), ("AUC", f"{a:.4f}"),
                      ("Umbral optimo", f"{opt_t:.4f}"),
                      ("Sensibilidad", f"{sens:.4f}"),
                      ("Especificidad", f"{spec_opt:.4f}"),
                      ("Indice de Youden", f"{youden:.4f}")]:
            h += self._r(l, v)
        h += "</table>"

        if a >= 0.9:
            grade = "EXCELENTE"
        elif a >= 0.8:
            grade = "BUENA"
        elif a >= 0.7:
            grade = "ACEPTABLE"
        elif a >= 0.6:
            grade = "REGULAR"
        else:
            grade = "POBRE"

        h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#eef2ff;font-size:12px;'>{Icons.INFO} <b>Interpretacion:</b> AUC={a:.3f} = {grade}. AUC=1.0 es perfecto, AUC=0.5 es como azar.</div>"

        if stats_diag:
            h += "<b style='font-size:12px;'>Matriz de confusion (umbral optimo):</b><table style='font-size:12px;'>"
            for l, v in [("Verdaderos positivos", stats_diag["tp"]),
                          ("Verdaderos negativos", stats_diag["tn"]),
                          ("Falsos positivos", stats_diag["fp"]),
                          ("Falsos negativos", stats_diag["fn"]),
                          ("Exactitud", f"{stats_diag['accuracy']:.4f}"),
                          ("Valor predictivo positivo", f"{stats_diag['ppv']:.4f}"),
                          ("Valor predictivo negativo", f"{stats_diag['npv']:.4f}")]:
                h += self._r(l, v)
            h += "</table>"

        fig, ax = plt.subplots(figsize=(7, 6))
        ax.plot(fpr, tpr, color='#4f6ef7', lw=2, label=f'ROC (AUC = {a:.3f})')
        ax.plot([0, 1], [0, 1], color='#d1d5e0', lw=1, ls='--', label='Azar')
        ax.scatter([1-spec_opt], [sens], color='#ef4444', s=80, zorder=5, label=f'Optimo ({opt_t:.2f})')
        ax.set_xlabel('1 - Especificidad (FPR)')
        ax.set_ylabel('Sensibilidad (TPR)')
        ax.set_title('Curva ROC', fontweight='bold')
        ax.legend(loc='lower right', framealpha=0.9)
        ax.set_xlim([0, 1])
        ax.set_ylim([0, 1])
        fig.tight_layout()
        self._show_fig(fig)

        return h

    # --- Bland-Altman ---
    def _bland(self, c1, c2):
        if c1 not in self.data.columns or c2 not in self.data.columns:
            return "<b>Error:</b> Columnas no encontradas."
        d1, d2 = self.data[c1].dropna(), self.data[c2].dropna()
        n = min(len(d1), len(d2))
        if n < 3:
            return "<b>Error:</b> Minimo 3 pares."

        result = bland_altman_analysis(d1.values[:n], d2.values[:n])
        if result is None:
            return "<b>Error:</b> No se pudo calcular."

        h = self._h(f"{Icons.CHART} Bland-Altman — {c1} vs {c2}")
        h += "<table style='font-size:12px;'>"
        for l, v in [("n", result["n"]),
                      ("Media Metodo 1", f"{result['mean_method1']:.4f}"),
                      ("Media Metodo 2", f"{result['mean_method2']:.4f}"),
                      ("Sesgo (media diff)", f"{result['mean_difference']:.4f}"),
                      ("Sesgo %", f"{result['bias_pct']:.2f}%"),
                      ("DE diferencias", f"{result['sd_difference']:.4f}"),
                      ("Limite superior (+1.96DE)", f"{result['loa_upper']:.4f}"),
                      ("Limite inferior (-1.96DE)", f"{result['loa_lower']:.4f}"),
                      ("Correlacion r", f"{result['correlation_r']:.4f}")]:
            h += self._r(l, v)
        h += "</table>"

        bias_ok = abs(result["bias_pct"]) < 5
        if bias_ok:
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#ecfdf5;border-left:3px solid #22c55e;'><b style='color:#16a34a;'>{Icons.CHECK} Sesgo bajo ({result['bias_pct']:.1f}%)</b> — Los metodos son concordantes.</div>"
        else:
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#fef9ee;border-left:3px solid #f59e0b;'><b style='color:#d97706;'>{Icons.WARN} Sesgo elevado ({result['bias_pct']:.1f}%)</b> — Revisar concordancia.</div>"

        means, diffs = result["means"], result["diffs"]
        fig, ax = plt.subplots(figsize=(9, 6))
        ax.scatter(means, diffs, alpha=0.5, c='#4f6ef7', edgecolors='white', s=50)
        ax.axhline(result["mean_difference"], color='#22c55e', lw=2, label=f'Sesgo: {result["mean_difference"]:.3f}')
        ax.axhline(result["loa_upper"], color='#ef4444', ls='--', lw=1.5, label=f'+1.96DE: {result["loa_upper"]:.3f}')
        ax.axhline(result["loa_lower"], color='#ef4444', ls='--', lw=1.5, label=f'-1.96DE: {result["loa_lower"]:.3f}')
        ax.fill_between([means.min(), means.max()], result["loa_lower"], result["loa_upper"], alpha=0.08, color='#22c55e')
        ax.set_xlabel('Promedio de ambos metodos')
        ax.set_ylabel('Diferencia (Metodo1 - Metodo2)')
        ax.set_title(f'Bland-Altman — {c1} vs {c2}', fontweight='bold')
        ax.legend(loc='upper right', framealpha=0.9)
        fig.tight_layout()
        self._show_fig(fig)

        return h

    # --- Passing-Bablok ---
    def _passing(self, c1, c2):
        if c1 not in self.data.columns or c2 not in self.data.columns:
            return "<b>Error:</b> Columnas no encontradas."
        d1, d2 = self.data[c1].dropna(), self.data[c2].dropna()
        n = min(len(d1), len(d2))
        if n < 3:
            return "<b>Error:</b> Minimo 3 pares."

        result = passing_bablok(d1.values[:n], d2.values[:n])
        if result is None:
            return "<b>Error:</b> No se pudo calcular."

        h = self._h(f"{Icons.CHART} Passing-Bablok — {c1} vs {c2}")
        h += "<table style='font-size:12px;'>"
        for l, v in [("n", result["n"]),
                      ("Pendiente (b)", f"{result['slope']:.4f}"),
                      ("IC 95% pendiente", f"[{result['ci_slope'][0]:.4f}, {result['ci_slope'][1]:.4f}]"),
                      ("Intercepto (a)", f"{result['intercept']:.4f}"),
                      ("DE residuos", f"{result['se_residuals']:.4f}"),
                      ("Correlacion r", f"{result['correlation_r']:.4f}"),
                      ("Media Metodo 1", f"{result['method1_mean']:.4f}"),
                      ("Media Metodo 2", f"{result['method2_mean']:.4f}")]:
            h += self._r(l, v)
        h += "</table>"

        slope_incl1 = result["ci_slope"][0] <= 1 <= result["ci_slope"][1]
        intercept_zero = abs(result["intercept"]) < 0.1 * result["method1_mean"]

        if slope_incl1 and intercept_zero:
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#ecfdf5;border-left:3px solid #22c55e;'><b style='color:#16a34a;'>{Icons.CHECK} Metodos concordantes</b><br>Pendiente incluye 1 e intercepto cerca de 0.</div>"
        else:
            issues = []
            if not slope_incl1:
                issues.append(f"pendiente={result['slope']:.3f} (IC no incluye 1)")
            if not intercept_zero:
                issues.append(f"intercepto={result['intercept']:.3f} (no es ~0)")
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#fef9ee;border-left:3px solid #f59e0b;'><b style='color:#d97706;'>{Icons.WARN} Discordancia detectada</b><br>{'; '.join(issues)}</div>"

        m1, m2 = result["method1"], result["method2"]
        slope, intercept = result["slope"], result["intercept"]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        ax1.scatter(m1, m2, alpha=0.5, c='#4f6ef7', edgecolors='white', s=50)
        xl = np.linspace(m1.min(), m1.max(), 100)
        ax1.plot(xl, slope*xl + intercept, color='#ef4444', lw=2, label=f'y = {slope:.3f}x + {intercept:.3f}')
        ax1.plot(xl, xl, color='#d1d5e0', ls='--', lw=1, label='Identidad (y=x)')
        ax1.set_xlabel(c1)
        ax1.set_ylabel(c2)
        ax1.set_title('Passing-Bablok', fontweight='bold')
        ax1.legend(framealpha=0.9)

        ax2.scatter(m1, result["residuals"], alpha=0.5, c='#4f6ef7', edgecolors='white', s=50)
        ax2.axhline(0, color='#ef4444', ls='--', lw=1.5)
        ax2.set_xlabel(c1)
        ax2.set_ylabel('Residuos')
        ax2.set_title('Residuos', fontweight='bold')

        fig.tight_layout()
        self._show_fig(fig)

        return h

    # --- Kaplan-Meier ---
    def _kaplan_meier(self, time_col, event_col):
        if time_col not in self.data.columns or event_col not in self.data.columns:
            return "<b>Error:</b> Selecciona columna de tiempo y de evento (1=event, 0=censura)."
        t = self.data[time_col].dropna()
        e = self.data[event_col].dropna()
        n = min(len(t), len(e))
        if n < 5:
            return "<b>Error:</b> Minimo 5 observaciones."

        km = kaplan_meier(t.values[:n], e.values[:n].astype(int))
        if km is None:
            return "<b>Error:</b> No se pudo calcular."

        h = self._h(f"{Icons.CHART} Kaplan-Meier — {time_col}")
        h += "<table style='font-size:12px;'>"
        for l, v in [("n total", km["n_total"]), ("Eventos", km["n_events"]),
                      ("Censurados", km["n_censored"]),
                      ("Supervivencia media", f"{np.mean(km['survival']):.4f}")]:
            h += self._r(l, v)
        if km["median_survival"] is not None:
            h += self._r("Supervivencia mediana", f"{km['median_survival']:.2f}")
        h += "</table>"
        h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#eef2ff;font-size:12px;'>{Icons.INFO} <b>Interpretacion:</b> La curva muestra la probabilidad de supervivencia en cada tiempo. La mediana es el tiempo donde el 50% sobrevive.</div>"

        fig, ax = plt.subplots(figsize=(9, 6))
        ax.step(km["times"], km["survival"], where='post', color='#4f6ef7', lw=2)
        ax.fill_between(km["times"], km["ci_lower"], km["ci_upper"], step='post', alpha=0.15, color='#4f6ef7')
        ax.set_xlabel('Tiempo')
        ax.set_ylabel('Probabilidad de supervivencia')
        ax.set_title('Kaplan-Meier', fontweight='bold')
        ax.set_ylim([0, 1.05])
        ax.grid(True, alpha=0.25)
        fig.tight_layout()
        self._show_fig(fig)

        return h

    # --- Log-rank ---
    def _log_rank(self, time_col, event_col, group_col):
        if time_col not in self.data.columns or event_col not in self.data.columns:
            return "<b>Error:</b> Selecciona tiempo y evento."
        if group_col not in self.data.columns:
            return "<b>Error:</b> Selecciona columna de grupo en Variable 3."

        groups = self.data[group_col].dropna().unique()
        if len(groups) != 2:
            return f"<b>Error:</b> Se necesitan exactamente 2 grupos. Encontrados: {len(groups)}"

        g1 = self.data[self.data[group_col] == groups[0]]
        g2 = self.data[self.data[group_col] == groups[1]]

        valid1 = g1[time_col].notna() & g1[event_col].notna()
        t1, e1 = g1.loc[valid1, time_col], g1.loc[valid1, event_col]
        valid2 = g2[time_col].notna() & g2[event_col].notna()
        t2, e2 = g2.loc[valid2, time_col], g2.loc[valid2, event_col]

        if len(t1) < 3 or len(t2) < 3:
            return "<b>Error:</b> Minimo 3 obs por grupo."

        lr = log_rank_test(t1.values, e1.values.astype(int), t2.values, e2.values.astype(int))

        km1 = kaplan_meier(t1.values, e1.values.astype(int))
        km2 = kaplan_meier(t2.values, e2.values.astype(int))

        h = self._h(f"{Icons.RUN} Log-rank Test")
        h += "<table style='font-size:12px;'>"
        for l, v in [("Grupo 1", f"{groups[0]} (n={len(t1)})"),
                      ("Grupo 2", f"{groups[1]} (n={len(t2)})"),
                      ("Chi-cuadrado", f"{lr['chi2']:.4f}"),
                      ("Valor p", f"{lr['p']:.6f}"),
                      ("Observado (G1)", lr["observed"]),
                      ("Esperado (G1)", f"{lr['expected']:.2f}")]:
            h += self._r(l, v)
        h += "</table>"
        h += self._ok(lr['p'] < 0.05, "CURVAS DIFERENTES", "CURVAS SIMILARES")

        fig, ax = plt.subplots(figsize=(9, 6))
        ax.step(km1["times"], km1["survival"], where='post', color='#4f6ef7', lw=2, label=str(groups[0]))
        ax.step(km2["times"], km2["survival"], where='post', color='#ef4444', lw=2, label=str(groups[1]))
        ax.fill_between(km1["times"], km1["ci_lower"], km1["ci_upper"], step='post', alpha=0.1, color='#4f6ef7')
        ax.fill_between(km2["times"], km2["ci_lower"], km2["ci_upper"], step='post', alpha=0.1, color='#ef4444')
        ax.set_xlabel('Tiempo')
        ax.set_ylabel('Supervivencia')
        ax.set_title('Comparacion de Curvas (Log-rank)', fontweight='bold')
        ax.legend(framealpha=0.9)
        ax.set_ylim([0, 1.05])
        fig.tight_layout()
        self._show_fig(fig)

        return h

    # --- Meta-analisis ---
    def _meta(self, effect_col, se_col):
        if effect_col not in self.data.columns or se_col not in self.data.columns:
            return "<b>Error:</b> Selecciona columna de efectos y de error estandar."
        eff = self.data[effect_col].dropna().values
        se = self.data[se_col].dropna().values
        n = min(len(eff), len(se))
        if n < 2:
            return "<b>Error:</b> Minimo 2 estudios."

        result = meta_analysis(eff[:n], se[:n])
        if result is None:
            return "<b>Error:</b> No se pudo calcular."

        h = self._h(f"{Icons.STATS} Meta-analisis")
        h += "<table style='font-size:12px;'>"
        for l, v in [("Estudios (k)", result["k"]),
                      ("Modelo", result["model"]),
                      ("Efecto combinado", f"{result['effect']:.4f}"),
                      ("IC 95%", f"[{result['ci_lower']:.4f}, {result['ci_upper']:.4f}]"),
                      ("Z", f"{result['z']:.4f}"),
                      ("Valor p", f"{result['p']:.6f}"),
                      ("Q de Cochran", f"{result['q']:.4f}"),
                      ("p heterogeneidad", f"{result['p_heterogeneity']:.4f}"),
                      ("I2", f"{result['i2']:.1f}%")]:
            h += self._r(l, v)
        h += "</table>"

        if result['i2'] < 25:
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#ecfdf5;border-left:3px solid #22c55e;'><b style='color:#16a34a;'>{Icons.CHECK} Baja heterogeneidad (I2={result['i2']:.0f}%)</b></div>"
        elif result['i2'] < 75:
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#fef9ee;border-left:3px solid #f59e0b;'><b style='color:#d97706;'>{Icons.WARN} Heterogeneidad moderada (I2={result['i2']:.0f}%)</b></div>"
        else:
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#fef2f2;border-left:3px solid #ef4444;'><b style='color:#dc2626;'>{Icons.WARN} Heterogeneidad alta (I2={result['i2']:.0f}%)</b></div>"

        fig, ax = plt.subplots(figsize=(8, max(3, result["k"] * 0.6 + 1)))
        y_pos = range(result["k"])
        ax.errorbar(result["effects"], y_pos, xerr=1.96*result["se_effects"],
                    fmt='o', color='#4f6ef7', ecolor='#d1d5e0', capsize=3, markersize=6)
        ax.errorbar(result["effect"], -1, xerr=1.96*result["se"],
                    fmt='D', color='#ef4444', ecolor='#ef4444', capsize=5, markersize=8, label='Combinado')
        ax.axvline(0, color='#d1d5e0', ls='--', lw=1)
        ax.set_yticks(list(y_pos) + [-1])
        ax.set_yticklabels(result["labels"] + ["COMBINADO"])
        ax.set_xlabel('Efecto')
        ax.set_title('Forest Plot', fontweight='bold')
        ax.legend(loc='lower right', framealpha=0.9)
        fig.tight_layout()
        self._show_fig(fig)

        return h

    # --- Tamano muestral (1 media) ---
    def _ss_mean(self):
        h = self._h(f"{Icons.STATS} Tamano Muestral — 1 media")
        h += "<div style='padding:8px;border-radius:6px;background:#eef2ff;font-size:12px;margin-bottom:12px;'>"
        h += f"{Icons.INFO} Calcula cuantas observaciones necesitas para detectar una diferencia dada."
        h += "</div>"
        h += "<div style='padding:12px;border-radius:8px;background:#f8f9fa;font-size:13px;'>"
        h += "<b>Formula:</b> n = ((Z_alpha + Z_beta) × SD / delta)²<br><br>"
        h += "Ejemplo: Para detectar diferencia de 5 con DE=10, alpha=0.05, poder=0.80:<br>"
        r = sample_size_mean(5, 10)
        h += f"<b>n = {r['n_per_group']} observaciones</b> (tamano de efecto d={r['effect_size']:.2f})"
        h += "</div>"
        h += "<div style='margin-top:8px;padding:8px;border-radius:6px;background:#eef2ff;font-size:12px;'>"
        h += f"{Icons.INFO} <b>Tip:</b> Para tu propio calculo, usa: sample_size_mean(delta, sd, alpha, power)"
        h += "</div>"
        return h

    # --- Tamano muestral (2 medias) ---
    def _ss_two_means(self):
        h = self._h(f"{Icons.STATS} Tamano Muestral — 2 medias")
        r = sample_size_two_means(5, 10)
        h += "<div style='padding:12px;border-radius:8px;background:#f8f9fa;font-size:13px;'>"
        h += "<b>Formula:</b> n = ((Z_alpha + Z_beta) × SD / delta)² × (1 + 1/ratio)<br><br>"
        h += f"Ejemplo: Delta=5, DE=10, alpha=0.05, poder=0.80<br>"
        h += f"<b>n = {r['n_group1']} por grupo</b> ({r['n_total']} total, d={r['effect_size']:.2f})"
        h += "</div>"
        return h

    # --- Tamano muestral (2 proporciones) ---
    def _ss_prop(self):
        h = self._h(f"{Icons.STATS} Tamano Muestral — 2 proporciones")
        r = sample_size_proportions(0.3, 0.5)
        h += "<div style='padding:12px;border-radius:8px;background:#f8f9fa;font-size:13px;'>"
        h += "<b>Formula:</b> basada en la prueba Z para diferencias de proporciones<br><br>"
        h += f"Ejemplo: p1=0.3, p2=0.5, alpha=0.05, poder=0.80<br>"
        h += f"<b>n = {r['n_per_group']} por grupo</b> ({r['n_total']} total)"
        h += "</div>"
        return h

    # --- Poder estadistico ---
    def _power(self):
        h = self._h(f"{Icons.STATS} Poder Estadistico")
        r = power_analysis(100, 5, 10)
        h += "<div style='padding:12px;border-radius:8px;background:#f8f9fa;font-size:13px;'>"
        h += "Calcula la probabilidad de detectar un efecto real dado un tamano de muestra.<br><br>"
        h += f"Ejemplo: n=100, delta=5, DE=10, alpha=0.05<br>"
        h += f"<b>Poder = {r['power']:.1%}</b> (tamano de efecto d={r['effect_size']:.2f})"
        h += "</div>"
        h += "<div style='margin-top:8px;padding:8px;border-radius:6px;background:#eef2ff;font-size:12px;'>"
        h += f"{Icons.INFO} <b>Interpretacion:</b> Un poder >= 80% (0.80) es generalmente aceptable."
        h += "</div>"
        return h

    # --- Bootstrap (media) ---
    def _boot_mean(self, col):
        if col not in self.data.columns:
            return f"<b>Error:</b> '{col}' no encontrada."
        d = self.data[col].dropna()
        if len(d) < 5:
            return "<b>Error:</b> Minimo 5 datos para bootstrap."

        self._set_formula(
            "Formula: Bootstrap IC para la Media",
            "1. Remuestrear n datos con reemplazo\n2. Calcular media de cada remuestreo\n3. IC = [P(alpha/2), P(1-alpha/2)]\n   de las B medias bootstrap",
            f"n original = {len(d)}\nB = 10000 remuestreos\nIC 95% calculado sobre distribucion bootstrap"
        )

        result = bootstrap_mean(d.values)
        if result is None:
            return "<b>Error:</b> No se pudo calcular."

        h = self._h(f"{Icons.STATS} Bootstrap — Media de {col}")
        h += "<table style='font-size:12px;'>"
        for l, v in [("n original", result["n_original"]),
                      ("Media original", f"{result['original_mean']:.6f}"),
                      ("Media bootstrap", f"{result['bootstrap_mean']:.6f}"),
                      ("SE bootstrap", f"{result['bootstrap_se']:.6f}"),
                      ("IC 95%", f"[{result['ci_lower']:.4f}, {result['ci_upper']:.4f}]"),
                      ("Sesgo", f"{result['bias']:.6f}"),
                      ("Remuestreos", result["n_bootstrap"])]:
            h += self._r(l, v)
        h += "</table>"
        h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#eef2ff;font-size:12px;'>{Icons.INFO} Bootstrap no asume distribucion normal. El IC se obtiene directamente de la distribucion de medias remuestreadas.</div>"

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
        ax1.hist(d.values, bins=30, edgecolor='white', alpha=0.7, color='#4f6ef7')
        ax1.axvline(result['original_mean'], color='#ef4444', ls='--', lw=2, label=f'Media={result["original_mean"]:.2f}')
        ax1.set_title('Datos originales', fontweight='bold')
        ax1.legend(framealpha=0.9)

        ax2.hist(result['bootstrap_distribution'], bins=50, edgecolor='white', alpha=0.7, color='#22c55e')
        ax2.axvline(result['ci_lower'], color='#ef4444', ls='--', lw=1.5, label=f'IC bajo={result["ci_lower"]:.2f}')
        ax2.axvline(result['ci_upper'], color='#ef4444', ls='--', lw=1.5, label=f'IC alto={result["ci_upper"]:.2f}')
        ax2.set_title('Distribucion bootstrap', fontweight='bold')
        ax2.legend(framealpha=0.9)

        fig.tight_layout()
        self._show_fig(fig)

        return h

    # --- Bootstrap (diferencia) ---
    def _boot_diff(self, c1, c2):
        if c1 not in self.data.columns or c2 not in self.data.columns:
            return "<b>Error:</b> Columnas no encontradas."
        d1, d2 = self.data[c1].dropna(), self.data[c2].dropna()
        if len(d1) < 5 or len(d2) < 5:
            return "<b>Error:</b> Minimo 5 obs por grupo."

        self._set_formula(
            "Formula: Bootstrap IC para Diferencia de Medias",
            "1. Remuestrear n1 datos de grupo1 con reemplazo\n2. Remuestrear n2 datos de grupo2 con reemplazo\n3. Diff* = mean(muestreo1) - mean(muestreo2)\n4. IC = [P(2.5%), P(97.5%)] de las B diferencias",
            f"n1={len(d1)}, n2={len(d2)}\nB = 10000 remuestreos\nDiferencia original = {d1.mean()-d2.mean():.4f}"
        )

        result = bootstrap_difference(d1.values, d2.values)
        if result is None:
            return "<b>Error:</b> No se pudo calcular."

        h = self._h(f"{Icons.STATS} Bootstrap — Diferencia {c1} - {c2}")
        h += "<table style='font-size:12px;'>"
        for l, v in [("Diferencia original", f"{result['original_diff']:.4f}"),
                      ("Diferencia bootstrap", f"{result['bootstrap_diff']:.4f}"),
                      ("SE bootstrap", f"{result['bootstrap_se']:.6f}"),
                      ("IC 95%", f"[{result['ci_lower']:.4f}, {result['ci_upper']:.4f}]")]:
            h += self._r(l, v)
        h += "</table>"

        includes_zero = result['ci_lower'] <= 0 <= result['ci_upper']
        if includes_zero:
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#fef9ee;border-left:3px solid #f59e0b;'><b style='color:#d97706;'>{Icons.WARN} IC incluye 0 — Sin diferencia significativa</b></div>"
        else:
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#ecfdf5;border-left:3px solid #22c55e;'><b style='color:#16a34a;'>{Icons.CHECK} IC NO incluye 0 — Diferencia significativa</b></div>"

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(result['bootstrap_distribution'], bins=50, edgecolor='white', alpha=0.7, color='#4f6ef7')
        ax.axvline(result['ci_lower'], color='#ef4444', ls='--', lw=1.5)
        ax.axvline(result['ci_upper'], color='#ef4444', ls='--', lw=1.5)
        ax.axvline(0, color='#d1d5e0', ls='--', lw=1.5, label='0')
        ax.set_title('Bootstrap: Diferencia de Medias', fontweight='bold')
        ax.legend()
        fig.tight_layout()
        self._show_fig(fig)

        return h

    # --- Bootstrap (correlacion) ---
    def _boot_corr(self, c1, c2):
        if c1 not in self.data.columns or c2 not in self.data.columns:
            return "<b>Error:</b> Columnas no encontradas."
        d1, d2 = self.data[c1].dropna(), self.data[c2].dropna()
        n = min(len(d1), len(d2))
        if n < 5:
            return "<b>Error:</b> Minimo 5 pares."

        self._set_formula(
            "Formula: Bootstrap IC para Correlacion",
            "1. Remuestrear pares (xi, yi) con reemplazo\n2. Calcular r de cada remuestreo\n3. IC = [P(2.5%), P(97.5%)] de las B correlaciones",
            f"n = {n}\nB = 10000 remuestreos\nMetodo = Pearson"
        )

        result = bootstrap_correlation(d1.values[:n], d2.values[:n])
        if result is None:
            return "<b>Error:</b> No se pudo calcular."

        h = self._h(f"{Icons.CHART} Bootstrap — Correlacion")
        h += "<table style='font-size:12px;'>"
        for l, v in [("r original", f"{result['original_r']:.6f}"),
                      ("r bootstrap", f"{result['bootstrap_r']:.6f}"),
                      ("SE bootstrap", f"{result['bootstrap_se']:.6f}"),
                      ("IC 95%", f"[{result['ci_lower']:.4f}, {result['ci_upper']:.4f}]"),
                      ("p original", f"{result['original_p']:.6f}")]:
            h += self._r(l, v)
        h += "</table>"

        includes_zero = result['ci_lower'] <= 0 <= result['ci_upper']
        if includes_zero:
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#fef9ee;border-left:3px solid #f59e0b;'><b style='color:#d97706;'>{Icons.WARN} IC incluye 0 — Sin correlacion significativa</b></div>"
        else:
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#ecfdf5;border-left:3px solid #22c55e;'><b style='color:#16a34a;'>{Icons.CHECK} IC NO incluye 0 — Correlacion significativa</b></div>"

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(result['bootstrap_distribution'], bins=50, edgecolor='white', alpha=0.7, color='#8b5cf6')
        ax.axvline(result['ci_lower'], color='#ef4444', ls='--', lw=1.5)
        ax.axvline(result['ci_upper'], color='#ef4444', ls='--', lw=1.5)
        ax.axvline(0, color='#d1d5e0', ls='--', lw=1.5, label='0')
        ax.set_title('Bootstrap: Correlacion', fontweight='bold')
        ax.legend()
        fig.tight_layout()
        self._show_fig(fig)

        return h

    # --- Random Forest (clasificacion) ---
    def _rf_class(self, target_col, feature_cols_str=None):
        if target_col not in self.data.columns:
            return f"<b>Error:</b> '{target_col}' no encontrada."

        nums = self.data.select_dtypes(include="number").columns.tolist()
        if target_col in nums:
            nums.remove(target_col)
        if len(nums) < 1:
            return "<b>Error:</b> Se necesitan al menos 1 variable predictora numerica."

        X = self.data[nums].dropna()
        y = self.data.loc[X.index, target_col]

        valid = y.notna()
        X, y = X[valid].values, y[valid].values

        if len(np.unique(y)) < 2:
            return "<b>Error:</b> Target debe tener al menos 2 clases."

        self._set_formula(
            "Formula: Random Forest (Clasificacion)",
            "1. Para cada arbol:\n   a. Remuestrear datos con reemplazo (bagging)\n   b. En cada nodo, probar sqrt(p) features\n   c. Elegir mejor split por Gini\n2. Clasificacion = voto mayoritario de B arboles\n3. Gini = 1 - Σ(pi²)",
            f"n_arboles = 100\nn_features = sqrt({len(nums)}) = {int(np.sqrt(len(nums)))}\nFeatures: {', '.join(nums[:5])}\nTarget: {target_col}"
        )

        rf = RandomForestClassifier(n_trees=100, max_depth=8, random_state=42)
        rf.fit(X, y)
        acc = rf.score(X, y)
        importances = rf.get_feature_importance()

        h = self._h(f"{Icons.STATS} Random Forest — Clasificacion")
        h += "<table style='font-size:12px;'>"
        h += self._r("Target", target_col)
        h += self._r("Features", len(nums))
        h += self._r("Observaciones", len(y))
        h += self._r("Clases", len(np.unique(y)))
        h += self._r("Accuracy (train)", f"{acc:.4f}")
        h += "</table>"

        h += "<b style='font-size:12px;'>Importancia de Variables:</b><table style='font-size:12px;'>"
        sorted_idx = np.argsort(importances)[::-1]
        for i in sorted_idx[:8]:
            bar = "█" * int(importances[i] * 50)
            h += self._r(nums[i], f"{importances[i]:.4f} {bar}")
        h += "</table>"

        fig, ax = plt.subplots(figsize=(8, max(3, min(8, len(nums)) * 0.5)))
        top_n = min(8, len(nums))
        idx = sorted_idx[:top_n]
        ax.barh(range(top_n), importances[idx], color='#4f6ef7', edgecolor='white')
        ax.set_yticks(range(top_n))
        ax.set_yticklabels([nums[i] for i in idx])
        ax.set_xlabel('Importancia')
        ax.set_title('Random Forest — Importancia', fontweight='bold')
        ax.invert_yaxis()
        fig.tight_layout()
        self._show_fig(fig)

        return h

    # --- Random Forest (regresion) ---
    def _rf_regress(self, target_col, feature_cols_str=None):
        if target_col not in self.data.columns:
            return f"<b>Error:</b> '{target_col}' no encontrada."

        nums = self.data.select_dtypes(include="number").columns.tolist()
        if target_col in nums:
            nums.remove(target_col)
        if len(nums) < 1:
            return "<b>Error:</b> Se necesitan al menos 1 feature numerico."

        X = self.data[nums].dropna()
        y = self.data.loc[X.index, target_col].dropna()
        common = X.index.intersection(y.index)
        X, y = X.loc[common].values, y.loc[common].values

        if len(y) < 10:
            return "<b>Error:</b> Minimo 10 observaciones."

        self._set_formula(
            "Formula: Random Forest (Regresion)",
            "1. Para cada arbol:\n   a. Remuestrear datos con reemplazo\n   b. Mejor split por varianza minimizada\n2. Prediccion = promedio de B arboles\n3. Varianza = (1/n) × Σ(yi - ȳ)²",
            f"n_arboles = 100\nFeatures: {', '.join(nums[:5])}\nTarget: {target_col}\nn = {len(y)}"
        )

        rf = RandomForestRegressor(n_trees=100, max_depth=8, random_state=42)
        rf.fit(X, y)
        r2 = rf.score(X, y)
        y_pred = rf.predict(X)
        rmse = np.sqrt(np.mean((y - y_pred)**2))
        mae = np.mean(np.abs(y - y_pred))

        h = self._h(f"{Icons.STATS} Random Forest — Regresion")
        h += "<table style='font-size:12px;'>"
        h += self._r("Target", target_col)
        h += self._r("Features", len(nums))
        h += self._r("Observaciones", len(y))
        h += self._r("R²", f"{r2:.4f}")
        h += self._r("RMSE", f"{rmse:.4f}")
        h += self._r("MAE", f"{mae:.4f}")
        h += "</table>"

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5))

        ax1.scatter(y, y_pred, alpha=0.5, c='#4f6ef7', edgecolors='white', s=50)
        lims = [min(y.min(), y_pred.min()), max(y.max(), y_pred.max())]
        ax1.plot(lims, lims, '--', color='#ef4444', lw=1.5, label='Prediccion perfecta')
        ax1.set_xlabel('Observado')
        ax1.set_ylabel('Predicho')
        ax1.set_title(f'Observado vs Predicho (R²={r2:.3f})', fontweight='bold')
        ax1.legend(framealpha=0.9)

        sorted_idx = np.argsort(rf.get_feature_importance())[::-1][:min(8, len(nums))]
        ax2.barh(range(len(sorted_idx)), rf.get_feature_importance()[sorted_idx], color='#22c55e', edgecolor='white')
        ax2.set_yticks(range(len(sorted_idx)))
        ax2.set_yticklabels([nums[i] for i in sorted_idx])
        ax2.set_xlabel('Importancia')
        ax2.set_title('Importancia de Variables', fontweight='bold')
        ax2.invert_yaxis()

        fig.tight_layout()
        self._show_fig(fig)

        return h

    # --- Mann-Whitney U ---
    def _mannwhitney(self, c1, c2):
        if c1 not in self.data.columns or c2 not in self.data.columns:
            return "<b>Error:</b> Columnas no encontradas."
        d1, d2 = self.data[c1].dropna(), self.data[c2].dropna()
        if len(d1) < 2 or len(d2) < 2:
            return "<b>Error:</b> Minimo 2 obs por grupo."
        r = mannwhitneyu(d1.values, d2.values)
        if r is None:
            return "<b>Error:</b> No se pudo calcular."
        self._set_formula("Formula: Mann-Whitney U", "U = n1*n2 + n1*(n1+1)/2 - R1\nDonde R1 = suma de rangos del grupo 1", f"U = {r['u']:.1f}\np = {r['p']:.6f}\nn1={r['n1']}, n2={r['n2']}")
        h = self._h(f"{Icons.RUN} Mann-Whitney U — {c1} vs {c2}")
        h += "<table style='font-size:12px;'>"
        for l, v in [("Grupo 1", f"{c1} (n={r['n1']}, mediana={r['median1']:.2f})"),
                      ("Grupo 2", f"{c2} (n={r['n2']}, mediana={r['median2']:.2f})"),
                      ("U", f"{r['u']:.1f}"), ("p", f"{r['p']:.6f}")]:
            h += self._r(l, v)
        return h + "</table>" + self._ok(r['p'] < 0.05)

    # --- Wilcoxon pareado ---
    def _wilcoxon(self, c1, c2):
        if c1 not in self.data.columns or c2 not in self.data.columns:
            return "<b>Error:</b> Columnas no encontradas."
        d1, d2 = self.data[c1].dropna(), self.data[c2].dropna()
        n = min(len(d1), len(d2))
        r = wilcoxon_signed_rank(d1.values[:n], d2.values[:n])
        if r is None:
            return "<b>Error:</b> Minimo 5 pares con diferencias != 0."
        self._set_formula("Formula: Wilcoxon Signed-Rank", "W = suma de rangos de |diferencias| con signo", f"W = {r['w']:.1f}\np = {r['p']:.6f}\nn = {r['n']}")
        h = self._h(f"{Icons.RUN} Wilcoxon — {c1} vs {c2}")
        h += "<table style='font-size:12px;'>"
        for l, v in [("Pares (n)", r['n']), ("W", f"{r['w']:.1f}"), ("p", f"{r['p']:.6f}")]:
            h += self._r(l, v)
        return h + "</table>" + self._ok(r['p'] < 0.05)

    # --- Chi-cuadrado ---
    def _chi2(self):
        nums = self.data.select_dtypes(include="number").columns
        if len(nums) < 2:
            return "<b>Error:</b> Minimo 2 columnas numericas."
        d1 = self.data[nums[0]].dropna()
        d2 = self.data[nums[1]].dropna()
        n = min(len(d1), len(d2))
        if n < 4:
            return "<b>Error:</b> Minimo 4 datos."
        cats1 = np.unique(d1.values[:n])
        cats2 = np.unique(d2.values[:n])
        if len(cats1) > 10 or len(cats2) > 10:
            return "<b>Error:</b> Chi-cuadrado es para datos categoricos (max 10 categorias por variable)."
        matrix = np.zeros((len(cats1), len(cats2)))
        for v1, v2 in zip(d1.values[:n], d2.values[:n]):
            i = np.where(cats1 == v1)[0][0]
            j = np.where(cats2 == v2)[0][0]
            matrix[i, j] += 1
        if np.any(matrix < 0):
            return "<b>Error:</b> Tabla con valores negativos."
        r = chi_square_test(matrix)
        if r is None:
            return "<b>Error:</b> No se pudo calcular."
        self._set_formula("Formula: Chi-cuadrado", "X2 = Sum((O-E)^2 / E)\nE = (fila_total * col_total) / n_total", f"X2 = {r['chi2']:.4f}\np = {r['p']:.6f}\ndf = {r['df']}")
        h = self._h(f"{Icons.RUN} Chi-cuadrado")
        h += "<table style='font-size:12px;'>"
        for l, v in [("Chi2", f"{r['chi2']:.4f}"), ("p", f"{r['p']:.6f}"), ("df", r['df'])]:
            h += self._r(l, v)
        return h + "</table>" + self._ok(r['p'] < 0.05, "ASOCIACION", "SIN ASOCIACION")

    # --- Fisher exact ---
    def _fisher(self):
        nums = self.data.select_dtypes(include="number").columns
        if len(nums) < 2:
            return "<b>Error:</b> Minimo 2 columnas."
        table = self.data[nums[:2]].dropna().values
        if table.shape[0] < 2 or table.shape[1] < 2:
            return "<b>Error:</b> Tabla 2x2 requerida."
        a, b, c, d = int(table[0, 0]), int(table[0, 1]), int(table[1, 0]), int(table[1, 1])
        r = fisher_exact_test(a, b, c, d)
        self._set_formula("Formula: Fisher Exact", "P = (a+b)!(c+d)!(a+c)!(b+d)! / (a!b!c!d!n!)", f"OR = {r['odds_ratio']:.4f}\np = {r['p']:.6f}")
        h = self._h(f"{Icons.RUN} Fisher Exact")
        h += "<table style='font-size:12px;'>"
        for l, v in [("OR", f"{r['odds_ratio']:.4f}"), ("p", f"{r['p']:.6f}")]:
            h += self._r(l, v)
        return h + "</table>" + self._ok(r['p'] < 0.05, "ASOCIACION", "SIN ASOCIACION")

    # --- McNemar ---
    def _mcnemar(self):
        nums = self.data.select_dtypes(include="number").columns
        if len(nums) < 2:
            return "<b>Error:</b> Minimo 2 columnas."
        table = self.data[nums[:2]].dropna().values
        if table.shape[0] < 2 or table.shape[1] < 2:
            return "<b>Error:</b> Tabla 2x2."
        b, c = int(table[0, 1]), int(table[1, 0])
        r = mcnemar_test(b, c)
        self._set_formula("Formula: McNemar", "X2 = (|b-c|-1)^2 / (b+c)", f"b={b}, c={c}\nX2 = {r['chi2']:.4f}\np = {r['p']:.6f}")
        h = self._h(f"{Icons.RUN} McNemar")
        h += "<table style='font-size:12px;'>"
        for l, v in [("Discordantes b", b), ("Discordantes c", c), ("Chi2", f"{r['chi2']:.4f}"), ("p", f"{r['p']:.6f}")]:
            h += self._r(l, v)
        return h + "</table>" + self._ok(r['p'] < 0.05, "CAMBIO", "SIN CAMBIO")

    # --- Kruskal-Wallis ---
    def _kruskal(self):
        nums = self.data.select_dtypes(include="number").columns
        groups = [self.data[c].dropna().values for c in nums if len(self.data[c].dropna()) > 0]
        if len(groups) < 3:
            return "<b>Error:</b> Minimo 3 grupos."
        r = kruskal_wallis(groups)
        if r is None:
            return "<b>Error:</b> No se pudo calcular."
        self._set_formula("Formula: Kruskal-Wallis", "H = (12/n(n+1)) * Sum(Ri^2/ni) - 3(n+1)", f"H = {r['h']:.4f}\np = {r['p']:.6f}")
        h = self._h(f"{Icons.RUN} Kruskal-Wallis")
        h += "<table style='font-size:12px;'>"
        for l, v in [("H", f"{r['h']:.4f}"), ("p", f"{r['p']:.6f}"), ("Grupos", r['k'])]:
            h += self._r(l, v)
        return h + "</table>" + self._ok(r['p'] < 0.05, "DIFERENCIAS", "SIN DIFERENCIAS")

    # --- Friedman ---
    def _friedman(self):
        nums = self.data.select_dtypes(include="number").columns
        groups = [self.data[c].dropna().values for c in nums if len(self.data[c].dropna()) > 0]
        if len(groups) < 3:
            return "<b>Error:</b> Minimo 3 condiciones."
        r = friedman_test(*groups)
        if r is None:
            return "<b>Error:</b> No se pudo calcular."
        self._set_formula("Formula: Friedman", "X2r = (12/nk(k+1)) * Sum(Rj^2) - 3n(k+1)", f"X2 = {r['chi2']:.4f}\np = {r['p']:.6f}")
        h = self._h(f"{Icons.RUN} Friedman")
        h += "<table style='font-size:12px;'>"
        for l, v in [("Chi2", f"{r['chi2']:.4f}"), ("p", f"{r['p']:.6f}"), ("k", r['k'])]:
            h += self._r(l, v)
        return h + "</table>" + self._ok(r['p'] < 0.05, "DIFERENCIAS", "SIN DIFERENCIAS")

    # --- F-test ---
    def _ftest(self, c1, c2):
        if c1 not in self.data.columns or c2 not in self.data.columns:
            return "<b>Error:</b> Columnas no encontradas."
        d1, d2 = self.data[c1].dropna(), self.data[c2].dropna()
        if len(d1) < 3 or len(d2) < 3:
            return "<b>Error:</b> Minimo 3 obs por grupo."
        r = f_test_variances(d1.values, d2.values)
        if r is None:
            return "<b>Error:</b> No se pudo calcular."
        self._set_formula("Formula: F-test", "F = s1^2 / s2^2 (mayor/menor)", f"F = {r['f']:.4f}\np = {r['p']:.6f}")
        h = self._h(f"{Icons.RUN} F-test — {c1} vs {c2}")
        h += "<table style='font-size:12px;'>"
        for l, v in [("DE 1", f"{r['sd1']:.4f}"), ("DE 2", f"{r['sd2']:.4f}"),
                      ("F", f"{r['f']:.4f}"), ("p", f"{r['p']:.6f}")]:
            h += self._r(l, v)
        return h + "</table>" + self._ok(r['p'] < 0.05, "VARIANZAS DIFERENTES", "VARIANZAS SIMILARES")

    # --- Kappa ---
    def _kappa(self):
        nums = self.data.select_dtypes(include="number").columns
        if len(nums) < 2:
            return "<b>Error:</b> Minimo 2 columnas (evaluadores)."
        table = self.data[nums[:2]].dropna().values
        if table.shape[0] < 2 or table.shape[1] < 2:
            return "<b>Error:</b> Tabla 2x2."
        max_val = int(table.max())
        if max_val > 20:
            return f"<b>Error:</b> Kappa es para datos categoricos (0-20 max). Valores: 0 a {max_val}."
        matrix = np.zeros((max_val+1, max_val+1))
        for row in table:
            matrix[int(row[0]), int(row[1])] += 1
        r = cohens_kappa(matrix)
        if r is None:
            return "<b>Error:</b> No se pudo calcular."
        self._set_formula("Formula: Kappa de Cohen", "K = (Po - Pe) / (1 - Pe)", f"Kappa = {r['kappa']:.4f}\np = {r['p']:.6f}\nFuerza: {r['strength']}")
        h = self._h(f"{Icons.RUN} Kappa de Cohen")
        h += "<table style='font-size:12px;'>"
        for l, v in [("Kappa", f"{r['kappa']:.4f}"), ("Fuerza", r['strength']), ("p", f"{r['p']:.6f}")]:
            h += self._r(l, v)
        return h + "</table>"

    # --- ICC ---
    def _icc(self, c1, c2):
        if c1 not in self.data.columns or c2 not in self.data.columns:
            return "<b>Error:</b> Columnas no encontradas."
        d1, d2 = self.data[c1].dropna(), self.data[c2].dropna()
        n = min(len(d1), len(d2))
        if n < 3:
            return "<b>Error:</b> Minimo 3 pares."
        data = np.column_stack([d1.values[:n], d2.values[:n]])
        r = intraclass_correlation(data)
        if r is None:
            return "<b>Error:</b> No se pudo calcular."
        self._set_formula("Formula: ICC", "ICC = (MS_rows - MS_error) / (MS_rows + (k-1)*MS_error)", f"ICC = {r['icc']:.4f}\nF = {r['f']:.4f}\np = {r['p']:.6f}")
        h = self._h(f"{Icons.RUN} ICC — {c1} vs {c2}")
        h += "<table style='font-size:12px;'>"
        for l, v in [("ICC", f"{r['icc']:.4f}"), ("F", f"{r['f']:.4f}"), ("p", f"{r['p']:.6f}")]:
            h += self._r(l, v)
        return h + "</table>"

    # --- Cronbach alpha ---
    def _cronbach(self):
        nums = self.data.select_dtypes(include="number").columns
        if len(nums) < 3:
            return "<b>Error:</b> Minimo 3 items."
        data = self.data[nums].dropna().values
        r = cronbach_alpha(data)
        if r is None:
            return "<b>Error:</b> No se pudo calcular."
        self._set_formula("Formula: Alfa de Cronbach", "a = (k/(k-1)) * (1 - Sum(var_i)/var_total)", f"Alfa = {r['alpha']:.4f}\nk = {r['n_items']}")
        h = self._h(f"{Icons.RUN} Alfa de Cronbach")
        h += "<table style='font-size:12px;'>"
        h += self._r("Alfa", f"{r['alpha']:.4f}")
        h += self._r("Items", r['n_items'])
        h += "</table>"
        return h

    # --- Regresion lineal ---
    def _reg_lineal(self, c1, c2):
        if c1 not in self.data.columns or c2 not in self.data.columns:
            return "<b>Error:</b> Columnas no encontradas."
        x, y = self.data[c1].dropna(), self.data[c2].dropna()
        n = min(len(x), len(y))
        r = linear_regression(x.values[:n], y.values[:n])
        if r is None:
            return "<b>Error:</b> Minimo 3 datos."
        self._set_formula("Formula: Regresion Lineal", "y = b0 + b1*x\nb1 = S(x-xbar)(y-ybar) / S(x-xbar)^2", f"y = {r['intercept']:.4f} + {r['slope']:.4f}*x\nR2 = {r['r2']:.4f}\np = {r['p_slope']:.6f}")
        h = self._h(f"{Icons.CHART} Regresion Lineal — {c1} vs {c2}")
        h += "<table style='font-size:12px;'>"
        for l, v in [("Pendiente", f"{r['slope']:.4f}"), ("Intercepto", f"{r['intercept']:.4f}"),
                      ("R2", f"{r['r2']:.4f}"), ("p", f"{r['p_slope']:.6f}"), ("n", r['n'])]:
            h += self._r(l, v)
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(r['x'], r['y'], alpha=0.5, c='#4f6ef7', edgecolors='white', s=50)
        xl = np.linspace(r['x'].min(), r['x'].max(), 100)
        ax.plot(xl, r['intercept'] + r['slope']*xl, color='#ef4444', lw=2)
        ax.set_xlabel(c1); ax.set_ylabel(c2)
        ax.set_title(f'Regresion Lineal (R2={r["r2"]:.3f})', fontweight='bold')
        fig.tight_layout(); self._show_fig(fig)
        return h

    # --- Regresion multiple ---
    def _reg_multiple(self):
        nums = self.data.select_dtypes(include="number").columns.tolist()
        if len(nums) < 3:
            return "<b>Error:</b> Minimo 3 columnas (1 target + 2 predictors)."
        target = nums[-1]
        predictors = nums[:-1]
        X = self.data[predictors].dropna()
        y = self.data.loc[X.index, target].dropna()
        common = X.index.intersection(y.index)
        X, y = X.loc[common].values, y.loc[common].values
        r = multiple_regression(X, y)
        if r is None:
            return "<b>Error:</b> No se pudo calcular."
        self._set_formula("Formula: Regresion Multiple", "y = b0 + b1*x1 + b2*x2 + ...\nBeta = (X'X)^-1 X'Y", f"R2 = {r['r2']:.4f}\nR2 adj = {r['r2_adj']:.4f}\nF = {r['f']:.4f}")
        h = self._h(f"{Icons.CHART} Regresion Multiple — {target}")
        h += "<table style='font-size:12px;'>"
        h += self._r("R2", f"{r['r2']:.4f}")
        h += self._r("R2 ajustado", f"{r['r2_adj']:.4f}")
        h += self._r("F", f"{r['f']:.4f}")
        h += self._r("p modelo", f"{r['p_model']:.6f}")
        h += "</table><b>Coeficientes:</b><table style='font-size:12px;'>"
        labels = ["Intercepto"] + predictors
        for i, l in enumerate(labels):
            h += self._r(l, f"b={r['coeffs'][i]:.4f}, p={r['p'][i]:.4f}")
        h += "</table>"
        return h

    # --- Regresion logistica ---
    def _reg_logistica(self):
        nums = self.data.select_dtypes(include="number").columns.tolist()
        if len(nums) < 3:
            return "<b>Error:</b> Minimo 3 columnas."
        target = nums[-1]
        y_vals = self.data[target].dropna().unique()
        if not all(v in [0, 1] for v in y_vals):
            return f"<b>Error:</b> Target debe ser 0/1."
        predictors = nums[:-1]
        X = self.data[predictors].dropna()
        y = self.data.loc[X.index, target].dropna()
        common = X.index.intersection(y.index)
        X, y = X.loc[common].values, y.loc[common].values
        r = logistic_regression(X, y)
        if r is None:
            return "<b>Error:</b> No se pudo calcular."
        self._set_formula("Formula: Regresion Logistica", "ln(p/(1-p)) = b0 + b1*x1 + ...\nOR = exp(b)", f"Accuracy = {r['accuracy']:.4f}\nAIC = {r['aic']:.2f}")
        h = self._h(f"{Icons.RUN} Regresion Logistica — {target}")
        h += "<table style='font-size:12px;'>"
        h += self._r("Accuracy", f"{r['accuracy']:.4f}")
        h += self._r("AIC", f"{r['aic']:.2f}")
        h += "</table><b>Coeficientes:</b><table style='font-size:12px;'>"
        labels = ["Intercepto"] + predictors
        for i, l in enumerate(labels):
            h += self._r(l, f"b={r['coeffs'][i]:.4f}, OR={r['odds_ratios'][i]:.4f}, p={r['p'][i]:.4f}")
        h += "</table>"
        return h

    # --- Odds Ratio ---
    def _odds_ratio(self):
        nums = self.data.select_dtypes(include="number").columns
        if len(nums) < 2:
            return "<b>Error:</b> Minimo 2 columnas."
        table = self.data[nums[:2]].dropna().values
        if table.shape[0] < 2 or table.shape[1] < 2:
            return "<b>Error:</b> Tabla 2x2."
        a, b, c, d = int(table[0, 0]), int(table[0, 1]), int(table[1, 0]), int(table[1, 1])
        r = odds_ratio(a, b, c, d)
        self._set_formula("Formula: Odds Ratio", "OR = (a*d)/(b*c)\nSE(ln OR) = sqrt(1/a+1/b+1/c+1/d)", f"OR = {r['or']:.4f}\nIC95% = [{r['ci_lower']:.4f}, {r['ci_upper']:.4f}]\np = {r['p']:.6f}")
        h = self._h(f"{Icons.RUN} Odds Ratio")
        h += "<table style='font-size:12px;'>"
        for l, v in [("OR", f"{r['or']:.4f}"), ("IC 95%", f"[{r['ci_lower']:.4f}, {r['ci_upper']:.4f}]"), ("p", f"{r['p']:.6f}")]:
            h += self._r(l, v)
        return h + "</table>"

    # --- Riesgo Relativo ---
    def _riesgo_relativo(self):
        nums = self.data.select_dtypes(include="number").columns
        if len(nums) < 2:
            return "<b>Error:</b> Minimo 2 columnas."
        table = self.data[nums[:2]].dropna().values
        if table.shape[0] < 2 or table.shape[1] < 2:
            return "<b>Error:</b> Tabla 2x2."
        a, b, c, d = int(table[0, 0]), int(table[0, 1]), int(table[1, 0]), int(table[1, 1])
        r = relative_risk(a, b, c, d)
        if r is None:
            return "<b>Error:</b> No se pudo calcular."
        self._set_formula("Formula: Riesgo Relativo", "RR = (a/(a+b)) / (c/(c+d))\nNNT = 1/ARR", f"RR = {r['rr']:.4f}\nIC95% = [{r['ci_lower']:.4f}, {r['ci_upper']:.4f}]\nNNT = {r['nnt']:.1f}")
        h = self._h(f"{Icons.RUN} Riesgo Relativo")
        h += "<table style='font-size:12px;'>"
        for l, v in [("RR", f"{r['rr']:.4f}"), ("IC 95%", f"[{r['ci_lower']:.4f}, {r['ci_upper']:.4f}]"), ("NNT", f"{r['nnt']:.1f}")]:
            h += self._r(l, v)
        return h + "</table>"

    # --- Diagnostic test ---
    def _diag_test(self):
        nums = self.data.select_dtypes(include="number").columns
        if len(nums) < 2:
            return "<b>Error:</b> Minimo 2 columnas."
        table = self.data[nums[:2]].dropna().values
        if table.shape[0] < 2 or table.shape[1] < 2:
            return "<b>Error:</b> Tabla 2x2."
        a, b, c, d = int(table[0, 0]), int(table[0, 1]), int(table[1, 0]), int(table[1, 1])
        r = diagnostic_test(a, b, c, d)
        self._set_formula("Formula: Prueba Diagnostica", "Sens=a/(a+c), Spec=d/(b+d)\nPPV=a/(a+b), NPV=d/(c+d)", f"Sens={r['sens']:.4f}, Spec={r['spec']:.4f}\nPPV={r['ppv']:.4f}, NPV={r['npv']:.4f}")
        h = self._h(f"{Icons.RUN} Prueba Diagnostica")
        h += "<table style='font-size:12px;'>"
        for l, v in [("Sensibilidad", f"{r['sens']:.4f}"), ("Especificidad", f"{r['spec']:.4f}"),
                      ("VPP", f"{r['ppv']:.4f}"), ("VPN", f"{r['npv']:.4f}"),
                      ("Exactitud", f"{r['acc']:.4f}"), ("LR+", f"{r['plr']:.4f}"), ("LR-", f"{r['nlr']:.4f}")]:
            h += self._r(l, v)
        return h + "</table>"

    # --- Outliers Grubbs ---
    def _outliers_grubbs(self, col):
        if col not in self.data.columns:
            return f"<b>Error:</b> '{col}' no encontrada."
        d = self.data[col].dropna()
        r = grubbs_test(d.values)
        if r is None:
            return "<b>Error:</b> Minimo 5 datos."
        self._set_formula("Formula: Grubbs", "G = |xi - xbar| / s", f"G = {r['g']:.4f}\nG critico = {r['g_crit']:.4f}\nOutlier: {r['outlier_value']:.4f}")
        h = self._h(f"{Icons.WARN} Outliers — Grubbs ({col})")
        h += "<table style='font-size:12px;'>"
        for l, v in [("Valor", f"{r['outlier_value']:.4f}"), ("G", f"{r['g']:.4f}"),
                      ("G critico", f"{r['g_crit']:.4f}"), ("Es outlier?", "SI" if r['is_outlier'] else "NO")]:
            h += self._r(l, v)
        return h + "</table>"

    # --- Outliers Tukey ---
    def _outliers_tukey(self, col):
        if col not in self.data.columns:
            return f"<b>Error:</b> '{col}' no encontrada."
        d = self.data[col].dropna()
        r = tukey_outliers(d.values)
        if r is None:
            return "<b>Error:</b> Minimo 4 datos."
        self._set_formula("Formula: Tukey", "Lim interno: Q1-1.5*IQR, Q3+1.5*IQR\nLim externo: Q1-3*IQR, Q3+3*IQR", f"IQR = {r['iqr']:.4f}\nSuaves: {r['n_mild']}\nExtremos: {r['n_extreme']}")
        h = self._h(f"{Icons.WARN} Outliers — Tukey ({col})")
        h += "<table style='font-size:12px;'>"
        h += self._r("IQR", f"{r['iqr']:.4f}")
        h += self._r("Outliers suaves", f"{r['n_mild']}")
        h += self._r("Outliers extremos", f"{r['n_extreme']}")
        if r['outliers_mild']:
            h += self._r("Valores", str(r['outliers_mild'][:5]))
        h += "</table>"
        return h

    # --- Intervalos de referencia ---
    def _ref_interval(self, col):
        if col not in self.data.columns:
            return f"<b>Error:</b> '{col}' no encontrada."
        d = self.data[col].dropna()
        if len(d) < 20:
            return "<b>Error:</b> Minimo 20 datos."
        ri = reference_interval(d.values)
        if ri is None:
            return "<b>Error:</b> No se pudo calcular."
        self._set_formula("Formula: Intervalo de Referencia", "Basado en percentiles 2.5 y 97.5\nIC via bootstrap", f"Limite inf (2.5%): {ri['lower']:.4f}\nLimite sup (97.5%): {ri['upper']:.4f}")
        h = self._h(f"{Icons.STATS} Intervalos de Referencia — {col}")
        h += "<table style='font-size:12px;'>"
        h += self._r("Limite inferior (2.5%)", f"{ri['lower']:.4f}")
        h += self._r("Limite superior (97.5%)", f"{ri['upper']:.4f}")
        h += self._r("IC lim inf", f"[{ri['ci_lower_low']:.4f}, {ri['ci_lower_high']:.4f}]")
        h += self._r("IC lim sup", f"[{ri['ci_upper_low']:.4f}, {ri['ci_upper_high']:.4f}]")
        h += "</table>"
        return h

    # --- Asimetria y curtosis ---
    def _skew_kurt(self, col):
        if col not in self.data.columns:
            return f"<b>Error:</b> '{col}' no encontrada."
        d = self.data[col].dropna()
        sk = skewness_test(d.values)
        ku = kurtosis_test(d.values)
        if sk is None or ku is None:
            return "<b>Error:</b> Minimo 8 datos."
        self._set_formula("Formula: Asimetria y Curtosis", "Sesgo = E[(x-mu)^3]/sigma^3\nCurtosis = E[(x-mu)^4]/sigma^4 - 3", f"Sesgo = {sk['skewness']:.4f} (p={sk['p']:.4f})\nCurtosis = {ku['kurtosis']:.4f} (p={ku['p']:.4f})")
        h = self._h(f"{Icons.STATS} Asimetria y Curtosis — {col}")
        h += "<table style='font-size:12px;'>"
        h += self._r("Asimetria", f"{sk['skewness']:.4f} (p={sk['p']:.4f})")
        h += self._r("Curtosis", f"{ku['kurtosis']:.4f} (p={ku['p']:.4f})")
        h += "</table>"
        return h

    # --- Media recortada ---
    def _trimmed(self, col):
        if col not in self.data.columns:
            return f"<b>Error:</b> '{col}' no encontrada."
        d = self.data[col].dropna()
        r = trimmed_mean(d.values, 0.1)
        if r is None:
            return "<b>Error:</b> Minimo 5 datos."
        self._set_formula("Formula: Media Recortada", "Recortar 10% superior e inferior", f"Media original = {np.mean(d.values):.4f}\nMedia recortada = {r['mean']:.4f}\nSE = {r['se']:.4f}")
        h = self._h(f"{Icons.STATS} Media Recortada (10%) — {col}")
        h += "<table style='font-size:12px;'>"
        h += self._r("Media original", f"{np.mean(d.values):.4f}")
        h += self._r("Media recortada", f"{r['mean']:.4f}")
        h += self._r("IC 95%", f"[{r['ci95'][0]:.4f}, {r['ci95'][1]:.4f}]")
        h += "</table>"
        return h

    # --- Correlacion parcial ---
    def _partial_corr(self, c1, c2, c3):
        if c3 == "(ninguna)" or c3 not in self.data.columns:
            return "<b>Error:</b> Selecciona Variable 3 para controlar."
        if c1 not in self.data.columns or c2 not in self.data.columns:
            return "<b>Error:</b> Columnas no encontradas."
        df = self.data[[c1, c2, c3]].dropna()
        if len(df) < 4:
            return "<b>Error:</b> Minimo 4 datos."
        r = partial_correlation(df[c1].values, df[c2].values, df[c3].values)
        if r is None:
            return "<b>Error:</b> No se pudo calcular."
        self._set_formula("Formula: Correlacion Parcial", "r_xy.z = (r_xy - r_xz*r_yz) / sqrt((1-r_xz^2)(1-r_yz^2))", f"r = {r['r_partial']:.4f}\np = {r['p']:.6f}")
        h = self._h(f"{Icons.CHART} Correlacion Parcial — {c1}, {c2} | {c3}")
        h += "<table style='font-size:12px;'>"
        for l, v in [("r parcial", f"{r['r_partial']:.4f}"), ("p", f"{r['p']:.6f}"), ("df", r['df'])]:
            h += self._r(l, v)
        return h + "</table>" + self._ok(r['p'] < 0.05, "CORRELACION", "SIN CORRELACION")

    # --- Core Module Runners ---
    def _run_core(self, func_name, c1=None, c2=None):
        """Run a core module function and display results."""
        try:
            if func_name == "geometric_mean":
                if c1 is None or c1 not in self.data.columns:
                    return "<b>Error:</b> Selecciona una columna."
                d = self.data[c1].dropna()
                if d.min() <= 0:
                    return "<b>Error:</b> La media geométrica requiere datos positivos."
                result = geometric_mean(d)
                self._set_formula("Formula: Media Geométrica", "GM = (x1 × x2 × ... × xn)^(1/n)")
                h = self._h(f"{Icons.CHART} Media Geométrica — {c1}")
                h += "<table style='font-size:12px;'>"
                h += self._r("Resultado", f"{result:.4f}")
                h += self._r("n", len(d))
                return h + "</table>"

            elif func_name == "harmonic_mean":
                if c1 is None or c1 not in self.data.columns:
                    return "<b>Error:</b> Selecciona una columna."
                d = self.data[c1].dropna()
                if d.min() <= 0:
                    return "<b>Error:</b> La media armónica requiere datos positivos."
                result = harmonic_mean(d)
                self._set_formula("Formula: Media Armónica", "HM = n / (1/x1 + 1/x2 + ... + 1/xn)")
                h = self._h(f"{Icons.CHART} Media Armónica — {c1}")
                h += "<table style='font-size:12px;'>"
                h += self._r("Resultado", f"{result:.4f}")
                h += self._r("n", len(d))
                return h + "</table>"

            elif func_name == "ttest_1sample":
                if c1 is None or c1 not in self.data.columns:
                    return "<b>Error:</b> Selecciona una columna."
                d = self.data[c1].dropna()
                result = ttest_1sample(d, mu=0)
                self._set_formula("Formula: t-test 1 Muestra", "t = (x̄ - μ₀) / (s / √n)")
                h = self._h(f"{Icons.CHART} t-test 1 Muestra — {c1}")
                h += "<table style='font-size:12px;'>"
                h += self._r("t", f"{result['t']:.4f}")
                h += self._r("p", f"{result['p']:.6f}")
                h += self._r("gl", result['df'])
                h += self._r("Media", f"{result['mean']:.4f}")
                return h + "</table>" + self._ok(result['p'] < 0.05, "DIFERENTE DE 0", "IGUAL A 0")

            elif func_name == "anova_oneway":
                if self.data.shape[1] < 2:
                    return "<b>Error:</b> Se necesitan al menos 2 columnas."
                groups = [self.data.iloc[:, i].dropna().values for i in range(self.data.shape[1])]
                result = anova_oneway(groups)
                self._set_formula("Formula: ANOVA Una Vía", "F = MS_between / MS_within")
                h = self._h(f"{Icons.CHART} ANOVA Una Vía (Core)")
                h += "<table style='font-size:12px;'>"
                h += self._r("F", f"{result['F']:.4f}")
                h += self._r("p", f"{result['p']:.6f}")
                h += self._r("gl entre", result['df_between'])
                h += self._r("gl dentro", result['df_within'])
                return h + "</table>" + self._ok(result['p'] < 0.05, "DIFERENCIAS SIGNIFICATIVAS", "SIN DIFERENCIAS")

            elif func_name == "sign_test":
                if c1 is None or c2 is None:
                    return "<b>Error:</b> Selecciona 2 columnas."
                if c1 not in self.data.columns or c2 not in self.data.columns:
                    return "<b>Error:</b> Columnas no encontradas."
                d1 = self.data[c1].dropna()
                d2 = self.data[c2].dropna()
                result = sign_test(d1, d2)
                self._set_formula("Formula: Sign Test", "p = Σ C(n,k) × 0.5^n para k ≤ observados")
                h = self._h(f"{Icons.CHART} Sign Test — {c1} vs {c2}")
                h += "<table style='font-size:12px;'>"
                h += self._r("Estadístico", f"{result['statistic']:.4f}")
                h += self._r("p", f"{result['p']:.6f}")
                return h + "</table>" + self._ok(result['p'] < 0.05, "DIFERENCIA SIGNIFICATIVA", "SIN DIFERENCIA")

            elif func_name == "cochran_q":
                if self.data.shape[1] < 2:
                    return "<b>Error:</b> Se necesitan al menos 2 columnas."
                result = cochran_q(self.data.values)
                self._set_formula("Formula: Cochran Q", "Q = (k-1) × [k×ΣC² - T²] / [k×T - ΣR²]")
                h = self._h(f"{Icons.CHART} Cochran Q")
                h += "<table style='font-size:12px;'>"
                h += self._r("Q", f"{result['Q']:.4f}")
                h += self._r("p", f"{result['p']:.6f}")
                h += self._r("gl", result['df'])
                return h + "</table>" + self._ok(result['p'] < 0.05, "DIFERENCIAS SIGNIFICATIVAS", "SIN DIFERENCIAS")

            elif func_name == "weighted_kappa":
                if self.data.shape[1] < 2:
                    return "<b>Error:</b> Se necesitan 2 columnas categóricas."
                d1 = self.data.iloc[:, 0].dropna()
                d2 = self.data.iloc[:, 1].dropna()
                min_len = min(len(d1), len(d2))
                d1, d2 = d1[:min_len], d2[:min_len]
                cats = sorted(set(d1) | set(d2))
                n = len(cats)
                matrix = np.zeros((n, n))
                for a, b in zip(d1, d2):
                    i, j = cats.index(a), cats.index(b)
                    matrix[i][j] += 1
                result = weighted_kappa(matrix)
                self._set_formula("Formula: Kappa Ponderado", "κ_w = 1 - (Σ w_ij × O_ij) / (Σ w_ij × E_ij)")
                h = self._h(f"{Icons.CHART} Kappa Ponderado")
                h += "<table style='font-size:12px;'>"
                h += self._r("Kappa", f"{result['kappa']:.4f}")
                h += self._r("SE", f"{result['se']:.4f}")
                h += self._r("95% CI", f"[{result['ci_low']:.4f}, {result['ci_high']:.4f}]")
                return h + "</table>"

            elif func_name == "deming":
                if c1 is None or c2 is None:
                    return "<b>Error:</b> Selecciona 2 columnas."
                if c1 not in self.data.columns or c2 not in self.data.columns:
                    return "<b>Error:</b> Columnas no encontradas."
                x = self.data[c1].dropna().values
                y = self.data[c2].dropna().values
                min_len = min(len(x), len(y))
                x, y = x[:min_len], y[:min_len]
                result = deming_regression(x, y)
                self._set_formula("Formula: Deming Regression", "y = β₀ + β₁x (ajustada para error en ambas variables)")
                h = self._h(f"{Icons.CHART} Deming Regression — {c1} vs {c2}")
                h += "<table style='font-size:12px;'>"
                h += self._r("Pendiente", f"{result['slope']:.4f}")
                h += self._r("Intercepto", f"{result['intercept']:.4f}")
                h += self._r("95% CI pendiente", f"[{result['slope_ci_low']:.4f}, {result['slope_ci_high']:.4f}]")
                return h + "</table>"

            elif func_name == "cv_duplicates":
                if c1 is None or c2 is None:
                    return "<b>Error:</b> Selecciona 2 columnas."
                if c1 not in self.data.columns or c2 not in self.data.columns:
                    return "<b>Error:</b> Columnas no encontradas."
                d1 = self.data[c1].dropna().values
                d2 = self.data[c2].dropna().values
                min_len = min(len(d1), len(d2))
                d1, d2 = d1[:min_len], d2[:min_len]
                result = cv_from_duplicates(d1, d2)
                self._set_formula("Formula: CV desde Duplicatas", "CV = (DE / Media) × 100%")
                h = self._h(f"{Icons.CHART} CV desde Duplicatas")
                h += "<table style='font-size:12px;'>"
                h += self._r("CV", f"{result['cv']:.2f}%")
                h += self._r("CV intra", f"{result['cv_intra']:.2f}%")
                h += self._r("CV inter", f"{result['cv_inter']:.2f}%")
                return h + "</table>"

            elif func_name == "likelihood_ratios":
                if self.data.shape[0] < 2 or self.data.shape[1] < 2:
                    return "<b>Error:</b> Se necesita matriz 2x2 con TP, FP, FN, TN."
                a = int(self.data.iloc[0, 0])
                b = int(self.data.iloc[0, 1])
                c = int(self.data.iloc[1, 0])
                d = int(self.data.iloc[1, 1])
                result = likelihood_ratios(a, b, c, d)
                self._set_formula("Formula: Likelihood Ratios", "LR+ = Sens / (1 - Spec)\nLR- = (1 - Sens) / Spec")
                h = self._h(f"{Icons.CHART} Likelihood Ratios")
                h += "<table style='font-size:12px;'>"
                h += self._r("LR+", f"{result['plr']:.4f}")
                h += self._r("95% CI LR+", f"[{result['plr_ci_low']:.4f}, {result['plr_ci_high']:.4f}]")
                h += self._r("LR-", f"{result['nlr']:.4f}")
                h += self._r("95% CI LR-", f"[{result['nlr_ci_low']:.4f}, {result['nlr_ci_high']:.4f}]")
                return h + "</table>"

            elif func_name == "compare_means":
                if self.data.shape[0] < 6:
                    return "<b>Error:</b> Se necesitan 6 valores: m1, sd1, n1, m2, sd2, n2."
                m1 = self.data.iloc[0, 0]
                sd1 = self.data.iloc[1, 0]
                n1 = int(self.data.iloc[2, 0])
                m2 = self.data.iloc[3, 0]
                sd2 = self.data.iloc[4, 0]
                n2 = int(self.data.iloc[5, 0])
                result = compare_two_means(m1, sd1, n1, m2, sd2, n2)
                self._set_formula("Formula: Comparar 2 Medias", "t = (m1 - m2) / √(sd1²/n1 + sd2²/n2)")
                h = self._h(f"{Icons.CHART} Comparar 2 Medias")
                h += "<table style='font-size:12px;'>"
                h += self._r("t", f"{result['t']:.4f}")
                h += self._r("p", f"{result['p']:.6f}")
                h += self._r("Diferencia", f"{result['diff']:.4f}")
                return h + "</table>" + self._ok(result['p'] < 0.05, "DIFERENCIA SIGNIFICATIVA", "SIN DIFERENCIA")

            elif func_name == "compare_props":
                if self.data.shape[0] < 4:
                    return "<b>Error:</b> Se necesitan 4 valores: p1, n1, p2, n2."
                p1 = self.data.iloc[0, 0]
                n1 = int(self.data.iloc[1, 0])
                p2 = self.data.iloc[2, 0]
                n2 = int(self.data.iloc[3, 0])
                result = compare_two_proportions(p1, n1, p2, n2)
                self._set_formula("Formula: Comparar 2 Proporciones", "z = (p1 - p2) / √(p̂(1-p̂)(1/n1 + 1/n2))")
                h = self._h(f"{Icons.CHART} Comparar 2 Proporciones")
                h += "<table style='font-size:12px;'>"
                h += self._r("z", f"{result['z']:.4f}")
                h += self._r("p", f"{result['p']:.6f}")
                h += self._r("Diferencia", f"{result['diff']:.4f}")
                return h + "</table>" + self._ok(result['p'] < 0.05, "DIFERENCIA SIGNIFICATIVA", "SIN DIFERENCIA")

            elif func_name == "compare_auc":
                if self.data.shape[0] < 6:
                    return "<b>Error:</b> Se necesitan 6 valores: auc1, se1, n1, auc2, se2, n2."
                auc1 = self.data.iloc[0, 0]
                se1 = self.data.iloc[1, 0]
                n1 = int(self.data.iloc[2, 0])
                auc2 = self.data.iloc[3, 0]
                se2 = self.data.iloc[4, 0]
                n2 = int(self.data.iloc[5, 0])
                result = compare_two_auc(auc1, se1, n1, auc2, se2, n2)
                self._set_formula("Formula: Comparar 2 AUC", "z = (AUC1 - AUC2) / √(SE1² + SE2²)")
                h = self._h(f"{Icons.CHART} Comparar 2 AUC")
                h += "<table style='font-size:12px;'>"
                h += self._r("z", f"{result['z']:.4f}")
                h += self._r("p", f"{result['p']:.6f}")
                return h + "</table>" + self._ok(result['p'] < 0.05, "DIFERENCIAS SIGNIFICATIVAS", "SIN DIFERENCIAS")

            elif func_name == "percentile_table":
                if c1 is None or c1 not in self.data.columns:
                    return "<b>Error:</b> Selecciona una columna."
                d = self.data[c1].dropna()
                result = percentile_table(d)
                self._set_formula("Formula: Percentiles", "P_k = valor en posición k×(n+1)/100")
                h = self._h(f"{Icons.CHART} Tabla de Percentiles — {c1}")
                h += "<table style='font-size:12px;'>"
                h += "<tr><th>Percentil</th><th>Valor</th><th>95% CI</th></tr>"
                for p, val, ci_low, ci_high in zip(result['percentiles'], result['values'], result['ci_low'], result['ci_high']):
                    h += f"<tr><td>{p}%</td><td>{val:.4f}</td><td>[{ci_low:.4f}, {ci_high:.4f}]</td></tr>"
                return h + "</table>"

            elif func_name == "age_related":
                if self.data.shape[1] < 2:
                    return "<b>Error:</b> Se necesitan 2 columnas: edad, valor."
                ages = self.data.iloc[:, 0].dropna().values
                values = self.data.iloc[:, 1].dropna().values
                min_len = min(len(ages), len(values))
                ages, values = ages[:min_len], values[:min_len]
                result = age_related_reference(ages, values)
                self._set_formula("Formula: Intervalos por Edad", "Intervalos basados en percentiles por grupo de edad")
                h = self._h(f"{Icons.CHART} Intervalos de Referencia por Edad")
                h += "<table style='font-size:12px;'>"
                h += self._r("Grupo", f"{result['age_min']}-{result['age_max']} años")
                h += self._r("n", result['n'])
                h += self._r("Media", f"{result['mean']:.4f}")
                h += self._r("2.5%-97.5%", f"[{result['ref_low']:.4f}, {result['ref_high']:.4f}]")
                return h + "</table>"

            elif func_name == "generalized_esd":
                if c1 is None or c1 not in self.data.columns:
                    return "<b>Error:</b> Selecciona una columna."
                d = self.data[c1].dropna().values
                result = generalized_esd(d, max_outliers=10, alpha=0.05)
                self._set_formula("Formula: ESD Generalizado", "R_i = |x_i - x̄| / s")
                h = self._h(f"{Icons.CHART} Test ESD Generalizado — {c1}")
                h += "<table style='font-size:12px;'>"
                h += self._r("Outliers encontrados", len(result['outliers']))
                if result['outliers']:
                    h += self._r("Valores", ", ".join([f"{v:.4f}" for v in result['outliers']]))
                h += self._r("Índices", str(result['indices']))
                return h + "</table>"

            elif func_name == "bootstrap_median":
                if c1 is None or c1 not in self.data.columns:
                    return "<b>Error:</b> Selecciona una columna."
                d = self.data[c1].dropna().values
                result = bootstrap_median(d)
                self._set_formula("Formula: Bootstrap Mediana", "IC = percentiles de la distribución bootstrap")
                h = self._h(f"{Icons.CHART} Bootstrap (Mediana) — {c1}")
                h += "<table style='font-size:12px;'>"
                h += self._r("Mediana", f"{result['median']:.4f}")
                h += self._r("95% CI", f"[{result['ci_low']:.4f}, {result['ci_high']:.4f}]")
                return h + "</table>"

            elif func_name == "bootstrap_regression":
                if c1 is None or c2 is None:
                    return "<b>Error:</b> Selecciona 2 columnas."
                if c1 not in self.data.columns or c2 not in self.data.columns:
                    return "<b>Error:</b> Columnas no encontradas."
                x = self.data[c1].dropna().values
                y = self.data[c2].dropna().values
                min_len = min(len(x), len(y))
                x, y = x[:min_len], y[:min_len]
                result = bootstrap_regression(x, y)
                self._set_formula("Formula: Bootstrap Regresión", "IC para coeficientes de regresión")
                h = self._h(f"{Icons.CHART} Bootstrap (Regresión) — {c1} vs {c2}")
                h += "<table style='font-size:12px;'>"
                h += self._r("Pendiente", f"{result['slope']:.4f}")
                h += self._r("95% CI pendiente", f"[{result['slope_ci_low']:.4f}, {result['slope_ci_high']:.4f}]")
                h += self._r("Intercepto", f"{result['intercept']:.4f}")
                return h + "</table>"

            elif func_name == "sample_size_corr":
                if c1 is None or c2 is None:
                    return "<b>Error:</b> Selecciona 2 columnas para calcular r."
                if c1 not in self.data.columns or c2 not in self.data.columns:
                    return "<b>Error:</b> Columnas no encontradas."
                r_result = pearson_r(self.data[c1].dropna(), self.data[c2].dropna())
                r = abs(r_result['r'])
                result = sample_size_correlation(r)
                self._set_formula("Formula: Tamaño Muestral (Correlación)", "n = [(Z_α/2 + Z_β) / arctanh(r)]² + 3")
                h = self._h(f"{Icons.CHART} Tamaño Muestral (Correlación)")
                h += "<table style='font-size:12px;'>"
                h += self._r("r observado", f"{r:.4f}")
                h += self._r("n necesario", result['n'])
                h += self._r("Poder", f"{result['power']:.4f}")
                return h + "</table>"

            else:
                return f"<b>Error:</b> Función desconocida: {func_name}"

        except Exception as e:
            return f"<p style='color:red'>Error en {func_name}: {str(e)}</p>"

    def _run_two_way_anova(self):
        """Run Two-way ANOVA."""
        if self.data.shape[1] < 2:
            return "<b>Error:</b> Se necesitan al menos 2 columnas."
        try:
            n_per_cell = max(1, self.data.shape[0] // 4)
            result = two_way_anova(self.data.values, n_per_cell)
            self._set_formula("Formula: ANOVA Dos Vías", "F = MS_between / MS_within para cada factor e interacción")
            h = self._h(f"{Icons.CHART} ANOVA Dos Vías")
            h += "<table style='font-size:12px;'>"
            h += self._r("Factor A", f"F={result['F_A']:.4f}, p={result['p_A']:.4f}, gl={result['df_A']}")
            h += self._r("Factor B", f"F={result['F_B']:.4f}, p={result['p_B']:.4f}, gl={result['df_B']}")
            h += self._r("Interacción A×B", f"F={result['F_AB']:.4f}, p={result['p_AB']:.4f}, gl={result['df_AB']}")
            h += self._r("Error", f"gl={result['df_error']}")
            return h + "</table>"
        except Exception as e:
            return f"<p style='color:red'>Error: {str(e)}</p>"

    def _run_ancova(self, c1, c2, c3):
        """Run ANCOVA."""
        if c1 is None or c2 is None or c3 is None:
            return "<b>Error:</b> Selecciona Variable dependiente (V1), Factor (V2), y Covariable (V3)."
        if c1 not in self.data.columns or c2 not in self.data.columns or c3 not in self.data.columns:
            return "<b>Error:</b> Columnas no encontradas."
        try:
            dependent = self.data[c1].dropna().values
            group = self.data[c2].dropna().values
            covariate = self.data[c3].dropna().values
            min_len = min(len(dependent), len(group), len(covariate))
            result = ancova(dependent[:min_len], group[:min_len], covariate[:min_len])
            self._set_formula("Formula: ANCOVA", "F = MS_group / MS_error (ajustado por covariable)")
            h = self._h(f"{Icons.CHART} ANCOVA — {c1} por {c2} | {c3}")
            h += "<table style='font-size:12px;'>"
            h += self._r("Factor", f"F={result['F']:.4f}, p={result['p']:.6f}, gl={result['df_group']}")
            h += self._r("Covariable", f"F={result['F_covariate']:.4f}, p={result['p_covariate']:.6f}")
            h += self._r("η²", f"{result['eta_squared']:.4f}")
            h += self._r("Error", f"gl={result['df_error']}")
            return h + "</table>" + self._ok(result['p'] < 0.05, "EFECTO SIGNIFICATIVO", "SIN EFECTO SIGNIFICATIVO")
        except Exception as e:
            return f"<p style='color:red'>Error: {str(e)}</p>"

    def _run_repeated_measures(self):
        """Run Repeated Measures ANOVA."""
        if self.data.shape[1] < 3:
            return "<b>Error:</b> Se necesitan al menos 3 columnas (mediciones repetidas)."
        try:
            result = repeated_measures_anova(self.data.values)
            self._set_formula("Formula: Medidas Repetidas", "F = MS_time / MS_error (con corrección GG)")
            h = self._h(f"{Icons.CHART} ANOVA Medidas Repetidas")
            h += "<table style='font-size:12px;'>"
            h += self._r("F", f"{result['F']:.4f}")
            h += self._r("p", f"{result['p']:.6f}")
            h += self._r("F (GG corregido)", f"{result['F_gg']:.4f}")
            h += self._r("p (GG corregido)", f"{result['p_gg']:.6f}")
            h += self._r("Epsilon (GG)", f"{result['epsilon']:.4f}")
            h += self._r("gl tiempo", result['df_time'])
            h += self._r("gl error", result['df_error'])
            return h + "</table>" + self._ok(result['p_gg'] < 0.05, "CAMBIOS SIGNIFICATIVOS ENTRE TIEMPOS", "SIN CAMBIOS SIGNIFICATIVOS")
        except Exception as e:
            return f"<p style='color:red'>Error: {str(e)}</p>"

    def _run_cox(self, c1, c2):
        """Run Cox Regression."""
        if c1 is None or c2 is None:
            return "<b>Error:</b> Selecciona Tiempo (V1) y Evento (V2, 0/1)."
        if c1 not in self.data.columns or c2 not in self.data.columns:
            return "<b>Error:</b> Columnas no encontradas."
        try:
            times = self.data[c1].dropna().values
            events = self.data[c2].dropna().values
            covariates = self.data.iloc[:, 3:].dropna().values if self.data.shape[1] > 2 else np.ones((len(times), 1))
            min_len = min(len(times), len(events), covariates.shape[0])
            result = cox_regression(times[:min_len], events[:min_len], covariates[:min_len])
            self._set_formula("Formula: Cox PH", "h(t) = h₀(t) × exp(β₁x₁ + β₂x₂ + ...)")
            h = self._h(f"{Icons.CHART} Cox Regression")
            h += "<table style='font-size:12px;'>"
            h += self._r("n", result['n'])
            h += self._r("Eventos", result['events'])
            h += self._r("Log-likelihood", f"{result['log_likelihood']:.4f}")
            h += self._r("AIC", f"{result['aic']:.4f}")
            for i, (hr, p, ci_l, ci_h) in enumerate(zip(result['hazard_ratios'], result['p_values'], result['hr_ci_low'], result['hr_ci_high'])):
                h += self._r(f"Covariable {i+1}", f"HR={hr:.4f}, p={p:.6f}, 95%CI=[{ci_l:.4f}, {ci_h:.4f}]")
            return h + "</table>"
        except Exception as e:
            return f"<p style='color:red'>Error: {str(e)}</p>"

    def _run_probit(self, c1, c2):
        """Run Probit Regression."""
        if c1 is None or c2 is None:
            return "<b>Error:</b> Selecciona Predictora (V1) y Respuesta binaria (V2, 0/1)."
        if c1 not in self.data.columns or c2 not in self.data.columns:
            return "<b>Error:</b> Columnas no encontradas."
        try:
            X = self.data[c1].dropna().values.reshape(-1, 1)
            y = self.data[c2].dropna().values
            min_len = min(len(X), len(y))
            result = probit_regression(X[:min_len], y[:min_len])
            self._set_formula("Formula: Probit", "P(Y=1) = Φ(β₀ + β₁x)")
            h = self._h(f"{Icons.CHART} Probit Regression — {c1} → {c2}")
            h += "<table style='font-size:12px;'>"
            h += self._r("n", result['n'])
            h += self._r("Log-likelihood", f"{result['log_likelihood']:.4f}")
            h += self._r("AIC", f"{result['aic']:.4f}")
            for i, (coef, p) in enumerate(zip(result['coefficients'], result['p_values'])):
                h += self._r(f"β{i}", f"{coef:.4f}, p={p:.6f}")
            return h + "</table>"
        except Exception as e:
            return f"<p style='color:red'>Error: {str(e)}</p>"

    def _run_cmh(self):
        """Run CMH Test."""
        if self.data.shape[0] < 2 or self.data.shape[1] < 4:
            return "<b>Error:</b> Se necesitan al menos 2 filas y 4 columnas (2x2xK tablas)."
        try:
            tables = self.data.values.reshape(-1, 2, 2)
            result = cmh_test(tables)
            self._set_formula("Formula: CMH", "CMH = (Σ(a - n1m1/n))² / Σ(var)")
            h = self._h(f"{Icons.CHART} Cochran-Mantel-Haenszel")
            h += "<table style='font-size:12px;'>"
            h += self._r("CMH", f"{result['cmh_statistic']:.4f}")
            h += self._r("p", f"{result['p_value']:.6f}")
            h += self._r("OR común", f"{result['common_odds_ratio']:.4f}")
            h += self._r("95% CI OR", f"[{result['or_ci_low']:.4f}, {result['or_ci_high']:.4f}]")
            h += self._r("K tablas", result['K'])
            return h + "</table>" + self._ok(result['p_value'] < 0.05, "ASOCIACIÓN SIGNIFICATIVA", "SIN ASOCIACIÓN SIGNIFICATIVA")
        except Exception as e:
            return f"<p style='color:red'>Error: {str(e)}</p>"

    def _run_serial(self):
        """Run Serial Measurements Analysis."""
        if self.data.shape[1] < 3:
            return "<b>Error:</b> Se necesitan al menos 3 columnas (mediciones repetidas)."
        try:
            result = serial_measurements_summary(self.data.values)
            self._set_formula("Formula: Mediciones Seriales", "Resumen de medias, SD y pendientes por sujeto")
            h = self._h(f"{Icons.CHART} Mediciones Seriales")
            h += "<table style='font-size:12px;'>"
            h += self._r("Sujetos", result['n_subjects'])
            h += self._r("Mediciones", result['n_timepoints'])
            h += self._r("Pendiente media", f"{result['mean_slope']:.4f}")
            h += self._r("DE pendientes", f"{result['sd_slope']:.4f}")
            h += self._r("Pendiente global", f"{result['overall_slope']:.4f}")
            h += self._r("r global", f"{result['overall_r']:.4f}")
            h += self._r("p global", f"{result['overall_p']:.6f}")
            h += "</table>"
            h += "<b style='font-size:12px;'>Medias por tiempo:</b><table style='font-size:12px;'>"
            for i, (m, s) in enumerate(zip(result['means'], result['sds'])):
                h += self._r(f"T{i+1}", f"{m:.4f} ± {s:.4f}")
            return h + "</table>"
        except Exception as e:
            return f"<p style='color:red'>Error: {str(e)}</p>"

    def _run_youden(self, score_col, label_col):
        """Run Youden Plot."""
        if label_col is None or label_col == "(ninguna)" or label_col not in self.data.columns:
            return "<b>Error:</b> Selecciona Variable 3 (etiquetas 0/1)."
        if score_col is None or score_col not in self.data.columns:
            return "<b>Error:</b> Selecciona Variable 1 (scores)."
        try:
            y_true = self.data[label_col].dropna().values
            y_score = self.data[score_col].dropna().values
            n = min(len(y_true), len(y_score))
            result = youden_data(y_true[:n], y_score[:n])
            if result is None:
                return "<b>Error:</b> No se pudo calcular."
            
            self._set_formula("Formula: Youden's J", "J = Sensibilidad + Especificidad - 1")
            
            h = self._h(f"{Icons.CHART} Youden Plot — {score_col}")
            h += "<table style='font-size:12px;'>"
            h += self._r("Umbral óptimo", f"{result['optimal_threshold']:.4f}")
            h += self._r("J máximo", f"{result['optimal_j']:.4f}")
            h += self._r("Sensibilidad", f"{result['sensitivity'][result['optimal_idx']]:.4f}")
            h += self._r("Especificidad", f"{result['specificity'][result['optimal_idx']]:.4f}")
            h += "</table>"
            
            fig, ax = plt.subplots(figsize=(7, 5))
            ax.plot(result['thresholds'], result['sensitivity'], label='Sensibilidad', color='#4f6ef7', lw=2)
            ax.plot(result['thresholds'], result['specificity'], label='Especificidad', color='#22c55e', lw=2)
            ax.plot(result['thresholds'], result['j_statistic'], label="Youden's J", color='#f59e0b', lw=2, ls='--')
            ax.axvline(result['optimal_threshold'], color='#ef4444', ls=':', alpha=0.7, label=f'Óptimo ({result["optimal_threshold"]:.2f})')
            ax.set_xlabel('Umbral')
            ax.set_ylabel('Valor')
            ax.set_title("Gráfico de Youden", fontweight='bold')
            ax.legend(loc='lower left', framealpha=0.9)
            ax.set_xlim([result['thresholds'][-1], result['thresholds'][0]])
            ax.set_ylim([0, 1.1])
            fig.tight_layout()
            self._show_fig(fig)
            
            return h
        except Exception as e:
            return f"<p style='color:red'>Error: {str(e)}</p>"

    def _run_polar(self):
        """Run Polar Plot."""
        if self.data.shape[1] < 3:
            return "<b>Error:</b> Se necesitan al menos 3 columnas."
        try:
            categories = self.data.columns.tolist()[:min(8, self.data.shape[1])]
            values = [self.data[c].mean() for c in categories]
            result = polar_plot_data(categories, values)
            
            self._set_formula("Formula: Polar Plot", "Cada eje representa una variable")
            
            h = self._h(f"{Icons.CHART} Polar Plot")
            h += "<table style='font-size:12px;'>"
            for cat, val in zip(categories, values):
                h += self._r(cat, f"{val:.4f}")
            h += "</table>"
            
            fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
            ax.plot(result['angles'], result['values'], 'o-', linewidth=2, color='#4f6ef7')
            ax.fill(result['angles'], result['values'], alpha=0.25, color='#4f6ef7')
            ax.set_xticks(result['angles'][:-1])
            ax.set_xticklabels(categories)
            ax.set_title("Gráfico Polar", fontweight='bold', pad=20)
            fig.tight_layout()
            self._show_fig(fig)
            
            return h
        except Exception as e:
            return f"<p style='color:red'>Error: {str(e)}</p>"

    def _run_waterfall(self, col):
        """Run Waterfall Chart."""
        if col is None or col not in self.data.columns:
            return "<b>Error:</b> Selecciona una columna."
        try:
            values = self.data[col].dropna().values
            if len(values) < 2:
                return "<b>Error:</b> Se necesitan al menos 2 valores."
            
            result = waterfall_data(values)
            
            self._set_formula("Formula: Waterfall", "Muestra contribución acumulada de cada valor")
            
            h = self._h(f"{Icons.CHART} Waterfall Chart — {col}")
            h += "<table style='font-size:12px;'>"
            for label, val, cum in zip(result['labels'][:-1], result['values'][:-1], result['ends'][:-1]):
                h += self._r(label, f"{val:.4f} (acum: {cum:.4f})")
            h += self._r("Total", f"{result['values'][-1]:.4f}")
            h += "</table>"
            
            fig, ax = plt.subplots(figsize=(10, 5))
            x = range(len(result['labels']))
            colors = ['#22c55e' if p else '#ef4444' for p in result['is_positive']]
            
            for i, (start, end, color) in enumerate(zip(result['starts'], result['ends'], colors)):
                ax.bar(i, abs(end - start), bottom=min(start, end), color=color, edgecolor='white', width=0.6)
            
            ax.set_xticks(x)
            ax.set_xticklabels(result['labels'], rotation=45, ha='right')
            ax.set_ylabel('Valor')
            ax.set_title('Gráfico de Cascada', fontweight='bold')
            ax.axhline(y=0, color='black', linewidth=0.5)
            fig.tight_layout()
            self._show_fig(fig)
            
            return h
        except Exception as e:
            return f"<p style='color:red'>Error: {str(e)}</p>"

    def _run_mountain(self, col):
        """Run Mountain Plot."""
        if col is None or col not in self.data.columns:
            return "<b>Error:</b> Selecciona una columna."
        try:
            data = self.data[col].dropna().values
            result = mountain_plot_data(data)
            if result is None:
                return "<b>Error:</b> Se necesitan al menos 5 datos."
            
            self._set_formula("Formula: Mountain Plot", "Distribución plegada (folded normal)")
            
            h = self._h(f"{Icons.CHART} Mountain Plot — {col}")
            h += "<table style='font-size:12px;'>"
            h += self._r("n", result['n'])
            h += self._r("Media", f"{result['mean']:.4f}")
            h += self._r("DE", f"{result['sd']:.4f}")
            h += self._r("Mediana", f"{result['median']:.4f}")
            h += self._r("Q25-Q75", f"[{result['q25']:.4f}, {result['q75']:.4f}]")
            h += "</table>"
            
            fig, ax = plt.subplots(figsize=(7, 5))
            ax.bar(result['hist_x'], result['hist_y'], width=(result['hist_x'][1] - result['hist_x'][0]) * 0.8, 
                   alpha=0.6, color='#4f6ef7', label='Datos')
            ax.plot(result['x'], result['y_density'], color='#ef4444', lw=2, label='Normal ajustada')
            ax.axvline(result['mean'], color='#22c55e', ls='--', alpha=0.7, label=f'Media ({result["mean"]:.2f})')
            ax.axvline(result['median'], color='#f59e0b', ls=':', alpha=0.7, label=f'Mediana ({result["median"]:.2f})')
            ax.set_xlabel(col)
            ax.set_ylabel('Densidad')
            ax.set_title('Mountain Plot', fontweight='bold')
            ax.legend(loc='upper right', framealpha=0.9)
            fig.tight_layout()
            self._show_fig(fig)
            
            return h
        except Exception as e:
            return f"<p style='color:red'>Error: {str(e)}</p>"

    def _run_bland_multi(self):
        """Run Bland-Altman for multiple methods."""
        if self.data.shape[1] < 3:
            return "<b>Error:</b> Se necesitan al menos 3 columnas (múltiples métodos)."
        try:
            method_labels = self.data.columns.tolist()
            result = bland_altman_multiple(self.data, method_labels)
            
            self._set_formula("Formula: Bland-Altman Múltiple", "Sesgo = Media(diferencias)\nLoA = Sesgo ± 1.96 × DE(diferencias)")
            
            h = self._h(f"{Icons.CHART} Bland-Altman Múltiple")
            h += "<table style='font-size:12px;'>"
            h += self._r("Sujetos", result['n_subjects'])
            h += self._r("Métodos", result['n_methods'])
            h += self._r("Comparaciones", result['n_comparisons'])
            h += "</table>"
            
            for comp in result['comparisons']:
                h += f"<b style='font-size:12px;'>{comp['method1']} vs {comp['method2']}:</b>"
                h += "<table style='font-size:12px;'>"
                h += self._r("n", comp['n'])
                h += self._r("Sesgo", f"{comp['mean_diff']:.4f}")
                h += self._r("DE diferencias", f"{comp['sd_diff']:.4f}")
                h += self._r("LoA superior", f"{comp['loa_upper']:.4f}")
                h += self._r("LoA inferior", f"{comp['loa_lower']:.4f}")
                h += self._r("Sesgo %", f"{comp['bias_pct']:.2f}%")
                h += "</table>"
            
            return h
        except Exception as e:
            return f"<p style='color:red'>Error: {str(e)}</p>"
