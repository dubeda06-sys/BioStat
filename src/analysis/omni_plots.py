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
_BORDE = "#cbd5e1"


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


def _mcbride_zonas():
    """Cortes de McBride GB (2005), NIWA Client Report HAM2005-062."""
    return [(0.00, "pobre", "#fee2e2"), (0.90, "moderada", "#fef3c7"),
            (0.95, "sustancial", "#dcfce7"), (0.99, "casi perfecta", "#bbf7d0")]


def _riel(ax, y, valor, color, etiqueta, alto):
    """Una barra que llega hasta `valor` sobre un riel que llega a 1.

    El riel importa: sin el, una barra de 0,89 y una de 0,99 se ven casi
    iguales. Con el riel se lee cuanto FALTA, que es la pregunta.
    """
    ax.barh(y, 1.0, height=alto, color="#f1f5f9", edgecolor=_BORDE,
            linewidth=0.8, zorder=2)
    ax.barh(y, max(valor, 0.0), height=alto, color=color, zorder=3)
    ax.text(1.02, y, f"{valor:.4g}", va="center", ha="left",
            fontsize=10.5, fontweight="bold", color=color)
    ax.text(-0.02, y, etiqueta, va="center", ha="right", fontsize=10, color=_INK)


def ccc_decomposition_figure(plot_data: dict):
    """CCC de Lin descompuesto: cuanto del desacuerdo es dispersion y cuanto sesgo.

    Dos paneles, y ninguno repite lo que ya se ve en otra figura. La version
    anterior ponia a la izquierda un diagrama de dispersion con la identidad y
    una recta inclinada — o sea, exactamente el grafico de regresion de
    comparacion que esta dos pestanas antes. Repetirlo no agregaba una vista:
    gastaba medio grafico, y ademas quedaba aplastado porque el aspecto
    cuadrado en un panel ancho deja casi la mitad en blanco.

    Izquierda, DONDE CAE este par en el plano precision x veracidad. Como
    rho_c = rho * Cb, las curvas de igual rho_c son hiperbolas, y el punto
    (Cb, rho) dice de un vistazo cual de los dos factores manda. Un punto
    pegado al techo y corrido a la izquierda es un metodo preciso y
    descalibrado: se recalibra. Uno pegado a la derecha y bajo es un metodo
    centrado e impreciso: no hay recalibracion que lo arregle. Esa distincion
    es la razon de ser de la figura y no aparece en ninguna otra.

    Derecha, CUANTO pesa cada cosa. Tres rieles: rho y Cb por separado, cada
    uno sobre un riel que llega a 1 para que se lea cuanto falta, y abajo el
    reparto exacto

        1 - rho_c = (1 - rho) + rho * (1 - Cb)

    que no deja residuo sin nombre.
    """
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

    fig, (ax_mapa, ax_barras) = plt.subplots(
        1, 2, figsize=(12.6, 5.4), gridspec_kw={"width_ratios": [1, 1.1]})

    # ---------- Panel izquierdo: el plano precision x veracidad ----------
    # Con rho<=0 el punto se sale del plano y las hiperbolas no significan
    # nada. Se dice, en vez de dibujar un mapa donde el punto no entra.
    if rho > 0 and cb > 0 and ccc > 0:
        piso = max(0.0, min(0.80, rho - 0.14, cb - 0.14))
        # El techo pasa de 1: en datos buenos rho ronda 0,999 y con el limite
        # justo en 1 el punto queda partido por el borde superior.
        techo = 1.0 + (1.0 - piso) * 0.06
        rejilla = np.linspace(piso, 1.0, 260)
        CB, RHO = np.meshgrid(rejilla, rejilla)
        Z = CB * RHO

        niveles = [v for v, _, _ in _mcbride_zonas()] + [1.0]
        colores = [c for _, _, c in _mcbride_zonas()]
        ax_mapa.contourf(CB, RHO, Z, levels=niveles, colors=colores, alpha=0.75,
                         zorder=1)
        lineas = ax_mapa.contour(CB, RHO, Z, levels=[0.90, 0.95, 0.99],
                                 colors=_MUTED, linewidths=0.9,
                                 linestyles="--", zorder=2)
        ax_mapa.clabel(lineas, fmt="%.2f", fontsize=7.5, inline=True)

        # Guias hasta los ejes: dicen que el punto se lee como par (Cb, rho).
        ax_mapa.plot([cb, cb], [piso, rho], color=_INK, lw=0.8, ls=":", zorder=3)
        ax_mapa.plot([piso, cb], [rho, rho], color=_INK, lw=0.8, ls=":", zorder=3)
        punto = ax_mapa.scatter([cb], [rho], s=200, c=_TEAL,
                                edgecolors="white", linewidths=2.2, zorder=5)
        # gid para que los tests puedan encontrar el punto sin adivinar entre
        # las colecciones de contorno, que tambien exponen get_offsets().
        punto.set_gid("ccc_punto")

        # La etiqueta se corre hacia adentro: pegada a un borde se sale del eje.
        dx = -16 if cb > (piso + techo) / 2 else 16
        dy = -30 if rho > (piso + techo) / 2 else 26
        ax_mapa.annotate(f"\u03c1c = {ccc:.4g}", xy=(cb, rho),
                         xytext=(dx, dy), textcoords="offset points",
                         ha="right" if dx < 0 else "left",
                         va="top" if dy < 0 else "bottom",
                         fontsize=11.5, fontweight="bold", color=_INK,
                         bbox=dict(boxstyle="round,pad=0.35", fc="white",
                                   ec=_TEAL, lw=1.3, alpha=0.96),
                         arrowprops=dict(arrowstyle="-", color=_TEAL, lw=1.1),
                         zorder=6)

        # Las zonas necesitan nombre: sin leyenda son manchas de color.
        zonas = [plt.Rectangle((0, 0), 1, 1, fc=c, alpha=0.75, ec=_BORDE)
                 for _, _, c in _mcbride_zonas()]
        ax_mapa.legend(zonas, [n for _, n, _ in _mcbride_zonas()],
                       title="Concordancia (McBride)", fontsize=7.5,
                       title_fontsize=8, loc="lower left", framealpha=0.95,
                       handlelength=1.1, handleheight=0.9, borderpad=0.5)

        ax_mapa.set_xlim(piso, techo)
        ax_mapa.set_ylim(piso, techo)
        ax_mapa.set_aspect("equal", adjustable="box")
        ax_mapa.set_xlabel("Cb \u2014 veracidad  (1 = sin sesgo)", fontsize=10)
        ax_mapa.set_ylabel("\u03c1 \u2014 precisión  (1 = sin dispersión)", fontsize=10)
    else:
        ax_mapa.text(0.5, 0.5,
                     f"\u03c1 = {rho:.4g}\n\nCon correlación nula o negativa el par\n"
                     f"no cae en el plano precisión \u00d7 veracidad:\n"
                     f"\u03c1c = \u03c1 \u00b7 Cb deja de ser una descomposición.",
                     ha="center", va="center", fontsize=10.5, color=_RED,
                     transform=ax_mapa.transAxes)
        ax_mapa.set_xticks([])
        ax_mapa.set_yticks([])

    ax_mapa.set_title("Dónde cae este par", fontweight="bold", color=_INK,
                      fontsize=11.5, pad=10)

    # ---------- Panel derecho: los tres rieles ----------
    ax_barras.set_xlim(-0.42, 1.16)
    ax_barras.set_ylim(-0.95, 2.8)
    ax_barras.set_yticks([])
    ax_barras.set_xticks([])
    for lado in ("top", "right", "left", "bottom"):
        ax_barras.spines[lado].set_visible(False)
    ax_barras.set_title("Cuánto pesa cada cosa", fontweight="bold", color=_INK,
                        fontsize=11.5, pad=10)

    if rho <= 0 or ccc <= 0:
        ax_barras.text(0.3, 1.0,
                       f"\u03c1c = {ccc:.4g}\n\nNo se puede repartir el desacuerdo:\n"
                       f"la correlación es {'nula' if rho == 0 else 'negativa'} "
                       f"(\u03c1 = {rho:.4g}).\nLos dos métodos no miden lo mismo.",
                       ha="center", va="center", fontsize=10.5, color=_RED)
        fig.suptitle(f"CCC de Lin descompuesto \u2014 {nx} vs {ny}",
                     fontweight="bold", color=_INK, fontsize=13)
        fig.tight_layout(rect=(0, 0.02, 1, 0.93))
        return fig

    ALTO = 0.44
    _riel(ax_barras, 2.25, rho, _TEAL, "\u03c1  precisión", ALTO)
    _riel(ax_barras, 1.5, cb, _AMBER, "Cb  veracidad", ALTO)

    # El reparto exacto, abajo y con su propio riel de fondo.
    perdida_disp = 1.0 - rho
    perdida_sesgo = rho * (1.0 - cb)
    ax_barras.barh(0.55, 1.0, height=ALTO, color="#f1f5f9", edgecolor=_BORDE,
                   linewidth=0.8, zorder=2)
    ax_barras.barh(0.55, ccc, height=ALTO, color=_TEAL, zorder=3)
    ax_barras.barh(0.55, perdida_disp, left=ccc, height=ALTO, color=_RED,
                   alpha=0.8, zorder=3)
    ax_barras.barh(0.55, perdida_sesgo, left=ccc + perdida_disp, height=ALTO,
                   color=_AMBER, alpha=0.9, zorder=3)
    ax_barras.text(-0.02, 0.55, "\u03c1c  lograda", va="center", ha="right",
                   fontsize=10, color=_INK)
    ax_barras.text(1.02, 0.55, f"{ccc:.4g}", va="center", ha="left",
                   fontsize=10.5, fontweight="bold", color=_TEAL)

    if ic and all(v is not None and np.isfinite(float(v)) for v in ic):
        bajo, arriba = float(ic[0]), float(ic[1])
        ax_barras.errorbar(ccc, 0.55, xerr=[[max(ccc - bajo, 0.0)],
                                            [max(arriba - ccc, 0.0)]],
                           fmt="none", ecolor=_INK, elinewidth=1.6, capsize=5,
                           zorder=4)
        pie_ic = f"IC 95 % del \u03c1c: {bajo:.4g} a {arriba:.4g}"
    else:
        pie_ic = "IC 95 % del \u03c1c: no definido con estos datos"

    falta = perdida_disp + perdida_sesgo
    if falta < 0.005:
        reparto = "Prácticamente no falta nada para el acuerdo perfecto."
    else:
        pct_disp = 100.0 * perdida_disp / falta
        reparto = (f"De lo que falta: {pct_disp:.0f} % dispersión \u00b7 "
                   f"{100 - pct_disp:.0f} % sesgo")

    parches = [plt.Rectangle((0, 0), 1, 1, fc=_TEAL),
               plt.Rectangle((0, 0), 1, 1, fc=_RED, alpha=0.8),
               plt.Rectangle((0, 0), 1, 1, fc=_AMBER, alpha=0.9)]
    ax_barras.legend(parches,
                     [f"lograda  {ccc:.3g}",
                      f"perdido por dispersión  {perdida_disp:.3g}",
                      f"perdido por sesgo  {perdida_sesgo:.3g}"],
                     fontsize=8.5, framealpha=0.95, ncol=3,
                     loc="upper center", bbox_to_anchor=(0.42, 0.20),
                     handlelength=1.1, columnspacing=1.0)

    ax_barras.text(0.3, -0.62, reparto, ha="center", va="center",
                   fontsize=9.5, color=_INK)
    ax_barras.text(0.3, -0.85, pie_ic, ha="center", va="center",
                   fontsize=9, color=_MUTED)
    if fuerza:
        ax_barras.text(0.3, 2.72,
                       f"Concordancia {fuerza.lower()} (McBride, 2005)",
                       ha="center", va="center", fontsize=9.5, color=_MUTED)

    fig.suptitle(f"CCC de Lin descompuesto \u2014 {nx} vs {ny}",
                 fontweight="bold", color=_INK, fontsize=13)
    fig.tight_layout(rect=(0, 0.02, 1, 0.93))
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
