# Auditoría numérica de BioStat — 2026-08-23

**Alcance:** ~100 funciones públicas de `src/core`, el motor del Omnianálisis y la
capa Qt. Oráculos independientes: scipy 1.17, statsmodels 0.14.6, lifelines
0.30.3, sklearn 1.9, pingouin 0.6.1, y ejemplos publicados (NIST/SEMATECH,
CLSI EP12/EP28, Passing & Bablok 1983).

**Estado:** 443 → **698 tests** verdes, smoke UI 76/76, 0 bugs de código.

---

## Defectos que cambiaban un resultado clínico

### D1 — Passing-Bablok: el intervalo de confianza no era un intervalo de confianza
`src/core/passing_bablok.py`

Usaba los percentiles empíricos 2,5 y 97,5 de las pendientes por pares. Las Sij
no son observaciones independientes, así que sus cuantiles no forman un IC.

| n | cobertura del "IC 95%" | ancho | ancho correcto |
|---|---|---|---|
| 30 | 100 % | 2.62 | 0.074 |
| 50 | 100 % | 2.41 | 0.056 |
| 100 | 100 % | 2.37 | 0.038 |

**Potencia ante un sesgo proporcional real del 10 %: 0 de 900 corridas.** La
implementación correcta detecta 99.7–100 %. Un laboratorio habría concluido
"métodos intercambiables" teniendo 10 % de sesgo. El daño llegaba al
Omnianálisis: `omni_analyzer.py` decide `sesgo_proporcional` preguntando si ese
IC contiene el 1.

Corregido con estadísticos de orden: `C = z·√(n(n−1)(2n+5)/18)`, `M1 =
round((N−C)/2)`, `M2 = N−M1+1`.

### D2 — Passing-Bablok: era Theil-Sen, no Passing-Bablok
Faltaba el desplazamiento `K = #{Sij < −1}` de la mediana. Se detecta con la
propiedad que define al método —simetría al intercambiar ejes, `b(x,y)·b(y,x) = 1`
exacto—: daba 0.994 con datos limpios y **0.04** con ruido.

### D3 — Cox: los errores estándar eran una constante
`src/core/cox_regression.py`

```python
hessian_inv = np.linalg.inv(result.hes_inv) if hasattr(result, 'hes_inv') else np.eye(p) * 0.01
```

El atributo de scipy es `hess_inv`. El `hasattr` daba **siempre** False y caía al
`else`: todos los errores estándar valían exactamente 0.1, con cualquier dato y
cualquier n. De ahí salían todos los z y todos los p.

Dos defectos más en la misma función: el conjunto de riesgo estaba invertido
(`np.cumsum(...)[::-1]`), y el AIC tenía el signo cambiado (`2p + 2logL`), o sea
que premiaba el peor modelo. Reescrito con Efron; coincide con lifelines a 1e−5
en coeficientes, 1e−6 en SE, 1e−9 en p y log-verosimilitud, con y sin empates.

### D4 — AUC subestimado cuando el score tiene empates
`src/core/roc.py`

La curva no incluía el origen (0,0) y evaluaba cada umbral por separado, así que
el trapecio se comía el triángulo inicial. Error **siempre por debajo**:

| score | error medio | máximo |
|---|---|---|
| continuo | 0.000000 | 0.000000 |
| 20 niveles | −0.000261 | 0.001063 |
| 5 niveles | −0.009149 | 0.015006 |
| binario | **−0.094580** | 0.111667 |

En laboratorio los scores empatan todo el tiempo: escalas semicuantitativas,
resultados redondeados, ordinales. Ahora coincide con `sklearn.roc_auc_score`
exacto en todas las densidades de empate.

### D5 — CMH: el IC del OR contradecía a su propio p
`src/core/cmh.py`

La varianza del log(OR) no era ninguna de las publicadas. Daba `se = 1.967`
donde corresponde `0.468`: con **p = 0.00036** el IC era **(0.109, 243.9)**, que
contiene el 1 holgadamente. Reemplazada por Robins-Breslow-Greenland (1986);
ahora coincide con statsmodels a 5.6e−17.

### D6 — ESD generalizado: perdía el enmascaramiento
`src/core/outliers.py`

Dos errores. `λ_i` restaba `i` a una `n` que ya venía reducida —doble resta—, y
el error crecía con cada paso: contra el ejemplo publicado del NIST, −0.003 en
el primero y −0.100 en el décimo. Y evaluaba cada punto por separado en vez de
aplicar la regla de Rosner (el **mayor** i con R_i > λ_i).

El ejemplo del NIST está construido justo para eso: R₁ y R₂ **no** pasan, R₃
**sí**. Respuesta publicada: 3 outliers. BioStat declaraba **1**. Ahora declara 3,
con λ a 0.0009 del publicado.

### D7 — Tamaño muestral: z donde va t, y la app se autoconfirmaba
`src/core/sample_size.py`

| delta/sd | n que daba | n correcto | poder real de ese n |
|---|---|---|---|
| 0.4 | 50 | 52 | 0.792 |
| 1.0 | 8 | 10 | 0.681 |
| **2.0** | **2** | **5** | **0.176** |

Se pedía 0.80 y se obtenía 0.18. Peor: `power_analysis` también usaba z, así que
la ida y vuelta cerraba en 0.807 y confirmaba su propio error. Reescrito con t no
central; coincide con statsmodels en las 22 celdas probadas.

### D8 — Kappa ponderado devolvía −55
`src/core/agreement.py`

```python
e = np.outer(row_sums, col_sums) / n**2   # ya es matriz de PROPORCIONES
p_e = 1 - np.sum(w * e) / n               # y vuelve a dividir por n
```

Doble división: `p_e ≈ 1` y el cociente estallaba contra un denominador ≈0.
κ está acotado a [−1, 1]. Estaba expuesto en la UI como "Kappa ponderado". Ahora
coincide con `sklearn.cohen_kappa_score` exacto, lineal y cuadrático.

### D9 — Grubbs: `side` se aceptaba y se ignoraba, y el p llegaba a 3.58
Pedir `side="upper"` devolvía el resultado de `"both"`. Y el factor `2n` es una
cota de Bonferroni, que puede pasarse de 1: se informaban "probabilidades" de
hasta 3.58.

### D10 — Riesgo relativo: rechazaba tablas calculables
`src/core/diagnostic_tests.py`

Exigía `b != 0 and d != 0`, pero el RR no los necesita: `b = 0` solo significa
que todos los expuestos tuvieron el evento. Devolvía `None` y la UI mostraba "No
se pudo calcular". Además, con `a = 0` el error estándar quedaba en 0 y el IC
salía de ancho cero —precisión absoluta a partir de cero eventos—, y el NNT
devolvía infinito cuando la exposición **aumenta** el riesgo, diciendo "no hay
efecto" justo donde el efecto es dañino.

### D11 — Sensibilidad y especificidad sin ningún intervalo de confianza
CLSI EP12 los exige. Sin ellos, 20 de 20 se lee como "sensibilidad 100 %" a
secas. Agregado el IC de Wilson (verificado contra statsmodels): para 20/20 da
(0.839, 1.000); el de Wald daría (1.000, 1.000), ancho cero.

### D12 — Intervalo de referencia sin el mínimo de EP28
`reference_interval` no mencionaba en ningún n los 120 sujetos que pide CLSI
EP28-A3c para establecer un intervalo no paramétrico. El usuario lleva ese número
a una acreditación. Ahora avisa por debajo de 120, distingue establecer de
verificar, y dice cuántos datos sostienen cada límite.

---

## Robustez: la app no se cae

Barrido de **3.990 llamadas** contra entradas hostiles sobre las ~100 funciones
públicas.

### R1 — Los infinitos se colaban por el filtro
El core limpiaba con `~np.isnan(x)`, que descarta NaN pero **no** ±inf.
`ttest_ind` devolvía t, p, media y sd en NaN, en silencio. Un inf entra solo:
`#¡DIV/0!` de Excel, log(0), código de desborde del analizador.

`guards.py` ya usaba `isfinite` y lo explicaba en un comentario, pero nunca se
había propagado: **44 sitios en 13 archivos** seguían con `isnan`. Migrados.
Incluso `validation.py` —el módulo cuyo trabajo es validar— dejaba pasar los
infinitos, y `get_validation_summary` devolvía `max = inf` porque `np.nanmax`
saltea NaN pero no inf.

### R2 — Datos constantes: 8 funciones devolvían NaN sin decir por qué
Es el modo de falla que el propio `guards.py` declara querer evitar: *"Devolver
NaN sin avisar es peor que rechazar: el número llega al informe y se reporta."*
Ahora rechazan con motivo. `descriptive_stats` conserva lo que sí vale (media,
mediana, extremos) y avisa qué queda indefinido.

### R3 — Cuatro crashes del Omnianálisis, tres causados por mi propio arreglo
Endurecer `pearson_r` movió la falla de "NaN mudo en el informe" a
`KeyError: 'r'`, porque el analizador hacía `pearson_r(a, b)["r"]` sin mirar. Las
dos son inaceptables. Guardados los llamadores; un par indefinido ya no entra en
la corrección FDR con un p fabricado ni tumba los pares sanos.

Los 12 datasets hostiles pasan: una sola fila, columnas constantes, 90 %
faltantes, texto, infinitos, acentos, fechas, todo cero, escala 1e12 y 1e−9.

### R4 — Otros
`compare_two_proportions` no validaba que p ∈ [0,1]: con conteos, `p_pool > 1`,
la raíz de un negativo daba NaN y llegaba a pantalla. `compare_two_means` no
validaba n ≥ 2 (divide por n−1). `graphs_panel` dibujaba **"r = nan"** sobre el
gráfico con una columna constante.

---

## Verificado correcto con oráculo fuerte

| área | oráculo | resultado |
|---|---|---|
| Bland-Altman LoA | modelo simulado, 600 corridas | encierran 95.3 % (nominal 95) |
| IC del LoA | varianza B&A 1999 + cobertura | 94.5 %; fórmula exacta a 1e−12 |
| CCC de Lin | identidad ρc = ρ·Cb | exacta (0.0e+00) en 400 datasets |
| IC del CCC | cobertura, 500 corridas | 97.8 % |
| McBride | cortes publicados | 4/4 |
| Deming | scipy.odr | 5/5 a 1e−4; dirección de λ correcta |
| Kappa simple | sklearn | exacto |
| CV de duplicados | CV verdadero simulado | 5.07 vs 5.00 |
| Kaplan-Meier | lifelines | 1e−15; IC dentro de [0,1] |
| Log-rank | lifelines | exacto |
| Regresión múltiple | statsmodels OLS | p y R²aj exactos a escala 1e3…1e−4 |
| Meta-análisis | I² = max(0,·), Q | correcto; homogéneos → I² = 0 |
| ICC | delega en pingouin | el oráculo ya está adentro |
| Regresión logística | delega en statsmodels Logit | ya migrada |
| Omni: catálogo/analizador | 41 ensayos | 41 = 41, sin huérfanos ni muertos |
| Omni: ruteo | 3 casos de respuesta conocida | 3/3 |
| Omni: texto vs números | 10 escenarios | 0 contradicciones |

Los `linregress` desempaquetados por posición —el bug encontrado en la sesión
anterior— no se replicaron en ningún otro sitio.

---

## Limitaciones que quedan anotadas, sin ser defectos

**Passing-Bablok sub-cubre cuando un método es mucho más preciso que el otro.**
El método asume error en ambos con razón de varianzas igual a la pendiente. Con
el supuesto cumplido la cobertura es 95–96 %; con el error concentrado en un solo
método cae a 66–78 %. Es limitación del método, no de la implementación —ambas
coinciden exacto—, pero conviene advertirla en pantalla.

**`compare_two_auc` solo hace el caso independiente.** El uso clínico habitual es
comparar dos pruebas sobre los mismos pacientes, donde las AUC están
correlacionadas y este p es conservador. La firma no recibe la correlación, así
que no puede hacer el caso pareado. Agregado el aviso; falta DeLong.

**CMH sin prueba de homogeneidad.** Agrupar estratos solo es válido si los OR son
homogéneos. Falta Breslow-Day.

**El IC del intervalo de referencia es bootstrap, no los rangos de orden
tabulados en EP28.** Con n ≥ 120 coinciden de cerca; por debajo el bootstrap es
optimista porque remuestrea de una cola casi vacía. Declarado en el retorno.
