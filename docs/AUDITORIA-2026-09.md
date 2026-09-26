# Auditoría de BioStat — 2026-09-26

**Alcance.** Todo lo que produce un número o una decisión:

- las ~100 funciones públicas de `src/core`;
- lo que la capa Qt calcula, arma y **muestra** (`src/ui/analysis_methods.py`: tablas, fórmulas del recuadro, veredictos);
- el Omnianálisis completo: motor, catálogo, árbol dibujado, auditoría y vista caso por caso;
- el Bland-Altman recién migrado a `Resultado` (sin commit a la fecha de este informe).

**Cómo se verificó.**

- **Oráculos independientes:** statsmodels 0.14.6, pingouin 0.6.1, scipy 1.17, lifelines 0.30.3, sklearn 1.9.
- **Simulación:** cobertura de IC y error tipo I, entre 1.000 y 4.000 corridas por punto.
- **Normas leídas del PDF**, no de memoria: CLSI EP28-A3c y EP09c, en `Downloads/CLSI-…/CLSI/`. Las fichas del vault (`Cerebro/CLSI/`) sirvieron para ubicar las secciones.

Los scripts de verificación quedaron fuera del repo. Cada hallazgo de abajo trae el número que lo demuestra.

**Resumen.** 10 críticos, 16 altos, 16 medios. Ninguno de los críticos era visible en la suite: 820 tests en verde y smoke 76/76.

La auditoría de agosto verificó bien el núcleo numérico que miró. Lo que se escapó está en tres lugares:

- funciones del core que no entraron en su tabla (probit, ANCOVA, medidas repetidas);
- la frontera entre la hoja y el core: **qué columnas y qué filas llegan a cada análisis**;
- las reglas de decisión del Omnianálisis, que se habían probado en 3 casos pero no se habían contrastado contra EP09c.

---

## Críticos — el número o la conclusión que ve el usuario está mal

### K1 — Omnianálisis: el sesgo en niveles de decisión sale con el signo invertido
`src/analysis/omni_analyzer.py:926-935`

Cuando el método de referencia declarado es la **segunda** columna del par, la regresión igual pone la primera en X. El sesgo se calcula como Y − X en percentiles de X, o sea **referencia − método en prueba**, en niveles del método en prueba.

| | informado | real |
|---|---|---|
| método en prueba que lee **+10 %** | **−9,3 %** en los tres niveles | +10 % |

EP09c, tabla 1: X es el procedimiento comparativo o de referencia, Y el candidato. El sesgo en un nivel de decisión se evalúa en X_c, que es una concentración del **comparativo**. El orden del par depende del orden alfabético o del de selección, nunca de la referencia.

**Arreglo:** orientar el par por la referencia declarada antes de toda la rama (regresión, niveles, signo de las diferencias). Sin referencia declarada, decirlo en el informe.

### K2 — ANOVA, Kruskal-Wallis, Friedman y Cronbach toman todas las columnas numéricas de la hoja
`src/ui/analysis_methods.py:550, 1358, 1374, 1456`

No usan las variables elegidas: cada columna numérica pasa a ser un grupo. La ayuda del propio programa dice lo contrario: «una variable categórica de múltiples niveles y una respuesta numérica continua».

| hoja `Valor` + `Grupo` (1/2/3), medias iguales | BioStat | correcto |
|---|---|---|
| ANOVA de una vía | F = **7460,6**, p < 0,000001, «SIGNIFICATIVO» | p = 0,79 |
| Kruskal-Wallis | «Error: mínimo 3 grupos» | — |

Compara los valores contra los **códigos** de grupo.

### K3 — Fisher, McNemar, OR, RR, prueba diagnóstica y LR leen las dos primeras filas como una tabla de conteos
`src/ui/analysis_methods.py:1324, 1341, 1553, 1570, 1589, 1873`

Chi² y Kappa, del mismo menú, **tabulan** los datos crudos de las dos primeras columnas numéricas. Fisher y el resto toman `fila 0 = [a, b]` y `fila 1 = [c, d]` de esas columnas. Sobre la misma hoja de 80 pacientes codificados 0/1:

| | BioStat | tabla real `[[34,3],[9,34]]` |
|---|---|---|
| Chi² | p < 0,000001, asociación | — |
| Fisher | **OR = nan, p = 1,000, «sin asociación»** | p ≈ 0 |
| Prueba diagnóstica | sensibilidad 1,000, especificidad «no definida» | — |

Nada avisa. La ayuda de «Prueba diagnóstica» pide «resultados de la prueba y el estándar de oro», es decir, datos crudos.

### K4 — ANCOVA: el cálculo es incorrecto
`src/core/ancova.py:38, 44`

Tiene tres defectos:

- la pendiente de la covariable sale de la regresión **total**, no de la intragrupo;
- el ajuste de las medias tiene el **signo invertido**;
- la SS del error se obtiene por resta y **sale negativa**.

| semilla | F grupo BioStat | statsmodels (y ~ C(g) + x) = pingouin |
|---|---|---|
| 1 | **168,62** (p ≈ 0) | 4,67 (p = 0,013) |
| 2 | **0,00** (p = 1), SS error = **−1015** | 2,18 (p = 0,12) |
| 3 | **0,00** (p = 1), SS error = **−377** | 5,82 (p = 0,005) |

**Arreglo:** delegar en `pingouin.ancova` o en `statsmodels`, como ya se hace con la ANOVA de dos vías.

### K5 — Probit: el mismo bug de Cox que en agosto se arregló solo en Cox
`src/core/probit.py:36, 49`

`result.hes_inv` no existe, y un `except:` desnudo lo tapa. **Todos los EE valen 0,1**, con cualquier dato. Aun con el nombre bien escrito, invertir `hess_inv` daría el Hessiano, no la covarianza. El AIC tiene el signo cambiado.

| | BioStat | statsmodels Probit |
|---|---|---|
| EE (n=40) | 0,1 / 0,1 | 0,250 / 0,412 |
| p intercepto (n=40) | 0,318 | 0,689 |
| AIC (n=60) | **−66,7** | 74,7 |

Los coeficientes coinciden: solo está mal lo que sale de la varianza.

### K6 — Tamaño muestral y poder: los valores están fijos en el código
`src/ui/analysis_methods.py:932, 949, 960, 971`

Estos análisis calculan siempre el mismo ejemplo, sin leer nada del usuario:

- `sample_size_mean(5, 10)`
- `sample_size_two_means(5, 10)`
- `sample_size_proportions(0.3, 0.5)`
- `power_analysis(100, 5, 10)`

El informe termina con un «Tip: usa `sample_size_mean(delta, sd, alpha, power)`», que es una función de Python. La fórmula que muestra 2 medias es la de z, aunque el core pasó a t no central en agosto.

### K7 — Omnianálisis: el mismo par dice «significativo» en su bloque y «no significativo» en la matriz
`src/analysis/omni_analyzer.py:367, 377` y `1040`

La corrección de Benjamini-Hochberg se aplica solo a la matriz de correlación. Los bloques bivariados, que son los mismos pares más las comparaciones de grupos y las tablas, informan el p crudo con su veredicto.

Con 8 columnas de **ruido puro**, el bloque dice «Asociación lineal significativa (p = 0,046)», y la matriz, para el mismo par, dice p ajustado = 0,766, no significativo.

### K8 — Random Forest informa la exactitud sobre los mismos datos con que se entrenó
`src/ui/analysis_methods.py:1158, 1218`

Con 5 predictoras de **ruido puro**, informa exactitud = **0,95**. La validación cruzada da 0,56, y el azar es 0,50.

### K9 — Medidas repetidas: el ε de Greenhouse-Geisser está mal
`src/core/repeated_measures.py:41-43`

Usa la matriz de covarianzas sin doble centrado. La F sin corregir coincide con pingouin; la corregida no.

| | ε BioStat | ε pingouin | p-GG BioStat | p-GG pingouin |
|---|---|---|---|---|
| semilla 1 | 0,747 | 0,548 | 0,00073 | 0,00265 |
| semilla 2 | 0,548 | 0,502 | 0,0124 | 0,0150 |

### K10 — Omnianálisis: 3 o más grupos normales con varianzas distintas van a Kruskal-Wallis
`src/analysis/omni_analyzer.py:478`

Kruskal-Wallis supone distribuciones de igual forma bajo H0. Con dispersiones distintas rechaza por la dispersión, no por la posición.

| medias **iguales**, DE 2/6/14, n 40/20/10 | falsos positivos |
|---|---|
| motor (elige Kruskal-Wallis 1000/1000 veces) | **16,7 %** |
| ANOVA de Welch | 5,6 % |

**Arreglo:** con normales heterocedásticos, ANOVA de Welch con post-hoc de Games-Howell.

---

## Altos — fórmula o regla incorrecta, con impacto acotado

| # | dónde | qué | evidencia |
|---|---|---|---|
| A1 | `core/reference.py:30` | Límites de referencia con el percentil lineal de numpy. EP28-A3c §9.4.1 (p. 24) define r₁ = 0,025·(n+1) y r₂ = 0,975·(n+1), interpolando. El comentario de la línea 8 dice «estadísticos de orden 3 y 118», pero el código cae en 4 y 117. Además, EP28 §9.5.1 define el IC de los límites como un **90 %** por rangos (tabla 8), y BioStat informa un 95 % bootstrap | n=120: BioStat [10,983; 35,008]; EP28 [10,755; 36,214] |
| A2 | `omni_analyzer.py:722, 849` + catálogo y caso | La «estructura de la diferencia» regresa la **media** de las diferencias, o sea el sesgo proporcional, y la usa como si fuera **heterocedasticidad**. EP09c §5.4 pide determinar primero si la **variabilidad** de las diferencias es constante (DE) o proporcional (CV). §6.2 indica Deming para DE constante y **Deming ponderado** para CV constante; BioStat no tiene Deming ponderado | CV constante sin sesgo: «constante / homocedástico» 190/200. Sesgo proporcional con DE constante: Deming descartado por «error heterocedástico» 200/200 |
| A3 | `core/diagnostic_tests.py:77, 79` | EE del ln(LR+) con términos de LR−, y LR− reutiliza ese mismo EE | cobertura del IC 95 %: **100 %** (Simel 1991 da 95,2 %). (90,20,10,80): LR+ IC [2,09; 9,70], correcto [3,02; 6,70] |
| A4 | `core/statistics.py:57` | IC de la media recortada con la DE de la muestra recortada, cuando corresponde la varianza winsorizada (Tukey-McLaughlin) | cobertura **86,1 %**; con el EE correcto, 95,5 % |
| A5 | `core/outliers.py:46` | El p de Grubbs invierte la relación G→t sin el factor n/(n−1) | con G = G crítico: «es outlier: SÍ» con p = **0,13** (n=8), 0,078 (n=15); el correcto es 0,050 |
| A6 | `core/survival.py:84` | Log-rank descarta los tiempos 0 y deja esos sujetos en el conjunto de riesgo | χ² 0,001 contra 1,705 de lifelines (con los mismos datos corridos +0,5: 1,705) |
| A7 | `core/reference.py:117` | Intervalos por edad: las edades del último tramo quedan fuera de todos los grupos | 500 sujetos de 18 a 90 años: **17 perdidos** (≥ 88 años), sin aviso |
| A8 | `omni_analyzer.py:566, 601` + `omni_caso.py:413` | Tabla r×c con esperadas < 5: corre chi². La auditoría escribe «esperada mínima **0,1 ≥ 5**», y el caso dice «se calcula la probabilidad exacta» para mostrar en el paso siguiente «Chi-cuadrado: p = 0,4363» | tabla 3×3, esperada mínima 0,1 |
| A9 | `analysis_methods.py:642` | ROC sin IC ni EE del AUC, y sin detectar la dirección invertida | score invertido: AUC = 0,064, «POBRE», umbral con sensibilidad 1 y especificidad 0; invertido sería 0,936 |
| A10 | `analysis_methods.py:1892` y siguientes | «Comparar 2 medias / proporciones / AUC» toman las primeras 6 o 4 filas de la primera columna como m1, sd1, n1… aunque la hoja tenga datos reales | 40 glucemias: «t = −1,01, p = 0,31, SIN DIFERENCIA» calculado con las 6 primeras |
| A11 | `core/serial_measurements.py:31` | «p global» de una regresión que trata las n×k mediciones como independientes | pendientes individuales sin tendencia real: p < 0,05 en **19,7 %**; con niveles individuales: 0,1 % |
| A12 | `core/plots.py:111`, UI 2318 | El «Mountain plot» es un histograma con una normal ajustada. Un mountain plot (Krouwer y Monti 1995) es la acumulada plegada de las diferencias entre dos métodos | leído del código |
| A13 | `core/agreement.py:139` | Deming: λ se usa invertido respecto de su propia documentación (`var_err(x)/var_err(y)`). **Latente**: la UI y el Omnianálisis usan λ = 1 | errores DE 6 en X y 1,5 en Y, pendiente real 1,10: ODR 1,089; BioStat 1,076; con 1/λ, 1,089 |
| A14 | `omni_arbol.py:137-138, 168-169` | El árbol dibujado no coincide con el motor. «3+, normal → ANOVA» omite la condición de Levene. «constante → Deming» omite la de normalidad de las diferencias | leído del código |
| A15 | `omni_analyzer.py:131` | Grupos codificados 1/2/3 (enteros ≤ 10 valores) → «numérica discreta» → correlación de Spearman, en vez de comparación de grupos | Hb × Grupo(1,2,3): «Spearman ρ = 0,52, asociación monótona significativa» |
| A16 | `omni_caso.py:588` | Cuando el paso 1 (pendiente de diferencias contra promedio) y la regresión discrepan, el caso dice «vale la del paso 1». Esa pendiente es la que se ve afectada cuando los dos métodos tienen imprecisión distinta: cov(d, m) = (σ²ₐ − σ²_b)/2 (Bland y Altman 1999). No hay base para darle prioridad | leído del código |

---

## Medios

| # | dónde | qué |
|---|---|---|
| M1 | `core/agreement.py:22` | El p de kappa usa el EE bajo H1 en lugar de H0: p 0,0020 contra 0,0039 (statsmodels). **Kappa sin IC**, que MedCalc sí informa: statsmodels da (0,151; 0,649) |
| M2 | `core/statistics.py:93, 110` | Asimetría y curtosis con EE asintótico. Con datos normales, error tipo I de 1,2 % y **0,1 %** (n=10), 2,8 % y 1,3 % (n=20). D'Agostino y Anscombe-Glynn dan ~5 % |
| M3 | `core/statistics.py:194` | Prueba F de varianzas: p = **1,008** con n muy desiguales |
| M4 | `core/diagnostic_tests.py:129` | IC de p1 − p2 con el EE agrupado (el de H0): [0,050; 0,350] contra [0,087; 0,313] |
| M5 | `core/bootstrap.py:103` | Bootstrap de la correlación con n=5: IC = (nan, nan), porque hay remuestreos constantes y `percentile` propaga el NaN |
| M6 | `core/regression.py:64` | Regresión múltiple con predictoras colineales: EE = 0 y **p = 1 en todos**, sin aviso |
| M7 | `core/statistics.py:66, 76` | Medias geométrica y armónica descartan ceros y negativos en silencio: [0, 2, 8, −1, 4] → MG = 4 |
| M8 | `omni_analyzer.py:536` | «Dunn (Bonferroni)» es Mann-Whitney por pares con Bonferroni. Los p difieren poco (0,157 contra 0,160), pero el nombre del test es otro |
| M9 | `core/passing_bablok.py:25` | Descarta los pares con xᵢ = xⱼ. EP09c, apéndice I2, los toma como ±∞ según el signo de yᵢ − yⱼ. Con datos redondeados a entero, la pendiente difiere en 190/200 corridas, hasta 0,014 |
| M10 | UI, recuadro de fórmula | Fórmulas que no son lo que se calcula: descriptivas «IC = x̄ ± 1,96·SE» (el core usa t); chi² sin mencionar Yates en 2×2; percentiles «k·(n+1)/100» (el core usa el lineal); CV de duplicados «DE/Media» (es DE(d)/(√2·media)); ICC con la fórmula de MS_error para el modelo de una vía; 2 medias con z |
| M11 | `core/agreement.py:95` | ICC por defecto de una vía, ICC(1,1), informado como «ICC» a secas. Para dos métodos o evaluadores fijos corresponde el de dos vías de acuerdo absoluto |
| M12 | UI 1496, 1524 | Regresión múltiple y logística: el objetivo es la **última** columna numérica y las predictoras, **todas** las demás |
| M13 | UI 615 | Shapiro-Wilk con p ≥ 0,05 dice «Es normal. Puedes usar pruebas paramétricas»: no rechazar no es probar |
| M14 | Omni, conclusiones | Los bloques del informe dicen «significativa»; la vista por caso evita esa palabra a propósito |
| M15 | `omni_catalogo.py:89, 223` | El catálogo dice que Anderson-Darling evita rechazar por desviaciones triviales (es aún más potente) y que el promedio «ATENÚA» (el motor ya sabe que distorsiona en las dos direcciones) |
| M16 | `core/bland_altman.py:228` | Bland-Altman múltiple compara todas las columnas contra todas, sin referencia (MedCalc usa Krouwer) y sin IC de los límites |

---

## El Bland-Altman migrado (sin commit)

Los números son los del core, y la paridad contra el informe viejo dio 642/642. Hereda dos puntos de arriba:

- **No evalúa la variabilidad de las diferencias** (DE o CV constante, EP09c §5.4) antes de dar límites en unidades absolutas.
- **El signo** es d = columna 1 − columna 2, aunque la referencia declarada sea la columna 1. EP09c usa candidato − comparativo.

---

## Verificado correcto

Revisado el código, y cuando hay oráculo, el número:

- **Pruebas de hipótesis:** t de una muestra, pareada y de Welch; Mann-Whitney; Wilcoxon; signos; Kruskal-Wallis; Friedman; Q de Cochran; chi² (scipy); Fisher; McNemar (igual a statsmodels); Pearson; Spearman; correlación parcial.
- **Regresión:** lineal simple; múltiple sin colinealidad; logística (statsmodels); ANOVA de dos vías (statsmodels, tipo II).
- **Diagnóstico y riesgo:** OR y RR con Haldane; IC de Wilson.
- **Supervivencia y meta-análisis:** Kaplan-Meier; log-rank con tiempos > 0; meta-análisis (DerSimonian-Laird); CMH (Robins-Breslow-Greenland); Cox (Efron, contra lifelines en agosto).
- **Comparación de métodos:** pendiente, K e IC de Passing-Bablok (EP09c I7-I11); LoA de Bland-Altman y su IC con t(n−1); CCC e IC; Deming con λ = 1.
- **Resto:** ESD de Rosner; kappa simple y ponderado (el valor); tamaño muestral del core (t no central); Youden.

## Correcciones a lo que se había dado por verificado

- **«Deming — dirección de λ correcta»** (auditoría de agosto, HANDOFF y la ficha `Cerebro/Proyectos/BioStat/BioStat.md`): es al revés, ver A13.
- **«Omni: ruteo 3/3»:** los tres casos no cubrían grupos codificados con enteros, heterocedasticidad en 3 o más grupos, tablas r×c ralas ni una referencia declarada en la segunda columna.

## Orden de arreglo propuesto

1. **Lo que devuelve basura sin avisar:** K2, K3, K6, A10 (qué columnas y filas llegan a cada análisis) y K1 (signo del sesgo).
2. **Reemplazar por oráculo:** K4 ANCOVA → pingouin; K5 probit → statsmodels; K9 → `pingouin.rm_anova`; K8 → validación cruzada.
3. **Reglas del Omnianálisis:** K10 (ANOVA de Welch), K7 (una sola política de multiplicidad), A2 y A15 (EP09c §5.4/§6.2, con Deming ponderado), A8, A14, A16.
4. **Fórmulas puntuales:** A1 (EP28), A3, A4, A5, A6, A7, A13, M1–M9.
5. **Textos:** M10, M13, M14, M15.

Cada arreglo lleva un test que falle antes y pase después, igual que en agosto. Donde el número cambia a propósito, el test lo dice en su nombre.
