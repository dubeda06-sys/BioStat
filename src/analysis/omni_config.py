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

    # --- Perfilado de tipos ---
    CARDINALITY_THRESHOLD: int = 10  # corte discreta/continua y nominal/ordinal

    # --- Detección de comparación de métodos ---
    CORR_MIN_COMPARACION: float = 0.80   # correlación mínima para sospechar comparación
    SCORE_UMBRAL_COMPARACION: float = 3.0  # puntaje total para gatillar ventana

    # Pesos reglas fuertes
    PESO_UNIDAD: float = 2.0
    PESO_RANGO: float = 1.5
    PESO_ESCALA: float = 1.0
    PESO_CORR: float = 2.0
    # Pesos reglas de apoyo
    PESO_NOMBRE: float = 1.0
    PESO_PAREADO: float = 0.5
    PESO_DIF_CHICA: float = 1.0

    # --- Multiplicidad ---
    FDR_METHOD: str = "fdr_bh"     # Benjamini-Hochberg

    # --- Detección proporcional vs constante (Bland-Altman) ---
    # p del test de pendiente (diff vs mean) bajo el cual la diferencia es proporcional
    PROPORTIONAL_SLOPE_ALPHA: float = 0.05

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
