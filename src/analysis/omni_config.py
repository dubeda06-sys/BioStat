"""Parámetros configurables del motor de Omnianálisis (Anexo A del spec).

Valores de partida razonables — calibrar con datos reales.
No incrustar umbrales en el código: importar desde aquí.
"""
from dataclasses import dataclass, field


@dataclass
class OmniConfig:
    # --- Normalidad / significancia ---
    SHAPIRO_MAX: int = 5000        # n máx para Shapiro-Wilk; sobre esto Anderson-Darling
    ALPHA: float = 0.05            # nivel de significancia

    # --- Outliers ---
    TUKEY_K: float = 1.5           # multiplicador IQR para outliers

    # --- Tablas de contingencia ---
    FISHER_MIN_FREQ: float = 5     # frecuencia esperada mínima antes de saltar Chi²→Fisher
    # Tablas mayores que 2×2 con esperadas chicas: p del chi-cuadrado por
    # permutación. Semilla fija para que la misma tabla dé siempre el mismo p.
    MONTECARLO_N: int = 9999
    MONTECARLO_SEMILLA: int = 20260926

    # --- Perfilado de tipos ---
    CARDINALITY_THRESHOLD: int = 10  # corte discreta/continua y nominal/ordinal

    # --- Detección de comparación de métodos ---
    CORR_MIN_COMPARACION: float = 0.80   # correlación mínima para sospechar comparación
    # Calibrado el 27 sep contra un banco sintético de pares de laboratorio
    # (`tests/test_omni_score_banco.py`): 7 comparaciones de métodos y 9 pares
    # que no lo son. No hay datos reales etiquetados todavía; cuando los haya,
    # se recalibra con el mismo test. Ver el docstring del test.
    SCORE_UMBRAL_COMPARACION: float = 3.5  # puntaje total para gatillar ventana

    # Pesos reglas fuertes
    # La unidad compartida casi no discrimina: en una hoja de laboratorio la
    # mayoría de los analitos están en mg/dL o U/L. Con el 2,0 del spec,
    # glucosa contra colesterol y dos calibradores en Ct pasaban a candidatos.
    # Lo que sí discrimina es la unidad DISTINTA: dos métodos del mismo
    # analito se comparan en la misma unidad.
    PESO_UNIDAD: float = 0.5
    PESO_UNIDAD_DISTINTA: float = 2.0  # se RESTA si las dos declaran unidad y difieren
    PESO_RANGO: float = 1.5
    PESO_ESCALA: float = 1.0
    PESO_CORR: float = 2.0
    # Pesos reglas de apoyo
    PESO_NOMBRE: float = 1.0
    PESO_PAREADO: float = 0.5
    PESO_DIF_CHICA: float = 1.0

    # --- Multiplicidad ---
    FDR_METHOD: str = "fdr_bh"     # Benjamini-Hochberg

    # --- Concordancia: dos preguntas distintas sobre las diferencias ---
    # ¿El sesgo cambia con la concentración? p de la pendiente de la diferencia
    # contra el eje (Bland-Altman). Es informativo: no elige la regresión.
    PROPORTIONAL_SLOPE_ALPHA: float = 0.05
    # ¿La DISPERSIÓN de las diferencias cambia con la concentración? (CLSI
    # EP09c §5.4: DE constante, CV constante o mixta). p de la pendiente de los
    # residuos absolutos contra el eje (Bland y Altman 1999). Esta sí elige la
    # escala del Bland-Altman y la regresión (EP09c §6.2).
    VARIABILIDAD_ALPHA: float = 0.05

    # Umbral de "media de diferencias pequeña" relativo al rango (regla de apoyo)
    DIF_CHICA_FRAC: float = 0.05

    # --- Comparación de métodos (CLSI EP09) ---
    # λ de Deming = razón de varianzas del error analítico X/Y. 1.0 = igual
    # precisión (Deming ortogonal). Ajustar si se conoce la imprecisión de cada método.
    DEMING_LAMBDA: float = 1.0
    # Niveles de decisión médica donde estimar el sesgo desde la recta de
    # regresión. Vacío => se usan los percentiles P25/P50/P75 de los datos.
    DECISION_LEVELS: tuple = ()
    GENERAR_GRAFICOS_COMPARACION: bool = True  # Bland-Altman + regresión (Passing-Bablok/Deming)


DEFAULT_CONFIG = OmniConfig()
