"""Two-way ANOVA (statsmodels, type-II sum of squares)."""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.formula.api import ols


def two_way_anova(response, factor_a, factor_b):
    """ANOVA de dos vias con interaccion.

    Args:
        response: valores de la variable dependiente (continua).
        factor_a: niveles del factor A (categorico).
        factor_b: niveles del factor B (categorico).

    Returns:
        dict con F, p y gl para Factor A, B e interaccion A*B, mas el error.
        None si no hay replicas suficientes para estimar el error.
    """
    df = pd.DataFrame({
        "y": np.asarray(response, dtype=float),
        "A": np.asarray(factor_a),
        "B": np.asarray(factor_b),
    }).dropna()
    if len(df) < 4 or df["A"].nunique() < 2 or df["B"].nunique() < 2:
        return None

    model = ols("y ~ C(A) + C(B) + C(A):C(B)", data=df).fit()
    aov = sm.stats.anova_lm(model, typ=2)
    if "Residual" not in aov.index or aov.loc["Residual", "df"] <= 0:
        return None  # sin replicas: no se puede estimar el error

    def row(name):
        return (float(aov.loc[name, "F"]), float(aov.loc[name, "PR(>F)"]), int(aov.loc[name, "df"]),
                float(aov.loc[name, "sum_sq"]))

    f_a, p_a, df_a, ss_a = row("C(A)")
    f_b, p_b, df_b, ss_b = row("C(B)")
    f_ab, p_ab, df_ab, ss_ab = row("C(A):C(B)")
    ss_error = float(aov.loc["Residual", "sum_sq"])
    df_error = int(aov.loc["Residual", "df"])

    return {
        "F_A": f_a, "p_A": p_a, "df_A": df_a,
        "F_B": f_b, "p_B": p_b, "df_B": df_b,
        "F_AB": f_ab, "p_AB": p_ab, "df_AB": df_ab,
        "df_error": df_error,
        "ss_A": ss_a, "ss_B": ss_b, "ss_AB": ss_ab, "ss_error": ss_error,
    }
