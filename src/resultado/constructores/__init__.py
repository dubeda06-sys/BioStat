"""Un constructor por análisis: de la hoja a un `Resultado`, sin Qt.

Cada constructor recibe el DataFrame, las columnas y las opciones de método, y
devuelve un `Resultado`. No dibuja: deja `Figura`s que se dibujan al mostrarse.
El panel los llama desde su `dispatch`; los tests, directamente.

`CONSTRUCTORES` es la lista de los ya migrados. Los tests de contrato la
recorren entera: todo lo que entra acá tiene que tener ficha, no decir
«significativo» y no imprimir un p como cero. `FIRMAS` dice cómo se llama cada
uno, para que el contrato pueda correrlos a todos sin saber de cada familia:

    "una":   f(df, columna)
    "par":   f(df, columna1, columna2)
    "lista": f(df, [columnas])
    "trio":  f(df, columna1, columna2, columna3)
    "respuesta_binaria": f(df, respuesta_0_1, [predictoras])
    "dosis_respuesta":   f(df, dosis, respuesta_0_1)
    "calculadora":       f(opciones), sin hoja; ejemplo en EJEMPLOS
    "respuesta_grupo":   f(df, respuesta, grupo)  (formato largo)
    "respuesta_dos_factores":     f(df, respuesta, factor_a, factor_b)
    "respuesta_grupo_covariable": f(df, respuesta, grupo, covariable)
    "lista_tres":    f(df, [3 columnas o más])
    "lista_binaria": f(df, [columnas 0/1])
    "binarias":      f(df, binaria1, binaria2)
    "binarias_estrato": f(df, exposicion, evento, estrato)
    "tiempo_evento":           f(df, tiempo, evento_0_1)
    "tiempo_evento_grupo":     f(df, tiempo, evento_0_1, grupo)
    "tiempo_evento_covariables": f(df, tiempo, evento_0_1, [covariables])
"""
from src.resultado.constructores.anova import (
    ancova, anova_dos_vias, anova_una_via, medidas_repetidas,
)
from src.resultado.constructores.bootstrap import (
    boot_correlacion, boot_diferencia, boot_media, boot_mediana, boot_regresion,
)
from src.resultado.constructores.comparacion import (
    bland_altman, bland_altman_multiple, cv_duplicados, deming, icc, passing_bablok,
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
from src.resultado.constructores.precision import precision_ep15
from src.resultado.constructores.referencia import intervalo_referencia, intervalos_por_edad
from src.resultado.constructores.regresion import (
    probit, regresion_lineal, regresion_logistica, regresion_multiple,
)
from src.resultado.constructores.roc import comparar_auc, curva_roc
from src.resultado.constructores.resumen import (
    asimetria_curtosis, descriptivas, esd, grubbs, media_armonica, media_geometrica,
    media_recortada, percentiles, shapiro_wilk, tukey,
)
from src.resultado.constructores.supervivencia import kaplan_meier, log_rank, regresion_cox
from src.resultado.constructores.tamano import (
    poder_t, tam_correlacion, tam_dos_medias, tam_dos_proporciones, tam_una_media,
)
from src.resultado.constructores.tablas import (
    chi_cuadrado, cmh, dos_proporciones, fisher, mcnemar, odds_ratio_tabla,
    riesgo_relativo,
)
from src.resultado.constructores.validacion import validar_metodo

CONSTRUCTORES = {
    # Resumen y distribución
    "descriptivas": descriptivas,
    "asimetria_curtosis": asimetria_curtosis,
    "percentiles": percentiles,
    "media_recortada": media_recortada,
    "media_geometrica": media_geometrica,
    "media_armonica": media_armonica,
    "shapiro_wilk": shapiro_wilk,
    "grubbs": grubbs,
    "tukey": tukey,
    "esd": esd,
    # Correlación
    "pearson": pearson,
    "spearman": spearman,
    "parcial": parcial,
    # Regresión
    "regresion_lineal": regresion_lineal,
    "regresion_multiple": regresion_multiple,
    "regresion_logistica": regresion_logistica,
    "probit": probit,
    # Comparación de medias
    "t_una_muestra": t_una_muestra,
    "t_pareada": t_pareada,
    "t_independiente": t_independiente,
    "comparar_medias": comparar_medias,
    "f_varianzas": f_varianzas,
    # ANOVA
    "anova_una_via": anova_una_via,
    "anova_dos_vias": anova_dos_vias,
    "ancova": ancova,
    "medidas_repetidas": medidas_repetidas,
    # No paramétricas
    "mann_whitney": mann_whitney,
    "wilcoxon": wilcoxon,
    "kruskal": kruskal,
    "friedman": friedman,
    "signos": signos,
    "cochran": cochran,
    # Proporciones y tablas
    "chi_cuadrado": chi_cuadrado,
    "fisher": fisher,
    "mcnemar": mcnemar,
    "dos_proporciones": dos_proporciones,
    "odds_ratio": odds_ratio_tabla,
    "riesgo_relativo": riesgo_relativo,
    "cmh": cmh,
    # Concordancia
    "kappa": kappa,
    "kappa_ponderado": kappa_ponderado,
    "cronbach": cronbach,
    # Comparación de métodos
    "bland_altman": bland_altman,
    "passing_bablok": passing_bablok,
    "deming": deming,
    "cv_duplicados": cv_duplicados,
    "icc": icc,
    "bland_altman_multiple": bland_altman_multiple,
    "precision_ep15": precision_ep15,
    "validar_metodo": validar_metodo,
    "mountain": mountain,
    "youden": youden,
    "polar": polar,
    "cascada": cascada,
    # Curvas ROC
    "curva_roc": curva_roc,
    "comparar_auc": comparar_auc,
    # Supervivencia
    "kaplan_meier": kaplan_meier,
    "log_rank": log_rank,
    "regresion_cox": regresion_cox,
    # Valores de referencia
    "intervalo_referencia": intervalo_referencia,
    "intervalos_edad": intervalos_por_edad,
    # Tamaño de muestra y poder
    "tam_una_media": tam_una_media,
    "tam_dos_medias": tam_dos_medias,
    "tam_dos_proporciones": tam_dos_proporciones,
    "tam_correlacion": tam_correlacion,
    "poder_t": poder_t,
    # Bootstrap
    "boot_media": boot_media,
    "boot_mediana": boot_mediana,
    "boot_diferencia": boot_diferencia,
    "boot_correlacion": boot_correlacion,
    "boot_regresion": boot_regresion,
}

FIRMAS = {nombre: "par" for nombre in CONSTRUCTORES}
FIRMAS.update({n: "una" for n in (
    "descriptivas", "asimetria_curtosis", "percentiles", "media_recortada",
    "media_geometrica", "media_armonica", "shapiro_wilk", "grubbs", "tukey", "esd")})
FIRMAS["precision_ep15"] = "lista"
FIRMAS["parcial"] = "trio"
FIRMAS["regresion_logistica"] = "respuesta_binaria"
FIRMAS["probit"] = "dosis_respuesta"
FIRMAS["t_una_muestra"] = "una"
FIRMAS["comparar_medias"] = "calculadora"
FIRMAS["anova_una_via"] = "respuesta_grupo"
FIRMAS["anova_dos_vias"] = "respuesta_dos_factores"
FIRMAS["ancova"] = "respuesta_grupo_covariable"
FIRMAS["medidas_repetidas"] = "lista"
FIRMAS["kruskal"] = "respuesta_grupo"
FIRMAS["friedman"] = "lista_tres"
FIRMAS["cochran"] = "lista_binaria"
for _n in ("chi_cuadrado", "fisher", "mcnemar", "odds_ratio", "riesgo_relativo"):
    FIRMAS[_n] = "binarias"
FIRMAS["dos_proporciones"] = "calculadora"
FIRMAS["cmh"] = "binarias_estrato"
FIRMAS["kappa"] = FIRMAS["kappa_ponderado"] = "binarias"
FIRMAS["cronbach"] = "lista_tres"
FIRMAS["polar"] = "lista_tres"
FIRMAS["cascada"] = "una"
FIRMAS["curva_roc"] = "dosis_respuesta"
FIRMAS["comparar_auc"] = "calculadora"
FIRMAS["kaplan_meier"] = "tiempo_evento"
FIRMAS["log_rank"] = "tiempo_evento_grupo"
FIRMAS["regresion_cox"] = "tiempo_evento_covariables"
FIRMAS["intervalo_referencia"] = "una"
for _n in ("tam_una_media", "tam_dos_medias", "tam_dos_proporciones", "tam_correlacion",
           "poder_t"):
    FIRMAS[_n] = "calculadora"
FIRMAS["boot_media"] = FIRMAS["boot_mediana"] = "una"

from src.resultado.constructores.medias import EJEMPLOS  # noqa: E402
from src.resultado.constructores.tablas import EJEMPLOS as _EJ_TABLAS  # noqa: E402
from src.resultado.constructores.roc import EJEMPLOS as _EJ_ROC  # noqa: E402
from src.resultado.constructores.tamano import EJEMPLOS as _EJ_TAMANO  # noqa: E402

EJEMPLOS = {**EJEMPLOS, **_EJ_TABLAS, **_EJ_ROC, **_EJ_TAMANO}

__all__ = ["CONSTRUCTORES", "EJEMPLOS", "FIRMAS", *sorted(CONSTRUCTORES)]
