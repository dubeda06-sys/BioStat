"""Dibujo del arbol de decisiones del Omnianalisis, con el camino recorrido.

Cada etapa del arbol se dibuja aparte. Meter los 40 ensayos en una sola figura
da algo ilegible; cinco figuras chicas se leen.

Los nodos se pintan segun lo que hizo la corrida:

  verde  ejecutado           el motor corrio ese ensayo
  gris   descartado          lo evaluo y eligio la otra rama, con motivo
  claro  no aplica           nunca se llego a ese nodo
  azul   nodo de decision    no es un ensayo, es la pregunta que bifurca

Sin auditoria, sale el arbol en blanco: sirve como mapa del motor.

El layout es a mano y no automatico a proposito. Un grafo auto-ubicado cruza
aristas y mueve los nodos de lugar entre corridas; este arbol se lee siempre
igual, que es lo que hace falta para compararlo contra otra corrida.
"""
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from src.analysis.omni_auditoria import DESCARTADO, EJECUTADO, NO_APLICA
from src.analysis.omni_catalogo import (
    BIVARIADO, CONCORDANCIA, ETAPAS, MULTIVARIADO, PERFILADO, POR_ID, UNIVARIADO,
)

# ---- Paleta -------------------------------------------------------------
_ESTILO = {
    EJECUTADO:  {"fondo": "#dcfce7", "borde": "#15803d", "texto": "#14532d",
                 "lw": 1.8, "ls": "solid"},
    DESCARTADO: {"fondo": "#f1f5f9", "borde": "#94a3b8", "texto": "#64748b",
                 "lw": 1.0, "ls": "solid"},
    NO_APLICA:  {"fondo": "#ffffff", "borde": "#cbd5e1", "texto": "#94a3b8",
                 "lw": 0.9, "ls": "dashed"},
}
_DECISION = {"fondo": "#e0f2fe", "borde": "#0e7490", "texto": "#0c4a6e",
             "lw": 1.4, "ls": "solid"}

_ANCHO_CAJA = 1.72
_ALTO_CAJA = 0.62


# ---- Nodos de decision (no son ensayos) ---------------------------------
# clave -> texto que se muestra. Las claves arrancan con "?" para no chocar
# nunca con un id del catalogo.
DECISIONES = {
    "?datos": "DATOS\ncargados",
    "?rama": "¿Cuántas\ncolumnas?\n1→A 2→B 3+→C",
    "?tipo": "¿Tipo de la\ncolumna?",
    "?tipos_par": "¿Tipos\ndel par?",
    "?norm_par": "¿Ambas\nnormales?",
    "?k_grupos": "¿Cuántos\ngrupos?",
    "?esperadas": "¿Esperadas\n≥ 5?",
    "?confirma": "El usuario\nconfirma el par",
    "?rama_c": "Rama C\n(3+ columnas)",
    "?objetivo": "¿Hay variable\nobjetivo?",
}


# ---- Layout: (clave, columna, fila) y aristas (origen, destino, etiqueta)
LAYOUT = {
    PERFILADO: {
        "nodos": [
            ("?datos", 0, 1.0),
            ("perfil_tipos", 1, 2.0),
            ("perfil_estructura", 1, 1.0),
            ("perfil_temporal", 1, 0.0),
            ("?rama", 2, 1.0),
        ],
        "aristas": [
            ("?datos", "perfil_tipos", ""),
            ("?datos", "perfil_estructura", ""),
            ("?datos", "perfil_temporal", ""),
            ("perfil_tipos", "?rama", ""),
            ("perfil_estructura", "?rama", ""),
        ],
    },
    UNIVARIADO: {
        "nodos": [
            ("?tipo", 0, 2.0),
            ("desc_numericos", 1, 4.2),
            ("tukey_outliers", 1, 2.8),
            ("frecuencias", 1, 1.4),
            ("moda", 1, 0.7),
            ("entropia", 1, 0.0),
            ("shapiro", 2, 4.9),
            ("anderson", 2, 3.5),
            ("central_media", 3, 4.9),
            ("central_mediana", 3, 3.5),
        ],
        "aristas": [
            ("?tipo", "desc_numericos", "numérica"),
            ("?tipo", "tukey_outliers", ""),
            ("?tipo", "frecuencias", "categórica"),
            ("?tipo", "moda", ""),
            ("?tipo", "entropia", ""),
            ("desc_numericos", "shapiro", "n ≤ 5000"),
            ("desc_numericos", "anderson", "n > 5000"),
            ("shapiro", "central_media", "normal"),
            ("shapiro", "central_mediana", "no normal"),
            ("anderson", "central_media", ""),
            ("anderson", "central_mediana", ""),
        ],
    },
    BIVARIADO: {
        "nodos": [
            ("?tipos_par", 0, 3.0),
            ("?norm_par", 1, 6.0),
            ("pearson", 2, 6.6),
            ("spearman", 2, 5.4),
            ("levene", 1, 3.0),
            ("?k_grupos", 2, 3.0),
            ("t_student", 3, 4.4),
            ("t_welch", 3, 3.6),
            ("mann_whitney", 3, 2.8),
            ("anova", 3, 1.8),
            ("kruskal", 3, 1.0),
            ("tukey_hsd", 4, 1.8),
            ("dunn", 4, 1.0),
            ("?esperadas", 1, 0.0),
            ("chi2", 2, 0.4),
            ("fisher", 2, -0.4),
        ],
        "aristas": [
            ("?tipos_par", "?norm_par", "num × num"),
            ("?norm_par", "pearson", "sí"),
            ("?norm_par", "spearman", "no"),
            ("?tipos_par", "levene", "num × cat"),
            ("levene", "?k_grupos", ""),
            ("?k_grupos", "t_student", "2, normal, var="),
            ("?k_grupos", "t_welch", "2, normal, var≠"),
            ("?k_grupos", "mann_whitney", "2, no normal"),
            ("?k_grupos", "anova", "3+, normal"),
            ("?k_grupos", "kruskal", "3+, no normal"),
            ("anova", "tukey_hsd", "si p<α"),
            ("kruskal", "dunn", "si p<α"),
            ("?tipos_par", "?esperadas", "cat × cat"),
            ("?esperadas", "chi2", "sí"),
            ("?esperadas", "fisher", "no (2×2)"),
        ],
    },
    CONCORDANCIA: {
        "nodos": [
            ("score_comparacion", 0, 1.8),
            ("?confirma", 1, 1.8),
            ("estructura_diferencia", 2, 3.4),
            ("normalidad_diferencias", 2, 2.2),
            ("ccc", 2, 0.2),
            ("ba_parametrico", 3, 3.6),
            ("ba_no_parametrico", 3, 2.8),
            ("deming", 3, 1.8),
            ("passing_bablok", 3, 1.0),
            ("ccc_descomposicion", 3, 0.2),
            ("sesgo_niveles", 4, 1.4),
        ],
        "aristas": [
            ("score_comparacion", "?confirma", "score ≥ umbral"),
            ("?confirma", "estructura_diferencia", ""),
            ("?confirma", "normalidad_diferencias", ""),
            ("?confirma", "ccc", ""),
            ("normalidad_diferencias", "ba_parametrico", "normales"),
            ("normalidad_diferencias", "ba_no_parametrico", "no normales"),
            ("estructura_diferencia", "deming", "constante"),
            ("estructura_diferencia", "passing_bablok", "proporcional"),
            ("deming", "sesgo_niveles", ""),
            ("passing_bablok", "sesgo_niveles", ""),
            ("ccc", "ccc_descomposicion", ""),
        ],
    },
    MULTIVARIADO: {
        "nodos": [
            ("?rama_c", 0, 1.4),
            ("matriz_correlacion", 1, 2.6),
            ("?objetivo", 1, 0.8),
            ("fdr_bh", 2, 2.6),
            ("regresion_multiple", 2, 1.4),
            ("pca", 2, 0.2),
            ("vif", 3, 1.4),
            ("clustering", 3, 0.2),
        ],
        "aristas": [
            ("?rama_c", "matriz_correlacion", "2+ numéricas"),
            ("?rama_c", "?objetivo", ""),
            ("matriz_correlacion", "fdr_bh", "obligatorio"),
            ("?objetivo", "regresion_multiple", "sí"),
            ("?objetivo", "pca", "no"),
            ("regresion_multiple", "vif", ""),
            ("pca", "clustering", ""),
        ],
    },
}


def _etiqueta(clave, auditoria):
    """Texto del nodo. Los ejecutados llevan el conteo."""
    if clave.startswith("?"):
        return DECISIONES.get(clave, clave)
    ens = POR_ID.get(clave)
    nombre = ens.nombre if ens else clave
    texto = "\n".join(textwrap.wrap(nombre, 22))
    if auditoria:
        # El color solo no alcanza: gris "descartado" y gris "no aplica" se
        # confunden, y son cosas distintas. La palabra lo desambigua.
        estado = auditoria.get("estado", {}).get(clave)
        if estado == EJECUTADO:
            fila = next((f for f in auditoria.get("filas", []) if f["id"] == clave), None)
            texto += f"\n×{fila['veces'] if fila else 1}"
        elif estado == DESCARTADO:
            texto += "\ndescartado"
        else:
            texto += "\nno aplica"
    return texto


def _estilo(clave, auditoria):
    if clave.startswith("?"):
        return _DECISION
    if not auditoria:
        return _ESTILO[NO_APLICA]
    return _ESTILO.get(auditoria.get("estado", {}).get(clave, NO_APLICA),
                       _ESTILO[NO_APLICA])


def figura_etapa(etapa: str, auditoria: dict | None = None):
    """Figura del subarbol de una etapa, coloreado por lo que hizo la corrida."""
    layout = LAYOUT[etapa]
    nodos = layout["nodos"]
    pos = {clave: (col, fila) for clave, col, fila in nodos}

    cols = [c for _, c, _ in nodos]
    filas = [f for _, _, f in nodos]
    ancho = (max(cols) - min(cols) + 1) * (_ANCHO_CAJA + 0.85)
    alto = (max(filas) - min(filas) + 1) * (_ALTO_CAJA + 0.30)

    fig, ax = plt.subplots(figsize=(max(6.5, ancho), max(2.6, alto)))
    ax.set_axis_off()

    # Cuando varias aristas salen del mismo nodo, sus etiquetas caen todas a la
    # misma distancia y se pisan. Se escalonan a lo largo de la arista.
    salidas = {}
    for origen, _, _ in layout["aristas"]:
        salidas[origen] = salidas.get(origen, 0) + 1
    vistas = {}

    # Aristas primero, para que las cajas queden encima.
    for origen, destino, etiqueta in layout["aristas"]:
        if origen not in pos or destino not in pos:
            continue
        x0, y0 = pos[origen]
        x1, y1 = pos[destino]
        # Del borde derecho del origen al borde izquierdo del destino.
        xa = x0 * (_ANCHO_CAJA + 0.85) + _ANCHO_CAJA / 2
        xb = x1 * (_ANCHO_CAJA + 0.85) - _ANCHO_CAJA / 2
        ya = y0 * (_ALTO_CAJA + 0.30)
        yb = y1 * (_ALTO_CAJA + 0.30)
        # La arista se apaga si el destino no se ejecuto: asi el camino
        # realmente recorrido salta a la vista. Un nodo de decision no se
        # "ejecuta", hereda del origen — si no, el camino queda cortado en cada
        # pregunta del arbol.
        estados = (auditoria or {}).get("estado", {})
        origen_activo = origen.startswith("?") or estados.get(origen) == EJECUTADO
        if destino.startswith("?"):
            activo = bool(auditoria) and origen_activo
        else:
            # Los dos extremos: si el destino corrio pero por la OTRA rama, esta
            # arista no es el camino que se recorrio.
            activo = origen_activo and estados.get(destino) == EJECUTADO
        ax.annotate("", xy=(xb, yb), xytext=(xa, ya),
                    arrowprops=dict(arrowstyle="-|>", color="#15803d" if activo else "#cbd5e1",
                                    lw=1.6 if activo else 0.9,
                                    connectionstyle="arc3,rad=0.05",
                                    shrinkA=0, shrinkB=2))
        indice = vistas.get(origen, 0)
        vistas[origen] = indice + 1
        if etiqueta:
            # Cerca del origen: en un abanico, el punto medio de cada arista cae
            # encima de la caja vecina. Se escalona entre 0,22 y 0,52.
            n_salidas = salidas.get(origen, 1)
            t = 0.22 + (0.30 * indice / max(1, n_salidas - 1) if n_salidas > 1 else 0.0)
            ax.text(xa + (xb - xa) * t, ya + (yb - ya) * t, etiqueta,
                    ha="center", va="center", fontsize=6.4,
                    color="#0e7490" if activo else "#94a3b8", zorder=5,
                    bbox=dict(boxstyle="round,pad=0.14", facecolor="white",
                              edgecolor="none", alpha=0.85))

    for clave, col, fila in nodos:
        est = _estilo(clave, auditoria)
        x = col * (_ANCHO_CAJA + 0.85)
        y = fila * (_ALTO_CAJA + 0.30)
        caja = FancyBboxPatch(
            (x - _ANCHO_CAJA / 2, y - _ALTO_CAJA / 2), _ANCHO_CAJA, _ALTO_CAJA,
            boxstyle="round,pad=0.03,rounding_size=0.08",
            facecolor=est["fondo"], edgecolor=est["borde"],
            linewidth=est["lw"], linestyle=est["ls"], zorder=3,
        )
        ax.add_patch(caja)
        ax.text(x, y, _etiqueta(clave, auditoria), ha="center", va="center",
                fontsize=7.0, color=est["texto"], zorder=4,
                fontweight="bold" if not clave.startswith("?") and
                _estilo(clave, auditoria) is _ESTILO[EJECUTADO] else "normal")

    paso = _ANCHO_CAJA + 0.85
    ax.set_xlim(min(cols) * paso - _ANCHO_CAJA, max(cols) * paso + _ANCHO_CAJA)
    paso_y = _ALTO_CAJA + 0.30
    ax.set_ylim(min(filas) * paso_y - _ALTO_CAJA * 1.4,
                max(filas) * paso_y + _ALTO_CAJA * 1.4)
    ax.set_title(etapa, fontsize=10, fontweight="bold", color="#0e7490", loc="left")
    fig.tight_layout()
    return fig


def figuras(auditoria: dict | None = None):
    """[(etapa, Figure), ...] en orden de ejecucion del arbol."""
    return [(etapa, figura_etapa(etapa, auditoria)) for etapa in ETAPAS]


def figura_resumen(auditoria: dict):
    """Barras apiladas: cuanto del catalogo se toco en cada etapa."""
    por_etapa = auditoria.get("por_etapa") or {}
    etapas = [e for e in ETAPAS if por_etapa.get(e, {}).get("total")]
    if not etapas:
        etapas = list(ETAPAS)

    fig, ax = plt.subplots(figsize=(7.4, 0.52 * len(etapas) + 1.5))
    y = range(len(etapas))
    ejec = [por_etapa.get(e, {}).get(EJECUTADO, 0) for e in etapas]
    desc = [por_etapa.get(e, {}).get(DESCARTADO, 0) for e in etapas]
    noap = [por_etapa.get(e, {}).get(NO_APLICA, 0) for e in etapas]

    ax.barh(list(y), ejec, color="#22c55e", edgecolor="#15803d", label="Ejecutado")
    ax.barh(list(y), desc, left=ejec, color="#cbd5e1", edgecolor="#94a3b8",
            label="Descartado con motivo")
    ax.barh(list(y), noap, left=[a + b for a, b in zip(ejec, desc)],
            color="#f8fafc", edgecolor="#e2e8f0", label="No aplica")

    for i, e in enumerate(etapas):
        total = por_etapa.get(e, {}).get("total", 0)
        if ejec[i]:
            ax.text(ejec[i] / 2, i, str(ejec[i]), ha="center", va="center",
                    fontsize=8, color="#14532d", fontweight="bold")
        ax.text(total + 0.15, i, f"de {total}", va="center", fontsize=7.5, color="#64748b")

    ax.set_yticks(list(y))
    ax.set_yticklabels(etapas, fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlabel("Ensayos del catálogo", fontsize=8.5)
    ax.tick_params(axis="x", labelsize=8)
    ax.legend(fontsize=7.5, loc="lower right", framealpha=0.95)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    return fig
