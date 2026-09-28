# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Versionado [semántico](https://semver.org/lang/es/).

> [!warning] Todo build anterior a **1.1.0** puede producir números equivocados
> La auditoría del 26 de septiembre de 2026 encontró 42 defectos más en la
> 1.0.0; el peor desalineaba los pares con una sola celda vacía. Ver la
> entrada 1.1.0 y `docs/AUDITORIA-2026-09.md`.
>
> **Anteriores a 1.0.0:**
> La auditoría del 23 de agosto de 2026 encontró 12 defectos de cálculo, varios
> capaces de cambiar una decisión clínica. Si validaste un método con una
> versión anterior usando **Passing-Bablok**, **Cox**, **tamaño muestral** o
> **AUC con puntajes empatados**, conviene rehacer ese análisis. El detalle
> está en `docs/AUDITORIA-2026-08.md`.

---

## [Sin publicar]

### Cambiado
- **EP15: el factor F del límite de verificación (UVL) sale de la tabla 7 de
  EP15-A3**, por grados de libertad y número de muestras, con el valor impreso
  (dos decimales). Antes se calculaba con la fórmula del apéndice B5, de la que
  la tabla sale; la diferencia está en el tercer decimal (con 20 gl y 2
  muestras, 1,307 contra 1,31) y en un caso al límite podía dar otro veredicto.
  Fuera de la tabla (gl < 5 o > 34, más de 6 muestras) se usa la fórmula, y el
  informe dice cuál se usó.
- **EP15, veracidad, escenario A completo (§3.3)**: nuevas opciones «U con
  cobertura del 95 %» (se_RM = U/1,96) y «del 99 %» (U/2,58); los límites de un
  IC entran por ahí con U = (superior − inferior)/2. El factor k ya no viene
  cargado con 2: con «U, con su factor k» hay que escribirlo, y sin él el
  análisis lo pide. Antes una U «al 95 %» sin k se dividía por 2 en vez de 1,96.

---

## [1.2.0] — 2026-09-27

Versión de interfaz: los números son los de la 1.1.0. Lo que cambia es cómo se
cargan los datos, cómo se lee el informe y cómo se ve la aplicación.

### Interfaz
- **El informe empieza por la conclusión**: «Cómo se lee» y «Qué NO se puede
  concluir», después las advertencias, y recién ahí los números, el método, lo
  verificado, la fórmula y las referencias. Antes la lectura quedaba abajo,
  fuera de la vista en el panel. Recuadros que Qt sí dibuja (tablas, no `div`).
- **La hoja de datos dice el tipo de cada columna** (el mismo que usa el
  Omnianálisis: numérica, categórica, fecha, «códigos 1–3», «a confirmar») y
  cuántas celdas vacías tiene; las vacías se pintan.
- **Tema renovado, igual de denso**: tarjetas blancas con el título en el
  acento teal, pestañas planas, botón principal con relleno, bordes suaves; el
  Omnianálisis deja su azul propio. Los combos vuelven a tener flecha.
- Cambiar de pestaña ya no borra las variables elegidas; la misma columna dos
  veces se rechaza; «12,5» con coma se lee como número; el diálogo de «Validar
  un método» entra en una notebook; tildes en menús y títulos.

### Corregido
- Vaciar una celda guardaba "" y la columna dejaba de ser numérica; lo escrito
  en una fila agregada con «Fila» se perdía.
- El recuadro «Fórmula» del panel pegaba todas las líneas en un párrafo.
- El rótulo del eje Y del Bland-Altman en % salía cortado.

---

## [1.1.0] — 2026-09-27

Una segunda auditoría, esta vez de las fórmulas, de qué columnas y filas llega a
cada análisis, y de las reglas de decisión del Omnianálisis contra CLSI EP09c.
Encontró **42 defectos que la 1.0.0 todavía tiene**; diez de ellos cambian el
número o la conclusión que ve el usuario. Detalle en `docs/AUDITORIA-2026-09.md`.

### Corregido — el análisis recibía otros datos

- **Los análisis pareados comparaban cada fila con la del paciente siguiente.**
  Cada columna descartaba sus faltantes por separado y después se cortaban a la
  misma longitud: con **una sola celda vacía**, todo lo que seguía quedaba
  desalineado. En Bland-Altman, con un NaN en 20 pares, los límites de acuerdo
  pasaban de ±2,4 a **±90**, sin aviso. Afectaba a 22 análisis (t pareado,
  Wilcoxon, signos, Bland-Altman, Passing-Bablok, Deming, ICC, regresión,
  Kaplan-Meier, ROC, bootstrap y otros). **Los informes del panel manual hechos
  con hojas que tenían celdas vacías pueden estar mal.**
- **ANOVA, Kruskal-Wallis, Friedman y Cronbach tomaban todas las columnas
  numéricas de la hoja**, no las elegidas: comparaban los valores contra los
  códigos de grupo (F = 7460 donde corresponde p = 0,79).
- **Fisher, McNemar, OR, RR, prueba diagnóstica y razones de verosimilitud
  leían las dos primeras filas como una tabla de conteos**, en vez de tabular
  los datos crudos: sobre 80 pacientes codificados 0/1, Fisher daba «OR = nan,
  p = 1» donde p ≈ 0.
- **Tamaño muestral, poder y las calculadoras de 2 medias, 2 proporciones y 2
  AUC** calculaban siempre el mismo ejemplo fijo, o las primeras celdas de la
  hoja. Ahora piden sus números en el diálogo.
- Regresión múltiple y logística: el objetivo era la última columna y las
  predictoras, todas las demás. Ahora, las elegidas.

### Corregido — cálculo

- **ANCOVA**: pendiente total en vez de intragrupo, ajuste de medias con el
  signo invertido y suma de cuadrados del error negativa. Ahora statsmodels.
- **Probit**: todos los errores estándar valían 0,1 (el mismo defecto que Cox
  tenía en la 1.0.0) y el AIC tenía el signo cambiado.
- **Medidas repetidas**: el ε de Greenhouse-Geisser sin doble centrado.
- **Random Forest** informaba la exactitud sobre los datos de entrenamiento
  (0,95 con predictoras de ruido puro). Ahora fuera de muestra, contra no tener
  modelo, con importancia por permutación.
- **Deming**: λ se aplicaba al revés de su propia definición (latente con λ = 1).
  El IC jackknife usaba t(N−1); EP09c pide t(N−2). Nuevo **Deming ponderado**
  (EP09c, apéndice B) para CV constante; el IC de su intercepto usa el n
  efectivo de los pesos (con t(N−2) cubría ~91 %).
- Límites de referencia con los rangos de EP28-A3c e IC del 90 %; intervalos por
  edad que perdían el último tramo; razones de verosimilitud con el EE cruzado
  (IC con 100 % de cobertura); IC de la media recortada (86 % de cobertura);
  p de Grubbs; log-rank con tiempos 0; kappa con el EE de H1 y sin IC;
  asimetría y curtosis; F de varianzas con p > 1; mediciones seriales con un
  «p global» que trataba las mediciones repetidas como independientes.
- **Kaplan-Meier** imprimía una «supervivencia media» que era el promedio de
  los puntos de la curva: ahora la mediana con IC. **Cox** avisaba «no
  convergió» en 19 de cada 20 ajustes sanos y dejaba pasar la separación
  completa como convergida.

### Corregido — Omnianálisis

- Con la referencia en la segunda columna, el **sesgo en los niveles de
  decisión salía con el signo invertido** (−9,3 % para un método que lee
  +10 %).
- Elegía la regresión por el sesgo medio en vez de por la variabilidad de las
  diferencias (EP09c §5.4), y no tenía Deming ponderado.
- El mismo par decía «significativo» en su bloque y «no significativo» en la
  matriz: ahora una sola familia de Benjamini-Hochberg.
- Grupos con dispersiones distintas iban a Kruskal-Wallis (16,7 % de falsos
  positivos con medias iguales). Ahora Welch con Games-Howell, normales o no.
- Grupos codificados 1/2/3 se leían como una cantidad; tablas ralas con χ²
  (ahora Fisher o Monte Carlo); Dunn con corrección por empates.

### Agregado

- **Asistente «Validar un método»** (menú *Comparación de métodos*): EP09c +
  EP15-A3 en un veredicto. Bland-Altman con CCC, la recta que corresponde, el
  sesgo en los niveles de decisión con su IC, la precisión por EP15-A3 y el
  sesgo contra el valor asignado; contra el sesgo permitido y/o el error total
  (TEa) da **cumple / no cumple / no concluyente**.
- **Precisión EP15-A3** como análisis suelto, verificado contra la norma con
  sus fe de erratas de 2015 y 2017.
- **Prueba Cusum de linealidad** para Passing-Bablok (Passing y Bablok 1983).
- **Omnianálisis**: series temporales (Mann-Kendall, pendiente de Sen,
  Ljung-Box); el puntaje de cada par candidato a comparación de métodos en la
  auditoría.
- Todos los informes llevan el método y por qué ese, los supuestos
  verificados, la fórmula con sus citas, la lectura y lo que **no** se puede
  concluir. Ningún informe dice «significativo» ni imprime un p como cero.
- Kaplan-Meier con cuantiles e IC log-log; log-rank con k grupos y HR; Cox con
  riesgos proporcionales (Schoenfeld); meta-análisis con τ², intervalo de
  predicción y Egger; bootstrap BCa; intervalos por edad por regresión (Altman
  1993); verificación de un intervalo de referencia publicado.

### Cambiado a propósito

- La t de una muestra prueba contra el μ₀ elegido (antes, siempre contra 0).
- CMH pide exposición, evento y estrato como columnas crudas.
- «Youden plot» es el interlaboratorio de MedCalc; el índice J pasó a la curva
  ROC. El «Mountain plot» es el de Krouwer (antes, un histograma).
- Passing-Bablok ya no dice «métodos concordantes» por un criterio del 10 % de
  la media que no sale de ninguna norma: decide por los intervalos, y un
  intervalo demasiado ancho no concluye.

### Quitado

- **La pestaña Control de Calidad** (estadísticas y tendencias de control), que
  no tenía ni núcleo de cálculo ni tests. Si vuelve, será verificada.

---

## [1.0.0] — 2026-08-23

Primera versión con el núcleo estadístico verificado contra oráculos
independientes. El salto de mayor no es por funcionalidad nueva: es porque los
números de varias pruebas cambian respecto de cualquier versión anterior.

### Corregido — cálculo

Verificado contra scipy, statsmodels, lifelines, sklearn y pingouin, y contra
ejemplos publicados (NIST/SEMATECH, CLSI EP12 y EP28, Passing & Bablok 1983).

- **Passing-Bablok: el intervalo de confianza no era un intervalo de
  confianza.** Usaba los percentiles empíricos 2,5 y 97,5 de las pendientes por
  pares, que no son observaciones independientes. Cubría el **100 %** y ante un
  sesgo proporcional real del 10 % lo detectaba en **0 de 900** corridas.
  Reemplazado por los estadísticos de orden de la publicación original.
- **Passing-Bablok: faltaba el desplazamiento K**, así que era Theil-Sen. La
  simetría `b(x,y)·b(y,x)` daba 0,04 con ruido en vez de 1.
- **Cox: los errores estándar eran una constante.** El código leía
  `result.hes_inv`; el atributo de scipy es `hess_inv`. El `hasattr` daba
  siempre falso y todos los errores estándar valían 0,1, con cualquier dato.
  También estaban invertidos el conjunto de riesgo y el signo del AIC.
  Reescrito con la corrección de Efron.
- **Tamaño muestral: usaba z donde va t.** Con efecto grande pedía `n = 2` para
  un poder de 0,80 cuyo poder real es 0,18. Y `power_analysis` usaba z también,
  así que la ida y vuelta cerraba y confirmaba su propio error.
- **AUC subestimado con puntajes empatados.** La curva ROC no arrancaba en el
  origen. Error medio de −0,095 con puntaje binario, siempre por debajo.
- **CMH: el IC del OR contradecía a su propio p.** Con `p = 0,00036` el
  intervalo era (0,11 – 243,9). Varianza reemplazada por Robins-Breslow-Greenland.
- **Kappa ponderado devolvía −55**, con κ acotado a [−1, 1]. Doble división por n.
- **ESD generalizado: perdía el enmascaramiento.** Contra el ejemplo del NIST
  declaraba 1 outlier donde la respuesta publicada es 3.
- **Grubbs: el parámetro `side` se aceptaba y se ignoraba**, y el p llegaba a 3,58.
- **Riesgo relativo: rechazaba tablas calculables**, daba intervalos de ancho
  cero con `a = 0`, y devolvía NNT infinito cuando la exposición aumenta el riesgo.

### Agregado — cálculo

- Intervalos de confianza de Wilson para sensibilidad y especificidad, que
  **CLSI EP12 exige** y no existían.
- Aviso del mínimo de **120 sujetos** de CLSI EP28-A3c en los intervalos de
  referencia, con la distinción entre establecer y verificar.
- Advertencia en `compare_two_auc` de que solo cubre AUC independientes.

### Corregido — robustez

- El núcleo filtraba con `~np.isnan(x)`, que **deja pasar ±infinito**. 44 sitios
  en 13 archivos migrados a `isfinite`. Un infinito entra solo en datos de
  laboratorio: un `#¡DIV/0!` de Excel, un log(0), un código de desborde.
- Ocho funciones devolvían NaN sin explicación con datos constantes; ahora
  rechazan con motivo.
- Cuatro caídas del Omnianálisis con datos degenerados.
- `ax.grid(False, alpha=...)` **encendía** la grilla en vez de apagarla.

### Agregado — interfaz

- **Gráficos editables.** Cada figura trae la barra de matplotlib (zoom,
  desplazamiento, guardar, editor de curvas) y un diálogo propio: título y
  rótulos, tamaño y familia de letra, tamaño / color / opacidad de los puntos,
  grilla, leyenda con posición, tamaño en pulgadas, exportación de 72 a 600 ppp
  y líneas de tendencia lineal, cuadrática o cúbica con su ecuación y su R².
- **La pantalla de carga dice qué build es**: versión, fecha, rama y commit,
  horneados por `build_exe.py` en cada compilación.

### Cambiado — interfaz

- **El CCC de Lin descompuesto se rediseñó.** Su panel izquierdo repetía el
  gráfico de regresión de comparación. Ahora ubica el par (Cb, ρ) en el plano
  precisión × veracidad, con las curvas de igual ρc y las zonas de McBride. El
  panel derecho pasó de una barra fina a tres rieles que llegan a 1.

### Pruebas

De 443 a 744. Las nuevas comparan contra implementaciones independientes y
contra ejemplos publicados: ninguno de los 12 defectos hacía fallar a las 443
anteriores, porque comparaban BioStat contra sí mismo.

---

## [0.9.0] — 2026-08-22

Etiqueta **retroactiva**, puesta el 23 de agosto para poder nombrar el estado
anterior a la auditoría. No hubo una publicación con este número.

Corresponde al commit `1c72f41`, el último antes de que empezara la revisión de
cálculo. Es la versión de la que salieron los ejecutables del 22 y del 23 de
agosto por la mañana.

### Contenía

- Omnianálisis auditable: catálogo de 41 ensayos, árbol de decisión dibujado,
  vista caso por caso.
- Bland-Altman con sus tres variantes y el eje de referencia de Krouwer.
- CCC de Lin descompuesto en precisión y veracidad.
- 443 pruebas.

### Defectos conocidos, corregidos en 1.0.0

Los 12 de la sección anterior. **No usar esta versión para validar métodos.**
