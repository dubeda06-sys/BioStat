"""Gráficos de comparación de métodos (CLSI EP09) para el Omnianálisis.

Construye figuras matplotlib a partir del diccionario `_plot` que produce
`concordance_analysis`:
  - Gráfico de diferencias de Bland-Altman (sesgo + límites de acuerdo).
  - Diagrama de dispersión con recta de regresión (Passing-Bablok / Deming) y
    línea de identidad (y = x).

Las funciones devuelven objetos `Figure`; la UI los pinta con FigureCanvas.
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_TEAL = "#0e7490"
_INK = "#1e293b"
_MUTED = "#64748b"
_RED = "#dc2626"
_AMBER = "#d97706"


def bland_altman_figure(plot_data: dict):
    """Gráfico de Bland-Altman: diferencias (Y−X) vs promedio."""
    x = np.asarray(plot_data["x"], dtype=float)
    y = np.asarray(plot_data["y"], dtype=float)
    nx, ny = plot_data.get("nombre_x", "X"), plot_data.get("nombre_y", "Y")
    means = (x + y) / 2
    diffs = y - x
    bias = plot_data.get("sesgo")
    loa = plot_data.get("loa", (None, None))
    tipo = plot_data.get("ba_tipo", "paramétrico")

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.scatter(means, diffs, s=42, c=_TEAL, alpha=0.7, edgecolors="white", linewidths=0.6, zorder=3)

    if bias is not None:
        ax.axhline(bias, color=_INK, lw=1.6, zorder=2,
                   label=f"Sesgo = {bias:.3g}")
    lo, hi = loa
    if lo is not None and hi is not None:
        ax.axhline(hi, color=_RED, ls="--", lw=1.3, zorder=2,
                   label=f"LoA sup = {hi:.3g}")
        ax.axhline(lo, color=_RED, ls="--", lw=1.3, zorder=2,
                   label=f"LoA inf = {lo:.3g}")
        ax.fill_between([means.min(), means.max()], lo, hi, color=_RED, alpha=0.05, zorder=1)
    ax.axhline(0, color=_MUTED, lw=0.8, ls=":", zorder=1)

    ax.set_xlabel(f"Promedio de los métodos  ({nx} + {ny})/2")
    ax.set_ylabel(f"Diferencia  ({ny} − {nx})")
    ax.set_title(f"Bland-Altman ({tipo}) — {nx} vs {ny}", fontweight="bold", color=_INK)
    ax.legend(fontsize=9, framealpha=0.9, loc="best")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    return fig


def comparison_regression_figure(plot_data: dict):
    """Dispersión Y vs X con recta de comparación (Passing-Bablok/Deming) e identidad."""
    x = np.asarray(plot_data["x"], dtype=float)
    y = np.asarray(plot_data["y"], dtype=float)
    nx, ny = plot_data.get("nombre_x", "X"), plot_data.get("nombre_y", "Y")
    slope = plot_data.get("reg_slope")
    intercept = plot_data.get("reg_intercept")
    metodo = plot_data.get("reg_metodo", "regresión")

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    lo = float(min(x.min(), y.min()))
    hi = float(max(x.max(), y.max()))
    pad = (hi - lo) * 0.05 or 1.0
    lims = [lo - pad, hi + pad]

    ax.scatter(x, y, s=42, c=_TEAL, alpha=0.7, edgecolors="white", linewidths=0.6, zorder=3)
    ax.plot(lims, lims, ls="--", color=_MUTED, lw=1.2, label="Identidad (y = x)", zorder=2)
    if slope is not None and intercept is not None:
        xr = np.array(lims)
        ax.plot(xr, slope * xr + intercept, color=_AMBER, lw=1.8, zorder=2,
                label=f"{metodo}: y = {slope:.3g}·x + {intercept:.3g}")

    ax.set_xlim(lims); ax.set_ylim(lims)
    ax.set_xlabel(f"{nx} (método comparativo)")
    ax.set_ylabel(f"{ny} (método a evaluar)")
    ax.set_title(f"Regresión de comparación — {nx} vs {ny}", fontweight="bold", color=_INK)
    ax.legend(fontsize=9, framealpha=0.9, loc="best")
    ax.grid(True, alpha=0.25)
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    return fig


def comparison_figures(plot_data: dict):
    """Devuelve [(titulo, Figure), ...] para un par comparado."""
    figs = []
    try:
        figs.append(("Bland-Altman", bland_altman_figure(plot_data)))
    except Exception:
        pass
    try:
        figs.append(("Regresión de comparación", comparison_regression_figure(plot_data)))
    except Exception:
        pass
    return figs
