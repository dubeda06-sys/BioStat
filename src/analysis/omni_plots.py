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


def ccc_decomposition_figure(plot_data: dict):
    """CCC de Lin descompuesto: cuanto del desacuerdo es dispersion y cuanto sesgo.

    Dos paneles porque son dos preguntas distintas:

    Izquierda, DONDE se ve. El eje mayor reducido (RMA) es la recta cuya
    pendiente es sigma_y/sigma_x y que pasa por (media_x, media_y): sus dos
    desvios respecto de la identidad — corrimiento y cambio de escala — son
    exactamente los dos ingredientes de Cb. Asi que la dispersion alrededor de
    la recta ambar es `rho`, y la separacion entre la ambar y la gris es `Cb`.

    Derecha, CUANTO pesa cada uno. La descomposicion se reparte exacta:

        1 - rho_c = (1 - rho) + rho * (1 - Cb)

    o sea que lo que falta para la concordancia perfecta se corta en un pedazo
    de dispersion y uno de sesgo sin residuo. Importa separarlos porque se
    arreglan por vias distintas: el sesgo se recalibra, la dispersion no.
    """
    x = np.asarray(plot_data["x"], dtype=float)
    y = np.asarray(plot_data["y"], dtype=float)
    nx, ny = plot_data.get("nombre_x", "X"), plot_data.get("nombre_y", "Y")
    ccc = plot_data.get("ccc")
    rho = plot_data.get("ccc_rho")
    cb = plot_data.get("ccc_cb")
    fuerza = plot_data.get("ccc_fuerza", "")
    ic = plot_data.get("ccc_ic95")

    if ccc is None or rho is None or cb is None:
        raise ValueError("faltan los componentes del CCC en los datos de gráfico")
    ccc, rho, cb = float(ccc), float(rho), float(cb)
    if not all(np.isfinite(v) for v in (ccc, rho, cb)):
        raise ValueError("los componentes del CCC no son finitos")

    fig, (ax_disp, ax_barra) = plt.subplots(
        1, 2, figsize=(11.8, 4.8), gridspec_kw={"width_ratios": [1.25, 1]})

    # ---------- Panel izquierdo: identidad vs eje mayor reducido ----------
    lo = float(min(x.min(), y.min()))
    hi = float(max(x.max(), y.max()))
    pad = (hi - lo) * 0.05 or 1.0
    lims = [lo - pad, hi + pad]

    ax_disp.scatter(x, y, s=40, c=_TEAL, alpha=0.7, edgecolors="white",
                    linewidths=0.6, zorder=3)
    ax_disp.plot(lims, lims, ls="--", color=_MUTED, lw=1.3, zorder=2,
                 label="Identidad (y = x) — acuerdo perfecto")

    sx, sy = np.std(x, ddof=0), np.std(y, ddof=0)
    if sx > 0 and sy > 0:
        signo = np.sign(np.mean((x - x.mean()) * (y - y.mean()))) or 1.0
        pend = signo * sy / sx
        orden = y.mean() - pend * x.mean()
        xr = np.array(lims)
        ax_disp.plot(xr, pend * xr + orden, color=_AMBER, lw=1.8, zorder=2,
                     label=f"La recta que Cb compara con la gris "
                           f"(pendiente {pend:.3g})")

    ax_disp.set_xlim(lims)
    ax_disp.set_ylim(lims)
    ax_disp.set_aspect("equal", adjustable="box")
    ax_disp.set_xlabel(nx)
    ax_disp.set_ylabel(ny)
    ax_disp.set_title("Lo que se ve", fontweight="bold", color=_INK, fontsize=11)
    ax_disp.legend(fontsize=8, framealpha=0.9, loc="upper left")
    ax_disp.grid(True, alpha=0.25)
    # Ojo con el texto de esta ayuda: la recta ambar se inclina por el cociente
    # de dispersiones, no solo por descalibracion. Decir "la ambar lejos de la
    # gris = mal calibrado" seria falso — con ruido grande se inclina sola. Se
    # afirma solo lo que Cb realmente mide.
    ax_disp.text(0.5, -0.20,
                 "Cuanto más apretados los puntos contra la ámbar, mayor la precisión (ρ).\n"
                 "Cuanto más se aparta la ámbar de la gris, menor la veracidad (Cb).",
                 transform=ax_disp.transAxes, ha="center", va="top",
                 fontsize=8.5, color=_INK)

    # ---------- Panel derecho: la descomposicion, repartida ----------
    ax_barra.set_xlim(0, 1)
    ax_barra.set_ylim(-0.6, 0.82)
    ax_barra.set_yticks([])
    ax_barra.set_xticks(np.linspace(0, 1, 6))
    ax_barra.set_xlabel("Concordancia (0 = ninguna, 1 = perfecta)")
    ax_barra.grid(True, axis="x", alpha=0.25)
    ax_barra.set_title("Cómo se reparte", fontweight="bold", color=_INK, fontsize=11)

    # Con rho<=0 o CCC<=0 el reparto no tiene sentido: los pedazos saldrian
    # negativos o mayores que 1. Se dice, en vez de dibujar una barra falsa.
    if rho <= 0 or ccc <= 0:
        ax_barra.text(0.5, 0.1,
                      f"ρc = {ccc:.4g}\n\nNo se puede repartir el desacuerdo:\n"
                      f"la correlación es {'nula' if rho == 0 else 'negativa'} "
                      f"(ρ = {rho:.4g}).\nLos dos métodos no miden lo mismo.",
                      ha="center", va="center", fontsize=10, color=_RED)
        fig.suptitle(f"CCC de Lin descompuesto — {nx} vs {ny}",
                     fontweight="bold", color=_INK, fontsize=12.5)
        fig.tight_layout(rect=(0, 0.02, 1, 0.94))
        return fig

    perdida_disp = 1.0 - rho
    perdida_sesgo = rho * (1.0 - cb)
    alto = 0.34

    ax_barra.barh(0.25, ccc, height=alto, color=_TEAL, zorder=3,
                  label=f"Concordancia lograda — ρc = {ccc:.4g}")
    ax_barra.barh(0.25, perdida_disp, left=ccc, height=alto, color=_RED,
                  alpha=0.75, zorder=3,
                  label=f"Perdido por dispersión — 1−ρ = {perdida_disp:.4g}")
    ax_barra.barh(0.25, perdida_sesgo, left=ccc + perdida_disp, height=alto,
                  color=_AMBER, alpha=0.85, zorder=3,
                  label=f"Perdido por sesgo — ρ(1−Cb) = {perdida_sesgo:.4g}")

    if ic and all(v is not None and np.isfinite(float(v)) for v in ic):
        bajo, arriba = float(ic[0]), float(ic[1])
        ax_barra.errorbar(ccc, 0.25, xerr=[[ccc - bajo], [arriba - ccc]],
                          fmt="none", ecolor=_INK, elinewidth=1.4, capsize=5,
                          zorder=4)
        pie_ic = f"IC 95% del ρc: {bajo:.4g} a {arriba:.4g}"
    else:
        pie_ic = "IC 95% del ρc: no definido con estos datos"

    ax_barra.legend(fontsize=8.5, framealpha=0.95, loc="lower center",
                    bbox_to_anchor=(0.5, -0.02))

    falta = perdida_disp + perdida_sesgo
    # Umbral solo de presentacion: por debajo de esto los porcentajes del reparto
    # bailan con el redondeo y no dicen nada.
    if falta < 0.005:
        reparto = "Prácticamente no falta nada para el acuerdo perfecto."
    else:
        pct_disp = 100.0 * perdida_disp / falta
        reparto = (f"De lo que falta, {pct_disp:.0f} % es dispersión y "
                   f"{100 - pct_disp:.0f} % es sesgo.")

    # Tres renglones y no dos: juntos se pasaban del ancho del panel y la ultima
    # cifra del IC quedaba cortada por el borde.
    ax_barra.text(0.5, 0.72,
                  f"ρ (precisión) = {rho:.4g}   ·   Cb (veracidad) = {cb:.4g}"
                  + (f"   ·   {fuerza}" if fuerza else ""),
                  transform=ax_barra.transData, ha="center", va="center",
                  fontsize=9.5, color=_INK)
    ax_barra.text(0.5, 0.60, reparto, transform=ax_barra.transData,
                  ha="center", va="center", fontsize=9, color=_INK)
    ax_barra.text(0.5, 0.49, pie_ic, transform=ax_barra.transData,
                  ha="center", va="center", fontsize=8.5, color=_MUTED)

    fig.suptitle(f"CCC de Lin descompuesto — {nx} vs {ny}",
                 fontweight="bold", color=_INK, fontsize=12.5)
    fig.tight_layout(rect=(0, 0.02, 1, 0.94))
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
    try:
        figs.append(("CCC de Lin descompuesto", ccc_decomposition_figure(plot_data)))
    except Exception:
        pass
    return figs
