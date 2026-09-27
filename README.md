# BioStat

Software estadístico para laboratorio clínico. Inspirado en MedCalc.

> [!warning] Usá 1.1.0 o posterior
> Toda versión anterior a **1.1.0** tiene defectos de cálculo que pueden cambiar
> una decisión clínica — ver [CHANGELOG.md](CHANGELOG.md). La pantalla de carga
> dice qué build estás corriendo: versión, fecha, rama y commit.

## Cómo está organizado el repositorio

| Rama | Para qué |
|---|---|
| `develop` | **Donde se trabaja.** Siempre es la más nueva. |
| `master` | Lo publicado. Se adelanta desde `develop` al sacar una versión, y se etiqueta ahí. |

Las versiones publicadas llevan **etiqueta anotada** (`git tag -n`), así que
`git describe` identifica cualquier build. La misma identidad va horneada en el
ejecutable y se muestra en la pantalla de carga: si alguna vez aparece un
`.exe` suelto, alcanza con abrirlo para saber de dónde salió.

```bash
git clone -b develop https://github.com/dubeda06-sys/BioStat.git   # para trabajar
git tag -n                                                          # versiones publicadas
```

Antes de compilar, correr las pruebas:

```bash
python -m pytest tests/ -q     # 1614 (27 sep); el número crece
python scripts/smoke_ui.py     # 78/78
```

## Instalación

```bash
pip install -r requirements.txt
python main.py
```

## Compilar ejecutable

```bash
pip install pyinstaller
python build_exe.py
```

El ejecutable `BioStat.exe` se copiará automáticamente al Escritorio.

## Funcionalidades

### Estadísticas Descriptivas
- Media, mediana, DE, varianza, CV%, sesgo, curtosis
- Media geométrica y armónica
- Media recortada (robusta)
- Asimetría y curtosis (tests formales)
- Tabla de percentiles con IC

### Comparación de Grupos
- t-test pareado e independiente
- t-test de 1 muestra
- ANOVA una vía y dos vías
- ANCOVA (con covariable)
- Medidas repetidas (Greenhouse-Geisser)
- Mann-Whitney U, Wilcoxon, Kruskal-Wallis, Friedman
- Sign test
- Comparar 2 medias y 2 proporciones (datos resumen)

### Tablas de Contingencia
- Chi-cuadrado, Fisher exact, McNemar
- Cochran Q
- Cochran-Mantel-Haenszel (CMH)
- F-test (comparar varianzas)

### Correlación y Regresión
- Pearson, Spearman, correlación parcial
- Regresión lineal simple y múltiple
- Regresión logística con odds ratios
- Passing-Bablok, Deming
- Regresión de Cox (supervivencia)
- Regresión Probit

### Análisis de Métodos
- Curva ROC con AUC y umbral óptimo (Youden)
- Bland-Altman (simple y múltiple)
- Concordancia (Kappa, Kappa ponderado, ICC, Cronbach alfa)
- CV de duplicados
- Comparar 2 AUC independientes

### Prueba Diagnóstica
- Sensibilidad, especificidad, PPV, NPV
- Likelihood Ratios (LR+, LR-)
- Odds Ratio y Riesgo Relativo

### Supervivencia
- Kaplan-Meier
- Log-rank test
- Regresión de Cox

### Meta-análisis
- Modelo de efectos fijos y aleatorios
- Forest plot
- Heterogeneidad (I², Q de Cochran)

### Machine Learning
- Random Forest (clasificación y regresión)
- Bootstrap (media, mediana, diferencia, correlación, regresión)

### Tamaño Muestral
- 1 media, 2 medias, 2 proporciones
- Correlación, poder estadístico

### Detección de Outliers
- Grubbs, Tukey (IQR), ESD generalizado

### Intervalos de Referencia
- Percentiles con IC
- Intervalos edad-relacionados

### Gráficos Especializados
- Youden plot, Polar plot, Waterfall chart, Mountain plot
- Mediciones seriales (resumen por sujeto)

### Normalidad
- Shapiro-Wilk

## Arquitectura del Proyecto

```
BioStat/
├── main.py                  # Punto de entrada
├── build_exe.py             # Compila el .exe (usa biostat.spec)
├── src/
│   ├── core/                # Cálculo puro: estadística verificada contra oráculos
│   ├── resultado/           # La envoltura Resultado
│   │   ├── modelo.py        # Resultado, Valor, Supuesto, Figura
│   │   ├── citas.py         # Fórmula y citas de cada análisis
│   │   ├── render_html.py   # El único renderizador del informe
│   │   └── constructores/   # Un constructor por análisis (78), por familia
│   ├── analysis/            # Omnianálisis: árbol de decisión, auditoría, casos
│   ├── ui/                  # Interfaz (PyQt6)
│   │   ├── main_window.py   # Ventana, menús y pestañas
│   │   ├── entradas.py      # Del diálogo a cada constructor (sin Qt)
│   │   ├── analysis_panel.py
│   │   ├── dialogs.py       # El diálogo de cada análisis
│   │   ├── omni_panel.py    # Omnianálisis
│   │   └── graphs_panel.py
│   └── utils/
└── tests/                   # Un archivo por familia, contra oráculos externos
```

Todo análisis devuelve un `Resultado`: valores con IC, el método y por qué,
los supuestos verificados, fórmula, citas, lectura y matiz. Un análisis nuevo
entra en `CONSTRUCTORES`, `FIRMAS` y `citas.py`, y en `ENTRADAS` para el panel;
el test de contrato lo recorre solo. Leé `docs/HANDOFF.md` antes de tocar nada.

## Requisitos

- Python 3.8+
- PyQt6
- NumPy, SciPy, pandas
- Matplotlib, Seaborn
- qtawesome (iconos profesionales)

## Iconografía

Los iconos utilizan la librería `qtawesome` (FontAwesome 5 / Material Design)
para una apariencia profesional y consistente en toda la aplicación.

## Tema Visual

BioStat utiliza el tema **Clean Clinical**:
- Fondos claros (#F3F5F9, #FFFFFF)
- Acento azul médico (#2B579A) para elementos interactivos
- Verde institucional (#107C41) para acciones de éxito
- Sin colores oscuros ni neón — diseñado para uso prolongado en laboratorio
