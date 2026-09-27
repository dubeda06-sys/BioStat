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
"""
from src.resultado.constructores.comparacion import (
    bland_altman, bland_altman_multiple, cv_duplicados, deming, icc, passing_bablok,
)
from src.resultado.constructores.correlacion import parcial, pearson, spearman
from src.resultado.constructores.medias import (
    comparar_medias, f_varianzas, t_independiente, t_pareada, t_una_muestra,
)
from src.resultado.constructores.precision import precision_ep15
from src.resultado.constructores.regresion import (
    probit, regresion_lineal, regresion_logistica, regresion_multiple,
)
from src.resultado.constructores.resumen import (
    asimetria_curtosis, descriptivas, esd, grubbs, media_armonica, media_geometrica,
    media_recortada, percentiles, shapiro_wilk, tukey,
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
    # Comparación de métodos
    "bland_altman": bland_altman,
    "passing_bablok": passing_bablok,
    "deming": deming,
    "cv_duplicados": cv_duplicados,
    "icc": icc,
    "bland_altman_multiple": bland_altman_multiple,
    "precision_ep15": precision_ep15,
    "validar_metodo": validar_metodo,
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

from src.resultado.constructores.medias import EJEMPLOS  # noqa: E402

__all__ = ["CONSTRUCTORES", "EJEMPLOS", "FIRMAS", *sorted(CONSTRUCTORES)]
