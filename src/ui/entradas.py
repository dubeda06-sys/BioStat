"""De lo elegido en el diálogo a cada constructor: la entrada de los 78 análisis.

Reemplaza al mixin `analysis_methods.py` (paso 5 del plan de `Resultado`, 27
sep). Eran 78 métodos de una o dos líneas que leían el diálogo y llamaban al
constructor. Ahora es una tabla, nombre del combo → cómo se arman los
argumentos, y una sola función, `correr`. No importa Qt: se prueba sin ventana.

Todo sale como `Resultado`. Un parámetro del diálogo mal escrito también: es
un rechazo con el motivo, no un HTML armado a mano.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

from src.resultado.constructores import (
    bland_altman, bland_altman_multiple, cv_duplicados, deming, icc, passing_bablok,
    precision_ep15, validar_metodo,
)
from src.resultado.constructores.anova import (
    ancova, anova_dos_vias, anova_una_via, medidas_repetidas,
)
from src.resultado.constructores.bootstrap import (
    boot_correlacion, boot_diferencia, boot_media, boot_mediana, boot_regresion,
)
from src.resultado.constructores.concordancia import cronbach, kappa, kappa_ponderado
from src.resultado.constructores.correlacion import parcial, pearson, spearman
from src.resultado.constructores.graficos import cascada, mountain, polar, youden
from src.resultado.constructores.medias import (
    comparar_medias, f_varianzas, t_independiente, t_pareada, t_una_muestra,
)
from src.resultado.constructores.ml import rf_clasificacion, rf_regresion
from src.resultado.constructores.noparametricas import (
    cochran, friedman, kruskal, mann_whitney, signos, wilcoxon,
)
from src.resultado.constructores.referencia import intervalo_referencia, intervalos_por_edad
from src.resultado.constructores.regresion import (
    probit, regresion_lineal, regresion_logistica, regresion_multiple,
)
from src.resultado.constructores.resumen import (
    asimetria_curtosis, descriptivas, esd, grubbs, media_armonica, media_geometrica,
    media_recortada, percentiles, shapiro_wilk, tukey,
)
from src.resultado.constructores.roc import comparar_auc, curva_roc
from src.resultado.constructores.sueltos import (
    mediciones_seriales, meta_analisis, prueba_diagnostica, razones_verosimilitud,
)
from src.resultado.constructores.supervivencia import kaplan_meier, log_rank, regresion_cox
from src.resultado.constructores.tablas import (
    chi_cuadrado, cmh, dos_proporciones, fisher, mcnemar, odds_ratio_tabla, riesgo_relativo,
)
from src.resultado.constructores.tamano import (
    poder_t, tam_correlacion, tam_dos_medias, tam_dos_proporciones, tam_una_media,
)
from src.resultado.modelo import Resultado
from src.ui.analysis_specs import parametros as spec_parametros
from src.ui.analysis_specs import variables as spec_variables


@dataclass
class Eleccion:
    """Lo que eligió el usuario: la hoja, las variables del panel y lo del diálogo.

    columnas:   las tildadas en el diálogo (analysis_specs.MULTI). None = no
                hubo diálogo: se usan todas las numéricas y el informe las nombra.
    opciones:   decisiones de método (analysis_specs.OPCIONES).
    parametros: números del diálogo (analysis_specs.PARAMETROS), como texto.
    """
    data: pd.DataFrame
    c1: str | None = None
    c2: str | None = None
    c3: str | None = None
    alpha: float = 0.05
    opciones: dict = field(default_factory=dict)
    columnas: list | None = None
    parametros: dict = field(default_factory=dict)

    def hay(self, columna) -> bool:
        return columna is not None and columna in self.data.columns


class ParametroInvalido(ValueError):
    """Un número del diálogo mal escrito o fuera de rango. Es lo único que
    `correr` convierte en rechazo: un ValueError de un cálculo es un defecto y
    tiene que verse como tal."""


def param(e: Eleccion, analisis: str, clave: str):
    """Parámetro numérico: el del diálogo, o el de ejemplo si no hubo diálogo."""
    spec = {p.clave: p for p in spec_parametros(analisis)}[clave]
    crudo = (e.parametros or {}).get(clave)
    if crudo is None or str(crudo).strip() == "":
        return spec.defecto          # None en los opcionales: «no se declaró»
    try:
        valor = float(str(crudo).strip().replace(",", "."))
    except ValueError:
        raise ParametroInvalido(
            f"«{spec.etiqueta}» tiene que ser un número; se escribió «{crudo}».") from None
    if not spec.minimo <= valor <= spec.maximo:
        raise ParametroInvalido(f"«{spec.etiqueta}» = {valor:g} está fuera de rango "
                                f"({spec.minimo:g} a {spec.maximo:g}).")
    return int(round(valor)) if spec.entero else valor


def columnas_multi(e: Eleccion, excluir=()):
    """Columnas de un análisis que usa una lista (analysis_specs.MULTI).

    Devuelve (columnas, del_dialogo). Desde el diálogo, las tildadas; sin
    diálogo, todas las numéricas de la hoja, y el informe las nombra para que
    se vea si se coló un ID o una edad. Antes se usaban todas en silencio
    (auditoría 2026-09, K2).
    """
    numericas = list(e.data.select_dtypes(include="number").columns)
    if e.columnas is not None:
        return [c for c in e.columnas if c in numericas and c not in excluir], True
    return [c for c in numericas if c not in excluir], False


def con_nota(res, columnas, del_dialogo, que="predictoras", ejemplo="una fecha"):
    """Sin diálogo se usaron todas las numéricas: el informe lo dice."""
    if res.ok and not del_dialogo:
        res.advertencias.append(
            f"Se usaron todas las columnas numéricas de la hoja como {que}: "
            + ", ".join(str(c) for c in columnas) + ". Si alguna no corresponde "
            f"(un número de muestra, {ejemplo}), abrí el análisis desde el menú "
            "Estadísticas y destildala.")
    return res


_EJEMPLO = ("Son los valores de ejemplo. Para calcular con los tuyos, abrí el análisis "
            "desde el menú Estadísticas.")
_EJEMPLO_DIALOGO = ("Son los valores de ejemplo. Para calcular con los tuyos, abrí el "
                    "análisis desde el menú Estadísticas: el diálogo los pide.")


def _de_ejemplo(res, e: Eleccion, texto=_EJEMPLO):
    if res.ok and not e.parametros:
        res.advertencias.append(texto)
    return res


# ---------------- Formas de llamar ----------------

def _una(f):
    return lambda e: f(e.data, e.c1)


def _par(f):
    return lambda e: f(e.data, e.c1, e.c2)


def _par_alfa(f):
    return lambda e: f(e.data, e.c1, e.c2, {"alpha": e.alpha})


def _una_opciones(f):
    return lambda e: f(e.data, e.c1, e.opciones)


def _par_opciones(f):
    return lambda e: f(e.data, e.c1, e.c2, e.opciones)


def _lista(f, que, excluir=None):
    """f(df, [columnas]) con las tildadas, o todas con aviso."""
    def armar(e):
        cols, del_dialogo = columnas_multi(e)
        return con_nota(f(e.data, cols), cols, del_dialogo, que)
    return armar


def _respuesta_y_lista(f, que="predictoras"):
    """f(df, c1, [columnas sin c1]): la respuesta en la Variable 1."""
    def armar(e):
        cols, del_dialogo = columnas_multi(e, excluir=(e.c1,))
        return con_nota(f(e.data, e.c1, cols), cols, del_dialogo, que)
    return armar


def _con_tercera(f, analisis, titulo, motivo):
    """f(df, c1, c2, c3) solo si hay Variable 3; si no, el rechazo dice cuál falta."""
    def armar(e):
        if not e.hay(e.c3):
            return Resultado.rechazo(analisis, titulo, motivo)
        return f(e.data, e.c1, e.c2, e.c3)
    return armar


def _con_parametros(nombre, claves, f, texto=_EJEMPLO):
    """Una calculadora de datos resumen: f(opciones) con los números del diálogo."""
    def armar(e):
        return _de_ejemplo(f({k: param(e, nombre, k) for k in claves}), e, texto)
    return armar


def _calculadora(nombre, f, extra: Callable[[Eleccion], dict] | None = None):
    """Todos los parámetros del análisis, más lo que agregue `extra`."""
    def armar(e):
        opciones = {p.clave: param(e, nombre, p.clave) for p in spec_parametros(nombre)}
        opciones.update(extra(e) if extra else {})
        return _de_ejemplo(f(opciones), e, _EJEMPLO_DIALOGO)
    return armar


# ---------------- Los que necesitan algo propio ----------------

def _t_una(e):
    return t_una_muestra(e.data, e.c1, {"mu": param(e, "t-test 1 muestra", "mu")})


def _roc(e):
    if not e.hay(e.c3):
        return Resultado.rechazo("curva_roc", "Curva ROC",
                                 "Elegí la etiqueta (1 enfermo, 0 sano) en la Variable 3.")
    return curva_roc(e.data, e.c1, e.c3)


def _log_rank(e):
    if not e.hay(e.c3):
        return Resultado.rechazo("log_rank", "Log-rank", "Elegí el grupo en la Variable 3.")
    return log_rank(e.data, e.c1, e.c2, e.c3)


def _deming(e):
    opciones = dict(e.opciones)
    opciones["lambda"] = param(e, "Deming regression", "lambda")
    return deming(e.data, e.c1, e.c2, opciones)


def _diagnostica(e):
    return prueba_diagnostica(e.data, e.c1, e.c2,
                              {"prevalencia": param(e, "Diagnostic test", "prevalencia")})


def _razones(e):
    return razones_verosimilitud(e.data, e.c1, e.c2,
                                 {"pretest": param(e, "Likelihood Ratios", "pretest")})


def _referencia(e):
    return intervalo_referencia(e.data, e.c1, {k: param(e, "Intervalos de referencia", k)
                                               for k in ("inferior", "superior")})


def _edad(e):
    if not (e.hay(e.c1) and e.hay(e.c2)):
        return Resultado.rechazo("intervalos_edad", "Intervalos por edad",
                                 "Elegí la edad en la Variable 1 y el valor en la Variable 2.")
    return intervalos_por_edad(e.data, e.c1, e.c2, e.opciones)


def _cox(e):
    covariables, del_dialogo = columnas_multi(e, excluir=(e.c1, e.c2))
    return con_nota(regresion_cox(e.data, e.c1, e.c2, covariables), covariables,
                    del_dialogo, "covariables")


def _bland_multiple(e):
    if not e.hay(e.c1):
        return Resultado.rechazo("bland_altman_multiple", "Bland-Altman múltiple",
                                 "Elegí el método de referencia en la Variable 1.")
    metodos, del_dialogo = columnas_multi(e, excluir=(e.c1,))
    return con_nota(bland_altman_multiple(e.data, e.c1, metodos), metodos, del_dialogo,
                    "métodos", ejemplo="una edad")


def _validar(e):
    """El asistente B: Variable 1 = método en uso, Variable 2 = en prueba.

    Las corridas de EP15 solo entran si se tildaron en el diálogo: sin diálogo
    no hay forma de saber cuáles columnas son corridas, y tomarlas todas
    metería los dos métodos como si fueran días.
    """
    corridas, del_dialogo = columnas_multi(e, excluir=(e.c1, e.c2))
    opciones = dict(e.opciones)
    for clave in ("sesgo_permitido", "tea", "lambda", "sigma_r", "sigma_wl", "n_muestras",
                  "valor_asignado", "u", "k", "n_lab"):
        opciones[clave] = param(e, "Validar un método", clave)
    opciones["niveles"] = [v for v in (param(e, "Validar un método", f"nivel_{i}")
                                       for i in (1, 2, 3)) if v is not None]
    opciones["corridas"] = corridas if del_dialogo else []
    return validar_metodo(e.data, e.c1, e.c2, opciones)


def _ep15(e):
    """EP15-A3: cada columna tildada es una corrida."""
    corridas, del_dialogo = columnas_multi(e)
    opciones = dict(e.opciones)
    for clave in ("sigma_r", "sigma_wl", "n_muestras", "valor_asignado", "u", "k", "n_lab"):
        opciones[clave] = param(e, "Precisión EP15", clave)
    res = precision_ep15(e.data, corridas, opciones)
    if res.ok and not del_dialogo:
        res.advertencias.append(
            "Se tomaron todas las columnas numéricas de la hoja como corridas: "
            + ", ".join(str(c) for c in corridas) + ". Para elegir las corridas y cargar "
            "lo que declara el fabricante, abrí el análisis desde el menú Estadísticas.")
    return res


# ---------------- La tabla: nombre del combo → (id del análisis, cómo armarlo) ----------------

ENTRADAS: dict[str, tuple[str, Callable[[Eleccion], Resultado]]] = {
    # Resumen y distribución
    "Estadisticas descriptivas": ("descriptivas", _una(descriptivas)),
    "Asimetria y curtosis": ("asimetria_curtosis", _una(asimetria_curtosis)),
    "Tabla de percentiles": ("percentiles", _una(percentiles)),
    "Media recortada": ("media_recortada", _una(media_recortada)),
    "Media geometrica": ("media_geometrica", _una(media_geometrica)),
    "Media armonica": ("media_armonica", _una(media_armonica)),
    "Shapiro-Wilk": ("shapiro_wilk", _una(shapiro_wilk)),
    "Outliers (Grubbs)": ("grubbs", _una(grubbs)),
    "Outliers (Tukey)": ("tukey", _una(tukey)),
    "Outliers (ESD)": ("esd", _una(esd)),
    # Correlación y regresión
    "Correlacion de Pearson": ("pearson", _par(pearson)),
    "Correlacion de Spearman": ("spearman", _par(spearman)),
    "Correlacion parcial": ("parcial", _con_tercera(
        parcial, "parcial", "Correlación parcial",
        "Elegí en la Variable 3 la variable que se quiere controlar.")),
    "Regresion lineal": ("regresion_lineal", _par(regresion_lineal)),
    "Regresion multiple": ("regresion_multiple", _respuesta_y_lista(regresion_multiple)),
    "Regresion logistica": ("regresion_logistica", _respuesta_y_lista(regresion_logistica)),
    "Probit regression": ("probit", _par_opciones(probit)),
    # Comparación de medias
    "t-test 1 muestra": ("t_una_muestra", _t_una),
    "t-test pareado": ("t_pareada", _par_alfa(t_pareada)),
    "t-test independiente": ("t_independiente", _par_alfa(t_independiente)),
    "Comparar 2 medias": ("comparar_medias", _con_parametros(
        "Comparar 2 medias", ("m1", "de1", "n1", "m2", "de2", "n2"), comparar_medias)),
    "F-test (varianzas)": ("f_varianzas", _par(f_varianzas)),
    # ANOVA
    "ANOVA una via": ("anova_una_via", _par_alfa(anova_una_via)),
    "ANOVA una via (core)": ("anova_una_via", _par_alfa(anova_una_via)),
    "ANOVA dos vias": ("anova_dos_vias", _con_tercera(
        anova_dos_vias, "anova_dos_vias", "ANOVA de dos vías",
        "Elegí el segundo factor en la Variable 3.")),
    "ANCOVA": ("ancova", _con_tercera(
        ancova, "ancova", "ANCOVA", "Elegí la covariable en la Variable 3.")),
    "Medidas repetidas": ("medidas_repetidas", _lista(medidas_repetidas, "tiempos")),
    # No paramétricas
    "Mann-Whitney U": ("mann_whitney", _par(mann_whitney)),
    "Wilcoxon pareado": ("wilcoxon", _par(wilcoxon)),
    "Kruskal-Wallis": ("kruskal", _par(kruskal)),
    "Friedman": ("friedman", _lista(friedman, "condiciones")),
    "Sign test": ("signos", _par(signos)),
    "Cochran Q": ("cochran", _lista(cochran, "tratamientos")),
    # Proporciones y tablas
    "Chi-cuadrado": ("chi_cuadrado", _par(chi_cuadrado)),
    "Fisher exact": ("fisher", _par(fisher)),
    "McNemar": ("mcnemar", _par(mcnemar)),
    "Comparar 2 proporciones": ("dos_proporciones", _con_parametros(
        "Comparar 2 proporciones", ("x1", "n1", "x2", "n2"), dos_proporciones)),
    "Odds Ratio": ("odds_ratio", _par(odds_ratio_tabla)),
    "Riesgo Relativo": ("riesgo_relativo", _par(riesgo_relativo)),
    "CMH test": ("cmh", _con_tercera(
        cmh, "cmh", "Cochran-Mantel-Haenszel", "Elegí el estrato en la Variable 3.")),
    # Concordancia
    "Kappa": ("kappa", _par(kappa)),
    "Kappa ponderado": ("kappa_ponderado", _par_opciones(kappa_ponderado)),
    "Cronbach alfa": ("cronbach", _lista(cronbach, "ítems")),
    # Comparación de métodos
    "Bland-Altman": ("bland_altman", _par_opciones(bland_altman)),
    "Passing-Bablok": ("passing_bablok", _par(passing_bablok)),
    "Deming regression": ("deming", _deming),
    "CV duplicatas": ("cv_duplicados", _par(cv_duplicados)),
    "ICC": ("icc", _par(icc)),
    "Bland-Altman múltiple": ("bland_altman_multiple", _bland_multiple),
    "Precisión EP15": ("precision_ep15", _ep15),
    "Validar un método": ("validar_metodo", _validar),
    "Mountain plot": ("mountain", _par(mountain)),
    "Youden plot": ("youden", _par(youden)),
    "Polar plot": ("polar", _lista(polar, "ejes")),
    "Waterfall chart": ("cascada", _una(cascada)),
    # Curvas ROC y pruebas diagnósticas
    "Curva ROC": ("curva_roc", _roc),
    "Comparar 2 AUC": ("comparar_auc", _con_parametros(
        "Comparar 2 AUC", ("auc1", "ee1", "n1", "auc2", "ee2", "n2"), comparar_auc)),
    "Diagnostic test": ("prueba_diagnostica", _diagnostica),
    "Likelihood Ratios": ("razones_verosimilitud", _razones),
    # Supervivencia
    "Kaplan-Meier": ("kaplan_meier", _par(kaplan_meier)),
    "Log-rank test": ("log_rank", _log_rank),
    "Cox regression": ("regresion_cox", _cox),
    # Valores de referencia
    "Intervalos de referencia": ("intervalo_referencia", _referencia),
    "Edad-relacionada": ("intervalos_edad", _edad),
    # Tamaño de muestra y poder
    "Tamano muestral (1 media)": ("tam_una_media", _calculadora(
        "Tamano muestral (1 media)", tam_una_media)),
    "Tamano muestral (2 medias)": ("tam_dos_medias", _calculadora(
        "Tamano muestral (2 medias)", tam_dos_medias)),
    "Tamano muestral (2 proporciones)": ("tam_dos_proporciones", _calculadora(
        "Tamano muestral (2 proporciones)", tam_dos_proporciones)),
    "Tamaño muestral (correlacion)": ("tam_correlacion", _calculadora(
        "Tamaño muestral (correlacion)", tam_correlacion)),
    "Poder estadistico": ("poder_t", _calculadora(
        "Poder estadistico", poder_t, lambda e: {"diseno": e.opciones.get("diseno", "una")})),
    # Bootstrap
    "Bootstrap (media)": ("boot_media", _una_opciones(boot_media)),
    "Bootstrap (mediana)": ("boot_mediana", _una_opciones(boot_mediana)),
    "Bootstrap (diferencia)": ("boot_diferencia", _par_opciones(boot_diferencia)),
    "Bootstrap (correlacion)": ("boot_correlacion", _par_opciones(boot_correlacion)),
    "Bootstrap (regresion)": ("boot_regresion", _par_opciones(boot_regresion)),
    # Machine learning
    "Random Forest (clasificacion)": ("rf_clasificacion", _respuesta_y_lista(rf_clasificacion)),
    "Random Forest (regresion)": ("rf_regresion", _respuesta_y_lista(rf_regresion)),
    # Sueltos
    "Meta-analisis": ("meta_analisis", _par_opciones(meta_analisis)),
    "Mediciones seriales": ("mediciones_seriales", _lista(mediciones_seriales, "tiempos")),
}


def correr(nombre: str, e: Eleccion) -> Resultado:
    """El análisis `nombre` (texto del combo) con lo elegido en `e`."""
    analisis, armar = ENTRADAS[nombre]
    # Una columna contra sí misma no es un análisis: un Bland-Altman de A
    # contra A daba «concordancia casi perfecta» con todo en cero.
    usadas = [getattr(e, v) for v in spec_variables(nombre) if v in ("c1", "c2", "c3")]
    usadas = [c for c in usadas if c is not None]
    repetidas = [c for i, c in enumerate(usadas) if c in usadas[:i]]
    if repetidas:
        return Resultado.rechazo(
            analisis, nombre,
            f"La columna «{repetidas[0]}» está elegida dos veces: cada variable del "
            "análisis tiene que ser una columna distinta.")
    try:
        return armar(e)
    except ParametroInvalido as err:
        return Resultado.rechazo(analisis, nombre, str(err))
