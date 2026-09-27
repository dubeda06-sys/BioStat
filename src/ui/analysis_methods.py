"""Panel de analisis estadistico."""
import matplotlib
matplotlib.use('QtAgg')
import matplotlib.pyplot as plt



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



from src.ui.analysis_specs import parametros as spec_parametros
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
from src.resultado.constructores.bootstrap import (
    boot_correlacion, boot_diferencia, boot_media, boot_mediana, boot_regresion,
)
from src.resultado.constructores.ml import rf_clasificacion, rf_regresion
from src.resultado.constructores.roc import comparar_auc, curva_roc
from src.resultado.constructores.sueltos import (
    mediciones_seriales, meta_analisis, prueba_diagnostica, razones_verosimilitud,
)
from src.resultado.constructores.tamano import (
    poder_t, tam_correlacion, tam_dos_medias, tam_dos_proporciones, tam_una_media,
)
from src.resultado.constructores.supervivencia import kaplan_meier, log_rank, regresion_cox
from src.resultado.constructores.resumen import (
    asimetria_curtosis, descriptivas, esd, grubbs, media_armonica, media_geometrica,
    media_recortada, percentiles, shapiro_wilk, tukey,
)
from src.resultado.modelo import Resultado

plt.rcParams.update({
    'figure.facecolor': 'white', 'axes.facecolor': '#fafbfd',
    'axes.edgecolor': '#d8dbe3', 'axes.grid': True,
    'grid.alpha': 0.25, 'grid.color': '#d8dbe3',
    'font.size': 11, 'axes.titlesize': 13,
})




class AnalysisMethodsMixin:
    """Métodos de cálculo+render de cada análisis (mixin de AnalysisPanel)."""

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
        """Variable 1 = efecto de cada estudio, Variable 2 = su error estándar."""
        return meta_analisis(self.data, effect_col, se_col,
                             getattr(self, "opciones_metodo", None))

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

    # --- Bootstrap: src/resultado/constructores/bootstrap.py ---
    def _boot_mean(self, col):
        return boot_media(self.data, col, getattr(self, "opciones_metodo", None))

    def _boot_median(self, col):
        return boot_mediana(self.data, col, getattr(self, "opciones_metodo", None))

    def _boot_diff(self, c1, c2):
        return boot_diferencia(self.data, c1, c2, getattr(self, "opciones_metodo", None))

    def _boot_corr(self, c1, c2):
        return boot_correlacion(self.data, c1, c2, getattr(self, "opciones_metodo", None))

    def _boot_reg(self, c1, c2):
        """Variable 1 = X, Variable 2 = Y."""
        return boot_regresion(self.data, c1, c2, getattr(self, "opciones_metodo", None))

    # --- Machine learning: src/resultado/constructores/ml.py ---
    def _rf_class(self, target_col):
        """Variable 1 = la clase; predictoras = las tildadas."""
        predictoras, del_dialogo = self._columnas_multi(excluir=(target_col,))
        return self._con_nota_columnas(rf_clasificacion(self.data, target_col, predictoras),
                                       predictoras, del_dialogo)

    def _rf_regress(self, target_col):
        """Variable 1 = la respuesta; predictoras = las tildadas."""
        predictoras, del_dialogo = self._columnas_multi(excluir=(target_col,))
        return self._con_nota_columnas(rf_regresion(self.data, target_col, predictoras),
                                       predictoras, del_dialogo)

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
        """Variable 1 = resultado de la prueba, Variable 2 = estándar de oro."""
        try:
            prevalencia = self._param("Diagnostic test", "prevalencia")
        except ValueError as e:
            return f"<b>Error:</b> {e}"
        return prueba_diagnostica(self.data, c1, c2, {"prevalencia": prevalencia})

    def _lr(self, c1, c2):
        """Variable 1 = resultado de la prueba, Variable 2 = estándar de oro."""
        try:
            pretest = self._param("Likelihood Ratios", "pretest")
        except ValueError as e:
            return f"<b>Error:</b> {e}"
        return razones_verosimilitud(self.data, c1, c2, {"pretest": pretest})

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
        """Una columna por tiempo (en orden), una fila por sujeto."""
        cols, del_dialogo = self._columnas_multi()
        return self._con_nota_columnas(mediciones_seriales(self.data, cols), cols,
                                       del_dialogo, "tiempos")

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
            for clave in ("sesgo_permitido", "tea", "lambda", "sigma_r", "sigma_wl",
                          "n_muestras", "valor_asignado", "u", "k", "n_lab"):
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
