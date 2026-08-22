# BioStat — Handoff / Dónde seguir

> Última actualización: **2026-08-22**. Leé esto primero para retomar.
> Rama de verdad: **`develop`**. `master` está 17 commits atrás — ver más abajo.

## El `.exe` del Escritorio ya está al día

Recompilado el **22 de agosto** desde `develop`. El binario anterior era del 1 de
julio y **no tenía ninguna corrección de cálculo de este año** — sobre todo el IC de
los límites de acuerdo, que con `1.96` en vez de `t(n−1)` sale **8,6 % más angosto**
a n=15. Si alguien validó un método con ese exe entre julio y agosto, los IC que
imprimió están mal. Quedó una copia como `BioStat_2026-07-01_VIEJO.exe` en el
Escritorio, solo para comparar; conviene borrarla para que nadie la abra por error.

**Después de tocar el core, recompilar:**

```bash
python -m pytest tests/ -q        # esperar 292 verdes
python scripts/smoke_ui.py        # esperar 76/76, 0 bugs
python build_exe.py               # deja dist/BioStat.exe y lo copia al Escritorio
```

En Windows, para Qt sin pantalla: `QT_QPA_PLATFORM=offscreen`.

## Lo que entró el 22 de agosto

- **Levey-Jennings y Westgard: eliminados.** Ver Deudas.
- **Barra de menús por familia estadística, al estilo MedCalc.** Los 76 análisis
  estaban en un combo plano; ahora se agrupan en 15 submenús bajo `Estadísticas`,
  más `Gráficos`, `Pruebas diagnósticas`, `Control de Calidad`, `Herramientas` y
  `Ver` (Ctrl+1..5). La tabla vive en `src/ui/menus.py`, separada de los widgets, y
  `tests/test_menus.py` la verifica en las dos direcciones. Hace falta porque el
  menú elige por texto (`findText`): **un acento de diferencia deja la entrada
  muerta en silencio**, sin excepción ni mensaje.
- **PyQt6 mataba la aplicación cuando una excepción salía de un slot.** Un análisis
  que fallaba por la forma de los datos no mostraba error: cerraba la app de golpe.
  `src/utils/errores.py` instala un `sys.excepthook` propio — PyQt solo aborta si es
  el de fábrica — y la sesión sobrevive. **No reemplaza a `src/core/guards.py`**: es
  el último colchón, el contrato sigue siendo del core.
- **Ventana de carga con barra de progreso** en el `.exe` (`src/utils/splash.py`,
  `assets/splash.png`, `scripts/make_splash.py`). Cubre el arranque de Python
  (~6 s); los ~10 s previos son la descompresión del onefile, donde manda el
  bootloader y no corre Python.

> [!bug] Dos trampas encontradas, por si vuelven
> `Splash(..., text_font='Segoe UI')` rompe el splash entero: PyInstaller pega el
> nombre de la fuente en el script Tcl sin comillas y el espacio parte el comando.
> No hay error visible — queda una ventana Tk vacía de 216×239 en vez del splash.
> Y verificar mirando la clase de ventana **no alcanza**: `TkTopLevel` existe igual
> estando rota; hay que fotografiar la ventana.
>
> `biostat.spec` es ahora la receta real (`build_exe.py` compila desde el spec).
> Antes apuntaba a una ruta muerta de otra máquina y no lo usaba nadie.

## Estado actual de `develop` (`0a60ea5`)

Lo que entró el 13 de agosto, verificado contra MedCalc 23.6.5 con datos reales de
un panel CAP de EBV (n=15):

- **IC de los LoA con el multiplicador correcto.** La varianza ya estaba bien
  (`var(LoA) = s²(1/n + z²/(2(n−1)))`); fallaba el multiplicador, que es `t(n−1)`
  y no `1,96`. Ahora los cuatro informes de MedCalc se reproducen exactos.
- **CCC arreglado.** Mezclaba momentos muestrales (`ddof=1`) con el término
  `(m₁−m₂)²`, que no se escala, y por eso **rompía su propia identidad `ρc = ρ·Cb`**.
  Con momentos poblacionales la identidad se cumple exacto.
- **CCC descompuesto en ρ (precisión) × Cb (veracidad)** con IC y escala de McBride.
- **Eje X de referencia en Bland-Altman** (`reference="x"/"y"`, Krouwer 2008 / CLSI
  EP09): con un método de referencia las diferencias se regresan contra la
  referencia, no contra el promedio.
- **LoA no paramétricos** + Shapiro-Wilk sobre las diferencias.
- **`src/core/guards.py` y contrato de robustez**: nunca crashear por los datos,
  nunca devolver un no-finito sin nota, y al rechazar decir por qué. Auditoría:
  de CRASH=2 / BASURA=16 / NONE=26 a **CRASH=0, NONE=0, RECHAZO=32 con motivo**.
  Causa raíz: el core filtraba con `np.isnan` en 14 módulos y con `np.isfinite` en
  ninguno, así que los infinitos contaminaban medias, varianzas e intervalos.

> [!warning] Cambio de contrato que rompe consumidores
> Las seis funciones de comparación de métodos devuelven ahora `{"error": motivo}`
> en vez de `None`. **Un dict de rechazo es *truthy*** — un `if res:` lo deja pasar
> y revienta al indexar. Usá los helpers `_ok()` / `_sin_resultado()`. Los 36
> consumidores ya están actualizados; cualquier código nuevo tiene que respetarlo.

## Hacia dónde va: «MedCalc pero guiado»

Decidido el 21 de agosto. Tres definiciones que acotan todo lo demás:

1. **Identidad.** No un clon de catálogo: misma amplitud que MedCalc pero que
   acompañe — elige la prueba según los datos, avisa cuando no se cumplen los
   supuestos, y explica el resultado en castellano. **El diferencial es el criterio,
   no la cantidad de rutinas.**
2. **Público.** Se usa para el trabajo diario **y para formar gente**. Cada
   resultado tiene que ser una lección auditable: qué prueba, por qué esa, la
   fórmula, la norma citada y la interpretación.
3. **Primer ciclo: validación de métodos, a fondo.** EP09, veracidad,
   Bland-Altman, Passing-Bablok, Deming, CCC y repetibilidad (EP15). Pocas
   rutinas, impecables. Es donde el core ya está corregido y verificado contra
   MedCalc. (El control de calidad diario —Westgard— se sacó el 22 de agosto;
   ver Deudas.)

### Arquitectura propuesta (falta aprobar el detalle)

**A — Envoltura `Resultado` (sustrato).** El core sigue devolviendo lo suyo; encima
va un objeto que carga **valores, método, supuestos verificados, fórmula, cita e
interpretación redactada**. La UI y el informe lo consumen; nadie arma texto a mano.

El beneficio lateral es grande: hoy **`src/ui/analysis_methods.py` tiene 2329
líneas** porque cada análisis arma su HTML a mano, unas 40 ramas escritas de a una.
Con la envoltura hay **un solo renderizador** y ese archivo se desploma. La capa de
guía y el arreglo del archivo grande son la misma obra.

**B — Asistente «Validar un método» (primer consumidor).** Un flujo que corre
Bland-Altman + Passing-Bablok + Deming + CCC + repetibilidad juntos, chequea
supuestos y emite un veredicto único con su norma. Es como se trabaja de verdad:
nadie corre un Bland-Altman suelto, valida un método.

**Orden: A y después B.** Si se arranca por B sin A, el asistente escribe su propio
texto y quedan dos verdades.

El registro de supuestos y citas **no es un proyecto aparte**: es el campo
`supuestos` de la envoltura, alimentado por una tabla declarativa.

### Las citas ya existen, no hay que investigarlas

En `docs/referencia-medcalc/` están las fórmulas de MedCalc **con la URL del manual
de donde salió cada una** — comparación de métodos, concordancia y control de
calidad. Ver el `LEEME.md` de esa carpeta.

## Deudas conocidas

1. **`src/ui/analysis_methods.py`, 2329 líneas.** Lo resuelve la envoltura de A.
2. **Levey-Jennings y Westgard: eliminados el 22 de agosto.** Estaban dentro de
   `src/ui/qc_panel.py` (`_lj`, `_wj`, `_wj_rules`), sin core ni tests — la parte
   que decide si un lote analítico se acepta o se rechaza era la única sin
   verificación de referencia, y se sacó en vez de dejarla dando veredictos sin
   respaldo. La pestaña QC queda con **Estadísticas** y **Tendencias**.
   `src/core/qc/__init__.py` sigue **vacío**. Si el QC vuelve, entra por el core
   con tests contra un caso publicado, no dentro del panel.
3. **`passing_bablok` omite la corrección de desplazamiento K** (conteo de
   pendientes < −1). Inocuo con pendientes positivas normales, pero no es la
   definición completa. Cambiarlo altera resultados: **validar contra un caso
   publicado antes de tocarlo.**
4. Pendientes del Omnianálisis (de julio, siguen vigentes): calibrar los pesos del
   score de comparación con datos reales; `PESO_UNIDAD` y `PESO_PAREADO` sin
   cablear; series temporales detectadas pero no analizadas.

## Cómo correr

```bash
python main.py                                   # la app
python -m pytest tests/ -q                       # 292 tests
python scripts/smoke_ui.py                       # smoke de UI, 76/76
python build_exe.py                              # dist/BioStat.exe + copia al Escritorio
```

> [!caution] Nunca uses `sed` sobre archivos de este repo
> Corrompe los caracteres multibyte (μ₀ √ d̄) y hace crashear Qt. Editá con
> herramientas que respeten UTF-8, o con E/S de Python en UTF-8 explícito.

## Ramas

| Rama | Estado |
|---|---|
| `develop` | **fuente de verdad**, `0a60ea5` |
| `master` | 17 commits atrás, sin ninguna corrección de este año. `origin/HEAD` apunta acá, así que **un clon nuevo cae en código viejo** — usar `git clone -b develop` |
| `feat/medcalc-informed-agreement` | ya fusionada en develop, se puede borrar |
| `fix/correctness-and-refactor`, `optimización-de-código-d7fdb` | viejas |

## Referencias

- Fórmulas y citas: `docs/referencia-medcalc/`
- Spec del Omnianálisis: `docs/omnianalisis_spec.md` · plan: `docs/omnianalisis_plan.md`
- Repo: https://github.com/dubeda06-sys/BioStat
