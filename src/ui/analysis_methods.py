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


def _bins(valores, maximo=50):
    """Numero de barras seguro para un histograma.

    matplotlib revienta con "Too many bins for data range" cuando todos los
    valores son iguales (por ejemplo, el bootstrap de la correlacion de una
    columna consigo misma: siempre 1,0). Con rango cero, una sola barra.
    """
    import numpy as _np
    v = _np.asarray(valores, dtype=float)
    v = v[_np.isfinite(v)]
    if v.size == 0:
        return 1
    rango = float(_np.ptp(v))
    if rango == 0:
        return 1
    # numpy tambien falla cuando el rango existe pero es tan chico que el ancho
    # de barra no se puede representar en punto flotante (p.ej. remuestreos de
    # una correlacion de 0,9999999 que solo difieren en el ultimo bit).
    minimo_representable = float(_np.spacing(float(_np.max(_np.abs(v))))) * 4
    n = min(maximo, max(1, v.size))
    while n > 1 and rango / n <= minimo_representable:
        n //= 2
    return max(1, n)

def _fmt_p_html(p):
    """p para mostrar. Redondear a 4 decimales convierte 3e-9 en `0.0000`, que
    se lee como "p exactamente cero" — no existe tal cosa."""
    if p is None:
        return "n/d"
    p = float(p)
    if p != p:
        return "n/d"
    return "&lt;0.0001" if p < 0.0001 else f"{p:.4f}"


def _p_html(p):
    """El token entero: `p=0.0345` o `p&lt;0.0001`.

    Concatenar el `=` a mano dejaba `p=<0.0001`, con el igual y el menor
    pegados."""
    t = _fmt_p_html(p)
    return f"p{t}" if t.startswith("&lt;") else f"p={t}"


def _sin_resultado(res):
    """True si el core no pudo calcular: None, o dict de rechazo con motivo."""
    return res is None or (isinstance(res, dict) and res.get("error"))


def _msg_error(res, generico):
    """Mensaje de error para la UI.

    Prefiere el motivo especifico que devuelve el core (guards.py) sobre el
    texto generico. Un "No se pudo calcular" no le dice al usuario que arreglar;
    "Se necesitan al menos 3 pares de datos; hay 2" si.
    """
    if isinstance(res, dict) and res.get("error"):
        return f"<b>No se puede calcular:</b> {res['error']}"
    return f"<b>Error:</b> {generico}"
from html import escape

import pandas as pd

from src.core.roc import auc_delong
from src.core.sample_size import power_two_means
from src.ui.analysis_specs import parametros as spec_parametros
from src.core.survival import kaplan_meier, log_rank_test
from src.resultado.datos import filas_completas
from src.resultado.constructores import (
    bland_altman, bland_altman_multiple, cv_duplicados, deming, icc,
    passing_bablok as passing_bablok_resultado, precision_ep15, validar_metodo,
)
from src.resultado.constructores.anova import (
    ancova as ancova_resultado, anova_dos_vias, anova_una_via, medidas_repetidas,
)
from src.resultado.constructores.correlacion import parcial, pearson, spearman
from src.resultado.constructores.medias import (
    comparar_medias, f_varianzas, t_independiente, t_pareada, t_una_muestra,
)
from src.resultado.constructores.noparametricas import (
    cochran, friedman, kruskal, mann_whitney, signos, wilcoxon,
)
from src.resultado.constructores.tablas import (
    chi_cuadrado, cmh, dos_proporciones, fisher, mcnemar, odds_ratio_tabla,
    riesgo_relativo,
)
from src.resultado.constructores.regresion import (
    probit, regresion_lineal, regresion_logistica, regresion_multiple,
)
from src.resultado.constructores.resumen import (
    asimetria_curtosis, descriptivas, esd, grubbs, media_armonica, media_geometrica,
    media_recortada, percentiles, shapiro_wilk, tukey,
)
from src.resultado.lenguaje import texto_descartes
from src.resultado.modelo import Resultado
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
    f_test_variances, ttest_1sample, ttest_paired, ttest_ind,
    partial_correlation, anova_oneway, sign_test, cochran_q, pearson_r, spearman_rho,
)
from src.core.agreement import (
    cohens_kappa, cronbach_alpha, weighted_kappa,
)
from src.core.regression import linear_regression, multiple_regression, logistic_regression
from src.core.diagnostic_tests import (
    odds_ratio, relative_risk, diagnostic_test,
    likelihood_ratios, compare_two_means, compare_two_proportions, compare_two_auc
)
from src.core.reference import reference_interval, age_related_reference
from src.core.two_way_anova import two_way_anova
from src.core.ancova import ancova
from src.core.repeated_measures import repeated_measures_anova
from src.core.cox_regression import cox_regression
from src.core.probit import probit_regression
from src.core.cmh import cmh_test
from src.core.serial_measurements import serial_measurements_summary
from src.core.plots import youden_data, polar_plot_data, waterfall_data, mountain_plot_data
from src.core.validation import (
    validate_numeric_data, validate_paired_data, validate_groups,
    validate_binary_outcome, validate_positive_values, validate_range,
    validate_contingency_table, get_validation_summary
)

plt.rcParams.update({
    'figure.facecolor': 'white', 'axes.facecolor': '#fafbfd',
    'axes.edgecolor': '#d8dbe3', 'axes.grid': True,
    'grid.alpha': 0.25, 'grid.color': '#d8dbe3',
    'font.size': 11, 'axes.titlesize': 13,
})

from src.ui.help_text import ANALYSIS_HELP



class AnalysisMethodsMixin:
    """Métodos de cálculo+render de cada análisis (mixin de AnalysisPanel)."""

    # Filas incompletas que dejo afuera el ultimo `_filas_completas`. `_run` lo
    # pone en cero antes de cada analisis y lo informa despues.
    _descartadas = 0

    def _filas_completas(self, *cols):
        """Las filas con dato en TODAS las columnas pedidas, sin reindexar.

        Un analisis pareado compara cada fila consigo misma. El panel hacia
        `data[c1].dropna()` y `data[c2].dropna()` por separado y despues cortaba
        las dos al mismo largo: con una sola celda vacia, desde ahi cada valor
        se comparaba con el del paciente siguiente (un Bland-Altman de 20 pares
        con un hueco daba limites de +-90 en vez de +-2,4, sin aviso). Ver
        `tests/test_pares_alineados.py`.

        Deja en `self._descartadas` cuantas filas tenian dato en alguna de las
        columnas y no en todas. La regla vive en `src/resultado/datos.py`, que
        es lo que usan los analisis ya migrados a `Resultado`.
        """
        completas, entrada = filas_completas(self.data, *cols)
        self._descartadas = entrada.descartadas
        return completas

    def _nota_descartes(self, n):
        return ("<div style='margin-top:8px;padding:8px 10px;border-radius:6px;"
                "background:#fdf6ec;border-left:3px solid #d97706;font-size:12px;'>"
                f"{texto_descartes(n)}</div>")

    # ------------------------------------------------------------ entrada
    def _columnas_multi(self, excluir=()):
        """Columnas de un analisis que usa una lista (analysis_specs.MULTI).

        Devuelve (columnas, del_dialogo). Desde el dialogo, las tildadas; sin
        dialogo, todas las numericas de la hoja, y el informe las nombra para que
        se vea si se colo un ID o una edad. Antes se usaban todas en silencio
        (auditoria 2026-09, K2).
        """
        numericas = list(self.data.select_dtypes(include="number").columns)
        elegidas = getattr(self, "columnas_elegidas", None)
        if elegidas is not None:
            return [c for c in elegidas if c in numericas and c not in excluir], True
        return [c for c in numericas if c not in excluir], False

    def _nota_columnas(self, columnas, del_dialogo):
        lista = escape(", ".join(str(c) for c in columnas))
        if del_dialogo:
            return f"<p style='font-size:11px;color:#555;'>Columnas usadas: {lista}.</p>"
        return ("<p style='font-size:11px;color:#b45309;'>Se usaron <b>todas</b> las "
                f"columnas numéricas de la hoja: {lista}. Si alguna no corresponde (un "
                "número de muestra, una edad), abrí el análisis desde el menú "
                "<b>Estadísticas</b> y destildala.</p>")

    def _param(self, analisis, clave):
        """Parametro numerico: el del dialogo, o el de ejemplo si no hubo dialogo."""
        spec = {p.clave: p for p in spec_parametros(analisis)}[clave]
        crudo = (getattr(self, "parametros", None) or {}).get(clave)
        if crudo is None or str(crudo).strip() == "":
            return spec.defecto          # None en los opcionales: «no se declaró»
        try:
            valor = float(str(crudo).strip().replace(",", "."))
        except ValueError:
            raise ValueError(f"«{spec.etiqueta}» tiene que ser un número; se escribió «{crudo}».")
        if not spec.minimo <= valor <= spec.maximo:
            raise ValueError(f"«{spec.etiqueta}» = {valor:g} está fuera de rango "
                             f"({spec.minimo:g} a {spec.maximo:g}).")
        return int(round(valor)) if spec.entero else valor

    def _nota_parametros(self):
        if getattr(self, "parametros", None):
            return ""
        return ("<p style='font-size:11px;color:#b45309;'>Son los valores de ejemplo. Para "
                "calcular con los tuyos, abrí este análisis desde el menú "
                "<b>Estadísticas</b>: el diálogo los pide.</p>")

    def _avisos_html(self, avisos):
        return "".join(f"<p style='font-size:11px;color:#b45309;'>{a}</p>" for a in avisos if a)

    _POSITIVOS = {"1", "1.0", "si", "sí", "s", "positivo", "positiva", "pos", "+", "yes",
                  "y", "true", "verdadero", "reactivo", "detectado", "presente", "enfermo",
                  "expuesto", "evento", "anormal", "caso"}

    def _niveles_binarios(self, serie, nombre):
        """(positivo, negativo, aviso) de una variable con dos valores, o (None, None, motivo)."""
        valores = list(pd.unique(serie))
        if len(valores) != 2:
            return None, None, (f"«{escape(str(nombre))}» tiene {len(valores)} valor(es) "
                                "distinto(s); para una tabla 2×2 hacen falta exactamente 2 "
                                "(por ejemplo 0/1).")
        if all(isinstance(v, (int, float, np.integer, np.floating)) for v in valores):
            bajo, alto = sorted(valores, key=float)
            if (float(bajo), float(alto)) == (0.0, 1.0):
                return alto, bajo, ""
            return alto, bajo, (f"«{escape(str(nombre))}» no está codificada 0/1: se tomó "
                                f"{float(alto):g} como positivo y {float(bajo):g} como "
                                "negativo. Si es al revés, recodificá a 0/1.")
        texto = [str(v).strip().lower() for v in valores]
        es_pos = [i for i, t in enumerate(texto) if t in self._POSITIVOS]
        if len(es_pos) == 1:
            i = es_pos[0]
            return valores[i], valores[1 - i], ""
        pos, neg = sorted(valores, key=str)
        return pos, neg, (f"No se reconoce cuál valor de «{escape(str(nombre))}» es el "
                          f"positivo: se tomó «{escape(str(pos))}». Si es al revés, "
                          "recodificá a 0/1.")

    def _tabla_2x2(self, c1, c2):
        """Tabla 2×2 a partir de las variables elegidas.

        Lo normal: dos columnas de datos crudos, una fila por sujeto. Si la
        seleccion tiene exactamente 2 filas de conteos enteros que no son todos
        0/1, se lee como tabla ya armada, y el informe dice cual de las dos
        lecturas uso. Antes Fisher, McNemar, OR, RR y la prueba diagnostica
        tomaban SIEMPRE las dos primeras filas de la hoja como conteos: sobre
        datos crudos, Fisher daba p = 1 donde el real es p < 0,000001
        (auditoria 2026-09, K3).

        Returns: (a, b, c, d, filas, columnas, lectura, avisos) o str (HTML de error).
        """
        for c in (c1, c2):
            if c is None or c not in self.data.columns:
                return f"<b>Error:</b> la columna «{escape(str(c))}» no está en la hoja."
        if c1 == c2:
            return "<b>Error:</b> Variable 1 y Variable 2 son la misma columna."
        pares = self._filas_completas(c1, c2)
        v1, v2 = pares[c1], pares[c2]
        if len(pares) == 2:
            try:
                cuentas = np.array([[float(v1.iloc[0]), float(v2.iloc[0])],
                                    [float(v1.iloc[1]), float(v2.iloc[1])]])
            except (TypeError, ValueError):
                cuentas = None
            if (cuentas is not None and np.all(cuentas >= 0)
                    and np.allclose(cuentas, np.round(cuentas))
                    and not set(cuentas.ravel()) <= {0.0, 1.0}):
                a, b, c, d = (int(x) for x in cuentas.ravel())
                return (a, b, c, d, ("fila 1", "fila 2"),
                        (escape(str(c1)), escape(str(c2))),
                        (f"Se leyó como <b>tabla de conteos ya armada</b> (2 filas): "
                         f"[{a}, {b}] / [{c}, {d}]."), [])
        pos1, neg1, av1 = self._niveles_binarios(v1, c1)
        if pos1 is None:
            return f"<b>Error:</b> {av1}"
        pos2, neg2, av2 = self._niveles_binarios(v2, c2)
        if pos2 is None:
            return f"<b>Error:</b> {av2}"
        a = int(np.sum((v1 == pos1) & (v2 == pos2)))
        b = int(np.sum((v1 == pos1) & (v2 == neg2)))
        c = int(np.sum((v1 == neg1) & (v2 == pos2)))
        d = int(np.sum((v1 == neg1) & (v2 == neg2)))
        n1, n2 = escape(str(c1)), escape(str(c2))
        lectura = (f"Tabla armada con {len(pares)} filas, una por sujeto: filas = «{n1}» "
                   f"({escape(str(pos1))} / {escape(str(neg1))}), columnas = «{n2}» "
                   f"({escape(str(pos2))} / {escape(str(neg2))}).")
        return (a, b, c, d, (f"{n1} = {escape(str(pos1))}", f"{n1} = {escape(str(neg1))}"),
                (f"{n2} = {escape(str(pos2))}", f"{n2} = {escape(str(neg2))}"),
                lectura, [x for x in (av1, av2) if x])

    def _html_tabla_2x2(self, a, b, c, d, filas, columnas):
        celda = "padding:2px 10px;text-align:center;"
        return ("<table style='font-size:12px;border-collapse:collapse;margin:4px 0;'>"
                f"<tr><td></td><td style='{celda}'><b>{columnas[0]}</b></td>"
                f"<td style='{celda}'><b>{columnas[1]}</b></td></tr>"
                f"<tr><td><b>{filas[0]}</b></td><td style='{celda}'>{a}</td>"
                f"<td style='{celda}'>{b}</td></tr>"
                f"<tr><td><b>{filas[1]}</b></td><td style='{celda}'>{c}</td>"
                f"<td style='{celda}'>{d}</td></tr></table>")

    def _tabla_rxc(self, c1, c2, max_niveles=10):
        """Tabla de contingencia r×c de las dos variables elegidas (datos crudos)."""
        for c in (c1, c2):
            if c is None or c not in self.data.columns:
                return f"<b>Error:</b> la columna «{escape(str(c))}» no está en la hoja."
        if c1 == c2:
            return "<b>Error:</b> Variable 1 y Variable 2 son la misma columna."
        pares = self._filas_completas(c1, c2)
        tabla = pd.crosstab(pares[c1], pares[c2])
        if tabla.shape[0] > max_niveles or tabla.shape[1] > max_niveles:
            return (f"<b>Error:</b> «{escape(str(c1))}» tiene {tabla.shape[0]} categorías y "
                    f"«{escape(str(c2))}» {tabla.shape[1]}: esta prueba es para variables "
                    f"categóricas (hasta {max_niveles} categorías cada una).")
        if tabla.shape[0] < 2 or tabla.shape[1] < 2:
            return "<b>Error:</b> cada variable necesita al menos 2 categorías con datos."
        return tabla

    def _html_tabla_rxc(self, tabla):
        celda = "padding:2px 8px;text-align:center;"
        h = "<table style='font-size:12px;border-collapse:collapse;margin:4px 0;'><tr><td></td>"
        h += "".join(f"<td style='{celda}'><b>{escape(str(c))}</b></td>" for c in tabla.columns)
        h += "</tr>"
        for idx, fila in tabla.iterrows():
            h += f"<tr><td><b>{escape(str(idx))}</b></td>"
            h += "".join(f"<td style='{celda}'>{int(v)}</td>" for v in fila.values)
            h += "</tr>"
        return h + "</table>"

    def _grupos_largo(self, c1, c2):
        """Grupos en formato largo: c1 = respuesta numerica, c2 = grupo.

        Returns: (etiquetas, [arrays], lectura) o str (HTML de error).
        """
        for c in (c1, c2):
            if c is None or c not in self.data.columns:
                return f"<b>Error:</b> la columna «{escape(str(c))}» no está en la hoja."
        if c1 == c2:
            return "<b>Error:</b> Variable 1 (respuesta) y Variable 2 (grupo) son la misma columna."
        pares = self._filas_completas(c1, c2)
        y = pd.to_numeric(pares[c1], errors="coerce")
        if y.isna().any():
            return f"<b>Error:</b> «{escape(str(c1))}» (la respuesta) tiene valores no numéricos."
        grupos = [(str(k), g.to_numpy(dtype=float)) for k, g in y.groupby(pares[c2])]
        k, n = len(grupos), len(pares)
        if k < 2:
            return f"<b>Error:</b> «{escape(str(c2))}» (el grupo) tiene un solo valor."
        if k > 20 or k > n / 2:
            return (f"<b>Error:</b> «{escape(str(c2))}» tiene {k} valores distintos para {n} "
                    "filas: parece una medición, no un código de grupo. La Variable 1 es la "
                    "respuesta y la Variable 2 el grupo (por ejemplo 1, 2, 3 o A, B, C).")
        return [g[0] for g in grupos], [g[1] for g in grupos]

    def _html_grupos(self, etiquetas, datos):
        h = ("<table style='font-size:12px;'><tr><td><b>Grupo</b></td><td><b>n</b></td>"
             "<td><b>Media</b></td><td><b>DE</b></td><td><b>Mediana</b></td></tr>")
        for e, g in zip(etiquetas, datos):
            de = f"{np.std(g, ddof=1):.4f}" if len(g) > 1 else "—"
            h += (f"<tr><td>{escape(e)}</td><td>{len(g)}</td><td>{np.mean(g):.4f}</td>"
                  f"<td>{de}</td><td>{np.median(g):.4f}</td></tr>")
        return h + "</table>"

    # --- Resumen y distribucion: los arma src/resultado/constructores/resumen.py ---
    def _desc(self, col):
        return descriptivas(self.data, col)

    def _geo_mean(self, col):
        return media_geometrica(self.data, col)

    def _harm_mean(self, col):
        return media_armonica(self.data, col)

    def _percentiles(self, col):
        return percentiles(self.data, col)

    def _esd(self, col):
        return esd(self.data, col)

    # --- t-test pareado ---
    # --- Comparacion de medias: la arma src/resultado/constructores/medias.py ---
    def _t_paired(self, c1, c2, a):
        return t_pareada(self.data, c1, c2, {"alpha": a})

    def _t_una(self, c1):
        try:
            mu = self._param("t-test 1 muestra", "mu")
        except ValueError as e:
            return f"<b>Error:</b> {e}"
        return t_una_muestra(self.data, c1, {"mu": mu})

    def _comparar_medias(self):
        try:
            opciones = {k: self._param("Comparar 2 medias", k)
                        for k in ("m1", "de1", "n1", "m2", "de2", "n2")}
        except ValueError as e:
            return f"<b>Error:</b> {e}"
        res = comparar_medias(opciones)
        if res.ok and not getattr(self, "parametros", None):
            res.advertencias.append("Son los valores de ejemplo. Para calcular con los "
                                    "tuyos, abrí el análisis desde el menú Estadísticas.")
        return res

    # --- t-test independiente ---
    def _t_ind(self, c1, c2, a):
        return t_independiente(self.data, c1, c2, {"alpha": a})

    # --- ANOVA ---
    # --- ANOVA: la arma src/resultado/constructores/anova.py ---
    def _anova(self, c1, c2, a):
        """Variable 1 = respuesta, Variable 2 = grupo (formato largo)."""
        return anova_una_via(self.data, c1, c2, {"alpha": a})

    # --- Correlacion: la arma src/resultado/constructores/correlacion.py ---
    def _corr_p(self, c1, c2):
        return pearson(self.data, c1, c2)

    def _corr_s(self, c1, c2):
        return spearman(self.data, c1, c2)

    # --- Shapiro-Wilk ---
    def _shapiro(self, col):
        return shapiro_wilk(self.data, col)

    # --- Curva ROC ---
    def _roc(self, score_col, label_col):
        if label_col == "(ninguna)" or label_col not in self.data.columns:
            return f"<b>Error:</b> Selecciona la columna de etiquetas en Variable 3 (0=negativo, 1=positivo)."
        if score_col not in self.data.columns:
            return f"<b>Error:</b> '{score_col}' no encontrada."

        pares = self._filas_completas(score_col, label_col)
        y_true, y_score = pares[label_col].values, pares[score_col].values
        n = len(pares)

        unique = np.unique(y_true)
        if not all(u in [0, 1] for u in unique):
            return f"<b>Error:</b> Variable 3 debe contener solo 0 y 1. Valores encontrados: {unique.tolist()}"
        if len(unique) < 2:
            return ("<b>Error:</b> La etiqueta tiene una sola clase "
                    f"(todos {int(unique[0])}). Una curva ROC compara enfermos "
                    "contra sanos: hacen falta los dos grupos.")

        fpr, tpr, thresh = roc_curve(y_true, y_score)
        a = auc(fpr, tpr)
        opt_t, youden, sens, fpr_opt = optimal_threshold(fpr, tpr, thresh)
        spec_opt = 1 - fpr_opt
        stats_diag = diagnostic_stats(y_true, y_score, opt_t)
        dl = auc_delong(y_true, y_score)
        self._set_formula("Formula: Curva ROC",
                          "AUC = área bajo la curva (trapecios, con los empates agrupados)\n"
                          "EE del AUC: DeLong, DeLong y Clarke-Pearson (1988); IC 95% = AUC ± 1,96·EE\n"
                          "Umbral óptimo: máximo índice de Youden, J = Sens + Espec − 1")

        h = self._h(f" Curva ROC — {escape(str(score_col))}")
        h += "<table style='font-size:12px;'>"
        filas = [("Variable (score)", escape(str(score_col))),
                 ("Variable (etiqueta)", escape(str(label_col))),
                 ("Observaciones", n), ("AUC", f"{a:.4f}")]
        if not _sin_resultado(dl):
            filas += [("EE (DeLong)", f"{dl['se']:.4f}"),
                      ("IC 95% del AUC", f"{dl['ci'][0]:.4f} a {dl['ci'][1]:.4f}")]
        filas += [("Umbral optimo", f"{opt_t:.4f}"), ("Sensibilidad", f"{sens:.4f}"),
                  ("Especificidad", f"{spec_opt:.4f}"), ("Indice de Youden", f"{youden:.4f}")]
        for l, v in filas:
            h += self._r(l, v)
        h += "</table>"

        if a < 0.5:
            # Un AUC de 0,06 no es una prueba "pobre": discrimina casi perfecto,
            # pero al reves. Llamarla pobre esconde que la etiqueta o el sentido
            # de la prueba estan invertidos (auditoria 2026-09, A9).
            h += ("<div style='margin-top:8px;padding:8px;border-radius:6px;background:#fdf6ec;"
                  "border-left:3px solid #d97706;font-size:12px;'><b>La curva sale invertida "
                  f"(AUC = {a:.3f} &lt; 0,5).</b> En estos datos los valores ALTOS corresponden "
                  f"a los negativos: leída al revés, el AUC sería {1 - a:.3f}. Revisá si 1 es de "
                  "verdad el enfermo en la etiqueta, o si la prueba baja con la enfermedad.</div>")
        else:
            if a >= 0.9:
                grade = "excelente"
            elif a >= 0.8:
                grade = "buena"
            elif a >= 0.7:
                grade = "aceptable"
            elif a >= 0.6:
                grade = "regular"
            else:
                grade = "pobre"
            h += (f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#eef2ff;"
                  f"font-size:12px;'> <b>Interpretación:</b> AUC = {a:.3f}, discriminación {grade}. "
                  "AUC = 1 es perfecta; 0,5, lo mismo que tirar una moneda. Mirá el IC: con "
                  "pocos casos puede ir de pobre a excelente.</div>")

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
    def _bland(self, c1, c2, opciones=None):
        """Bland-Altman + CCC. Lo arma `src/resultado/constructores/comparacion.py`:
        es el primer analisis migrado a `Resultado`."""
        return bland_altman(self.data, c1, c2, opciones)

    # --- Comparación de métodos: la familia de validación, migrada ---
    # Los arma src/resultado/constructores/comparacion.py. El veredicto de
    # Passing-Bablok ya no usa el «10 % de la media» (no sale de ninguna norma):
    # decide por los intervalos, y un intervalo ancho no concluye.
    def _passing(self, c1, c2):
        return passing_bablok_resultado(self.data, c1, c2)

    def _deming(self, c1, c2):
        opciones = dict(getattr(self, "opciones_metodo", None) or {})
        try:
            opciones["lambda"] = self._param("Deming regression", "lambda")
        except ValueError as e:
            return f"<b>Error:</b> {e}"
        return deming(self.data, c1, c2, opciones)

    def _cv_dup(self, c1, c2):
        return cv_duplicados(self.data, c1, c2)

    # --- Kaplan-Meier ---
    def _kaplan_meier(self, time_col, event_col):
        if time_col not in self.data.columns or event_col not in self.data.columns:
            return "<b>Error:</b> Selecciona columna de tiempo y de evento (1=event, 0=censura)."
        pares = self._filas_completas(time_col, event_col)
        t, e = pares[time_col], pares[event_col]
        if len(pares) < 5:
            return "<b>Error:</b> Minimo 5 observaciones."

        km = kaplan_meier(t.values, e.values.astype(int))
        if _sin_resultado(km):
            return _msg_error(km, "No se pudo calcular.")

        h = self._h(f" Kaplan-Meier — {time_col}")
        h += "<table style='font-size:12px;'>"
        for l, v in [("n total", km["n_total"]), ("Eventos", km["n_events"]),
                      ("Censurados", km["n_censored"]),
                      ("Supervivencia media", f"{np.mean(km['survival']):.4f}")]:
            h += self._r(l, v)
        if km["median_survival"] is not None:
            h += self._r("Supervivencia mediana", f"{km['median_survival']:.2f}")
        h += "</table>"
        h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#eef2ff;font-size:12px;'> <b>Interpretacion:</b> La curva muestra la probabilidad de supervivencia en cada tiempo. La mediana es el tiempo donde el 50% sobrevive.</div>"

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
        if _sin_resultado(lr):
            return _msg_error(lr, "No se pudo calcular.")

        km1 = kaplan_meier(t1.values, e1.values.astype(int))
        km2 = kaplan_meier(t2.values, e2.values.astype(int))

        h = self._h(f" Log-rank Test")
        h += "<table style='font-size:12px;'>"
        for l, v in [("Grupo 1", f"{groups[0]} (n={len(t1)})"),
                      ("Grupo 2", f"{groups[1]} (n={len(t2)})"),
                      ("Chi-cuadrado", f"{lr['chi2']:.4f}"),
                      ("Valor p", f"{lr['p']:.6f}"),
                      ("Observado (G1)", lr["observed"]),
                      ("Esperado (G1)", f"{lr['expected']:.2f}")]:
            h += self._r(l, v)
        h += "</table>"
        h += self._ok(lr['p'] < 0.05, "Se detectó diferencia entre las curvas", "No se detectó diferencia entre las curvas")

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
        pares = self._filas_completas(effect_col, se_col)
        eff, se = pares[effect_col].values, pares[se_col].values
        n = len(pares)
        if n < 2:
            return "<b>Error:</b> Minimo 2 estudios."

        result = meta_analysis(eff, se)
        if _sin_resultado(result):
            return _msg_error(result, "No se pudo calcular.")

        h = self._h(f" Meta-analisis")
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
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#ecfdf5;border-left:3px solid #22c55e;'><b style='color:#16a34a;'> Baja heterogeneidad (I2={result['i2']:.0f}%)</b></div>"
        elif result['i2'] < 75:
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#fef9ee;border-left:3px solid #f59e0b;'><b style='color:#d97706;'> Heterogeneidad moderada (I2={result['i2']:.0f}%)</b></div>"
        else:
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#fef2f2;border-left:3px solid #ef4444;'><b style='color:#dc2626;'> Heterogeneidad alta (I2={result['i2']:.0f}%)</b></div>"

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
        """Tamaño muestral para comparar una media con un valor de referencia."""
        nombre = "Tamano muestral (1 media)"
        try:
            delta, sd = self._param(nombre, "delta"), self._param(nombre, "sd")
            alfa, poder = self._param(nombre, "alpha"), self._param(nombre, "poder")
        except ValueError as e:
            return f"<b>Error:</b> {e}"
        r = sample_size_mean(delta, sd, alfa, poder)
        if _sin_resultado(r):
            return _msg_error(r, "La diferencia a detectar no puede ser 0.")
        self._set_formula("Formula: Tamaño muestral — 1 media",
                          "El n más chico cuyo poder EXACTO llega al pedido:\n"
                          "poder = P(|T| > t crítico), T ~ t no central(gl = n−1, λ = (Δ/DE)·√n)")
        h = self._h(" Tamaño Muestral — 1 media")
        h += "<table style='font-size:12px;'>"
        for l, v in [("Diferencia a detectar (Δ)", f"{delta:g}"), ("DE esperada", f"{sd:g}"),
                     ("Alfa (dos colas)", f"{alfa:g}"), ("Poder buscado", f"{poder:g}"),
                     ("Tamaño del efecto (Δ/DE)", f"{r['effect_size']:.3f}"),
                     ("n necesario", f"<b>{r['n_per_group']}</b>"),
                     ("Poder real con ese n", f"{r['power_real']:.3f}")]:
            h += self._r(l, v)
        return h + "</table>" + self._nota_parametros()

    # --- Tamano muestral (2 medias) ---
    def _ss_two_means(self):
        """Tamaño muestral para comparar dos medias independientes."""
        nombre = "Tamano muestral (2 medias)"
        try:
            delta, sd = self._param(nombre, "delta"), self._param(nombre, "sd")
            ratio = self._param(nombre, "ratio")
            alfa, poder = self._param(nombre, "alpha"), self._param(nombre, "poder")
        except ValueError as e:
            return f"<b>Error:</b> {e}"
        r = sample_size_two_means(delta, sd, alfa, poder, ratio)
        if _sin_resultado(r):
            return _msg_error(r, "La diferencia a detectar no puede ser 0.")
        self._set_formula("Formula: Tamaño muestral — 2 medias",
                          "El n1 más chico cuyo poder EXACTO llega al pedido, con n2 = ratio·n1:\n"
                          "T ~ t no central(gl = n1+n2−2, λ = (Δ/DE)/√(1/n1 + 1/n2))")
        h = self._h(" Tamaño Muestral — 2 medias")
        h += "<table style='font-size:12px;'>"
        for l, v in [("Diferencia a detectar (Δ)", f"{delta:g}"), ("DE común", f"{sd:g}"),
                     ("Razón n2/n1", f"{ratio:g}"), ("Alfa (dos colas)", f"{alfa:g}"),
                     ("Poder buscado", f"{poder:g}"),
                     ("n grupo 1", f"<b>{r['n_group1']}</b>"), ("n grupo 2", f"<b>{r['n_group2']}</b>"),
                     ("n total", r['n_total'])]:
            h += self._r(l, v)
        return h + "</table>" + self._nota_parametros()

    # --- Tamano muestral (2 proporciones) ---
    def _ss_prop(self):
        """Tamaño muestral para comparar dos proporciones."""
        nombre = "Tamano muestral (2 proporciones)"
        try:
            p1, p2 = self._param(nombre, "p1"), self._param(nombre, "p2")
            alfa, poder = self._param(nombre, "alpha"), self._param(nombre, "poder")
        except ValueError as e:
            return f"<b>Error:</b> {e}"
        r = sample_size_proportions(p1, p2, alfa, poder)
        if _sin_resultado(r):
            return _msg_error(r, "Las dos proporciones no pueden ser iguales.")
        self._set_formula("Formula: Tamaño muestral — 2 proporciones",
                          "n por grupo = [z(α/2)·√(2·p̄·q̄) + z(β)·√(p1q1 + p2q2)]² / (p1 − p2)²\n"
                          "(Fleiss, sin corrección de continuidad)")
        h = self._h(" Tamaño Muestral — 2 proporciones")
        h += "<table style='font-size:12px;'>"
        for l, v in [("p1", f"{p1:g}"), ("p2", f"{p2:g}"), ("Alfa (dos colas)", f"{alfa:g}"),
                     ("Poder buscado", f"{poder:g}"),
                     ("n por grupo", f"<b>{r['n_per_group']}</b>"), ("n total", r['n_total'])]:
            h += self._r(l, v)
        return h + "</table>" + self._nota_parametros()

    # --- Poder estadistico ---
    def _power(self):
        """Poder de una prueba t, para una muestra/pareada o dos grupos."""
        nombre = "Poder estadistico"
        try:
            n, delta = self._param(nombre, "n"), self._param(nombre, "delta")
            sd, alfa = self._param(nombre, "sd"), self._param(nombre, "alpha")
        except ValueError as e:
            return f"<b>Error:</b> {e}"
        dos = (self.opciones_metodo or {}).get("diseno") == "dos"
        r = power_two_means(n, delta, sd, alfa) if dos else power_analysis(n, delta, sd, alfa)
        if _sin_resultado(r):
            return _msg_error(r, "No se pudo calcular.")
        self._set_formula("Formula: Poder de la prueba t",
                          "poder = P(|T| > t crítico) con T ~ t no central\n"
                          + ("gl = 2n − 2, λ = (Δ/DE)·√(n/2)" if dos else "gl = n − 1, λ = (Δ/DE)·√n"))
        h = self._h(" Poder Estadístico — " + ("dos grupos independientes" if dos
                                               else "una muestra o datos pareados"))
        h += "<table style='font-size:12px;'>"
        for l, v in [("n" + (" por grupo" if dos else ""), n), ("Diferencia (Δ)", f"{delta:g}"),
                     ("DE", f"{sd:g}"), ("Alfa (dos colas)", f"{alfa:g}"),
                     ("Tamaño del efecto (Δ/DE)", f"{r['effect_size']:.3f}"),
                     ("Poder", f"<b>{r['power']:.1%}</b>")]:
            h += self._r(l, v)
        return h + "</table>" + self._nota_parametros()

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
        if _sin_resultado(result):
            return _msg_error(result, "No se pudo calcular.")

        h = self._h(f" Bootstrap — Media de {col}")
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
        h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#eef2ff;font-size:12px;'> Bootstrap no asume distribucion normal. El IC se obtiene directamente de la distribucion de medias remuestreadas.</div>"

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
        ax1.hist(d.values, bins=_bins(d.values, 30), edgecolor='white', alpha=0.7, color='#4f6ef7')
        ax1.axvline(result['original_mean'], color='#ef4444', ls='--', lw=2, label=f'Media={result["original_mean"]:.2f}')
        ax1.set_title('Datos originales', fontweight='bold')
        ax1.legend(framealpha=0.9)

        ax2.hist(result['bootstrap_distribution'], bins=_bins(result['bootstrap_distribution']), edgecolor='white', alpha=0.7, color='#22c55e')
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
        if _sin_resultado(result):
            return _msg_error(result, "No se pudo calcular.")

        h = self._h(f" Bootstrap — Diferencia {c1} - {c2}")
        h += "<table style='font-size:12px;'>"
        for l, v in [("Diferencia original", f"{result['original_diff']:.4f}"),
                      ("Diferencia bootstrap", f"{result['bootstrap_diff']:.4f}"),
                      ("SE bootstrap", f"{result['bootstrap_se']:.6f}"),
                      ("IC 95%", f"[{result['ci_lower']:.4f}, {result['ci_upper']:.4f}]")]:
            h += self._r(l, v)
        h += "</table>"

        includes_zero = result['ci_lower'] <= 0 <= result['ci_upper']
        if includes_zero:
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#fef9ee;border-left:3px solid #f59e0b;'><b style='color:#d97706;'> El IC incluye el 0: no se detectó diferencia</b><br><span style='font-size:11px;'>No detectarla no prueba que no exista.</span></div>"
        else:
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#ecfdf5;border-left:3px solid #22c55e;'><b style='color:#16a34a;'> El IC no incluye el 0: se detectó diferencia</b></div>"

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(result['bootstrap_distribution'], bins=_bins(result['bootstrap_distribution']), edgecolor='white', alpha=0.7, color='#4f6ef7')
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
        pares = self._filas_completas(c1, c2)
        d1, d2 = pares[c1], pares[c2]
        n = len(pares)
        if n < 5:
            return "<b>Error:</b> Minimo 5 pares."

        self._set_formula(
            "Formula: Bootstrap IC para Correlacion",
            "1. Remuestrear pares (xi, yi) con reemplazo\n2. Calcular r de cada remuestreo\n3. IC = [P(2.5%), P(97.5%)] de las B correlaciones",
            f"n = {n}\nB = 10000 remuestreos\nMetodo = Pearson"
        )

        result = bootstrap_correlation(d1.values, d2.values)
        if _sin_resultado(result):
            return _msg_error(result, "No se pudo calcular.")

        h = self._h(f" Bootstrap — Correlacion")
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
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#fef9ee;border-left:3px solid #f59e0b;'><b style='color:#d97706;'> El IC incluye el 0: no se detectó correlación</b><br><span style='font-size:11px;'>No detectarla no prueba que no exista.</span></div>"
        else:
            h += f"<div style='margin-top:8px;padding:8px;border-radius:6px;background:#ecfdf5;border-left:3px solid #22c55e;'><b style='color:#16a34a;'> El IC no incluye el 0: se detectó correlación</b></div>"

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(result['bootstrap_distribution'], bins=_bins(result['bootstrap_distribution']), edgecolor='white', alpha=0.7, color='#8b5cf6')
        ax.axvline(result['ci_lower'], color='#ef4444', ls='--', lw=1.5)
        ax.axvline(result['ci_upper'], color='#ef4444', ls='--', lw=1.5)
        ax.axvline(0, color='#d1d5e0', ls='--', lw=1.5, label='0')
        ax.set_title('Bootstrap: Correlacion', fontweight='bold')
        ax.legend()
        fig.tight_layout()
        self._show_fig(fig)

        return h

    # --- Random Forest (clasificacion) ---
    def _rf_class(self, target_col):
        """Random Forest (clasificación): Variable 1 = clase; predictoras = las tildadas."""
        if target_col not in self.data.columns:
            return f"<b>Error:</b> '{escape(str(target_col))}' no encontrada."
        nums, del_dialogo = self._columnas_multi(excluir=(target_col,))
        if len(nums) < 1:
            return "<b>Error:</b> Se necesita al menos 1 predictora numérica."
        filas = self._filas_completas(target_col, *nums)
        X, y = filas[nums].values, filas[target_col].values
        if len(np.unique(y)) < 2:
            return "<b>Error:</b> La clase tiene que tener al menos 2 valores."
        if not np.all(y == y.astype(int)) or len(np.unique(y)) > 20:
            return ("<b>Error:</b> La clase tiene que ser categórica (pocas clases discretas, "
                    "ej. 0/1). Para una variable continua usá <b>Random Forest (regresión)</b>.")
        self._set_formula(
            "Formula: Random Forest (Clasificacion)",
            "1. Cada árbol: remuestreo con reemplazo; en cada nodo, √p predictoras al azar; corte por Gini\n"
            "2. Clase = voto mayoritario de 100 árboles\n"
            "3. Desempeño: exactitud por validación cruzada estratificada (k particiones)",
            f"Predictoras: {', '.join(str(c) for c in nums[:5])}\nClase: {target_col}")
        rf = RandomForestClassifier(n_trees=100, max_depth=8, random_state=42)
        rf.fit(X, y)
        cv = rf.validacion_cruzada(X, y)
        importances = rf.get_feature_importance()
        h = self._h(" Random Forest — Clasificación")
        h += "<table style='font-size:12px;'>"
        h += self._r("Clase", escape(str(target_col)))
        h += self._r("Observaciones", len(y))
        h += self._r("Clases", len(np.unique(y)))
        if _sin_resultado(cv):
            h += self._r("Exactitud por validación cruzada", cv.get("error", "—"))
        else:
            h += self._r(f"Exactitud por validación cruzada (k={cv['k']})",
                         f"{cv['media']:.4f} ± {cv['de']:.4f}")
        h += self._r("Exactitud sobre los datos de entrenamiento (optimista)", f"{rf.score(X, y):.4f}")
        h += "</table>"
        h += ("<p style='font-size:11px;color:#555;'>La exactitud que vale es la de validación "
              "cruzada: la de entrenamiento mide al modelo sobre los mismos casos con que se "
              "ajustó y con ruido puro da cerca de 1.</p>")
        h += "<b style='font-size:12px;'>Importancia de Variables:</b><table style='font-size:12px;'>"
        sorted_idx = np.argsort(importances)[::-1]
        for i in sorted_idx[:8]:
            bar = "█" * int(importances[i] * 50)
            h += self._r(escape(str(nums[i])), f"{importances[i]:.4f} {bar}")
        h += "</table>" + self._nota_columnas(nums, del_dialogo)

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
    def _rf_regress(self, target_col):
        """Random Forest (regresión): Variable 1 = respuesta; predictoras = las tildadas."""
        if target_col not in self.data.columns:
            return f"<b>Error:</b> '{escape(str(target_col))}' no encontrada."
        nums, del_dialogo = self._columnas_multi(excluir=(target_col,))
        if len(nums) < 1:
            return "<b>Error:</b> Se necesita al menos 1 predictora numérica."
        filas = self._filas_completas(target_col, *nums)
        X, y = filas[nums].values, filas[target_col].values
        if len(y) < 10:
            return "<b>Error:</b> Minimo 10 observaciones."
        self._set_formula(
            "Formula: Random Forest (Regresion)",
            "1. Cada árbol: remuestreo con reemplazo; corte que minimiza la varianza\n"
            "2. Predicción = promedio de 100 árboles\n"
            "3. Desempeño: R² por validación cruzada (k particiones)",
            f"Predictoras: {', '.join(str(c) for c in nums[:5])}\nRespuesta: {target_col}\nn = {len(y)}")
        rf = RandomForestRegressor(n_trees=100, max_depth=8, random_state=42)
        rf.fit(X, y)
        cv = rf.validacion_cruzada(X, y)
        r2_train = rf.score(X, y)
        y_pred = rf.predict(X)
        h = self._h(" Random Forest — Regresión")
        h += "<table style='font-size:12px;'>"
        h += self._r("Respuesta", escape(str(target_col)))
        h += self._r("Observaciones", len(y))
        if _sin_resultado(cv):
            h += self._r("R² por validación cruzada", cv.get("error", "—"))
        else:
            h += self._r(f"R² por validación cruzada (k={cv['k']})", f"{cv['media']:.4f} ± {cv['de']:.4f}")
        h += self._r("R² sobre los datos de entrenamiento (optimista)", f"{r2_train:.4f}")
        h += "</table>" + self._nota_columnas(nums, del_dialogo)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5))
        ax1.scatter(y, y_pred, alpha=0.5, c='#4f6ef7', edgecolors='white', s=50)
        lims = [min(y.min(), y_pred.min()), max(y.max(), y_pred.max())]
        ax1.plot(lims, lims, '--', color='#ef4444', lw=1.5, label='Predicción perfecta')
        ax1.set_xlabel('Observado')
        ax1.set_ylabel('Predicho (sobre entrenamiento)')
        ax1.set_title('Observado vs Predicho', fontweight='bold')
        ax1.legend(framealpha=0.9)
        imp = rf.get_feature_importance()
        sorted_idx = np.argsort(imp)[::-1][:min(8, len(nums))]
        ax2.barh(range(len(sorted_idx)), imp[sorted_idx], color='#22c55e', edgecolor='white')
        ax2.set_yticks(range(len(sorted_idx)))
        ax2.set_yticklabels([nums[i] for i in sorted_idx])
        ax2.set_xlabel('Importancia')
        ax2.set_title('Importancia de Variables', fontweight='bold')
        ax2.invert_yaxis()
        fig.tight_layout()
        self._show_fig(fig)
        return h

    # --- Mann-Whitney U ---
    # --- No parametricas: las arma src/resultado/constructores/noparametricas.py ---
    def _mannwhitney(self, c1, c2):
        return mann_whitney(self.data, c1, c2)

    def _signos(self, c1, c2):
        return signos(self.data, c1, c2)

    def _cochran(self):
        cols, del_dialogo = self._columnas_multi()
        return self._con_nota_columnas(cochran(self.data, cols), cols, del_dialogo,
                                       "tratamientos")

    # --- Wilcoxon pareado ---
    def _wilcoxon(self, c1, c2):
        return wilcoxon(self.data, c1, c2)

    # --- Chi-cuadrado ---
    # --- Proporciones y tablas: las arma src/resultado/constructores/tablas.py ---
    def _chi2(self, c1, c2):
        return chi_cuadrado(self.data, c1, c2)

    def _dos_proporciones(self):
        try:
            opciones = {k: self._param("Comparar 2 proporciones", k)
                        for k in ("x1", "n1", "x2", "n2")}
        except ValueError as e:
            return f"<b>Error:</b> {e}"
        res = dos_proporciones(opciones)
        if res.ok and not getattr(self, "parametros", None):
            res.advertencias.append("Son los valores de ejemplo. Para calcular con los "
                                    "tuyos, abrí el análisis desde el menú Estadísticas.")
        return res

    # --- Fisher exact ---
    def _fisher(self, c1, c2):
        return fisher(self.data, c1, c2)

    # --- McNemar ---
    def _mcnemar(self, c1, c2):
        return mcnemar(self.data, c1, c2)

    # --- Kruskal-Wallis ---
    def _kruskal(self, c1, c2):
        """Variable 1 = respuesta, Variable 2 = grupo (formato largo)."""
        return kruskal(self.data, c1, c2)

    # --- Friedman ---
    def _friedman(self):
        cols, del_dialogo = self._columnas_multi()
        return self._con_nota_columnas(friedman(self.data, cols), cols, del_dialogo,
                                       "condiciones")

    # --- F-test ---
    def _ftest(self, c1, c2):
        return f_varianzas(self.data, c1, c2)

    # --- Kappa ---
    def _kappa(self, c1, c2):
        """Kappa de Cohen: Variable 1 y Variable 2 = las clasificaciones de dos
        evaluadores o métodos, una fila por sujeto."""
        for c in (c1, c2):
            if c is None or c not in self.data.columns:
                return f"<b>Error:</b> la columna «{escape(str(c))}» no está en la hoja."
        pares = self._filas_completas(c1, c2)
        categorias = sorted(set(pares[c1]) | set(pares[c2]), key=str)
        if len(categorias) > 20:
            return (f"<b>Error:</b> hay {len(categorias)} categorías distintas: kappa es para "
                    "clasificaciones categóricas.")
        tabla = pd.crosstab(pares[c1], pares[c2]).reindex(index=categorias,
                                                           columns=categorias, fill_value=0)
        r = cohens_kappa(tabla.values)
        if _sin_resultado(r):
            return _msg_error(r, "No se pudo calcular.")
        self._set_formula("Formula: Kappa de Cohen",
                          "κ = (Po − Pe) / (1 − Pe)\n"
                          "IC 95%: EE de Fleiss, Cohen y Everitt (1969)\n"
                          "p: EE bajo H0 (κ = 0)",
                          f"κ = {r['kappa']:.4f}\np = {r['p']:.6f}\nFuerza: {r['strength']}")
        h = self._h(f" Kappa de Cohen — {escape(str(c1))} vs {escape(str(c2))}")
        h += self._html_tabla_rxc(tabla)
        h += "<table style='font-size:12px;'>"
        for l, v in [("n", r['n']), ("Kappa", f"{r['kappa']:.4f}"),
                     ("IC 95%", f"{r['ci'][0]:.4f} a {r['ci'][1]:.4f}"),
                     ("Fuerza (Altman 1991)", r['strength']), ("p", _p_html(r['p']))]:
            h += self._r(l, v)
        return h + "</table>"

    # --- ICC ---
    def _icc(self, c1, c2):
        """ICC(A,1) y ICC(C,1): lo arma el constructor de `Resultado`."""
        return icc(self.data, c1, c2)

    # --- Cronbach alpha ---
    def _cronbach(self):
        """Alfa de Cronbach sobre los ítems elegidos (una columna por ítem)."""
        cols, del_dialogo = self._columnas_multi()
        if len(cols) < 2:
            return f"<b>Error:</b> hacen falta al menos 2 ítems (columnas numéricas); hay {len(cols)}."
        data = self._filas_completas(*cols).values
        r = cronbach_alpha(data)
        if _sin_resultado(r):
            return _msg_error(r, "No se pudo calcular.")
        self._set_formula("Formula: Alfa de Cronbach",
                          "α = (k/(k−1)) · (1 − Σ varᵢ / var_total)",
                          f"α = {r['alpha']:.4f}\nk = {r['n_items']}")
        h = self._h(f" Alfa de Cronbach")
        h += "<table style='font-size:12px;'>"
        h += self._r("Alfa", f"{r['alpha']:.4f}")
        h += self._r("Ítems", r['n_items'])
        h += self._r("Sujetos completos", r['n_subjects'])
        h += "</table>"
        return h + self._nota_columnas(cols, del_dialogo)

    # --- Regresion lineal ---
    # --- Regresion: la arma src/resultado/constructores/regresion.py ---
    def _reg_lineal(self, c1, c2):
        return regresion_lineal(self.data, c1, c2)

    # --- Regresion multiple ---
    def _reg_multiple(self, c1):
        """Variable 1 = respuesta; predictoras = las tildadas."""
        predictoras, del_dialogo = self._columnas_multi(excluir=(c1,))
        return self._con_nota_columnas(
            regresion_multiple(self.data, c1, predictoras), predictoras, del_dialogo)

    # --- Regresion logistica ---
    def _reg_logistica(self, c1):
        """Variable 1 = respuesta 0/1; predictoras = las tildadas."""
        predictoras, del_dialogo = self._columnas_multi(excluir=(c1,))
        return self._con_nota_columnas(
            regresion_logistica(self.data, c1, predictoras), predictoras, del_dialogo)

    def _con_nota_columnas(self, res, columnas, del_dialogo, que="predictoras"):
        """Sin dialogo se usaron todas las numericas: el informe lo dice."""
        if res.ok and not del_dialogo:
            res.advertencias.append(
                f"Se usaron todas las columnas numéricas de la hoja como {que}: "
                + ", ".join(str(c) for c in columnas) + ". Si alguna no corresponde "
                "(un número de muestra, una fecha), abrí el análisis desde el menú "
                "Estadísticas y destildala.")
        return res

    # --- Odds Ratio ---
    def _odds_ratio(self, c1, c2):
        """Variable 1 = exposición, Variable 2 = evento."""
        return odds_ratio_tabla(self.data, c1, c2)

    # --- Riesgo Relativo ---
    def _riesgo_relativo(self, c1, c2):
        """Variable 1 = exposición, Variable 2 = evento."""
        return riesgo_relativo(self.data, c1, c2)

    # --- Diagnostic test ---
    def _diag_test(self, c1, c2):
        """Prueba diagnóstica: Variable 1 = resultado de la prueba, Variable 2 =
        estándar de oro (enfermo/sano), una fila por sujeto."""
        t = self._tabla_2x2(c1, c2)
        if isinstance(t, str):
            return t
        a, b, c, d, filas, columnas, lectura, avisos = t
        r = diagnostic_test(a, b, c, d)
        self._set_formula("Formula: Prueba Diagnostica",
                          "a = VP, b = FP, c = FN, d = VN\nSens = a/(a+c), Espec = d/(b+d)\n"
                          "VPP = a/(a+b), VPN = d/(c+d)\nIC 95%: Wilson (CLSI EP12)",
                          f"Sens={r['sens']:.4f}, Spec={r['spec']:.4f}\nPPV={r['ppv']:.4f}, NPV={r['npv']:.4f}")
        h = self._h(" Prueba Diagnostica")
        h += f"<p style='font-size:11px;'>{lectura}</p>"
        h += self._html_tabla_2x2(a, b, c, d, filas, columnas)
        h += "<table style='font-size:12px;'>"

        def _con_ic(valor, ic):
            """Una proporcion sin su intervalo invita a leer 20/20 como
            certeza. CLSI EP12 pide el IC; el metodo es Wilson."""
            if not np.isfinite(valor):
                return "no definido"
            if ic is None or not all(np.isfinite(x) for x in ic):
                return f"{valor:.4f}"
            return f"{valor:.4f}  (IC 95%: {ic[0]:.4f} – {ic[1]:.4f})"

        for l, clave, ic_clave in [("Sensibilidad", "sens", "ci_sens"),
                                   ("Especificidad", "spec", "ci_spec"),
                                   ("VPP", "ppv", "ci_ppv"),
                                   ("VPN", "npv", "ci_npv"),
                                   ("Exactitud", "acc", "ci_acc")]:
            h += self._r(l, _con_ic(r[clave], r.get(ic_clave)))
        for l, clave in [("LR+", "plr"), ("LR-", "nlr")]:
            v = r[clave]
            h += self._r(l, "infinito" if not np.isfinite(v) else f"{v:.4f}")
        h += "</table>"
        return h + self._avisos_html(list(avisos) + list(r.get("avisos", [])))

    # --- Outliers Grubbs ---
    def _outliers_grubbs(self, col):
        return grubbs(self.data, col)

    # --- Outliers Tukey ---
    def _outliers_tukey(self, col):
        return tukey(self.data, col)

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
        self._set_formula(
            "Formula: Intervalo de Referencia (CLSI EP28-A3c)",
            "Limite inferior = dato de rango 0,025·(n+1), interpolado (§9.4.1)\n"
            "Limite superior = dato de rango 0,975·(n+1), interpolado\n"
            "IC 90% de cada limite: rangos de orden de la tabla 8 (§9.5.1), n ≥ 119",
            f"Limite inf (2.5%): {ri['lower']:.4f}\nLimite sup (97.5%): {ri['upper']:.4f}")
        h = self._h(f" Intervalos de Referencia — {col}")
        h += "<table style='font-size:12px;'>"
        h += self._r("n", ri['n'])
        h += self._r("Limite inferior (2.5%)", f"{ri['lower']:.4f}")
        h += self._r("Limite superior (97.5%)", f"{ri['upper']:.4f}")
        if ri["rangos_ic"] is not None:
            a, b = ri["rangos_ic"]
            h += self._r("IC 90% del limite inferior",
                         f"{ri['ci_lower_low']:.4f} a {ri['ci_lower_high']:.4f} (rangos {a} y {b})")
            h += self._r("IC 90% del limite superior",
                         f"{ri['ci_upper_low']:.4f} a {ri['ci_upper_high']:.4f} "
                         f"(rangos {ri['n'] + 1 - b} y {ri['n'] + 1 - a})")
        else:
            h += self._r("IC de los limites", "sin IC normativo (EP28 lo da desde n = 119)")
        h += "</table>"
        for aviso in ri.get("avisos", []):
            h += f"<p style='font-size:11px;color:#b45309;'>{aviso}</p>"
        return h

    # --- Asimetria y curtosis ---
    def _skew_kurt(self, col):
        return asimetria_curtosis(self.data, col)

    # --- Media recortada ---
    def _trimmed(self, col):
        return media_recortada(self.data, col)

    # --- Correlacion parcial ---
    def _partial_corr(self, c1, c2, c3):
        if c3 is None or c3 not in self.data.columns:
            return Resultado.rechazo(
                "parcial", "Correlación parcial",
                "Elegí en la Variable 3 la variable que se quiere controlar.")
        return parcial(self.data, c1, c2, c3)

    # --- Core Module Runners ---
    def _run_core(self, func_name, c1=None, c2=None):
        """Run a core module function and display results."""
        try:
            if func_name == "weighted_kappa":
                for c in (c1, c2):
                    if c is None or c not in self.data.columns:
                        return "<b>Error:</b> Elegí las dos clasificaciones ordinales en la Variable 1 y la Variable 2."
                pares = self._filas_completas(c1, c2)
                d1, d2 = pares[c1], pares[c2]
                cats = sorted(set(d1) | set(d2))
                if len(cats) > 20:
                    return f"<b>Error:</b> hay {len(cats)} categorías: el kappa ponderado es para escalas ordinales."
                n = len(cats)
                matrix = np.zeros((n, n))
                for a, b in zip(d1, d2):
                    i, j = cats.index(a), cats.index(b)
                    matrix[i][j] += 1
                result = weighted_kappa(matrix)
                if _sin_resultado(result):
                    return _msg_error(result, "No se pudo calcular.")
                self._set_formula("Formula: Kappa Ponderado (pesos lineales)",
                                  "κ_w = 1 − (Σ wᵢⱼ·Oᵢⱼ) / (Σ wᵢⱼ·Eᵢⱼ),  wᵢⱼ = |i − j| / (k − 1)\n"
                                  "Las categorías se ordenan de menor a mayor")
                h = self._h(f" Kappa Ponderado — {escape(str(c1))} vs {escape(str(c2))}")
                h += "<table style='font-size:12px;'>"
                h += self._r("n", result['n'])
                h += self._r("Categorías (en orden)", escape(", ".join(str(c) for c in cats)))
                h += self._r("Kappa ponderado", f"{result['kappa']:.4f}")
                h += self._r("Acuerdo observado (po)", f"{result['po']:.4f}")
                h += self._r("Acuerdo esperado (pe)", f"{result['pe']:.4f}")
                return h + "</table>"

            elif func_name == "likelihood_ratios":
                t = self._tabla_2x2(c1, c2)
                if isinstance(t, str):
                    return t
                a, b, c, d, filas, columnas, lectura, avisos = t
                result = likelihood_ratios(a, b, c, d)
                self._set_formula("Formula: Likelihood Ratios (Simel et al., 1991)",
                                  "LR+ = Sens / (1 − Espec),  LR− = (1 − Sens) / Espec\n"
                                  "Var(ln LR+) = 1/a − 1/(a+c) + 1/b − 1/(b+d)\n"
                                  "Var(ln LR−) = 1/c − 1/(a+c) + 1/d − 1/(b+d)")
                h = self._h(" Likelihood Ratios")
                h += f"<p style='font-size:11px;'>{lectura}</p>"
                h += self._html_tabla_2x2(a, b, c, d, filas, columnas)
                h += "<table style='font-size:12px;'>"
                h += self._r("LR+", f"{result['plr']:.4f}")
                if result.get('ci_plr'):
                    h += self._r("IC 95% LR+", f"{result['ci_plr'][0]:.4f} a {result['ci_plr'][1]:.4f}")
                h += self._r("LR−", f"{result['nlr']:.4f}")
                if result.get('ci_nlr'):
                    h += self._r("IC 95% LR−", f"{result['ci_nlr'][0]:.4f} a {result['ci_nlr'][1]:.4f}")
                return h + "</table>" + self._avisos_html(avisos)

            elif func_name == "compare_auc":
                valores = pd.to_numeric(self.data.iloc[:, 0], errors="coerce").dropna()
                if len(valores) != 6:
                    return ("<b>Error:</b> esta calculadora lee exactamente 6 valores de la "
                            "primera columna, en este orden: AUC1, EE1, n1, AUC2, EE2, n2. La columna tiene "
                            f"{len(valores)}. Si tenés los datos de cada sujeto, usá la prueba "
                            "correspondiente, que los toma de las columnas.")
                auc1, se1, n1, auc2, se2, n2 = valores.iloc[:6]
                n1, n2 = int(n1), int(n2)
                result = compare_two_auc(auc1, se1, n1, auc2, se2, n2)
                if _sin_resultado(result):
                    return _msg_error(result, "No se pudo comparar las AUC.")
                self._set_formula("Formula: Comparar 2 AUC (curvas independientes)",
                                  "z = (AUC1 − AUC2) / √(EE1² + EE2²)")
                h = self._h(" Comparar 2 AUC")
                h += "<table style='font-size:12px;'>"
                h += self._r("Diferencia", f"{result['diff']:.4f}")
                h += self._r("z", f"{result['z']:.4f}")
                h += self._r("p", _p_html(result['p']))
                h += "</table>" + self._avisos_html(result.get("avisos", []))
                return h + self._ok(result['p'] < 0.05)
            elif func_name == "age_related":
                for c in (c1, c2):
                    if c is None or c not in self.data.columns:
                        return "<b>Error:</b> Elegí la edad en la Variable 1 y el valor en la Variable 2."
                pares = self._filas_completas(c1, c2)
                ages, values = pares[c1].values, pares[c2].values
                result = age_related_reference(ages, values)
                self._set_formula("Formula: Intervalos por Edad",
                                  "Grupos de edad de ancho fijo [desde, hasta); en cada uno, "
                                  "percentiles 5, 50 y 95 del valor")
                h = self._h(f" Intervalos por Edad — {escape(str(c2))} según {escape(str(c1))}")
                h += "<table style='font-size:12px;'>"
                if not result['groups']:
                    h += "<tr><td>Sin datos.</td></tr>"
                else:
                    def _v(x):
                        return "—" if not np.isfinite(x) else f"{x:.2f}"
                    h += "<tr><th>Grupo</th><th>n</th><th>Media</th><th>P5</th><th>Mediana</th><th>P95</th></tr>"
                    for g in result['groups']:
                        h += (f"<tr><td>{g['age_group']}</td><td>{g['n']}</td><td>{g['mean']:.2f}</td>"
                              f"<td>{_v(g['p5'])}</td><td>{_v(g['median'])}</td><td>{_v(g['p95'])}</td></tr>")
                h += "</table>"
                if any(g.get("nota") for g in result['groups']):
                    h += self._avisos_html(["Los grupos con menos de 5 sujetos se muestran sin "
                                            "percentiles: con tan pocos datos no hay percentil 5 "
                                            "ni 95 que estimar."])
                return h

            elif func_name == "bootstrap_median":
                if c1 is None or c1 not in self.data.columns:
                    return "<b>Error:</b> Selecciona una columna."
                d = self.data[c1].dropna().values
                result = bootstrap_median(d)
                self._set_formula("Formula: Bootstrap Mediana", "IC = percentiles de la distribución bootstrap")
                h = self._h(f" Bootstrap (Mediana) — {c1}")
                h += "<table style='font-size:12px;'>"
                h += self._r("Mediana", f"{result['original_median']:.4f}")
                h += self._r("Mediana bootstrap", f"{result['bootstrap_median']:.4f}")
                h += self._r("95% CI", f"[{result['ci_lower']:.4f}, {result['ci_upper']:.4f}]")
                return h + "</table>"

            elif func_name == "bootstrap_regression":
                if c1 is None or c2 is None:
                    return "<b>Error:</b> Selecciona 2 columnas."
                if c1 not in self.data.columns or c2 not in self.data.columns:
                    return "<b>Error:</b> Columnas no encontradas."
                pares = self._filas_completas(c1, c2)
                x, y = pares[c1].values, pares[c2].values
                result = bootstrap_regression(x, y)
                self._set_formula("Formula: Bootstrap Regresión", "IC para coeficientes de regresión")
                h = self._h(f" Bootstrap (Regresión) — {c1} vs {c2}")
                h += "<table style='font-size:12px;'>"
                h += self._r("Pendiente", f"{result['original_slope']:.4f}")
                h += self._r("95% CI pendiente", f"[{result['ci_slope'][0]:.4f}, {result['ci_slope'][1]:.4f}]")
                h += self._r("Intercepto", f"{result['original_intercept']:.4f}")
                return h + "</table>"

            elif func_name == "sample_size_corr":
                if c1 is None or c2 is None:
                    return "<b>Error:</b> Selecciona 2 columnas para calcular r."
                if c1 not in self.data.columns or c2 not in self.data.columns:
                    return "<b>Error:</b> Columnas no encontradas."
                pares = self._filas_completas(c1, c2)
                r_result = pearson_r(pares[c1], pares[c2])
                r = abs(r_result['r'])
                result = sample_size_correlation(r)
                self._set_formula("Formula: Tamaño Muestral (Correlación)", "n = [(Z_α/2 + Z_β) / arctanh(r)]² + 3")
                h = self._h(f" Tamaño Muestral (Correlación)")
                h += "<table style='font-size:12px;'>"
                h += self._r("r observado", f"{r:.4f}")
                h += self._r("n necesario", result['n'])
                h += self._r("Poder", f"{result['power']:.4f}")
                return h + "</table>"

            else:
                return f"<b>Error:</b> Función desconocida: {func_name}"

        except Exception as e:
            return f"<p style='color:red'>Error en {func_name}: {str(e)}</p>"

    def _run_two_way_anova(self, c1, c2, c3):
        """Variable 1 = respuesta, Variable 2 = factor A, Variable 3 = factor B."""
        if c3 is None or c3 not in self.data.columns:
            return Resultado.rechazo("anova_dos_vias", "ANOVA de dos vías",
                                     "Elegí el segundo factor en la Variable 3.")
        return anova_dos_vias(self.data, c1, c2, c3)

    def _run_ancova(self, c1, c2, c3):
        """Variable 1 = respuesta, Variable 2 = grupo, Variable 3 = covariable."""
        if c3 is None or c3 not in self.data.columns:
            return Resultado.rechazo("ancova", "ANCOVA",
                                     "Elegí la covariable en la Variable 3.")
        return ancova_resultado(self.data, c1, c2, c3)

    def _run_repeated_measures(self):
        """Una columna por tiempo, una fila por sujeto."""
        cols, del_dialogo = self._columnas_multi()
        return self._con_nota_columnas(medidas_repetidas(self.data, cols), cols,
                                       del_dialogo, "tiempos")

    def _run_cox(self, c1, c2):
        """Run Cox Regression."""
        if c1 is None or c2 is None:
            return "<b>Error:</b> Selecciona Tiempo (V1) y Evento (V2, 0/1)."
        if c1 not in self.data.columns or c2 not in self.data.columns:
            return "<b>Error:</b> Columnas no encontradas."
        try:
            cols_cov = list(self.data.columns[3:]) if self.data.shape[1] > 2 else []
            filas = self._filas_completas(c1, c2, *cols_cov)
            times = filas[c1].values
            events = filas[c2].values
            covariates = filas[cols_cov].values if cols_cov else np.ones((len(times), 1))
            result = cox_regression(times, events, covariates)
            self._set_formula("Formula: Cox PH", "h(t) = h₀(t) × exp(β₁x₁ + β₂x₂ + ...)")
            h = self._h(f" Cox Regression")
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
        """Variable 1 = dosis, Variable 2 = respuesta 0/1."""
        return probit(self.data, c1, c2, getattr(self, "opciones_metodo", None))

    def _run_cmh(self, c1, c2, c3):
        """Exposición (V1), evento (V2) y estrato (V3), una fila por sujeto."""
        if c3 is None or c3 not in self.data.columns:
            return Resultado.rechazo("cmh", "Cochran-Mantel-Haenszel",
                                     "Elegí el estrato en la Variable 3.")
        return cmh(self.data, c1, c2, c3)

    def _run_serial(self):
        """Mediciones seriadas: una columna por tiempo (en orden), una fila por sujeto."""
        cols, del_dialogo = self._columnas_multi()
        if len(cols) < 2:
            return f"<b>Error:</b> hacen falta al menos 2 tiempos (columnas numéricas); hay {len(cols)}."
        try:
            result = serial_measurements_summary(self.data[cols].values)
            self._set_formula("Formula: Mediciones Seriadas (medidas resumen)",
                              "Pendiente de cada sujeto contra el tiempo (0, 1, ..., k−1)\n"
                              "Tendencia: t de una muestra sobre las pendientes (H0: media = 0)")
            h = self._h(" Mediciones Seriadas")
            h += "<table style='font-size:12px;'>"
            h += self._r("Sujetos", result['n_subjects'])
            h += self._r("Mediciones", result['n_timepoints'])
            ic = result['ic_pendiente_media']
            h += self._r("Pendiente media por sujeto", f"{result['mean_slope']:.4f}")
            h += self._r("IC 95% de la pendiente media", f"{ic[0]:.4f} a {ic[1]:.4f}")
            h += self._r("DE de las pendientes", f"{result['sd_slope']:.4f}")
            h += self._r("¿Hay tendencia? (t sobre las pendientes)",
                         f"t={result['t_tendencia']:.3f}, {_p_html(result['p_tendencia'])}")
            h += "</table>"
            h += ("<p style='font-size:11px;color:#555;'>Cada sujeto aporta una sola "
                  "pendiente: sus mediciones no son independientes entre sí, las de "
                  "sujetos distintos sí (Matthews et al., BMJ 1990).</p>")
            h += self._avisos_html(result.get("avisos", []))
            h += "<b style='font-size:12px;'>Medias por tiempo:</b><table style='font-size:12px;'>"
            for c, m, s, k in zip(cols, result['means'], result['sds'], result['n_por_tiempo']):
                h += self._r(escape(str(c)), f"{m:.4f} ± {s:.4f} (n={k})")
            return h + "</table>" + self._nota_columnas(cols, del_dialogo)
        except Exception as e:
            return f"<p style='color:red'>Error: {escape(str(e))}</p>"

    def _run_youden(self, score_col, label_col):
        """Run Youden Plot."""
        if label_col is None or label_col == "(ninguna)" or label_col not in self.data.columns:
            return "<b>Error:</b> Selecciona Variable 3 (etiquetas 0/1)."
        if score_col is None or score_col not in self.data.columns:
            return "<b>Error:</b> Selecciona Variable 1 (scores)."
        try:
            pares = self._filas_completas(score_col, label_col)
            y_true = pares[label_col].values
            y_score = pares[score_col].values
            n = len(pares)
            result = youden_data(y_true, y_score)
            if _sin_resultado(result):
                return _msg_error(result, "No se pudo calcular.")
            
            self._set_formula("Formula: Youden's J", "J = Sensibilidad + Especificidad - 1")
            
            h = self._h(f" Youden Plot — {score_col}")
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
            
            h = self._h(f" Polar Plot")
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
            
            h = self._h(f" Waterfall Chart — {col}")
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

    def _run_mountain(self, c1, c2):
        """Mountain plot: acumulada plegada de las diferencias Variable 1 − Variable 2."""
        for c in (c1, c2):
            if c is None or c not in self.data.columns:
                return "<b>Error:</b> Elegí los dos métodos en la Variable 1 y la Variable 2."
        pares = self._filas_completas(c1, c2)
        result = mountain_plot_data(pares[c1].values, pares[c2].values)
        if _sin_resultado(result):
            return _msg_error(result, "Se necesitan al menos 5 pares.")
        self._set_formula("Formula: Mountain Plot (Krouwer y Monti, 1995)",
                          "d = método 1 − método 2, ordenadas\n"
                          "percentil = 100·rango / (n + 1); si pasa de 50, se pliega: 100 − percentil")
        h = self._h(f" Mountain Plot — {escape(str(c1))} − {escape(str(c2))}")
        h += "<table style='font-size:12px;'>"
        h += self._r("n", result['n'])
        h += self._r("Mediana de las diferencias (pico)", f"{result['mediana']:.4f}")
        h += self._r("Percentiles 25 a 75", f"{result['p25']:.4f} a {result['p75']:.4f}")
        if np.isfinite(result['p2_5']):
            h += self._r("Percentiles 2,5 a 97,5", f"{result['p2_5']:.4f} a {result['p97_5']:.4f}")
        h += "</table>"
        h += ("<p style='font-size:11px;color:#555;'>Dos métodos intercambiables dan una "
              "montaña angosta con el pico en 0. El pico corrido es sesgo; la montaña ancha, "
              "desacuerdo.</p>")
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(result['diferencias'], result['percentil_plegado'], color='#4f6ef7', lw=1.8)
        ax.fill_between(result['diferencias'], result['percentil_plegado'], color='#4f6ef7', alpha=0.12)
        ax.axvline(0, color='#9ca3af', ls=':', lw=1.2, label='Diferencia 0')
        ax.axvline(result['mediana'], color='#ef4444', ls='--', lw=1.2,
                   label=f"Mediana: {result['mediana']:.3f}")
        ax.set_xlabel(f'Diferencia ({c1} − {c2})')
        ax.set_ylabel('Percentil plegado')
        ax.set_ylim(0, 52)
        ax.set_title('Mountain Plot', fontweight='bold')
        ax.legend(loc='upper right', framealpha=0.9)
        fig.tight_layout()
        self._show_fig(fig)
        return h

    def _run_bland_multi(self, c1):
        """Varios métodos contra UNO de referencia (Variable 1): lo arma el constructor."""
        if c1 is None or c1 not in self.data.columns:
            return "<b>Error:</b> Elegí el método de referencia en la Variable 1."
        metodos, del_dialogo = self._columnas_multi(excluir=(c1,))
        res = bland_altman_multiple(self.data, c1, metodos)
        if res.ok and not del_dialogo:
            res.advertencias.append(
                "Se usaron todas las columnas numéricas de la hoja como métodos: "
                + ", ".join(str(m) for m in metodos) + ". Si alguna no corresponde (un "
                "número de muestra, una edad), abrí el análisis desde el menú "
                "Estadísticas y destildala.")
        return res

    def _validar(self, c1, c2):
        """El asistente B: Variable 1 = método en uso, Variable 2 = en prueba.

        Las corridas de EP15 solo entran si se tildaron en el diálogo: sin
        diálogo no hay forma de saber cuáles columnas son corridas, y tomarlas
        todas metería los dos métodos como si fueran días.
        """
        corridas, del_dialogo = self._columnas_multi(excluir=(c1, c2))
        opciones = dict(getattr(self, "opciones_metodo", None) or {})
        try:
            for clave in ("sesgo_permitido", "lambda", "sigma_r", "sigma_wl", "n_muestras"):
                opciones[clave] = self._param("Validar un método", clave)
            opciones["niveles"] = [v for v in (self._param("Validar un método", f"nivel_{i}")
                                               for i in (1, 2, 3)) if v is not None]
        except ValueError as e:
            return f"<b>Error:</b> {e}"
        opciones["corridas"] = corridas if del_dialogo else []
        return validar_metodo(self.data, c1, c2, opciones)

    def _ep15(self):
        """EP15-A3: cada columna tildada es una corrida. Lo arma el constructor."""
        corridas, del_dialogo = self._columnas_multi()
        opciones = dict(getattr(self, "opciones_metodo", None) or {})
        try:
            for clave in ("sigma_r", "sigma_wl", "n_muestras", "valor_asignado", "u", "k",
                          "n_lab"):
                opciones[clave] = self._param("Precisión EP15", clave)
        except ValueError as e:
            return f"<b>Error:</b> {e}"
        res = precision_ep15(self.data, corridas, opciones)
        if res.ok and not del_dialogo:
            res.advertencias.append(
                "Se tomaron todas las columnas numéricas de la hoja como corridas: "
                + ", ".join(str(c) for c in corridas) + ". Para elegir las corridas y "
                "cargar lo que declara el fabricante, abrí el análisis desde el menú "
                "Estadísticas.")
        return res
