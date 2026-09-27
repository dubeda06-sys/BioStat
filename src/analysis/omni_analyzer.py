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
from src.resultado.lenguaje import fmt_p, p_token
from src.core.statistics import (
    descriptive_stats, normality_test, anova_oneway, kruskal_wallis,
    chi_square_test, fisher_exact_test, pearson_r, spearman_rho, tukey_hsd,
    dunn_test, welch_anova, games_howell,
)
from src.core.bland_altman import (
    CV_CONSTANTE, DE_CONSTANTE, MIXTA, bland_altman_analysis,
    concordance_correlation, recta_ols as _recta, variabilidad_diferencias,
)


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


# Como se escribe un p: vive en src/resultado/lenguaje.py, compartido con el
# panel manual. Los nombres viejos quedan para no tocar a los llamadores.
_fmt_p = fmt_p
_p = p_token


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
from src.core.ep09 import regla_ep09
from src.core.agreement import deming_regression, deming_ponderado
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
        # Códigos: enteros consecutivos que arrancan en 0 o 1, pocos valores y
        # repetidos (Grupo 1/2/3, grado 0-4, estadio 1-4). Leídos como número,
        # un Grupo 1/2/3 terminaba en una correlación de Spearman cuyo resultado
        # depende de cómo se numeraron los grupos; como categoría se comparan
        # grupos, y eso no depende de la numeración (auditoría 2026-09, A15).
        if all_int and _son_codigos(arr, n_unique, cfg):
            lo, hi = int(round(arr.min())), int(round(arr.max()))
            info["tipo"] = CATEGORICAL_ORDINAL
            info["codigos"] = True
            info["nota"] = (
                f"Enteros consecutivos de {lo} a {hi}: se toman como códigos de "
                f"categoría (grupo, grado, estadio) y se comparan como grupos. Tratados "
                f"como cantidad, el resultado dependería de cómo se numeraron."
            )
            return info
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


def _son_codigos(arr, n_unique: int, cfg: OmniConfig) -> bool:
    """Enteros 0..k o 1..k sin huecos, con 3 a CARDINALITY_THRESHOLD valores
    y al menos dos casos por valor en promedio: así se ve una columna de
    códigos. Un identificador o una medición entera no repiten tanto."""
    if not 3 <= n_unique <= cfg.CARDINALITY_THRESHOLD or len(arr) < 2 * n_unique:
        return False
    valores = np.unique(np.round(arr))
    return valores[0] in (0.0, 1.0) and valores[-1] - valores[0] + 1 == n_unique


def _como_categoria(serie: pd.Series) -> pd.Series:
    """Una columna de códigos numéricos, con rótulos "1", "2"... en vez de
    "1.0", "2.0": el rótulo es lo que se lee en las tablas y en los pares."""
    if pd.api.types.is_numeric_dtype(serie):
        s = serie.dropna()
        arr = s.to_numpy(dtype=float)
        if len(arr) and np.all(np.isfinite(arr)) and np.allclose(arr, np.round(arr)):
            return s.round().astype(int).astype(str).reindex(serie.index)
    return serie


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
    arr = arr[np.isfinite(arr)]
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
    clean = [g[np.isfinite(g)] for g in clean]
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
    counts = _como_categoria(s).value_counts()
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
# Cada bloque bivariado corre su prueba y deja el p CRUDO en `_p`, sin decidir.
# La decisión la toma `_decidir` después, cuando `run_omnianalysis` ya juntó
# todos los p de la corrida: en la rama C se corrigen juntos (una sola familia
# de Benjamini-Hochberg), y el bloque, la matriz y el caso leen el mismo p
# corregido. Antes cada bloque decidía con su p crudo y la matriz corregía
# aparte, así que el mismo par salía "detectado" en un lado y no en el otro
# (auditoría 2026-09, K7). Los post-hoc también esperan: solo corren si la
# prueba global detectó algo con el p corregido.
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
        r = pearson_r(a, b) if both_normal else spearman_rho(a, b)
        if not _ok(r):
            # Una columna constante deja la correlacion indefinida: se dice y
            # se sigue con los demas bloques, no se tumba el informe entero.
            motivo = r.get("error") if isinstance(r, dict) else "no se pudo calcular"
            block["advertencias"].append(f"Correlacion: {motivo}")
            _descartar(block, "pearson", motivo)
            _descartar(block, "spearman", motivo)
            block["conclusion"] = f"No se puede medir la asociación: {motivo}"
            return block
        if both_normal:
            block["pruebas"].append({"prueba": "Pearson", "r": round(float(r["r"]), 4),
                                     "r2": round(float(r["r2"]), 4), "p": round(float(r["p"]), 4)})
            _marcar(block, "pearson", f"r={round(float(r['r']), 4)}, {_p(r['p'])}")
            _descartar(block, "spearman", "ambas variables pasaron la prueba de normalidad")
        else:
            block["pruebas"].append({"prueba": "Spearman", "rho": round(float(r["rho"]), 4),
                                     "p": round(float(r["p"]), 4)})
            _marcar(block, "spearman", f"rho={round(float(r['rho']), 4)}, {_p(r['p'])}")
            _descartar(block, "pearson",
                       f"normalidad incumplida ({c1}: {'sí' if norm1['normal'] else 'no'}, "
                       f"{c2}: {'sí' if norm2['normal'] else 'no'})")
        _dejar_p(block, r["p"])
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


def _dejar_p(block: dict, p) -> None:
    """Deja el p crudo para la decisión. Un p no finito no entra a la familia:
    corregirlo con los demás inventaría un número."""
    if p is not None and np.isfinite(p):
        block["_p"] = float(p)
    else:
        block["advertencias"].append("La prueba no devolvió un p calculable.")


def _align(s1: pd.Series, s2: pd.Series):
    df = pd.DataFrame({"a": s1, "b": s2}).dropna()
    return df["a"].to_numpy(dtype=float), df["b"].to_numpy(dtype=float)


def _compare_groups(num_name: str, num_s: pd.Series, cat_s: pd.Series,
                    cfg: OmniConfig, block: dict) -> dict:
    block["tipo"] = "comparación de grupos"
    df = pd.DataFrame({"y": num_s, "g": _como_categoria(cat_s)}).dropna()
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
    # Con dispersiones distintas manda Levene, no la normalidad: la prueba por
    # rangos supone la misma forma bajo H0 y rechaza por la dispersión. Medido
    # (auditoría 2026-09, K10, 4000 corridas con medias iguales, DE 2/6/14):
    # cuando algún grupo normal no pasaba Shapiro, Kruskal-Wallis daba 23 % de
    # falsos positivos, Welch sobre medias recortadas al 20 % 13 %, y Welch
    # 6,5 %. Con asimetría (chi², exponencial) Welch sigue siendo el que menos
    # infla: 6-10 % contra 33-37 % de los rangos.
    welch_sin_normalidad = not all_normal and not lev["equal_var"]
    if welch_sin_normalidad:
        block["advertencias"].append(
            "Los grupos no son normales y además dispersan distinto (Levene "
            f"{_p(lev['p'])}). La prueba por rangos no sirve acá: reacciona a la "
            "diferencia de dispersión, no solo a la de posición. Se usa Welch, que "
            "compara promedios sin suponer dispersión pareja y tolera la falta de "
            "normalidad; con grupos chicos y muy asimétricos el p es aproximado, y "
            "conviene mirar los datos en escala logarítmica."
        )

    if k == 2:
        # Los de 3+ grupos no compiten aca: no aplican, no fueron descartados.
        if all_normal or welch_sin_normalidad:
            equal_var = lev["equal_var"]
            t_stat, t_p = stats.ttest_ind(groups[0], groups[1], equal_var=equal_var)
            name = "t de Student" if equal_var else "t de Welch"
            block["traza"].append(
                f"2 grupos {'normales' if all_normal else 'no normales'}, varianzas "
                f"{'iguales' if equal_var else 'distintas'} → {name}.")
            block["pruebas"].append({"prueba": name, "estadístico": round(float(t_stat), 4),
                                     "p": round(float(t_p), 4)})
            elegido = "t_student" if equal_var else "t_welch"
            rival = "t_welch" if equal_var else "t_student"
            _marcar(block, elegido, f"t={round(float(t_stat), 4)}, {_p(t_p)}")
            _descartar(block, rival,
                       f"Levene {_p(lev['p'])}: varianzas "
                       f"{'iguales' if equal_var else 'distintas'}")
            _descartar(block, "mann_whitney",
                       "los dos grupos pasaron la prueba de normalidad" if all_normal else
                       f"Levene {_p(lev['p'])}: con dispersiones distintas la prueba por "
                       "rangos reacciona a la dispersión, no solo a la posición")
            _dejar_p(block, float(t_p))
        else:
            u_stat, u_p = stats.mannwhitneyu(groups[0], groups[1], alternative="two-sided")
            block["traza"].append("2 grupos, alguno no normal, varianzas iguales → Mann-Whitney U.")
            block["pruebas"].append({"prueba": "Mann-Whitney U", "estadístico": round(float(u_stat), 4),
                                     "p": round(float(u_p), 4)})
            _marcar(block, "mann_whitney", f"U={round(float(u_stat), 4)}, {_p(u_p)}")
            _descartar(block, "t_student", "normalidad incumplida en al menos un grupo")
            _descartar(block, "t_welch",
                       f"Levene {_p(lev['p'])}: dispersión pareja, y con algún grupo no "
                       "normal la comparación va por rangos")
            _dejar_p(block, float(u_p))
        return block

    # k >= 3 grupos. Tres caminos, y el post-hoc va con su camino.
    if all_normal and lev["equal_var"]:
        av = anova_oneway(groups)
        block["traza"].append(f"{k} grupos normales y con varianzas iguales → ANOVA.")
        block["pruebas"].append({"prueba": "ANOVA una vía", "estadístico": round(float(av["f"]), 4),
                                 "p": round(float(av["p"]), 4)})
        _marcar(block, "anova", f"F={round(float(av['f']), 4)}, {_p(av['p'])}")
        _descartar(block, "anova_welch",
                   f"Levene {_p(lev['p'])}: varianzas iguales, y así el ANOVA clásico "
                   "tiene más potencia")
        _descartar(block, "kruskal", "los grupos son normales y con varianzas iguales")
        block["_posthoc"] = {"camino": "anova", "grupos": groups, "etiquetas": labels,
                             "y": df["y"].to_numpy(dtype=float),
                             "g": df["g"].astype(str).to_numpy()}
        _dejar_p(block, float(av["p"]))
    elif not lev["equal_var"]:
        # Varianzas distintas, normales o no: ANOVA de Welch. Kruskal-Wallis NO es
        # la salida: supone la misma forma bajo H0 y rechaza por la dispersión.
        # Con medias iguales y DE 2/6/14 el motor daba 16,7 % de falsos
        # positivos por ese camino; Welch, 5,6 % (auditoría 2026-09, K10).
        wa = welch_anova(groups)
        if not _ok(wa):
            motivo = wa.get("error") if isinstance(wa, dict) else "no se pudo calcular"
            block["advertencias"].append(f"ANOVA de Welch: {motivo}")
            _descartar(block, "anova_welch", motivo)
            block["conclusion"] = f"No se pudo comparar los grupos: {motivo}"
            return block
        block["traza"].append(
            f"{k} grupos {'normales' if all_normal else 'no normales'} con varianzas "
            "distintas → ANOVA de Welch.")
        block["pruebas"].append({"prueba": "ANOVA de Welch", "estadístico": round(float(wa["f"]), 4),
                                 "gl": (round(float(wa["df1"]), 2), round(float(wa["df2"]), 2)),
                                 "p": round(float(wa["p"]), 4)})
        _marcar(block, "anova_welch", f"F={round(float(wa['f']), 4)}, {_p(wa['p'])}")
        _descartar(block, "anova",
                   f"Levene {_p(lev['p'])}: varianzas distintas, y el ANOVA clásico las "
                   "supone iguales")
        _descartar(block, "kruskal",
                   ("los grupos son normales; " if all_normal else "")
                   + "con dispersiones distintas Kruskal-Wallis reacciona a la "
                   "dispersión, no solo a la posición")
        block["_posthoc"] = {"camino": "welch", "grupos": groups, "etiquetas": labels}
        _dejar_p(block, wa["p"])
    else:
        kw = kruskal_wallis(groups)
        block["traza"].append(f"{k} grupos, alguno no normal, varianzas iguales → Kruskal-Wallis.")
        block["pruebas"].append({"prueba": "Kruskal-Wallis", "estadístico": round(float(kw["h"]), 4),
                                 "p": round(float(kw["p"]), 4)})
        _marcar(block, "kruskal", f"H={round(float(kw['h']), 4)}, {_p(kw['p'])}")
        _descartar(block, "anova", "normalidad incumplida en al menos un grupo")
        _descartar(block, "anova_welch",
                   f"Levene {_p(lev['p'])}: dispersión pareja, y con algún grupo no "
                   "normal la comparación va por rangos")
        block["_posthoc"] = {"camino": "kruskal", "grupos": groups, "etiquetas": labels}
        _dejar_p(block, float(kw["p"]))
    return block


# Post-hoc de cada camino, y los que no le tocan.
_POSTHOC = {"anova": "tukey_hsd", "welch": "games_howell", "kruskal": "dunn"}
_NOMBRE_GLOBAL = {"anova": "El ANOVA", "welch": "El ANOVA de Welch",
                  "kruskal": "Kruskal-Wallis"}
_POR_QUE_NO = {
    "tukey_hsd": {"welch": "Tukey supone varianzas iguales y Levene dijo que no",
                  "kruskal": "el camino fue por rangos (Kruskal-Wallis)"},
    "games_howell": {"anova": "las varianzas son iguales: Tukey es el que corresponde",
                     "kruskal": "el camino fue por rangos (Kruskal-Wallis)"},
    "dunn": {"anova": "el camino fue paramétrico (ANOVA)",
             "welch": "el camino fue paramétrico (ANOVA de Welch)"},
}


def _correr_posthoc(block: dict, detectado: bool, p_txt: str, cfg: OmniConfig) -> None:
    datos = block.pop("_posthoc", None)
    if datos is None:
        return
    camino = datos["camino"]
    propio = _POSTHOC[camino]
    for otro, motivos in _POR_QUE_NO.items():
        if otro != propio:
            _descartar(block, otro, motivos[camino])
    if not detectado:
        _descartar(block, propio,
                   f"{_NOMBRE_GLOBAL[camino]} no detectó diferencia ({p_txt}): correr el "
                   "post-hoc igual inflaría los falsos positivos")
        return
    k = len(datos["grupos"])
    if camino == "anova":
        ph = _tukey_posthoc(datos["y"], datos["g"], cfg)
        block["traza"].append(f"{_NOMBRE_GLOBAL[camino]} detectó diferencia → post-hoc de Tukey.")
        _marcar(block, "tukey_hsd", f"{k} grupos")
    elif camino == "welch":
        ph = games_howell(datos["grupos"], datos["etiquetas"])
        block["traza"].append(f"{_NOMBRE_GLOBAL[camino]} detectó diferencia → post-hoc de Games-Howell.")
        _marcar(block, "games_howell", f"{k} grupos")
    else:
        ph = dunn_test(datos["grupos"], datos["etiquetas"])
        block["traza"].append(f"{_NOMBRE_GLOBAL[camino]} detectó diferencia → post-hoc de Dunn.")
        _marcar(block, "dunn", f"{k} grupos, Bonferroni")
    if not ph or ph.get("error"):
        block["advertencias"].append(
            "No se pudo correr el post-hoc"
            + (f": {ph['error']}" if ph and ph.get("error") else "."))
        return
    if ph.get("comparaciones"):
        for c in ph["comparaciones"]:
            c["detectado"] = bool(c["p_adj"] < cfg.ALPHA)
            for clave in ("p", "p_adj", "z", "diferencia"):
                if clave in c:
                    c[clave] = round(float(c[clave]), 4)
    block["resultados"]["posthoc"] = ph


def _tukey_posthoc(y, g, cfg: OmniConfig):
    """El Tukey del core (el mismo que usa el panel), desde el formato largo."""
    y, g = np.asarray(y, dtype=float), np.asarray(g).astype(str)
    etiquetas = sorted(set(g))
    return tukey_hsd([y[g == e] for e in etiquetas], etiquetas, alpha=cfg.ALPHA)


def _contingency(c1, s1, c2, s2, cfg: OmniConfig, block: dict) -> dict:
    block["tipo"] = "tabla de contingencia"
    ct = pd.crosstab(_como_categoria(s1).dropna(), _como_categoria(s2).dropna())
    block["resultados"]["tabla"] = ct.to_dict()
    chi = chi_square_test(ct.values)
    if chi is None:
        block["conclusion"] = "Tabla degenerada — sin prueba."
        return block
    expected = np.asarray(chi["expected"])
    min_exp = float(np.min(expected))
    es_2x2 = ct.shape == (2, 2)
    alcanza = min_exp >= cfg.FISHER_MIN_FREQ
    camino = "chi2" if alcanza else ("fisher" if es_2x2 else "chi2_montecarlo")
    forma = f"{ct.shape[0]}×{ct.shape[1]}"
    block["resultados"]["supuestos"] = {
        "esperada_minima": round(min_exp, 2),
        "umbral": cfg.FISHER_MIN_FREQ,
        "forma": (int(ct.shape[0]), int(ct.shape[1])),
        "n_total": int(ct.values.sum()),
        "camino": camino,
        "simulaciones": cfg.MONTECARLO_N,
    }
    comparador = "≥" if alcanza else "<"
    block["traza"].append(
        f"Tabla {forma}, frecuencia esperada mínima={round(min_exp, 2)} "
        f"({comparador} {cfg.FISHER_MIN_FREQ}) → "
        + {"chi2": "Chi-cuadrado.",
           "fisher": "Fisher (probabilidad exacta).",
           "chi2_montecarlo": f"Chi-cuadrado con p por simulación ({cfg.MONTECARLO_N} tablas "
                              "con los mismos totales)."}[camino]
    )
    razon_esperada = (f"esperada mínima {round(min_exp, 2)} {comparador} "
                      f"{cfg.FISHER_MIN_FREQ}")
    if camino == "fisher":
        (a, b), (c, d) = ct.values
        fe = fisher_exact_test(int(a), int(b), int(c), int(d))
        block["pruebas"].append({"prueba": "Test exacto de Fisher", "p": round(float(fe["p"]), 4),
                                 "odds_ratio": round(float(fe["odds_ratio"]), 4)})
        _marcar(block, "fisher", f"{_p(fe['p'])}, "
                                 f"OR={round(float(fe['odds_ratio']), 4)}")
        _descartar(block, "chi2", f"{razon_esperada}: la aproximación chi-cuadrado no vale")
        _descartar(block, "chi2_montecarlo",
                   "la tabla es 2×2: Fisher da la probabilidad exacta, no hace falta simular")
        _dejar_p(block, float(fe["p"]))
    elif camino == "chi2_montecarlo":
        # Tabla más grande que 2×2 con casilleros flacos: la aproximación del
        # chi-cuadrado no vale y Fisher de r×c no está a mano. El p se calcula
        # permutando una columna contra la otra, que deja fijos los totales de
        # filas y columnas. Con semilla fija: la misma tabla da siempre el mismo
        # p (auditoría 2026-09, A8).
        mc = stats.chi2_contingency(
            ct.values, correction=False,
            method=stats.PermutationMethod(n_resamples=cfg.MONTECARLO_N,
                                           rng=np.random.default_rng(cfg.MONTECARLO_SEMILLA)))
        block["pruebas"].append({"prueba": "Chi-cuadrado (p por simulación)",
                                 "estadístico": round(float(mc.statistic), 4),
                                 "gl": int(chi["df"]), "p": round(float(mc.pvalue), 4)})
        _marcar(block, "chi2_montecarlo",
                f"χ²={round(float(mc.statistic), 4)}, {_p(mc.pvalue)}, "
                f"{cfg.MONTECARLO_N} simulaciones")
        _descartar(block, "chi2", f"{razon_esperada}: la aproximación chi-cuadrado no vale")
        _descartar(block, "fisher", f"la tabla es {forma}, no 2×2")
        _dejar_p(block, float(mc.pvalue))
    else:
        nombre = "Chi-cuadrado (con corrección de Yates)" if es_2x2 else "Chi-cuadrado"
        block["pruebas"].append({"prueba": nombre, "estadístico": round(float(chi["chi2"]), 4),
                                 "gl": int(chi["df"]), "p": round(float(chi["p"]), 4)})
        _marcar(block, "chi2", f"χ²={round(float(chi['chi2']), 4)}, gl={int(chi['df'])}, "
                               f"{_p(chi['p'])}")
        _descartar(block, "fisher", f"{razon_esperada}: la aproximación vale")
        _descartar(block, "chi2_montecarlo", f"{razon_esperada}: no hace falta simular")
        _dejar_p(block, float(chi["p"]))
    return block


# ============================================================
#  Decisión: se toma con el p de la familia, no con el del bloque
# ============================================================
_QUE_SE_BUSCA = {
    "comparación de grupos": "diferencia entre los grupos",
    "tabla de contingencia": "asociación entre las categorías",
}
_SIMBOLO = {"t de Student": "t", "t de Welch": "t", "Mann-Whitney U": "U",
            "ANOVA una vía": "F", "ANOVA de Welch": "F", "Kruskal-Wallis": "H"}


def _texto_p(p, p_adj, n_familia: int) -> str:
    if n_familia > 1:
        return (f"{_p(p)} sin corregir; corregido por las {n_familia} pruebas de esta "
                f"corrida (Benjamini-Hochberg), {_p(p_adj)}")
    return _p(p)


def _decidir(block: dict, p_adj, n_familia: int, cfg: OmniConfig) -> None:
    """Cierra un bloque bivariado con el p que le toca.

    `p_adj` es el p corregido por la familia (rama C) o el mismo p crudo (rama
    B, una sola prueba). El veredicto, la conclusión y el post-hoc salen de acá
    y de ningún otro lado.
    """
    p = block.pop("_p", None)
    if p is None or not block.get("pruebas"):
        block.pop("_posthoc", None)
        return
    pr = block["pruebas"][0]
    detectado = bool(p_adj < cfg.ALPHA)
    pr["p_adj"] = round(float(p_adj), 4)
    pr["n_familia"] = int(n_familia)
    pr["detectado"] = detectado
    p_txt = _texto_p(p, p_adj, n_familia)

    tipo = block.get("tipo")
    if tipo == "correlación":
        forma = "lineal" if pr["prueba"] == "Pearson" else "monótona"
        coef = (f"r={pr['r']}, R²={pr['r2']}" if pr["prueba"] == "Pearson"
                else f"ρ={pr['rho']}")
        veredicto = (f"Se detectó asociación {forma}" if detectado
                     else f"No se detectó asociación {forma}")
        block["conclusion"] = f"{pr['prueba']}: {coef}, {p_txt}. {veredicto} (α={cfg.ALPHA})."
    else:
        que = _QUE_SE_BUSCA.get(tipo, "efecto")
        simbolo = _SIMBOLO.get(pr["prueba"], "χ²" if pr["prueba"].startswith("Chi") else "estadístico")
        estad = (f"{simbolo}={pr['estadístico']}, " if "estadístico" in pr else "")
        extra = (f"OR={pr['odds_ratio']}, " if "odds_ratio" in pr else "")
        veredicto = f"Se detectó {que}" if detectado else f"No se detectó {que}"
        block["conclusion"] = (f"{pr['prueba']}: {estad}{extra}{p_txt}. "
                               f"{veredicto} (α={cfg.ALPHA}).")
    _correr_posthoc(block, detectado, _p(p_adj), cfg)


# ============================================================
#  Detección de comparación de métodos (reglas duras + score)
# ============================================================
# Unidades que se reconocen escritas al final del nombre de columna, ya
# normalizadas (minúsculas, µ → u, IU → UI). Entre paréntesis o corchetes
# vale cualquier texto: «Glucosa (mg/dL)», «Hb [g/dL]».
_UNIDADES = (
    "mg/dl", "g/dl", "g/l", "mg/l", "ug/l", "ug/dl", "ng/ml", "ng/dl", "pg/ml",
    "mmol/l", "umol/l", "nmol/l", "pmol/l", "meq/l", "u/l", "ui/l", "mui/ml",
    "mui/l", "uui/ml", "ui/ml", "copias/ml", "fl", "pg", "ct", "%",
)


def _unidad_declarada(nombre: str) -> str | None:
    """La unidad escrita en el nombre de la columna, normalizada, o None.

    Primero lo que esté entre paréntesis o corchetes al final; si no, una
    unidad conocida como última palabra («glucosa mg/dl», «glu_mg_dl»).
    """
    import re
    s = str(nombre).strip().lower().replace("µ", "u").replace("μ", "u")
    s = s.replace("iu/", "ui/").replace("miu/", "mui/")
    m = re.search(r"[\(\[]\s*([^\)\]]+?)\s*[\)\]]\s*$", s)
    if m:
        return re.sub(r"\s+", "", m.group(1))
    plano = re.sub(r"[\s_\-]+", " ", s).strip()
    for u in _UNIDADES:
        for forma in {u, u.replace("/", " ")}:
            if plano.endswith(" " + forma):  # «Ct» solo es el nombre, no una unidad
                return u
    return None


def _sin_unidad(nombre: str) -> str:
    """El nombre sin la unidad: si no, «AST (U/L)» y «ALT (U/L)» se parecen
    por el paréntesis y no por el analito."""
    import re
    s = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]\s*$", "", str(nombre).strip())
    u = _unidad_declarada(s)
    if u:
        plano = re.sub(r"[\s_\-]+", " ", s.lower().replace("µ", "u")).strip()
        for forma in (u, u.replace("/", " ")):
            if plano.endswith(" " + forma):
                return plano[: -len(forma) - 1]
    return s


def _comparison_score(c1, s1, c2, s2, cfg: OmniConfig) -> dict:
    a, b = _align(s1, s2)
    if len(a) < 3:
        return {"score": 0, "reasons": [], "corr": None}
    score = 0.0
    reasons = []

    # misma unidad declarada en el nombre (regla fuerte del spec, §6.1)
    u1, u2 = _unidad_declarada(c1), _unidad_declarada(c2)
    if u1 and u1 == u2:
        score += cfg.PESO_UNIDAD
        reasons.append(f"misma unidad declarada ({u1})")
    elif u1 and u2:
        score -= cfg.PESO_UNIDAD_DISTINTA
        reasons.append(f"unidades declaradas distintas ({u1} y {u2}): resta")

    # corrcoef divide por la desviacion: con una columna constante da NaN, y
    # todas las comparaciones contra NaN son False, asi que el puntaje quedaba
    # bajo por un motivo que no era el suyo.
    if np.ptp(a) == 0 or np.ptp(b) == 0:
        return {"score": 0, "reasons": ["una de las dos columnas es constante"],
                "corr": None}
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

    # nombres similares (sin la unidad, que ya contó aparte)
    if _similar_names(_sin_unidad(c1), _sin_unidad(c2)):
        score += cfg.PESO_NOMBRE
        reasons.append("nombres de columna parecidos")

    # media de diferencias pequeña relativa al rango
    mean_diff = abs(np.mean(a - b))
    if span > 0 and mean_diff < cfg.DIF_CHICA_FRAC * span:
        score += cfg.PESO_DIF_CHICA
        reasons.append("media de diferencias pequeña")

    # mismo n y faltantes en las mismas filas: las dos columnas se midieron
    # sobre las mismas muestras (regla de apoyo del spec, §6.1)
    falta1, falta2 = s1.isna().to_numpy(), s2.isna().to_numpy()
    if len(falta1) == len(falta2) and np.array_equal(falta1, falta2):
        score += cfg.PESO_PAREADO
        reasons.append("mismo n y faltantes en las mismas filas")

    return {"score": round(score, 2), "reasons": reasons, "corr": round(r, 4)}


def _similar_names(c1: str, c2: str) -> bool:
    import difflib
    a, b = c1.lower(), c2.lower()
    # quitar sufijos numéricos comunes (metodo1/metodo2, a/b)
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    return ratio >= 0.6


def puntuar_pares(df: pd.DataFrame, num_cols: list[str], cfg: OmniConfig) -> list[dict]:
    """El puntaje de TODOS los pares numéricos, con sus motivos, supere o no
    el umbral. La auditoría lo muestra par por par: antes decía cuántos
    pares se puntuaron, no cuánto sacó cada uno."""
    pares = []
    for i in range(len(num_cols)):
        for j in range(i + 1, len(num_cols)):
            c1, c2 = num_cols[i], num_cols[j]
            sc = _comparison_score(c1, df[c1], c2, df[c2], cfg)
            pares.append({"col1": c1, "col2": c2, **sc,
                          "supera": bool(sc["score"] >= cfg.SCORE_UMBRAL_COMPARACION)})
    return pares


def detect_comparison_candidates(df: pd.DataFrame, num_cols: list[str], cfg: OmniConfig) -> list[dict]:
    """Corre reglas duras sobre todos los pares numéricos. Devuelve candidatos sobre umbral."""
    return [{k: v for k, v in p.items() if k != "supera"}
            for p in puntuar_pares(df, num_cols, cfg) if p["supera"]]


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

    El par se orienta como en CLSI EP09c (tabla 1): X es el procedimiento
    comparativo — la referencia, si se declaró — e Y el candidato. La
    diferencia es Y − X, la regresión es Y sobre X y el sesgo en un nivel de
    decisión se evalúa en una concentración de X. Antes la rama usaba el orden
    alfabético: con la referencia en la segunda columna, un método que leía
    10 % alto salía con −9,3 % de sesgo (auditoría 2026-09, K1).
    """
    hay_ref = referencia in (c1, c2)
    if referencia == c2:
        nx, ny, sx, sy = c2, c1, s2, s1
    else:
        nx, ny, sx, sy = c1, c2, s1, s2
    block = {"titulo": f"Concordancia de métodos — {nx} vs {ny}", "tipo": "concordancia",
             "traza": [], "advertencias": [], "resultados": {}, "conclusion": "", "pruebas": [],
             "ensayos": []}
    x, y = _align(sx, sy)
    if len(x) < 3:
        block["conclusion"] = "n<3 — sin concordancia."
        return block
    if np.ptp(x) == 0 or np.ptp(y) == 0:
        cual = nx if np.ptp(x) == 0 else ny
        block["advertencias"].append(f"{cual} no varía: no hay recta ni acuerdo que medir.")
        block["conclusion"] = f"Sin comparación: {cual} es constante."
        return block

    block["resultados"]["orientacion"] = {
        "x": nx, "y": ny, "referencia_declarada": bool(hay_ref),
        "diferencia": f"{ny} − {nx}",
    }
    if hay_ref:
        block["traza"].append(
            f"Orientación: {nx} es la referencia → eje X; {ny} es el método en prueba "
            f"→ eje Y. Diferencia = {ny} − {nx} (EP09c, tabla 1).")
    else:
        block["traza"].append(
            f"Orientación: sin referencia declarada, {nx} va en X y {ny} en Y. "
            f"Diferencia = {ny} − {nx}.")
        block["advertencias"].append(
            f"Ninguna de las dos columnas se declaró método de referencia. Se tomó {nx} "
            f"como comparativo (eje X) y {ny} como el método en prueba: las diferencias "
            f"son {ny} − {nx}, y el sesgo en los niveles de decisión se mide en valores "
            f"de {nx}. Si la referencia es {ny}, el signo del sesgo se invierte: "
            f"declarala al confirmar el par."
        )

    d = y - x
    medias = (x + y) / 2
    eje = x if hay_ref else medias
    eje_nombre = nx if hay_ref else "el promedio"

    # 1) NODO variabilidad de las diferencias (EP09c §5.4). Decide la escala del
    # Bland-Altman y la regresión; por eso va primero.
    var = variabilidad_diferencias(eje, d, cfg.VARIABILIDAD_ALPHA)
    clase = var["clase"]
    escala = "porcentaje" if clase == CV_CONSTANTE else "unidades"
    unidad = " %" if escala == "porcentaje" else ""
    d_esc = 100.0 * d / eje if escala == "porcentaje" else d
    block["resultados"]["variabilidad"] = clase
    block["traza"].append(
        f"NODO variabilidad: |residuos| contra {eje_nombre}: pendiente="
        f"{var['pendiente_de']}, {_p(var['p_de'])}"
        + (f"; en %: {_p(var['p_cv'])}" if var["p_cv"] is not None else "")
        + f" → {clase}.")
    _marcar(block, "variabilidad_diferencias",
            f"contra {eje_nombre}: {_p(var['p_de'])} en unidades"
            + (f", {_p(var['p_cv'])} en %" if var["p_cv"] is not None else "")
            + f" → {clase}")
    if clase == CV_CONSTANTE:
        _marcar(block, "ba_escala_porcentual",
                "la dispersión crece con la concentración y en % queda pareja")
    elif clase == DE_CONSTANTE:
        _descartar(block, "ba_escala_porcentual",
                   f"la dispersión de las diferencias es pareja ({_p(var['p_de'])}): "
                   "se informa en unidades")
    else:
        _descartar(block, "ba_escala_porcentual",
                   "la dispersión no es pareja ni en unidades ni en %: variabilidad mixta")
        block["advertencias"].append(
            "La dispersión de las diferencias no es pareja ni proporcional en todo el "
            "rango (variabilidad mixta, CLSI EP09c §5.4.3). Un solo par de límites de "
            "acuerdo exagera el margen en un tramo y lo achica en otro: conviene mirar "
            "el gráfico por tramos de concentración."
            + ("" if var["cv_calculable"] else
               " Además hay valores ≤ 0 en el eje, y ahí el porcentaje no existe.")
        )

    # 2) NODO tendencia del sesgo: ¿la diferencia misma cambia con el nivel?
    # Contra la referencia si la hay; contra el promedio, el ruido del método en
    # prueba entra en los dos lados de la cuenta y fabrica pendiente. Se mide en
    # la escala elegida, donde la dispersión es pareja y el p de OLS vale.
    slope, _, p_slope, _ = _recta(eje, d_esc)
    tendencia = p_slope < cfg.PROPORTIONAL_SLOPE_ALPHA
    block["traza"].append(
        f"NODO tendencia: pendiente(diferencia{unidad} ~ {eje_nombre})={round(slope, 4)}, "
        f"{_p(p_slope)} → el sesgo {'CAMBIA' if tendencia else 'no cambia'} con la "
        f"concentración.")
    block["resultados"]["estructura_diferencia"] = "proporcional" if tendencia else "constante"
    _marcar(block, "estructura_diferencia",
            f"contra {eje_nombre}: pendiente={round(slope, 4)}, {_p(p_slope)} → "
            f"{'cambia con la concentración' if tendencia else 'constante'}")

    # 3) NODO normalidad de las DIFERENCIAS (no de datos crudos), en su escala.
    norm_diff = _normality(d_esc, cfg)
    block["traza"].append(
        f"NODO normalidad de DIFERENCIAS{unidad} ({norm_diff['test']}): p={norm_diff['p']} → "
        f"{'normal' if norm_diff['normal'] else 'NO normal'}."
    )
    _marcar(block, "normalidad_diferencias",
            f"{norm_diff['test']}, {_p(norm_diff['p'])} → "
            f"{'normales' if norm_diff['normal'] else 'NO normales'}")
    block["resultados"]["supuestos"] = {
        "n_pares": int(len(x)),
        "x": nx, "y": ny,
        # Nombre sin "mean": con una referencia declarada el eje NO es el promedio.
        "eje_estructura": eje_nombre,
        "variabilidad": var,
        "escala": escala,
        "pendiente_estructura": round(float(slope), 4),
        "p_pendiente": round(float(p_slope), 4),
        "proporcional": bool(tendencia),
        "normalidad_diferencias": norm_diff,
    }

    # 4) Bland-Altman: d = Y − X en la escala elegida. El core resta
    # method1 − method2, así que va (y, x); reference="y" apunta a x.
    ba = bland_altman_analysis(y, x, reference="y" if hay_ref else None, escala=escala)
    if not _ok(ba):
        block["resultados"]["bland_altman"] = {"error": ba.get("error") if isinstance(ba, dict)
                                               else "No se pudo calcular Bland-Altman."}
        block["advertencias"].append(block["resultados"]["bland_altman"]["error"])
        return block
    if norm_diff["normal"]:
        block["resultados"]["bland_altman"] = {
            "tipo": "paramétrico",
            "escala": escala,
            "sesgo": round(float(ba["mean_difference"]), 4),
            "loa_inferior": round(float(ba["loa_lower"]), 4),
            "loa_superior": round(float(ba["loa_upper"]), 4),
            "ic_sesgo": tuple(round(float(v), 4) for v in ba["ci_mean"]),
        }
        block["traza"].append(f"Diferencias{unidad} normales → Bland-Altman PARAMÉTRICO "
                              "(sesgo ± 1,96·DE).")
        _marcar(block, "ba_parametrico",
                f"sesgo={round(float(ba['mean_difference']), 4)}{unidad}, "
                f"LoA [{round(float(ba['loa_lower']), 4)}, {round(float(ba['loa_upper']), 4)}]")
        _descartar(block, "ba_no_parametrico",
                   f"las diferencias pasaron la prueba de normalidad ({_p(norm_diff['p'])})")
    else:
        lo, hi = float(ba["loa_np_lower"]), float(ba["loa_np_upper"])
        block["resultados"]["bland_altman"] = {
            "tipo": "no paramétrico",
            "escala": escala,
            "sesgo_mediana": round(float(np.median(d_esc)), 4),
            "loa_inferior_p2.5": round(float(lo), 4),
            "loa_superior_p97.5": round(float(hi), 4),
        }
        block["advertencias"].append(
            "Diferencias NO normales: Bland-Altman paramétrico sería incorrecto. "
            "Se usan percentiles empíricos 2.5/97.5."
        )
        block["traza"].append(f"Diferencias{unidad} NO normales → Bland-Altman NO PARAMÉTRICO "
                              "(percentiles).")
        _marcar(block, "ba_no_parametrico",
                f"mediana={round(float(np.median(d_esc)), 4)}{unidad}, "
                f"P2,5/P97,5 [{round(lo, 4)}, {round(hi, 4)}]")
        _descartar(block, "ba_parametrico",
                   f"las diferencias NO son normales ({_p(norm_diff['p'])}): los LoA "
                   "paramétricos serían incorrectos")

    # 4b) NODO eje X: promedio (Bland-Altman clasico) o referencia (Krouwer).
    # El promedio contiene a los dos métodos y distorsiona la pendiente en las
    # dos direcciones. Se informan las dos para que se vea, no se afirme.
    ba_res = block["resultados"]["bland_altman"]
    ba_res["eje_x"] = (f"{nx} (método de referencia)" if hay_ref
                       else "promedio de ambos métodos")
    if not hay_ref:
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
            detalle = (f"pendiente contra {nx}={round(p_ref, 4)}, "
                       f"contra el promedio={round(p_prom, 4)}"
                       + ("; el eje cambia la conclusión" if cambia else
                          "; misma conclusión por los dos ejes"))
            _marcar(block, "ba_eje_referencia", detalle)
            block["traza"].append(
                f"NODO eje X: {nx} es el método de referencia → se grafica y "
                f"regresa contra ella, no contra el promedio (Krouwer). {detalle}."
            )
            if cambia:
                quien = (f"solo contra {nx} se detecta sesgo proporcional"
                         if det_ref else
                         f"el sesgo proporcional aparece solo contra el promedio y "
                         f"no contra {nx}, o sea que el promedio lo inventa")
                block["advertencias"].append(
                    f"El eje X cambia la conclusión sobre el sesgo proporcional: "
                    f"pendiente contra {nx} = {round(p_ref, 4)}, contra el "
                    f"promedio = {round(p_prom, 4)}, y {quien}. Se informa la de "
                    f"{nx}: el promedio contiene a los dos métodos y "
                    f"distorsiona la pendiente en las dos direcciones — la achica "
                    f"cuando el sesgo es real y la infla con el ruido del método en "
                    f"prueba (Krouwer 2008, Stat Med 27:778-780)."
                )
        else:
            _descartar(block, "ba_eje_referencia",
                       "alguna de las dos pendientes no se pudo calcular: hay un eje "
                       "sin variación")

    # 5) Regresión de comparación (CLSI EP09c §6.2), Y sobre X:
    #    DE constante + diferencias normales  → Deming
    #    CV constante + diferencias normales  → Deming ponderado (apéndice B)
    #    mixta, o diferencias no normales     → Passing-Bablok (§6.2.3, §6.2.4)
    reg_slope = reg_intercept = None
    elegida = regla_ep09(clase, norm_diff["normal"])
    if elegida == "deming":
        dem = deming_regression(x, y, lambda_ratio=cfg.DEMING_LAMBDA)
        _descartar(block, "deming_ponderado",
                   f"la dispersión de las diferencias es pareja ({_p(var['p_de'])}): no "
                   "hace falta ponderar")
    elif elegida == "deming_ponderado":
        dem = deming_ponderado(x, y, lambda_ratio=cfg.DEMING_LAMBDA)
        _descartar(block, "deming",
                   "la dispersión crece con la concentración (CV constante): sin "
                   "ponderar, los puntos altos arrastran la recta")
    else:
        dem = None
        faltantes = []
        if not norm_diff["normal"]:
            faltantes.append(f"las diferencias no son normales ({_p(norm_diff['p'])})")
        if clase == MIXTA:
            faltantes.append("la dispersión de las diferencias es mixta")
        motivo = "Deming supone diferencias normales con DE o CV constante; " + \
                 " y ".join(faltantes)
        _descartar(block, "deming", motivo)
        _descartar(block, "deming_ponderado", motivo)

    if dem is not None and not _ok(dem):
        # Si la recta paramétrica no se puede calcular, la salida es la robusta.
        error = dem.get("error") if isinstance(dem, dict) else "no se pudo calcular"
        nombre = "Deming" if elegida == "deming" else "Deming ponderado"
        block["advertencias"].append(f"Regresión de {nombre}: {error}. Se usa Passing-Bablok.")
        _descartar(block, elegida, error)
        elegida, dem = "passing_bablok", None

    if dem is not None:
        _descartar(block, "passing_bablok",
                   "diferencias normales y con dispersión pareja: Deming es más eficiente"
                   if elegida == "deming" else
                   "diferencias en % normales y CV constante: Deming ponderado es más "
                   "eficiente (EP09c §6.2.2)")
        ci_s, ci_i = dem["ci_slope"], dem["ci_intercept"]
        slope_no_prop = ci_s[0] <= 1 <= ci_s[1]
        intercept_no_const = ci_i[0] <= 0 <= ci_i[1]
        reg_slope, reg_intercept = dem["slope"], dem["intercept"]
        nombre = "Deming" if elegida == "deming" else "Deming ponderado"
        block["resultados"]["regresion"] = {
            "metodo": nombre, "lambda": dem["lambda"],
            "pendiente": round(float(dem["slope"]), 4), "ic_pendiente": tuple(round(float(v), 4) for v in ci_s),
            "intercepto": round(float(dem["intercept"]), 4), "ic_intercepto": tuple(round(float(v), 4) for v in ci_i),
            "r2": round(float(dem["r2"]), 4),
            "sesgo_proporcional": not slope_no_prop,
            "sesgo_constante": not intercept_no_const,
        }
        _marcar(block, elegida,
                f"pendiente={round(float(dem['slope']), 4)}, intercepto={round(float(dem['intercept']), 4)}, "
                f"λ={dem['lambda']}")
        block["traza"].append(
            f"Diferencias{unidad} normales, {clase} → {nombre} (λ={dem['lambda']}). "
            f"IC pendiente {tuple(round(float(v), 4) for v in ci_s)} "
            f"{'incluye' if slope_no_prop else 'NO incluye'} 1 → "
            f"{'sin' if slope_no_prop else 'HAY'} sesgo proporcional. "
            f"IC intercepto {tuple(round(float(v), 4) for v in ci_i)} "
            f"{'incluye' if intercept_no_const else 'NO incluye'} 0 → "
            f"{'sin' if intercept_no_const else 'HAY'} sesgo constante."
        )
    elif elegida == "passing_bablok":
        pb = passing_bablok(x, y)
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
                "pendiente": round(float(pb["slope"]), 4), "ic_pendiente": tuple(round(float(v), 4) for v in ci_s),
                "intercepto": round(float(pb["intercept"]), 4), "ic_intercepto": tuple(round(float(v), 4) for v in ci_i),
                "sesgo_proporcional": not slope_no_prop,
                "sesgo_constante": not intercept_no_const,
            }
            # Cusum de linealidad (Passing y Bablok 1983): lo mismo que dice el panel.
            cusum = pb.get("cusum") or {}
            if not cusum.get("error") and "p" in cusum:
                block["resultados"]["regresion"]["cusum_h"] = round(cusum["h"], 4)
                block["resultados"]["regresion"]["cusum_p"] = cusum["p"]
                if cusum["p"] < 0.05:
                    block["advertencias"].append(
                        f"Passing-Bablok: la prueba Cusum detectó desvío de la linealidad "
                        f"({_p(cusum['p'])}). La recta no describe estos datos.")
                block["traza"].append(
                    f"Cusum de linealidad: H={round(cusum['h'], 4)}, {_p(cusum['p'])} → "
                    f"{'se detectó' if cusum['p'] < 0.05 else 'no se detectó'} desvío de "
                    f"la linealidad.")
            _marcar(block, "passing_bablok",
                    f"pendiente={round(float(pb['slope']), 4)}, intercepto={round(float(pb['intercept']), 4)}")
            block["traza"].append(
                f"Sin distribución asumida → Passing-Bablok. "
                f"IC pendiente {tuple(round(float(v), 4) for v in ci_s)} "
                f"{'incluye' if slope_no_prop else 'NO incluye'} 1 → "
                f"{'sin' if slope_no_prop else 'HAY'} sesgo proporcional. "
                f"IC intercepto {tuple(round(float(v), 4) for v in ci_i)} "
                f"{'incluye' if intercept_no_const else 'NO incluye'} 0 → "
                f"{'sin' if intercept_no_const else 'HAY'} sesgo constante."
            )

    # 5b) Sesgo en niveles de decisión médica, desde la recta, en valores de X
    # (el comparativo): EP09c evalúa el sesgo en X_c.
    if reg_slope is not None:
        levels = list(cfg.DECISION_LEVELS) if cfg.DECISION_LEVELS else \
            [float(np.percentile(x, q)) for q in (25, 50, 75)]
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
            f"Sesgo estimado en niveles de decisión de {nx} (desde la recta): " +
            "; ".join(f"X={s['nivel']}→{s['sesgo_abs']}" for s in sesgo_niveles) + "."
        )
        _marcar(block, "sesgo_niveles", f"{len(sesgo_niveles)} nivel(es) de {nx}")
    else:
        _descartar(block, "sesgo_niveles",
                   "no hubo recta de comparación: sin ella no hay sesgo que estimar")

    # 5c) Datos para graficar (Bland-Altman + regresión) — los usa la UI
    if cfg.GENERAR_GRAFICOS_COMPARACION:
        ba_res_tmp = block["resultados"]["bland_altman"]
        block["resultados"]["_plot"] = {
            "x": np.asarray(x, dtype=float),
            "y": np.asarray(y, dtype=float),
            "nombre_x": nx, "nombre_y": ny,
            "ba_tipo": ba_res_tmp["tipo"],
            "escala": escala,
            "eje_ba": "referencia" if hay_ref else "promedio",
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

    # 6) Concordancia global — CCC (NO Pearson), descompuesto en precisión × veracidad
    ccc = concordance_correlation(x, y)
    if not _ok(ccc):
        motivo = ccc.get("error") if isinstance(ccc, dict) else "No se pudo calcular el CCC."
        block["advertencias"].append(f"CCC de Lin: {motivo}")
        _descartar(block, "ccc", motivo)
        _descartar(block, "ccc_descomposicion", "el CCC no se pudo calcular")
        block["conclusion"] = f"Comparacion de metodos incompleta: {motivo}"
        return block
    block["resultados"]["ccc"] = round(float(ccc["ccc"]), 4)
    block["resultados"]["ccc_rho"] = round(float(ccc["rho"]), 4)
    block["resultados"]["ccc_cb"] = round(float(ccc["cb"]), 4)
    block["resultados"]["ccc_fuerza"] = ccc["strength"]
    _marcar(block, "ccc", f"CCC={round(float(ccc['ccc']), 4)} ({ccc['strength']})")
    if np.isfinite(ccc["ci_low"]):
        block["resultados"]["ccc_ic95"] = (round(float(ccc["ci_low"]), 4), round(float(ccc["ci_high"]), 4))

    # El grafico de la descomposicion necesita rho y Cb, y `_plot` se arma mas
    # arriba, antes de que el CCC exista. Se completa aca en vez de mover el
    # bloque: los datos de Bland-Altman de `_plot` dependen de decisiones que se
    # toman antes, y moverlas por un grafico seria al reves.
    plot_data = block["resultados"].get("_plot")
    if plot_data is not None:
        plot_data["ccc"] = float(ccc["ccc"])
        plot_data["ccc_rho"] = float(ccc["rho"])
        plot_data["ccc_cb"] = float(ccc["cb"])
        plot_data["ccc_fuerza"] = ccc["strength"]
        plot_data["ccc_ic95"] = block["resultados"].get("ccc_ic95")
    block["advertencias"].append(
        "NO usar Pearson como medida de acuerdo: correlación alta ≠ concordancia. "
        f"CCC (Lin) = {round(float(ccc['ccc']), 4)}."
    )
    block["traza"].append(
        f"Concordancia global → CCC de Lin = {round(float(ccc['ccc']), 4)} "
        f"({ccc['strength']}, escala de McBride 2005)."
    )
    # La descomposición CCC = rho × Cb dice DÓNDE está el defecto: rho bajo con Cb
    # alto = problema de dispersión; Cb bajo con rho alto = sesgo sistemático.
    # Son causas distintas y se corrigen por vías distintas (recalibración vs
    # imprecisión analítica), así que conviene decirlo explícito.
    if np.isfinite(ccc["rho"]) and np.isfinite(ccc["cb"]):
        if ccc["cb"] < 0.95 and ccc["rho"] >= 0.95:
            donde = ("el desacuerdo es sobre todo de VERACIDAD (sesgo): Cb="
                     f"{round(float(ccc['cb']), 4)} con rho={round(float(ccc['rho']), 4)} alto. "
                     "Apunta a calibración, no a imprecisión.")
        elif ccc["rho"] < 0.95 and ccc["cb"] >= 0.95:
            donde = ("el desacuerdo es sobre todo de PRECISIÓN (dispersión): rho="
                     f"{round(float(ccc['rho']), 4)} con Cb={round(float(ccc['cb']), 4)} alto. "
                     "Apunta a imprecisión analítica, no a calibración.")
        elif ccc["rho"] < 0.95 and ccc["cb"] < 0.95:
            donde = (f"hay componente de dispersión (rho={round(float(ccc['rho']), 4)}) Y de "
                     f"sesgo (Cb={round(float(ccc['cb']), 4)}).")
        else:
            donde = (f"ambos componentes son altos (rho={round(float(ccc['rho']), 4)}, "
                     f"Cb={round(float(ccc['cb']), 4)}).")
        block["traza"].append("Descomposición CCC = rho × Cb → " + donde)
        _marcar(block, "ccc_descomposicion",
                f"rho={round(float(ccc['rho']), 4)}, Cb={round(float(ccc['cb']), 4)}")
    else:
        _descartar(block, "ccc_descomposicion", "rho o Cb no finitos")

    ba_res = block["resultados"]["bland_altman"]
    sesgo = ba_res.get("sesgo", ba_res.get("sesgo_mediana"))
    reg = block["resultados"].get("regresion", {})
    block["conclusion"] = (
        f"Comparación de métodos ({ny} − {nx}): sesgo={sesgo}{unidad}, "
        f"CCC={round(float(ccc['ccc']), 4)}; dispersión de las diferencias: {clase}"
        + (f"; recta de {reg['metodo']}" if reg else "")
        + ". Ver Bland-Altman y regresión de comparación arriba."
    )
    return block


# ============================================================
#  Rama C — multiplicidad + matriz de correlación + regresión múltiple
# ============================================================
def _correlation_matrix(bloques: list[dict]) -> dict:
    """Matriz de correlación: una vista de los bloques bivariados numéricos.

    No recalcula nada. Cada celda es el mismo Pearson o Spearman del bloque de
    ese par — elegido celda por celda según la normalidad del par — con el
    mismo p corregido por la familia de la corrida. Cuando la matriz calculaba
    y corregía por su cuenta, el mismo par salía detectado en su bloque y no
    detectado en la matriz (auditoría 2026-09, K7).
    """
    cells = []
    for b in bloques:
        if b.get("tipo") != "correlación":
            continue
        par = b.get("titulo", "").replace("Bivariado — ", "")
        pruebas = b.get("pruebas") or []
        if not pruebas:
            # Un par indefinido no puede sacar del informe a los demas pares,
            # ni entrar en la correccion con un p inventado.
            cells.append({"par": par, "metodo": "—", "coef": None, "p": None,
                          "nota": "; ".join(b.get("advertencias") or []) or "no se pudo calcular"})
            continue
        pr = pruebas[0]
        cells.append({"par": par, "metodo": pr["prueba"],
                      "coef": pr.get("r", pr.get("rho")), "p": pr.get("p"),
                      "p_adj": pr.get("p_adj"), "detectado": bool(pr.get("detectado"))})
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
    bivariados = []
    for c1, c2 in pairs:
        b = _bivariate(c1, df[c1], col_types[c1]["tipo"],
                       c2, df[c2], col_types[c2]["tipo"], cfg)
        report["blocks"].append(b)
        bivariados.append(b)

    # --- Una sola familia de pruebas ---
    # En la rama C se miran muchos pares a la vez, y alguno da un p chico por
    # azar. Todos los p de la corrida se corrigen JUNTOS y cada bloque decide
    # con el suyo corregido: el bloque, la matriz y el caso leen el mismo número.
    familia = [b for b in bivariados if "_p" in b]
    crudos = [b["_p"] for b in familia]
    if branch == "C" and len(crudos) > 1:
        corregidos = _fdr(crudos, cfg)
        n_familia = len(crudos)
        report["warnings_globales"].append(
            f"Corrección por multiplicidad (Benjamini-Hochberg) sobre las {n_familia} "
            "pruebas bivariadas de esta corrida: cada una informa su p crudo y su p "
            "corregido, y decide con el corregido."
        )
        _marcar(report, "fdr_bh", f"{cfg.FDR_METHOD} sobre {n_familia} prueba(s) bivariada(s)")
    else:
        corregidos, n_familia = crudos, 1
        _descartar(report, "fdr_bh",
                   "una sola prueba bivariada: no hay multiplicidad que corregir"
                   if branch == "B" else "menos de 2 pruebas bivariadas con p calculable")
    for b, p_adj in zip(familia, corregidos):
        _decidir(b, float(p_adj), n_familia, cfg)

    # --- Detección de comparación de métodos (pares numéricos) ---
    puntajes = puntuar_pares(df, num_cols, cfg)
    report["comparison_scores"] = puntajes
    for p in puntajes:
        motivos = "; ".join(p["reasons"]) or "ninguna regla"
        _marcar(report, "score_comparacion",
                f"{p['col1']} × {p['col2']}: {p['score']} "
                f"({'≥' if p['supera'] else '<'} {cfg.SCORE_UMBRAL_COMPARACION}) — {motivos}")
    if not puntajes:
        _descartar(report, "score_comparacion", "menos de 2 columnas numéricas")
    candidates = [{k: v for k, v in p.items() if k != "supera"}
                  for p in puntajes if p["supera"]]
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
            report["correlation_matrix"] = _correlation_matrix(bivariados)
            n_celdas = len(report["correlation_matrix"].get("celdas", []))
            _marcar(report, "matriz_correlacion", f"{n_celdas} celda(s)")
        else:
            _descartar(report, "matriz_correlacion", "menos de 2 columnas numéricas")

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
