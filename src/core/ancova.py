"""ANCOVA de una via (statsmodels, sumas de cuadrados tipo II).

La version anterior era casera y tenia tres defectos (auditoria 2026-09, K4):
la pendiente de la covariable salia de la regresion TOTAL y no de la
intragrupo, las medias ajustadas tenian el signo invertido, y la SS del error se
obtenia por resta y podia salir negativa. Contra statsmodels daba F = 168,6
donde corresponde 4,67. Ahora se ajusta el modelo lineal y ~ grupo + covariable,
como ya se hace con la ANOVA de dos vias.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.formula.api import ols


def ancova(dependent, group, covariate):
    """ANCOVA de una via: diferencias entre grupos ajustadas por una covariable.

    Args:
        dependent: variable respuesta (continua).
        group: factor de grupo (categorico).
        covariate: covariable continua.

    Returns:
        dict con F y p del grupo (ajustado por la covariable), F y p de la
        covariable, eta cuadrado parcial, SS tipo II, medias ajustadas a la media
        de la covariable, y la prueba de paralelismo (interaccion grupo x
        covariable), que es el supuesto central del metodo.
    """
    df = pd.DataFrame({
        "y": pd.to_numeric(pd.Series(np.asarray(dependent)), errors="coerce"),
        "g": pd.Series(np.asarray(group)).astype(object),
        "x": pd.to_numeric(pd.Series(np.asarray(covariate)), errors="coerce"),
    })
    df = df[np.isfinite(df["y"]) & np.isfinite(df["x"]) & df["g"].notna()]
    df["g"] = df["g"].astype(str)
    k = df["g"].nunique()
    n = len(df)
    if k < 2:
        return {"error": "Hace falta al menos 2 grupos para una ANCOVA."}
    if n - k - 1 <= 0:
        return {"error": f"Con {n} observaciones y {k} grupos no queda ningun grado de "
                         f"libertad para estimar el error."}
    if np.ptp(df["x"]) == 0:
        return {"error": "La covariable es constante: no hay nada por lo cual ajustar."}

    modelo = ols("y ~ C(g) + x", data=df).fit()
    aov = sm.stats.anova_lm(modelo, typ=2)
    ss_g, ss_x, ss_e = (float(aov.loc["C(g)", "sum_sq"]), float(aov.loc["x", "sum_sq"]),
                        float(aov.loc["Residual", "sum_sq"]))

    # Medias ajustadas: la prediccion de cada grupo en la media GENERAL de la
    # covariable (media marginal estimada).
    xbar = float(df["x"].mean())
    niveles = sorted(df["g"].unique())
    pred = modelo.predict(pd.DataFrame({"g": niveles, "x": [xbar] * len(niveles)}))
    medias_ajustadas = {nivel: float(v) for nivel, v in zip(niveles, pred)}

    # Paralelismo: si la covariable pesa distinto en cada grupo, "ajustar" por
    # ella no tiene un solo sentido y la comparacion de medias ajustadas depende
    # de en que valor de la covariable se mire.
    avisos = []
    p_inter = np.nan
    try:
        completo = sm.stats.anova_lm(ols("y ~ C(g) * x", data=df).fit(), typ=2)
        p_inter = float(completo.loc["C(g):x", "PR(>F)"])
    except Exception:
        pass
    if np.isfinite(p_inter) and p_inter < 0.05:
        avisos.append(f"Las pendientes de la covariable no son paralelas entre grupos "
                      f"(interaccion grupo x covariable, p={p_inter:.4f}): el supuesto "
                      f"de la ANCOVA no se cumple y la diferencia ajustada depende del "
                      f"valor de la covariable en que se mire.")

    return {
        "F": float(aov.loc["C(g)", "F"]), "p": float(aov.loc["C(g)", "PR(>F)"]),
        "df_group": int(aov.loc["C(g)", "df"]), "df_error": int(aov.loc["Residual", "df"]),
        "F_covariate": float(aov.loc["x", "F"]), "p_covariate": float(aov.loc["x", "PR(>F)"]),
        "eta_squared": ss_g / (ss_g + ss_e) if (ss_g + ss_e) > 0 else np.nan,
        "ss_group": ss_g, "ss_covariate": ss_x, "ss_error": ss_e,
        "pendiente_covariable": float(modelo.params["x"]),
        "medias_ajustadas": medias_ajustadas, "media_covariable": xbar,
        "p_interaccion": p_inter, "avisos": avisos, "n": n, "k": k,
    }
