---
tags: [biostat, medcalc, brechas, laboratorio, software]
tipo: analisis
fecha: 2026-08-13
repo: github.com/dubeda06-sys/BioStat
rama_verdad: develop
cobertura: 82/109
---

# BioStat — Brechas contra MedCalc

Inventario de MedCalc: [[MedCalc - Procedimientos estadisticos]] · fórmulas verificadas:
[[MedCalc - Formulas - Comparacion de metodos y concordancia]] · mapa: [[MedCalc - Mapa]]

**BioStat** = app PyQt6 de estadística para laboratorio clínico, propia
(`github.com/dubeda06-sys/BioStat`, rama **`develop`** = fuente de verdad).
102 funciones públicas en `src/core` y `src/analysis`, ~9 000 líneas.

Clon de trabajo durable: `C:\Users\Laboratorio2\Desktop\Daniel\BioStat-work`.

## Cobertura

**82 de los 109 procedimientos estadísticos de MedCalc** están cubiertos. No es poco: el núcleo
clínico (comparación de métodos, ROC, regresión, supervivencia, no paramétricas, meta-análisis,
concordancia) está entero.

| Tema | Faltan |
|---|---|
| Tamaño de muestra | 12 |
| Comparación de métodos | 3 |
| Proporciones y tasas | 3 |
| ROC / diagnóstico | 3 |
| Control de calidad | 2 |
| Regresión | 2 |
| Correlación / acuerdo | 1 |
| Medias / ANOVA | 1 |

## Lo que ya se corrigió en esta pasada

Commit `c953688` en la rama `feat/medcalc-informed-agreement`. **Local, sin push.**

**Dos defectos verificados contra MedCalc**, usando los 15 datos reales del panel CAP de EBV
([[EBV - Veracidad contra consenso CAP]]) y los cuatro informes que MedCalc dejó en `%TEMP%`:

1. **IC de los límites de acuerdo con multiplicador equivocado.** `bland_altman.py` multiplicaba el
   error estándar por `1.96` en vez de `t(n-1)`. La varianza ya era la correcta
   (`var(LoA) = s²(1/n + z²/(2(n−1)))`); fallaba sólo el multiplicador. A n=15 el semiancho salía
   **8,6 % más corto**. Ahora los cuatro informes de MedCalc se reproducen exactos.

2. **CCC rompía su propia identidad.** `concordance_correlation` mezclaba momentos muestrales
   (`ddof=1`) con el término `(mean1−mean2)²`, que no se escala. Eso hace que **`ρc ≠ ρ · Cb`**
   (error de hasta +0,0075 en el peor caso del set). Con momentos poblacionales la identidad se
   cumple exacto — y eso importa ahora que se exponen ρ y Cb por separado: tienen que multiplicar
   de vuelta al CCC reportado.

**Ampliaciones**, todas trazadas a fuente:

- **CCC descompuesto en ρ (precisión) × Cb (veracidad)**, con IC 95 % (Fisher z, Lin 1989) y la
  escala de McBride (2005). Es la adición de más valor: separa si el desacuerdo es dispersión o
  sesgo — causas distintas, correcciones distintas. En el caso EBV fue lo que reveló que un ensayo
  tenía problema de veracidad y el otro de precisión.
- **Eje X de referencia** en Bland-Altman (`reference="x"/"y"`). Con un método de referencia las
  diferencias se regresan contra la referencia, no contra el promedio, que atenúa el sesgo
  proporcional (Krouwer 2008, citado por el propio manual de MedCalc; distinción de CLSI EP09).
  Se devuelven **ambas** pendientes. Medido: +0,336 (P=0,08) contra referencia vs +0,097 (P=0,67)
  contra el promedio.
- **LoA no paramétricos** (percentiles 2,5–97,5) + Shapiro-Wilk sobre las diferencias, para elegir
  entre la versión paramétrica y la que no asume normalidad. MedCalc ofrece las dos.
- El Omnianálisis reporta la descomposición y **nombra dónde está el defecto**.

Verificación: **83 tests verdes** (68 previos + 15 nuevos), smoke de UI **76/76**, 0 bugs.
Los 15 nuevos están en `tests/test_agreement_medcalc.py` y comparan contra los valores exactos de
MedCalc, no contra nuestra propia aritmética.

## Segunda pasada — robustez (commit `0a60ea5`, en `develop`)

Objetivo declarado: *«que BioStat sea tan robusta como MedCalc»*. Lo medí en vez de suponerlo:
12 casos degenerados × 6 funciones del core (n<3, columnas constantes, NaN, infinitos, ceros,
negativos).

| | Antes | Después |
|---|---|---|
| **CRASH** (excepción no controlada) | 2 | **0** |
| **BASURA** (NaN/inf devuelto en silencio) | 16 | **8**, todos con nota |
| **NONE** (rechazo mudo) | 26 | **0** |
| **RECHAZO** (con motivo específico) | — | **32** |
| OK | 28 | 32 |

**Causa raíz:** el core filtraba con `np.isnan` en 14 módulos y con `np.isfinite` en **ninguno**.
Los infinitos entraban y contaminaban medias, varianzas e intervalos. Los 2 crashes eran
`stats.linregress` con todos los x idénticos, subiendo como `ValueError` hasta la UI.

**Contrato nuevo**, copiado del comportamiento de MedCalc, en `src/core/guards.py`:

1. Nunca lanzar excepción por culpa de los datos.
2. Nunca devolver un número no finito sin nota que lo explique.
3. Al rechazar, decir **por qué**, con un mensaje accionable.

Antes la UI decía «No se pudo calcular». Ahora dice *«Quedan 2 pares utilizables de 5: se
descartaron 3 con valores ausentes o no finitos. Se necesitan al menos 3.»* — el registro de los
mensajes que extraje del binario de MedCalc.

Los 8 NaN que quedan son intervalos **genuinamente indefinidos** (concordancia perfecta, n=2) y
todos vienen con su nota. Cero NaN mudos.

Bonus: Passing-Bablok ahora **avisa sin negarse** cuando n < 30 (Bablok & Passing 1985; Ludbrook
2010 sugiere 50) — que es justamente el comportamiento «robusto como MedCalc»: calcula, y te dice
que la estimación no tiene potencia.

**253 tests** (eran 68), smoke 76/76.

> [!note] Deuda conocida que dejé anotada
> `passing_bablok` omite la corrección de desplazamiento **K** (conteo de pendientes < −1) del
> estimador. Es inocuo con datos de comparación de métodos normales (pendientes positivas), pero
> no es la definición completa de Passing-Bablok. Cambiarlo altera resultados, así que necesita
> validación contra un caso publicado antes de tocarlo.

## Hallazgo estructural: el QC no es testeable

Levey-Jennings, reglas de Westgard y análisis de tendencias **existen**, pero implementados
**dentro de `src/ui/qc_panel.py`** (`_wj_rules`, `_lj`, `_tr`). `src/core/qc/__init__.py` está
**vacío**.

Consecuencia: la parte del programa que decide **si un lote analítico se acepta o se rechaza** es la
única sin tests de referencia, porque el arnés numérico sólo cubre `src/core`. Mover esa lógica al
core y darle tests es, en mi lectura, la mejora de mayor impacto que queda — por encima de agregar
procedimientos nuevos.

## Brechas por prioridad

### Alta — comparación de métodos, que es lo que este laboratorio usa

| Falta | Por qué importa | Fuente |
|---|---|---|
| **Coeficiente de repetibilidad** | Mide repetibilidad de UN método con duplicados. Fórmula publicada: `CR = 1.96·√(Σ(d₂−d₁)²/n)` | `bland-altman-plot.php` |
| **LoA dependientes de la magnitud** | Para heterocedasticidad. `LoA = b₀+b₁A ± 2.46(c₀+c₁A)`, con el LoAA como resumen | Bland & Altman 1999, eqs 3.1–3.3 |
| **Máxima diferencia permitida** | Campo que MedCalc expone en el diálogo; combina el CV de ambos métodos | `bland-altman-plot.php` |
| **Comparación de múltiples métodos** | Hoy sólo por pares | `comparison-of-multiple-methods.php` |
| **Pitman-Morgan** | Prueba de varianzas **pareadas**. La F ordinaria supone independencia y no la hay | — |

### Media

- **Comparación de coeficientes de correlación** — MedCalc **sí publica** las tres fórmulas:
  z de Fisher, `se = √(1/(n₁−3) + 1/(n₂−3))` y el estadístico z. Implementable tal cual.
- **Área parcial bajo la curva ROC** y **precision-recall**.
- **Tasas e IC de una tasa**, comparación de tasas.
- **Yuen-Welch** (medias recortadas, independientes) — hay `trimmed_mean` pero no la prueba.
- **IC del kappa** por Fleiss et al. 2003; **límite inferior del alfa de Cronbach** por Feldt 1965.

### Baja — tamaño de muestra por precisión del IC

Los 12 faltantes son casi todos de la familia «IC de anchura requerida». **El manual de MedCalc no
publica ninguna fórmula para estos**: remite a Machin et al. 2009. Implementarlos exige ir al libro.

## Lo que MedCalc tiene y BioStat no, fuera del catálogo de pruebas

Esto no sale del conteo 82/109 pero es arquitectura que vale mirar:

1. **Informes como HTML+CSS con hoja de estilo editable.** MedCalc escribe cada informe a HTML con
   `reports.css` al lado; cambiar ese archivo reestiliza *todos* los informes. Y guarda la
   **precisión completa en el atributo `title`** de cada valor mostrado, así que el número redondeado
   se ve y el exacto se puede recuperar. BioStat ya arma HTML en los paneles — falta la hoja
   separada y el `title`.
2. **Lenguaje de scripts** con captura de `$report` / `$graph`, bootstrap BCa y jackknife como
   funciones de alto nivel sobre cualquier procedimiento. Ver [[MedCalc - Lenguaje de scripts]].
3. **Catálogo de funciones de celda**: 296 funciones en 18 categorías, con una familia `V*` que
   opera sobre variables con **filtro** (`AGE>40`). Ver [[MedCalc - Funciones (referencia completa)]].
4. **Atribución explícita del método.** MedCalc dice en cada página *qué variante* corre y de dónde
   la saca («according to Conover, 1999, p. 369-373»). Es lo que permite auditar un número. BioStat
   tiene buenos docstrings; llevarlos a la salida del informe sería barato y valioso.

## Enlaces

- [[MedCalc - Procedimientos estadisticos]] · [[MedCalc - Formulas - Comparacion de metodos y concordancia]]
- [[EBV - Veracidad contra consenso CAP]] — el caso real que destapó los dos defectos
- [[MedCalc - Mapa]]
