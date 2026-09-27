# Propuesta — la envoltura `Resultado`

> **2026-09-26.** Aprobada, con las cuatro recomendaciones del final. Es el paso
> **A** de «MedCalc pero guiado» (ver `docs/HANDOFF.md`, *Hacia dónde va*).
> Hecho: el arreglo de pares (paso 1), el esqueleto (paso 2) y el paso 3
> completo: Bland-Altman con el CCC, Passing-Bablok, Deming (con y sin
> ponderar), imprecisión desde duplicados, ICC y Bland-Altman múltiple, en
> `src/resultado/constructores/comparacion.py`. El asistente B quedó hecho el
> 27 sep sobre esa base (`constructores/validacion.py`, ver `docs/HANDOFF.md`);
> falta el paso 4, el resto de las familias.

## Qué hay hoy (leído del código, no del HANDOFF)

`src/ui/analysis_methods.py` tiene **2496 líneas** (el HANDOFF decía 2329: sigue
creciendo). Cada análisis es un método del mixin que hace todo junto: busca las
columnas, las limpia, llama al core, arma el HTML a mano, escribe la fórmula en
el recuadro de al lado y dibuja el gráfico. Consecuencias concretas:

| síntoma | cuántos | por qué importa |
|---|---|---|
| `_set_formula(...)` escrito a mano | 66 | la fórmula vive en la UI, sin cita, y el informe guardado no la lleva |
| `p` formateado con `:.6f` | 59 | `p=0.000000` se lee como *p exactamente cero*: el mismo defecto que `_fmt_p` ya arregló en el Omnianálisis |
| `_ok(...)` con «SIGNIFICATIVO» | 25 | el Omnianálisis evita esa palabra a propósito (se lee «importante») y lo fija un test; el panel manual la grita en un recuadro verde |
| veredictos propios | varios | `_passing` dice **«Métodos concordantes»** si el IC de la pendiente incluye 1 y el intercepto es menor que el 10 % de la media. Ese 10 % no sale de ninguna norma, y lo del IC es la trampa n.º 1 que `_regresion_concluyente()` ya desactivó en el Omnianálisis |

El mismo par de columnas puede dar hoy **dos lecturas distintas** según se
entre por el panel o por el Omnianálisis. Es la incoherencia que el HANDOFF
llama «dos verdades», pero ya está pasando antes de que exista el asistente B.

## Hallazgo que no puede esperar a la envoltura

> [!bug] Los análisis pareados del panel manual desalinean los pares
> Patrón repetido:
>
> ```python
> d1, d2 = self.data[c1].dropna(), self.data[c2].dropna()
> n = min(len(d1), len(d2))
> resultado = f(d1.values[:n], d2.values[:n])
> ```
>
> Cada columna descarta **sus** faltantes por separado y después se cortan a la
> misma longitud. Con un solo valor ausente en una columna, **cada fila a partir
> de ahí se compara con la del paciente siguiente**.
>
> Reproducido con Bland-Altman: 20 pares, método en prueba = referencia + ruido
> de DE 1, un solo NaN en la fila 0.
>
> | | sin faltantes | con 1 NaN, panel actual | con 1 NaN, pareado bien |
> |---|---|---|---|
> | sesgo | 0,032 | **−1,274** | 0,034 |
> | DE de las diferencias | 1,211 | **46,398** | 1,244 |
> | LoA | −2,34 a 2,41 | **−92,2 a 89,7** | −2,41 a 2,47 |
>
> No hay aviso: el informe sale con los números equivocados.
>
> **Mismo patrón en 22 análisis en total** (la lista está en el HANDOFF, y
> `tests/test_pares_alineados.py` los reproduce uno por uno). Pearson y Spearman están bien (hacen
> `data[[c1, c2]].dropna()`), y el Omnianálisis también (`omni_analyzer.py:425`).
> Los grupos independientes (t de Welch, Mann-Whitney, F, Kruskal, bootstrap de
> la diferencia de medias) no tienen
> este problema: ahí descartar por columna es lo correcto.
>
> **Propuesta:** arreglarlo ya, en un commit aparte y antes de A, con una sola
> función `_pares(c1, c2)` que haga `dropna` conjunto e informe cuántas filas
> descartó. Test: el de la tabla de arriba. Después, la envoltura absorbe esa
> función.
>
> Los informes del panel manual hechos con datos que tenían celdas vacías
> **pueden estar mal**. Con la hoja completa, no.

## La envoltura

Un objeto sin Qt, que arma un **constructor** por análisis y que consume **un
solo renderizador**.

```python
@dataclass
class Resultado:
    analisis: str                 # id estable, p.ej. "bland_altman"
    titulo: str                   # "Bland-Altman no paramétrico — A vs B"
    entrada: Entrada              # columnas, n usado, n descartado y por qué
    valores: list[Valor]          # nombre, número, IC, formato
    metodo: Metodo                # qué se corrió y POR QUÉ ese
    supuestos: list[Supuesto]     # misma forma que omni_caso.Paso
    formula: str
    citas: list[Cita]             # de la tabla declarativa, no escritas a mano
    lectura: str                  # qué dice, en castellano llano
    matiz: str                    # qué NO se puede concluir
    advertencias: list[str]
    figuras: list[Figura]         # título + función que dibuja la Figure
    crudo: dict                   # lo que devolvió el core, sin tocar
    error: str | None = None
```

### Cinco decisiones de diseño, con su porqué

1. **`Supuesto` copia la forma de `omni_caso.Paso`**: pregunta, medición,
   respuesta, consecuencia y *qué habría pasado si daba al revés*. Ese formato ya
   se probó en el Omnianálisis y es lo que vuelve auditable una decisión. Así,
   el día que el Omnianálisis migre, no hay que traducir nada.

2. **Un rechazo no puede evaluarse como verdadero.** El HANDOFF avisa que
   `{"error": ...}` es *truthy* y un `if res:` lo deja pasar. `Resultado` define
   `.ok` y hace que `__bool__` **lance una excepción**: el error de uso aparece la
   primera vez que se corre el test, no en el informe de un paciente.

3. **Las figuras son funciones que devuelven `Figure`**, no llamadas a
   `self._show_fig` escondidas dentro del cálculo. Con más de una, el panel las
   **apila con su título**, como la pestaña Gráficos del Omnianálisis (se pensó
   en un selector; apiladas se ven todas y la ventana de informe se lleva el
   bloque). Eso **cerró la deuda del CCC en el panel manual**.

4. **Fórmulas y citas en una tabla declarativa** (`src/resultado/citas.py`),
   con la clave del análisis. Se carga desde `docs/referencia-medcalc/`, que ya
   tiene cada fórmula con la URL del manual. Un test exige que todo análisis
   migrado tenga fórmula y al menos una cita.

5. **El lenguaje llano se muda, no se duplica.** `probabilidad_en_palabras`,
   `_fmt_p` y `_regresion_concluyente` salen de `omni_caso` hacia
   `src/resultado/lenguaje.py`, y los dos lados los importan de ahí. Si cada lado
   tiene su copia, vuelven a divergir.

### Dónde vive

```
src/resultado/
    modelo.py           # Resultado, Entrada, Valor, Metodo, Supuesto, Cita
    lenguaje.py         # p en palabras, formato de p, regresión concluyente
    citas.py            # tabla declarativa análisis → fórmula + citas
    datos.py            # pares(df, c1, c2), una(df, c): limpieza con conteo
    render_html.py      # el único renderizador
    constructores/
        comparacion.py  # bland_altman, passing_bablok, deming, ccc, cv_duplicados, icc
        ...             # una familia por archivo, como los menús
```

Sin Qt en ningún archivo: todo se prueba sin levantar ventana, igual que el
núcleo de `grafico_editable`.

## Cómo se migra sin romper nada

Las dos formas conviven. El `dispatch` de `_run` puede devolver `str` (lo viejo)
o `Resultado` (lo nuevo); el panel mira el tipo. `report_window` recibe el HTML
renderizado igual que hoy, así que no se entera.

**Orden:**

1. **Arreglo de pares** (commit aparte, arriba).
2. **Esqueleto**: `modelo`, `lenguaje`, `datos`, `render_html`, con tests.
   Ningún análisis migrado todavía.
3. **Familia de validación de métodos**: Bland-Altman (con el CCC), Passing-Bablok,
   Deming, CV de duplicados, ICC, Bland-Altman múltiple. Es el primer ciclo
   decidido en agosto y lo que va a consumir el asistente B.
4. **El resto, por familia**, en el orden de los menús. Cada familia es un
   commit y deja al mixin más chico.
5. Cuando el mixin quede vacío, se borra. Recién ahí se cierra la deuda 1.

**Cada migración lleva un test de paridad**: el constructor nuevo contra los
números que mostraba el HTML viejo, con los mismos datos. Donde el número
**cambia a propósito** (pares arreglados, veredicto de Passing-Bablok), el test
dice por qué en su nombre, como ya se hace en el repo.

**Tests de contrato**, sobre todos los análisis migrados:

- el HTML no contiene «significativo»;
- ningún p sale como `0.0000…`;
- hay fórmula y cita;
- un rechazo muestra el motivo del core, no «No se pudo calcular».

`scripts/smoke_ui.py` tiene que seguir en 76/76 después de cada paso.

## Qué NO entra

- **El Omnianálisis no migra en este ciclo.** Comparte `lenguaje.py` y la forma
  de `Supuesto`, nada más. Migrarlo es otro trabajo.
- **Nada de repetibilidad EP15.** El asistente B la nombra, pero hoy **no existe
  en el core**. Hay que escribirla con su test contra el ejemplo publicado de la
  norma, y eso es parte de B, no de A.
- Ningún cambio visual. El renderizador reproduce el estilo actual; rediseñar el
  informe es otra discusión.

## Decisiones (aprobadas el 26 sep: sí a las cuatro)

1. **¿Arreglo los pares ya**, antes de todo lo demás? Recomiendo que sí: hoy
   produce informes clínicos equivocados.
2. **«SIGNIFICATIVO» en el panel manual**: ¿se reemplaza por el lenguaje del
   Omnianálisis? Recomiendo que sí, por coherencia y porque el repo ya decidió
   que esa palabra engaña.
3. **Veredicto de Passing-Bablok en el panel**: ¿se saca el «10 % de la media» y
   se usa `_regresion_concluyente`? Recomiendo que sí: el 10 % es inventado, como
   lo era el «5 %» que se sacó de Bland-Altman en agosto.
4. **Alcance del primer tramo**: ¿solo la familia de validación (pasos 1–3) y
   después arrancamos B, o migramos todo antes de B? Recomiendo solo la familia:
   B la necesita, el resto no, y así se prueba el diseño en seis análisis antes
   de aplicarlo a 76.
