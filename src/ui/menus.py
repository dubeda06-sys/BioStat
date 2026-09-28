"""Estructura de la barra de menus, al estilo MedCalc.

Los 78 analisis viven en un solo combo dentro del panel Analisis. Buscarlos ahi
obliga a recorrer una lista plana; MedCalc los agrupa por familia estadistica y
por eso se encuentran sin saber el nombre exacto de la rutina. Esta tabla es esa
agrupacion.

Cada entrada es `(etiqueta_visible, texto_del_combo)`:

- la **etiqueta** es lo que lee el usuario, con acentos y nombre corriente;
- el **texto del combo** tiene que coincidir *exacto* con la clave de
  `ANALYSIS_HELP` (o de `GRAPH_HELP`), porque el menu selecciona el
  item por texto. Si no coincide, la accion no hace nada en silencio.

`tests/test_menus.py` verifica las dos direcciones: que ningun menu apunte a un
analisis inexistente y que ningun analisis quede sin entrada de menu.
"""

# Menu "Estadisticas": (submenu, [(etiqueta, texto_del_combo), ...])
MENU_ESTADISTICAS = [
    ("Resumen y distribución", [
        ("Estadísticas descriptivas", "Estadisticas descriptivas"),
        ("Asimetría y curtosis", "Asimetria y curtosis"),
        ("Tabla de percentiles", "Tabla de percentiles"),
        ("Media recortada", "Media recortada"),
        ("Media geométrica", "Media geometrica"),
        ("Media armónica", "Media armonica"),
        ("Prueba de normalidad (Shapiro-Wilk)", "Shapiro-Wilk"),
        ("Valores atípicos - Grubbs", "Outliers (Grubbs)"),
        ("Valores atípicos - Tukey (IQR)", "Outliers (Tukey)"),
        ("Valores atípicos - ESD generalizado", "Outliers (ESD)"),
    ]),
    ("Correlación", [
        ("Correlación de Pearson", "Correlacion de Pearson"),
        ("Correlación de Spearman", "Correlacion de Spearman"),
        ("Correlación parcial", "Correlacion parcial"),
    ]),
    ("Regresión", [
        ("Regresión lineal", "Regresion lineal"),
        ("Regresión múltiple", "Regresion multiple"),
        ("Regresión logística", "Regresion logistica"),
        ("Regresión probit", "Probit regression"),
    ]),
    ("Comparación de medias", [
        ("t de Student - 1 muestra", "t-test 1 muestra"),
        ("t de Student - muestras pareadas", "t-test pareado"),
        ("t de Student - muestras independientes", "t-test independiente"),
        ("Comparar 2 medias (resumidas)", "Comparar 2 medias"),
        ("Razón de varianzas (F)", "F-test (varianzas)"),
    ]),
    ("ANOVA", [
        ("ANOVA de una vía", "ANOVA una via"),
        ("ANOVA de una vía (core)", "ANOVA una via (core)"),
        ("ANOVA de dos vías", "ANOVA dos vias"),
        ("ANCOVA", "ANCOVA"),
        ("Medidas repetidas", "Medidas repetidas"),
    ]),
    ("Pruebas no paramétricas", [
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
        ("Coeficiente de correlación intraclase (ICC)", "ICC"),
        ("Alfa de Cronbach", "Cronbach alfa"),
        ("CV a partir de duplicados", "CV duplicatas"),
    ]),
    ("Comparación de métodos", [
        ("Validar un método (asistente EP09c + EP15)", "Validar un método"),
        ("Bland-Altman", "Bland-Altman"),
        ("Bland-Altman múltiple", "Bland-Altman múltiple"),
        ("Regresión de Passing-Bablok", "Passing-Bablok"),
        ("Regresión de Deming", "Deming regression"),
        ("Precisión y veracidad (EP15)", "Precisión EP15"),
        ("Mountain plot", "Mountain plot"),
        ("Gráfico de Youden", "Youden plot"),
        ("Gráfico polar", "Polar plot"),
        ("Gráfico de cascada", "Waterfall chart"),
    ]),
    ("Curvas ROC", [
        ("Curva ROC", "Curva ROC"),
        ("Comparar 2 curvas ROC (AUC)", "Comparar 2 AUC"),
    ]),
    ("Análisis de supervivencia", [
        ("Kaplan-Meier", "Kaplan-Meier"),
        ("Log-rank", "Log-rank test"),
        ("Regresión de Cox", "Cox regression"),
    ]),
    ("Valores de referencia", [
        ("Intervalos de referencia", "Intervalos de referencia"),
        ("Intervalos por edad", "Edad-relacionada"),
    ]),
    ("Tamaño de muestra y poder", [
        ("Tamaño muestral - 1 media", "Tamano muestral (1 media)"),
        ("Tamaño muestral - 2 medias", "Tamano muestral (2 medias)"),
        ("Tamaño muestral - 2 proporciones", "Tamano muestral (2 proporciones)"),
        ("Tamaño muestral - correlación", "Tamaño muestral (correlacion)"),
        ("Poder estadístico", "Poder estadistico"),
    ]),
    ("Remuestreo (bootstrap)", [
        ("Bootstrap de la media", "Bootstrap (media)"),
        ("Bootstrap de la mediana", "Bootstrap (mediana)"),
        ("Bootstrap de la diferencia", "Bootstrap (diferencia)"),
        ("Bootstrap de la correlación", "Bootstrap (correlacion)"),
        ("Bootstrap de la regresión", "Bootstrap (regresion)"),
    ]),
    ("Machine learning", [
        ("Random Forest - clasificación", "Random Forest (clasificacion)"),
        ("Random Forest - regresión", "Random Forest (regresion)"),
    ]),
]

# Analisis que no pertenecen a ninguna familia: van sueltos al pie del menu.
ESTADISTICAS_SUELTAS = [
    ("Meta-análisis", "Meta-analisis"),
    ("Mediciones seriales", "Mediciones seriales"),
]

# Menu "Pruebas diagnosticas" (el menu "Tests" de MedCalc).
MENU_PRUEBAS = [
    ("Evaluación de una prueba diagnóstica", "Diagnostic test"),
    ("Razones de verosimilitud", "Likelihood Ratios"),
]

# Menu "Graficos": claves de GRAPH_HELP (panel Graficos).
MENU_GRAFICOS = [
    ("Histograma", "Histograma"),
    ("Diagrama de caja", "Diagrama de caja"),
    ("Diagrama de dispersión", "Dispersion"),
    ("Gráfico de barras", "Barras"),
    ("Serie temporal", "Serie temporal"),
]


def analisis_referenciados():
    """Todos los textos de combo del panel Analisis que apunta algun menu."""
    nombres = [combo for _, items in MENU_ESTADISTICAS for _, combo in items]
    nombres += [combo for _, combo in ESTADISTICAS_SUELTAS]
    nombres += [combo for _, combo in MENU_PRUEBAS]
    return nombres


def nombre_visible(combo_text):
    """El nombre que lee el usuario: la etiqueta del menú, con tildes. La clave
    del combo («Diagnostic test», «Tamano muestral (1 media)») es interna; antes
    era el título del diálogo y de la ventana del informe."""
    for _, items in MENU_ESTADISTICAS:
        for etiqueta, combo in items:
            if combo == combo_text:
                return etiqueta
    for etiqueta, combo in ESTADISTICAS_SUELTAS + MENU_PRUEBAS + MENU_GRAFICOS:
        if combo == combo_text:
            return etiqueta
    return combo_text

