# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Versionado [semántico](https://semver.org/lang/es/).

> [!warning] Todo build anterior a **1.0.0** produce números equivocados
> La auditoría del 23 de agosto de 2026 encontró 12 defectos de cálculo, varios
> capaces de cambiar una decisión clínica. Si validaste un método con una
> versión anterior usando **Passing-Bablok**, **Cox**, **tamaño muestral** o
> **AUC con puntajes empatados**, conviene rehacer ese análisis. El detalle
> está en `docs/AUDITORIA-2026-08.md`.

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
