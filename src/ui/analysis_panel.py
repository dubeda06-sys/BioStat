"""Panel de analisis estadistico."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QPushButton, QLabel, QTextEdit, QGroupBox,
    QLineEdit, QFormLayout, QScrollArea, QSplitter
)
from PyQt6.QtCore import Qt
import matplotlib
matplotlib.use('QtAgg')
from src.ui.grafico_editable import GraficoEditable
import matplotlib.pyplot as plt

from src.ui.icons import Icons
from src.resultado import render_html

plt.rcParams.update({
    'figure.facecolor': 'white', 'axes.facecolor': '#fafbfd',
    'axes.edgecolor': '#d8dbe3', 'axes.grid': True,
    'grid.alpha': 0.25, 'grid.color': '#d8dbe3',
    'font.size': 11, 'axes.titlesize': 13,
})

from src.ui.help_text import ANALYSIS_HELP
from src.ui import entradas

ANALYSIS_LEGENDS = {
    "Estadisticas descriptivas": {
        "legend": "Proporciona un resumen numérico fundamental (media, mediana, DE, etc.). Úselo en la fase inicial del análisis para entender la distribución y calidad de los datos numéricos antes de aplicar pruebas inferenciales.",
        "formula": "Media: x̄ = Σxi / n\nDE: s = √[Σ(xi − x̄)² / (n−1)]\nIC 95%: x̄ ± t(n−1)·s/√n\nCV%: (s / x̄) × 100"
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
        "formula": "y = β₀ + β₁x (mediana desplazada de las pendientes por pares)\nIC de la pendiente con el 1 y del intercepto con el 0 → no se detecta sesgo;\ncon un IC muy ancho no se puede afirmar nada"
    },
    "Kaplan-Meier": {
        "legend": "Estima la probabilidad de que los pacientes sobrevivan a lo largo del tiempo sin experimentar un evento (ej. muerte o recaída). Requiere datos de tiempo de seguimiento y el estado final (evento o censurado).",
        "formula": "S(t) = Π[(nᵢ - dᵢ) / nᵢ]\ndonde nᵢ = en riesgo, dᵢ = eventos"
    },
    "Log-rank test": {
        "legend": "Compara estadísticamente dos o más curvas de supervivencia de Kaplan-Meier. Úselo para evaluar si un tratamiento mejora el tiempo de supervivencia frente a un grupo control.",
        "formula": "χ² = (O₁ − E₁)² / V\nO₁ = eventos observados en el grupo 1, E₁ = esperados,\nV = Σ d·n₁·n₂·(n − d) / (n²(n − 1)) en cada tiempo de evento"
    },
    "Meta-analisis": {
        "legend": "Sintetiza matemáticamente los resultados de múltiples estudios independientes. Úselo para obtener una estimación global y más potente del tamaño del efecto (ej. odds ratio global) de una intervención.",
        "formula": "EF = Σ(wᵢ × EFᵢ) / Σ(wᵢ)\nwᵢ = 1 / SEᵢ²\nI² = (Q - df) / Q × 100%"
    },
    "Tamano muestral (1 media)": {
        "legend": "Calcula cuántos pacientes necesita reclutar para demostrar que la media de su muestra difiere de un valor de referencia conocido, considerando la potencia y significancia deseadas.",
        "formula": "El n más chico cuyo poder EXACTO llega al pedido\n(t no central, gl = n − 1, λ = (δ/σ)·√n)"
    },
    "Tamano muestral (2 medias)": {
        "legend": "Calcula la cantidad de pacientes necesarios para detectar una diferencia clínica importante entre dos grupos independientes. Es crucial para el diseño de ensayos clínicos.",
        "formula": "El n₁ más chico cuyo poder EXACTO llega al pedido, n₂ = r·n₁\n(t no central, λ = (δ/σ)/√(1/n₁ + 1/n₂))"
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
        "formula": "b + c < 25: binomial exacta;  si no, χ² = (|b − c| − 1)² / (b + c)\nb y c = pares discordantes"
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
        "formula": "ICC(A,1) = (MS_suj − MS_err) / (MS_suj + (k−1)·MS_err + k·(MS_met − MS_err)/n)\ndos vías, acuerdo absoluto; k = número de métodos"
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
        "formula": "Límites: datos de rango 0,025·(n+1) y 0,975·(n+1) (CLSI EP28 §9.4.1)\nIC 90% de cada límite por rangos de orden (tabla 8), n ≥ 119"
    },
    "Asimetria y curtosis": {
        "legend": "Métricas que evalúan formalmente la forma de la distribución de los datos. Desviaciones significativas de 0 indican que los datos están sesgados (colas asimétricas) o son muy apuntados.",
        "formula": "g1 = m₃/m₂^1,5;  g2 = m₄/m₂² − 3\nPruebas: D'Agostino (asimetría) y Anscombe-Glynn (curtosis)"
    },
    "Media recortada": {
        "legend": "Calcula la media descartando un porcentaje (ej. 5%) de los valores más extremos superiores e inferiores. Proporciona un estimado robusto de la tendencia central resistente a outliers.",
        "formula": "Media recortada = promedio sin el 10% de cada cola\nEE = DE winsorizada / ((1 − 2·0,1)·√n)  (Tukey-McLaughlin)"
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
        "formula": "d = medición 1 − medición 2;  DE intraserie = DE(d) / √2\nCV = DE intraserie / media general × 100"
    },
    "Likelihood Ratios": {
        "legend": "Razones de verosimilitud (LR+ y LR-) que indican cuánto cambia la probabilidad post-prueba de una enfermedad. LR+ alto (>10) confirma; LR- bajo (<0.1) descarta firmemente.",
        "formula": "LR+ = Sens / (1 - Spec)\nLR- = (1 - Sens) / Spec\nPre-odds × LR = Post-odds"
    },
    "Comparar 2 medias": {
        "legend": "Compara las medias de dos grupos a partir de la media, la DE y el n de cada uno, sin los datos crudos.",
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
        "formula": "Pₖ = valor en la posición k·(n+1)/100, interpolado\nIC por bootstrap"
    },
    "Edad-relacionada": {
        "legend": "Intervalos de referencia que cambian con la edad: centiles por regresión (Altman 1993) o percentiles de EP28 por grupos de edad.",
        "formula": "Media(edad) y DE(edad) por regresión; centiles = media ± 1,96·DE (Altman 1993)"
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
        "legend": "El número de sujetos para detectar una correlación esperada (r, de un piloto o de la literatura), con el alfa y el poder que se eligen en el diálogo.",
        "formula": "n = [(Z_α/2 + Z_β) / arctanh(r)]² + 3"
    },
    "ANOVA dos vias": {
        "legend": "Analiza simultáneamente el efecto de dos variables categóricas independientes sobre una respuesta continua. También evalúa si existe interacción entre los factores.",
        "formula": "F_factor = MS_factor / MS_error\nF_interacción = MS_AB / MS_error"
    },
    "ANCOVA": {
        "legend": "Análisis de covarianza. Compara grupos ajustando por variables continuas de confusión (covariables, ej. edad basal). Aumenta el poder estadístico al reducir el error residual.",
        "formula": "y = b₀ + grupo + b·covariable; F del grupo con SS tipo II\nη² parcial = SS_grupo / (SS_grupo + SS_error)"
    },
    "Medidas repetidas": {
        "legend": "Compara promedios de la misma variable medida en múltiples ocasiones en los mismos sujetos. Aplica correcciones automáticas (Greenhouse-Geisser) para violaciones de esfericidad.",
        "formula": "F = MS_tiempo / MS_error\nGG: ε = (Σλᵢ)² / ((k−1)·Σλᵢ²), λ = autovalores de la covarianza doblemente centrada"
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
        "formula": "Pendiente de cada sujeto contra el tiempo\nTendencia: t de una muestra sobre las pendientes (Matthews et al. 1990)"
    },
    "Youden plot": {
        "legend": "Gráfico de Youden interlaboratorio: cada laboratorio midió dos muestras y es un punto. Lejos de la recta de 45°, error aleatorio; sobre la recta y lejos del centro, error sistemático del laboratorio.",
        "formula": "Centro = mediana de Manhattan; círculo del 95 %: radio = 2,448·s"
    },
    "Polar plot": {
        "legend": "Gráfico de radar utilizado para visualizar y comparar simultáneamente múltiples parámetros (ej. panel de citocinas) entre grupos o estados de la enfermedad.",
        "formula": "Ángulos = 2π × i/k\nejes = cada variable normalizada"
    },
    "Waterfall chart": {
        "legend": "Una barra por sujeto con su cambio (por ejemplo, % respecto del basal), ordenadas de mayor a menor.",
        "formula": "Barras ordenadas de mayor a menor; color según el signo"
    },
    "Mountain plot": {
        "legend": "También conocido como gráfico de distribución plegada (folded empirical CDF). Muestra de forma muy sensible las diferencias de distribución o sesgos entre dos métodos clínicos.",
        "formula": "d = método 1 − método 2, ordenadas\npercentil = 100·rango/(n+1); por encima de 50 se pliega: 100 − percentil"
    },
    "Bland-Altman múltiple": {
        "legend": "Compara varios métodos contra uno de referencia, cada uno con su sesgo y sus límites de acuerdo, graficados contra la referencia (Krouwer). La Variable 1 es la referencia; los métodos se tildan en el diálogo.",
        "formula": "Para cada método: d = método − referencia;  sesgo ± 1,96·DE(d)"
    },
    "Validar un método": {
        "legend": "Asistente de verificación de un método nuevo contra el que está en uso (CLSI EP09c + EP15-A3). Corre Bland-Altman con el CCC, elige la recta según la forma de los datos, estima el sesgo en los niveles de decisión médica con su IC y lo compara con el sesgo permitido: un solo veredicto, con cada análisis debajo.",
        "formula": "sesgo(Xc) = a + (b − 1)·Xc\nCumple: IC 95 % entero dentro de ±permitido; no cumple: entero afuera; no concluyente: lo cruza"
    },
    "Precisión EP15": {
        "legend": "Verificación de precisión y estimación del sesgo del usuario (CLSI EP15-A3): 5 corridas de 5 réplicas. Estima repetibilidad e intralaboratorio, los compara con lo que declara el fabricante y, si el material tiene valor asignado, dice si el sesgo se distingue del azar.",
        "formula": "s_R = √MS dentro;  s_WL = √(MS dentro + (MS entre − MS dentro)/n0)\nUVL = σ declarada · √(χ²(1−α/nMuestras; gl)/gl)"
    },
}


class AnalysisPanel(QWidget):
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

        cfg = QGroupBox(f"    Configuracion")
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

        rg = QGroupBox(f"    Resultados")
        rl = QVBoxLayout()
        rl.setContentsMargins(4, 2, 4, 2)
        self.txt_results = QTextEdit()
        self.txt_results.setReadOnly(True)
        self.txt_results.setPlaceholderText("Resultados...")
        rl.addWidget(self.txt_results)
        rg.setLayout(rl)
        right_l.addWidget(rg, stretch=2)

        pg = QGroupBox(f"    Grafico")
        pl = QVBoxLayout()
        pl.setContentsMargins(4, 2, 4, 2)
        self.graph_scroll = QScrollArea()
        self.graph_scroll.setWidgetResizable(True)
        self.graph_ph = QLabel(f"<div style='text-align:center;color:#a0a8b8;padding:20px;'> El grafico aparecera aqui</div>")
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
        # Lo que dejo el dialogo es de UN analisis: al cambiar de analisis no
        # puede quedar colgado para el siguiente.
        self.opciones_metodo = {}
        self.columnas_elegidas = None
        self.parametros = {}
        
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

    # Decisiones de metodo que deja el dialogo (ver analysis_specs.OPCIONES).
    # Vacio = cada analisis usa sus valores por defecto.
    opciones_metodo: dict = {}
    # Columnas tildadas en el dialogo (analysis_specs.MULTI). None = no hubo
    # dialogo: se usan todas las numericas y el informe las nombra.
    columnas_elegidas = None
    # Parametros numericos del dialogo (analysis_specs.PARAMETROS), como texto.
    parametros: dict = {}

    def _run(self):
        if self.data is None:
            self.txt_results.setHtml(f"<div style='color:#d97706;padding:12px;'> <b>Sin datos.</b> Importa un archivo en la pestaña Datos.</div>")
            return

        at = self.combo_analysis.currentText()
        if at not in entradas.ENTRADAS:
            return
        c3 = self.combo_col3.currentText()
        try:
            alpha = float(self.input_alpha.text())
        except ValueError:
            alpha = 0.05
        self._mostrar_resultado(self.correr(
            at, self.combo_col1.currentText() or None, self.combo_col2.currentText() or None,
            None if c3 in ("", "(ninguna)") else c3, alpha))

    def correr(self, nombre, c1=None, c2=None, c3=None, alpha=0.05):
        """El análisis `nombre` con estas variables y lo que dejó el diálogo.

        Lo arma `src/ui/entradas.py`; acá solo se junta el estado del panel.
        Devuelve el `Resultado` sin mostrarlo.
        """
        return entradas.correr(nombre, entradas.Eleccion(
            self.data, c1, c2, c3, alpha, dict(self.opciones_metodo or {}),
            self.columnas_elegidas, dict(self.parametros or {})))

    def _mostrar_resultado(self, res):
        self.txt_results.setHtml(render_html(res))
        if not res.ok:
            return
        if res.formula:
            titulo = res.metodo.nombre if res.metodo else res.titulo
            self._set_formula(f"Formula: {titulo}", res.formula)
        if res.figuras:
            self._mostrar_figuras(res.figuras)

    def _mostrar_figuras(self, figuras):
        """Una figura va sola, como siempre. Varias se apilan con su titulo, igual
        que en la pestaña Graficos del Omnianalisis: se ven todas sin tener que
        elegir, y la ventana de informe se lleva el bloque entero."""
        if len(figuras) == 1:
            self._show_fig(figuras[0].dibujar())
            return
        anterior = self._vaciar_grafico()
        if anterior is not None:
            anterior.deleteLater()
        bloque = QWidget()
        caja = QVBoxLayout(bloque)
        caja.setContentsMargins(0, 0, 0, 0)
        for figura in figuras:
            fig = figura.dibujar()
            titulo = QLabel(figura.titulo)
            titulo.setStyleSheet("font-weight:bold; color:#2c3650; padding:8px 2px 2px;")
            caja.addWidget(titulo)
            grafico = GraficoEditable(fig)
            grafico.setMinimumHeight(380)
            caja.addWidget(grafico)
            plt.close(fig)
        self.canvas = bloque
        self.graph_scroll.setWidget(bloque)

    def _vaciar_grafico(self):
        """Saca lo que haya en el area de grafico y lo devuelve.

        `QScrollArea.setWidget` se queda con la propiedad del widget y destruye
        el anterior: poner un grafico borraba el cartel de "aparecera aqui", y
        el siguiente `_clear` reventaba con "wrapped C/C++ object of type QLabel
        has been deleted". `takeWidget` devuelve la propiedad primero.
        """
        actual = self.graph_scroll.takeWidget()
        return None if actual is self.graph_ph else actual

    def _show_fig(self, fig):
        anterior = self._vaciar_grafico()
        if anterior is not None:
            anterior.deleteLater()
        # GraficoEditable y no FigureCanvas pelado: agrega la barra de
        # matplotlib (zoom, desplazamiento, guardar) y el dialogo de estilo.
        # Expone .figure y .draw(), asi que la ventana de informe lo sigue
        # tratando igual que antes.
        self.canvas = GraficoEditable(fig)
        self.graph_scroll.setWidget(self.canvas)
        plt.close(fig)

    def tomar_grafico(self):
        """Entrega el grafico actual (para la ventana de informe) y repone el cartel."""
        canvas = self._vaciar_grafico()
        self.canvas = None
        self.graph_scroll.setWidget(self.graph_ph)
        return canvas

    def _clear(self):
        self.txt_results.clear()
        self.txt_formula.clear()
        anterior = self._vaciar_grafico()
        if anterior is not None:
            anterior.deleteLater()
        self.graph_scroll.setWidget(self.graph_ph)

    def _h(self, t):
        return f"<div style='border-bottom:2px solid #4f6ef7;padding-bottom:5px;margin-bottom:10px;'><b style='color:#2c3650;font-size:14px;'>{t}</b></div>"

    def _r(self, l, v):
        return f"<tr><td style='padding:2px 12px 2px 0;color:#8892a4;'>{l}</td><td style='padding:2px 0;font-weight:600;'>{v}</td></tr>"

    def _ok(self, yes, msg_yes="Se detectó diferencia", msg_no="No se detectó diferencia"):
        """El veredicto de una prueba, en castellano llano.

        Sin la palabra «significativo», que se lee como «importante»: lo mismo
        que ya decidio el Omnianalisis (decision 2 de la propuesta de Resultado).
        Y el caso negativo dice que no detectar no es probar que no hay.
        """
        if yes:
            return (f"<div style='margin-top:10px;padding:8px;border-radius:6px;background:#ecfdf5;"
                    f"border-left:3px solid #22c55e;'><b style='color:#16a34a;'>{msg_yes}</b> "
                    f"(p &lt; α)<br><span style='font-size:11px;'>Que sea detectable no dice que "
                    f"sea grande: el tamaño lo dan la diferencia y su intervalo.</span></div>")
        return (f"<div style='margin-top:10px;padding:8px;border-radius:6px;background:#fef9ee;"
                f"border-left:3px solid #f59e0b;'><b style='color:#d97706;'>{msg_no}</b> (p ≥ α)"
                f"<br><span style='font-size:11px;'>No detectarlo no prueba que no exista: con "
                f"pocos datos puede pasar desapercibido.</span></div>")

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
