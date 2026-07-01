# BioStat — Handoff / Dónde seguir

> Última actualización: **2026-07-01**. Lee esto primero para retomar el trabajo.

## Qué se hizo en esta sesión

Se implementó y completó el **Motor de Omnianálisis** (sistema experto estadístico
con árbol de decisión determinista). Antes solo existía el plan en
`docs/omnianalisis_plan.md`; ahora está el código completo según la spec técnica
`docs/omnianalisis_spec.md`.

### Archivos nuevos
- `src/analysis/omni_config.py` — parámetros configurables (Anexo A de la spec:
  `ALPHA`, `SHAPIRO_MAX`, `TUKEY_K`, `FISHER_MIN_FREQ`, `CORR_MIN_COMPARACION`,
  pesos de score, `FDR_METHOD`, etc.). **Ningún umbral está hardcodeado.**
- `src/analysis/omni_analyzer.py` — motor de decisión.
- `src/ui/omni_panel.py` — panel UI (pestaña "Omnianálisis") + ventana de
  confirmación de comparación de métodos (`ComparisonConfirmDialog`).
- `tests/test_omni_analyzer.py` — 24 tests.

### Archivos modificados
- `src/ui/main_window.py` — pestaña "Omnianálisis" (índice 4).
- `src/core/passing_bablok.py` — agregado `ci_intercept` (IC del intercepto).

## Arquitectura del motor (`run_omnianalysis`)

```
DATASET → PERFILADO (tipos + estructura)  ← corre siempre
        → switch por nº columnas:
            1  → Rama A (univariado)
            2  → Rama B (univariado ×2 + bivariado)
            3+ → Rama C (todo B + matriz correlación + FDR + regresión múltiple / PCA)
```

- **Perfilado:** clasifica cada columna (continua / discreta / nominal / ordinal /
  binaria / fecha / ambiguo) + métricas estructurales (n, nulos, duplicados).
- **Supuestos ANTES del test** en cada nodo param/no-param:
  Shapiro-Wilk (n≤5000) o Anderson-Darling; Levene para homocedasticidad.
- **Matriz bivariada:** Pearson/Spearman · t-Student/Welch/Mann-Whitney ·
  ANOVA/Kruskal-Wallis (+post-hoc Tukey/Dunn solo si el test global es significativo) ·
  Chi²/Fisher (regla de frecuencia esperada).
- **Comparación de métodos:** score por reglas duras → `ComparisonConfirmDialog`
  (el humano confirma) → sub-árbol de concordancia:
  Bland-Altman param/no-param **sobre las diferencias**, Passing-Bablok (con IC de
  pendiente e intercepto) o Deming, CCC de Lin. Botón "marcar par como comparable"
  para override manual.
- **Advertencias activas:** media vs mediana, OLS inapropiado, Pearson ≠ acuerdo.
- **Rama C:** matriz de correlación (método correcto celda por celda) + corrección
  Benjamini-Hochberg (FDR) + regresión múltiple con VIF y diagnóstico de residuos,
  o PCA+KMeans (silueta) si no hay variable objetivo.
- **Trazabilidad:** cada bloque registra `traza` (pasos de decisión),
  `advertencias`, `pruebas`, `resultados`, `conclusion`.

## Estado

- ✅ **45 tests pasan** (`pytest tests/`).
- ✅ Todos los módulos importan; la app arranca.
- ✅ Deps instaladas en el entorno: `statsmodels`, `scikit-learn`, `lifelines`,
  `qtawesome`, `reportlab`, `python-docx`, `seaborn` (estaban en requirements.txt
  pero faltaban en el entorno local).
- 🔨 Build del `.exe` (PyInstaller onefile) ejecutado con `python build_exe.py`
  → genera `dist/BioStat.exe` y lo copia al Escritorio.

## Cómo correr / probar / compilar

```bash
# Python del entorno:
# C:\Users\dubed\AppData\Local\Python\pythoncore-3.14-64\python.exe

# Correr la app
python main.py

# Tests
python -m pytest tests/ -q

# Compilar ejecutable
python build_exe.py     # → dist/BioStat.exe + copia al Escritorio
```

## Dónde seguir (pendientes)

1. **Prueba manual del panel Omnianálisis:** cargar un CSV clínico real, verificar
   que el informe HTML y la ventana de confirmación se ven/comportan bien. Los
   tests cubren la lógica, no el render visual de Qt.
2. **Calibrar los pesos del score de comparación** (`SCORE_UMBRAL_COMPARACION` y
   `PESO_*` en `omni_config.py`) con datos reales — hoy son valores de partida.
3. **`PESO_UNIDAD`** no se usa aún: no hay metadatos de unidad por columna. Si se
   agregan (p.ej. un dict de unidades), sumar esa regla fuerte al score en
   `_comparison_score`.
4. **Regla `mismo_n && sin_nulos_desalineados`** (`PESO_PAREADO`) tampoco está
   cableada — evaluar si vale la pena.
5. **Series temporales:** el perfilado las detecta y emite advertencia, pero el
   árbol no las analiza (rama futura, Anexo B punto 5 de la spec).
6. **Anderson-Darling** se usa como fallback para n>5000; verificar comportamiento
   con datasets grandes reales.
7. **Passing-Bablok — IC del intercepto:** se deriva de los límites del IC de la
   pendiente (aproximación). Si se requiere rigor, implementar el método exacto de
   la literatura (ver Anexo B punto 1 de la spec).

## Referencias
- Spec técnica: `docs/omnianalisis_spec.md`
- Plan original: `docs/omnianalisis_plan.md`
- Repo: https://github.com/dubeda06-sys/BioStat
