"""Importadores robustos de datos para BioStat.

Maneja CSV con separador `,`/`;`/tab/`|` autodetectado, coma decimal (formato
Latam/Europa, habitual en exportaciones de LIS), distintos encodings, y Excel
con fila de cabecera desplazada. Centraliza la limpieza de datos.
"""
import csv
import numpy as np
import pandas as pd

# Codigos de error de hoja de calculo que deben tratarse como vacios
SPREADSHEET_ERRORS = ["#REF!", "#DIV/0!", "#N/A", "#VALUE!", "#NAME?", "#NULL!", "#NUM!"]
_CANDIDATE_SEPS = [";", "\t", "|", ","]


def read_any(file_path):
    """Lee un CSV o Excel y devuelve un DataFrame ya limpio."""
    low = file_path.lower()
    if low.endswith(".csv") or low.endswith(".txt") or low.endswith(".tsv"):
        df = read_csv_smart(file_path)
    elif low.endswith((".xlsx", ".xls")):
        df = read_excel_smart(file_path)
    else:
        raise ValueError(f"Formato no soportado: {file_path}")
    return clean_dataframe(df)


def _read_sample(file_path):
    """Lee una muestra del archivo probando varios encodings. Devuelve (texto, encoding)."""
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            with open(file_path, "r", encoding=enc) as f:
                return f.read(16384), enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    # ultimo recurso: latin-1 nunca falla en decodificacion
    with open(file_path, "r", encoding="latin-1") as f:
        return f.read(16384), "latin-1"


def _detect_separator(sample):
    """Detecta el separador de columnas. csv.Sniffer con respaldo por conteo."""
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t|")
        if dialect.delimiter in _CANDIDATE_SEPS:
            return dialect.delimiter
    except csv.Error:
        pass
    # respaldo: el separador mas frecuente en la primera linea
    first_line = sample.splitlines()[0] if sample.splitlines() else ""
    counts = {s: first_line.count(s) for s in _CANDIDATE_SEPS}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","


def read_csv_smart(file_path):
    """Lee CSV detectando separador, encoding y coma decimal."""
    sample, enc = _read_sample(file_path)
    sep = _detect_separator(sample)
    # Heuristica de decimal: si el separador es ';' y NO hay puntos decimales
    # pero si comas dentro de los campos, asumimos coma decimal (Latam/Europa).
    decimal = "."
    if sep == ";":
        # cuenta comas que parecen decimales (digito,coma,digito)
        import re
        if re.search(r"\d,\d", sample):
            decimal = ","
    df = pd.read_csv(file_path, sep=sep, decimal=decimal, encoding=enc, engine="python")
    return df


def read_excel_smart(file_path):
    """Lee Excel detectando la fila de cabecera (primera con >=2 celdas no vacias)."""
    raw = pd.read_excel(file_path, header=None)
    header_row = 0
    for i in range(min(10, len(raw))):
        if raw.iloc[i].notna().sum() >= 2:
            header_row = i
            break
    df = pd.read_excel(file_path, header=header_row)
    return df


def clean_dataframe(df):
    """Quita columnas 'Unnamed'/vacias, filas totalmente vacias, codigos de error,
    y convierte a numerico lo que se pueda (incluida coma decimal residual)."""
    if df is None or len(df) == 0:
        return df
    df.columns = [str(c).strip() for c in df.columns]
    drop = [c for c in df.columns if "unnamed" in c.lower() or df[c].isna().all()]
    if drop:
        df = df.drop(columns=drop)
    df = df.dropna(how="all").reset_index(drop=True)

    for col in df.columns:
        if df[col].dtype == object:
            cleaned = df[col].astype(str)
            for e in SPREADSHEET_ERRORS:
                cleaned = cleaned.str.replace(e, "", regex=False)
            # coma decimal residual -> punto (solo si parece numero)
            maybe = cleaned.str.strip().str.replace(",", ".", regex=False)
            try:
                df[col] = pd.to_numeric(maybe)
            except (ValueError, TypeError):
                # dejar la columna como texto (categorica)
                pass
    return df
