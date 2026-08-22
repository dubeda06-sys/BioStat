---
tags: [medcalc, formulas, estadistica, referencia]
tipo: referencia
version: 23.6.5.0
grupo: control-de-calidad
formulas: 53
paginas: 10
fecha_extraccion: 2026-08-13
---

# MedCalc - Formulas - Control de calidad y variabilidad analitica

Volver a [[MedCalc - Mapa]] | indice de procedimientos: [[MedCalc - Procedimientos estadisticos]]

**53 formulas** extraidas de **10 paginas** del manual oficial de MedCalc.

> [!info] Procedencia
> Cada formula es transcripcion literal de la pagina del manual que se cita debajo de ella.
> No hay formulas escritas de memoria: si el manual no la publica, aca dice que no la publica.
> Notacion ASCII (`sqrt`, `^`, `*`, `+/-`) conservando los nombres de simbolo de la pagina.
> Manual leido: el **ingles** (`/en/manual/`); las formulas y las frases entre comillas quedan en ingles.
> Estado de verificacion de esta cosecha (que paginas se re-chequearon y cual no): ver [[MedCalc - Mapa]].

---

## Summary statistics

`summary-statistics.php` - https://www.medcalc.org/en/manual/summary-statistics.php

Pagina nuclear de definiciones: 9 ecuaciones mostradas (verificado con 9 bloques MathJax) mas varias definiciones adicionales en prosa. Cubre media aritmetica, mediana, varianza, SD, RSD/CV, SEM e IC de la media, media geometrica, media armonica, percentiles con su formula de rango y condicion de validez, asimetria y curtosis, test de normalidad y recomendaciones de presentacion de resultados. IMPORTANTE: el calculo de la Trimmed mean (media recortada) NO esta en esta pagina; se remite a la pagina aparte note-trimmedmean.php. Tampoco se dan las formulas de los coeficientes de asimetria y curtosis, solo su interpretacion y su valor 0 bajo normalidad. Opciones: transformacion logaritmica (entonces la media reportada ya es la media geometrica, y varianza/SD/SEM no se retrotransforman ni se reportan), test de normalidad, seleccion de percentiles y hasta 8 subgrupos.

**Referencias que cita la pagina:** Altman DG (1980) Statistics and ethics in medical research. VI - Presentation of results. British Medical Journal 281:1542-1544. | Altman DG (1991) Practical statistics for medical research. London: Chapman and Hall. | Altman DG, Gore SM, Gardner MJ, Pocock SJ (1983) Statistical guidelines for contributors to medical journals. British Medical Journal 286:1489-1493. | Campbell MJ, Gardner MJ (1988) Calculating confidence intervals for some non-parametric analyses. British Medical Journal 296:1454-1456. | Lentner C (ed) (1982) Geigy Scientific Tables, 8th edition, Volume 2. Basle: Ciba-Geigy Limited. | Schoonjans F, De Bacquer D, Schmid P (2011) Estimation of population percentiles. Epidemiology 22: 750-751. | Sheskin DJ (2011) Handbook of parametric and non-parametric statistical procedures. 5th ed. Boca Raton: Chapman & Hall /CRC. | Westfall PH (2014) Kurtosis as Peakedness, 1905 - 2014. R.I.P. The American Statistician 68:191-195.

### Sample size (n)

```
n = numero de entradas numericas (numeric entries) de la variable que cumplen el filtro
```

**Simbolos / literal de la pagina.** n = number of cases

**Supuestos / condiciones.** Enunciado en prosa. La pagina reporta ademas el lowest value y el highest value de todas las observaciones (range).

### Arithmetic mean

```
xbar = (x_1 + x_2 + ... + x_n) / n = (1/n) * sum_{i=1}^{n} x_i = (1/n) * sum(x)
```

**Simbolos / literal de la pagina.** xbar = media aritmetica; x_i = observaciones; n = numero de observaciones

**Supuestos / condiciones.** Ecuacion mostrada (las tres formas equivalentes aparecen alineadas en la pagina). LaTeX original: \bar{x} = \frac{x_1+x_2+\cdots +x_n}{n} = {1 \over n} \sum_{i=1}^{n}{x_i} = {1 \over n} \sum{x}

### Variance

```
s^2 = sum( (x - xbar)^2 ) / (n - 1)
```

**Simbolos / literal de la pagina.** s^2 = varianza; xbar = media aritmetica; n = numero de observaciones

**Supuestos / condiciones.** Ecuacion mostrada. Definicion verbal de la pagina: la varianza es la media del cuadrado de las diferencias de todos los valores con la media aritmetica (denominador n-1). LaTeX original: s^2 = \frac{\sum{(x-\bar{x})^2}}{n-1}

### Standard deviation

```
s = sqrt( sum( (x - xbar)^2 ) / (n - 1) )
```

**Simbolos / literal de la pagina.** s o SD = desviacion estandar; xbar = media aritmetica; n = numero de observaciones

**Supuestos / condiciones.** Ecuacion mostrada. Es la raiz cuadrada de la varianza y mide la dispersion de los datos. LaTeX original: s = \sqrt{\frac{\sum{(x-\bar{x})^2}}{n-1}}

### Rango descriptivo del 95% de las observaciones (si la distribucion es Normal)

```
mean - 1.96 SD   to   mean + 1.96 SD
```

**Simbolos / literal de la pagina.** mean = media; SD = desviacion estandar; 1.96 = valor de la distribucion Normal para el 95%

**Supuestos / condiciones.** Enunciado en prosa. Solo valido cuando la distribucion de las observaciones es Normal. La pagina advierte explicitamente que NO debe confundirse con el intervalo de confianza del 95% de la media, que es mas pequeno: este intervalo representa un rango descriptivo de confianza del 95% para las observaciones individuales, mientras que el IC 95% de la media representa la incertidumbre estadistica de la media aritmetica. Para otros valores remite a la tabla 'Values of the Normal distribution'.

### Relative standard deviation (RSD) / coefficient of variation

```
RSD = s / mean          CV(%) = 100 * RSD
```

**Simbolos / literal de la pagina.** RSD = relative standard deviation; s = desviacion estandar; mean = media

**Supuestos / condiciones.** Enunciado en prosa: es la desviacion estandar dividida por la media; si es apropiado, ese numero puede expresarse como porcentaje multiplicandolo por 100 para obtener el coefficient of variation. En el informe de ejemplo de la pagina se muestra RSD = 0.1244 (12.44%).

### Standard error of the mean (SEM)

```
SEM = s / sqrt(n)
```

**Simbolos / literal de la pagina.** SEM = error estandar de la media; s = desviacion estandar; n = tamano de muestra

**Supuestos / condiciones.** Ecuacion mostrada. Se obtiene dividiendo la desviacion estandar por la raiz cuadrada del tamano de muestra. LaTeX original: SEM = \frac{s}{\sqrt{n}}

### 95% confidence interval (CI) for the mean

```
IC 95% = xbar +/- t * SEM
```

**Simbolos / literal de la pagina.** xbar = media aritmetica; SEM = error estandar de la media; t = valor de la distribucion t con n-1 grados de libertad y una confianza del 95%

**Supuestos / condiciones.** Enunciado en prosa. Valido cuando la distribucion de las observaciones es Normal o aproximadamente Normal. La pagina indica que para tamanos de muestra grandes t es proximo a 1.96, y remite a la tabla 'Values of the t-distribution'.

**Intervalo de confianza.** Metodo parametrico basado en la distribucion t de Student con n-1 grados de libertad, usando el SEM.

### Median

```
con n observaciones ordenadas de menor a mayor, la mediana es el valor con numero de orden (n+1)/2
```

**Simbolos / literal de la pagina.** n = numero de observaciones

**Supuestos / condiciones.** Enunciado en prosa. La mediana es igual al percentil 50. Si la distribucion de los datos es Normal, la mediana es igual a la media aritmetica. No es sensible a valores extremos ni atipicos, por lo que puede ser mejor medida de tendencia central que la media aritmetica.

**Intervalo de confianza.** El IC 95% de la mediana se calcula segun Campbell & Gardner, 1988 (la pagina no reproduce la formula). Solo puede calcularse cuando el tamano de muestra no es demasiado pequeno.

### Geometric mean

```
GeometricMean = ( prod_{i=1}^{n} x_i )^(1/n) = nthroot(n, x_1 * x_2 * ... * x_n) = exp[ (1/n) * sum_{i=1}^{n} ln(x_i) ]
```

**Simbolos / literal de la pagina.** x_i = observaciones; n = numero de observaciones; ln = logaritmo natural

**Supuestos / condiciones.** Ecuacion mostrada (opcion 'Other averages' en More options). No esta disponible cuando se selecciona Logarithmic transformation, porque en ese caso la media reportada ya es la media geometrica. LaTeX original: \left ( \prod_{i=1}^n{x_i} \right ) ^\tfrac1n = \sqrt[n]{x_1 x_2 \cdots x_n} = \exp\left[\frac1n\sum_{i=1}^n\ln x_i\right]

### Harmonic mean

```
HarmonicMean = n / ( 1/x_1 + 1/x_2 + ... + 1/x_n ) = n / sum_{i=1}^{n} (1/x_i)
```

**Simbolos / literal de la pagina.** x_i = observaciones; n = numero de observaciones

**Supuestos / condiciones.** Ecuacion mostrada (opcion 'Other averages' en More options). No esta disponible cuando se selecciona Logarithmic transformation. LaTeX original: \frac{n}{\frac1{x_1} + \frac1{x_2} + \cdots + \frac1{x_n}} = \frac{n}{\sum\limits_{i=1}^n \frac1{x_i}}

### Percentile rank number R(p)

```
R(p) = 0.5 + (p * n) / 100
```

**Simbolos / literal de la pagina.** R(p) = numero de rango (rank number) del percentil p; p = percentil buscado; n = numero de observaciones ordenadas de menor a mayor

**Supuestos / condiciones.** Ecuacion mostrada. Atribuida a Lentner, 1982 y Schoonjans et al., 2011. Cuando R(p) es un numero entero, el percentil coincide con el valor de la muestra; si R(p) es fraccionario, el percentil esta entre los valores con rangos adyacentes a R(p) y MedCalc usa interpolacion para calcularlo. LaTeX original: R(p) = 0.5 + \frac{p \times n}{100}

### Condicion de validez de R(p)

```
1/n  <=  p/100  <=  (n-1)/n
```

**Simbolos / literal de la pagina.** p = percentil; n = numero de observaciones

**Supuestos / condiciones.** Ecuacion mostrada. La pagina declara que la formula de R(p) solo es valida bajo esta condicion. Consecuencia declarada: no tiene sentido citar los percentiles 5 y 95 cuando el tamano de muestra es menor que 20; en ese caso se aconseja citar los percentiles 10 y 90, al menos si el tamano de muestra no es menor que 10. LaTeX original: \frac{1}{n} \leq \frac{p}{100} \leq \frac{n-1}{n}

### Ejemplo numerico de la condicion de validez (percentiles 5 y 95 con n = 20)

```
1/20  <=  5/100    and    95/100  <=  (20-1)/20
```

**Simbolos / literal de la pagina.** n = 20; p = 5 y p = 95

**Supuestos / condiciones.** Ecuacion mostrada. Es el ejemplo con que la pagina justifica que los percentiles 5 y 95 solo pueden estimarse cuando n >= 20. LaTeX original: \frac{1}{20} \leq \frac{5}{100} \; \text{and} \; \frac{95}{100} \leq \frac{20-1}{20}

### Cuartiles, interquartile range y central ranges

```
percentil 25 = 1st quartile;  percentil 50 = 2nd quartile = Median;  percentil 75 = 3rd quartile;  interquartile range = percentil 75 - percentil 25;  95% central range = [percentil 2.5, percentil 97.5];  90% central range = [percentil 5, percentil 95];  80% central range = [percentil 10, percentil 90]
```

**Simbolos / literal de la pagina.** p % de las observaciones estan por debajo del percentil p (p.ej. 10% de las observaciones estan por debajo del percentil 10)

**Supuestos / condiciones.** Enunciado en prosa. El interquartile range se define como la diferencia numerica entre el percentil 25 y el percentil 75.

### Coefficient of Skewness (interpretacion, sin formula)

```
Skewness < 0 -> distribucion con asimetria negativa (skewed to the left);  Skewness = 0 -> distribucion Normal, simetrica;  Skewness > 0 -> distribucion con asimetria positiva (skewed to the right)
```

**Simbolos / literal de la pagina.** -

**Supuestos / condiciones.** La pagina NO da la formula del coeficiente de asimetria. Es una medida del grado de simetria de la distribucion de la variable. Si el valor de P asociado es bajo (P < 0.05) la simetria de la variable difiere significativamente de la de una distribucion Normal, que tiene un coeficiente de asimetria igual a 0 (Sheskin, 2011).

### Coefficient of Kurtosis (interpretacion, sin formula)

```
Kurtosis < 0 -> distribucion platicurtica (colas mas delgadas);  Kurtosis = 0 -> distribucion Normal, mesocurtica;  Kurtosis > 0 -> distribucion leptocurtica (colas mas gruesas)
```

**Simbolos / literal de la pagina.** -

**Supuestos / condiciones.** La pagina NO da la formula del coeficiente de curtosis. Es una medida del grado de 'tailedness' de la distribucion (Westfall, 2014). Si el valor de P asociado es bajo (P < 0.05) la tailedness difiere significativamente de la de una distribucion Normal, que tiene un coeficiente de curtosis igual a 0 (Sheskin, 2011).

### Regla de decision del test de normalidad y consecuencias

```
si P > 0.05 -> 'accept Normality';  si P < 0.05 -> 'reject Normality'
```

**Simbolos / literal de la pagina.** -

**Supuestos / condiciones.** Enunciado en prosa. Si se rechaza la normalidad, la muestra no puede describirse con exactitud mediante media aritmetica y desviacion estandar, y no deberia someterse a ningun test o procedimiento estadistico parametrico (por ejemplo un t-test); la pagina propone el Wilcoxon test para diferencias y la rank correlation para correlacion. Cuando el tamano de muestra es pequeno puede no ser posible realizar el test seleccionado. En el informe de ejemplo se usa el Shapiro-Wilk test (W = 0.9835, accept Normality, P = 0.2462).

### Retrotransformacion e IC tras transformacion (presentacion de resultados)

```
tras transformacion logaritmica -> antilog del intervalo de confianza;  tras transformacion de raiz cuadrada -> elevar al cuadrado el intervalo de confianza
```

**Simbolos / literal de la pagina.** -

**Supuestos / condiciones.** Enunciado en prosa, atribuido a Altman et al., 1983. La media retrotransformada se llama Geometric mean. Varianza, desviacion estandar y error estandar de la media NO pueden retrotransformarse de forma significativa y no se reportan. El intervalo resultante no sera simetrico, reflejando la forma de la distribucion. Ejemplo de la pagina: si tras la transformacion logaritmica la media es 1.408 y el IC 95% es 1.334 a 1.482, se hace el antilogaritmo y se reporta: media 25.6 mm (95% CI 21.6 a 30.3). Regla de precision declarada: la media y el IC 95% pueden darse con un decimal mas que los datos brutos, y la desviacion estandar y el error estandar con un decimal extra.

---

## Control chart

`control-chart.php` - https://www.medcalc.org/en/manual/control-chart.php

Pagina del cuadro de dialogo Graphs > Control chart. No contiene ninguna ecuacion mostrada (0 bloques MathJax); todos los limites y reglas estan enunciados en prosa. Documenta como se construye el grafico de control de calidad, las tres formas de fijar los limites (a partir de los datos, a partir de un 'Standard' con Mean y SD introducidos, o valor de referencia con limites de control y de alarma que pueden ser asimetricos), la opcion de grafico de control 'custom' (en blanco, para marcar a mano), y las 5 reglas multirregla de Westgard. Nota tecnica: https://www.medcalc.org/en/manual/control-chart.php redirige 301 a la URL /en/manual/ indicada aqui, que es tambien el link rel=canonical.

**Referencias que cita la pagina:** Westgard JO, Barry PL, Hunt MR, Groth T (1981) A multi-rule Shewhart chart for Quality Control in Clinical Chemistry. Clinical Chemistry, 27, 493-501.

### Lineas y limites del grafico de control

```
lineas en: Mean, Mean - 2s, Mean + 2s, Mean - 3s, Mean + 3s     (s = standard deviation)
```

**Simbolos / literal de la pagina.** s = standard deviation (desviacion estandar); Mean = media de los datos seleccionados

**Supuestos / condiciones.** Enunciado en prosa, no como ecuacion mostrada. Los datos se representan (plotted) consecutivamente junto con una linea en la media.

**Intervalo de confianza.** La pagina declara literalmente que -2s/+2s corresponde a los limites de confianza del 95% y -3s/+3s a los del 99.7%.

### Origen de los limites de control (opcion basada en los datos, con 'until n =')

```
Mean y SD calculados a partir de los datos seleccionados; con la opcion "until n =" -> Mean y SD calculados SOLO con las primeras n observaciones
```

**Simbolos / literal de la pagina.** n = numero de observaciones iniciales sobre las que se basan los limites (ejemplo de la pagina: 40 observaciones representadas, limites basados en las primeras 20 -> se introduce 20)

**Supuestos / condiciones.** Enunciado en prosa. Alternativamente se puede seleccionar 'Standard' e introducir directamente el Mean y la Standard Deviation (SD) del estandar utilizado, o introducir el valor de referencia con limites superiores e inferiores de control y de alarma (warning), que en ese caso pueden ser asimetricos.

### 1:2S rule

```
if |measurement - Mean| > 2SD  (o si excede los warning limits)  ->  se comprueban todas las reglas siguientes
```

**Simbolos / literal de la pagina.** SD = standard deviation; Mean = media

**Supuestos / condiciones.** Si esta regla NO se selecciona, las reglas siguientes se comprueban tambien cuando la medicion no excede los warning limits de Mean +/- 2SD. La pagina indica que esto influye particularmente en la 4:1S rule y en la 10:X rule. Actua como filtro/condicion previa, no como criterio de fuera de control por si misma.

### 1:3S rule

```
if measurement > Mean + 3SD  OR  measurement < Mean - 3SD  ->  run is out of control
```

**Simbolos / literal de la pagina.** SD = standard deviation; Mean = media

**Supuestos / condiciones.** La pagina indica que esta regla detecta principalmente error aleatorio (random error), pero puede indicar tambien un error sistematico grande.

### 2:2S rule

```
if 2 consecutive measurements exceed the same (Mean + 2S)  OR  the same (Mean - 2S)  ->  run is out of control
```

**Simbolos / literal de la pagina.** S = standard deviation; Mean = media

**Supuestos / condiciones.** El criterio exige el MISMO limite (el mismo lado) en las 2 mediciones consecutivas. La pagina indica que esta regla detecta error sistematico (systematic error).

### 4:1S rule

```
if 4 or more consecutive measurements exceed the same (Mean + 1S)  OR  the same (Mean - 1S)  ->  run is out of control
```

**Simbolos / literal de la pagina.** S = standard deviation; Mean = media

**Supuestos / condiciones.** El criterio exige el MISMO limite (el mismo lado). La pagina indica que esta regla detecta sesgo sistematico (systematic bias).

### 10:X rule

```
if 10 or more consecutive measurements are on the same side of the Mean  ->  run is out of control
```

**Simbolos / literal de la pagina.** Mean = media; el umbral 10 es configurable

**Supuestos / condiciones.** El software permite seleccionar un valor distinto de 10: menor que 10 da mayor sensibilidad, mayor que 10 da menor sensibilidad. La pagina indica que esta regla detecta sesgo sistematico (systematic bias).

---

## Serial measurements

`serialmeasurements.php` - https://www.medcalc.org/en/manual/serialmeasurements.php

Pagina sin ecuaciones mostradas (0 bloques MathJax); varias medidas resumen se definen numericamente en prosa. Resume mediciones seriadas por sujeto (p.ej. una prueba de tolerancia a la glucosa) en una o dos medidas resumen y las compara entre subgrupos. Formato de datos exigido: a diferencia del resto de MedCalc, los datos de todos los casos van en UNA SOLA columna; hacen falta ademas una variable de tiempo (numerica, en la misma unidad, con intervalos que pueden ser desiguales), una variable categorica que identifica los casos y una variable categorica opcional de grupo. Medidas resumen ofrecidas: Minimum y Time to reach minimum, Maximum y Time to reach maximum, First observation, Last observation, Difference Last-First, % Change Last-First, Maximum difference with first observation, % Maximum difference with first observation, Time-weighted average, Area Under the Curve (AUC), y % Time above / above or equal to / below / below or equal to un valor umbral.

**Referencias que cita la pagina:** Bland M (2000) An introduction to medical statistics, 3rd ed. Oxford: Oxford University Press. | Mathews JNS, Altman DG, Campbell MJ, Royston P (1990) Analysis of serial measurements in medical research. British Medical Journal 300:230-235.

### % Change Last-First observation

```
% Change = 100 x (Last - First) / First
```

**Simbolos / literal de la pagina.** Last = ultima observacion del caso; First = primera observacion del caso

**Supuestos / condiciones.** Enunciado en prosa con la expresion numerica explicita. Condicion literal: para calcular esta medida resumen la primera observacion nunca debe ser igual a cero.

### % Maximum difference with first observation

```
% Maximum difference = 100 x (Max difference / First)
```

**Simbolos / literal de la pagina.** Max difference = maxima diferencia con la primera observacion; First = primera observacion del caso

**Supuestos / condiciones.** Enunciado en prosa con la expresion numerica explicita. Condicion literal: para calcular esta medida resumen la primera observacion nunca debe ser igual a cero.

### Time-weighted average

```
Time-weighted average = case AUC (baseline 0) / (time of last observation - time of first observation)
```

**Simbolos / literal de la pagina.** case AUC (baseline 0) = area bajo la curva del caso con linea base 0; el denominador es el intervalo de tiempo total del caso

**Supuestos / condiciones.** Enunciado en prosa. Regla literal para el caso degenerado: si solo hay una observacion, ese valor se toma como el time-weighted average. La pagina la propone como alternativa al AUC cuando la primera y ultima observaciones no estan fijadas al mismo tiempo en todos los casos.

### Area Under the Curve (AUC) - eleccion de linea base

```
AUC calculada de 3 formas distintas segun el valor tomado como linea base: baseline = 0, baseline = first observation, o baseline = minimum
```

**Simbolos / literal de la pagina.** -

**Supuestos / condiciones.** Enunciado en prosa; la pagina NO da la formula de integracion. Cuando se toma la primera observacion como linea base, el area bajo la curva puede ser un numero negativo. Requisito literal: para el AUC, MedCalc exige que en todos los casos la primera y la ultima observaciones esten fijadas al mismo tiempo; si no es asi, la alternativa es usar el Time-weighted average.

### Left-align time (opcion)

```
para cada caso: nuevo tiempo = tiempo observado - primer valor de tiempo de ese caso   (asi el tiempo de inicio de cada caso queda en 0)
```

**Simbolos / literal de la pagina.** -

**Supuestos / condiciones.** Enunciado en prosa.

### Seleccion automatica del test estadistico

```
parametrico: t-test si hay 2 grupos, One-way analysis of variance (ANOVA) si hay mas de 2 grupos.  No parametrico: Mann-Whitney si hay 2 grupos, Kruskal-Wallis si hay mas de 2 grupos.
```

**Simbolos / literal de la pagina.** -

**Supuestos / condiciones.** Enunciado en prosa. Con la opcion 'Automatic': MedCalc analiza los estadisticos resumen en los distintos grupos y realiza un test de normalidad (el test de normalidad se hace sobre la muestra completa, despues de transformar los valores a z-scores POR GRUPO). Si los datos tienen distribucion Normal se usa un test parametrico; si no, se intenta una transformacion logaritmica; si tras la transformacion logaritmica los datos son Normales, el test se hace sobre los datos log-transformados; si no, se usa un test no parametrico sobre los datos no transformados. La opcion de elegir el test de normalidad solo esta disponible con 'Automatic'. Criterio de decision declarado: si el valor de P resultante es menor que 0.05, se concluye que hay una diferencia significativa de la medida resumen entre los distintos subgrupos.

---

## Coefficient of variation from duplicate measurements

`cvfromduplicates.php` - https://www.medcalc.org/en/manual/cvfromduplicates.php

Pagina con mayor densidad de formulas del grupo: 6 ecuaciones mostradas (verificado con 6 bloques MathJax). Calcula el CV a partir de mediciones duplicadas hechas sobre varios sujetos o materiales, como alternativa a hacer muchas observaciones sobre un solo sujeto para estimar directamente la imprecision intraserie (within-run imprecision) (Jones & Payne, 1997). Ofrece tres metodos: Root mean square, Logarithmic y Within-subject standard deviation. El orden de las dos variables de medicion no importa.

**Referencias que cita la pagina:** Bland M (2006) How should I calculate a within-subject coefficient of variation? https://www-users.york.ac.uk/~mb55/meas/cv.htm | Bland M, Altman DG (1996) Statistics Notes: Measurement error proportional to the mean. British Medical Journal 313:106. | Hyslop NP, White WH (2009) Estimating precision using duplicate measurements. Journal of the Air & Waste Management Association 59:1032-1039. | Jones R, Payne B (1997) Clinical investigation and statistics in laboratory medicine. London: ACB Venture Publications. | Synek V (2008) Evaluation of the standard deviation from duplicate results. Accreditation and Quality Assurance 13:335-337.

### Mean (media global)

```
Mean = sum( x_1 + x_2 ) / (2n)
```

**Simbolos / literal de la pagina.** n = numero de pares de datos (number of data pairs); x_1 y x_2 = las mediciones duplicadas

**Supuestos / condiciones.** Ecuacion mostrada. LaTeX original de la pagina: \text{Mean} = \frac{\sum(x_1+x_2)}{2n}

### CV(%) - Root mean square method

```
CV(%) = 100 * sqrt( sum( (d / m)^2 ) / (2n) )
```

**Simbolos / literal de la pagina.** d = the difference between two paired measurements; m = the mean of paired measurements; n = numero de pares de datos

**Supuestos / condiciones.** Metodo atribuido a Hyslop & White, 2009. Ecuacion mostrada. Restriccion literal de la pagina: no puede usarse cuando la media de uno o mas pares de mediciones es 0. La pagina indica que los metodos Root mean square y Logarithmic permiten calcular un intervalo de confianza para el CV y son los metodos recomendados. LaTeX original: \text{CV(\%)} = 100 \times \sqrt{\frac{\sum(d/m)^2}{2n}}

**Intervalo de confianza.** Para el calculo del intervalo de confianza del 95%, la pagina remite a Bland, 2006 (no reproduce la formula del IC).

### sl - suma de cuadrados de las diferencias de logaritmos (Logarithmic method, paso 1)

```
sl = sum( ( ln(x_1) - ln(x_2) )^2 )
```

**Simbolos / literal de la pagina.** x_1 y x_2 = las mediciones duplicadas; ln = logaritmo natural

**Supuestos / condiciones.** Metodo atribuido a Bland & Altman, 1996 y Bland, 2006. Ecuacion mostrada. LaTeX original: sl = \sum(\ln(x_1)-ln(x_2))^2

### CV(%) - Logarithmic method (paso 2)

```
CV(%) = 100 * ( exp( sqrt( sl / (2n) ) ) - 1 )
```

**Simbolos / literal de la pagina.** sl = suma de cuadrados de las diferencias de logaritmos (formula anterior); n = numero de pares de datos

**Supuestos / condiciones.** Metodo atribuido a Bland & Altman, 1996 y Bland, 2006. Ecuacion mostrada. Restriccion literal de la pagina: el metodo logaritmico no puede usarse cuando algun valor es 0 o negativo. LaTeX original: \text{CV(\%)} = 100 \times ( \exp{\sqrt{\frac{sl}{2n}}}-1 )

**Intervalo de confianza.** La pagina declara que los metodos Root mean square y Logarithmic permiten calcular un intervalo de confianza para el CV; remite a Bland, 2006 para el IC del 95%.

### SD - Within-subject standard deviation

```
SD = sqrt( sum( (x_1 - x_2)^2 ) / (2n) )
```

**Simbolos / literal de la pagina.** x_1 y x_2 = las mediciones duplicadas; n = numero de pares de datos

**Supuestos / condiciones.** Atribuido a Jones & Payne 1997 y Synek 2008. Ecuacion mostrada. Condicion literal de la pagina: el metodo Within-subject standard deviation solo puede usarse cuando puede asumirse que la desviacion estandar es razonablemente constante a lo largo del intervalo de concentracion. LaTeX original: \text{SD} = \sqrt{\frac{\sum(x_1-x_2)^2}{2n}}

### CV(%) - Within-subject standard deviation method

```
CV(%) = 100 * SD / Mean
```

**Simbolos / literal de la pagina.** SD = within-subject standard deviation (formula anterior); Mean = media global

**Supuestos / condiciones.** El coeficiente de variacion es la desviacion estandar dividida por la media (x 100). Ecuacion mostrada. Restriccion literal: no puede usarse cuando la media global de las mediciones es 0. LaTeX original: \text{CV(\%)} = 100 \times \frac{\text{SD}}{\text{Mean}}

**Intervalo de confianza.** Ninguno: la pagina declara literalmente que en este metodo no se reporta intervalo de confianza.

---

## Multirules for control chart

`control-chart-rules.php` - https://www.medcalc.org/en/manual/control-chart-rules.php

Pagina del cuadro de dialogo 'Multirules' donde se seleccionan las reglas que se aplicaran al grafico de control. No contiene ninguna ecuacion mostrada (0 bloques MathJax) ni seccion Literature; los criterios de cada regla estan enunciados en prosa y son identicos a los de control-chart.php. Se registran igualmente porque la pagina los declara literalmente.

### 1:2S rule

```
if |measurement - Mean| > 2SD  (o si excede los warning limits)  ->  se comprueban todas las reglas siguientes
```

**Simbolos / literal de la pagina.** SD = standard deviation; Mean = media

**Supuestos / condiciones.** Si esta regla no se selecciona, las reglas siguientes se comprueban tambien cuando la medicion no excede los warning limits de Mean +/- 2SD. Influye particularmente en la 4:1S rule y en la 10:X rule.

### 1:3S rule

```
if measurement > Mean + 3SD  OR  measurement < Mean - 3SD  ->  run is out of control
```

**Simbolos / literal de la pagina.** SD = standard deviation; Mean = media

**Supuestos / condiciones.** Detecta principalmente error aleatorio, pero puede indicar tambien un error sistematico grande.

### 2:2S rule

```
if 2 consecutive measurements exceed the same (Mean + 2S)  OR  the same (Mean - 2S)  ->  run is out of control
```

**Simbolos / literal de la pagina.** S = standard deviation; Mean = media

**Supuestos / condiciones.** Exige el mismo limite (el mismo lado). Detecta error sistematico.

### 4:1S rule

```
if 4 or more consecutive measurements exceed the same (Mean + 1S)  OR  the same (Mean - 1S)  ->  run is out of control
```

**Simbolos / literal de la pagina.** S = standard deviation; Mean = media

**Supuestos / condiciones.** Exige el mismo limite (el mismo lado). Detecta sesgo sistematico.

### 10:X rule

```
if 10 or more consecutive measurements are on the same side of the Mean  ->  run is out of control
```

**Simbolos / literal de la pagina.** Mean = media; umbral 10 configurable

**Supuestos / condiciones.** Se puede seleccionar un valor menor que 10 (mayor sensibilidad) o mayor que 10 (menor sensibilidad). Detecta sesgo sistematico.

---

## Outlier detection

`outliers.php` - https://www.medcalc.org/en/manual/outliers.php

Pagina sin ecuaciones mostradas (0 bloques MathJax). Documenta cuatro procedimientos de deteccion de valores atipicos: Grubbs (left-sided, right-sided, double-sided; Grubbs 1969), Generalized ESD (Rosner 1983) y Tukey (1977). SOLO las definiciones de Tukey se enuncian numericamente en la pagina; para Grubbs y ESD la pagina nombra el metodo y remite a la referencia sin dar el estadistico. Supuesto explicito: los metodos de deteccion de atipicos asumen que los datos siguen una distribucion aproximadamente normal (si el test de normalidad reporta 'reject Normality' los metodos pueden no ser validos y quiza los datos debian transformarse logaritmicamente). Advertencia literal de la pagina: el test de Grubbs solo puede usarse para detectar un unico atipico; si se sospecha mas de uno NO debe repetirse el procedimiento, hay que usar el Generalized ESD test. El nivel alpha (de 0.10 a 0.001) aplica solo a Grubbs y al Generalized ESD; un alpha mayor hace el test mas sensible pero puede dar falsos positivos. La pagina insiste en no eliminar atipicos automaticamente y en reportar siempre los atipicos y como se trataron. Curiosidad recogida en la pagina: John Tukey no usaba el termino 'outlier' sino las clasificaciones 'outside' y 'far out'.

**Referencias que cita la pagina:** Grubbs FE (1969) Procedures for detecting outlying observations in samples. Technometrics 11:1-21. | Rosner B (1983) Percentage points for a generalized ESD many-outlier procedure. Technometrics 25:165-172. | Tukey JW (1977) Exploratory data analysis. Reading, Mass: Addison-Wesley Publishing Company.

### Tukey - 'outside value' (inner fences)

```
outside value  <=>  value < (lower quartile - 1.5 * IQR)   OR   value > (upper quartile + 1.5 * IQR)
```

**Simbolos / literal de la pagina.** lower quartile = cuartil inferior (percentil 25); upper quartile = cuartil superior (percentil 75); IQR = interquartile range (rango intercuartilico)

**Supuestos / condiciones.** Enunciado en prosa con los coeficientes numericos explicitos. La pagina llama a estos limites las 'inner fences'. Atribuido a Tukey, 1977. Detecta multiples atipicos en ambos lados.

### Tukey - 'far out value' (outer fences)

```
far out value  <=>  value < (lower quartile - 3 * IQR)   OR   value > (upper quartile + 3 * IQR)
```

**Simbolos / literal de la pagina.** lower quartile = cuartil inferior (percentil 25); upper quartile = cuartil superior (percentil 75); IQR = interquartile range (rango intercuartilico)

**Supuestos / condiciones.** Enunciado en prosa con los coeficientes numericos explicitos. La pagina llama a estos limites las 'outer fences'. Atribuido a Tukey, 1977.

### Grubbs' test - variantes (definicion operativa, sin estadistico)

```
Grubbs left-sided: check only the smallest value  |  Grubbs right-sided: check only the largest value  |  Grubbs double-sided: check the most extreme value at either side
```

**Simbolos / literal de la pagina.** alpha-level seleccionable de 0.10 a 0.001

**Supuestos / condiciones.** La pagina NO da el estadistico de Grubbs, solo define que valor se examina en cada variante y lo atribuye a Grubbs, 1969. Nota literal: los tests de Grubbs de una sola cola (single-sided) son mas sensibles que el de doble cola (double-sided). Solo sirve para detectar UN atipico; no debe repetirse el procedimiento.

### Generalized ESD test (definicion operativa, sin estadistico)

```
Generalized Extreme Studentized Deviate (ESD) procedure: puede detectar multiples atipicos en un solo paso; parametro = maximum number of outliers to detect
```

**Simbolos / literal de la pagina.** alpha-level seleccionable de 0.10 a 0.001

**Supuestos / condiciones.** La pagina NO da el estadistico del ESD, solo lo describe y lo atribuye a Rosner, 1983. El ejemplo de la pagina usa los datos de Rosner (1983) en su escala original y por eso aplica transformacion logaritmica como en el articulo de Rosner. Es el metodo indicado cuando se sospecha mas de un atipico.

---

## Responsiveness

`responsiveness.php` - https://www.medcalc.org/en/manual/responsiveness.php

Pagina sin ecuaciones mostradas (0 bloques MathJax); los tres indices de responsiveness se definen en prosa como cocientes. Calcula indices de responsiveness, es decir la capacidad de detectar cualquier cambio, a partir de una 1a y una 2a medicion. Reporta summary statistics (tamano de muestra, media, varianza y desviacion estandar de la 1a y la 2a medicion) y la diferencia media con la desviacion estandar combinada (pooled) y, en el caso de observaciones emparejadas, la desviacion estandar de las diferencias emparejadas. Opciones: 'Paired data' (desmarcar si las 2 mediciones son independientes) y 'Calculate differences as' (por defecto 2a menos 1a; opcion 1a menos 2a).

**Referencias que cita la pagina:** Efron B (1987) Better Bootstrap Confidence Intervals. Journal of the American Statistical Association 82:171-185. | Efron B, Tibshirani RJ (1993) An introduction to the Bootstrap. Chapman & Hall/CRC. | Husted JA, Cook RJ, Farewell VT, Gladman DD (2000) Methods for assessing responsiveness: a critical review and recommendations. Journal of Clinical Epidemiology 53:459-168. | Norman GR, Wyrwich KW, Patrick DL (2007) The mathematical relationship among different forms of responsiveness coefficients. Quality of Life Research 16:815-822.

### Effect size (ES) using baseline SD (Glass' Delta)

```
ES_baseline = average difference / SD of the 1st measurement
```

**Simbolos / literal de la pagina.** average difference = diferencia media entre las dos mediciones; SD of the 1st measurement = desviacion estandar de la 1a medicion

**Supuestos / condiciones.** Enunciado en prosa. La pagina lo identifica literalmente como Glass' Delta. Por defecto las diferencias se calculan como 2a menos 1a medicion (opcion para 1a menos 2a).

**Intervalo de confianza.** Bootstrap con correccion de sesgo y acelerado (bias-corrected and accelerated, BCa) segun Efron, 1987 y Efron & Tibshirani, 1993; el numero de replicaciones y la semilla de numeros aleatorios se fijan en las opciones 'Advanced' de bootstrapping.

### Effect size (ES) using pooled SD (Cohen's d)

```
ES_pooled = average difference / pooled SD of both measurements
```

**Simbolos / literal de la pagina.** average difference = diferencia media entre las dos mediciones; pooled SD = desviacion estandar combinada de ambas mediciones

**Supuestos / condiciones.** Enunciado en prosa. La pagina lo identifica literalmente como Cohen's d.

**Intervalo de confianza.** Bootstrap BCa (bias-corrected and accelerated) segun Efron, 1987 y Efron & Tibshirani, 1993.

### Standardized response mean (SRM)

```
SRM = average difference / SD of the differences between the paired measurements
```

**Simbolos / literal de la pagina.** average difference = diferencia media entre las dos mediciones; SD of the differences = desviacion estandar de las diferencias entre las mediciones emparejadas

**Supuestos / condiciones.** Enunciado en prosa. Requiere observaciones emparejadas: la pagina indica que la desviacion estandar de las diferencias emparejadas se reporta solo en el caso de observaciones emparejadas (opcion 'Paired data' seleccionada, es decir mediciones repetidas en los mismos sujetos).

**Intervalo de confianza.** Bootstrap BCa (bias-corrected and accelerated) segun Efron, 1987 y Efron & Tibshirani, 1993.

---

## Variance ratio test (F-test)

`F-test.php` - https://www.medcalc.org/en/manual/F-test.php

Pagina sin ecuaciones mostradas (0 bloques MathJax). Documenta el F-test aplicado a dos variables de la hoja de calculo (a diferencia de comparison-of-standard-deviations-f-test.php, que trabaja con estadisticos introducidos a mano). Unica definicion computacional, en prosa: el F-statistic es el cociente de la varianza mayor sobre la menor, con su valor de P bilateral. Opcion 'Logarithmic transformation' para datos con asimetria positiva. No declara grados de libertad ni metodo de intervalo de confianza.

**Referencias que cita la pagina:** Bland M (2000) An introduction to medical statistics, 3rd ed. Oxford: Oxford University Press.

### F-statistic (variance ratio test)

```
F = larger variance / smaller variance        [cociente de la varianza mayor sobre la menor]
```

**Simbolos / literal de la pagina.** varianzas de las dos muestras (sample 1 y sample 2) identificadas en el dialogo

**Supuestos / condiciones.** ATENCION: enunciado en PROSA, no como ecuacion mostrada. Cita literal de la pagina: 'the F-statistic is given, which is the ratio of the larger variance over the smaller, with its associated (two-sided) P-value'. El valor de P es bilateral (two-sided). Criterio de decision declarado: si P < 0.05 se rechaza la hipotesis nula y se concluye que las dos varianzas difieren significativamente. La pagina NO indica los grados de libertad.

### Comportamiento con la opcion Logarithmic transformation

```
si se selecciona Logarithmic transformation -> se devuelven los summary statistics retrotransformados (back-transformed), pero las varianzas y el variance ratio se dan en la escala log-transformada
```

**Simbolos / literal de la pagina.** -

**Supuestos / condiciones.** Enunciado en prosa. Razon declarada por la pagina: 'The variance of the logs cannot be back-transformed meaningfully'. La transformacion logaritmica se recomienda cuando los datos tienen asimetria positiva (positively skewed).

---

## Comparison of standard deviations (F-test)

`comparison-of-standard-deviations-f-test.php` - https://www.medcalc.org/en/manual/comparison-of-standard-deviations-f-test.php

Pagina de cuadro de dialogo, sin ecuaciones mostradas (0 bloques MathJax). El unico contenido computacional esta enunciado en prosa: el F-test (o variance ratio test) eleva al cuadrado las desviaciones estandar para obtener las varianzas correspondientes y calcula su cociente. El test no se hace sobre datos de la hoja de calculo sino sobre estadisticos introducidos en el dialogo (las dos SD y el numero de casos). La pagina advierte que para comparar dos varianzas conocidas hay que calcular primero las desviaciones estandar tomando la raiz cuadrada, y despues comparar las dos desviaciones estandar. No declara grados de libertad ni metodo de intervalo de confianza.

**Referencias que cita la pagina:** Bland M (2000) An introduction to medical statistics, 3rd ed. Oxford: Oxford University Press.

### F-statistic (variance ratio test) para comparar dos desviaciones estandar conocidas

```
F = (SD_1)^2 / (SD_2)^2        [el cociente de las dos varianzas; si las dos varianzas no difieren significativamente, F sera proxima a 1]
```

**Simbolos / literal de la pagina.** SD_1, SD_2 = las dos desviaciones estandar conocidas introducidas en el dialogo; n_1, n_2 = numero de casos correspondiente a cada muestra

**Supuestos / condiciones.** ATENCION: enunciado en PROSA, no como ecuacion mostrada. La pagina dice literalmente 'In this test, the ratio of two variances is calculated. If the two variances are not significantly different, their ratio will be close to 1' y 'the square of the standard deviations is calculated to obtain the corresponding variances'. La pagina NO especifica que se ponga la varianza mayor en el numerador (a diferencia de F-test.php) ni indica los grados de libertad. Muestras independientes. Ejemplo trabajado propio de la pagina: SD = 25.6 con n = 60 para la primera muestra, SD = 23.2 con n = 80 para la segunda -> F-statistic = 1.2176, P = 0.412; al no ser P < 0.05 se concluye que no hay diferencia significativa entre las dos desviaciones estandar. Criterio de decision declarado: P < 0.05 -> las dos desviaciones estandar son estadisticamente significativamente diferentes.

---

## Comparison of Coefficients of Variation

`comparison-of-coefficients-of-variation.php` - https://www.medcalc.org/en/manual/comparison-of-coefficients-of-variation.php

La pagina NO enuncia ninguna formula (0 bloques MathJax, ningun estadistico escrito). Es una pagina de cuadro de dialogo: documenta que se realiza un test para comparar dos coeficientes de variacion procedentes de muestras independientes, expresados como porcentaje; el test no se hace sobre datos de la hoja de calculo sino sobre estadisticos introducidos en el dialogo (los dos CV en porcentaje y el numero de casos correspondiente). Unica atribucion computacional literal: 'The test is performed according to Forkman (2009)'. Criterio de decision declarado: cuando el valor de P calculado es menor que 0.05, se concluye que los dos coeficientes de variacion son significativamente diferentes. No indica metodo de intervalo de confianza.

**Referencias que cita la pagina:** Forkman J (2009) Estimator and tests for common coefficients of variation in normal distributions. Communications in Statistics - Theory and Methods 38:233-251.

*La pagina no publica formulas.*

---

## Enlaces

- [[MedCalc - Mapa]]
- [[MedCalc - Procedimientos estadisticos]]
- [[MedCalc - Funciones (referencia completa)]]
