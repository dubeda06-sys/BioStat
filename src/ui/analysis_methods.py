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
from src.ui.analysis_specs import parametros as spec_parametros
from src.resultado.datos import filas_completas
from src.resultado.constructores import (
    bland_altman, bland_altman_multiple, cv_duplicados, deming, icc,
    passing_bablok as passing_bablok_resultado, precision_ep15, validar_metodo,
)
from src.resultado.constructores.anova import (
    ancova as ancova_resultado, anova_dos_vias, anova_una_via, medidas_repetidas,
)
from src.resultado.constructores.concordancia import cronbach, kappa, kappa_ponderado
from src.resultado.constructores.correlacion import parcial, pearson, spearman
from src.resultado.constructores.graficos import cascada, mountain, polar, youden
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
from src.resultado.constructores.referencia import intervalo_referencia, intervalos_por_edad
from src.resultado.constructores.roc import comparar_auc, curva_roc
from src.resultado.constructores.tamano import (
    poder_t, tam_correlacion, tam_dos_medias, tam_dos_proporciones, tam_una_media,
)
from src.resultado.constructores.supervivencia import kaplan_meier, log_rank, regresion_cox
from src.resultado.constructores.resumen import (
    asimetria_curtosis, descriptivas, esd, grubbs, media_armonica, media_geometrica,
    media_recortada, percentiles, shapiro_wilk, tukey,
)
from src.resultado.lenguaje import texto_descartes
from src.resultado.modelo import Resultado
from src.core.meta_analysis import meta_analysis
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
from src.core.two_way_anova import two_way_anova
from src.core.ancova import ancova
from src.core.repeated_measures import repeated_measures_anova
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
    # --- Curvas ROC: src/resultado/constructores/roc.py ---
    def _roc(self, score_col, label_col):
        if label_col is None or label_col not in self.data.columns:
            return Resultado.rechazo("curva_roc", "Curva ROC",
                                     "Elegí la etiqueta (1 enfermo, 0 sano) en la Variable 3.")
        return curva_roc(self.data, score_col, label_col)

    def _comparar_auc(self):
        try:
            opciones = {k: self._param("Comparar 2 AUC", k)
                        for k in ("auc1", "ee1", "n1", "auc2", "ee2", "n2")}
        except ValueError as e:
            return f"<b>Error:</b> {e}"
        res = comparar_auc(opciones)
        if res.ok and not getattr(self, "parametros", None):
            res.advertencias.append("Son los valores de ejemplo. Para calcular con los "
                                    "tuyos, abrí el análisis desde el menú Estadísticas.")
        return res

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

    # --- Supervivencia: src/resultado/constructores/supervivencia.py ---
    def _kaplan_meier(self, time_col, event_col):
        """Variable 1 = tiempo; Variable 2 = evento (1) o censura (0)."""
        return kaplan_meier(self.data, time_col, event_col)

    def _log_rank(self, time_col, event_col, group_col):
        """Variable 3 = grupo (dos o más)."""
        if group_col is None or group_col not in self.data.columns:
            return Resultado.rechazo("log_rank", "Log-rank",
                                     "Elegí el grupo en la Variable 3.")
        return log_rank(self.data, time_col, event_col, group_col)

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

    # --- Tamaño de muestra y poder: src/resultado/constructores/tamano.py ---
    def _calculadora(self, nombre, constructor, extra=None):
        """Los parámetros del diálogo (o los de ejemplo) a una calculadora."""
        try:
            opciones = {p.clave: self._param(nombre, p.clave)
                        for p in spec_parametros(nombre)}
        except ValueError as e:
            return f"<b>Error:</b> {e}"
        opciones.update(extra or {})
        res = constructor(opciones)
        if res.ok and not getattr(self, "parametros", None):
            res.advertencias.append("Son los valores de ejemplo. Para calcular con los "
                                    "tuyos, abrí el análisis desde el menú Estadísticas: "
                                    "el diálogo los pide.")
        return res

    def _ss_mean(self):
        return self._calculadora("Tamano muestral (1 media)", tam_una_media)

    def _ss_two_means(self):
        return self._calculadora("Tamano muestral (2 medias)", tam_dos_medias)

    def _ss_prop(self):
        return self._calculadora("Tamano muestral (2 proporciones)", tam_dos_proporciones)

    def _ss_corr(self):
        return self._calculadora("Tamaño muestral (correlacion)", tam_correlacion)

    def _power(self):
        diseno = (getattr(self, "opciones_metodo", None) or {}).get("diseno", "una")
        return self._calculadora("Poder estadistico", poder_t, {"diseno": diseno})

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
    # --- Concordancia: la arma src/resultado/constructores/concordancia.py ---
    def _kappa(self, c1, c2):
        return kappa(self.data, c1, c2)

    def _kappa_ponderado(self, c1, c2):
        return kappa_ponderado(self.data, c1, c2, getattr(self, "opciones_metodo", None))

    # --- ICC ---
    def _icc(self, c1, c2):
        """ICC(A,1) y ICC(C,1): lo arma el constructor de `Resultado`."""
        return icc(self.data, c1, c2)

    # --- Cronbach alpha ---
    def _cronbach(self):
        cols, del_dialogo = self._columnas_multi()
        return self._con_nota_columnas(cronbach(self.data, cols), cols, del_dialogo,
                                       "ítems")

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

    # --- Valores de referencia: src/resultado/constructores/referencia.py ---
    def _ref_interval(self, col):
        """Una columna; los límites publicados, opcionales, para verificarlos."""
        try:
            opciones = {k: self._param("Intervalos de referencia", k)
                        for k in ("inferior", "superior")}
        except ValueError as e:
            return f"<b>Error:</b> {e}"
        return intervalo_referencia(self.data, col, opciones)

    def _edad(self, c1, c2):
        """Variable 1 = edad, Variable 2 = valor."""
        for c in (c1, c2):
            if c is None or c not in self.data.columns:
                return Resultado.rechazo("intervalos_edad", "Intervalos por edad",
                                         "Elegí la edad en la Variable 1 y el valor en la "
                                         "Variable 2.")
        return intervalos_por_edad(self.data, c1, c2,
                                   getattr(self, "opciones_metodo", None))

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
            if func_name == "likelihood_ratios":
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
        """Variable 1 = tiempo, Variable 2 = evento; covariables = las tildadas."""
        covariables, del_dialogo = self._columnas_multi(excluir=(c1, c2))
        return self._con_nota_columnas(regresion_cox(self.data, c1, c2, covariables),
                                       covariables, del_dialogo, "covariables")

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

    # --- Graficos de comparacion: src/resultado/constructores/graficos.py ---
    def _run_youden(self, c1, c2):
        """Muestra 1 (V1) y muestra 2 (V2), una fila por laboratorio."""
        return youden(self.data, c1, c2)

    def _run_polar(self):
        cols, del_dialogo = self._columnas_multi()
        return self._con_nota_columnas(polar(self.data, cols), cols, del_dialogo,
                                       "ejes")

    def _run_waterfall(self, col):
        return cascada(self.data, col)

    def _run_mountain(self, c1, c2):
        return mountain(self.data, c1, c2)

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
