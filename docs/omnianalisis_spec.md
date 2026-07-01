# Motor de Omnianálisis Estadístico — Especificación Técnica

> Documento base para implementación. El motor es un **árbol de decisiones determinista**: reglas `if/then` explícitas, sin ningún modelo que "decida" qué análisis correr. Cada resultado que se emite es trazable a la condición que lo gatilló.

---

## 0. Principios de diseño (no negociables)

1. **Determinismo total.** El motor no usa un LLM para elegir análisis. Toda decisión es una regla explícita sobre la estructura y las propiedades de los datos. Un LLM puede, opcionalmente, redactar el reporte final en lenguaje natural — pero nunca decide qué test correr.
2. **Verificar supuestos ANTES de elegir el test.** En cada nodo donde exista variante paramétrica vs no paramétrica, primero se verifica el supuesto, después se elige la rama. El motor **jamás** ejecuta un test cuyos supuestos no se cumplieron.
3. **Trazabilidad.** Cada análisis emitido debe registrar: qué condición lo gatilló, qué supuestos se verificaron, con qué resultado, y por qué se descartaron las alternativas.
4. **Advertencias activas.** Cuando el motor detecta que un análisis popular sería inapropiado, lo marca explícitamente en el output (ej: "Pearson mide asociación, no acuerdo").
5. **Parámetros configurables, no incrustados.** Todos los umbrales (ver Anexo A) viven en un archivo de configuración. Los valores dados son puntos de partida razonables, a calibrar con datos reales.

---

## 1. Nodo raíz: Perfilado (corre siempre)

Antes de cualquier estadística, el sistema caracteriza la base de datos. **Esta capa define qué ramas del árbol se activan.**

### 1.1 Clasificación de tipo por columna

La decisión más importante de todo el sistema. Por cada columna, determinar:

| Tipo | Criterio de detección |
|------|----------------------|
| Numérica continua | Valores reales, alta cardinalidad |
| Numérica discreta / conteo | Enteros no negativos, cardinalidad moderada |
| Categórica nominal | Texto o pocos valores sin orden natural |
| Categórica ordinal | Categorías con orden declarado o inferible |
| Binaria | Exactamente 2 valores distintos |
| Fecha / tiempo | Parseable como fecha |

> **Nota de implementación:** la distinción continua/discreta y nominal/ordinal a veces es ambigua. Cuando la cardinalidad caiga en zona gris (ver `CARDINALITY_THRESHOLD` en Anexo A), marcar como ambiguo y pedir confirmación al usuario en vez de asumir.

### 1.2 Métricas estructurales

- Número de columnas → **primer switch del árbol** (Rama A / B / C)
- Número de filas (n) → condiciona qué tests tienen potencia suficiente
- % de nulos por columna
- Duplicados (filas completas y por columna)
- Forma del dataset: transversal / serie temporal / pareado

---

## 2. Switch principal: número de columnas

```
perfilado()
│
├── 1 columna  → Rama A (univariado)
├── 2 columnas → Rama B (univariado ×2 + bivariado)
└── 3+ columnas → Rama C (univariado ×N + todos los pares + multivariado)
```

---

## 3. Rama A — Una sola columna

No hay asociaciones posibles. Solo describir la variable según su tipo.

### 3.1 Si es NUMÉRICA

```
1. Descriptivos:
   n, media, mediana, DS, CV, mín, máx, Q1, Q3, IQR, rango

2. Forma de la distribución:
   asimetría (skewness), curtosis

3. NODO DE DECISIÓN — Normalidad:
   test de normalidad (Shapiro-Wilk si n < SHAPIRO_MAX, si no usar
   Anderson-Darling o Kolmogorov-Smirnov con Lilliefors)
   │
   ├── Normal    → reportar tendencia central como MEDIA ± DS
   └── No normal → reportar tendencia central como MEDIANA + IQR
                   (+ ADVERTENCIA: usar media aquí sería engañoso)

4. Outliers: regla de Tukey (fuera de [Q1 − 1.5·IQR, Q3 + 1.5·IQR])

5. Visualización: histograma + Q-Q plot
```

### 3.2 Si es CATEGÓRICA

```
1. Tabla de frecuencias (absolutas y relativas)
2. Moda
3. Entropía / índice de diversidad (si aplica)
4. Visualización: gráfico de barras
```

---

## 4. Rama B — Dos columnas

Ejecuta univariado sobre cada columna (Rama A) **más** el análisis bivariado. La combinación de tipos decide el test, sin criterio "inteligente".

### 4.1 Matriz de decisión bivariada

| Columna 1 | Columna 2 | Verificación de supuestos | Test si se cumplen | Test si NO se cumplen |
|-----------|-----------|--------------------------|--------------------|-----------------------|
| Numérica | Numérica | Normalidad bivariada | **Pearson** | **Spearman** |
| Numérica | Categórica (2 grupos) | Normalidad por grupo + homocedasticidad (Levene) | **t-test** | **Mann-Whitney U** |
| Numérica | Categórica (3+ grupos) | Normalidad por grupo + homocedasticidad (Levene) | **ANOVA** | **Kruskal-Wallis** |
| Categórica | Categórica | Frecuencias esperadas ≥ 5 en todas las celdas | **Chi-cuadrado** | **Test exacto de Fisher** |

> Para ANOVA significativo, gatillar post-hoc (Tukey HSD si paramétrico, Dunn si Kruskal-Wallis).

### 4.2 Sub-árbol de concordancia (numérica × numérica)

Solo tiene sentido cuando **las dos columnas son mediciones de lo mismo** (dos métodos, dos equipos, dos observadores). Como no usamos un LLM para inferir significado, se gatilla por **reglas duras + ventana de confirmación** (ver Sección 6).

Una vez confirmado que es comparación de métodos:

```
1. NODO DE DECISIÓN — Estructura de la diferencia:
   regresión de (diferencia) vs (promedio de ambos métodos)
   │
   ├── Diferencia constante     → trabajar con diferencias ABSOLUTAS
   └── Diferencia proporcional  → trabajar con diferencias RELATIVAS (%)
                                  o transformar (log)

2. NODO DE DECISIÓN — Normalidad de las DIFERENCIAS:
   (¡de las diferencias, NO de los datos crudos!)
   test de normalidad sobre la serie de diferencias
   │
   ├── Normal    → Bland-Altman PARAMÉTRICO
   │               (sesgo medio ± 1.96·DS, con IC de los LoA)
   └── No normal → Bland-Altman NO PARAMÉTRICO
                   (percentiles empíricos 2.5 y 97.5)

   ⚠️ ESTE es el nodo que evita el error de calcular Bland-Altman
      paramétrico sobre datos no paramétricos.

3. Regresión de comparación — NODO DE DECISIÓN:
   │
   ├── Sin distribución asumida / con outliers → Passing-Bablok
   │      (reportar intercepto e IC → sesgo constante;
   │       pendiente e IC → sesgo proporcional)
   │      Decisión automática:
   │        ¿IC del intercepto incluye 0?  → no hay sesgo constante
   │        ¿IC de la pendiente incluye 1? → no hay sesgo proporcional
   │
   ├── Datos ~normales + homocedástico → Deming
   └── Error heterocedástico           → Deming ponderado

   ⚠️ ADVERTENCIA ACTIVA: si el usuario/sistema intenta OLS (regresión
      lineal ordinaria) para comparar métodos, MARCARLO como inapropiado.
      OLS asume que X no tiene error; en comparación de métodos ambos ejes
      tienen error.

4. Concordancia global:
   CCC (Coeficiente de Correlación de Concordancia de Lin)

   ⚠️ ADVERTENCIA ACTIVA: NO usar Pearson como medida de acuerdo.
      Correlación alta ≠ concordancia. Pearson solo sirve aquí para
      verificar que el rango de concentraciones es suficiente.

5. Imprecisión (SOLO si hay réplicas):
   CV intra-ensayo, CV inter-ensayo, repetibilidad, reproducibilidad
```

---

## 5. Rama C — Tres o más columnas

Ejecuta todo lo de Rama A por columna y Rama B por cada par, **más** lo que solo tiene sentido con múltiples variables.

```
1. Matriz de correlación completa
   → método correcto CELDA POR CELDA según normalidad de cada par
     (no asumir Pearson para toda la matriz)

2. Detección de pares candidatos a concordancia
   → correr reglas duras (Sección 6) sobre TODOS los pares numéricos
   → una sola ventana de confirmación que liste todos los candidatos

3. Si hay variable numérica "objetivo" + varias predictoras:
   → regresión múltiple (con diagnóstico de supuestos:
     linealidad, normalidad de residuos, homocedasticidad,
     multicolinealidad vía VIF)

4. Si hay muchas numéricas sin objetivo claro:
   → PCA y/o clustering (exploratorio)

5. ⚠️ CORRECCIÓN POR MULTIPLICIDAD — OBLIGATORIA:
   al correr muchas comparaciones simultáneas, algunas saldrán
   "significativas" por azar.
   → aplicar Benjamini-Hochberg (FDR) sobre el conjunto de p-valores
   → reportar tanto p crudo como p ajustado
```

---

## 6. Nodo de detección de comparación (reglas duras + confirmación)

El motor detecta candidatos automáticamente pero **el usuario confirma el contexto**. Reglas duras que proponen, humano que valida. Cero inferencia de significado por LLM.

### 6.1 Cálculo del puntaje de sospecha (por par de columnas numéricas)

```
score = 0

// Reglas fuertes
if (misma_unidad_declarada)               score += PESO_UNIDAD
if (rangos_solapados)                     score += PESO_RANGO
if (mismo_orden_de_magnitud)              score += PESO_ESCALA
if (correlacion >= CORR_MIN_COMPARACION)  score += PESO_CORR

// Reglas de apoyo
if (nombres_columnas_similares)           score += PESO_NOMBRE
if (mismo_n && sin_nulos_desalineados)    score += PESO_PAREADO
if (media_diferencias_pequena)            score += PESO_DIF_CHICA

if (score >= SCORE_UMBRAL_COMPARACION)
    → gatillar ventana de confirmación
else
    → tratar como par numérico común (solo correlación)
```

### 6.2 Ventana de confirmación

**No** debe ser un sí/no pelado. Debe mostrar el razonamiento y las consecuencias:

```
┌─────────────────────────────────────────────────────────┐
│ ¿Estas dos columnas son mediciones de lo mismo?          │
│                                                          │
│ Detecté que [col_A] y [col_B] podrían ser mediciones     │
│ comparables porque:                                      │
│   • comparten rango ([min]–[max])                        │
│   • tienen escala similar                                │
│   • correlacionan alto (r = [valor])                     │
│                                                          │
│ Si confirmás: corro Bland-Altman, Passing-Bablok y CCC.  │
│ Si no: las trato como variables independientes (solo     │
│        correlación).                                     │
│                                                          │
│   [ Sí, son comparables ]   [ No, son independientes ]   │
└─────────────────────────────────────────────────────────┘
```

### 6.3 Reglas de la ventana

- **Múltiples candidatos (Rama C):** una sola ventana con checkboxes para confirmar varios pares de una vez, no una ventana por par.
- **Salvaguarda manual:** siempre disponible un botón "marcar columnas como comparables manualmente", por si dos métodos miden lo mismo pero en unidades distintas o con nombres no parecidos y las reglas duras no los pillan. El automatismo propone, nunca encierra.

---

## Anexo A — Parámetros configurables

> Valores de partida. **Calibrar con datos reales.** No incrustar en el código.

| Parámetro | Valor inicial sugerido | Qué controla |
|-----------|------------------------|--------------|
| `SHAPIRO_MAX` | 5000 | n máximo para usar Shapiro-Wilk; sobre esto, usar Anderson-Darling/KS |
| `ALPHA` | 0.05 | Nivel de significancia |
| `TUKEY_K` | 1.5 | Multiplicador IQR para outliers |
| `FISHER_MIN_FREQ` | 5 | Frecuencia esperada mínima antes de saltar de Chi² a Fisher |
| `CARDINALITY_THRESHOLD` | 10 | Corte para distinguir discreta/continua y nominal/ordinal |
| `CORR_MIN_COMPARACION` | 0.80 | Correlación mínima para sospechar comparación de métodos |
| `SCORE_UMBRAL_COMPARACION` | (a calibrar) | Puntaje total para gatillar la ventana |
| `PESO_UNIDAD` / `PESO_RANGO` / `PESO_ESCALA` / `PESO_CORR` | (a calibrar) | Pesos de las reglas fuertes |
| `PESO_NOMBRE` / `PESO_PAREADO` / `PESO_DIF_CHICA` | (a calibrar) | Pesos de las reglas de apoyo |
| `FDR_METHOD` | Benjamini-Hochberg | Método de corrección por multiplicidad |

---

## Anexo B — Notas de implementación a verificar al codear

1. **Passing-Bablok:** verificar qué algoritmo de intervalo de confianza usa la librería elegida (hay más de una convención). Fijar la librería antes de implementar este nodo.
2. **Normalidad en Bland-Altman:** el test SIEMPRE va sobre la serie de diferencias, nunca sobre los datos crudos de cada método. Error común, dejarlo blindado.
3. **CCC vs Pearson:** no confundir en la implementación. Son fórmulas distintas con interpretación distinta.
4. **Post-hoc:** solo correr si el test global (ANOVA/Kruskal) resultó significativo, para no inflar comparaciones.
5. **Serie temporal:** si el perfilado detecta estructura temporal, este árbol no la cubre todavía. Marcar como rama futura, no forzar análisis transversal sobre datos temporales.

---

## Resumen del flujo completo

```
DATASET
  │
  ▼
PERFILADO (tipos + estructura)          ← corre siempre, define todo
  │
  ▼
¿cuántas columnas?
  │
  ├─ 1 → UNIVARIADO (según tipo; normalidad decide media vs mediana)
  │
  ├─ 2 → UNIVARIADO ×2
  │      + BIVARIADO (tabla de decisión: tipos → test)
  │         └─ si numérica×numérica → reglas duras
  │              └─ ¿score alto? → VENTANA confirmación
  │                   └─ confirmado → sub-árbol concordancia
  │                        (Bland-Altman param/no-param,
  │                         Passing-Bablok, CCC)
  │
  └─ 3+ → UNIVARIADO ×N
         + todos los pares (Rama B)
         + matriz correlación (método correcto por celda)
         + regresión múltiple / PCA / clustering
         + CORRECCIÓN POR MULTIPLICIDAD (obligatoria)

En CADA nodo con variante param/no-param:
  verificar supuesto PRIMERO → elegir rama DESPUÉS
  + emitir ADVERTENCIAS ACTIVAS cuando un análisis común sería inapropiado
```
