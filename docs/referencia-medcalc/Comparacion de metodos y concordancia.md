---
tags: [medcalc, formulas, estadistica, referencia]
tipo: referencia
version: 23.6.5.0
grupo: comparacion-de-metodos
formulas: 48
paginas: 9
fecha_extraccion: 2026-08-13
---

# MedCalc - Formulas - Comparacion de metodos y concordancia

Volver a [[MedCalc - Mapa]] | indice de procedimientos: [[MedCalc - Procedimientos estadisticos]]

**48 formulas** extraidas de **9 paginas** del manual oficial de MedCalc.

> [!info] Procedencia
> Cada formula es transcripcion literal de la pagina del manual que se cita debajo de ella.
> No hay formulas escritas de memoria: si el manual no la publica, aca dice que no la publica.
> Notacion ASCII (`sqrt`, `^`, `*`, `+/-`) conservando los nombres de simbolo de la pagina.
> Manual leido: el **ingles** (`/en/manual/`); las formulas y las frases entre comillas quedan en ingles.
> Estado de verificacion de esta cosecha (que paginas se re-chequearon y cual no): ver [[MedCalc - Mapa]].

---

## Bland-Altman plot

`bland-altman-plot.php` - https://www.medcalc.org/en/manual/bland-altman-plot.php

Pagina principal del grafico de Bland-Altman. Documenta las 3 metodologias que ofrece MedCalc (Parametric conventional, Non-Parametric, Regression-Based), las opciones del cuadro de dialogo (eje X, diferencias / diferencias en % / razones, maxima diferencia permitida, linea de igualdad, IC 95%, recta de regresion de las diferencias, subgrupos), la interpretacion, el informe y el Coefficient of Repeatability. Es la unica pagina del grupo que trae formulas algebraicas explicitas (MathJax/LaTeX incrustado, ademas de la version SVG renderizada). Las formulas de la seccion regression-based se atribuyen literalmente a Bland-Altman 1999, Eqs 3.1, 3.2 y 3.3.

**Referencias que cita la pagina:** Abu-Arafeh A, Jordan H, Drummond G (2016) Reporting of method comparison studies: a review of advice, an assessment of current practice, and specific suggestions for future reports. British Journal of Anaesthesia 117:569-575. | Barnhart HX, Barboriak DP (2009) Applications of the repeatability of quantitative imaging biomarkers: a review of statistical analysis of repeat data sets. Translational Oncology 2:231-235. | Bland JM, Altman DG (1986) Statistical method for assessing agreement between two methods of clinical measurement. The Lancet i:307-310. | Bland JM, Altman DG (1995) Comparing methods of measurement: why plotting difference against standard method is misleading. The Lancet 346:1085-1087. | Bland JM, Altman DG (1999) Measuring agreement in method comparison studies. Statistical Methods in Medical Research 8:135-160. | CLSI (2013) Measurement procedure comparison and bias estimation using patient samples; Approved guideline - 3rd edition. CLSI document EP09-A3. Wayne, PA: Clinical and Laboratory Standards Institute. | Gerke O (2020) Reporting Standards for a Bland-Altman Agreement Analysis: A Review of Methodological Reviews. Diagnostics 10, no. 5: 334. | Hanneman SK (2008) Design, analysis, and interpretation of method-comparison studies. AACN Advanced Critical Care 19:223-234. | Krouwer JS (2008) Why Bland-Altman plots should use X, not (Y+X)/2 when X is a reference method. Statistics in Medicine 27:778-780. | Jensen AL, Kjelgaard-Hansen M (2010) Diagnostic test validation. In: Weiss D, Wardrop KJ, editors. Schalm's Veterinary Hematology, 6th ed. Ames: Wiley-Blackwell; p. 1027-1033. | Stockl D, Rodriguez Cabaleiro D, Van Uytfanghe K, Thienpont LM (2004) Interpreting method comparison studies by use of the Bland-Altman plot: reflecting the importance of sample size by incorporating confidence limits and predefined error limits in the graphic. Clinical Chemistry 50:2216-2218.

### Limites de concordancia (LoA) - metodo parametrico (conventional)

```
LoA = mean difference +/- 1.96 * (standard deviation of the differences)
```

**Simbolos / literal de la pagina.** La pagina lo enuncia en prosa dos veces: "Horizontal lines are drawn at the mean difference, and at the limits of agreement, which are defined as the mean difference plus and minus 1.96 times the standard deviation of the differences" y "In the parametric approach, the limits of agreement (LoA) are calculated as the mean difference +/- 1.96 times the standard deviation of the differences". mean difference = media de las diferencias entre los dos metodos (el informe la llama Arithmetic mean y es el bias); SD of the differences = desvio estandar de esas diferencias. Objetivo declarado: "define an interval within which 95% of the differences between measurements are expected to lie". No se imprime la formula algebraica del SD ni la del IC.

**Supuestos / condiciones.** Opcion Parametric (conventional): "Assumes constant bias and homoscedasticity (Bland & Altman 1986)". En el grafico original las diferencias se representan contra el promedio de los dos metodos.

**Intervalo de confianza.** La pagina indica que el informe entrega "the exact values and confidence intervals for average difference (bias) and the limits of agreement", y que la opcion "95% CI of limits of agreement" muestra barras de error con el IC 95% de ambos LoA citando Bland & Altman, 1999. No se imprime la formula del IC.

### Limites de concordancia (LoA) - metodo no parametrico

```
LoA (non-parametric) = [2.5th percentile of the differences , 97.5th percentile of the differences]
```

**Simbolos / literal de la pagina.** Texto literal: "In the non-parametric approach, the LoA are defined by the 2.5th and 97.5th percentiles of the differences". Ambos enfoques (parametrico y no parametrico) buscan el intervalo que contiene el 95% de las diferencias.

**Supuestos / condiciones.** Opcion Non-Parametric: "uses ranks or quantiles to assess agreement without assuming normality or constant variance (Bland & Altman 1999)". No exige normalidad ni varianza constante.

### Regresion de las diferencias sobre los promedios (metodo regression-based, paso 1)

```
\hat{D} = b_0 + b_1 A
```

**Simbolos / literal de la pagina.** Literal de la pagina (MathJax): "First, the differences $D$ are regressed on the averages $A$, yielding: $ \hat{D} = b_0 + b_1 A $". D = las diferencias entre los dos metodos; A = los promedios de los dos metodos; b_0 y b_1 = intercepto y pendiente de esa regresion. La pagina NO imprime la definicion algebraica de D ni de A (solo los nombra en prosa como differences y averages).

**Supuestos / condiciones.** Opcion Regression-Based: "models bias and limits of agreement as functions of the measurement magnitude. Useful when heteroscedasticity is present (Bland & Altman 1999)". Atribuida a Bland-Altman, 1999; Eqs 3.1, 3.2 and 3.3.

**Intervalo de confianza.** El informe de ejemplo lista, para esta regresion, Coefficient, SE, t, P y 95% CI de Intercept y Slope, mas la Residual standard deviation; la pagina no explicita el metodo de calculo del IC.

### Regresion de los residuos absolutos sobre los promedios (metodo regression-based, paso 2)

```
\hat{R} = c_0 + c_1 A
```

**Simbolos / literal de la pagina.** Literal: "Next, the absolute residuals $R$ from this regression are regressed on the averages: $ \hat{R} = c_0 + c_1 A $". R = residuos absolutos de la regresion del paso 1; A = promedios de los dos metodos; c_0 y c_1 = intercepto y pendiente de la regresion de los residuos absolutos.

**Supuestos / condiciones.** Segundo paso del procedimiento de Bland-Altman 1999 (Eqs 3.1, 3.2, 3.3).

### Limites de concordancia dependientes de la magnitud (LoA regression-based)

```
LoA = b_0 + b_1 A \pm 2.46 \{ c_0 + c_1 A \}
```

**Simbolos / literal de la pagina.** Literal: "the limits of agreement (LoA) are then given by: $ b_0 + b_1 A \pm 2.46 \{ c_0 + c_1 A \} $". El factor 2.46 esta impreso tal cual en la pagina. Los LoA dejan de ser dos rectas horizontales y pasan a ser funciones del promedio A.

**Supuestos / condiciones.** Bland-Altman, 1999; Eqs 3.1, 3.2 and 3.3. Recomendado cuando hay heterocedasticidad (ejemplos 2 y 3 de la pagina).

### LoA regression-based reescritos - limite inferior

```
Lower limit: (b_0 - 2.46\ c_0) + (b_1 - 2.46\ c_1)\ A
```

**Simbolos / literal de la pagina.** Reescritura literal que da la pagina ("These can be rewritten as"). En el informe de ejemplo aparece instanciado como "Lower Limit of Agreement = -2.1552 + 0.06178 x".

### LoA regression-based reescritos - limite superior

```
Upper limit: (b_0 + 2.46\ c_0) + (b_1 + 2.46\ c_1)\ A
```

**Simbolos / literal de la pagina.** Reescritura literal de la pagina. En el informe de ejemplo: "Upper Limit of Agreement = 2.6303 - 0.08940 x".

### Limits of Agreement Area (LoAA)

```
LoAA = area between the limits of agreement curves over the interval [ x_{min}, x_{max} ]
```

**Simbolos / literal de la pagina.** Literal: "The area between the limits of agreement curves (LoAA) over the interval $ [ x_{min}, x_{max} ] $ provides a summary measure of overall disagreement between the two measurement methods". x_min y x_max delimitan el rango de los valores observados. La pagina define el LoAA verbalmente como el area entre las dos curvas de LoA; NO imprime la integral. En el informe de ejemplo LoAA = 23.6960.

**Supuestos / condiciones.** Solo disponible en el metodo Regression-Based; se lista en el informe junto con las ecuaciones de regresion.

### Coefficient of Repeatability (CR)

```
CR = 1.96 \times \sqrt{\frac{\sum{(d_2-d_1)^2}}{n}}
```

**Simbolos / literal de la pagina.** Formula en display MathJax, literal. d_1 y d_2 = las dos mediciones repetidas con un mismo metodo sobre cada sujeto; n = numero de casos. La pagina aclara: "Since for the repeated measurements the same method is used, the mean difference should be zero. Therefore the Coefficient of Repeatability (CR) can be calculated as 1.96 (or 2) times the standard deviation of the differences between the two measurements (d2 and d1) (Bland & Altman, 1986)". Se obtiene en el panel Info del grafico. No se reporta si se eligio "Plot ratios".

**Supuestos / condiciones.** Aplica al uso del Bland-Altman plot (metodo parametrico) para evaluar repetibilidad de UN solo metodo con mediciones repetidas; se asume media de las diferencias igual a cero.

**Intervalo de confianza.** "The 95% confidence interval for the Coefficient of Repeatability is calculated according to Barnhart & Barborial, 2009" (asi escrito en el cuerpo del texto; en la bibliografia la referencia figura como Barnhart HX, Barboriak DP, 2009).

### Maxima diferencia permitida - imprecision inherente combinada de los dos metodos

```
(CV^2_method1 + CV^2_method2)^(1/2)   ; con mediciones duplicadas: [(CV^2_method1 /2)+ (CV^2_method2)/2)]^(1/2)
```

**Simbolos / literal de la pagina.** Transcripcion ASCII de lo impreso con sup/sub en la pagina: "the combined inherent imprecision of both methods is calculated (CV2method1 + CV2method2)1/2, or in case of duplicate measurements [(CV2method1 /2)+ (CV2method2)/2)]1/2". CV = coeficiente de variacion de cada metodo. Los parentesis de la segunda expresion estan desbalanceados en la pagina original y se reproducen tal cual, sin corregir.

**Supuestos / condiciones.** Primer enfoque de Jensen & Kjelgaard-Hansen (2010) para fijar la maxima diferencia permitida. La pagina menciona dos enfoques mas: (2) limites de aceptacion basados en especificaciones analiticas de calidad, p.ej. las de CLIA (Clinical Laboratory Improvement Amendments), y (3) un tercer enfoque basado en requerimientos clinicos.

### Criterio de decision de concordancia con la maxima diferencia permitida

```
Delta > upper 95% CI limit of the higher LoA   AND   -Delta < lower 95% CI limit of the lower LoA
```

**Simbolos / literal de la pagina.** Literal: "Proper interpretation (Stockl et al., 2004) considers the 95% confidence interval of the LoA, and to be 95% certain that the methods do not disagree, Delta must be higher than the upper 95 CI limit of the higher LoA and -Delta must be less than the lower 95% CI limit of the lower LoA". Delta (&Delta;) = maxima diferencia permitida entre metodos; en la seccion de opciones del dialogo la misma cantidad se denomina D: "The value D must be chosen so that differences in the range -D to D (for ratios 1/D to D) are clinically irrelevant or neglectable". Criterio mas laxo tambien enunciado: "If limits of agreement do not exceed the maximum allowed difference between methods Delta ... the two methods are considered to be in agreement and may be used interchangeably".

**Supuestos / condiciones.** Se recomienda (Stockl et al., 2004; Abu-Arafeh et al., 2016) ingresar un valor para "Maximum allowed difference between methods" y activar la opcion "95% CI of limits of agreement".

**Intervalo de confianza.** Usa el IC 95% de los limites de concordancia (opcion 95% CI of limits of agreement, Bland & Altman, 1999).

### Definiciones computacionales del eje X y de la escala de las diferencias

```
X-axis = average of the two methods (default) | one of the two methods (reference / gold standard) | geometric mean of both methods | sample rank (ranked by the average of the two methods), rank of the first method, or rank of the second method ; Y = differences | differences as % of the observations represented on the X-axis | ratios
```

**Simbolos / literal de la pagina.** Opciones literales del dialogo. El grafico original (Bland & Altman, 1986) usa el promedio de los dos metodos; graficar contra uno de los metodos cuando este es referencia o "gold standard" se atribuye a Krouwer, 2008; las variantes por rango "will give a 'Ranked order difference plot' according to CLSI, 2013". Para "Plot differences as %" las diferencias se expresan como porcentaje de las observaciones del eje X.

**Supuestos / condiciones.** Para "Plot ratios": "MedCalc performs the calculations on log-transformed data in the background" y el programa avisa si alguno de los dos metodos contiene valores cero. Las opciones % y ratios se recomiendan cuando la variabilidad de las diferencias crece con la magnitud de la medicion.

---

## Passing-Bablok regression

`passing-bablok-regression.php` - https://www.medcalc.org/en/manual/passing-bablok-regression.php

Pagina de procedimiento e interpretacion. NO imprime la formula algebraica del estimador de la pendiente B ni del intercepto A: los atribuye por completo a Passing & Bablok (1983). Si define computacionalmente el intervalo de diferencias aleatorias, el criterio de outlier, las pruebas de hipotesis via IC y el uso del Cusum test. Incluye recomendaciones de tamano de muestra.

**Referencias que cita la pagina:** Bablok W, Passing H (1985) Application of statistical procedures in analytical instrument testing. Journal of Automatic Chemistry 7:74-79. | CLSI (2018) Measurement procedure comparison and bias estimation using patient samples. 3rd ed. CLSI guideline EP09c. Wayne, PA: Clinical and Laboratory Standards Institute. | Linnet K, Boyd JC (2012) Selection and analytical evaluation of methods - with statistical techniques. In Burtis CA, Ashwood ER, Bruns DE (eds). Tietz Textbook of Clinical Chemistry and Molecular Diagnostics (5th ed). Elsevier Saunders, St Louis, MO, pp. 201-228. | Ludbrook J (2010) Linear regression analysis for comparing two measures or methods of measurement: but which regression? Clinical and Experimental Pharmacology & Physiology 37:692-699. | Mayer B, Gaus W, Braisch U (2016) The fallacy of the Passing-Bablok-regression. Jokull Journal 66:95-106. | Passing H, Bablok W (1983) A new biometrical procedure for testing the equality of measurements from two different analytical methods. Application of linear regression procedures for method comparison studies in Clinical Chemistry, Part I. J. Clin. Chem. Clin. Biochem. 21:709-720. | Passing H, Bablok W (1984) Comparison of several regression procedures for method comparison studies and determination of sample sizes. Application of linear regression procedures for method comparison studies in Clinical Chemistry, Part II. J. Clin. Chem. Clin. Biochem. 22:431-445. | Serdar CC, Cihan M, Yucel D, Serdar MA (2021) Sample size, power and effect size revisited: simplified and practical approaches in pre-clinical, clinical and laboratory studies. Biochemia Medica (Zagreb) 31:010502.

### Ecuacion de regresion Passing-Bablok

```
y = A + B x
```

**Simbolos / literal de la pagina.** A = Intercept (medida de las diferencias sistematicas entre los dos metodos); B = Slope (medida de las diferencias proporcionales). Literal: "The regression equation: the regression equation with the calculated values for A and B according to Passing & Bablok (1983)". En el informe de ejemplo: "y = 22.904132 + 1.008326 x". La pagina destaca: "The result does not depend on the assignment of the methods (or instruments) to X and Y".

**Supuestos / condiciones.** "Passing-Bablok regression is a linear regression procedure with no special assumptions regarding the distribution of the samples and the measurement errors (Passing & Bablok, 1983)". Notas de la pagina: "The Passing-Bablok procedure should only be used on variables that have a linear relationship and are highly correlated" y se aconseja complementar con un Bland-Altman plot.

**Intervalo de confianza.** Se calculan A y B con su intervalo de confianza al 95%; la pagina no imprime el metodo de calculo del IC (lo atribuye a Passing & Bablok, 1983). Opcionalmente, via el boton Advanced, se pueden calcular parametros bootstrap de los coeficientes de regresion (ver Bootstrapping options) o el sesgo esperado en valores umbral seleccionados segun la guia CLSI EP09c (3rd ed, 2018).

### Prueba de diferencias sistematicas (intercepto A)

```
H0: A = 0  -> aceptada si el 95% CI de A contiene el valor 0
```

**Simbolos / literal de la pagina.** Literal: "The 95% confidence interval for the intercept A can be used to test the hypothesis that A=0. This hypothesis is accepted if the confidence interval for A contains the value 0. If the hypothesis is rejected, then it is concluded that A is significantly different from 0 and both methods differ at least by a constant amount."

### Prueba de diferencias proporcionales (pendiente B)

```
H0: B = 1  -> aceptada si el 95% CI de B contiene el valor 1
```

**Simbolos / literal de la pagina.** Literal: "The 95% confidence interval for the slope B can be used to test the hypothesis that B=1. This hypothesis is accepted if the confidence interval for B contains the value 1. If the hypothesis is rejected, then it is concluded that B is significantly different from 1 and there is at least a proportional difference between the two methods."

### Intervalo de diferencias aleatorias (Residual Standard Deviation)

```
-1.96 RSD  to  +1.96 RSD
```

**Simbolos / literal de la pagina.** RSD = Residual Standard Deviation, "a measure of the random differences between the two methods". Literal: "95% of random differences are expected to lie in the interval -1.96 RSD to +1.96 RSD. If this interval is large, the two methods may not be in agreement." El mismo intervalo se enuncia sobre los residuos: "95% of the residuals should lie in the interval +/- 1.96 times the residual standard deviation". En el informe de ejemplo: RSD = 35.0689 y "+/- 1.96 RSD Interval = -68.7351 to 68.7351".

**Supuestos / condiciones.** Los residuos representan la variacion restante tras corregir por diferencias sistematicas y proporcionales; al suponerse relacion lineal deberian mostrar un patron aleatorio y aproximarse a una distribucion normal. Opcion "Calculate perpendicular residuals": residuos perpendiculares a la recta de regresion (ver Passing & Bablok, 1983), a diferencia del metodo tradicional de minimos cuadrados que mide los residuos paralelos al eje y.

### Criterio de outlier

```
outlier = residual outside the 4 SD limit
```

**Simbolos / literal de la pagina.** Literal: "outliers - defined here as residuals outside the 4 SD limit - are plotted in a different color in the residuals plot". Linnet & Boyd (2012) recomiendan no descartarlos automaticamente sino investigar su causa; Bablok & Passing (1985) recomiendan re-analizar por ambos metodos las muestras con valores desviados y excluirlas solo si se identifico un error analitico o el analizador declaro el resultado como dudoso.

**Supuestos / condiciones.** "Since it is in essence a non-parametric procedure, Passing-Bablok regression is not influenced by the presence of one or relative few outliers."

### Cusum test for linearity (validez del modelo lineal)

```
P < 0.05  ->  no hay relacion lineal, el metodo Passing-Bablok no es aplicable
```

**Simbolos / literal de la pagina.** Literal: "the Cusum test for linearity is used to evaluate how well a linear model fits the data. The Cusum test for linearity only tests the applicability of the Passing-Bablok method; it has no further interpretation with regards to comparability of the two laboratory methods. A small P value (P<0.05) indicates that there is no linear relationship between the two measurements and therefore the Passing-Bablok method is not applicable." En el informe de ejemplo: "No significant deviation from linearity (P=0.74)". No se imprime la formula del estadistico Cusum.

### Tamano de muestra recomendado

```
n >= 30 (Bablok & Passing, 1985) ; tablas con n sugeridos entre 30 y 90 (Passing & Bablok, 1984; Bablok & Passing, 1985) ; n >= 50 (Ludbrook, 2010)
```

**Simbolos / literal de la pagina.** Literal: "Passing & Bablok W (1984) and Bablok & Passing (1985) give tables with suggested adequate sample sizes (ranging from 30 to 90) (see also Serdar et al, 2021, where the tables are reproduced). Bablok & Passing (1985) advise to have at least 30 samples. Ludbrook (2010) cites a sample size of at least 50."

**Supuestos / condiciones.** Advertencia de la pagina: con n pequeno los IC 95% de intercepto y pendiente son anchos y es mas probable que contengan 0 y 1 respectivamente (ver Mayer et al, 2016), de modo que "method comparison studies based on small sample sizes are biased to the conclusion that the laboratory methods are in agreement".

### Coeficiente de correlacion de Spearman (opcional)

```
Spearman's rank correlation coefficient (rho) con P-value y 95% Confidence Interval
```

**Simbolos / literal de la pagina.** Opcional en el informe. La pagina advierte: "Note that Passing & Bablok (1983) discourage reporting the correlation coefficient in method comparison studies. We have found that Passing & Bablok regression does not work when correlation is low; we report it not as a method-comparison statistic, but as a factor in the evaluation of the validity of the Passing-Bablok regression procedure itself." No se imprime la formula de rho.

**Intervalo de confianza.** Se reporta IC 95% de rho; la pagina no especifica el metodo.

---

## Method comparison: Comparison of multiple methods

`comparison-of-multiple-methods.php` - https://www.medcalc.org/en/manual/comparison-of-multiple-methods.php

Extension del Bland-Altman plot a mas de dos metodos: para cada metodo se grafican las diferencias contra el metodo de referencia (Krouwer, 2008), en multiples paneles con ejes alineados. Ofrece las mismas 3 metodologias (Parametric, Non-Parametric, Regression-Based) y remite a la pagina Bland-Altman plot (seccion regression) para el detalle del metodo regression-based. La formula propia de esta pagina es la del absolute percentage error (APE).

**Referencias que cita la pagina:** Bland JM, Altman DG (1986) Statistical method for assessing agreement between two methods of clinical measurement. The Lancet i:307-310. | Bland JM, Altman DG (1995) Comparing methods of measurement: why plotting difference against standard method is misleading. The Lancet 346:1085-1087. | Bland JM, Altman DG (1999) Measuring agreement in method comparison studies. Statistical Methods in Medical Research 8:135-160. | Hanneman SK (2008) Design, analysis, and interpretation of method-comparison studies. AACN Advanced Critical Care 19:223-234. | Krouwer JS (2008) Why Bland-Altman plots should use X, not (Y+X)/2 when X is a reference method. Statistics in Medicine 27:778-780.

### Absolute percentage error (APE)

```
APE = 100 x ABS[(y - ref)/ref]
```

**Simbolos / literal de la pagina.** Literal: "the absolute percentage error (APE) is calculated as 100 x ABS[(y-ref)/ref] where y is the observation and ref is the reference value". y = la observacion del metodo evaluado; ref = el valor del metodo de referencia.

**Supuestos / condiciones.** El primer metodo seleccionado es el metodo de referencia ("First method is the reference method ... informational, this option is fixed").

**Intervalo de confianza.** "MedCalc also reports the 95% confidence intervals for both statistics, if sample size is large enough" (para MdAPE y para el percentil 95 del APE). No se especifica el metodo del IC.

### Median absolute percentage error (MdAPE) y percentil 95 del APE

```
MdAPE = median of APE ; APE_p95 = 95th percentile of the absolute percentage error
```

**Simbolos / literal de la pagina.** Literal: "MedCalc calculates the median APE (MdAPE) and the 95th percentile of the absolute percentage error. The 95th percentile APE is interpreted as follows: the percentage difference between a measurement and the reference value is not expected, with 95% certainty, to exceed this value."

**Intervalo de confianza.** IC 95% reportados para ambos estadisticos si el tamano de muestra es suficiente.

### Calculo de las diferencias

```
difference = measurement - reference   (positive = overestimation, negative = underestimation)
```

**Simbolos / literal de la pagina.** Literal: "Differences are calculated as measurement-reference (*) so a positive difference is an overestimation and a negative difference is an underestimation." La nota (*) aclara: "You can reverse this by selecting the option Reference-Variable", es decir difference = reference - measurement.

### Calculo de las razones y de las diferencias porcentuales

```
ratio = measurement / reference   (ratio > 1 = overestimation, ratio < 1 = underestimation) ; difference as % = difference expressed as percentage of the values on the axis
```

**Simbolos / literal de la pagina.** Literal para razones: "Ratios are calculated as measurement/reference (*) so a ratio > 1 indicates an overestimation and a ratio < 1 indicates an underestimation." Para porcentajes: "the differences will be expressed as percentages of the values on the axis (i.e. proportionally to the magnitude of measurements)".

**Supuestos / condiciones.** En esta pagina la opcion Plot ratios se presenta como forma de "avoiding the need for logarithmic transformation". Ambas opciones (% y ratios) son utiles cuando la variabilidad de las diferencias crece con la magnitud de la medicion.

### Limites de concordancia (LoA) parametricos y no parametricos

```
LoA (parametric) = mean difference +/- 1.96 * (standard deviation of the differences) ; LoA (non-parametric) = [2.5th percentile , 97.5th percentile] of the differences
```

**Simbolos / literal de la pagina.** Literal: "In the parametric approach, the limits of agreement (LoA) are calculated as the mean difference +/- 1.96 times the standard deviation of the differences. In the non-parametric approach, the LoA are defined by the 2.5th and 97.5th percentiles of the differences. Both methods aim to define an interval within which 95% of the differences between measurements are expected to lie." El informe lista, por variable, n, Mean, SD y 95% CI de las diferencias, y los LoA inferior y superior con sus IC 95%.

**Supuestos / condiciones.** Parametric (conventional): "Assumes constant bias and homoscedasticity (Bland & Altman 1986)". Non-Parametric: "uses ranks or quantiles ... without assuming normality or constant variance (Bland & Altman 1999)". Regression-Based: "models bias and limits of agreement as functions of the measurement magnitude ... (Bland & Altman 1999)", con el detalle en la pagina Bland-Altman plot (seccion regression).

**Intervalo de confianza.** Se reportan IC 95% de la media de las diferencias y de ambos LoA (opciones "95% CI of mean difference" y "95% CI of limits of agreement"); la pagina no imprime las formulas.

### Regresion de las diferencias contra el valor de referencia

```
differences regressed on the reference value -> intercept y slope con 95% CI, y P-value para el slope
```

**Simbolos / literal de la pagina.** Literal: "Parameters of the regression of the differences against the reference value: intercept and slope with 95% CI, and P-value for slope." La recta de regresion de las diferencias "may help to detect a proportional difference".

**Intervalo de confianza.** Se reporta IC 95% de intercepto y pendiente y, opcionalmente, el IC 95% de la recta de regresion en el grafico.

### Criterio de diferencia sistematica significativa

```
si la line of equality NO esta dentro del 95% CI of mean difference -> hay una diferencia sistematica significativa
```

**Simbolos / literal de la pagina.** Literal: "the 95% Confidence Interval of the mean difference illustrates the magnitude of the systematic difference. If the line of equality is not in the interval, there is a significant systematic difference."

---

## Deming regression

`deming-regression.php` - https://www.medcalc.org/en/manual/deming-regression.php

Pagina de procedimiento e interpretacion. NO imprime formulas algebraicas: el intercepto y la pendiente se atribuyen a Linnet (1990, 1993) y los errores estandar e IC al metodo jackknife (Armitage et al., 2002). Si define en prosa la razon de varianzas, los supuestos del modelo, la entrada de imprecision (2 variables con mediciones repetidas o 1 variable mas un CV% establecido), el criterio de outlier y las pruebas de hipotesis via IC.

**Referencias que cita la pagina:** Armitage P, Berry G, Matthews JNS (2002) Statistical methods in medical research. 4th ed. Blackwell Science. | Linnet K (1990) Estimation of the linear relationship between the measurements of two methods with proportional errors. Statistics in Medicine 12:1463-1473. | Linnet K (1993) Evaluation of regression procedures for methods comparison studies. Clinical Chemistry 39:424-432. | Linnet K, Boyd JC (2012) Selection and analytical evaluation of methods - with statistical techniques. In Burtis CA, Ashwood ER, Bruns DE (eds). Tietz Textbook of Clinical Chemistry and Molecular Diagnostics (5th ed). Elsevier Saunders, St Louis, MO, pp. 201-228. | NCSS (2026) NCSS Documentation, Chapter 303: Deming regression.

### Ecuacion de regresion de Deming

```
y = Intercept + Slope * x
```

**Simbolos / literal de la pagina.** Literal en el informe de ejemplo: "y = 0.005201 + 1.2212 x". "The Intercept and Slope are calculated according to Linnet (1990, 1993)." El informe tambien lista Mean y Coefficient of variation (%) de cada metodo, Sample size, Variance ratio y el Pearson correlation coefficient con su IC 95%.

**Supuestos / condiciones.** "Whereas the ordinary linear regression method assumes that only the Y measurements are associated with random measurement errors, the Deming method takes measurement errors for both methods into account." Ademas: "Deming regression assumes a constant ratio of measurement error variances between the two variables for all observations. Weighted Deming regression extends this by allowing observation-specific weights (or error variances), so points with different measurement precisions contribute differently to the fit."

**Intervalo de confianza.** Literal: "The standard errors and confidence intervals are estimated using the jackknife method (Armitage et al., 2002)." No se imprime la formula del jackknife.

### Variance ratio

```
Variance ratio = ratio of the measurement errors of X and Y
```

**Simbolos / literal de la pagina.** Definicion literal de la pagina: "Variance ratio: this is the ratio of the measurement errors of X and Y." En el informe de ejemplo Variance ratio = 0.3779, con CV(X) = 4.12% y CV(Y) = 6.70%. No se imprime la expresion algebraica del cociente.

**Supuestos / condiciones.** Es el parametro que materializa el supuesto de razon constante de varianzas de error de medicion.

### Entrada de la imprecision de cada metodo

```
por cada tecnica: 2 variables con mediciones repetidas  O  1 variable + Coefficient of Variation (CV, expressed as a percentage) ya establecido
```

**Simbolos / literal de la pagina.** Literal: "For each of both techniques you can either enter 2 variables (which contain repeated measurements) or you can enter only one variable, in which case you will have to enter an already established Coefficient of Variation (CV, expressed as a percentage)."

**Supuestos / condiciones.** Opcion "Weighted Deming regression": calcula la regresion de Deming ponderada segun Linnet 1990 & 1993.

### Prueba de diferencias sistematicas (intercepto A)

```
H0: A = 0  -> aceptada si el 95% CI del Intercept contiene el valor 0
```

**Simbolos / literal de la pagina.** Literal: "The 95% confidence interval for the Intercept can be used to test the hypothesis that A=0. This hypothesis is accepted if the confidence interval for A contains the value 0. If the hypothesis is rejected, then it is concluded that A is significantly different from 0 and both methods differ at least by a constant amount."

**Intervalo de confianza.** IC 95% por jackknife (Armitage et al., 2002).

### Prueba de diferencias proporcionales (pendiente B)

```
H0: B = 1  -> aceptada si el 95% CI del Slope contiene el valor 1
```

**Simbolos / literal de la pagina.** Literal: "The 95% confidence interval for the Slope can be used to test the hypothesis that B=1. This hypothesis is accepted if the confidence interval for B contains the value 1. If the hypothesis is rejected, then it is concluded that B is significantly different from 1 and there is at least a proportional difference between the two methods."

**Intervalo de confianza.** IC 95% por jackknife (Armitage et al., 2002).

### Residuos y criterio de outlier

```
outlier = residual outside the 4 SD limit
```

**Simbolos / literal de la pagina.** Literal: "MedCalc calculates optimized residuals following NCSS 2026" y "Outliers, defined here as residuals outside the 4 SD limit, are plotted in a different color. Linnet & Boyd (2012) recommend that these measurements should not just be rejected automatically, but the reason for their presence should be scrutinized." No se imprime la definicion algebraica de los "optimized residuals".

**Supuestos / condiciones.** El grafico de residuos permite evaluar visualmente el ajuste del modelo lineal; un patron en los residuos indica que las dos variables no tienen relacion lineal.

---

## Youden plot

`youdenplot.php` - https://www.medcalc.org/en/manual/youdenplot.php

Pagina del menu Graphs (no del menu Statistics). Metodo grafico para datos interlaboratorio donde todos los laboratorios analizaron 2 muestras; visualiza variabilidad intra e interlaboratorio. Describe tres variantes (Youden original, adaptado a muestras no comparables, y la variacion con rectangulos). Las unicas definiciones computacionales literales son la del "far out value", la Manhattan median, el escalado de los ejes y las areas (circulos de cobertura y rectangulos de SD). No hay estimadores ni intervalos de confianza.

**Referencias que cita la pagina:** Youden WJ (1959) Graphical diagnosis of interlaboratory test results. Industrial Quality Control, 15, 24-28.

### Definicion de far out value (valor extremo excluido de las medianas)

```
far out value = value < (lower quartile - 3 * interquartile range)   OR   value > (upper quartile + 3 * interquartile range)
```

**Simbolos / literal de la pagina.** Literal: "Far out values are not used in determining the position of the median lines. A far out value is defined as a value that is smaller than the lower quartile minus 3 times the interquartile range, or larger than the upper quartile plus 3 times the interquartile range."

**Supuestos / condiciones.** Los far out values se excluyen para posicionar las lineas de mediana. Opcion "Outlier detection: MedCalc will detect outliers automatically and exclude them for calculations".

### Manhattan median

```
Manhattan median = interseccion de las dos lineas de mediana (una horizontal paralela al eje x y una vertical paralela al eje y)
```

**Simbolos / literal de la pagina.** Literal: "A horizontal median line is drawn parallel to the x-axis so that there are as many points above the line as there are below it. A second median line is drawn parallel to the y-axis so that there are as many points on the left as there are on the right of this line. ... The intersection of the two median lines is called the Manhattan median." Cada punto del grafico corresponde a un laboratorio, definido por la respuesta de la muestra 1 (eje horizontal) y la de la muestra 2 (eje vertical).

### Escalado de los ejes

```
Youden original: one unit on the x-axis = one unit on the y-axis  ;  version adaptada a muestras no comparables: one standard deviation on the X-axis = one standard deviation on the y-axis
```

**Simbolos / literal de la pagina.** Literal para el original: "The axes in this plot are drawn on the same scale: one unit on the x-axis has the same length as one unit on the y-axis." Literal para la adaptacion: "the axes of the plot are not drawn on the same scale, but in this case, one standard deviation on the X-axis has the same length as one standard deviation on the y-axis".

**Supuestos / condiciones.** Para el Youden plot original "the two samples must be similar and reasonably close in the magnitude of the property evaluated" (opcion "Samples are similar" del dialogo). La version adaptada se usa cuando se ensayan dos productos diferentes.

### Areas: circulos de probabilidad de cobertura y rectangulos de SD

```
circulo = area que incluiria el 90%, 95% o 99% de los laboratorios si se pudieran eliminar los errores constantes individuales ; rectangulos = 1 SD, 2 SD o 3 SD sobre los ejes x e y
```

**Simbolos / literal de la pagina.** Literal: "A circle is drawn that should include 95 % of the laboratories if individual constant errors could be eliminated" y, en las opciones, "90%, 95% or 99% Coverage probability: circles can be drawn that include 90%, 95% or 99% of the laboratories if individual constant errors could be eliminated"; "1 SD, 2 SD or 3 SD: draws rectangles representing 1, 2 or 3 SD on both the x-axis and y-axis". No se imprime la formula del radio del circulo.

**Supuestos / condiciones.** La variacion con rectangulos reemplaza el circulo por uno o mas rectangulos de 1, 2 o 3 SD.

### Lineas de referencia e interpretacion del error

```
Youden original: recta de referencia a 45 grados a traves de la Manhattan median ; version adaptada: recta que representa una razon constante de las dos muestras. Interpretacion: puntos cerca de la recta de 45 grados pero lejos de la Manhattan median -> large systematic error ; puntos lejos de la recta de 45 grados -> large random error ; puntos fuera del circulo -> large total error
```

**Simbolos / literal de la pagina.** Reglas de interpretacion literales de la pagina. Para la version adaptada: "Analogous to the 45-degree reference line in the original Youden plot, a reference line is drawn which in this case represents a constant ratio of the two samples. The interpretation is the same as for the original Youden plot."

**Supuestos / condiciones.** La pagina advierte que "In medical literature you may encounter different graphs referred to as 'Youden plot'".

---

## Sample size calculation: Bland-Altman plot

`sample-size-bland-altman.php` - https://www.medcalc.org/en/manual/sample-size-bland-altman.php

Pagina del menu Sample size. Explica la logica del calculo (potencia para que Delta caiga fuera del IC 95% de los LoA), los datos de entrada, un ejemplo numerico completo y la atribucion del algoritmo. NO imprime la formula del tamano de muestra: la delega integramente en Lu et al. (2016). Advierte que el Bland-Altman plot implementado por MedCalc tiene un nivel alfa fijo de 0.05.

**Referencias que cita la pagina:** Bland JM, Altman DG (1986) Statistical method for assessing agreement between two methods of clinical measurement. The Lancet i:307-310. | Lu MJ, Zhong WH, Liu YX, Miao HZ, Li YC, Ji MH (2016) Sample size for assessing agreement between two methods of measurement by Bland-Altman method. The International Journal of Biostatistics 12: issue 2 (8 pp).

### Limites de concordancia (LoA) usados en el calculo

```
LoA = mean of differences between two measurements +/- 1.96 * (standard deviation of the differences)
```

**Simbolos / literal de la pagina.** Literal: "In this method, limits of agreement (LoA) are calculated as the mean of differences between two measurements +/- 1.96 x their standard deviation (Bland & Altman, 1986)".

**Supuestos / condiciones.** Nota de la pagina: "the Bland-Altman plot implemented by MedCalc (and as described in Bland & Altman, 1986) has a fixed alpha level of 0.05".

### Criterio de concordancia (hipotesis del calculo)

```
Delta > higher limit of agreement  AND  -Delta < lower limit of agreement ; interpretacion correcta: Delta > upper 95% CI limit of the higher LoA  AND  -Delta < lower 95% CI limit of the lower LoA
```

**Simbolos / literal de la pagina.** Literal: "Two methods are considered to be in agreement when a pre-defined maximum allowed difference (Delta) is larger than the higher limit of agreement, and -Delta is lower than the lower limit of agreement. Proper interpretation takes into account the 95% confidence interval of the LoA, and to be 95% certain that the methods do not disagree, Delta must be higher than the upper 95 CI limit of the higher LoA and -Delta must be less than the lower %95 CI limit of the lower LoA" (el "%95" es una errata de la pagina original, se reproduce tal cual).

**Supuestos / condiciones.** Logica del calculo, literal: "With smaller sample sizes, the CI becomes larger and the probability that Delta lies within the 95 CI increases. With larger sample sizes, the CI becomes smaller and the probability that Delta lies within the 95 CI decreases. To show that two methods are in agreement, an adequate sample size must be established to have a high probability (power) that Delta will fall outside the 95 CI of the Limits of Agreement."

**Intervalo de confianza.** Se basa en el IC 95% de los limites de concordancia; la pagina no imprime su formula.

### Restriccion sobre la maxima diferencia permitida (dato de entrada)

```
Maximum allowed difference between methods > expected mean + 1.96 * expected standard deviation of differences
```

**Simbolos / literal de la pagina.** Literal: "Maximum allowed difference between methods: this is the pre-defined clinical agreement limit. Differences below this limit are clinically irrelevant or neglectable. This difference must be larger than expected mean + 1.96 x expected standard deviation of differences."

**Supuestos / condiciones.** Datos de entrada requeridos: Type I error alpha (nivel alfa, dos colas), Type II error beta, Expected mean of differences, Expected Standard Deviation of differences y Maximum allowed difference between methods.

### Algoritmo de calculo del tamano de muestra

```
MedCalc uses the method by Lu et al. (2016) to calculate the sample sizes
```

**Simbolos / literal de la pagina.** La pagina no imprime la formula. Ejemplo numerico literal (tomado de Lu et al., 2016): Expected mean of differences = 0.001167, Expected SD of differences = 0.001129, Maximum allowed difference = 0.004, alpha = 0.05, beta = 0.20 (potencia 80%) -> "the minimum required total sample size is 83". El programa muestra ademas una tabla con el n requerido para distintos niveles de error de tipo I y II.

**Supuestos / condiciones.** Atribucion explicita a Lu et al. (2016).

---

## Bland-Altman plot with multiple measurements per subject

`blandaltmanmultiple.php` - https://www.medcalc.org/en/manual/blandaltmanmultiple.php

Pagina mayormente de UI y de organizacion de datos (una columna de identificacion de sujeto y una columna por metodo; herramienta Stack columns para reorganizar). Documenta los dos modelos (True value is constant in each subject / True value varies), las opciones del dialogo y el informe. NO imprime formulas algebraicas: delega todo el calculo en Zou (2013) y enuncia los LoA solo en prosa.

**Referencias que cita la pagina:** Bland JM, Altman DG (1986) Statistical method for assessing agreement between two methods of clinical measurement. The Lancet i:307-310. | Bland JM, Altman DG (1995) Comparing methods of measurement: why plotting difference against standard method is misleading. The Lancet 346:1085-1087. | Bland JM, Altman DG (1999) Measuring agreement in method comparison studies. Statistical Methods in Medical Research 8:135-160. | Bland JM, Altman DG (2007) Agreement between methods of measurement with multiple observations per individual. Journal of Biopharmaceutical Statistics 17:571-582. | Krouwer JS (2008) Why Bland-Altman plots should use X, not (Y+X)/2 when X is a reference method. Statistics in Medicine 27:778-780. | Zou GY (2013) Confidence interval estimation for the Bland-Altman limits of agreement with multiple observations per individual. Statistical Methods in Medical Research 22:630-642.

### Limites de concordancia (enunciado en prosa)

```
LoA = mean difference +/- 1.96 * (standard deviation of the differences)
```

**Simbolos / literal de la pagina.** Literal: "Horizontal lines are drawn at the mean difference, and at the limits of agreement, which are defined as the mean difference plus and minus 1.96 times the standard deviation of the differences. If the differences within mean +/- 1.96 SD are not clinically important, the two methods may be used interchangeably." El informe de ejemplo reporta Mean, Lower limit y Upper limit con sus IC 95%.

**Supuestos / condiciones.** Procedimiento para cuando hay mas de una medicion por sujeto con cada metodo. Dos modelos: "True value is constant in each subject" (un solo marcador por sujeto, tamano proporcional al numero de observaciones, ver Bland & Altman, 2007) y el modelo alternativo "True value varies" (un marcador por par de observaciones).

**Intervalo de confianza.** Literal: "The calculations are performed as described by Zou (2013). For the estimation of the confidence intervals of the limits of agreement, the MOVER method is used (Zou, 2013)." No se imprime la formula del MOVER.

### Maxima diferencia permitida entre metodos (D)

```
differences in the range -D to D (for ratios 1/D to D) are clinically irrelevant or neglectable
```

**Simbolos / literal de la pagina.** D = limite de concordancia clinica predefinido ("the pre-defined clinical agreement limit D"). Segun la opcion elegida (Plot differences o Plot ratios) debe ingresarse una diferencia o una razon.

**Supuestos / condiciones.** Para "Plot ratios" MedCalc calcula sobre datos log-transformados en segundo plano y advierte si alguno de los dos metodos contiene valores cero.

### Definiciones computacionales del eje X

```
X-axis = mean of the two methods (recommended) | one of the two methods (reference / gold standard) | geometric mean of both methods
```

**Simbolos / literal de la pagina.** El grafico original (Bland & Altman, 1986) grafica las diferencias contra la media de los dos metodos, opcion recomendada segun Bland & Altman, 1995; graficar contra uno de los metodos cuando es referencia o "gold standard" se atribuye a Krouwer, 2008.

---

## Concordance correlation coefficient

`concordance.php` - https://www.medcalc.org/en/manual/concordance.php

Pagina corta del coeficiente de correlacion de concordancia de Lin. Menu: Statistics > Agreement & responsiveness > Concordance correlation coefficient. Imprime una sola formula (en display MathJax mas su SVG) y la escala descriptiva de McBride (2005). No enuncia el metodo de calculo del intervalo de confianza.

**Referencias que cita la pagina:** Lin L.I-K (1989) A concordance correlation coefficient to evaluate reproducibility. Biometrics 45:255-268. | Lin L.I-K (2000) A note on the concordance correlation coefficient. Biometrics 56:324-325. | McBride GB (2005) A proposal for strength-of-agreement criteria for Lin's Concordance Correlation Coefficient. NIWA Client Report: HAM2005-062.

### Concordance correlation coefficient (Lin)

```
\rho_c = \rho \space C_b
```

**Simbolos / literal de la pagina.** Formula literal en display MathJax. rho_c = coeficiente de correlacion de concordancia; rho = "the Pearson correlation coefficient, which measures how far each observation deviates from the best-fit line, and is a measure of precision"; C_b = "a bias correction factor that measures how far the best-fit line deviates from the 45deg line through the origin, and is a measure of accuracy". La pagina no imprime las formulas de rho ni de C_b.

**Supuestos / condiciones.** "The concordance correlation coefficient (Lin, 1989) evaluates the degree to which pairs of observations fall on the 45deg line through the origin." Se seleccionan las variables de las dos tecnicas a comparar.

**Intervalo de confianza.** No indicado en la pagina.

### Escala descriptiva de fuerza de concordancia (McBride, 2005)

```
rho_c < 0.90 -> Poor ; 0.90 - 0.95 -> Moderate ; 0.95 - 0.99 -> Substantial ; > 0.99 -> Almost perfect
```

**Simbolos / literal de la pagina.** Tabla literal de la pagina: "McBride (2005) suggests the following descriptive scale for values of the concordance correlation coefficient (for continuous variables)".

**Supuestos / condiciones.** Valida para variables continuas.

---

## Mountain plot

`mountain-plot.php` - https://www.medcalc.org/en/manual/mountain-plot.php

Pagina descriptiva del mountain plot ("folded empirical cumulative distribution plot"). Solo trae la definicion computacional de la construccion del grafico (calculo de percentiles y plegado). No hay estimadores ni intervalos de confianza. Admite 2 o 3 tecnicas; con 3 ensayos, el segundo y el tercero se comparan contra el primero (ensayo de referencia). El panel Info entrega sample size, mediana, minimo, maximo y los percentiles mas importantes.

**Referencias que cita la pagina:** CLSI (2003) Estimation of Total Analytical Error for Clinical Laboratory Methods; Approved Guideline. CLSI Document EP21-A. Wayne, PA: Clinical and Laboratory Standards Institute. | Krouwer JS, Monti KL (1995) A simple, graphical method to evaluate laboratory assays. Eur J Clin Chem Clin Biochem 33:525-527.

### Construccion del mountain plot (folded empirical cumulative distribution)

```
para cada diferencia ordenada (ranked difference) entre el metodo nuevo y el metodo de referencia se calcula un percentil; luego, para todos los percentiles > 50:  percentile = 100 - percentile ; estos percentiles se grafican contra las diferencias entre los dos metodos
```

**Simbolos / literal de la pagina.** Literal: "A mountain plot (or 'folded empirical cumulative distribution plot') is created by computing a percentile for each ranked difference between a new method and a reference method. To get a folded plot, the following transformation is performed for all percentiles above 50: percentile = 100 - percentile. These percentiles are then plotted against the differences between the two methods (Krouwer & Monti, 1995; CLSI, 2003)."

**Supuestos / condiciones.** Complemento del Bland & Altman plot. Ventajas declaradas: "It is easier to find the central 95% of the data, even when the data are not Normally distributed" y "Different distributions can be compared more easily". Interpretacion: "If two assays are unbiased with respect to each other, the mountain will be centered over zero. Long tails in the plot reflect large differences between the methods."

**Intervalo de confianza.** No aplica / no indicado en la pagina.

---

## Enlaces

- [[MedCalc - Mapa]]
- [[MedCalc - Procedimientos estadisticos]]
- [[MedCalc - Funciones (referencia completa)]]
