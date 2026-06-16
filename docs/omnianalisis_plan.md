# Módulo de Omnianálisis

El objetivo de este plan es diseñar e implementar el módulo de "Omnianálisis" en BioStat. Este módulo funcionará como un sistema experto o asistente inteligente que evaluará automáticamente los datos cargados y, mediante un árbol de decisión, seleccionará y ejecutará las pruebas estadísticas más adecuadas, generando finalmente un informe interpretativo.

## User Review Required

> [!IMPORTANT]
> Revisa la lógica del árbol de decisión inicial propuesta a continuación. ¿Estás de acuerdo con los criterios para diferenciar los datos (ej. normalidad con Shapiro-Wilk) o prefieres incluir otras validaciones antes de generar el informe?

## Propuesta de Arquitectura y Lógica (Árbol de Algoritmos)

El módulo actuará sobre los datos seleccionados por el usuario y realizará las siguientes comprobaciones en cadena:

1.  **Detección del Tipo de Datos:**
    *   Determinar si las variables son continuas, ordinales o categóricas/nominales en base a los valores únicos y tipos de datos (dtypes).
2.  **Evaluación de Supuestos (Si los datos son continuos):**
    *   **Normalidad:** Prueba de Shapiro-Wilk.
    *   **Homocedasticidad (Igualdad de varianzas):** Prueba de Levene (si se comparan grupos).
3.  **Selección Automática de Pruebas (Árbol de decisión de ejemplo):**
    *   *1 grupo, continuo, normal:* Prueba T para una muestra.
    *   *1 grupo, continuo, no normal:* Prueba de Wilcoxon.
    *   *2 grupos independientes, continuo, normal, varianzas iguales:* Prueba T de Student.
    *   *2 grupos independientes, continuo, normal, varianzas distintas:* Prueba T de Welch.
    *   *2 grupos independientes, continuo, no normal:* U de Mann-Whitney.
    *   *Variables categóricas:* Chi-cuadrado o Test Exacto de Fisher.
4.  **Generación de Informe:**
    *   Compilar los resultados de los estadísticos descriptivos, los supuestos probados y las conclusiones de las pruebas aplicadas en un texto de fácil comprensión y con un formato limpio.

## Cambios Propuestos

### Módulo Principal de Omnianálisis

#### [NEW] [omni_analyzer.py](file:///C:/Users/Laboratorio2/.gemini/antigravity/scratch/BioStat/src/analysis/omni_analyzer.py)
Creación de la lógica backend (funciones y árbol de decisión) para procesar un DataFrame o series de pandas, determinar los tipos de variables, ejecutar las pruebas pertinentes (usando scipy y statsmodels) y devolver un objeto estructurado con los resultados.

#### [NEW] [omni_panel.py](file:///C:/Users/Laboratorio2/.gemini/antigravity/scratch/BioStat/src/ui/omni_panel.py)
Creación de la interfaz gráfica de usuario (GUI) para el Omnianálisis. Contendrá:
- Selector de variables a analizar.
- Botón "Ejecutar Omnianálisis".
- Un área de texto enriquecido (o HTML) para visualizar el informe generado con las conclusiones y correlaciones.

### Integración en la Interfaz Principal

#### [MODIFY] [main_window.py](file:///C:/Users/Laboratorio2/.gemini/antigravity/scratch/BioStat/src/ui/main_window.py)
Añadir una pestaña o acceso en la barra de herramientas principal para el panel de "Omnianálisis".

## Verificación

### Automated Tests
- Se escribirán pruebas unitarias en `tests/test_omni_analyzer.py` pasándole conjuntos de datos ficticios (normales, no normales, categóricos) para validar que el algoritmo selecciona las pruebas correctas y no se producen excepciones.
- Ejecutar `python -m pytest tests/`

### Manual Verification
- Cargar un dataset clínico de prueba (ej. un CSV con distintas variables).
- Ejecutar el Omnianálisis y revisar que el informe generado sea preciso y tenga sentido clínico.
