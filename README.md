# BioStat

Software estadístico para laboratorio clínico. Inspirado en MedCalc.

## Instalación

```bash
pip install -r requirements.txt
python main.py
```

## Compilar ejecutable

```bash
pip install pyinstaller
python build_exe.py
```

El ejecutable `BioStat.exe` se copiará automáticamente al Escritorio.

## Funcionalidades

### Estadísticas Descriptivas
- Media, mediana, DE, varianza, CV%, sesgo, curtosis
- Media geométrica y armónica
- Media recortada (robusta)
- Asimetría y curtosis (tests formales)
- Tabla de percentiles con IC

### Comparación de Grupos
- t-test pareado e independiente
- t-test de 1 muestra
- ANOVA una vía y dos vías
- ANCOVA (con covariable)
- Medidas repetidas (Greenhouse-Geisser)
- Mann-Whitney U, Wilcoxon, Kruskal-Wallis, Friedman
- Sign test
- Comparar 2 medias y 2 proporciones (datos resumen)

### Tablas de Contingencia
- Chi-cuadrado, Fisher exact, McNemar
- Cochran Q
- Cochran-Mantel-Haenszel (CMH)
- F-test (comparar varianzas)

### Correlación y Regresión
- Pearson, Spearman, correlación parcial
- Regresión lineal simple y múltiple
- Regresión logística con odds ratios
- Passing-Bablok, Deming
- Regresión de Cox (supervivencia)
- Regresión Probit

### Análisis de Métodos
- Curva ROC con AUC y umbral óptimo (Youden)
- Bland-Altman (simple y múltiple)
- Concordancia (Kappa, Kappa ponderado, ICC, Cronbach alfa)
- CV de duplicados
- Comparar 2 AUC independientes

### Prueba Diagnóstica
- Sensibilidad, especificidad, PPV, NPV
- Likelihood Ratios (LR+, LR-)
- Odds Ratio y Riesgo Relativo

### Supervivencia
- Kaplan-Meier
- Log-rank test
- Regresión de Cox

### Meta-análisis
- Modelo de efectos fijos y aleatorios
- Forest plot
- Heterogeneidad (I², Q de Cochran)

### Machine Learning
- Random Forest (clasificación y regresión)
- Bootstrap (media, mediana, diferencia, correlación, regresión)

### Control de Calidad
- Levey-Jennings
- Reglas de Westgard (1-3s, 2-2s, 4-1s, 10x)
- Estadísticas de control (media, DE, CV%, z-scores)
- Análisis de tendencias

### Tamaño Muestral
- 1 media, 2 medias, 2 proporciones
- Correlación, poder estadístico

### Detección de Outliers
- Grubbs, Tukey (IQR), ESD generalizado

### Intervalos de Referencia
- Percentiles con IC
- Intervalos edad-relacionados

### Gráficos Especializados
- Youden plot, Polar plot, Waterfall chart, Mountain plot
- Mediciones seriales (resumen por sujeto)

### Normalidad
- Shapiro-Wilk

## Arquitectura del Proyecto

```
BioStat/
├── main.py                  # Punto de entrada
├── build_exe.py             # Script de compilación
├── requirements.txt         # Dependencias
├── biostat.spec             # Spec de PyInstaller
├── src/
│   ├── app.py               # Aplicación principal
│   ├── core/                # Módulos de cálculo
│   │   ├── statistics.py    # Tests paramétricos y no paramétricos
│   │   ├── roc.py           # Curva ROC
│   │   ├── bland_altman.py  # Bland-Altman
│   │   ├── passing_bablok.py
│   │   ├── survival.py      # Kaplan-Meier, Log-rank
│   │   ├── meta_analysis.py
│   │   ├── regression.py    # Regresión lineal, múltiple, logística
│   │   ├── agreement.py     # Kappa, ICC, Cronbach
│   │   ├── diagnostic_tests.py
│   │   ├── outliers.py      # Grubbs, Tukey, ESD
│   │   ├── reference.py     # Intervalos de referencia
│   │   ├── sample_size.py
│   │   ├── bootstrap.py
│   │   ├── random_forest.py
│   │   ├── validation.py    # Validación de datos
│   │   ├── export.py        # Exportación HTML
│   │   ├── two_way_anova.py
│   │   ├── ancova.py
│   │   ├── repeated_measures.py
│   │   ├── cox_regression.py
│   │   ├── probit.py
│   │   ├── cmh.py
│   │   ├── serial_measurements.py
│   │   ├── plots.py         # Youden, Polar, Waterfall, Mountain
│   │   └── qc/              # Control de calidad
│   ├── io/                  # Lectura/escritura de archivos
│   └── ui/                  # Interfaz gráfica
│       ├── main_window.py   # Ventana principal
│       ├── analysis_panel.py # Panel de análisis
│       ├── data_panel.py    # Panel de datos
│       ├── graphs_panel.py  # Panel de gráficos
│       ├── qc_panel.py      # Panel de control de calidad
│       ├── styles.py        # Tema visual (Clean Clinical)
│       └── icons.py         # Iconos (qtawesome)
└── tests/
    ├── test_statistics.py
    └── test_new_features.py
```

## Requisitos

- Python 3.8+
- PyQt6
- NumPy, SciPy, pandas
- Matplotlib, Seaborn
- qtawesome (iconos profesionales)

## Iconografía

Los iconos utilizan la librería `qtawesome` (FontAwesome 5 / Material Design)
para una apariencia profesional y consistente en toda la aplicación.

## Tema Visual

BioStat utiliza el tema **Clean Clinical**:
- Fondos claros (#F3F5F9, #FFFFFF)
- Acento azul médico (#2B579A) para elementos interactivos
- Verde institucional (#107C41) para acciones de éxito
- Sin colores oscuros ni neón — diseñado para uso prolongado en laboratorio
