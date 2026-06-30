"""Tests del importador robusto (separador/decimal/encoding)."""
import numpy as np
import pandas as pd
import pytest


def _write(tmp_path, name, text, encoding="utf-8"):
    p = tmp_path / name
    p.write_text(text, encoding=encoding)
    return str(p)


def test_csv_latam_punto_y_coma_y_coma_decimal(tmp_path):
    from src.io.importers import read_any
    path = _write(tmp_path, "latam.csv",
                  "Glucosa;Colesterol\n90,5;180,2\n101,0;195,7\n88,3;172,1\n")
    df = read_any(path)
    assert list(df.columns) == ["Glucosa", "Colesterol"]
    assert pd.api.types.is_numeric_dtype(df["Glucosa"])
    assert df["Glucosa"].iloc[0] == pytest.approx(90.5)
    assert df["Colesterol"].iloc[1] == pytest.approx(195.7)


def test_csv_estandar_coma(tmp_path):
    from src.io.importers import read_any
    path = _write(tmp_path, "std.csv", "A,B\n1.5,2.5\n3.0,4.0\n")
    df = read_any(path)
    assert df["A"].iloc[1] == pytest.approx(3.0)
    assert pd.api.types.is_numeric_dtype(df["B"])


def test_csv_tab(tmp_path):
    from src.io.importers import read_any
    path = _write(tmp_path, "t.tsv", "X\tY\n10\t20\n30\t40\n")
    df = read_any(path)
    assert list(df.columns) == ["X", "Y"]
    assert df["Y"].iloc[1] == 40


def test_limpia_codigos_de_error(tmp_path):
    from src.io.importers import read_any
    path = _write(tmp_path, "err.csv", "V\n1.0\n#DIV/0!\n3.0\n")
    df = read_any(path)
    # el codigo de error queda como vacio -> columna numerica con NaN
    assert df["V"].notna().sum() == 2


def test_encoding_latin1(tmp_path):
    from src.io.importers import read_any
    path = _write(tmp_path, "lat.csv", "Año;Valor\n2024;10,5\n2025;11,2\n", encoding="latin-1")
    df = read_any(path)
    assert "Año" in df.columns
    assert df["Valor"].iloc[0] == pytest.approx(10.5)
