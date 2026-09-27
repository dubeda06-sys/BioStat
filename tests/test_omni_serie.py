"""Omnianálisis: fecha × numérica ahora se analiza como serie temporal.

Hasta el 27 sep la estructura temporal se detectaba y se avisaba que «este
árbol no cubre series de tiempo». Ahora cada numérica contra la fecha lleva:

- Mann-Kendall: la τ de Kendall entre el tiempo y el valor (oráculo: scipy);
- pendiente de Sen con IC 95 % (oráculo: scipy.stats.theilslopes);
- Ljung-Box sobre los residuos de la recta de Sen (oráculo: statsmodels).
"""
import numpy as np
import pandas as pd
import pytest
from scipy import stats

from src.analysis.omni_analyzer import run_omnianalysis, _classify_column
from src.analysis.omni_auditoria import auditar
from src.analysis.omni_caso import casos
from src.analysis.omni_config import DEFAULT_CONFIG as CFG
from src.analysis.omni_plots import serie_figure


def _bloque(rep):
    return next(b for b in rep["blocks"] if b.get("tipo") == "serie temporal")


def _serie(n=60, pendiente=0.0, ar=0.0, semilla=1, faltan=0):
    rng = np.random.default_rng(semilla)
    fechas = pd.date_range("2025-07-01", periods=n, freq="3D")
    ruido = np.zeros(n)
    e = rng.normal(0, 1, n)
    for i in range(n):
        ruido[i] = (ar * ruido[i - 1] if i else 0) + e[i]
    y = 25 + pendiente * np.arange(n) * 3 + ruido
    df = pd.DataFrame({"Fecha": fechas, "Ct": y})
    if faltan:
        df.loc[rng.choice(n, faltan, replace=False), "Ct"] = np.nan
    return df


def test_mann_kendall_y_sen_coinciden_con_scipy():
    df = _serie(pendiente=0.02, semilla=2, faltan=4)
    b = _bloque(run_omnianalysis(df, ["Fecha", "Ct"]))
    ok = df.dropna()
    dias = (ok["Fecha"] - ok["Fecha"].iloc[0]).dt.days.to_numpy(dtype=float)
    tau, p = stats.kendalltau(dias, ok["Ct"])
    sen = stats.theilslopes(ok["Ct"], dias, alpha=0.95)
    pr = b["pruebas"][0]
    assert pr["prueba"] == "Mann-Kendall"
    assert pr["estadístico"] == pytest.approx(tau, abs=1e-4)
    assert pr["p"] == pytest.approx(p, abs=1e-4)
    se = b["resultados"]["serie"]
    assert se["n"] == len(ok)
    assert se["pendiente_sen_dia"] == pytest.approx(sen.slope)
    assert se["ic95_dia"] == pytest.approx((sen.low_slope, sen.high_slope))
    assert se["cambio_en_el_periodo"] == pytest.approx(sen.slope * dias[-1])


def test_ljung_box_coincide_con_statsmodels():
    from statsmodels.stats.diagnostic import acorr_ljungbox
    df = _serie(ar=0.7, semilla=3)
    b = _bloque(run_omnianalysis(df, ["Fecha", "Ct"]))
    dias = (df["Fecha"] - df["Fecha"].iloc[0]).dt.days.to_numpy(dtype=float)
    y = df["Ct"].to_numpy()
    sen = stats.theilslopes(y, dias)
    res = y - (sen.intercept + sen.slope * dias)
    lb = acorr_ljungbox(res, lags=[10], return_df=True)
    ac = b["resultados"]["serie"]["autocorrelacion"]
    assert ac["rezagos"] == 10
    assert ac["p"] == pytest.approx(float(lb["lb_pvalue"].iloc[0]), abs=1e-4)
    assert ac["p"] < 0.05
    assert any("rachas" in a for a in b["advertencias"])


def test_detecta_una_tendencia_real_y_no_inventa_una():
    con = _bloque(run_omnianalysis(_serie(pendiente=0.03, semilla=4), ["Fecha", "Ct"]))
    sin = _bloque(run_omnianalysis(_serie(pendiente=0.0, semilla=5), ["Fecha", "Ct"]))
    assert con["pruebas"][0]["detectado"] is True
    assert "Se detectó tendencia en el tiempo" in con["conclusion"]
    assert sin["pruebas"][0]["detectado"] is False


def test_el_error_tipo_i_de_la_tendencia_sin_autocorrelacion():
    detecta = 0
    for s in range(200):
        b = _bloque(run_omnianalysis(_serie(n=40, semilla=100 + s), ["Fecha", "Ct"]))
        detecta += b["pruebas"][0]["detectado"]
    assert detecta / 200 < 0.09


def test_la_auditoria_marca_los_dos_ensayos_y_el_perfil():
    rep = run_omnianalysis(_serie(), ["Fecha", "Ct"])
    est = auditar(rep)["estado"]
    assert est["perfil_temporal"] == "ejecutado"
    assert est["mann_kendall"] == "ejecutado"
    assert est["autocorrelacion"] == "ejecutado"
    assert not any("no cubre series" in w for w in rep["warnings_globales"])


def _sin_fecha(df, cuantas):
    """Filas sin fecha: la numérica sigue teniendo más de 10 valores distintos
    (con menos, el perfilado la toma como ambigua) pero la serie queda corta."""
    df = df.copy()
    df.loc[df.index[:cuantas], "Fecha"] = pd.NaT
    return df


def test_serie_corta_no_corre_la_autocorrelacion_y_lo_dice():
    b = _bloque(run_omnianalysis(_sin_fecha(_serie(n=12), 5), ["Fecha", "Ct"]))
    assert b["resultados"]["serie"]["n"] == 7
    assert b["pruebas"][0]["prueba"] == "Mann-Kendall"
    assert "autocorrelacion" not in b["resultados"]["serie"]
    assert any("no se puede verificar que las mediciones sean independientes" in a
               for a in b["advertencias"])
    corta = _bloque(run_omnianalysis(_sin_fecha(_serie(n=12), 8), ["Fecha", "Ct"]))
    assert corta["pruebas"] == []
    assert "demasiado corta" in corta["conclusion"]


def test_fechas_como_texto_de_un_csv():
    df = _serie(pendiente=0.03, semilla=6)
    df["Fecha"] = df["Fecha"].dt.strftime("%d/%m/%Y")
    assert _classify_column(df["Fecha"], CFG)["tipo"] == "fecha/tiempo"
    b = _bloque(run_omnianalysis(df, ["Fecha", "Ct"]))
    assert b["resultados"]["serie"]["desde"] == "2025-07-01"
    # «1», «2», «3» no son fechas aunque pandas los pueda leer como días
    assert _classify_column(pd.Series(["1", "2", "3", "4"] * 5), CFG)["tipo"] != "fecha/tiempo"


def test_el_caso_narrado_y_el_grafico():
    rep = run_omnianalysis(_serie(pendiente=0.03, semilla=7), ["Fecha", "Ct"])
    caso = next(c for c in casos(rep) if c.tipo == "¿Cambia con el tiempo?")
    preguntas = [p.pregunta for p in caso.pasos]
    assert preguntas[0].startswith("¿Cuántas mediciones")
    assert any("rachas" in p.consecuencia or "independiente" in p.consecuencia for p in caso.pasos)
    assert "por día" in caso.pasos[-1].consecuencia
    import matplotlib.pyplot as plt
    fig = serie_figure(_bloque(rep)["resultados"]["_plot_serie"])
    assert fig.axes[0].get_title() == "Ct en el tiempo"
    plt.close(fig)
