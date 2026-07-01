"""Omnianálisis — árbol de decisión estadístico automático."""
import numpy as np
import pandas as pd
from scipy import stats


def _is_numeric(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series)


def _is_categorical(series: pd.Series) -> bool:
    n_unique = series.nunique()
    n_total = len(series.dropna())
    return (not _is_numeric(series)) or (n_unique <= max(5, n_total * 0.05) and n_unique < 20)


def _normality(arr) -> tuple[bool, float, float]:
    arr = np.asarray(arr, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) < 3:
        return True, np.nan, np.nan
    if len(arr) > 5000:
        arr = np.random.choice(arr, 5000, replace=False)
    stat, p = stats.shapiro(arr)
    return p >= 0.05, float(stat), float(p)


def _levene(*groups) -> tuple[bool, float, float]:
    clean = [np.asarray(g, dtype=float) for g in groups]
    clean = [g[~np.isnan(g)] for g in clean]
    if any(len(g) < 2 for g in clean):
        return True, np.nan, np.nan
    stat, p = stats.levene(*clean)
    return p >= 0.05, float(stat), float(p)


def _descriptive(arr) -> dict:
    arr = np.asarray(arr, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) == 0:
        return {}
    n = len(arr)
    mean = np.mean(arr)
    sd = np.std(arr, ddof=1)
    sem = sd / np.sqrt(n)
    return {
        "n": n, "media": round(mean, 4), "mediana": round(float(np.median(arr)), 4),
        "DE": round(sd, 4), "SEM": round(sem, 4),
        "min": round(float(np.min(arr)), 4), "max": round(float(np.max(arr)), 4),
        "Q25": round(float(np.percentile(arr, 25)), 4),
        "Q75": round(float(np.percentile(arr, 75)), 4),
        "IC95": (round(mean - 1.96 * sem, 4), round(mean + 1.96 * sem, 4)),
    }


def _freq_table(series: pd.Series) -> dict:
    counts = series.value_counts()
    pct = (counts / counts.sum() * 100).round(1)
    return {str(k): {"n": int(v), "%": float(pct[k])} for k, v in counts.items()}


def analyze_column(col_name: str, series: pd.Series) -> dict:
    """Analiza una columna y retorna hallazgos estructurados."""
    series = series.dropna()
    result = {"columna": col_name, "n": len(series), "pasos": [], "pruebas": [], "conclusion": ""}

    if len(series) == 0:
        result["conclusion"] = "Sin datos."
        return result

    # --- Tipo de variable ---
    if _is_categorical(series):
        result["tipo"] = "categórica"
        result["frecuencias"] = _freq_table(series)
        n_cat = series.nunique()
        if n_cat == 2:
            counts = series.value_counts().values
            if len(counts) == 2:
                obs = np.array([[counts[0], counts[1]]])
                chi2, p, _, _ = stats.chi2_contingency(
                    np.array([[counts[0], series.sum() if pd.api.types.is_numeric_dtype(series) else counts[1]],
                               [counts[1], len(series) - counts[1]]])
                ) if False else (None, None, None, None)
            result["pasos"].append("Variable categórica binaria — tabla de frecuencias calculada.")
        else:
            result["pasos"].append(f"Variable categórica con {n_cat} categorías — tabla de frecuencias calculada.")
        result["conclusion"] = (
            f"Variable categórica. Categorías: {list(series.unique()[:10])}. "
            f"Frecuencias: {result['frecuencias']}."
        )
        return result

    # --- Numérica continua ---
    result["tipo"] = "numérica continua"
    arr = series.values.astype(float)
    desc = _descriptive(arr)
    result["descriptivos"] = desc
    result["pasos"].append(f"Estadísticos descriptivos: media={desc['media']}, DE={desc['DE']}, n={desc['n']}.")

    # Normalidad
    normal, sw_stat, sw_p = _normality(arr)
    result["normalidad"] = {"normal": normal, "Shapiro-W": round(sw_stat, 4) if not np.isnan(sw_stat) else None,
                             "p": round(sw_p, 4) if not np.isnan(sw_p) else None}
    normal_str = "normal" if normal else "no normal"
    result["pasos"].append(
        f"Normalidad (Shapiro-Wilk): W={result['normalidad']['Shapiro-W']}, p={result['normalidad']['p']} → distribución {normal_str}."
    )

    result["conclusion"] = (
        f"Variable numérica {normal_str}. "
        f"Media={desc['media']} ± {desc['DE']} (DE). "
        f"Mediana={desc['mediana']}. IC95%={desc['IC95']}."
    )
    return result


def analyze_two_groups(col1: str, s1: pd.Series, col2: str, s2: pd.Series) -> dict:
    """Compara dos grupos/variables numéricas."""
    a1 = s1.dropna().values.astype(float)
    a2 = s2.dropna().values.astype(float)
    result = {"tipo": "comparación 2 grupos", "pasos": [], "pruebas": [], "conclusion": ""}

    normal1, _, p1 = _normality(a1)
    normal2, _, p2 = _normality(a2)
    both_normal = normal1 and normal2

    result["pasos"].append(
        f"{col1}: {'normal' if normal1 else 'no normal'} (p={round(p1,4) if not np.isnan(p1) else 'N/A'}) | "
        f"{col2}: {'normal' if normal2 else 'no normal'} (p={round(p2,4) if not np.isnan(p2) else 'N/A'})"
    )

    if both_normal:
        equal_var, lev_stat, lev_p = _levene(a1, a2)
        result["pasos"].append(
            f"Levene homocedasticidad: F={round(lev_stat,4) if not np.isnan(lev_stat) else 'N/A'}, "
            f"p={round(lev_p,4) if not np.isnan(lev_p) else 'N/A'} → varianzas {'iguales' if equal_var else 'distintas'}."
        )
        t_stat, t_p = stats.ttest_ind(a1, a2, equal_var=equal_var)
        test_name = "t de Student" if equal_var else "t de Welch"
        result["pruebas"].append({
            "prueba": test_name,
            "estadístico": round(float(t_stat), 4),
            "p": round(float(t_p), 4),
            "significativo": t_p < 0.05,
        })
        sig = "sí" if t_p < 0.05 else "no"
        result["conclusion"] = (
            f"Datos normales → {test_name}. t={round(t_stat,4)}, p={round(t_p,4)}. "
            f"Diferencia {'estadísticamente significativa' if t_p<0.05 else 'no significativa'} (α=0.05)."
        )
    else:
        u_stat, u_p = stats.mannwhitneyu(a1, a2, alternative='two-sided')
        result["pruebas"].append({
            "prueba": "U de Mann-Whitney",
            "estadístico": round(float(u_stat), 4),
            "p": round(float(u_p), 4),
            "significativo": u_p < 0.05,
        })
        result["conclusion"] = (
            f"Datos no normales → U de Mann-Whitney. U={round(u_stat,4)}, p={round(u_p,4)}. "
            f"Diferencia {'estadísticamente significativa' if u_p<0.05 else 'no significativa'} (α=0.05)."
        )

    return result


def analyze_single_group(col: str, series: pd.Series) -> dict:
    """Prueba de un grupo vs hipótesis (media=0 por defecto)."""
    arr = series.dropna().values.astype(float)
    result = {"tipo": "prueba 1 grupo", "pasos": [], "pruebas": [], "conclusion": ""}

    normal, sw_stat, sw_p = _normality(arr)
    result["pasos"].append(
        f"Normalidad: {'normal' if normal else 'no normal'} "
        f"(Shapiro-Wilk p={round(sw_p,4) if not np.isnan(sw_p) else 'N/A'})."
    )

    if normal:
        t_stat, t_p = stats.ttest_1samp(arr, 0)
        result["pruebas"].append({
            "prueba": "t para una muestra (H₀: μ=0)",
            "estadístico": round(float(t_stat), 4),
            "p": round(float(t_p), 4),
            "significativo": t_p < 0.05,
        })
        result["conclusion"] = (
            f"Datos normales → t para una muestra. t={round(t_stat,4)}, p={round(t_p,4)}. "
            f"Media {'significativamente' if t_p<0.05 else 'no significativamente'} distinta de 0."
        )
    else:
        w_stat, w_p = stats.wilcoxon(arr)
        result["pruebas"].append({
            "prueba": "Wilcoxon (H₀: mediana=0)",
            "estadístico": round(float(w_stat), 4),
            "p": round(float(w_p), 4),
            "significativo": w_p < 0.05,
        })
        result["conclusion"] = (
            f"Datos no normales → Wilcoxon. W={round(w_stat,4)}, p={round(w_p,4)}. "
            f"Mediana {'significativamente' if w_p<0.05 else 'no significativamente'} distinta de 0."
        )

    return result


def analyze_categorical_pair(col1: str, s1: pd.Series, col2: str, s2: pd.Series) -> dict:
    """Chi-cuadrado / Fisher para dos variables categóricas."""
    result = {"tipo": "tabla de contingencia", "pasos": [], "pruebas": [], "conclusion": ""}
    ct = pd.crosstab(s1, s2)
    result["tabla_contingencia"] = ct.to_dict()

    chi2, p, dof, expected = stats.chi2_contingency(ct)
    min_expected = np.min(expected)
    use_fisher = ct.shape == (2, 2) and min_expected < 5

    if use_fisher:
        _, fisher_p = stats.fisher_exact(ct.values)
        result["pruebas"].append({
            "prueba": "Test Exacto de Fisher",
            "p": round(float(fisher_p), 4),
            "significativo": fisher_p < 0.05,
        })
        result["pasos"].append(f"Frecuencia esperada mínima={round(min_expected,2)} < 5 → Fisher Exact.")
        result["conclusion"] = (
            f"Tabla {ct.shape[0]}x{ct.shape[1]} → Fisher Exact. p={round(fisher_p,4)}. "
            f"Asociación {'significativa' if fisher_p<0.05 else 'no significativa'} (α=0.05)."
        )
    else:
        result["pruebas"].append({
            "prueba": "Chi-cuadrado de Pearson",
            "estadístico": round(float(chi2), 4),
            "gl": int(dof),
            "p": round(float(p), 4),
            "significativo": p < 0.05,
        })
        result["pasos"].append(f"Frecuencia esperada mínima={round(min_expected,2)} ≥ 5 → Chi-cuadrado.")
        result["conclusion"] = (
            f"Tabla {ct.shape[0]}x{ct.shape[1]} → Chi-cuadrado. χ²={round(chi2,4)}, gl={dof}, p={round(p,4)}. "
            f"Asociación {'significativa' if p<0.05 else 'no significativa'} (α=0.05)."
        )
    return result


def run_omnianalysis(df: pd.DataFrame, selected_cols: list[str]) -> list[dict]:
    """
    Punto de entrada principal. Retorna lista de bloques de resultado.
    Lógica:
      - 1 col numérica → prueba 1 grupo
      - 2 cols numéricas → comparación 2 grupos
      - 1 col categórica → frecuencias
      - 2 cols categóricas → Chi-cuadrado / Fisher
      - Mix o >2 → análisis individual por columna
    """
    if not selected_cols:
        return [{"error": "Selecciona al menos una columna."}]

    cols = [c for c in selected_cols if c in df.columns]
    if not cols:
        return [{"error": "Columnas no encontradas en el dataset."}]

    results = []

    num_cols = [c for c in cols if _is_numeric(df[c]) and not _is_categorical(df[c])]
    cat_cols = [c for c in cols if _is_categorical(df[c])]

    # Caso especial: 2 numéricas → comparación
    if len(num_cols) == 2 and len(cat_cols) == 0:
        results.append(analyze_two_groups(
            num_cols[0], df[num_cols[0]],
            num_cols[1], df[num_cols[1]]
        ))
        return results

    # Caso especial: 2 categóricas → contingencia
    if len(cat_cols) == 2 and len(num_cols) == 0:
        results.append(analyze_categorical_pair(
            cat_cols[0], df[cat_cols[0]],
            cat_cols[1], df[cat_cols[1]]
        ))
        return results

    # General: análisis individual por columna
    for col in cols:
        series = df[col]
        if _is_categorical(series):
            results.append(analyze_column(col, series))
        else:
            if len(series.dropna()) >= 3:
                r = analyze_single_group(col, series)
                r["columna"] = col
                r["descriptivos"] = _descriptive(series.dropna().values.astype(float))
                # prepend descriptivos en pasos
                d = r["descriptivos"]
                r["pasos"].insert(0, f"Descriptivos: media={d['media']}, DE={d['DE']}, n={d['n']}.")
                results.append(r)
            else:
                results.append(analyze_column(col, series))

    return results
