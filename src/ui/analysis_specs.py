"""Que variables pide cada analisis.

MedCalc no tiene un panel con tres combos siempre visibles: cada procedimiento
abre su propio cuadro de dialogo y ahi pide exactamente lo que necesita. Para
armar ese dialogo hace falta saber, por analisis, cuales de las tres variables
y el alfa entran en juego.

Esta tabla sale de leer el `dispatch` de `AnalysisPanel._run` — es la unica
fuente de verdad de que recibe cada rutina. `tests/test_analysis_specs.py`
vuelve a leer ese dispatch y compara: si alguien agrega un analisis o le cambia
los argumentos y no toca esta tabla, el test lo cachea.

Los 29 analisis con tupla vacia no toman columnas sueltas: trabajan sobre toda
la hoja (tablas de contingencia, ANOVA de varias columnas) o piden sus datos en
campos propios (tamano de muestra). El dialogo se los avisa al usuario en vez de
mostrarle selectores que no hacen nada.
"""

# analisis -> variables que consume, en orden: "c1", "c2", "c3", "alpha"
VARIABLES = {
    'Estadisticas descriptivas': ('c1',),
    't-test pareado': ('c1', 'c2', 'alpha'),
    't-test independiente': ('c1', 'c2', 'alpha'),
    'ANOVA una via': ('alpha',),
    'Correlacion de Pearson': ('c1', 'c2'),
    'Correlacion de Spearman': ('c1', 'c2'),
    'Shapiro-Wilk': ('c1',),
    'Curva ROC': ('c1', 'c3'),
    'Bland-Altman': ('c1', 'c2'),
    'Passing-Bablok': ('c1', 'c2'),
    'Kaplan-Meier': ('c1', 'c2'),
    'Log-rank test': ('c1', 'c2', 'c3'),
    'Meta-analisis': ('c1', 'c2'),
    'Tamano muestral (1 media)': (),
    'Tamano muestral (2 medias)': (),
    'Tamano muestral (2 proporciones)': (),
    'Poder estadistico': (),
    'Bootstrap (media)': ('c1',),
    'Bootstrap (diferencia)': ('c1', 'c2'),
    'Bootstrap (correlacion)': ('c1', 'c2'),
    'Random Forest (clasificacion)': ('c1', 'c2'),
    'Random Forest (regresion)': ('c1', 'c2'),
    'Mann-Whitney U': ('c1', 'c2'),
    'Wilcoxon pareado': ('c1', 'c2'),
    'Chi-cuadrado': (),
    'Fisher exact': (),
    'McNemar': (),
    'Kruskal-Wallis': (),
    'Friedman': (),
    'F-test (varianzas)': ('c1', 'c2'),
    'Kappa': (),
    'ICC': ('c1', 'c2'),
    'Cronbach alfa': (),
    'Regresion lineal': ('c1', 'c2'),
    'Regresion multiple': (),
    'Regresion logistica': (),
    'Odds Ratio': (),
    'Riesgo Relativo': (),
    'Diagnostic test': (),
    'Outliers (Grubbs)': ('c1',),
    'Outliers (Tukey)': ('c1',),
    'Intervalos de referencia': ('c1',),
    'Asimetria y curtosis': ('c1',),
    'Media recortada': ('c1',),
    'Correlacion parcial': ('c1', 'c2', 'c3'),
    'Media geometrica': ('c1',),
    'Media armonica': ('c1',),
    't-test 1 muestra': ('c1',),
    'ANOVA una via (core)': (),
    'Sign test': ('c1', 'c2'),
    'Cochran Q': (),
    'Kappa ponderado': (),
    'Deming regression': ('c1', 'c2'),
    'CV duplicatas': ('c1', 'c2'),
    'Likelihood Ratios': (),
    'Comparar 2 medias': (),
    'Comparar 2 proporciones': (),
    'Comparar 2 AUC': (),
    'Tabla de percentiles': ('c1',),
    'Edad-relacionada': (),
    'Outliers (ESD)': ('c1',),
    'Bootstrap (mediana)': ('c1',),
    'Bootstrap (regresion)': ('c1', 'c2'),
    'Tamaño muestral (correlacion)': ('c1', 'c2'),
    'ANOVA dos vias': ('c1', 'c2', 'c3'),
    'ANCOVA': ('c1', 'c2', 'c3'),
    'Medidas repetidas': (),
    'Cox regression': ('c1', 'c2'),
    'Probit regression': ('c1', 'c2'),
    'CMH test': (),
    'Mediciones seriales': (),
    'Youden plot': ('c1', 'c3'),
    'Polar plot': (),
    'Waterfall chart': ('c1',),
    'Mountain plot': ('c1',),
    'Bland-Altman múltiple': (),
}


def variables(analisis):
    """Variables que pide un analisis. Tupla vacia = trabaja sobre toda la hoja."""
    return VARIABLES.get(analisis, ())


def usa(analisis, variable):
    return variable in VARIABLES.get(analisis, ())


def sobre_toda_la_hoja(analisis):
    """True si el analisis no toma columnas sueltas."""
    return not [v for v in VARIABLES.get(analisis, ()) if v != "alpha"]
