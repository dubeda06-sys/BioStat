# BioStat — Handoff / Dónde seguir

> **2026-08-23**. Leé esto primero.
> Se trabaja en **`develop`**. `master` quedó al día el 23 de agosto (venía 45
> commits atrás, y como `origin/HEAD` apunta ahí, quien clonaba aterrizaba en
> código viejo: así nació el clon abandonado). Al publicar, `master` se adelanta
> desde `develop` y se etiqueta: `git tag -n` lista las versiones.
> Versión actual: **v1.0.0**.
> Última puesta al día: **27 sep** — el paso 4 de la envoltura, **terminado**:
> los 78 análisis salen de `Resultado` y el mixin quedó en envoltorios finos.
> Antes, el asistente B «Validar un método», con EP15-A3 y la prueba Cusum de
> Passing-Bablok. El 26 sep, la auditoría completa y sus 42 arreglos
> (`docs/AUDITORIA-2026-09.md`, sección «Estado»).

## El `.exe` del Escritorio ya está al día

Recompilado el **27 sep a la tarde** desde `develop` (`c789807`), con el paso 4
entero: los 78 análisis en `Resultado`. El de la mañana (`466e298`) tenía las
diez primeras familias: Kaplan-Meier con la «supervivencia media» sin sentido,
Cox con `columns[3:]` y el falso «no convergió», el bootstrap percentil. El de
antes (`84255a9`, también del 27) tenía los 42 arreglos de la
auditoría, la familia de validación y el asistente «Validar un método», pero no
los cambios a propósito del paso 4 (t de una muestra contra μ₀, calculadoras
desde el diálogo, CMH con estrato, Youden interlaboratorio). El de antes de ese
(`34d106a`) tenía todos los errores del informe: ANOVA y
tablas 2×2 con las columnas equivocadas, ANCOVA, probit, y el Omnianálisis con
referencia. **La pantalla de carga dice qué build es**: `v1.0.0 · fecha · rama ·
commit`, dibujado en `assets/splash.png` por `build_exe.py` en cada compilación.
Ver `src/version.py`.

Hizo falta porque había **tres** BioStat en la máquina y ninguno se
identificaba: el del Escritorio, una copia del 1 de julio, y un build del 16 de
junio detrás de un acceso directo que apuntaba a otro clon del repo bajo
`source/repos/BioStat`. Con el del 1 de julio se validaron métodos durante dos
meses con los IC de los límites de acuerdo impresos mal (`1.96` en vez de
`t(n−1)`, 8,6 % más angostos a n=15).

Los dos viejos se borraron y el acceso directo quedó reapuntado al actual. **En
ese clon abandonado siguen `BioStat.bat` y `BioStat.vbs`**, que corren
`python main.py` sobre el código de junio: no son ejecutables, pero abren la
app igual.

**Después de tocar el core, recompilar:**

```bash
python -m pytest tests/ -q        # esperar 1470 verdes (27 sep)
python scripts/smoke_ui.py        # esperar 78/78, 0 bugs
python build_exe.py               # deja dist/BioStat.exe y lo copia al Escritorio
```

Qt sin pantalla: `QT_QPA_PLATFORM=offscreen`.

## 27 sep: paso 4, las dieciséis familias en `Resultado`

En el orden de los menús, un commit por familia (`git log --oneline 84255a9..HEAD`).
Las diez primeras:
resumen y normalidad con atípicos, correlación, regresión (lineal, múltiple,
logística, probit), medias, ANOVA (una y dos vías, ANCOVA, medidas repetidas),
no paramétricas, tablas de contingencia, concordancia (kappa, ponderado,
Cronbach), gráficos de comparación (mountain, Youden, polar, cascada) y curvas
ROC. Constructores en `src/resultado/constructores/`, un test por familia
(`tests/test_*_resultado.py`) contra scipy, statsmodels, pingouin o sklearn, y
todos pasan por el contrato de `test_bland_resultado.py::test_contrato`, que
recorre `CONSTRUCTORES` con la firma de `FIRMAS`.

**Una sola verdad con el Omnianálisis**: Tukey, la regla EP09 para elegir
regresión, el camino del χ² (Fisher o Monte Carlo con esperados < 5) y el árbol
de grupos (Levene → ANOVA+Tukey o Welch+Games-Howell) salen del mismo código.

**Cambian a propósito**, cada uno con su test que dice por qué:

- La t de una muestra prueba contra el μ₀ elegido (antes, siempre contra 0).
- Las calculadoras (Comparar 2 medias, 2 proporciones, 2 AUC) toman sus números
  del diálogo; antes leían celdas de la primera columna.
- El CMH pide exposición, evento y estrato como columnas crudas; antes partía la
  hoja entera en tablas 2×2.
- «Youden plot» es el interlaboratorio de MedCalc; el índice J pasó a la curva
  ROC, como gráfico de sensibilidad y especificidad según el umbral.
- La cascada es la de oncología (barras ordenadas), no una contable acumulada.
- El polar usa las columnas tildadas, no las 8 primeras.
- P25 y P75 salen igual en todos lados (cuartiles de Weibull).
- La logística rechaza con motivo la separación completa, en vez de dar un OR
  enorme. El OR de Fisher es el condicional (el de scipy), no el muestral.

**Las seis que siguieron el mismo día**, con lo que cambia a propósito:

- **Supervivencia** (`b401880`, contra lifelines). Kaplan-Meier ya no imprime
  una «supervivencia media» que era el promedio de los puntos de la curva: da
  la mediana y los tiempos al 25 % y 75 % con IC de Brookmeyer-Crowley; el IC
  de la curva es log-log. Log-rank acepta k grupos, da el HR por O/E y prueba
  riesgos proporcionales. Cox usa las covariables tildadas (antes,
  `columns[3:]` en silencio), la razón de verosimilitudes y Schoenfeld
  (Grambsch-Therneau, escala 1 − KM(t⁻) de R). **Defecto encontrado**: Cox
  avisaba «no convergió» en 19 de 20 ajustes sanos (BFGS da «precision loss»
  con gradiente ~1e-5) y dejaba pasar la separación como convergida; ahora
  mira el gradiente y detecta la separación por DE de la covariable.
- **Valores de referencia** (`2c49f35`). EP28 con Dixon (Reed 1971) y
  verificación de un intervalo publicado (20 sujetos, ≤ 2 afuera); su IC se
  rotula 90 % (`Valor.nivel_ic`). Por edad, centiles por regresión (Altman
  1993), cobertura simulada 5,6 %; por grupos, percentiles 2,5 y 97,5 de EP28
  (antes 5 y 95 lineales).
- **Tamaño de muestra y poder** (`d1c881d`, contra statsmodels, Fleiss y
  Hulley). Cinco calculadoras con curva de poder. La de correlación pide la r
  esperada: antes usaba la r de la hoja (poder post hoc).
- **Bootstrap** (`adb7eb5`, contra `scipy.stats.bootstrap`). Remuestreo
  vectorizado, IC BCa por defecto (percentil a elección), IC exacto por rangos
  de la mediana como control, Spearman a elección.
- **Machine learning** (`eba526f`, contra `cross_val_predict`). Desempeño fuera
  de muestra contra no tener modelo, AUC con DeLong, importancia por
  permutación (la de impureza premiaba al ruido continuo), observado contra
  predicho fuera de muestra.
- **Sueltos y pruebas diagnósticas** (contra statsmodels y a mano).
  Meta-análisis con τ², intervalo de predicción, Egger desde 10 estudios y
  funnel; mediciones seriales con trayectorias; la prueba diagnóstica recalcula
  VPP y VPN para la prevalencia cargada; las razones de verosimilitud dan la
  probabilidad post-test.

Con la última familia se borraron `_run_core`, los armadores de tablas del
mixin y más de cien imports muertos: `analysis_methods.py` pasó de ~2400 líneas a 590 de
envoltorios que leen el diálogo y llaman al constructor.

## 26 sep: auditoría completa, 42 hallazgos arreglados

Informe: `docs/AUDITORIA-2026-09.md` (fórmulas, árboles de decisión y
Omnianálisis, contra oráculos y contra CLSI EP28-A3c y EP09c leídos del PDF).
Arreglos en cinco commits sobre `develop`, cada uno con sus tests; la tabla de
estado está al principio del informe. Lo que alguien que toque el código tiene
que saber:

- **Concordancia en el Omnianálisis, orientada como EP09c (tabla 1).** X es el
  comparativo —la referencia, si se declaró— e Y el candidato; la diferencia es
  **Y − X** y el sesgo en niveles de decisión se evalúa en valores de X. Sin
  referencia, X es la primera en orden alfabético y el informe lo avisa.
- **Dos preguntas distintas sobre las diferencias.** La *variabilidad* (DE
  constante, CV constante o mixta; `core/bland_altman.variabilidad_diferencias`,
  EP09c §5.4) **elige** la escala del Bland-Altman y la recta (§6.2): Deming,
  Deming ponderado (`core/agreement.deming_ponderado`, apéndice B, IC jackknife
  K1) o Passing-Bablok. La *tendencia del sesgo* (pendiente de la diferencia) es
  de apoyo y no elige nada. Antes se usaba la segunda como si fuera la primera.
- **Rama C: una sola familia de Benjamini-Hochberg.** Cada bloque bivariado deja
  su p crudo en `_p`; `run_omnianalysis` corrige todos juntos y `_decidir`
  cierra cada bloque (veredicto, conclusión y post-hoc) con el p corregido. La
  matriz de correlación ya no calcula nada: es una vista de esos bloques.
- **Grupos.** Normales con varianzas distintas → ANOVA de Welch + Games-Howell.
  Dunn es Dunn de verdad (rangos del ranking conjunto, con empates), no
  Mann-Whitney de a pares. Enteros consecutivos 0..k o 1..k con repeticiones →
  códigos de categoría, no cantidad.
- **Tablas r×c ralas** → chi-cuadrado con p por permutación (9999, semilla fija).
- **Sin «significativo»** en el Omnianálisis: «Se detectó / No se detectó».
- **El catálogo tiene 47 ensayos** y el árbol dibujado coincide con el motor:
  `test_auditoria_omni.py::test_a14_el_camino_ejecutado_es_un_camino_del_arbol`.
- **Bland-Altman manual:** con referencia declarada la resta es método en prueba
  − referencia; opción nueva **escala** (auto / unidades / %).

> [!warning] λ de Deming: la convención es la de EP09c
> λ = var_error(X) / var_error(Y). La auditoría de agosto dio por buena la
> dirección de λ y era al revés (A13): `_deming_fit` usaba λ donde va δ = 1/λ.
> Con λ = 1, que es lo que usan la UI y el Omnianálisis, no cambiaba nada. La
> ficha del vault `Cerebro/Proyectos/BioStat/BioStat.md` quedó corregida el 27
> sep.

## 27 sep: el asistente B, «Validar un método»

Primer ítem de **Comparación de métodos**. Variable 1 = método en uso
(comparativo, X), Variable 2 = método en prueba (Y); sesgo = Y − X. Arma
`src/resultado/constructores/validacion.py` y corre, sin reescribir ninguna
lectura:

1. **Bland-Altman** con el comparativo como eje (Krouwer) y el CCC.
2. **La recta que corresponde** por EP09c §6.2 (`core/ep09.regla_ep09`, la misma
   función que ahora usa el Omnianálisis: una sola copia) y la otra para
   comparar.
3. **El sesgo en los niveles de decisión** (hasta tres en el diálogo; vacíos =
   cuartiles del comparativo) con su IC 95 %: jackknife con t(N−2) si la recta es
   Deming (apéndice K), bootstrap percentil con semilla fija si es
   Passing-Bablok (el jackknife no sirve para medianas). Cobertura simulada,
   94,5 a 97 %.
4. **La precisión por EP15-A3**, si se tildan corridas.
5. **Un veredicto** contra el sesgo permitido (en % del nivel o en unidades), con
   lógica de equivalencia: el IC entero adentro **cumple**, entero afuera **no
   cumple**, si cruza el límite **no concluyente**. Sin sesgo permitido no hay
   veredicto. Una curva detectada por la Cusum impide el «cumple», y una
   precisión que no verifica lo declarado lo vuelve «no cumple».

Cada análisis va debajo con su informe entero: `Resultado.partes`, que
`render_html` dibuja después de las referencias.

**Dos análisis nuevos para el core que pedía B:**

- **Cusum de linealidad** (`core/passing_bablok.cusum_linealidad`, Passing y
  Bablok 1983; pasos de NCSS y del paquete `mcr` de R). Entra como supuesto del
  Passing-Bablok del panel y como advertencia del Omnianálisis. Es algo liberal:
  con datos lineales rechaza 4 a 9 % al 5 % nominal (simulado, y el informe lo
  dice). Con √n en vez de √(n₋ + 1) no rechazaría nunca: la normalización
  publicada compensa que la recta se ajusta a los mismos datos.
- **Precisión EP15** (`core/ep15.py`, análisis «Precisión EP15»): una columna por
  corrida, ANOVA de un factor con n0 para corridas desbalanceadas, verificación
  contra lo declarado con el UVL (gl de s_WL por Satterthwaite con la ρ
  declarada, apéndice B) y, con valor asignado, el intervalo de verificación del
  sesgo (escenarios A a E). Probado contra la **tabla 10** y los **ejemplos 1A,
  3A y 4** de la norma **con sus dos fe de erratas** (oct 2015, may 2017, en
  clsi.org). Dos diferencias con lo impreso, documentadas en
  `tests/test_ep15.py`: la tabla dice s_WL = 2,40 donde sus propios MS dan
  2,387 (redondeo de la tabla: las otras tres columnas cierran), y en el 1A la
  norma lee gl = 12 de la tabla 15A; desde los datos, Satterthwaite da 11,6 → 12
  y el intervalo 139,6 a 145,4 sale exacto.

`Parametro(defecto=None)`: campo vacío = «no se declaró» (lo del fabricante, el
valor asignado, el sesgo permitido). `analysis_specs.ETIQUETAS` rotula las
variables de un análisis («Método en uso», «Método en prueba») y
`Multi(tildadas=False)` deja la lista de corridas vacía de entrada.

**Queda afuera, a propósito:** el error total (TE = |sesgo| + 2·s, estilo
Westgard) no entra al veredicto; EP15 dentro del asistente verifica precisión
pero no el sesgo contra un valor asignado (eso es el análisis «Precisión EP15»
suelto); el caso narrado del Omnianálisis todavía no cuenta la Cusum (sí la
traza y la advertencia).

## 26 sep: la familia de validación, entera en `Resultado`

Paso 3 de la propuesta, cerrado. Los seis análisis de comparación de métodos
salen de `src/resultado/constructores/comparacion.py` y el panel solo los
muestra: Bland-Altman (con el CCC), **Passing-Bablok**, **Deming**,
**imprecisión desde duplicados**, **ICC** y **Bland-Altman múltiple**.
`tests/test_validacion_resultado.py` compara cada número contra el core; el
contrato común (ficha, sin «significativo», ningún p impreso como cero) corre
sobre todo `CONSTRUCTORES`.

Cambió a propósito, y cada test lo dice en su nombre:

- **Passing-Bablok** decide por los intervalos, y un intervalo de pendiente más
  ancho que 0,5 **no concluye**. Se fue el «10 % de la media» del veredicto viejo
  (decisión 3). Informa además el sesgo en P25/P50/P75 del comparativo (EP09c
  §6.3), como el Omnianálisis.
- **Deming** elige ponderar según la variabilidad de las diferencias (EP09c
  §6.2) y acepta **λ** desde el diálogo (Parámetros) y la ponderación (Opciones).
  Con λ = 1 lo dice, y explica cómo sacarlo de los CV de EP05.
- **CV de duplicados**: los tres métodos de MedCalc (DE intrasujeto, raíz
  cuadrática media, logarítmico) con IC por χ² (Bland 2006), y la variabilidad
  decide cuál leer. El panel mostraba DE(d)/(√2·media) con la DE centrada, que no
  es ninguno de los tres. `core/agreement.cv_duplicados`; el viejo
  `cv_from_duplicates` queda por compatibilidad.
- **ICC** muestra el de acuerdo absoluto y el de consistencia, explica la
  diferencia con una t pareada y se lee por su IC con la escala de Koo y Li.

## 26 sep: arranca la envoltura `Resultado`

Propuesta aprobada: `docs/plans/2026-09-26-envoltura-resultado.md`. Hecho el
esqueleto en `src/resultado/` (sin Qt): `modelo` (Resultado, Entrada, Valor,
Metodo, Supuesto, Cita), `lenguaje`, `datos` y `render_html`.

- **`lenguaje.py` es la única copia** de `fmt_p`, `p_token`,
  `probabilidad_en_palabras`, `num`, `ic_texto` y `pendiente_concluyente`. El
  Omnianálisis las importa de ahí con sus nombres viejos (`_fmt_p`, `_p`, `_num`,
  `_ic`); `tests/test_resultado.py` exige que sean **el mismo objeto**.
- **`if resultado:` lanza `ResultadoComoBooleano`.** Se pregunta `.ok`.
- **El panel acepta las dos formas**: el dispatch puede devolver HTML (lo viejo)
  o un `Resultado`, que `_mostrar_resultado` renderiza y del que toma fórmula y
  figuras. Con más de una figura, `_mostrar_figuras` las **apila con su título**
  (igual que la pestaña Gráficos del Omnianálisis) y la ventana de informe se
  lleva el bloque entero.

### Bland-Altman: el primer análisis migrado

`src/resultado/constructores/comparacion.py::bland_altman`. El `_bland` del
panel quedó en una línea que lo llama; `CONSTRUCTORES` lista los migrados y
`tests/test_bland_resultado.py` les aplica el contrato a todos (ficha con
fórmula y cita, sin «significativo», ningún p como cero, lectura y matiz).

- **Mismos números.** Cada `Valor` se compara contra `bland_altman_analysis` en
  las 9 combinaciones límites × eje, con diferencias normales y sin ellas. Además
  se corrió el `_bland` viejo (sacado de git) contra el nuevo en 36 casos: los
  **642** números del informe viejo están en el nuevo.
- **Entra el CCC al panel manual**, con sus valores (ρc con IC, ρ, Cb, McBride),
  su paso y su gráfico descompuesto — el mismo `ccc_decomposition_figure` del
  Omnianálisis. Si no se puede calcular (una columna constante), se avisa y el
  Bland-Altman sigue.
- **Pasos auditables**: normalidad de las diferencias → qué límites; método de
  referencia → qué eje; sesgo proporcional (por el IC de la pendiente, misma
  regla que el Omnianálisis); CCC. Con referencia declarada, si la pendiente
  contra el promedio y contra la referencia no concluyen lo mismo, lo dice.
- **Fórmula y 8 referencias** en `src/resultado/citas.py`, en el recuadro de
  fórmula y en el informe guardado (antes `_bland` no escribía fórmula).

> [!bug] El CCC contradecía al sesgo del mismo informe (también en el Omnianálisis)
> Con ρ y Cb ≥ 0,95, `_donde_falla_ccc` decía «ni corrimiento apreciable ni
> dispersión». Un método que lee 8 % alto sobre un rango de 20 a 200 da
> Cb = 0,98: Cb mide el corrimiento **frente a la dispersión de la muestra**, y
> con un rango amplio un 8 % casi no lo mueve. El paso negaba el sesgo que la
> tabla mostraba arriba. Ahora dice que los componentes pesan poco frente a esa
> dispersión y que el tamaño del sesgo lo dan el sesgo y los límites.
> `test_el_paso_del_ccc_no_niega_el_sesgo_que_muestra_la_tabla`.

**Sigue:** Passing-Bablok (con `_regresion_concluyente` en vez del 10 % de la
media), Deming, CV de duplicados, ICC y Bland-Altman múltiple.

## 26 sep: los análisis pareados del panel manual desalineaban las filas

> [!bug] Informes del panel manual con celdas vacías: pueden estar mal
> El panel hacía `data[c1].dropna()` y `data[c2].dropna()` **por separado** y
> después cortaba las dos al mismo largo. Con una sola celda vacía, desde esa
> fila cada valor se comparaba con el del paciente siguiente. Un Bland-Altman
> de 20 pares con un hueco daba LoA de **−92 a 90** donde corresponden −2,4 a
> 2,5, sin aviso.
>
> Afectaba a **22 análisis**: t pareado, Wilcoxon, sign test, Bland-Altman,
> Passing-Bablok, Deming, CV de duplicados, ICC, kappa ponderado, regresión
> lineal, bootstrap de correlación y de regresión, tamaño muestral por
> correlación, ROC, Youden, probit, Kaplan-Meier, Cox, meta-análisis,
> chi-cuadrado, Friedman e intervalos por edad. Con la hoja completa, los
> números eran correctos. El Omnianálisis nunca tuvo el problema.
>
> Ahora todos pasan por `_filas_completas(*cols)` y el informe dice cuántas
> filas incompletas quedaron afuera (las vacías del todo, que son el final de la
> planilla, no cuentan). `tests/test_pares_alineados.py` corre cada análisis con
> huecos y sin ellos y exige **el mismo informe, texto por texto**.
>
> **Cualquier análisis pareado nuevo usa `_filas_completas`.** La envoltura
> `Resultado` (`docs/plans/2026-09-26-envoltura-resultado.md`) lo va a absorber
> en `src/resultado/datos.py`.

## Los gráficos se editan, y el CCC dejó de repetir al Passing-Bablok

**`src/ui/grafico_editable.py`** envuelve cualquier `Figure` y le agrega la
barra de matplotlib (zoom, desplazamiento, guardar, y el editor de curvas que
vive detrás del ícono de la llave) más un diálogo con lo que esa barra no
cubre: título y rótulos, tamaño y familia de letra, tamaño/color/opacidad de
los puntos, grilla, leyenda con posición, tamaño en pulgadas, exportación de 72
a 600 ppp y tendencias lineal/cuadrática/cúbica con ecuación y R².

Conectado en los tres lugares que muestran figuras: `analysis_panel._show_fig`,
`graphs_panel._plot` y `omni_panel._render_plots`. El widget expone `.figure` y
`.draw()`, así que `report_window` y el guardado de la pestaña de gráficos lo
siguen tratando como al canvas.

El núcleo son funciones puras sobre `Figure`, sin Qt, para poder probarlas sin
levantar ventana. **Si tocás ese módulo, mirá primero los tests**: cuatro de
ellos guardan propiedades que no son obvias — que escalar la fuente no se
componga, que la tendencia no alimente el ajuste siguiente, que las rectas de
referencia no cuenten como datos, y que el control se apague donde no hay nube.

Defecto encontrado ahí: **`ax.grid(False, alpha=0.3)` ENCIENDE la grilla.**
matplotlib avisa que le pasaron propiedades de línea junto al `False` y hace lo
contrario de lo pedido. Hay que separar los dos casos.

**El CCC descompuesto** tenía a la izquierda un diagrama de dispersión con la
identidad y una recta inclinada — o sea el mismo gráfico de regresión de
comparación que está dos pestañas antes. Ahora ubica el par (Cb, ρ) en el plano
precisión × veracidad, con las hipérbolas de igual ρc y las zonas de McBride.
El panel derecho pasó de una tira fina a tres rieles que llegan a 1, para que
se lea cuánto falta y no solo cuánto hay.

## Auditoría numérica del 23 ago: 12 defectos de cálculo

Se verificaron las ~100 funciones públicas de `src/core` contra oráculos
independientes (scipy, statsmodels, lifelines, sklearn, pingouin) y contra
ejemplos publicados (NIST/SEMATECH, CLSI EP12 y EP28, Passing & Bablok 1983).
Informe completo con tablas y reproducciones: `docs/AUDITORIA-2026-08.md`.

**Lo que cambiaba un resultado clínico:**

| dónde | qué pasaba |
|---|---|
| `passing_bablok` | el IC era el percentil empírico de las pendientes: cubría el **100 %** y detectaba un sesgo proporcional real del 10 % en **0 de 900** corridas |
| `passing_bablok` | faltaba el desplazamiento K: era Theil-Sen. `b(x,y)·b(y,x)` daba 0.04 en vez de 1 |
| `cox_regression` | `hes_inv` en vez de `hess_inv`: el `hasattr` daba siempre False y **todos** los errores estándar valían 0.1. Además el conjunto de riesgo invertido y el AIC con el signo cambiado |
| `roc` | la curva no arrancaba en (0,0): el AUC subestimaba hasta **−0.11** con scores empatados |
| `cmh` | varianza del log(OR) no publicada: con **p = 0.00036** el IC era **(0.11, 243.9)** |
| `outliers` | ESD con doble resta en λ y sin la regla de Rosner: **1 outlier** donde el NIST publica **3** |
| `sample_size` | z donde va t: pedías poder 0.80 y con efecto grande te daba **n=2**, cuyo poder real es **0.18**. Y `power_analysis` usaba z también, así que confirmaba su propio error |
| `agreement` | `weighted_kappa` dividía dos veces por n y devolvía **−55**, con κ acotado a [−1,1]. Estaba en la UI |
| `outliers` | Grubbs aceptaba `side` y lo ignoraba; el p llegaba a **3.58** |
| `diagnostic_tests` | `relative_risk` rechazaba tablas calculables; IC de ancho cero con a=0; NNT infinito cuando la exposición daña |
| `diagnostic_tests` | sensibilidad y especificidad **sin ningún IC**, que CLSI EP12 exige |
| `reference` | ningún aviso del mínimo de **120** sujetos de CLSI EP28-A3c |

**Robustez.** Barrido de 3.990 llamadas con entradas hostiles. El core filtraba
con `~np.isnan(x)`, que **deja pasar ±inf**: 44 sitios en 13 archivos, migrados a
`isfinite`. `guards.py` ya lo hacía bien y hasta lo explicaba en un comentario,
pero nunca se había propagado. Ocho funciones devolvían NaN mudo con datos
constantes; ahora rechazan con motivo.

**Ojo con esto:** endurecer `pearson_r` *causó* tres crashes nuevos en el
Omnianálisis, que hacía `pearson_r(a, b)["r"]` sin mirar. Mover una falla de
"NaN silencioso" a "excepción" no la arregla. Cada vez que una función del core
pase a devolver `{"error": ...}`, hay que revisar sus llamadores — `_ok()` en
`omni_analyzer`, `_sin_resultado()` en la UI.

**Lo que se verificó correcto** (no se tocó): Bland-Altman y sus LoA, CCC de Lin
y su IC, Deming contra `scipy.odr`, kappa simple, CV de duplicados,
Kaplan-Meier y log-rank contra lifelines, regresión múltiple contra OLS,
meta-análisis, y el ruteo del Omnianálisis (41 ensayos = 41, sin huérfanos;
0 contradicciones entre el texto narrado y sus números en 10 escenarios).

## El Omnianálisis ahora se puede auditar

El motor decide bien pero no rendía cuentas: se veía el resultado, no la
decisión. Ahora sí.

- **Catálogo de ensayos** (`src/analysis/omni_catalogo.py`): los **47** ensayos
  que el motor puede correr, cada uno con su gatillo, su explicación y su norma.
- **Marcas en el motor.** `_marcar` / `_descartar` en `omni_analyzer` anotan
  **en el punto donde el ensayo ocurre**. No se reconstruye desde el texto de la
  traza: la traza es prosa, un id no.
- **Auditoría** (`src/analysis/omni_auditoria.py`): tres estados, y la
  distinción es todo el punto — **ejecutado**; **descartado** (el motor lo
  evaluó y eligió la otra rama, con motivo); **no aplica** (los datos nunca
  abrieron esa rama). "No corrí Fisher" no se audita; "no corrí Fisher porque la
  esperada mínima fue 12,4" sí.
- **Árbol dibujado** (`src/analysis/omni_arbol.py`): una figura por etapa, con
  el camino recorrido en verde. Layout **a mano, no auto-ubicado**: un grafo
  automático mueve los nodos entre corridas y deja de servir para comparar.
- **Panel en 5 pestañas**: Resumen (castellano llano), Árbol de decisión,
  Auditoría (tabla filtrable + exportar CSV), Informe, Gráficos.
- **Vista caso por caso** (`src/analysis/omni_caso.py`): el árbol general dice
  *qué corrió*; esta dice **qué dio y por qué se decidió así**, sobre columnas
  concretas. Cada paso lleva la pregunta en castellano, el número, la
  consecuencia, y **qué habría pasado si el número daba al revés** — sin eso la
  decisión parece un veredicto en vez de una regla, y una regla es lo único
  auditable. Cierra con la conclusión y con **qué NO se puede concluir**.
  Selector de vista en la pestaña Árbol de decisión.

> [!warning] Dos trampas de interpretación que la vista por caso desactiva
> **1. Un IC que incluye el 1 no prueba que no haya sesgo.** El IC de pendiente
> de Passing-Bablok puede ir de −3 a 5: incluye el 1, así que la regla mecánica
> dice "sin sesgo proporcional". Es falso — con ese ancho no puede descartar
> nada. `_regresion_concluyente()` marca el paso como **no concluyente** cuando
> el IC es más ancho que 0,5, y lo dice con todas las letras.
>
> **2. Dos pasos pueden contradecirse.** La tendencia del sesgo detecta desvío
> proporcional y la recta no, o al revés: miran lo mismo por caminos distintos.
> Una contradicción sin explicar destruye la confianza del lector, así que el
> caso la señala y explica por qué **ninguna manda**: la tendencia se deja
> engañar cuando un método es más impreciso que el otro, y la recta depende del
> λ que se le supone. (Antes decía «vale la del paso 1», sin base: A16.)
>
> Los textos evitan la palabra **«significativo»** (se lee como «importante») y
> traducen el p a frecuencia: *"aparecería 59 de cada 100 veces solo por azar"*.
> `tests/test_omni_caso.py` lo verifica.

> [!warning] Dos números que se confunden
> **Tipos de ensayo** (47 en el catálogo) no es **ejecuciones**: el univariado
> corre una vez por columna y el bivariado una por par. Con 10 columnas son
> ~106 ejecuciones de ~24 tipos. La pestaña Auditoría informa los dos.

> [!info] El catálogo se valida contra el motor
> `tests/test_omni_catalogo.py` lee `omni_analyzer.py` y compara los ids
> `_marcar(...)` contra el catálogo **en las dos direcciones**. Sin eso, agregar
> un ensayo al motor lo deja invisible en la auditoría, y sacarlo lo deja
> figurando como "no aplica" para siempre. Ninguna de las dos tira excepción.
> `tests/test_omni_arbol.py` exige además que los 47 estén dibujados.

También: `p` redondeado a 4 decimales salía `p=0.0`, que se lee como *p
exactamente cero*. `_fmt_p` / `_p` lo informan como `p<0.0001`.

## Bland-Altman: las tres variantes, a elección

El core ya calculaba las tres. Lo que faltaba era **poder elegir**: el panel
llamaba `bland_altman_analysis(d1, d2)` sin `reference` y mostraba solo los LoA
paramétricos, aunque los no paramétricos estuvieran calculados al lado.

- **`analysis_specs.OPCIONES`** — tabla declarativa de decisiones *de método*
  (distintas de las variables). Bland-Altman expone `limites`
  (`auto` / `parametrico` / `no_parametrico`) y `referencia`
  (`promedio` / `x` / `y`). `DialogoAnalisis` arma los selectores leyendo esa
  tabla; el valor viaja por `currentData()`, no por el texto.
- **`seleccion()` ahora devuelve 5 claves**, con `opciones`. `_aplicar_eleccion`
  la vuelca en `panel.opciones_metodo`, que el dispatch pasa al análisis.
- **El informe dice en qué se apoyó**: Shapiro-Wilk sobre las diferencias, con
  su p, y si el modo salió del automático o se forzó a mano. Forzar paramétrico
  sobre diferencias no normales avisa en vez de obedecer callado.

> [!warning] Por qué el eje X no es cosmético — Krouwer
> Con un método de **referencia** (o un valor asignado: consenso, material de
> control), graficar y regresar contra el promedio mete la referencia en los dos
> ejes y **atenúa el sesgo proporcional**: se ve menos desvío del que hay.
> Krouwer JS, 2008, *Stat Med* 27:778-780; recogido en CLSI EP09.
>
> `tests/test_bland_variantes.py::test_el_promedio_atenua_el_sesgo_proporcional`
> lo deja en un assert: sobre un método que lee 8 % alto, la pendiente contra el
> promedio sale **más chica en magnitud** que contra la referencia. Ese
> achicamiento es el que hace parecer un método mejor calibrado de lo que está.
>
> Cuando hay referencia se informan **las dos pendientes**, para poder
> contrastarlas; si se mostrara una sola, la atenuación sería invisible.

> [!bug] Veredicto inventado, eliminado
> `_bland` dictaminaba «sesgo < 5 % → **los métodos son concordantes**». Ese 5 %
> no salía de ninguna norma. Ahora informa el margen —dónde cae el 95 % de las
> diferencias— y dice explícitamente que el límite tolerable lo fija el
> requisito de calidad del analito, no el programa.

## El Omnianálisis también pregunta por la referencia

Esta era la deuda del bloque anterior, y era una incoherencia visible: el
análisis manual dejaba elegir Krouwer, pero el Omnianálisis corría siempre el
clásico contra el promedio. El mismo par de columnas daba dos números distintos
según por dónde se entrara, y nada lo explicaba.

- **La ventana de confirmación de pares** (`ComparisonConfirmDialog`) ahora
  pregunta, por cada par confirmado, si alguna de las dos columnas es el método
  de referencia. Es contexto humano: el motor no lo puede deducir.
- **`referencias()` devuelve `{par ordenado → nombre de columna}`**, no
  `"x"`/`"y"`. El par viaja ordenado alfabéticamente hacia el analizador, así
  que guardar la posición dejaría la referencia colgada de la columna
  equivocada cuando el orden del DataFrame no coincide con el alfabético.
  `tests/test_omni_referencia.py::test_la_referencia_no_se_muda_si_el_par_llega_al_reves`
  lo fija.
- **Ensayo nuevo en el catálogo: `ba_eje_referencia`** (41 en total). Sin
  referencia declarada queda **descartado con motivo**, no ausente — que es
  toda la diferencia entre «no correspondía» y «me lo olvidé».

> [!warning] El promedio distorsiona en las **dos** direcciones
> La lectura habitual de Krouwer es que el promedio *atenúa* el sesgo
> proporcional. Es cierto, pero el efecto es de centésimas y casi nunca alcanza
> para cambiar una conclusión.
>
> El artefacto grande va al revés. Con `ref` sin error y `prueba = ref + ε`:
> `diff = ε` y `promedio = ref + ε/2`, así que el ruido del método en prueba
> queda **de los dos lados de la cuenta** y la regresión contra el promedio
> **inventa** una pendiente que contra la referencia no existe. Una búsqueda
> sobre 4 800 combinaciones (`n`, ruido, semilla) encontró **1 109** casos de
> pendiente espuria contra **34** de atenuación que cambiara la conclusión.
>
> Por eso el aviso no se dispara por magnitud sino cuando **los dos ejes no
> concluyen lo mismo** (uno detecta sesgo proporcional y el otro no). Avisar por
> atenuación sería avisar siempre, y una advertencia que aparece siempre enseña
> a saltearla.

> [!bug] `linregress` desempaquetado por posición — bug de cálculo, corregido
> En `concordance_analysis` estaba así:
>
> ```python
> slope, intercept, _, _, p_slope = stats.linregress(means, diffs)
> ```
>
> `linregress` devuelve `(slope, intercept, rvalue, pvalue, stderr)`. Ese
> desempaquetado guardaba el **error estándar** en `p_slope`. O sea que
> `proporcional = p_slope < 0.05` venía comparando un error estándar contra un
> nivel de significancia.
>
> No era cosmético. De ahí salen: la estructura de la diferencia
> (proporcional/constante), la elección entre **Deming y Passing-Bablok**
> (`resid_homoced = not proporcional`), la traza, el detalle de auditoría y el
> paso 1 del caso. En el juego de datos de prueba el stderr daba 0,0860 y el p
> real 0,0405 — a lados opuestos de 0,05, o sea conclusión invertida.
>
> **Los informes de concordancia del Omnianálisis anteriores a este arreglo
> pueden haber elegido la regresión equivocada.** El análisis manual no estaba
> afectado. Fijado en `test_el_p_de_la_estructura_es_un_p_y_no_el_error_estandar`.
>
> Efecto colateral: dos tests de `test_omni_caso.py` pasaban solo por el bug —
> el motor entraba en la rama de Passing-Bablok y producía un IC ancho. Ahora
> tienen fixture propio (`caso_rango_angosto`: 12 pares entre 90 y 110), que es
> un defecto de diseño real de EP09 y produce la condición de verdad.

> [!note] La estructura de la diferencia también cambió de eje
> Con referencia declarada, la regresión del nodo «estructura» va contra la
> referencia, no contra el promedio. Dejarla contra el promedio hacía que el
> informe **se contradijera consigo mismo**: el paso 1 afirmaba justo el desvío
> que el nodo del eje X señalaba como artefacto del promedio, las dos cosas con
> el mismo aplomo. En `supuestos` las claves ahora son `eje_estructura` y
> `pendiente_estructura` (antes `pendiente_diff_mean`, nombre que mentía en
> cuanto había una referencia).

## El CCC de Lin, dibujado

`ccc_decomposition_figure` en `src/analysis/omni_plots.py`. Entra en la pestaña
**Gráficos** del Omnianálisis junto a Bland-Altman y la regresión. La
descomposición ya se informaba como texto; lo que faltaba era verla.

Dos paneles porque son dos preguntas:

- **«Lo que se ve»** — identidad (y = x) contra el **eje mayor reducido**: la
  recta de pendiente σ_y/σ_x que pasa por las medias. Sus dos desvíos respecto
  de la identidad —corrimiento y cambio de escala— son exactamente los
  ingredientes de Cb.
- **«Cómo se reparte»** — barra apilada con el reparto **exacto**:

  ```
  1 − ρc = (1 − ρ) + ρ(1 − Cb)
  ```

  Lo que falta para el acuerdo perfecto se corta en un pedazo de dispersión y
  uno de sesgo, sin residuo. El IC del CCC va como barra de error.

> [!warning] Dos formas de que este gráfico mienta, tapadas a propósito
> **1. Con ρ ≤ 0 los pedazos salen negativos** y la barra se dibujaría hacia
> atrás. Se escribe el motivo en el panel en vez de dibujar un reparto falso.
>
> **2. La recta ámbar se inclina por el cociente de dispersiones**, no solo por
> descalibración: con ruido grande se inclina sola. Un pie de figura que dijera
> «ámbar lejos de la gris = mal calibrado» sería falso justo en el caso de
> imprecisión pura, que es uno de los dos que el gráfico existe para
> distinguir. El texto afirma solo lo que Cb mide.
> `test_el_texto_no_afirma_descalibracion_por_la_inclinacion` lo fija.

`_plot` se arma **antes** de que el CCC exista, así que se completa después con
`ccc` / `ccc_rho` / `ccc_cb` / `ccc_ic95`. No se movió el bloque: los datos de
Bland-Altman de `_plot` dependen de decisiones anteriores, y reordenarlas por un
gráfico sería al revés.

**Resuelto el 26 sep:** entra también en el panel de análisis manual, debajo
del gráfico de diferencias (ver *Bland-Altman: el primer análisis migrado*).

## Lo que entró el 22 de agosto

- **Levey-Jennings y Westgard: eliminados.** Ver Deudas.
- **Menús por familia estadística, estilo MedCalc.** 76 análisis en 15 submenús
  bajo `Estadísticas`; más `Gráficos`, `Pruebas diagnósticas`,
  `Control de Calidad`, `Herramientas`, `Ver` (Ctrl+1..5). Tabla en `src/ui/menus.py`,
  verificada en las dos direcciones por `tests/test_menus.py`: el menú elige por
  texto (`findText`), y **un acento de diferencia deja la entrada muerta en
  silencio**.
- **Diálogo por análisis + informes en ventana propia.** `src/ui/dialogs.py`
  (ficha de variables en `src/ui/analysis_specs.py`) y `src/ui/report_window.py`
  (menú `Ventana`). Los informes se acumulan. El panel Análisis con su combo
  sigue existiendo.
- **Vista previa con mini gráfico** al elegir análisis: miniatura en el diálogo y
  en el tooltip del menú. 21 familias en `src/ui/previews.py`, datos sintéticos de
  semilla fija, cacheadas en PNG temporal (los tooltips de Qt piden ruta, no
  imagen incrustada). `tests/test_previews.py` exige que los 76 caigan en una
  familia con dibujo.
- **Tema `Clinico Clasico`** (`src/ui/styles.py`): gris de sistema, bordes 1 px,
  tipografía chica. Hoja de datos con letras de columna ("A  EBV_A"); doble clic
  en el encabezado renombra la variable.
- **PyQt6 mataba la app si una excepción salía de un slot** — cerraba de golpe,
  sin diálogo. `src/utils/errores.py` instala `sys.excepthook` propio (PyQt solo
  aborta con el de fábrica). **No reemplaza a `src/core/guards.py`**: es el último
  colchón, el contrato sigue siendo del core.
- **Ventana de carga con barra de progreso** (`src/utils/splash.py`,
  `assets/splash.png`, `scripts/make_splash.py`). Cubre el arranque de Python
  (~6 s); los ~10 s previos son descompresión del onefile: manda el bootloader, no
  corre Python.
- **Frases que rotan en la espera** (`src/utils/frases.py`): 34 líneas entre
  ingenio estadístico y oficio de laboratorio. Splash 520×300 → **700×330** para
  que entren; barra de 14 a 12 bloques. Justo después de cada hito se muestra
  **0,9 s el nombre de la etapa** y recién ahí entran las frases: si el arranque
  se cuelga, la etapa es la única pista de dónde quedó, y taparla con una
  humorada sería cambiar diagnóstico por decoración.

> [!warning] Las frases solo se ven ~6 s, no los ~16 s
> Durante la descompresión el bootloader escribe **él** en la línea de estado
> (el nombre del archivo que extrae) y Python todavía no corre: ahí no se puede
> dibujar nada. Rotando cada 1,6 s entran unas cuatro frases. Si se quisiera
> cubrir los 16 s enteros habría que pasar a `onedir`.
>
> **Verificado con foto** (23 ago): 40 cuadros del splash durante el arranque,
> con `PrintWindow` sobre su propio `hWnd`. Los ~29 primeros son el bootloader;
> del 30 en adelante, barra + porcentaje + frases rotando, acentos correctos.
> La clase de ventana **no** sirve como verificación: un splash roto sigue
> siendo `TkTopLevel`.

> [!todo] La barra se planta en 55 % casi toda la espera
> `main.py` marca el hito 0,55 y después importa `src.app`, que es **una sola
> sentencia** y el tramo más largo. Sin nada medible en el medio, la barra llega
> a 55 % y se queda. Es honesto —no promete avance que no ocurrió— y las frases
> rotando evitan que parezca colgada. Para que acompañe de verdad habría que
> partir esa importación en etapas con hitos intermedios.

> [!info] La ficha de variables se valida sola
> `analysis_specs.VARIABLES` salió de leer el `dispatch` de `AnalysisPanel._run`.
> `tests/test_analysis_specs.py` lo relee y compara. Sin eso, cambiar los
> argumentos de un análisis deja al diálogo pidiendo variables que la rutina
> ignora, y el informe sale sobre otra cosa **sin avisar**.

> [!bug] Trampas encontradas, por si vuelven
> `Splash(..., text_font='Segoe UI')` rompe el splash entero: PyInstaller pega la
> fuente en el script Tcl sin comillas, el espacio parte el comando. Sin error
> visible: queda una ventana Tk vacía de 216×239. Mirar la clase de ventana **no
> alcanza** — `TkTopLevel` existe igual estando rota; hay que fotografiarla.
>
> `biostat.spec` es la receta real (`build_exe.py` compila desde el spec). Antes
> apuntaba a una ruta muerta de otra máquina.
>
> `QScrollArea.setWidget` toma la propiedad y **destruye el widget anterior**:
> poner un gráfico borraba el cartel y el `_clear` siguiente reventaba con
> *wrapped C/C++ object of type QLabel has been deleted*. Los tres paneles con
> gráfico usan `takeWidget` primero.

## Correcciones de cálculo ya verificadas

Del 13 de agosto, verificado contra MedCalc 23.6.5 con datos reales de un panel
CAP de EBV (n=15). (El encabezado llevaba el hash de `develop`: quedaba viejo en
cada commit, incluido el que lo actualizaba. Para el estado, `git log`.)

- **IC de los LoA con el multiplicador correcto.** La varianza ya estaba bien
  (`var(LoA) = s²(1/n + z²/(2(n−1)))`); fallaba el multiplicador: `t(n−1)`, no
  `1,96`. Los cuatro informes de MedCalc se reproducen exactos.
- **CCC arreglado.** Mezclaba momentos muestrales (`ddof=1`) con `(m₁−m₂)²`, que
  no se escala, y **rompía su identidad `ρc = ρ·Cb`**. Con momentos poblacionales
  se cumple exacto.
- **CCC descompuesto en ρ (precisión) × Cb (veracidad)**, con IC y escala de
  McBride.
- **Eje X de referencia en Bland-Altman** (`reference="x"/"y"`, Krouwer 2008 /
  CLSI EP09): con método de referencia, las diferencias van contra la referencia,
  no contra el promedio.
- **LoA no paramétricos** + Shapiro-Wilk sobre las diferencias.
- **`src/core/guards.py`, contrato de robustez**: nunca crashear por los datos,
  nunca devolver un no-finito sin nota, al rechazar decir por qué. Auditoría: de
  CRASH=2 / BASURA=16 / NONE=26 a **CRASH=0, NONE=0, RECHAZO=32 con motivo**.
  Causa raíz: el core filtraba con `np.isnan` en 14 módulos y con `np.isfinite` en
  ninguno; los infinitos contaminaban medias, varianzas e intervalos.

> [!warning] Cambio de contrato que rompe consumidores
> Las seis funciones de comparación de métodos devuelven `{"error": motivo}`, no
> `None`. **Un dict de rechazo es *truthy***: un `if res:` lo deja pasar y revienta
> al indexar. Usá `_ok()` / `_sin_resultado()`. Los 36 consumidores ya están
> actualizados; el código nuevo tiene que respetarlo.

## Hacia dónde va: «MedCalc pero guiado»

Decidido el 21 de agosto. Tres definiciones que acotan el resto:

1. **Identidad.** No un clon de catálogo: misma amplitud que MedCalc pero que
   acompañe — elige la prueba según los datos, avisa cuando no se cumplen los
   supuestos, explica en castellano. **El diferencial es el criterio, no la
   cantidad de rutinas.**
2. **Público.** Trabajo diario **y** formación. Cada resultado, una lección
   auditable: qué prueba, por qué esa, fórmula, norma citada, interpretación.
3. **Primer ciclo: validación de métodos, a fondo.** EP09, veracidad,
   Bland-Altman, Passing-Bablok, Deming, CCC, repetibilidad (EP15). Pocas rutinas,
   impecables: ahí el core ya está corregido y verificado. (El QC diario
   —Westgard— se sacó el 22 de agosto; ver Deudas.)

### Arquitectura (A hecha el 26 sep para la familia de validación; B, el 27)

**A — Envoltura `Resultado` (sustrato).** El core devuelve lo suyo; encima, un
objeto con **valores, método, supuestos verificados, fórmula, cita e
interpretación redactada**. La UI y el informe lo consumen; nadie arma texto a
mano. Beneficio lateral: hoy **`src/ui/analysis_methods.py` tiene 2329 líneas**
porque cada análisis arma su HTML a mano, unas 40 ramas escritas de a una. Con la
envoltura hay **un solo renderizador**. La capa de guía y el arreglo del archivo
grande son la misma obra.

**B — Asistente «Validar un método».** Corre Bland-Altman + Passing-Bablok +
Deming + CCC + repetibilidad juntos, chequea supuestos, emite un veredicto único
con su norma. Así se trabaja: nadie corre un Bland-Altman suelto, valida un
método.

**Orden: A y después B.** Arrancar por B deja al asistente escribiendo su propio
texto: dos verdades. Así se hizo: B no escribe ninguna lectura propia salvo el
veredicto, y cada análisis que corre va debajo con su informe.

El registro de supuestos y citas **no es proyecto aparte**: es el campo
`supuestos` de la envoltura, alimentado por una tabla declarativa.

### Las citas ya existen, no hay que investigarlas

`docs/referencia-medcalc/` tiene las fórmulas de MedCalc **con la URL del manual
de donde salió cada una** — comparación de métodos, concordancia, control de
calidad. Ver su `LEEME.md`.

## Deudas conocidas

1. **`src/ui/analysis_methods.py`, cerrada el 27 sep.** Todo sale de
   `Resultado`; el mixin son envoltorios que leen el diálogo. El paso 5 del plan
   (borrarlo y que el dispatch llame a los constructores) es opcional: ya no
   hay lógica ahí que pueda divergir.
2. **Control de calidad, eliminado entero el 27 sep.** Levey-Jennings y
   Westgard se habían sacado el 22 ago (vivían en el panel, sin core ni tests).
   Lo que quedaba —**Estadísticas** y **Tendencias**, también sin core ni
   tests— se fue el 27 sep por decisión del usuario, con la pestaña, el menú y
   el `src/core/qc/` vacío. Las pestañas pasaron a ser cuatro y la navegación
   va por panel, no por índice (`tests/test_menus.py`). Si el QC vuelve, entra
   por el core con tests contra un caso publicado, no dentro de un panel.
3. **Asistente B, hecho el 27 sep.** Lo que podría seguir: error total contra
   TEa como criterio alternativo; el sesgo de EP15 contra valor asignado dentro
   del asistente; que el caso narrado del Omnianálisis cuente la Cusum. Y
   KaizenHub tiene su propio EP15 (`stats-engine/core/ep15_anova.py`) con dos
   diferencias con la norma: el UVL no corrige por el número de muestras y los
   gl de s_WL salen de lo observado, no de la ρ declarada.
4. Omnianálisis, de la auditoría del 26 sep: el pre-test de normalidad por
   grupo manda ~15 % de los grupos normales heterocedásticos a Kruskal-Wallis
   (falsos positivos 7,7 % en vez de 5 %); el IC jackknife del intercepto de
   Deming ponderado cubre ~91 %. Ver «Estado» en el informe.
5. Omnianálisis (de julio, vigentes): calibrar los pesos del score de comparación
   con datos reales; `PESO_UNIDAD` y `PESO_PAREADO` sin cablear; series temporales
   detectadas pero no analizadas. **El score no se marca ensayo por ensayo**: la
   auditoría dice cuántos pares se puntuaron, no el puntaje de cada uno.

## Cómo correr

```bash
python main.py                                   # la app
python -m pytest tests/ -q                       # 1470 verdes (27 sep); el número crece
python scripts/smoke_ui.py                       # smoke de UI, 78/78
python build_exe.py                              # dist/BioStat.exe + copia al Escritorio
```

> [!caution] Nunca uses `sed` sobre archivos de este repo
> Corrompe los multibyte (μ₀ √ d̄) y hace crashear Qt. Editá con herramientas que
> respeten UTF-8, o con E/S de Python en UTF-8 explícito.

## Ramas

| Rama | Estado |
|---|---|
| `develop` | **fuente de verdad** |
| `master` | al día con `develop` desde el 23 ago (v1.0.0). Se adelanta solo al publicar, así que entre versiones queda atrás: `origin/HEAD` apunta acá, por eso igual conviene `git clone -b develop` |
| `feat/medcalc-informed-agreement` | fusionada, borrable |
| `fix/correctness-and-refactor`, `optimización-de-código-d7fdb` | viejas |

## Referencias

- Fórmulas y citas: `docs/referencia-medcalc/`
- Spec del Omnianálisis: `docs/omnianalisis_spec.md` · plan: `docs/omnianalisis_plan.md`
- Repo: https://github.com/dubeda06-sys/BioStat
