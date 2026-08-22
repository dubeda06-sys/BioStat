"""Estructura de la barra de menus, al estilo MedCalc.

Los 76 analisis viven en un solo combo dentro del panel Analisis. Buscarlos ahi
obliga a recorrer una lista plana; MedCalc los agrupa por familia estadistica y
por eso se encuentran sin saber el nombre exacto de la rutina. Esta tabla es esa
agrupacion.

Cada entrada es `(etiqueta_visible, texto_del_combo)`:

- la **etiqueta** es lo que lee el usuario, con acentos y nombre corriente;
- el **texto del combo** tiene que coincidir *exacto* con la clave de
  `ANALYSIS_HELP` (o de `GRAPH_HELP` / `QC_HELP`), porque el menu selecciona el
  item por texto. Si no coincide, la accion no hace nada en silencio.

`tests/test_menus.py` verifica las dos direcciones: que ningun menu apunte a un
analisis inexistente y que ningun analisis quede sin entrada de menu.
"""

# Menu "Estadisticas": (submenu, [(etiqueta, texto_del_combo), ...])
MENU_ESTADISTICAS = [
    ("Resumen y distribucion", [
        ("Estadisticas descriptivas", "Estadisticas descriptivas"),
        ("Asimetria y curtosis", "Asimetria y curtosis"),
        ("Tabla de percentiles", "Tabla de percentiles"),
        ("Media recortada", "Media recortada"),
        ("Media geometrica", "Media geometrica"),
        ("Media armonica", "Media armonica"),
        ("Prueba de normalidad (Shapiro-Wilk)", "Shapiro-Wilk"),
        ("Valores atipicos - Grubbs", "Outliers (Grubbs)"),
        ("Valores atipicos - Tukey (IQR)", "Outliers (Tukey)"),
        ("Valores atipicos - ESD generalizado", "Outliers (ESD)"),
    ]),
    ("Correlacion", [
        ("Correlacion de Pearson", "Correlacion de Pearson"),
        ("Correlacion de Spearman", "Correlacion de Spearman"),
        ("Correlacion parcial", "Correlacion parcial"),
    ]),
    ("Regresion", [
        ("Regresion lineal", "Regresion lineal"),
        ("Regresion multiple", "Regresion multiple"),
        ("Regresion logistica", "Regresion logistica"),
        ("Regresion probit", "Probit regression"),
    ]),
    ("Comparacion de medias", [
        ("t de Student - 1 muestra", "t-test 1 muestra"),
        ("t de Student - muestras pareadas", "t-test pareado"),
        ("t de Student - muestras independientes", "t-test independiente"),
        ("Comparar 2 medias (resumidas)", "Comparar 2 medias"),
        ("Razon de varianzas (F)", "F-test (varianzas)"),
    ]),
    ("ANOVA", [
        ("ANOVA de una via", "ANOVA una via"),
        ("ANOVA de una via (core)", "ANOVA una via (core)"),
        ("ANOVA de dos vias", "ANOVA dos vias"),
        ("ANCOVA", "ANCOVA"),
        ("Medidas repetidas", "Medidas repetidas"),
    ]),
    ("Pruebas no parametricas", [
        ("Mann-Whitney U", "Mann-Whitney U"),
        ("Wilcoxon pareado", "Wilcoxon pareado"),
        ("Kruskal-Wallis", "Kruskal-Wallis"),
        ("Friedman", "Friedman"),
        ("Prueba de los signos", "Sign test"),
        ("Q de Cochran", "Cochran Q"),
    ]),
    ("Proporciones y tablas de contingencia", [
        ("Chi-cuadrado", "Chi-cuadrado"),
        ("Exacta de Fisher", "Fisher exact"),
        ("McNemar", "McNemar"),
        ("Comparar 2 proporciones", "Comparar 2 proporciones"),
        ("Odds Ratio", "Odds Ratio"),
        ("Riesgo Relativo", "Riesgo Relativo"),
        ("Cochran-Mantel-Haenszel", "CMH test"),
    ]),
    ("Concordancia y confiabilidad", [
        ("Kappa de Cohen", "Kappa"),
        ("Kappa ponderado", "Kappa ponderado"),
        ("Coeficiente de correlacion intraclase (ICC)", "ICC"),
        ("Alfa de Cronbach", "Cronbach alfa"),
        ("CV a partir de duplicados", "CV duplicatas"),
    ]),
    ("Comparacion de metodos", [
        ("Bland-Altman", "Bland-Altman"),
        ("Bland-Altman múltiple", "Bland-Altman múltiple"),
        ("Regresion de Passing-Bablok", "Passing-Bablok"),
        ("Regresion de Deming", "Deming regression"),
        ("Mountain plot", "Mountain plot"),
        ("Grafico de Youden", "Youden plot"),
        ("Grafico polar", "Polar plot"),
        ("Grafico de cascada", "Waterfall chart"),
    ]),
    ("Curvas ROC", [
        ("Curva ROC", "Curva ROC"),
        ("Comparar 2 curvas ROC (AUC)", "Comparar 2 AUC"),
    ]),
    ("Analisis de supervivencia", [
        ("Kaplan-Meier", "Kaplan-Meier"),
        ("Log-rank", "Log-rank test"),
        ("Regresion de Cox", "Cox regression"),
    ]),
    ("Valores de referencia", [
        ("Intervalos de referencia", "Intervalos de referencia"),
        ("Intervalos por edad", "Edad-relacionada"),
    ]),
    ("Tamano de muestra y poder", [
        ("Tamano muestral - 1 media", "Tamano muestral (1 media)"),
        ("Tamano muestral - 2 medias", "Tamano muestral (2 medias)"),
        ("Tamano muestral - 2 proporciones", "Tamano muestral (2 proporciones)"),
        ("Tamaño muestral - correlacion", "Tamaño muestral (correlacion)"),
        ("Poder estadistico", "Poder estadistico"),
    ]),
    ("Remuestreo (bootstrap)", [
        ("Bootstrap de la media", "Bootstrap (media)"),
        ("Bootstrap de la mediana", "Bootstrap (mediana)"),
        ("Bootstrap de la diferencia", "Bootstrap (diferencia)"),
        ("Bootstrap de la correlacion", "Bootstrap (correlacion)"),
        ("Bootstrap de la regresion", "Bootstrap (regresion)"),
    ]),
    ("Machine learning", [
        ("Random Forest - clasificacion", "Random Forest (clasificacion)"),
        ("Random Forest - regresion", "Random Forest (regresion)"),
    ]),
]

# Analisis que no pertenecen a ninguna familia: van sueltos al pie del menu.
ESTADISTICAS_SUELTAS = [
    ("Meta-analisis", "Meta-analisis"),
    ("Mediciones seriales", "Mediciones seriales"),
]

# Menu "Pruebas diagnosticas" (el menu "Tests" de MedCalc).
MENU_PRUEBAS = [
    ("Evaluacion de una prueba diagnostica", "Diagnostic test"),
    ("Razones de verosimilitud", "Likelihood Ratios"),
]

# Menu "Graficos": claves de GRAPH_HELP (panel Graficos).
MENU_GRAFICOS = [
    ("Histograma", "Histograma"),
    ("Diagrama de caja", "Diagrama de caja"),
    ("Diagrama de dispersion", "Dispersion"),
    ("Grafico de barras", "Barras"),
    ("Serie temporal", "Serie temporal"),
]

# Menu "Control de calidad": claves de QC_HELP (panel Control de Calidad).
MENU_QC = [
    ("Estadisticas de control", "Estadisticas"),
    ("Analisis de tendencias", "Tendencias"),
]


def analisis_referenciados():
    """Todos los textos de combo del panel Analisis que apunta algun menu."""
    nombres = [combo for _, items in MENU_ESTADISTICAS for _, combo in items]
    nombres += [combo for _, combo in ESTADISTICAS_SUELTAS]
    nombres += [combo for _, combo in MENU_PRUEBAS]
    return nombres
