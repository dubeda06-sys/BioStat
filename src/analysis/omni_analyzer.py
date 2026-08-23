"""Motor de Omnianálisis — árbol de decisiones determinista.

Reglas if/then explícitas. Ningún modelo decide qué test correr.
Cada análisis emitido es trazable a la condición que lo gatilló.
Verificación de supuestos SIEMPRE antes de elegir la rama param/no-param.

Spec: docs/omnianalisis_plan.md + omnianalisis_spec.md
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from src.analysis.omni_config import OmniConfig, DEFAULT_CONFIG
from src.core.statistics import (
    descriptive_stats, normality_test, anova_oneway, kruskal_wallis,
    chi_square_test, fisher_exact_test, pearson_r, spearman_rho,
)
from src.core.bland_altman import bland_altman_analysis, concordance_correlation


def _ok(res):
    """True si el core devolvio un resultado usable.

    Ojo: un dict de rechazo {"error": ...} es TRUTHY, asi que `if res:` no
    alcanza; hay que mirar la clave.
    """
    return bool(res) and not (isinstance(res, dict) and res.get("error"))


# ============================================================
#  Registro de ensayos (auditoria)
# ============================================================
# Cada vez que el motor corre un ensayo, o descarta su alternativa, lo anota.
# Se marca EN EL PUNTO donde el ensayo ocurre, no reconstruyendo despues desde
# el texto de la traza: la traza es prosa y cambia; un id no.
#
# Los ids tienen que existir en `omni_catalogo.ENSAYOS`; lo verifica
# `tests/test_omni_catalogo.py` leyendo este archivo.
EJECUTADO = "ejecutado"
DESCARTADO = "descartado"


def _fmt_p(p):
    """p para mostrar. Redondeado a 4 decimales, 3e-9 sale como `0.0`.

    Un p impreso como "0.0" se lee como "p exactamente cero", que no existe.
    Debajo del limite de resolucion se informa como desigualdad.
    """
    if p is None:
        return "n/d"
    p = float(p)
    if p != p:  # NaN
        return "n/d"
    if p < 0.0001:
        return "<0.0001"
    return f"{p:.4f}"


def _p(p):
    """El token completo: `p=0.0345` o `p<0.0001`.

    Concatenar el `=` a mano dejaba `p=<0.0001`, con el igual y el menor
    pegados. El signo es parte del token, asi que lo arma esta funcion.
    """
    texto = _fmt_p(p)
    return f"p{texto}" if texto.startswith("<") else f"p={texto}"


def _marcar(destino: dict, id_: str, detalle: str = ""):
    """Anota que el ensayo `id_` se ejecuto en este bloque."""
    destino.setdefault("ensayos", []).append(
        {"id": id_, "estado": EJECUTADO, "detalle": detalle}
    )


def _detecta_pendiente(s: dict) -> bool:
    """True si el IC 95% de la pendiente excluye el 0: sesgo proporcional detectado.

    Se decide por el intervalo y no por el p para que un IC no finito cuente como
    "no detectado" en vez de propagar una comparacion contra NaN en silencio.
    """
    lo, hi = s.get("ci", (np.nan, np.nan))
    if not (np.isfinite(lo) and np.isfinite(hi)):
        return False
    return not (lo <= 0 <= hi)


def _descartar(destino: dict, id_: str, motivo: str):
    """Anota que el ensayo `id_` NO se corrio, y por que.

    Descartar no es un fallo: es el motor eligiendo la rama correcta. Sin este
    registro, la auditoria no puede separar "el supuesto no se cumplio" de
    "nadie lo evaluo".
    """
    destino.setdefault("ensayos", []).append(
        {"id": id_, "estado": DESCARTADO, "motivo": motivo}
    )


from src.core.passing_bablok import passing_bablok
from src.core.agreement import deming_regression, cv_from_duplicates
from src.core.outliers import tukey_outliers


# ============================================================
#  Tipos de columna
# ============================================================
NUMERIC_CONTINUOUS = "numérica continua"
NUMERIC_DISCRETE = "numérica discreta"
CATEGORICAL_NOMINAL = "categórica nominal"
CATEGORICAL_ORDINAL = "categórica ordinal"
BINARY = "binaria"
DATETIME = "fecha/tiempo"
AMBIGUOUS = "ambiguo"


def _classify_column(series: pd.Series, cfg: OmniConfig) -> dict:
    """Clasifica el tipo de una columna. Devuelve dict con tipo y flags."""
    s = series.dropna()
    n = len(s)
    n_unique = s.nunique()

    info = {"n": int(len(series)), "n_valid": int(n), "n_unique": int(n_unique),
            "pct_null": round(float(series.isna().mean() * 100), 2)}

    if n == 0:
        info["tipo"] = AMBIGUOUS
        info["nota"] = "Columna vacía."
        return info

    # Fecha
    if pd.api.types.is_datetime64_any_dtype(s):
        info["tipo"] = DATETIME
        return info

    is_num = pd.api.types.is_numeric_dtype(s)

    # Binaria (exactamente 2 valores)
    if n_unique == 2:
        info["tipo"] = BINARY
        return info

    if is_num:
        arr = s.to_numpy(dtype=float)
        all_int = np.allclose(arr, np.round(arr))
        non_negative = np.all(arr >= 0)
        # Discreta / conteo: enteros no negativos, cardinalidad moderada
        if all_int and non_negative and n_unique <= cfg.CARDINALITY_THRESHOLD:
            info["tipo"] = NUMERIC_DISCRETE
            return info
        # Zona gris de cardinalidad → ambiguo (pide confirmación)
        if n_unique <= cfg.CARDINALITY_THRESHOLD:
            info["tipo"] = AMBIGUOUS
            info["nota"] = (
                f"Cardinalidad baja ({n_unique} valores únicos): podría ser "
                f"discreta/ordinal codificada. Confirmar tratamiento."
            )
            return info
        info["tipo"] = NUMERIC_CONTINUOUS
        return info

    # No numérica → categórica. Ordinal si el dtype declara orden.
    if isinstance(s.dtype, pd.CategoricalDtype) and s.dtype.ordered:
        info["tipo"] = CATEGORICAL_ORDINAL
    else:
        info["tipo"] = CATEGORICAL_NOMINAL
    return info


def _is_numeric_type(tipo: str) -> bool:
    return tipo in (NUMERIC_CONTINUOUS, NUMERIC_DISCRETE)


def _is_categorical_type(tipo: str) -> bool:
    return tipo in (CATEGORICAL_NOMINAL, CATEGORICAL_ORDINAL, BINARY)


# ============================================================
#  Perfilado (nodo raíz — corre siempre)
# ============================================================
def profile_dataset(df: pd.DataFrame, cols: list[str], cfg: OmniConfig) -> dict:
    """Caracteriza el dataset: tipos por columna + métricas estructurales."""
    col_types = {c: _classify_column(df[c], cfg) for c in cols}

    n_full_dups = int(df.duplicated().sum())
    shape = "transversal"
    # Detección simple de estructura temporal
    if any(col_types[c]["tipo"] == DATETIME for c in cols):
        shape = "serie temporal (sospecha)"

    return {
        "n_columns": len(cols),
        "n_rows": int(len(df)),
        "col_types": col_types,
        "full_duplicates": n_full_dups,
        "shape": shape,
    }


# ============================================================
#  Utilidades de supuestos
# ============================================================
def _normality(arr, cfg: OmniConfig) -> dict:
    """Normalidad con Shapiro-Wilk (n<=SHAPIRO_MAX) o Anderson-Darling."""
    arr = np.asarray(arr, dtype=float)
    arr = arr[~np.isnan(arr)]
    n = len(arr)
    if n < 3:
        return {"normal": True, "test": "n/a", "stat": None, "p": None,
                "nota": "n<3, no evaluable — se asume normal por defecto."}
    if n <= cfg.SHAPIRO_MAX:
        res = normality_test(arr)  # reusa core (Shapiro)
        return {"normal": bool(res["normal"]), "test": "Shapiro-Wilk",
                "stat": round(float(res["w"]), 4), "p": round(float(res["p"]), 4)}
    # Anderson-Darling para n grande
    ad = stats.anderson(arr, dist="norm")
    # comparar estadístico contra valor crítico al 5%
    idx = list(ad.significance_level).index(5.0) if 5.0 in list(ad.significance_level) else 2
    crit = ad.critical_values[idx]
    normal = ad.statistic < crit
    return {"normal": bool(normal), "test": "Anderson-Darling",
            "stat": round(float(ad.statistic), 4), "p": None,
            "critico_5pct": round(float(crit), 4)}


def _levene(groups) -> dict:
    """Homocedasticidad (Levene)."""
    clean = [np.asarray(g, dtype=float) for g in groups]
    clean = [g[~np.isnan(g)] for g in clean]
    clean = [g for g in clean if len(g) >= 2]
    if len(clean) < 2:
        return {"equal_var": True, "stat": None, "p": None, "nota": "no evaluable"}
    stat, p = stats.levene(*clean)
    return {"equal_var": bool(p >= 0.05), "stat": round(float(stat), 4), "p": round(float(p), 4)}


def _fmt_desc(arr) -> dict:
    d = descriptive_stats(arr)
    if d is None:
        return {}
    return {k: (round(float(v), 4) if isinstance(v, (int, float, np.floating)) and not isinstance(v, bool)
                else (tuple(round(float(x), 4) for x in v) if isinstance(v, tuple) else v))
            for k, v in d.items()}


# ============================================================
#  Rama A — univariado
# ============================================================
def _univariate(col: str, series: pd.Series, tipo: str, cfg: OmniConfig) -> dict:
    block = {"titulo": f"Univariado — {col}", "tipo": tipo,
             "traza": [], "advertencias": [], "resultados": {}, "conclusion": "",
             "ensayos": []}
    s = series.dropna()

    if _is_numeric_type(tipo):
        arr = s.to_numpy(dtype=float)
        desc = _fmt_desc(arr)
        block["resultados"]["descriptivos"] = desc
        block["traza"].append(f"Descriptivos calculados (n={desc.get('n')}).")
        _marcar(block, "desc_numericos", f"n={int(desc.get('n') or 0)}")

        norm = _normality(arr, cfg)
        block["resultados"]["normalidad"] = norm
        block["traza"].append(
            f"NODO normalidad ({norm['test']}): stat={norm['stat']}, p={norm['p']} → "
            f"{'normal' if norm['normal'] else 'NO normal'}."
        )
        if norm["test"] == "Shapiro-Wilk":
            _marcar(block, "shapiro", f"W={norm['stat']}, {_p(norm['p'])}")
            _descartar(block, "anderson", f"n={len(arr)} ≤ SHAPIRO_MAX ({cfg.SHAPIRO_MAX})")
        elif norm["test"] == "Anderson-Darling":
            _marcar(block, "anderson", f"A²={norm['stat']}, crítico 5%={norm.get('critico_5pct')}")
            _descartar(block, "shapiro", f"n={len(arr)} > SHAPIRO_MAX ({cfg.SHAPIRO_MAX})")

        if norm["normal"]:
            block["resultados"]["tendencia_central"] = f"MEDIA ± DS = {desc.get('mean')} ± {desc.get('std')}"
            _marcar(block, "central_media", f"{desc.get('mean')} ± {desc.get('std')}")
            _descartar(block, "central_mediana",
                       f"la distribución no se aparta de la normal ({_p(norm['p'])})")
            block["conclusion"] = (
                f"Distribución normal → tendencia central: media {desc.get('mean')} ± {desc.get('std')} (DS). "
                f"IC95%={desc.get('ci95')}."
            )
        else:
            block["resultados"]["tendencia_central"] = (
                f"MEDIANA + IQR = {desc.get('median')} [{desc.get('q25')}–{desc.get('q75')}]"
            )
            _marcar(block, "central_mediana",
                    f"{desc.get('median')} [{desc.get('q25')}–{desc.get('q75')}]")
            _descartar(block, "central_media",
                       f"la distribución se aparta de la normal ({_p(norm['p'])}): "
                       "la media sería engañosa")
            block["advertencias"].append(
                "Distribución NO normal: usar la media como tendencia central sería engañoso. "
                "Reportar mediana + IQR."
            )
            block["conclusion"] = (
                f"Distribución no normal → tendencia central: mediana {desc.get('median')} "
                f"[IQR {desc.get('q25')}–{desc.get('q75')}]."
            )

        # Outliers (Tukey)
        out = tukey_outliers(arr)
        if out is not None:
            n_out = out["n_mild"]
            block["resultados"]["outliers"] = {
                "n_leves": out["n_mild"], "n_extremos": out["n_extreme"],
                "limites_internos": (round(out["lower_inner"], 4), round(out["upper_inner"], 4)),
                "valores_leves": out["outliers_mild"],
            }
            block["traza"].append(
                f"Outliers (Tukey k={cfg.TUKEY_K}): {n_out} leve(s), {out['n_extreme']} extremo(s)."
            )
            _marcar(block, "tukey_outliers",
                    f"{n_out} leve(s), {out['n_extreme']} extremo(s)")
        else:
            _descartar(block, "tukey_outliers", "dispersión no evaluable (IQR nulo o n insuficiente)")
        return block

    # Categórica
    counts = s.value_counts()
    total = int(counts.sum())
    freq = {str(k): {"n": int(v), "%": round(float(v / total * 100), 1)} for k, v in counts.items()}
    block["resultados"]["frecuencias"] = freq
    moda = str(counts.index[0]) if len(counts) else None
    block["resultados"]["moda"] = moda
    # Entropía de Shannon (índice de diversidad)
    p = counts.values / total
    entropy = float(-np.sum(p * np.log2(p))) if total > 0 else 0.0
    block["resultados"]["entropia"] = round(entropy, 4)
    block["traza"].append(f"Tabla de frecuencias ({len(counts)} categorías), moda='{moda}'.")
    _marcar(block, "frecuencias", f"{len(counts)} categorías")
    _marcar(block, "moda", f"'{moda}'")
    _marcar(block, "entropia", f"{round(entropy, 4)} bits")
    block["conclusion"] = f"Variable {tipo}. Moda='{moda}'. {len(counts)} categorías. Entropía={round(entropy,3)} bits."
    return block


# ============================================================
#  Rama B — bivariado (matriz de decisión)
# ============================================================
def _bivariate(c1: str, s1: pd.Series, t1: str,
               c2: str, s2: pd.Series, t2: str, cfg: OmniConfig) -> dict:
    block = {"titulo": f"Bivariado — {c1} × {c2}", "traza": [],
             "advertencias": [], "resultados": {}, "conclusion": "", "pruebas": [],
             "ensayos": []}

    n1_num, n2_num = _is_numeric_type(t1), _is_numeric_type(t2)
    n1_cat, n2_cat = _is_categorical_type(t1), _is_categorical_type(t2)

    # --- numérica × numérica → correlación ---
    if n1_num and n2_num:
        block["tipo"] = "correlación"
        a, b = _align(s1, s2)
        norm1 = _normality(a, cfg)
        norm2 = _normality(b, cfg)
        both_normal = norm1["normal"] and norm2["normal"]
        # Los supuestos quedan estructurados, no solo narrados en la traza:
        # `omni_caso` los relee para contar el caso en castellano. Parsear la
        # prosa de vuelta seria fragil — la prosa cambia, un dict no.
        block["resultados"]["supuestos"] = {
            "normalidad": {c1: norm1, c2: norm2},
            "ambas_normales": both_normal,
            "n_pares": int(len(a)),
        }
        block["traza"].append(
            f"Normalidad {c1}: {'sí' if norm1['normal'] else 'no'} | "
            f"{c2}: {'sí' if norm2['normal'] else 'no'} → "
            f"{'Pearson' if both_normal else 'Spearman'}."
        )
        if both_normal:
            r = pearson_r(a, b)
            block["pruebas"].append({"prueba": "Pearson", "r": round(r["r"], 4),
                                     "r2": round(r["r2"], 4), "p": round(r["p"], 4),
                                     "significativo": r["p"] < cfg.ALPHA})
            _marcar(block, "pearson", f"r={round(r['r'], 4)}, {_p(r['p'])}")
            _descartar(block, "spearman", "ambas variables pasaron la prueba de normalidad")
            block["conclusion"] = (
                f"Ambas normales → Pearson r={round(r['r'],4)}, p={round(r['p'],4)}, "
                f"R²={round(r['r2'],4)}. Asociación lineal "
                f"{'significativa' if r['p']<cfg.ALPHA else 'no significativa'}."
            )
        else:
            r = spearman_rho(a, b)
            block["pruebas"].append({"prueba": "Spearman", "rho": round(r["rho"], 4),
                                     "p": round(r["p"], 4), "significativo": r["p"] < cfg.ALPHA})
            _marcar(block, "spearman", f"rho={round(r['rho'], 4)}, {_p(r['p'])}")
            _descartar(block, "pearson",
                       f"normalidad incumplida ({c1}: {'sí' if norm1['normal'] else 'no'}, "
                       f"{c2}: {'sí' if norm2['normal'] else 'no'})")
            block["conclusion"] = (
                f"No ambas normales → Spearman ρ={round(r['rho'],4)}, p={round(r['p'],4)}. "
                f"Asociación monótona {'significativa' if r['p']<cfg.ALPHA else 'no significativa'}."
            )
        return block

    # --- numérica × categórica → comparación de grupos ---
    if (n1_num and n2_cat) or (n2_num and n1_cat):
        if n1_num:
            num_s, cat_s, num_name = s1, s2, c1
        else:
            num_s, cat_s, num_name = s2, s1, c2
        return _compare_groups(num_name, num_s, cat_s, cfg, block)

    # --- categórica × categórica → contingencia ---
    if n1_cat and n2_cat:
        return _contingency(c1, s1, c2, s2, cfg, block)

    block["tipo"] = "no soportado"
    block["conclusion"] = f"Combinación de tipos ({t1} × {t2}) no cubierta por el árbol."
    return block


def _align(s1: pd.Series, s2: pd.Series):
    df = pd.DataFrame({"a": s1, "b": s2}).dropna()
    return df["a"].to_numpy(dtype=float), df["b"].to_numpy(dtype=float)


def _compare_groups(num_name: str, num_s: pd.Series, cat_s: pd.Series,
                    cfg: OmniConfig, block: dict) -> dict:
    block["tipo"] = "comparación de grupos"
    df = pd.DataFrame({"y": num_s, "g": cat_s}).dropna()
    groups = [g["y"].to_numpy(dtype=float) for _, g in df.groupby("g")]
    labels = [str(k) for k, _ in df.groupby("g")]
    k = len(groups)

    if k < 2:
        block["conclusion"] = "Menos de 2 grupos con datos — sin comparación."
        return block

    norms = [_normality(g, cfg) for g in groups]
    all_normal = all(nn["normal"] for nn in norms)
    lev = _levene(groups)
    block["traza"].append(
        f"Normalidad por grupo: {['sí' if nn['normal'] else 'no' for nn in norms]}."
    )
    block["traza"].append(
        f"Homocedasticidad (Levene): stat={lev['stat']}, p={lev['p']} → "
        f"varianzas {'iguales' if lev['equal_var'] else 'distintas'}."
    )
    _marcar(block, "levene", f"{_p(lev['p'])} → varianzas "
                             f"{'iguales' if lev['equal_var'] else 'distintas'}")
    block["resultados"]["supuestos"] = {
        "k_grupos": k,
        "etiquetas": labels,
        "tamanos": [int(len(g)) for g in groups],
        "normalidad_por_grupo": {lab: nn for lab, nn in zip(labels, norms)},
        "todas_normales": all_normal,
        "levene": lev,
    }

    if k == 2:
        # Los de 3+ grupos no compiten aca: no aplican, no fueron descartados.
        if all_normal:
            equal_var = lev["equal_var"]
            t_stat, t_p = stats.ttest_ind(groups[0], groups[1], equal_var=equal_var)
            name = "t de Student" if equal_var else "t de Welch"
            block["traza"].append(f"2 grupos normales, varianzas {'iguales' if equal_var else 'distintas'} → {name}.")
            block["pruebas"].append({"prueba": name, "estadístico": round(float(t_stat), 4),
                                     "p": round(float(t_p), 4), "significativo": t_p < cfg.ALPHA})
            elegido = "t_student" if equal_var else "t_welch"
            rival = "t_welch" if equal_var else "t_student"
            _marcar(block, elegido, f"t={round(float(t_stat), 4)}, {_p(t_p)}")
            _descartar(block, rival,
                       f"Levene {_p(lev['p'])}: varianzas "
                       f"{'iguales' if equal_var else 'distintas'}")
            _descartar(block, "mann_whitney", "los dos grupos pasaron la prueba de normalidad")
            block["conclusion"] = (
                f"{name}: t={round(t_stat,4)}, p={round(t_p,4)}. Diferencia "
                f"{'significativa' if t_p<cfg.ALPHA else 'no significativa'} (α={cfg.ALPHA})."
            )
        else:
            u_stat, u_p = stats.mannwhitneyu(groups[0], groups[1], alternative="two-sided")
            block["traza"].append("2 grupos no normales → Mann-Whitney U.")
            block["pruebas"].append({"prueba": "Mann-Whitney U", "estadístico": round(float(u_stat), 4),
                                     "p": round(float(u_p), 4), "significativo": u_p < cfg.ALPHA})
            _marcar(block, "mann_whitney", f"U={round(float(u_stat), 4)}, {_p(u_p)}")
            _descartar(block, "t_student", "normalidad incumplida en al menos un grupo")
            _descartar(block, "t_welch", "normalidad incumplida en al menos un grupo")
            block["conclusion"] = (
                f"Mann-Whitney U: U={round(u_stat,4)}, p={round(u_p,4)}. Diferencia "
                f"{'significativa' if u_p<cfg.ALPHA else 'no significativa'} (α={cfg.ALPHA})."
            )
        return block

    # k >= 3 grupos
    if all_normal and lev["equal_var"]:
        av = anova_oneway(groups)
        block["traza"].append(f"{k} grupos normales + homocedásticos → ANOVA.")
        sig = av["p"] < cfg.ALPHA
        block["pruebas"].append({"prueba": "ANOVA una vía", "estadístico": round(float(av["f"]), 4),
                                 "p": round(float(av["p"]), 4), "significativo": sig})
        _marcar(block, "anova", f"F={round(float(av['f']), 4)}, {_p(av['p'])}")
        _descartar(block, "kruskal", "los grupos son normales y homocedásticos")
        block["conclusion"] = (
            f"ANOVA: F={round(av['f'],4)}, p={round(av['p'],4)}. "
            f"{'Al menos un grupo difiere' if sig else 'Sin diferencias'} (α={cfg.ALPHA})."
        )
        if sig:
            posthoc = _tukey_posthoc(df["y"].to_numpy(dtype=float), df["g"].astype(str).to_numpy())
            block["resultados"]["posthoc"] = posthoc
            block["traza"].append("ANOVA significativo → post-hoc Tukey HSD.")
            _marcar(block, "tukey_hsd", f"{k} grupos")
            _descartar(block, "dunn", "el camino fue paramétrico (ANOVA)")
        else:
            _descartar(block, "tukey_hsd",
                       f"ANOVA no significativo ({_p(av['p'])}): "
                       "correr el post-hoc igual inflaría los falsos positivos")
            _descartar(block, "dunn", "el camino fue paramétrico (ANOVA)")
    else:
        kw = kruskal_wallis(groups)
        block["traza"].append(f"{k} grupos no normales/heterocedásticos → Kruskal-Wallis.")
        sig = kw["p"] < cfg.ALPHA
        block["pruebas"].append({"prueba": "Kruskal-Wallis", "estadístico": round(float(kw["h"]), 4),
                                 "p": round(float(kw["p"]), 4), "significativo": sig})
        _marcar(block, "kruskal", f"H={round(float(kw['h']), 4)}, {_p(kw['p'])}")
        _descartar(block, "anova",
                   f"normalidad {'ok' if all_normal else 'incumplida'}, "
                   f"homocedasticidad {'ok' if lev['equal_var'] else 'incumplida'}")
        block["conclusion"] = (
            f"Kruskal-Wallis: H={round(kw['h'],4)}, p={round(kw['p'],4)}. "
            f"{'Al menos un grupo difiere' if sig else 'Sin diferencias'} (α={cfg.ALPHA})."
        )
        if sig:
            block["resultados"]["posthoc"] = _dunn_posthoc(groups, labels, cfg)
            block["traza"].append("Kruskal-Wallis significativo → post-hoc Dunn.")
            _marcar(block, "dunn", f"{k} grupos, Bonferroni")
            _descartar(block, "tukey_hsd", "el camino fue no paramétrico (Kruskal-Wallis)")
        else:
            _descartar(block, "dunn",
                       f"Kruskal-Wallis no significativo ({_p(kw['p'])})")
            _descartar(block, "tukey_hsd", "el camino fue no paramétrico (Kruskal-Wallis)")
    return block


def _tukey_posthoc(y, g):
    try:
        from statsmodels.stats.multicomp import pairwise_tukeyhsd
        res = pairwise_tukeyhsd(y, g)
        return {"metodo": "Tukey HSD", "resumen": str(res)}
    except Exception as e:
        return {"metodo": "Tukey HSD", "error": str(e)}


def _dunn_posthoc(groups, labels, cfg: OmniConfig):
    """Dunn con corrección Bonferroni (implementación mínima con Mann-Whitney)."""
    pairs = []
    raw_p = []
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            try:
                _, p = stats.mannwhitneyu(groups[i], groups[j], alternative="two-sided")
            except ValueError:
                p = 1.0
            pairs.append((labels[i], labels[j]))
            raw_p.append(p)
    m = len(raw_p)
    adj = [min(p * m, 1.0) for p in raw_p]  # Bonferroni
    return {"metodo": "Dunn (Bonferroni)",
            "comparaciones": [{"par": f"{a} vs {b}", "p": round(p, 4), "p_adj": round(pa, 4),
                               "significativo": pa < cfg.ALPHA}
                              for (a, b), p, pa in zip(pairs, raw_p, adj)]}


def _contingency(c1, s1, c2, s2, cfg: OmniConfig, block: dict) -> dict:
    block["tipo"] = "tabla de contingencia"
    ct = pd.crosstab(s1.dropna(), s2.dropna())
    block["resultados"]["tabla"] = ct.to_dict()
    chi = chi_square_test(ct.values)
    if chi is None:
        block["conclusion"] = "Tabla degenerada — sin prueba."
        return block
    expected = np.asarray(chi["expected"])
    min_exp = float(np.min(expected))
    use_fisher = ct.shape == (2, 2) and min_exp < cfg.FISHER_MIN_FREQ
    block["resultados"]["supuestos"] = {
        "esperada_minima": round(min_exp, 2),
        "umbral": cfg.FISHER_MIN_FREQ,
        "forma": (int(ct.shape[0]), int(ct.shape[1])),
        "n_total": int(ct.values.sum()),
    }
    block["traza"].append(
        f"Frecuencia esperada mínima={round(min_exp,2)} "
        f"({'<' if min_exp < cfg.FISHER_MIN_FREQ else '≥'} {cfg.FISHER_MIN_FREQ}) → "
        f"{'Fisher' if use_fisher else 'Chi-cuadrado'}."
    )
    if use_fisher:
        (a, b), (c, d) = ct.values
        fe = fisher_exact_test(int(a), int(b), int(c), int(d))
        block["pruebas"].append({"prueba": "Test exacto de Fisher", "p": round(float(fe["p"]), 4),
                                 "odds_ratio": round(float(fe["odds_ratio"]), 4),
                                 "significativo": fe["p"] < cfg.ALPHA})
        _marcar(block, "fisher", f"{_p(fe['p'])}, "
                                 f"OR={round(float(fe['odds_ratio']), 4)}")
        _descartar(block, "chi2",
                   f"frecuencia esperada mínima {round(min_exp, 2)} < "
                   f"{cfg.FISHER_MIN_FREQ}: la aproximación chi-cuadrado no vale")
        block["conclusion"] = (
            f"Fisher (2x2, esperadas<{cfg.FISHER_MIN_FREQ}): p={round(fe['p'],4)}, "
            f"OR={round(fe['odds_ratio'],4)}. Asociación "
            f"{'significativa' if fe['p']<cfg.ALPHA else 'no significativa'}."
        )
    else:
        block["pruebas"].append({"prueba": "Chi-cuadrado", "estadístico": round(float(chi["chi2"]), 4),
                                 "gl": int(chi["df"]), "p": round(float(chi["p"]), 4),
                                 "significativo": chi["p"] < cfg.ALPHA})
        _marcar(block, "chi2", f"χ²={round(float(chi['chi2']), 4)}, gl={int(chi['df'])}, "
                               f"{_p(chi['p'])}")
        _descartar(block, "fisher",
                   f"esperada mínima {round(min_exp, 2)} ≥ {cfg.FISHER_MIN_FREQ}"
                   + ("" if ct.shape == (2, 2) else f"; además la tabla es {ct.shape[0]}×{ct.shape[1]}, no 2×2"))
        block["conclusion"] = (
            f"Chi-cuadrado: χ²={round(chi['chi2'],4)}, gl={chi['df']}, p={round(chi['p'],4)}. "
            f"Asociación {'significativa' if chi['p']<cfg.ALPHA else 'no significativa'}."
        )
    return block


# ============================================================
#  Detección de comparación de métodos (reglas duras + score)
# ============================================================
def _comparison_score(c1, s1, c2, s2, cfg: OmniConfig) -> dict:
    a, b = _align(s1, s2)
    if len(a) < 3:
        return {"score": 0, "reasons": [], "corr": None}
    score = 0.0
    reasons = []

    r = float(np.corrcoef(a, b)[0, 1])

    # rangos solapados
    lo1, hi1, lo2, hi2 = a.min(), a.max(), b.min(), b.max()
    overlap = max(0, min(hi1, hi2) - max(lo1, lo2))
    span = max(hi1, hi2) - min(lo1, lo2)
    if span > 0 and overlap / span > 0.5:
        score += cfg.PESO_RANGO
        reasons.append(f"rangos solapados ([{round(lo1,2)}–{round(hi1,2)}] vs [{round(lo2,2)}–{round(hi2,2)}])")

    # mismo orden de magnitud
    m1, m2 = np.mean(np.abs(a)) + 1e-9, np.mean(np.abs(b)) + 1e-9
    if 0.5 <= m1 / m2 <= 2.0:
        score += cfg.PESO_ESCALA
        reasons.append("escala similar")

    # correlación alta
    if abs(r) >= cfg.CORR_MIN_COMPARACION:
        score += cfg.PESO_CORR
        reasons.append(f"correlación alta (r={round(r,3)})")

    # nombres similares
    if _similar_names(c1, c2):
        score += cfg.PESO_NOMBRE
        reasons.append("nombres de columna parecidos")

    # media de diferencias pequeña relativa al rango
    mean_diff = abs(np.mean(a - b))
    if span > 0 and mean_diff < cfg.DIF_CHICA_FRAC * span:
        score += cfg.PESO_DIF_CHICA
        reasons.append("media de diferencias pequeña")

    return {"score": round(score, 2), "reasons": reasons, "corr": round(r, 4)}


def _similar_names(c1: str, c2: str) -> bool:
    import difflib
    a, b = c1.lower(), c2.lower()
    # quitar sufijos numéricos comunes (metodo1/metodo2, a/b)
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    return ratio >= 0.6


def detect_comparison_candidates(df: pd.DataFrame, num_cols: list[str], cfg: OmniConfig) -> list[dict]:
    """Corre reglas duras sobre todos los pares numéricos. Devuelve candidatos sobre umbral."""
    candidates = []
    for i in range(len(num_cols)):
        for j in range(i + 1, len(num_cols)):
            c1, c2 = num_cols[i], num_cols[j]
            sc = _comparison_score(c1, df[c1], c2, df[c2], cfg)
            if sc["score"] >= cfg.SCORE_UMBRAL_COMPARACION:
                candidates.append({"col1": c1, "col2": c2, **sc})
    return candidates


# ============================================================
#  Sub-árbol de concordancia (comparación de métodos confirmada)
# ============================================================
def concordance_analysis(c1: str, s1: pd.Series, c2: str, s2: pd.Series, cfg: OmniConfig,
                         referencia: str | None = None) -> dict:
    """Sub-arbol de concordancia para un par confirmado.

    referencia: nombre de la columna que es el metodo de REFERENCIA (valor
        asignado, consenso, material de control), o None si los dos metodos
        son pares. Se recibe el NOMBRE y no "x"/"y" porque el par viaja
        ordenado alfabeticamente desde `run_omnianalysis`, y con "x"/"y" la
        referencia terminaria colgada de la columna equivocada.
    """
    block = {"titulo": f"Concordancia de métodos — {c1} vs {c2}", "tipo": "concordancia",
             "traza": [], "advertencias": [], "resultados": {}, "conclusion": "", "pruebas": [],
             "ensayos": []}
    a, b = _align(s1, s2)
    if len(a) < 3:
        block["conclusion"] = "n<3 — sin concordancia."
        return block

    diffs = a - b
    means = (a + b) / 2
    ref_arg = "x" if referencia == c1 else ("y" if referencia == c2 else None)

    # 1) NODO estructura de la diferencia (regresión de la diferencia contra el eje).
    # El eje es el promedio solo cuando NO hay referencia declarada. Con una
    # referencia hay que regresar contra ella: contra el promedio, el ruido del
    # metodo en prueba entra en los dos lados de la cuenta y fabrica pendiente.
    # Dejar este nodo contra el promedio y el de Bland-Altman contra la
    # referencia hacia que el informe se contradijera consigo mismo.
    eje_estructura = {"x": a, "y": b}.get(ref_arg, means)
    eje_nombre = referencia if ref_arg else "el promedio"
    # Por nombre y no por posicion: linregress devuelve
    # (slope, intercept, rvalue, pvalue, stderr), y el desempaquetado posicional
    # que habia aca metia el STDERR en p_slope. Toda la rama de "diferencia
    # proporcional" — y con ella la eleccion entre Deming y Passing-Bablok —
    # venia decidiendose comparando un error estandar contra 0,05.
    lr_estructura = stats.linregress(eje_estructura, diffs)
    slope, intercept, p_slope = (lr_estructura.slope, lr_estructura.intercept,
                                 lr_estructura.pvalue)
    proporcional = p_slope < cfg.PROPORTIONAL_SLOPE_ALPHA
    block["traza"].append(
        f"NODO estructura: pendiente(diff~{eje_nombre})={round(slope,4)}, "
        f"p={round(p_slope,4)} → diferencia "
        f"{'PROPORCIONAL (usar % / log)' if proporcional else 'CONSTANTE (absolutas)'}."
    )
    block["resultados"]["estructura_diferencia"] = (
        "proporcional" if proporcional else "constante"
    )
    _marcar(block, "estructura_diferencia",
            f"contra {eje_nombre}: pendiente={round(slope, 4)}, {_p(p_slope)} → "
            f"{'proporcional' if proporcional else 'constante'}")

    # 2) NODO normalidad de las DIFERENCIAS (no de datos crudos)
    norm_diff = _normality(diffs, cfg)
    block["traza"].append(
        f"NODO normalidad de DIFERENCIAS ({norm_diff['test']}): p={norm_diff['p']} → "
        f"{'normal' if norm_diff['normal'] else 'NO normal'}."
    )
    _marcar(block, "normalidad_diferencias",
            f"{norm_diff['test']}, {_p(norm_diff['p'])} → "
            f"{'normales' if norm_diff['normal'] else 'NO normales'}")
    block["resultados"]["supuestos"] = {
        "n_pares": int(len(a)),
        # Nombre sin "mean": con una referencia declarada el eje NO es el promedio.
        "eje_estructura": eje_nombre,
        "pendiente_estructura": round(float(slope), 4),
        "p_pendiente": round(float(p_slope), 4),
        "proporcional": bool(proporcional),
        "normalidad_diferencias": norm_diff,
    }
    ba = bland_altman_analysis(a, b, reference=ref_arg)
    if not _ok(ba):
        block["resultados"]["bland_altman"] = {"error": ba.get("error") if isinstance(ba, dict)
                                               else "No se pudo calcular Bland-Altman."}
        block["advertencias"].append(block["resultados"]["bland_altman"]["error"])
        return block
    if norm_diff["normal"]:
        block["resultados"]["bland_altman"] = {
            "tipo": "paramétrico",
            "sesgo": round(ba["mean_difference"], 4),
            "loa_inferior": round(ba["loa_lower"], 4),
            "loa_superior": round(ba["loa_upper"], 4),
            "ic_sesgo": tuple(round(x, 4) for x in ba["ci_mean"]),
        }
        block["traza"].append("Diferencias normales → Bland-Altman PARAMÉTRICO (sesgo ± 1.96·DS).")
        _marcar(block, "ba_parametrico",
                f"sesgo={round(ba['mean_difference'], 4)}, "
                f"LoA [{round(ba['loa_lower'], 4)}, {round(ba['loa_upper'], 4)}]")
        _descartar(block, "ba_no_parametrico",
                   f"las diferencias pasaron la prueba de normalidad ({_p(norm_diff['p'])})")
    else:
        lo = float(np.percentile(diffs, 2.5))
        hi = float(np.percentile(diffs, 97.5))
        block["resultados"]["bland_altman"] = {
            "tipo": "no paramétrico",
            "sesgo_mediana": round(float(np.median(diffs)), 4),
            "loa_inferior_p2.5": round(lo, 4),
            "loa_superior_p97.5": round(hi, 4),
        }
        block["advertencias"].append(
            "Diferencias NO normales: Bland-Altman paramétrico sería incorrecto. "
            "Se usan percentiles empíricos 2.5/97.5."
        )
        block["traza"].append("Diferencias NO normales → Bland-Altman NO PARAMÉTRICO (percentiles).")
        _marcar(block, "ba_no_parametrico",
                f"mediana={round(float(np.median(diffs)), 4)}, "
                f"P2,5/P97,5 [{round(lo, 4)}, {round(hi, 4)}]")
        _descartar(block, "ba_parametrico",
                   f"las diferencias NO son normales ({_p(norm_diff['p'])}): los LoA "
                   "paramétricos serían incorrectos")

    # 2b) NODO eje X: promedio (Bland-Altman clasico) o referencia (Krouwer).
    # El promedio mete la referencia en los dos ejes y atenua la pendiente. Se
    # informan las dos para que la atenuacion se vea, no se afirme.
    ba_res = block["resultados"]["bland_altman"]
    ba_res["eje_x"] = (f"{referencia} (método de referencia)" if ref_arg
                       else "promedio de ambos métodos")
    if not ref_arg:
        _descartar(block, "ba_eje_referencia",
                   "ninguna columna se declaró método de referencia: se grafica "
                   "contra el promedio (Bland-Altman clásico)")
    else:
        p_prom = float(ba["slope_vs_mean"]["slope"])
        p_ref = float(ba["slope_vs_reference"]["slope"])
        if np.isfinite(p_prom) and np.isfinite(p_ref):
            ba_res["pendiente_vs_promedio"] = round(p_prom, 4)
            ba_res["pendiente_vs_referencia"] = round(p_ref, 4)
            ba_res["promedio_atenua"] = bool(abs(p_prom) < abs(p_ref))
            # La atenuacion casi siempre existe, pero suele ser minuscula. Avisar
            # cada vez la vuelve ruido y entrena a ignorarla. El aviso se reserva
            # para cuando los dos ejes NO llevan a la misma conclusion: ahi el
            # promedio no achica un numero, cambia lo que se decide.
            det_ref = _detecta_pendiente(ba["slope_vs_reference"])
            det_prom = _detecta_pendiente(ba["slope_vs_mean"])
            cambia = det_ref != det_prom
            ba_res["cambia_la_conclusion"] = bool(cambia)
            detalle = (f"pendiente contra {referencia}={round(p_ref, 4)}, "
                       f"contra el promedio={round(p_prom, 4)}"
                       + ("; el eje cambia la conclusión" if cambia else
                          "; misma conclusión por los dos ejes"))
            _marcar(block, "ba_eje_referencia", detalle)
            block["traza"].append(
                f"NODO eje X: {referencia} es el método de referencia → se grafica y "
                f"regresa contra ella, no contra el promedio (Krouwer). {detalle}."
            )
            if cambia:
                quien = (f"solo contra {referencia} se detecta sesgo proporcional"
                         if det_ref else
                         f"el sesgo proporcional aparece solo contra el promedio y "
                         f"no contra {referencia}, o sea que el promedio lo inventa")
                block["advertencias"].append(
                    f"El eje X cambia la conclusión sobre el sesgo proporcional: "
                    f"pendiente contra {referencia} = {round(p_ref, 4)}, contra el "
                    f"promedio = {round(p_prom, 4)}, y {quien}. Se informa la de "
                    f"{referencia}: el promedio contiene a los dos métodos y "
                    f"distorsiona la pendiente en las dos direcciones — la achica "
                    f"cuando el sesgo es real y la infla con el ruido del método en "
                    f"prueba (Krouwer 2008, Stat Med 27:778-780)."
                )
        else:
            _descartar(block, "ba_eje_referencia",
                       "alguna de las dos pendientes no se pudo calcular: hay un eje "
                       "sin variación")

    # 3) Regresión de comparación (CLSI EP09)
    # ~normal + homocedástico → Deming (con λ configurable); si no → Passing-Bablok.
    resid_homoced = not proporcional
    reg_slope = reg_intercept = None
    if norm_diff["normal"] and resid_homoced:
        _descartar(block, "passing_bablok",
                   "diferencias normales y homocedásticas: Deming es más eficiente")
        dem = deming_regression(a, b, lambda_ratio=cfg.DEMING_LAMBDA)
        if not _ok(dem) and isinstance(dem, dict) and dem.get("error"):
            block["advertencias"].append(f"Regresion de Deming: {dem['error']}")
            _descartar(block, "deming", dem["error"])
        if _ok(dem):
            ci_s, ci_i = dem["ci_slope"], dem["ci_intercept"]
            slope_no_prop = ci_s[0] <= 1 <= ci_s[1]
            intercept_no_const = ci_i[0] <= 0 <= ci_i[1]
            reg_slope, reg_intercept = dem["slope"], dem["intercept"]
            block["resultados"]["regresion"] = {
                "metodo": "Deming", "lambda": dem["lambda"],
                "pendiente": round(dem["slope"], 4), "ic_pendiente": tuple(round(x, 4) for x in ci_s),
                "intercepto": round(dem["intercept"], 4), "ic_intercepto": tuple(round(x, 4) for x in ci_i),
                "r2": round(dem["r2"], 4),
                "sesgo_proporcional": not slope_no_prop,
                "sesgo_constante": not intercept_no_const,
            }
            _marcar(block, "deming",
                    f"pendiente={round(dem['slope'], 4)}, intercepto={round(dem['intercept'], 4)}, "
                    f"λ={dem['lambda']}")
            block["traza"].append(
                f"Diferencias normales + homocedásticas → Deming (λ={dem['lambda']}). "
                f"IC pendiente {tuple(round(x,4) for x in ci_s)} "
                f"{'incluye' if slope_no_prop else 'NO incluye'} 1 → "
                f"{'sin' if slope_no_prop else 'HAY'} sesgo proporcional. "
                f"IC intercepto {tuple(round(x,4) for x in ci_i)} "
                f"{'incluye' if intercept_no_const else 'NO incluye'} 0 → "
                f"{'sin' if intercept_no_const else 'HAY'} sesgo constante."
            )
    else:
        # Deming exige las dos cosas; decir cual de las dos fallo, no las dos.
        faltantes = []
        if not norm_diff["normal"]:
            faltantes.append(f"las diferencias no son normales ({_p(norm_diff['p'])})")
        if not resid_homoced:
            faltantes.append(f"la diferencia es proporcional al promedio ({_p(p_slope)}): "
                             "error heterocedástico")
        _descartar(block, "deming", "Deming asume normalidad y homocedasticidad; " +
                                    " y ".join(faltantes))
        pb = passing_bablok(a, b)
        if not _ok(pb) and isinstance(pb, dict) and pb.get("error"):
            block["advertencias"].append(f"Passing-Bablok: {pb['error']}")
            _descartar(block, "passing_bablok", pb["error"])
        elif _ok(pb) and pb.get("avisos"):
            block["advertencias"].extend(pb["avisos"])
        if _ok(pb):
            ci_s = pb["ci_slope"]
            ci_i = pb["ci_intercept"]
            slope_no_prop = ci_s[0] <= 1 <= ci_s[1]
            intercept_no_const = ci_i[0] <= 0 <= ci_i[1]
            reg_slope, reg_intercept = pb["slope"], pb["intercept"]
            block["resultados"]["regresion"] = {
                "metodo": "Passing-Bablok",
                "pendiente": round(pb["slope"], 4), "ic_pendiente": tuple(round(x, 4) for x in ci_s),
                "intercepto": round(pb["intercept"], 4), "ic_intercepto": tuple(round(x, 4) for x in ci_i),
                "sesgo_proporcional": not slope_no_prop,
                "sesgo_constante": not intercept_no_const,
            }
            _marcar(block, "passing_bablok",
                    f"pendiente={round(pb['slope'], 4)}, intercepto={round(pb['intercept'], 4)}")
            block["traza"].append(
                f"Sin distribución asumida / outliers → Passing-Bablok. "
                f"IC pendiente {tuple(round(x,4) for x in ci_s)} "
                f"{'incluye' if slope_no_prop else 'NO incluye'} 1 → "
                f"{'sin' if slope_no_prop else 'HAY'} sesgo proporcional. "
                f"IC intercepto {tuple(round(x,4) for x in ci_i)} "
                f"{'incluye' if intercept_no_const else 'NO incluye'} 0 → "
                f"{'sin' if intercept_no_const else 'HAY'} sesgo constante."
            )

    # 3b) Sesgo estimado en niveles de decisión médica (desde la recta EP09)
    if reg_slope is not None:
        levels = list(cfg.DECISION_LEVELS) if cfg.DECISION_LEVELS else \
            [float(np.percentile(a, q)) for q in (25, 50, 75)]
        sesgo_niveles = []
        for L in levels:
            pred = reg_slope * L + reg_intercept
            sesgo_niveles.append({
                "nivel": round(float(L), 4),
                "sesgo_abs": round(float(pred - L), 4),
                "sesgo_pct": round(float((pred - L) / L * 100), 2) if L != 0 else None,
            })
        block["resultados"]["sesgo_en_niveles"] = sesgo_niveles
        block["traza"].append(
            "Sesgo estimado en niveles de decisión (desde la recta): " +
            "; ".join(f"X={s['nivel']}→{s['sesgo_abs']}" for s in sesgo_niveles) + "."
        )
        _marcar(block, "sesgo_niveles", f"{len(sesgo_niveles)} nivel(es)")
    else:
        _descartar(block, "sesgo_niveles",
                   "no hubo recta de comparación: sin ella no hay sesgo que estimar")

    # 3c) Datos para graficar (Bland-Altman + regresión) — los usa la UI
    if cfg.GENERAR_GRAFICOS_COMPARACION:
        ba_res_tmp = block["resultados"]["bland_altman"]
        block["resultados"]["_plot"] = {
            "x": np.asarray(a, dtype=float),
            "y": np.asarray(b, dtype=float),
            "nombre_x": c1, "nombre_y": c2,
            "ba_tipo": ba_res_tmp["tipo"],
            "sesgo": ba_res_tmp.get("sesgo", ba_res_tmp.get("sesgo_mediana")),
            "loa": (ba_res_tmp.get("loa_inferior", ba_res_tmp.get("loa_inferior_p2.5")),
                    ba_res_tmp.get("loa_superior", ba_res_tmp.get("loa_superior_p97.5"))),
            "reg_metodo": block["resultados"].get("regresion", {}).get("metodo"),
            "reg_slope": reg_slope, "reg_intercept": reg_intercept,
        }

    block["advertencias"].append(
        "OLS (regresión lineal ordinaria) es INAPROPIADO para comparar métodos: asume que "
        "X no tiene error. Se usó regresión de errores en ambos ejes."
    )

    # 4) Concordancia global — CCC (NO Pearson), descompuesto en precisión × veracidad
    ccc = concordance_correlation(a, b)
    if not _ok(ccc):
        motivo = ccc.get("error") if isinstance(ccc, dict) else "No se pudo calcular el CCC."
        block["advertencias"].append(f"CCC de Lin: {motivo}")
        _descartar(block, "ccc", motivo)
        _descartar(block, "ccc_descomposicion", "el CCC no se pudo calcular")
        block["conclusion"] = f"Comparacion de metodos incompleta: {motivo}"
        return block
    block["resultados"]["ccc"] = round(ccc["ccc"], 4)
    block["resultados"]["ccc_rho"] = round(ccc["rho"], 4)
    block["resultados"]["ccc_cb"] = round(ccc["cb"], 4)
    block["resultados"]["ccc_fuerza"] = ccc["strength"]
    _marcar(block, "ccc", f"CCC={round(ccc['ccc'], 4)} ({ccc['strength']})")
    if np.isfinite(ccc["ci_low"]):
        block["resultados"]["ccc_ic95"] = (round(ccc["ci_low"], 4), round(ccc["ci_high"], 4))
    block["advertencias"].append(
        "NO usar Pearson como medida de acuerdo: correlación alta ≠ concordancia. "
        f"CCC (Lin) = {round(ccc['ccc'],4)}."
    )
    block["traza"].append(
        f"Concordancia global → CCC de Lin = {round(ccc['ccc'],4)} "
        f"({ccc['strength']}, escala de McBride 2005)."
    )
    # La descomposición CCC = rho × Cb dice DÓNDE está el defecto: rho bajo con Cb
    # alto = problema de dispersión; Cb bajo con rho alto = sesgo sistemático.
    # Son causas distintas y se corrigen por vías distintas (recalibración vs
    # imprecisión analítica), así que conviene decirlo explícito.
    if np.isfinite(ccc["rho"]) and np.isfinite(ccc["cb"]):
        if ccc["cb"] < 0.95 and ccc["rho"] >= 0.95:
            donde = ("el desacuerdo es sobre todo de VERACIDAD (sesgo): Cb="
                     f"{round(ccc['cb'],4)} con rho={round(ccc['rho'],4)} alto. "
                     "Apunta a calibración, no a imprecisión.")
        elif ccc["rho"] < 0.95 and ccc["cb"] >= 0.95:
            donde = ("el desacuerdo es sobre todo de PRECISIÓN (dispersión): rho="
                     f"{round(ccc['rho'],4)} con Cb={round(ccc['cb'],4)} alto. "
                     "Apunta a imprecisión analítica, no a calibración.")
        elif ccc["rho"] < 0.95 and ccc["cb"] < 0.95:
            donde = (f"hay componente de dispersión (rho={round(ccc['rho'],4)}) Y de "
                     f"sesgo (Cb={round(ccc['cb'],4)}).")
        else:
            donde = (f"ambos componentes son altos (rho={round(ccc['rho'],4)}, "
                     f"Cb={round(ccc['cb'],4)}).")
        block["traza"].append("Descomposición CCC = rho × Cb → " + donde)
        _marcar(block, "ccc_descomposicion",
                f"rho={round(ccc['rho'], 4)}, Cb={round(ccc['cb'], 4)}")
    else:
        _descartar(block, "ccc_descomposicion", "rho o Cb no finitos")

    ba_res = block["resultados"]["bland_altman"]
    sesgo = ba_res.get("sesgo", ba_res.get("sesgo_mediana"))
    block["conclusion"] = (
        f"Comparación de métodos: sesgo={sesgo}, CCC={round(ccc['ccc'],4)}, "
        f"estructura {block['resultados']['estructura_diferencia']}. "
        f"Ver Bland-Altman y regresión de comparación arriba."
    )
    return block


# ============================================================
#  Rama C — multiplicidad + matriz de correlación + regresión múltiple
# ============================================================
def _correlation_matrix(df: pd.DataFrame, num_cols: list[str], cfg: OmniConfig) -> dict:
    """Matriz de correlación con método correcto celda por celda + FDR."""
    cells = []
    p_values = []
    for i in range(len(num_cols)):
        for j in range(i + 1, len(num_cols)):
            c1, c2 = num_cols[i], num_cols[j]
            a, b = _align(df[c1], df[c2])
            if len(a) < 3:
                continue
            n1 = _normality(a, cfg)["normal"]
            n2 = _normality(b, cfg)["normal"]
            if n1 and n2:
                res = pearson_r(a, b)
                cells.append({"par": f"{c1} × {c2}", "metodo": "Pearson",
                              "coef": round(res["r"], 4), "p": round(res["p"], 4)})
                p_values.append(res["p"])
            else:
                res = spearman_rho(a, b)
                cells.append({"par": f"{c1} × {c2}", "metodo": "Spearman",
                              "coef": round(res["rho"], 4), "p": round(res["p"], 4)})
                p_values.append(res["p"])
    # FDR Benjamini-Hochberg
    adj = _fdr(p_values, cfg)
    for cell, pa in zip(cells, adj):
        cell["p_adj"] = round(float(pa), 4)
        cell["significativo_adj"] = pa < cfg.ALPHA
    return {"celdas": cells, "n_comparaciones": len(cells)}


def _fdr(p_values, cfg: OmniConfig):
    if not p_values:
        return []
    try:
        from statsmodels.stats.multitest import multipletests
        _, adj, _, _ = multipletests(p_values, alpha=cfg.ALPHA, method=cfg.FDR_METHOD)
        return adj
    except Exception:
        return p_values


def _pca_clustering(df, num_cols, cfg: OmniConfig) -> dict:
    """PCA + clustering exploratorio (muchas numéricas sin objetivo)."""
    try:
        from sklearn.decomposition import PCA
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import silhouette_score
    except Exception as e:
        return {"error": str(e)}
    sub = df[num_cols].dropna()
    if len(sub) < max(10, len(num_cols) + 2):
        return {"error": "n insuficiente para PCA/clustering."}
    X = StandardScaler().fit_transform(sub.to_numpy(dtype=float))

    # PCA
    pca = PCA()
    pca.fit(X)
    evr = pca.explained_variance_ratio_
    cum = np.cumsum(evr)
    n_90 = int(np.searchsorted(cum, 0.90) + 1)
    result = {
        "pca": {
            "varianza_explicada": [round(float(v), 4) for v in evr[:5]],
            "varianza_acumulada": [round(float(v), 4) for v in cum[:5]],
            "componentes_para_90pct": n_90,
        }
    }

    # KMeans — elegir k por silhouette (2..min(6,n-1))
    best = {"k": None, "silhouette": -1.0}
    max_k = min(6, len(sub) - 1)
    for k in range(2, max_k + 1):
        try:
            labels = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(X)
            sil = silhouette_score(X, labels)
            if sil > best["silhouette"]:
                best = {"k": k, "silhouette": round(float(sil), 4)}
        except Exception:
            continue
    result["clustering"] = {
        "metodo": "KMeans (k óptimo por silueta)",
        "k_optimo": best["k"], "silhouette": best["silhouette"],
        "nota": "Exploratorio: los clusters no implican grupos clínicos reales sin validación.",
    }
    return result


def _multiple_regression(df, target, predictors, cfg: OmniConfig) -> dict:
    """Regresión múltiple con diagnóstico de supuestos (VIF, residuos)."""
    try:
        import statsmodels.api as sm
        from statsmodels.stats.outliers_influence import variance_inflation_factor
    except Exception as e:
        return {"error": str(e)}
    sub = df[[target] + predictors].dropna()
    if len(sub) <= len(predictors) + 1:
        return {"error": "n insuficiente para regresión múltiple."}
    y = sub[target].to_numpy(dtype=float)
    X = sub[predictors].to_numpy(dtype=float)
    Xc = sm.add_constant(X)
    model = sm.OLS(y, Xc).fit()
    resid = model.resid
    norm_resid = _normality(resid, cfg)
    # VIF
    vif = {}
    for k, name in enumerate(predictors):
        try:
            vif[name] = round(float(variance_inflation_factor(Xc, k + 1)), 3)
        except Exception:
            vif[name] = None
    return {
        "target": target, "predictores": predictors,
        "r2": round(float(model.rsquared), 4),
        "r2_adj": round(float(model.rsquared_adj), 4),
        "f_p": round(float(model.f_pvalue), 4),
        "coef": {n: round(float(c), 4) for n, c in zip(["const"] + predictors, model.params)},
        "coef_p": {n: round(float(p), 4) for n, p in zip(["const"] + predictors, model.pvalues)},
        "vif": vif,
        "residuos_normales": norm_resid["normal"],
        "diagnostico": (
            "Residuos normales" if norm_resid["normal"] else
            "⚠ Residuos NO normales — revisar linealidad/transformaciones"
        ),
    }


# ============================================================
#  Orquestador
# ============================================================
def run_omnianalysis(df: pd.DataFrame, selected_cols: list[str],
                     confirmed_comparisons: list[tuple[str, str]] | None = None,
                     target: str | None = None,
                     cfg: OmniConfig = DEFAULT_CONFIG,
                     referencias: dict | None = None) -> dict:
    """Punto de entrada. Devuelve informe estructurado + candidatos a confirmar.

    Args:
        df: dataset
        selected_cols: columnas a analizar
        confirmed_comparisons: pares confirmados como comparación de métodos
        target: variable objetivo para regresión múltiple (Rama C)
        cfg: configuración (Anexo A)
        referencias: {par ordenado -> nombre de la columna que es método de
            referencia}. El par se ordena alfabéticamente igual que
            `confirmed`, y el valor es el NOMBRE de la columna, así que no
            depende del orden en que llegue el par. Sin entrada, ese par usa
            Bland-Altman clásico contra el promedio.
    """
    if not selected_cols:
        return {"error": "Selecciona al menos una columna."}
    cols = [c for c in selected_cols if c in df.columns]
    if not cols:
        return {"error": "Columnas no encontradas."}

    confirmed = set(tuple(sorted(p)) for p in (confirmed_comparisons or []))
    refs = {tuple(sorted(k)): v for k, v in (referencias or {}).items() if v}

    profile = profile_dataset(df, cols, cfg)
    n = len(cols)
    branch = "A" if n == 1 else ("B" if n == 2 else "C")

    report = {"profile": profile, "branch": branch, "blocks": [],
              "comparison_candidates": [], "warnings_globales": [],
              # Ensayos que no pertenecen a un bloque: perfilado y rama C.
              "ensayos": []}

    _marcar(report, "perfil_tipos", f"{len(cols)} columna(s) clasificada(s)")
    _marcar(report, "perfil_estructura",
            f"{profile['n_rows']} filas, {profile['full_duplicates']} duplicado(s)")

    if profile["shape"].startswith("serie temporal"):
        report["warnings_globales"].append(
            "Estructura temporal detectada: este árbol no cubre series de tiempo. "
            "Análisis transversal puede no ser válido (rama futura)."
        )
        _marcar(report, "perfil_temporal", "hay columna fecha/hora")
    else:
        _descartar(report, "perfil_temporal", "ninguna columna es fecha/hora")

    col_types = profile["col_types"]
    num_cols = [c for c in cols if _is_numeric_type(col_types[c]["tipo"])]

    # --- Univariado (siempre, todas las columnas) ---
    for c in cols:
        report["blocks"].append(_univariate(c, df[c], col_types[c]["tipo"], cfg))

    # --- Rama A: solo univariado ---
    if branch == "A":
        return report

    # --- Bivariado (todos los pares) ---
    pairs = [(cols[i], cols[j]) for i in range(n) for j in range(i + 1, n)]
    for c1, c2 in pairs:
        report["blocks"].append(
            _bivariate(c1, df[c1], col_types[c1]["tipo"],
                       c2, df[c2], col_types[c2]["tipo"], cfg)
        )

    # --- Detección de comparación de métodos (pares numéricos) ---
    n_pares_num = len(num_cols) * (len(num_cols) - 1) // 2
    if n_pares_num:
        _marcar(report, "score_comparacion", f"{n_pares_num} par(es) numérico(s) puntuado(s)")
    else:
        _descartar(report, "score_comparacion", "menos de 2 columnas numéricas")
    candidates = detect_comparison_candidates(df, num_cols, cfg)
    for cand in candidates:
        key = tuple(sorted((cand["col1"], cand["col2"])))
        if key in confirmed:
            report["blocks"].append(
                concordance_analysis(cand["col1"], df[cand["col1"]],
                                     cand["col2"], df[cand["col2"]], cfg,
                                     referencia=refs.get(key))
            )
        else:
            report["comparison_candidates"].append(cand)

    # También correr concordancia sobre pares confirmados manualmente aunque no scored
    for key in confirmed:
        c1, c2 = key
        if c1 in df.columns and c2 in df.columns:
            already = any(cand for cand in candidates
                          if tuple(sorted((cand["col1"], cand["col2"]))) == key)
            if not already:
                report["blocks"].append(
                    concordance_analysis(c1, df[c1], c2, df[c2], cfg,
                                         referencia=refs.get(key))
                )

    # --- Rama C: matriz correlación + multiplicidad + regresión múltiple ---
    if branch == "C":
        if len(num_cols) >= 2:
            report["correlation_matrix"] = _correlation_matrix(df, num_cols, cfg)
            report["warnings_globales"].append(
                "Corrección por multiplicidad (Benjamini-Hochberg) aplicada a la matriz de "
                "correlación: reportados p crudo y p ajustado."
            )
            n_celdas = len(report["correlation_matrix"].get("celdas", []))
            _marcar(report, "matriz_correlacion", f"{n_celdas} celda(s)")
            _marcar(report, "fdr_bh", f"{cfg.FDR_METHOD} sobre {n_celdas} p-valor(es)")
        else:
            _descartar(report, "matriz_correlacion", "menos de 2 columnas numéricas")
            _descartar(report, "fdr_bh", "no hubo matriz de correlación que corregir")

        if target and target in num_cols:
            predictors = [c for c in num_cols if c != target]
            if predictors:
                mr = _multiple_regression(df, target, predictors, cfg)
                report["multiple_regression"] = mr
                if "error" in mr:
                    _descartar(report, "regresion_multiple", mr["error"])
                    _descartar(report, "vif", "no hubo regresión múltiple")
                else:
                    _marcar(report, "regresion_multiple",
                            f"objetivo={target}, R²={mr['r2']}")
                    _marcar(report, "vif", f"{len(predictors)} predictora(s)")
                _descartar(report, "pca", f"hay objetivo declarado ({target}): "
                                          "se modela, no se explora")
                _descartar(report, "clustering", "no se corrió PCA exploratorio")
        elif len(num_cols) >= 3:
            # Muchas numéricas sin objetivo claro → exploratorio
            pc = _pca_clustering(df, num_cols, cfg)
            report["pca_clustering"] = pc
            _descartar(report, "regresion_multiple",
                       "no se declaró variable objetivo numérica")
            _descartar(report, "vif", "no hubo regresión múltiple")
            if "error" in pc:
                _descartar(report, "pca", pc["error"])
                _descartar(report, "clustering", pc["error"])
            else:
                _marcar(report, "pca",
                        f"{pc['pca']['componentes_para_90pct']} componente(s) para el 90%")
                _marcar(report, "clustering",
                        f"k={pc['clustering']['k_optimo']}, "
                        f"silueta={pc['clustering']['silhouette']}")
        else:
            _descartar(report, "regresion_multiple", "no se declaró variable objetivo numérica")
            _descartar(report, "vif", "no hubo regresión múltiple")
            _descartar(report, "pca", f"solo {len(num_cols)} columna(s) numérica(s), hacen falta 3")
            _descartar(report, "clustering", "no se corrió PCA exploratorio")

    return report
