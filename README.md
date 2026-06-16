# BioStat

Software estadistico para laboratorio clinico. Inspirado en MedCalc.

## Instalacion

```bash
pip install -r requirements.txt
python main.py
```

## Funcionalidades

### Estadisticas
- Estadisticas descriptivas (media, mediana, DE, varianza, CV%, sesgo, curtosis)
- t-test pareado e independiente
- ANOVA una via
- Mann-Whitney U, Wilcoxon, Kruskal-Wallis, Friedman
- Chi-cuadrado, Fisher exact, McNemar
- F-test (comparar varianzas)
- Shapiro-Wilk (normalidad)
- Media recortada, asimetria, curtosis

### Correlacion y Regresion
- Pearson, Spearman, correlacion parcial
- Regresion lineal simple y multiple
- Regresion logistica con odds ratios
- Passing-Bablok, Deming

### Analisis de Metodos
- Curva ROC con AUC y umbral optimo
- Bland-Altman
- Concordancia (Kappa, ICC, Cronbach alpha)

### Supervivencia
- Kaplan-Meier
- Log-rank test

### Meta-analisis
- Modelo de efectos fijos y aleatorios
- Forest plot
- Heterogeneidad (I2, Q de Cochran)

### Machine Learning
- Random Forest (clasificacion y regresion)
- Bootstrap (media, diferencia, correlacion)

### Control de Calidad
- Levey-Jennings
- Reglas de Westgard
- Analisis de tendencias

### Tamano Muestral
- 1 media, 2 medias, 2 proporciones
- Correlacion, poder estadistico

### Otros
- Odds Ratio, Riesgo Relativo, LR
- Deteccion de outliers (Grubbs, Tukey)
- Intervalos de referencia
- Prueba diagnostica completa

## Requisitos

- Python 3.8+
- PyQt6
- NumPy, SciPy, pandas
- Matplotlib
