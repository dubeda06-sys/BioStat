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
from src.core.passing_bablok import passing_bablok
from src.core.survival import kaplan_meier, log_rank_test
from src.core.meta_analysis import meta_analysis
from src.core.sample_size import (
    sample_size_mean, sample_size_two_means,
    sample_size_proportions, sample_size_correlation, power_analysis
)
from src.core.bootstrap import (
    bootstrap_mean, bootstrap_median, bootstrap_correlation,
    bootstrap_difference, bootstrap_regression
)
from src.core.random_forest import RandomForestClassifier, RandomForestRegressor
from src.core.statistics import (
    mannwhitneyu, wilcoxon_signed_rank, chi_square_test, fisher_exact_test,
    mcnemar_test, kruskal_wallis, friedman_test,
    f_test_variances, ttest_1sample, ttest_paired, ttest_ind,
    trimmed_mean, skewness_test, kurtosis_test,
    partial_correlation, descriptive_stats, geometric_mean, harmonic_mean,
    anova_oneway, sign_test, cochran_q, pearson_r, spearman_rho, normality_test
)
from src.core.agreement import (
    cohens_kappa, intraclass_correlation, cronbach_alpha,
    weighted_kappa, deming_regression, cv_from_duplicates
)
from src.core.regression import linear_regression, multiple_regression, logistic_regression
from src.core.diagnostic_tests import (
    odds_ratio, relative_risk, diagnostic_test,
    likelihood_ratios, compare_two_means, compare_two_proportions, compare_two_auc
)
from src.core.outliers import grubbs_test, tukey_outliers, generalized_esd
from src.core.reference import reference_interval, percentile_table, age_related_reference
from src.core.two_way_anova import two_way_anova
from src.core.ancova import ancova
from src.core.repeated_measures import repeated_measures_anova
from src.core.cox_regression import cox_regression
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

ANALYSIS_LEGENDS = {
    "Estadisticas descriptivas": {
        "legend": "Proporciona un resumen numérico fundamental (media, mediana, DE, etc.). Úselo en la fase inicial del análisis para entender la distribución y calidad de los datos numéricos antes de aplicar pruebas inferenciales.",
        "formula": "Media: x̄ = Σxi / n\nDE: s = √[Σ(xi - x̄)² / (n-1)]\nCV%: (s / x̄) × 100"
    },
    "t-test pareado": {
        "legend": "Compara las medias de dos mediciones realizadas en los mismos individuos (ej. antes y después de un tratamiento). Requiere que las diferencias entre pares sigan una distribución normal.",
        "formula": "t = (d̄ - μ₀) / (sd / √n)\ndonde d̄ = media de diferencias\nsd = DE de diferencias\nμ₀ = 0 (hipótesis nula)"
    },
    "t-test independiente": {
        "legend": "Compara las medias de dos grupos completamente distintos (ej. pacientes sanos vs enfermos). Requiere que los datos sean numéricos continuos y aproximadamente normales en cada grupo.",
        "formula": "t = (x̄₁ - x̄₂) / √(s₁²/n₁ + s₂²/n₂)\ndonde x̄ = media, s = DE, n = tamaño"
    },
    "ANOVA una via": {
        "legend": "Compara las medias de tres o más grupos independientes para ver si hay diferencias significativas entre ellos. Úselo cuando tiene una variable categórica de múltiples niveles y una respuesta numérica continua.",
        "formula": "F = MS_entre / MS_dentro\nMS_entre = SS_entre / (k-1)\nMS_dentro = SS_dentro / (N-k)"
    },
    "Correlacion de Pearson": {
        "legend": "Mide la fuerza de la relación lineal entre dos variables continuas (ej. concentración de dos analitos). Exige que ambas variables sigan una distribución normal y su relación sea lineal.",
        "formula": "r = Σ[(xi - x̄)(yi - ȳ)] / √[Σ(xi - x̄)² × Σ(yi - ȳ)²]\nt = r × √(n-2) / √(1-r²)"
    },
    "Correlacion de Spearman": {
        "legend": "Mide la relación monótona entre dos variables utilizando sus rangos. Es la alternativa no paramétrica a Pearson, ideal cuando los datos tienen valores atípicos (outliers) o no son normales.",
        "formula": "ρ = 1 - (6 × Σd²) / (n × (n² - 1))\ndonde d = diferencia de rangos"
    },
    "Shapiro-Wilk": {
        "legend": "Evalúa formalmente si un conjunto de datos sigue una distribución normal gaussiana. Es el primer paso recomendado (p < 0.05 indica no normalidad) antes de elegir entre pruebas paramétricas o no paramétricas.",
        "formula": "W = (Σaᵢxᵢ)² / Σ(xi - x̄)²\ndonde xᵢ son los datos ordenados"
    },
    "Curva ROC": {
        "legend": "Evalúa el rendimiento de un biomarcador o prueba diagnóstica. Muestra el equilibrio entre sensibilidad y especificidad a distintos puntos de corte. Requiere un resultado binario (enfermo/sano) y un valor numérico.",
        "formula": "Sensibilidad = TP / (TP + FN)\nEspecificidad = TN / (TN + FP)\nAUC = ∫ Sensibilidad d(1-Especificidad)"
    },
    "Bland-Altman": {
        "legend": "El estándar de oro para comparar dos métodos de medición clínica (ej. un analizador nuevo vs el de referencia). Evalúa si existe un sesgo sistemático y define los límites de concordancia clínica.",
        "formula": "Sesgo = Media(diferencias)\nLoA = Sesgo ± 1.96 × DE(diferencias)\n% Sesgo = (Sesgo / Media Método 1) × 100"
    },
    "Passing-Bablok": {
        "legend": "Regresión lineal robusta utilizada para comparar dos métodos analíticos. No es sensible a valores atípicos y permite determinar si hay errores sistemáticos constantes (intercepto) o proporcionales (pendiente).",
        "formula": "y = β₀ + β₁x\nPendiente = 1 y β₀ = 0 → concordancia"
    },
    "Kaplan-Meier": {
        "legend": "Estima la probabilidad de que los pacientes sobrevivan a lo largo del tiempo sin experimentar un evento (ej. muerte o recaída). Requiere datos de tiempo de seguimiento y el estado final (evento o censurado).",
        "formula": "S(t) = Π[(nᵢ - dᵢ) / nᵢ]\ndonde nᵢ = en riesgo, dᵢ = eventos"
    },
    "Log-rank test": {
        "legend": "Compara estadísticamente dos o más curvas de supervivencia de Kaplan-Meier. Úselo para evaluar si un tratamiento mejora el tiempo de supervivencia frente a un grupo control.",
        "formula": "χ² = (O₁ - E₁)² / E₁ + (O₂ - E₂)² / E₂\ndonde O = observados, E = esperados"
    },
    "Meta-analisis": {
        "legend": "Sintetiza matemáticamente los resultados de múltiples estudios independientes. Úselo para obtener una estimación global y más potente del tamaño del efecto (ej. odds ratio global) de una intervención.",
        "formula": "EF = Σ(wᵢ × EFᵢ) / Σ(wᵢ)\nwᵢ = 1 / SEᵢ²\nI² = (Q - df) / Q × 100%"
    },
    "Tamano muestral (1 media)": {
        "legend": "Calcula cuántos pacientes necesita reclutar para demostrar que la media de su muestra difiere de un valor de referencia conocido, considerando la potencia y significancia deseadas.",
        "formula": "n = [(Z_α/2 + Z_β) × σ / δ]²\ndonde δ = diferencia a detectar, σ = DE"
    },
    "Tamano muestral (2 medias)": {
        "legend": "Calcula la cantidad de pacientes necesarios para detectar una diferencia clínica importante entre dos grupos independientes. Es crucial para el diseño de ensayos clínicos.",
        "formula": "n₁ = [(Z_α/2 + Z_β) × σ / δ]² × (1 + 1/r)\nn₂ = n₁ × r"
    },
    "Tamano muestral (2 proporciones)": {
        "legend": "Determina la muestra necesaria para comparar tasas de éxito o prevalencia entre dos grupos (ej. porcentaje de curación con droga A vs droga B).",
        "formula": "n = [Z_α/2 × √(2p̄(1-p̄)) + Z_β × √(p₁(1-p₁) + p₂(1-p₂))]² / (p₁ - p₂)²"
    },
    "Poder estadistico": {
        "legend": "Analiza retrospectivamente si un estudio que no encontró diferencias significativas tenía el tamaño muestral suficiente (potencia > 80%) para haberlas detectado si existieran.",
        "formula": "Poder = 1 - β = P(rechazar H₀ | H₁ es verdadera)\nncp = δ × √n / σ"
    },
    "Bootstrap (media)": {
        "legend": "Técnica de remuestreo computacional para calcular intervalos de confianza de la media. Excelente alternativa cuando los datos no cumplen los supuestos de normalidad tradicional.",
        "formula": "IC = [θ*_(α/2), θ*_(1-α/2)]\ndonde θ* son los percentiles de B remuestreos"
    },
    "Bootstrap (diferencia)": {
        "legend": "Calcula el intervalo de confianza para la diferencia de medias mediante remuestreo. Muy útil cuando se comparan grupos pequeños con distribuciones desconocidas o asimétricas.",
        "formula": "IC = [θ*_(α/2), θ*_(1-α/2)]\nθ* = diferencia media de B remuestreos"
    },
    "Bootstrap (correlacion)": {
        "legend": "Estima la robustez de un coeficiente de correlación mediante remuestreo repetido, ideal cuando se sospecha que unos pocos puntos pueden estar influenciando excesivamente el resultado.",
        "formula": "IC = [r*_(α/2), r*_(1-α/2)]\nr* = correlación de B remuestreos"
    },
    "Random Forest (clasificacion)": {
        "legend": "Algoritmo de machine learning que utiliza múltiples árboles de decisión para clasificar pacientes en categorías (ej. alto riesgo / bajo riesgo) basado en múltiples variables predictoras complejas.",
        "formula": "ŷ = mode(.Tree₁(x), Tree₂(x), ..., Tree_B(x))\nImportancia = reducción en impureza Gini"
    },
    "Random Forest (regresion)": {
        "legend": "Modelo predictivo avanzado que estima un valor numérico continuo usando múltiples árboles. Puede capturar interacciones complejas no lineales entre las variables del paciente.",
        "formula": "ŷ = (1/B) × Σ Treeᵦ(x)\nMSE = (1/n) × Σ(yᵢ - ŷᵢ)²"
    },
    "Mann-Whitney U": {
        "legend": "Prueba no paramétrica equivalente al t-test independiente. Úsela para comparar dos grupos cuando los datos no son normales, son ordinales, o existen valores atípicos extremos.",
        "formula": "U = n₁ × n₂ + n₁(n₁+1)/2 - R₁\ndonde R₁ = suma de rangos del grupo 1"
    },
    "Wilcoxon pareado": {
        "legend": "Prueba no paramétrica para muestras relacionadas (antes/después). Es la alternativa al t-test pareado cuando las diferencias no se distribuyen normalmente.",
        "formula": "W = Σ Rᵢ⁺\ndonde Rᵢ⁺ = rangos de diferencias positivas"
    },
    "Chi-cuadrado": {
        "legend": "Prueba de asociación para dos variables categóricas (ej. grupo sanguíneo y presencia de enfermedad). Requiere que las frecuencias esperadas en la tabla de contingencia sean suficientes (>5).",
        "formula": "χ² = Σ[(Oᵢⱼ - Eᵢⱼ)² / Eᵢⱼ]\nEᵢⱼ = (Filaᵢ × Columnaⱼ) / Total"
    },
    "Fisher exact": {
        "legend": "Alternativa exacta al Chi-cuadrado para tablas 2x2. Es indispensable cuando se tienen muestras muy pequeñas o frecuencias esperadas menores a 5 celdas.",
        "formula": "P = (a+b)!(c+d)!(a+c)!(b+d)! / (a!b!c!d!n!)"
    },
    "McNemar": {
        "legend": "Analiza cambios en proporciones para datos pareados. Ideal para estudios antes-después donde el resultado es categórico (ej. positivo/negativo antes y después de tratamiento).",
        "formula": "χ² = (b - c)² / (b + c)\ndonde b y c son las discordancias"
    },
    "Kruskal-Wallis": {
        "legend": "El equivalente no paramétrico de ANOVA de una vía. Permite comparar las medianas de tres o más grupos independientes cuando no se puede asumir normalidad poblacional.",
        "formula": "H = (12 / (n(n+1))) × Σ(Rᵢ²/nᵢ) - 3(n+1)\ndonde Rᵢ = suma de rangos del grupo i"
    },
    "Friedman": {
        "legend": "Alternativa no paramétrica para ANOVA de medidas repetidas. Se usa cuando se evalúa a los mismos pacientes en 3 o más momentos distintos (ej. basal, mes 1, mes 6) sin asumir normalidad.",
        "formula": "Q = (12 / (nk(k+1))) × ΣRⱼ² - 3n(k+1)\ndonde Rⱼ = suma de rangos de la condición j"
    },
    "F-test (varianzas)": {
        "legend": "Compara las varianzas de dos poblaciones para determinar si son significativamente diferentes. Es útil para evaluar si dos métodos analíticos tienen la misma precisión.",
        "formula": "F = s₁² / s₂²\ndonde s₁² > s₂² (mayor varianza numerador)"
    },
    "Kappa": {
        "legend": "Evalúa el grado de concordancia entre dos observadores o métodos al clasificar datos categóricos (ej. dos patólogos leyendo biopsias), corrigiendo la coincidencia debida al azar.",
        "formula": "κ = (Pₒ - Pₑ) / (1 - Pₑ)\nPₒ = concordancia observada\nPₑ = concordancia esperada por azar"
    },
    "ICC": {
        "legend": "Coeficiente de Correlación Intraclase. Mide la fiabilidad y concordancia de mediciones continuas realizadas por diferentes evaluadores o equipos sobre la misma muestra.",
        "formula": "ICC = (MS_entre - MS_dentro) / (MS_entre + (k-1)×MS_dentro)\nk = número de mediciones"
    },
    "Cronbach alfa": {
        "legend": "Mide la consistencia interna o fiabilidad de un test o cuestionario compuesto por múltiples ítems (ej. escalas psicométricas de dolor o calidad de vida).",
        "formula": "α = (k / (k-1)) × (1 - Σσᵢ² / σₜ²)\nk = número de ítems, σᵢ² = varianza de cada ítem"
    },
    "Regresion lineal": {
        "legend": "Modela matemáticamente cómo una variable numérica (dependiente) cambia en función de otra (independiente). Úselo para predecir valores o establecer tendencias de calibración.",
        "formula": "ŷ = β₀ + β₁x\nβ₁ = Σ[(xi - x̄)(yi - ȳ)] / Σ(xi - x̄)²\nβ₀ = ȳ - β₁x̄"
    },
    "Regresion multiple": {
        "legend": "Extensión de la regresión lineal que predice un resultado numérico usando múltiples variables independientes simultáneamente, controlando posibles factores de confusión.",
        "formula": "ŷ = β₀ + β₁x₁ + β₂x₂ + ... + βₚxₚ\nβ = (X'X)⁻¹X'y"
    },
    "Regresion logistica": {
        "legend": "Estima la probabilidad de que ocurra un evento binario (ej. mortalidad: sí/no) basándose en una o más variables predictoras clínicas (edad, sexo, biomarcadores).",
        "formula": "ln(p/(1-p)) = β₀ + β₁x₁ + ... + βₚxₚ\np = 1 / (1 + e^-(β₀ + Σβᵢxᵢ))"
    },
    "Odds Ratio": {
        "legend": "Mide las probabilidades relativas de que ocurra un evento bajo cierta exposición frente a su ausencia. Es la medida estándar de asociación en estudios retrospectivos de casos y controles.",
        "formula": "OR = (a × d) / (b × c)\nln(OR) ± 1.96 × SE(ln(OR))"
    },
    "Riesgo Relativo": {
        "legend": "Calcula el riesgo de un evento en el grupo expuesto comparado con el grupo no expuesto. Aplicable en estudios prospectivos de cohortes o ensayos clínicos controlados.",
        "formula": "RR = [a/(a+b)] / [c/(c+d)]\nARR = Riesgo_expuesto - Riesgo_no_expuesto\nNNT = 1/ARR"
    },
    "Diagnostic test": {
        "legend": "Evalúa la utilidad clínica de una prueba. Requiere resultados de la prueba y el estándar de oro para calcular Sensibilidad, Especificidad y Valores Predictivos (VPP, VPN).",
        "formula": "Sens = TP/(TP+FN)\nSpec = TN/(TN+FP)\nPPV = TP/(TP+FP)\nNPV = TN/(TN+FN)"
    },
    "Outliers (Grubbs)": {
        "legend": "Detecta si el valor más extremo en un conjunto de datos es un valor atípico estadísticamente significativo. Asume que el resto de los datos se distribuye normalmente.",
        "formula": "G = |x_max - x̄| / s\nValor crítico: t_(α/2n) × √((n-1)² / (n(n-2+t²)))"
    },
    "Outliers (Tukey)": {
        "legend": "Identifica valores atípicos utilizando rangos intercuartílicos (IQR). Es más robusto que Grubbs y no requiere que los datos sigan estrictamente una distribución normal.",
        "formula": "IQR = Q₇₅ - Q₂₅\nLímite inferior = Q₂₅ - 1.5×IQR\nLímite superior = Q₇₅ + 1.5×IQR"
    },
    "Intervalos de referencia": {
        "legend": "Calcula los valores esperados para una población sana (generalmente percentiles 2.5 y 97.5). Indispensable para establecer rangos normales de laboratorio para nuevos analitos.",
        "formula": "Límite inferior = Percentil 2.5\nLímite superior = Percentil 97.5\nIC Bootstrap para precisión"
    },
    "Asimetria y curtosis": {
        "legend": "Métricas que evalúan formalmente la forma de la distribución de los datos. Desviaciones significativas de 0 indican que los datos están sesgados (colas asimétricas) o son muy apuntados.",
        "formula": "Sesgo = Σ(xi - x̄)³ / (n × s³)\nCurtosis = Σ(xi - x̄)⁴ / (n × s⁴) - 3"
    },
    "Media recortada": {
        "legend": "Calcula la media descartando un porcentaje (ej. 5%) de los valores más extremos superiores e inferiores. Proporciona un estimado robusto de la tendencia central resistente a outliers.",
        "formula": "Media recortada = (1/(n-2k)) × Σxᵢ\ndonde k = n × proporción recortada"
    },
    "Correlacion parcial": {
        "legend": "Mide la relación lineal entre dos variables continuas mientras se elimina (controla) matemáticamente el efecto de una tercera variable de confusión.",
        "formula": "r_xy.z = (r_xy - r_xz × r_yz) / √[(1-r_xz²)(1-r_yz²)]"
    },
    "Media geometrica": {
        "legend": "Medida de tendencia central adecuada para datos que crecen exponencialmente o están fuertemente sesgados a la derecha (ej. títulos de anticuerpos o cargas virales).",
        "formula": "GM = (x₁ × x₂ × ... × xₙ)^(1/n)\nGM = exp[(1/n) × Σln(xᵢ)]"
    },
    "Media armonica": {
        "legend": "Promedio utilizado frecuentemente para analizar tasas y proporciones. Es útil cuando se trabaja con promedios de velocidades o tiempos de procesamiento de laboratorio.",
        "formula": "HM = n / (1/x₁ + 1/x₂ + ... + 1/xₙ)\nHM = n / Σ(1/xᵢ)"
    },
    "t-test 1 muestra": {
        "legend": "Compara la media observada de su muestra frente a un valor teórico conocido o establecido previamente. Úselo para verificar si sus datos se desvían de un estándar.",
        "formula": "t = (x̄ - μ₀) / (s / √n)\ngl = n - 1"
    },
    "Sign test": {
        "legend": "Alternativa muy simple al Wilcoxon pareado que solo evalúa la dirección del cambio (positivo o negativo) sin considerar la magnitud. Es extremadamente robusto a outliers.",
        "formula": "p = 2 × Σ C(n,k) × 0.5ⁿ para k ≤ min(n_pos, n_neg)"
    },
    "Cochran Q": {
        "legend": "Extensión de la prueba de McNemar para comparar 3 o más tratamientos en datos dicotómicos relacionados (ej. éxito/fracaso de 3 terapias diferentes en los mismos pacientes).",
        "formula": "Q = (k-1) × [k × ΣC² - T²] / [k × T - ΣR²]\nk = condiciones, T = total de éxitos"
    },
    "Kappa ponderado": {
        "legend": "Versión del índice Kappa que penaliza los desacuerdos entre evaluadores dependiendo de su magnitud. Esencial para categorías ordinales (ej. grados tumorales I, II, III).",
        "formula": "κ_w = 1 - (Σ wᵢⱼ × Oᵢⱼ) / (Σ wᵢⱼ × Eᵢⱼ)\nwᵢⱼ = |i-j|/(k-1) (lineal)"
    },
    "Deming regression": {
        "legend": "Regresión lineal avanzada que asume que existen errores de medición tanto en X como en Y. Es el método recomendado (junto con Passing-Bablok) para comparar métodos de laboratorio.",
        "formula": "y = β₀ + β₁x\nβ₁ = (s_y - δ×s_x + √((s_y-δ×s_x)² + 4δ×s_xy²)) / (2×s_xy)"
    },
    "CV duplicatas": {
        "legend": "Calcula el Coeficiente de Variación analítico a partir de muestras procesadas en duplicado. Es clave para validar la repetibilidad intralaboratorio de un ensayo.",
        "formula": "CV = (DE × √2 / Media) × 100%\nCV intra = variabilidad dentro del ensayo"
    },
    "Likelihood Ratios": {
        "legend": "Razones de verosimilitud (LR+ y LR-) que indican cuánto cambia la probabilidad post-prueba de una enfermedad. LR+ alto (>10) confirma; LR- bajo (<0.1) descarta firmemente.",
        "formula": "LR+ = Sens / (1 - Spec)\nLR- = (1 - Sens) / Spec\nPre-odds × LR = Post-odds"
    },
    "Comparar 2 medias": {
        "legend": "Calcula diferencias significativas entre dos grupos ingresando directamente datos resumidos (media, DE, n) sin necesidad de tener los datos crudos originales.",
        "formula": "t = (m₁ - m₂) / √(s₁²/n₁ + s₂²/n₂)\ngl = Welch-Satterthwaite"
    },
    "Comparar 2 proporciones": {
        "legend": "Evalúa diferencias entre tasas de éxito utilizando datos agrupados (casos/totales) en lugar de variables binarias individuales a nivel de paciente.",
        "formula": "z = (p₁ - p₂) / √[p̄(1-p̄)(1/n₁ + 1/n₂)]\np̄ = (p₁n₁ + p₂n₂)/(n₁+n₂)"
    },
    "Comparar 2 AUC": {
        "legend": "Prueba estadística formal (ej. método DeLong) para determinar si un biomarcador es significativamente mejor que otro al comparar las áreas bajo sus curvas ROC.",
        "formula": "z = (AUC₁ - AUC₂) / √(SE₁² + SE₂²)"
    },
    "Tabla de percentiles": {
        "legend": "Genera una tabla completa de cuantiles (ej. p5, p10, p50, p90, p95) con sus respectivos intervalos de confianza. Útil para curvas de crecimiento pediátrico.",
        "formula": "Pₖ = valor en posición k×(n+1)/100\nIC Bootstrap para precisión"
    },
    "Edad-relacionada": {
        "legend": "Permite segmentar y calcular intervalos de referencia específicos para distintos grupos etarios o factores continuos. Clave en analitos como hormonas pediátricas.",
        "formula": "Intervalos por grupo de edad usando percentiles"
    },
    "Outliers (ESD)": {
        "legend": "Prueba de Desviación Estudentizada Extrema Generalizada (Rosner). Detecta progresivamente múltiples outliers simultáneos en una serie, superando el límite de Grubbs.",
        "formula": "Rᵢ = |x_i - x̄| / s\nλᵢ = valor crítico de t para cada paso"
    },
    "Bootstrap (mediana)": {
        "legend": "Remuestreo para calcular el intervalo de confianza de la mediana. Extremadamente útil en datos fuertemente asimétricos como tiempos de hospitalización.",
        "formula": "IC = [mediana*_(α/2), mediana*_(1-α/2)]"
    },
    "Bootstrap (regresion)": {
        "legend": "Genera estimaciones robustas e intervalos empíricos para las pendientes de regresión. Se emplea cuando se violan los supuestos de homocedasticidad o normalidad de los residuos.",
        "formula": "IC para β = [β*_(α/2), β*_(1-α/2)]"
    },
    "Tamaño muestral (correlacion)": {
        "legend": "Determina el número de sujetos necesarios para detectar si un coeficiente de correlación específico es estadísticamente diferente de cero.",
        "formula": "n = [(Z_α/2 + Z_β) / arctanh(r)]² + 3"
    },
    "ANOVA dos vias": {
        "legend": "Analiza simultáneamente el efecto de dos variables categóricas independientes sobre una respuesta continua. También evalúa si existe interacción entre los factores.",
        "formula": "F_factor = MS_factor / MS_error\nF_interacción = MS_AB / MS_error"
    },
    "ANCOVA": {
        "legend": "Análisis de covarianza. Compara grupos ajustando por variables continuas de confusión (covariables, ej. edad basal). Aumenta el poder estadístico al reducir el error residual.",
        "formula": "F = MS_ajustado / MS_error\nη² = SS_grupo / (SS_grupo + SS_error)"
    },
    "Medidas repetidas": {
        "legend": "Compara promedios de la misma variable medida en múltiples ocasiones en los mismos sujetos. Aplica correcciones automáticas (Greenhouse-Geisser) para violaciones de esfericidad.",
        "formula": "F = MS_tiempo / MS_error\nCorrección GG: ε = (Σλᵢ)² / (k-1)×Σλᵢ²"
    },
    "Cox regression": {
        "legend": "Modelo de riesgos proporcionales. Estima cómo múltiples factores de riesgo influyen simultáneamente en el tiempo de supervivencia de los pacientes frente a un evento clínico.",
        "formula": "h(t) = h₀(t) × exp(β₁x₁ + β₂x₂ + ...)\nHR = exp(βᵢ)"
    },
    "Probit regression": {
        "legend": "Modelo predictivo para respuestas binomiales basado en la distribución normal acumulada. Utilizado frecuentemente en toxicología y farmacología (ej. análisis dosis-respuesta y LD50).",
        "formula": "P(Y=1) = Φ(β₀ + β₁x)\nΦ = CDF normal estándar"
    },
    "CMH test": {
        "legend": "Test de Cochran-Mantel-Haenszel. Permite analizar la asociación en tablas de contingencia 2x2 controlando (estratificando) por una tercera variable de confusión multicategórica.",
        "formula": "CMH = (Σ(aᵢ - n₁ᵢm₁ᵢ/nᵢ))² / Σ(var_i)"
    },
    "Mediciones seriales": {
        "legend": "Resumen longitudinal de mediciones en pacientes (ej. curvas de glucosa). Permite calcular y analizar métricas como el Área Bajo la Curva (AUC), Cmax o Tmax individual.",
        "formula": "Pendiente = regresión lineal tiempo vs valor\nPendiente global = pendiente promedio"
    },
    "Youden plot": {
        "legend": "Representación gráfica avanzada de la sensibilidad frente a la especificidad. Ayuda a seleccionar visualmente el punto de corte óptimo que maximiza el Índice de Youden.",
        "formula": "J = Sensibilidad + Especificidad - 1\nUmbral óptimo = argmax(J)"
    },
    "Polar plot": {
        "legend": "Gráfico de radar utilizado para visualizar y comparar simultáneamente múltiples parámetros (ej. panel de citocinas) entre grupos o estados de la enfermedad.",
        "formula": "Ángulos = 2π × i/k\nejes = cada variable normalizada"
    },
    "Waterfall chart": {
        "legend": "Visualiza los cambios secuenciales positivos y negativos frente a un valor basal. Frecuentemente usado en oncología para mostrar la reducción o progresión del tamaño tumoral en pacientes.",
        "formula": "Acumulado = Σ(valores parciales)\nTotal = suma final"
    },
    "Mountain plot": {
        "legend": "También conocido como gráfico de distribución plegada (folded empirical CDF). Muestra de forma muy sensible las diferencias de distribución o sesgos entre dos métodos clínicos.",
        "formula": "f(x) = φ((x-μ)/σ) / σ\nSymmetric around median"
    },
    "Bland-Altman múltiple": {
        "legend": "Adaptación del método de Bland-Altman para cuando se tienen mediciones repetidas en los mismos sujetos para ambos métodos. Considera la varianza intra-sujeto e inter-sujeto.",
        "formula": "Para cada par: Sesgo ± 1.96 × DE(diferencias)"
    },
}
from src.ui.analysis_methods import AnalysisMethodsMixin


class AnalysisPanel(AnalysisMethodsMixin, QWidget):
    def __init__(self):
        super().__init__()
        self.data = None
        self.canvas = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(10, 4, 10, 4)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)
        left_l.setSpacing(4)

        cfg = QGroupBox(f"  {Icons.GEAR()}  Configuracion")
        cl = QFormLayout()
        cl.setSpacing(4)
        cl.setContentsMargins(6, 6, 6, 6)

        self.combo_analysis = QComboBox()
        self.combo_analysis.addItems(list(ANALYSIS_HELP.keys()))
        self.combo_analysis.setMinimumHeight(28)
        self.combo_analysis.currentTextChanged.connect(self._on_analysis_changed)
        cl.addRow("Analisis:", self.combo_analysis)

        self.lbl_help = QLabel(ANALYSIS_HELP["Estadisticas descriptivas"])
        self.lbl_help.setObjectName("subtitle")
        self.lbl_help.setWordWrap(True)
        self.lbl_help.setStyleSheet("color: #6b7280; font-style: italic; padding: 1px 0; font-size: 10px;")
        
        self.lbl_legend = QLabel("")
        self.lbl_legend.setWordWrap(True)
        self.lbl_legend.setStyleSheet("color: #374151; padding: 2px 0; font-size: 10px; background: #f9fafb; border-radius: 4px; padding: 6px;")
        cl.addRow("", self.lbl_help)
        cl.addRow("📚", self.lbl_legend)

        self.combo_col1 = QComboBox()
        self.combo_col1.setMinimumHeight(28)
        cl.addRow("Var 1:", self.combo_col1)

        self.combo_col2 = QComboBox()
        self.combo_col2.setMinimumHeight(28)
        cl.addRow("Var 2:", self.combo_col2)

        self.combo_col3 = QComboBox()
        self.combo_col3.setMinimumHeight(28)
        cl.addRow("Var 3:", self.combo_col3)

        self.input_alpha = QLineEdit("0.05")
        self.input_alpha.setMaximumWidth(60)
        self.input_alpha.setMinimumHeight(28)
        cl.addRow("Alpha:", self.input_alpha)

        cfg.setLayout(cl)
        left_l.addWidget(cfg)

        br = QHBoxLayout()
        br.setSpacing(4)
        self.btn_run = QPushButton("Ejecutar")
        self.btn_run.setIcon(Icons.RUN())
        self.btn_run.setMinimumHeight(30)
        self.btn_run.clicked.connect(self._run)
        br.addWidget(self.btn_run)
        btn_clr = QPushButton("Limpiar")
        btn_clr.setIcon(Icons.CLEAR())
        btn_clr.setObjectName("secondary")
        btn_clr.setMinimumHeight(30)
        btn_clr.clicked.connect(self._clear)
        br.addWidget(btn_clr)
        left_l.addLayout(br)

        fg = QGroupBox("Formula")
        fl = QVBoxLayout()
        fl.setContentsMargins(4, 2, 4, 2)
        self.txt_formula = QTextEdit()
        self.txt_formula.setReadOnly(True)
        self.txt_formula.setMaximumHeight(80)
        self.txt_formula.setPlaceholderText("Formula...")
        self.txt_formula.setStyleSheet("QTextEdit { font-family: Consolas, monospace; font-size: 10px; background: #f8f9fa; border: 1px solid #e8eaf0; border-radius: 4px; padding: 3px; }")
        fl.addWidget(self.txt_formula)
        fg.setLayout(fl)
        left_l.addWidget(fg)

        left.setMaximumWidth(300)
        left.setMinimumWidth(260)
        splitter.addWidget(left)

        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(4)

        rg = QGroupBox(f"  {Icons.DOC()}  Resultados")
        rl = QVBoxLayout()
        rl.setContentsMargins(4, 2, 4, 2)
        self.txt_results = QTextEdit()
        self.txt_results.setReadOnly(True)
        self.txt_results.setPlaceholderText("Resultados...")
        rl.addWidget(self.txt_results)
        rg.setLayout(rl)
        right_l.addWidget(rg, stretch=2)

        pg = QGroupBox(f"  {Icons.CHART()}  Grafico")
        pl = QVBoxLayout()
        pl.setContentsMargins(4, 2, 4, 2)
        self.graph_scroll = QScrollArea()
        self.graph_scroll.setWidgetResizable(True)
        self.graph_ph = QLabel(f"<div style='text-align:center;color:#a0a8b8;padding:20px;'>{Icons.CHART()} El grafico aparecera aqui</div>")
        self.graph_ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.graph_scroll.setWidget(self.graph_ph)
        pl.addWidget(self.graph_scroll)
        pg.setLayout(pl)
        right_l.addWidget(pg, stretch=3)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    def _on_analysis_changed(self, text):
        self.lbl_help.setText(ANALYSIS_HELP.get(text, ""))
        
        legend_info = ANALYSIS_LEGENDS.get(text, {})
        if legend_info:
            legend = legend_info.get('legend', '')
            formula = legend_info.get('formula', '')
            display_text = f"<b>Descripción:</b> {legend}"
            if formula:
                display_text += f"<br><br><b>Fórmula:</b><br><pre style='font-family:Consolas,monospace;font-size:9px;color:#4f6ef7;'>{formula}</pre>"
            self.lbl_legend.setText(display_text)
        else:
            self.lbl_legend.setText("")

    def set_data(self, data):
        self.data = data
        if data is not None:
            cols = data.columns.tolist()
            self.combo_col1.clear()
            self.combo_col2.clear()
            self.combo_col3.clear()
            self.combo_col1.addItems(cols)
            self.combo_col2.addItems(cols)
            self.combo_col3.addItems(["(ninguna)"] + cols)

    def _run(self):
        if self.data is None:
            self.txt_results.setHtml(f"<div style='color:#d97706;padding:12px;'>{Icons.WARN()} <b>Sin datos.</b> Importa un archivo en la pestaña Datos.</div>")
            return

        at = self.combo_analysis.currentText()
        c1 = self.combo_col1.currentText()
        c2 = self.combo_col2.currentText()
        c3 = self.combo_col3.currentText()
        try:
            alpha = float(self.input_alpha.text())
        except ValueError:
            alpha = 0.05

        dispatch = {
            "Estadisticas descriptivas": lambda: self._desc(c1),
            "t-test pareado": lambda: self._t_paired(c1, c2, alpha),
            "t-test independiente": lambda: self._t_ind(c1, c2, alpha),
            "ANOVA una via": lambda: self._anova(alpha),
            "Correlacion de Pearson": lambda: self._corr_p(c1, c2),
            "Correlacion de Spearman": lambda: self._corr_s(c1, c2),
            "Shapiro-Wilk": lambda: self._shapiro(c1),
            "Curva ROC": lambda: self._roc(c1, c3),
            "Bland-Altman": lambda: self._bland(c1, c2),
            "Passing-Bablok": lambda: self._passing(c1, c2),
            "Kaplan-Meier": lambda: self._kaplan_meier(c1, c2),
            "Log-rank test": lambda: self._log_rank(c1, c2, c3),
            "Meta-analisis": lambda: self._meta(c1, c2),
            "Tamano muestral (1 media)": lambda: self._ss_mean(),
            "Tamano muestral (2 medias)": lambda: self._ss_two_means(),
            "Tamano muestral (2 proporciones)": lambda: self._ss_prop(),
            "Poder estadistico": lambda: self._power(),
            "Bootstrap (media)": lambda: self._boot_mean(c1),
            "Bootstrap (diferencia)": lambda: self._boot_diff(c1, c2),
            "Bootstrap (correlacion)": lambda: self._boot_corr(c1, c2),
            "Random Forest (clasificacion)": lambda: self._rf_class(c1, c2),
            "Random Forest (regresion)": lambda: self._rf_regress(c1, c2),
            "Mann-Whitney U": lambda: self._mannwhitney(c1, c2),
            "Wilcoxon pareado": lambda: self._wilcoxon(c1, c2),
            "Chi-cuadrado": lambda: self._chi2(),
            "Fisher exact": lambda: self._fisher(),
            "McNemar": lambda: self._mcnemar(),
            "Kruskal-Wallis": lambda: self._kruskal(),
            "Friedman": lambda: self._friedman(),
            "F-test (varianzas)": lambda: self._ftest(c1, c2),
            "Kappa": lambda: self._kappa(),
            "ICC": lambda: self._icc(c1, c2),
            "Cronbach alfa": lambda: self._cronbach(),
            "Regresion lineal": lambda: self._reg_lineal(c1, c2),
            "Regresion multiple": lambda: self._reg_multiple(),
            "Regresion logistica": lambda: self._reg_logistica(),
            "Odds Ratio": lambda: self._odds_ratio(),
            "Riesgo Relativo": lambda: self._riesgo_relativo(),
            "Diagnostic test": lambda: self._diag_test(),
            "Outliers (Grubbs)": lambda: self._outliers_grubbs(c1),
            "Outliers (Tukey)": lambda: self._outliers_tukey(c1),
            "Intervalos de referencia": lambda: self._ref_interval(c1),
            "Asimetria y curtosis": lambda: self._skew_kurt(c1),
            "Media recortada": lambda: self._trimmed(c1),
            "Correlacion parcial": lambda: self._partial_corr(c1, c2, c3),
            "Media geometrica": lambda: self._run_core("geometric_mean", c1),
            "Media armonica": lambda: self._run_core("harmonic_mean", c1),
            "t-test 1 muestra": lambda: self._run_core("ttest_1sample", c1),
            "ANOVA una via (core)": lambda: self._run_core("anova_oneway"),
            "Sign test": lambda: self._run_core("sign_test", c1, c2),
            "Cochran Q": lambda: self._run_core("cochran_q"),
            "Kappa ponderado": lambda: self._run_core("weighted_kappa"),
            "Deming regression": lambda: self._run_core("deming", c1, c2),
            "CV duplicatas": lambda: self._run_core("cv_duplicates", c1, c2),
            "Likelihood Ratios": lambda: self._run_core("likelihood_ratios"),
            "Comparar 2 medias": lambda: self._run_core("compare_means"),
            "Comparar 2 proporciones": lambda: self._run_core("compare_props"),
            "Comparar 2 AUC": lambda: self._run_core("compare_auc"),
            "Tabla de percentiles": lambda: self._run_core("percentile_table", c1),
            "Edad-relacionada": lambda: self._run_core("age_related"),
            "Outliers (ESD)": lambda: self._run_core("generalized_esd", c1),
            "Bootstrap (mediana)": lambda: self._run_core("bootstrap_median", c1),
            "Bootstrap (regresion)": lambda: self._run_core("bootstrap_regression", c1, c2),
            "Tamaño muestral (correlacion)": lambda: self._run_core("sample_size_corr", c1, c2),
            "ANOVA dos vias": lambda: self._run_two_way_anova(c1, c2, c3),
            "ANCOVA": lambda: self._run_ancova(c1, c2, c3),
            "Medidas repetidas": lambda: self._run_repeated_measures(),
            "Cox regression": lambda: self._run_cox(c1, c2),
            "Probit regression": lambda: self._run_probit(c1, c2),
            "CMH test": lambda: self._run_cmh(),
            "Mediciones seriales": lambda: self._run_serial(),
            "Youden plot": lambda: self._run_youden(c1, c3),
            "Polar plot": lambda: self._run_polar(),
            "Waterfall chart": lambda: self._run_waterfall(c1),
            "Mountain plot": lambda: self._run_mountain(c1),
            "Bland-Altman múltiple": lambda: self._run_bland_multi(),
        }
        fn = dispatch.get(at)
        if fn:
            self.txt_results.setHtml(fn())

    def _show_fig(self, fig):
        self.canvas = FigureCanvas(fig)
        self.graph_scroll.setWidget(self.canvas)
        plt.close(fig)

    def _clear(self):
        self.txt_results.clear()
        self.txt_formula.clear()
        self.graph_scroll.setWidget(self.graph_ph)

    def _h(self, t):
        return f"<div style='border-bottom:2px solid #4f6ef7;padding-bottom:5px;margin-bottom:10px;'><b style='color:#2c3650;font-size:14px;'>{t}</b></div>"

    def _r(self, l, v):
        return f"<tr><td style='padding:2px 12px 2px 0;color:#8892a4;'>{l}</td><td style='padding:2px 0;font-weight:600;'>{v}</td></tr>"

    def _ok(self, yes, msg_yes="SIGNIFICATIVO", msg_no="NO SIGNIFICATIVO"):
        if yes:
            return f"<div style='margin-top:10px;padding:8px;border-radius:6px;background:#ecfdf5;border-left:3px solid #22c55e;'><b style='color:#16a34a;'>{Icons.CHECK()} {msg_yes}</b></div>"
        return f"<div style='margin-top:10px;padding:8px;border-radius:6px;background:#fef9ee;border-left:3px solid #f59e0b;'><b style='color:#d97706;'>{Icons.WARN()} {msg_no}</b></div>"

    def _set_formula(self, title, formula_text, steps=None):
        """Muestra formula y pasos en el recuadro de auditoria."""
        html = f"<b style='color:#2c3650;'>{title}</b><br><br>"
        html += f"<span style='font-family:Consolas,monospace; color:#4f6ef7;'>{formula_text}</span>"
        if steps:
            html += "<br><br><b>Pasos:</b><br>"
            html += "<span style='font-family:Consolas,monospace; font-size:11px;'>"
            html += steps.replace("\n", "<br>")
            html += "</span>"
        self.txt_formula.setText(html)

    # --- Estadisticas descriptivas ---
