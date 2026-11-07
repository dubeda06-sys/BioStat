"""Importacion robusta de tablas.

Antes BioStat cargaba datos con `pd.read_csv(path)` por defecto: fallaba con los
CSV europeos (delimitador `;`, coma decimal `3,14`) y con los encodings de Windows
en espanol (cp1252 / latin-1), que son justamente los habituales en laboratorio
clinico. Este modulo centraliza una importacion al estilo de paquetes como MedCalc:

- Detecta encoding probando una lista ordenada (utf-8-sig → utf-8 → cp1252 → latin-1).
- Detecta el delimitador (`,` `;` tab `|`) con csv.Sniffer + fallback por conteo.
- Coerciona columnas numericas tolerando formato europeo (coma decimal y punto de
  miles), restos de errores de Excel (#REF!, #DIV/0!, ...) y codigos de faltante.
- Soporta .csv/.tsv/.txt, .xlsx/.xls y .sav (SPSS, si pyreadstat esta disponible).
- Devuelve un informe de lo que detecto, para mostrarlo al usuario.

El objetivo es *no perder* datos clinicos por un separador o una coma decimal.
"""
import csv as _csv
import numpy as np
import pandas as pd

ENCODINGS = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
DELIMITERS = [",", ";", "\t", "|"]
EXCEL_ERRORS = ["#REF!", "#DIV/0!", "#N/A", "#VALUE!", "#NAME?", "#NULL!", "#NUM!"]
NA_TOKENS = ["", "nan", "NaN", "NA", "N/A", "null", "NULL", "None", "#N/A", "."]


def detect_encoding(path):
    """Primer encoding de ENCODINGS que decodifica el archivo entero."""
    for enc in ENCODINGS:
        try:
            with open(path, "r", encoding=enc) as fh:
                fh.read()
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "latin-1"  # latin-1 mapea cualquier byte: nunca falla


def detect_delimiter(sample):
    """Delimitador mas probable de un texto de muestra."""
    try:
        return _csv.Sniffer().sniff(sample, delimiters="".join(DELIMITERS)).delimiter
    except _csv.Error:
        lines = [ln for ln in sample.splitlines() if ln.strip()]
        first = lines[0] if lines else ""
        counts = {d: first.count(d) for d in DELIMITERS}
        best = max(counts, key=counts.get)
        return best if counts[best] > 0 else ","


def coerce_series(s):
    """Intenta convertir una serie de texto a numero.

    Devuelve (serie_convertida, formato) donde formato es 'us', 'eu' o None
    (se dejo como texto). La rama europea solo se usa si la conversion directa
    falla y la europea explica >=90% de los valores no nulos; asi no se rompen
    los datos estilo US. (Limitacion conocida: una coma de miles US aislada,
    '1,234', es ambigua y puede leerse como 1.234 — caso raro en datos de lab.)
    """
    s = s.astype(str).str.strip()
    s = s.replace(EXCEL_ERRORS, np.nan).replace(NA_TOKENS, np.nan)
    non_null = s.notna().sum()
    if non_null == 0:
        return s, None
    direct = pd.to_numeric(s, errors="coerce")
    if direct.notna().sum() >= 0.9 * non_null:
        return direct, "us"
    euro = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    euro_num = pd.to_numeric(euro, errors="coerce")
    if euro_num.notna().sum() >= 0.9 * non_null and euro_num.notna().sum() > direct.notna().sum():
        return euro_num, "eu"
    return s, None


def coerce_numeric_columns(df):
    """Coerciona cada columna object a numero cuando se puede. Devuelve
    (df_nuevo, columnas_convertidas, formato_europeo_detectado)."""
    coerced, eu_seen = [], False
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object:
            conv, fmt = coerce_series(out[col])
            if fmt is not None:
                out[col] = conv
                coerced.append(str(col))
                eu_seen = eu_seen or (fmt == "eu")
    return out, coerced, eu_seen


def _tidy(df):
    """Quita columnas 'Unnamed'/vacias y filas totalmente vacias."""
    df.columns = [str(c).strip() for c in df.columns]
    drop = [c for c in df.columns if "unnamed" in c.lower() or df[c].isna().all()]
    if drop:
        df = df.drop(columns=drop)
    return df.dropna(how="all").reset_index(drop=True)


def _read_delimited(path):
    enc = detect_encoding(path)
    with open(path, "r", encoding=enc) as fh:
        sample = fh.read(8192)
    delim = detect_delimiter(sample)
    df = pd.read_csv(path, sep=delim, encoding=enc, dtype=str,
                     keep_default_na=False, skip_blank_lines=True)
    return _tidy(df), {"encoding": enc, "delimiter": delim}


def _read_excel(path):
    raw = pd.read_excel(path, header=None)
    header_row = 0
    for i in range(min(10, len(raw))):
        if raw.iloc[i].notna().sum() >= 2:
            header_row = i
            break
    df = pd.read_excel(path, header=header_row, dtype=str)
    return _tidy(df), {"encoding": None, "delimiter": None, "header_row": header_row}


def _read_spss(path):
    try:
        df = pd.read_spss(path)  # requiere pyreadstat
    except Exception as exc:  # pyreadstat ausente o archivo no soportado
        raise ImportError(
            "Leer .sav requiere el paquete 'pyreadstat' (pip install pyreadstat)."
        ) from exc
    return _tidy(df.astype(str)), {"encoding": None, "delimiter": None}


def read_table(path):
    """Importa una tabla desde csv/tsv/txt, xlsx/xls o sav.

    Devuelve dict: {df, report}. `report` trae format, encoding, delimiter,
    n_rows, n_cols, coerced_cols (columnas que pasaron a numero) y
    european_decimal (bool). Lanza ValueError si la extension no se reconoce.
    """
    low = str(path).lower()
    if low.endswith((".csv", ".tsv", ".txt", ".dat")):
        fmt = "delimited"
        df, meta = _read_delimited(path)
    elif low.endswith((".xlsx", ".xls", ".xlsm")):
        fmt = "excel"
        df, meta = _read_excel(path)
    elif low.endswith(".sav"):
        fmt = "spss"
        df, meta = _read_spss(path)
    else:
        raise ValueError(f"Formato no reconocido: {path}")

    df, coerced, eu = coerce_numeric_columns(df)
    report = {
        "format": fmt,
        "encoding": meta.get("encoding"),
        "delimiter": meta.get("delimiter"),
        "n_rows": len(df),
        "n_cols": len(df.columns),
        "coerced_cols": coerced,
        "european_decimal": eu,
    }
    return {"df": df, "report": report}


def load_dataframe(path):
    """Conveniencia: devuelve solo el DataFrame importado."""
    return read_table(path)["df"]
