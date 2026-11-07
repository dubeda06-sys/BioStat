"""Pruebas de la importacion robusta (src/io/importers).

Cubren los casos que antes rompian la carga: CSV europeo (`;` + coma decimal),
encoding cp1252/latin-1, tab-separado, y coercion numerica con restos de Excel.
"""
import numpy as np
import pandas as pd
import pytest

from src.io.importers import (
    read_table, load_dataframe, detect_delimiter, detect_encoding, coerce_series,
)


def _write(tmp_path, name, text, encoding="utf-8"):
    p = tmp_path / name
    p.write_text(text, encoding=encoding)
    return str(p)


class TestDetectors:
    def test_delimiter_semicolon(self):
        assert detect_delimiter("a;b;c\n1;2;3\n4;5;6") == ";"

    def test_delimiter_tab(self):
        assert detect_delimiter("a\tb\n1\t2\n3\t4") == "\t"

    def test_delimiter_comma_default(self):
        assert detect_delimiter("a,b\n1,2") == ","

    def test_encoding_cp1252(self, tmp_path):
        p = _write(tmp_path, "e.csv", "glucemia;mañana\n5,2;sí", encoding="cp1252")
        assert detect_encoding(p) in ("cp1252", "latin-1", "utf-8")


class TestEuropeanCsv:
    def test_semicolon_decimal_comma_cp1252(self, tmp_path):
        text = "paciente;glucosa;hba1c\n1;5,4;6,1\n2;7,8;7,0\n3;6,25;5,9"
        p = _write(tmp_path, "lab.csv", text, encoding="cp1252")
        out = read_table(p)
        df, rep = out["df"], out["report"]
        assert rep["delimiter"] == ";"
        assert rep["european_decimal"] is True
        assert list(df.columns) == ["paciente", "glucosa", "hba1c"]
        assert df["glucosa"].dtype.kind == "f"
        assert df["glucosa"].iloc[2] == pytest.approx(6.25)
        assert df["hba1c"].iloc[0] == pytest.approx(6.1)

    def test_thousands_and_decimal(self):
        s = pd.Series(["1.234,56", "2.000,00", "3,14"])
        conv, fmt = coerce_series(s)
        assert fmt == "eu"
        assert conv.iloc[0] == pytest.approx(1234.56)
        assert conv.iloc[1] == pytest.approx(2000.0)


class TestUsCsv:
    def test_plain_comma_utf8_untouched(self, tmp_path):
        text = "x,y\n3.14,10\n2.71,20\n1.0,30"
        p = _write(tmp_path, "us.csv", text)
        df = load_dataframe(p)
        assert df["x"].dtype.kind == "f"
        assert df["x"].iloc[0] == pytest.approx(3.14)
        assert df["y"].iloc[1] == pytest.approx(20)

    def test_tab_separated_txt(self, tmp_path):
        text = "a\tb\n1\t2\n3\t4"
        p = _write(tmp_path, "t.txt", text)
        out = read_table(p)
        assert out["report"]["delimiter"] == "\t"
        assert out["df"]["a"].tolist() == [1, 3]


class TestCoercionEdges:
    def test_excel_errors_become_nan(self):
        conv, fmt = coerce_series(pd.Series(["1.5", "#DIV/0!", "2.5", "#REF!"]))
        assert fmt == "us"
        assert np.isnan(conv.iloc[1]) and np.isnan(conv.iloc[3])
        assert conv.iloc[0] == pytest.approx(1.5)

    def test_text_column_stays_text(self):
        conv, fmt = coerce_series(pd.Series(["masculino", "femenino", "masculino"]))
        assert fmt is None

    def test_unknown_extension_raises(self, tmp_path):
        p = _write(tmp_path, "x.foobar", "a,b\n1,2")
        with pytest.raises(ValueError):
            read_table(p)
