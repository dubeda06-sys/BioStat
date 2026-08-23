# BioStat — Handoff / Dónde seguir

> **2026-08-22**. Leé esto primero.
> Rama de verdad: **`develop`**. `master` 17 commits atrás.

## El `.exe` del Escritorio ya está al día

Recompilado 22 ago desde `develop`. El anterior era del 1 jul, **sin ninguna
corrección de cálculo de este año**: IC de LoA con `1.96` en vez de `t(n−1)`,
**8,6 % más angosto** a n=15. Método validado con ese exe entre julio y agosto =
IC impresos mal. Copia vieja: `BioStat_2026-07-01_VIEJO.exe` en el Escritorio;
borrarla para que nadie la abra por error.

**Después de tocar el core, recompilar:**

```bash
python -m pytest tests/ -q        # esperar 305 verdes
python scripts/smoke_ui.py        # esperar 76/76, 0 bugs
python build_exe.py               # deja dist/BioStat.exe y lo copia al Escritorio
```

Qt sin pantalla: `QT_QPA_PLATFORM=offscreen`.

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

## Estado actual de `develop` (`1e44e82`)

Del 13 de agosto, verificado contra MedCalc 23.6.5 con datos reales de un panel
CAP de EBV (n=15):

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

### Arquitectura propuesta (falta aprobar el detalle)

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
texto: dos verdades.

El registro de supuestos y citas **no es proyecto aparte**: es el campo
`supuestos` de la envoltura, alimentado por una tabla declarativa.

### Las citas ya existen, no hay que investigarlas

`docs/referencia-medcalc/` tiene las fórmulas de MedCalc **con la URL del manual
de donde salió cada una** — comparación de métodos, concordancia, control de
calidad. Ver su `LEEME.md`.

## Deudas conocidas

1. **`src/ui/analysis_methods.py`, 2329 líneas.** Lo resuelve la envoltura de A.
2. **Levey-Jennings y Westgard, eliminados el 22 ago.** Vivían en
   `src/ui/qc_panel.py` (`_lj`, `_wj`, `_wj_rules`), sin core ni tests: la parte
   que decide si un lote se acepta o rechaza era la única sin verificación de
   referencia. La pestaña QC queda con **Estadísticas** y **Tendencias**;
   `src/core/qc/__init__.py` sigue **vacío**. Si el QC vuelve, entra por el core
   con tests contra un caso publicado, no dentro del panel.
3. **`passing_bablok` omite la corrección de desplazamiento K** (pendientes < −1).
   Inocuo con pendientes positivas, pero no es la definición completa. Cambiarlo
   altera resultados: **validar contra un caso publicado antes de tocarlo.**
4. Omnianálisis (de julio, vigentes): calibrar los pesos del score de comparación
   con datos reales; `PESO_UNIDAD` y `PESO_PAREADO` sin cablear; series temporales
   detectadas pero no analizadas.

## Cómo correr

```bash
python main.py                                   # la app
python -m pytest tests/ -q                       # 305 tests
python scripts/smoke_ui.py                       # smoke de UI, 76/76
python build_exe.py                              # dist/BioStat.exe + copia al Escritorio
```

> [!caution] Nunca uses `sed` sobre archivos de este repo
> Corrompe los multibyte (μ₀ √ d̄) y hace crashear Qt. Editá con herramientas que
> respeten UTF-8, o con E/S de Python en UTF-8 explícito.

## Ramas

| Rama | Estado |
|---|---|
| `develop` | **fuente de verdad** |
| `master` | 17 commits atrás, sin correcciones de este año. `origin/HEAD` apunta acá: **un clon nuevo cae en código viejo** — usar `git clone -b develop` |
| `feat/medcalc-informed-agreement` | fusionada, borrable |
| `fix/correctness-and-refactor`, `optimización-de-código-d7fdb` | viejas |

## Referencias

- Fórmulas y citas: `docs/referencia-medcalc/`
- Spec del Omnianálisis: `docs/omnianalisis_spec.md` · plan: `docs/omnianalisis_plan.md`
- Repo: https://github.com/dubeda06-sys/BioStat
