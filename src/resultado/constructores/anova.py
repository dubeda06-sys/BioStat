"""ANOVA: una vía, dos vías, ANCOVA y medidas repetidas, migradas a `Resultado`.

La de una vía sigue el mismo árbol que el Omnianálisis para grupos normales:
con varianzas iguales (Levene) ANOVA clásico y Tukey; con distintas, ANOVA de
Welch y Games-Howell. Si los grupos no son normales lo dice y remite a
Kruskal-Wallis, que es otro análisis del menú.
"""
from __future__ import annotations

import numpy as np
from scipy import stats

from src.core.ancova import ancova as ancova_core
from src.core.repeated_measures import repeated_measures_anova
from src.core.statistics import (
    anova_oneway, games_howell, normality_test, tukey_hsd, welch_anova,
)
from src.core.two_way_anova import two_way_anova
from src.resultado.citas import ficha
from src.resultado.datos import columnas_faltantes, filas_completas, grupos
from src.resultado.lenguaje import fmt_p, p_token
from src.resultado.modelo import Entrada, Figura, Metodo, Resultado, Supuesto, Valor


def _f(x, dec=4) -> str:
    return Valor("", x, decimales=dec).texto()


def _alfa(opciones) -> float:
    try:
        a = float((opciones or {}).get("alpha", 0.05) or 0.05)
    except (TypeError, ValueError):
        return 0.05
    return a if 0 < a < 1 else 0.05


def _armar(analisis, titulo, entrada, valores, metodo, supuestos, lectura, matiz,
           advertencias=(), figuras=(), crudo=None) -> Resultado:
    f = ficha(analisis)
    return Resultado(analisis=analisis, titulo=titulo, entrada=entrada, valores=valores,
                     metodo=metodo, supuestos=list(supuestos), formula=f.formula,
                     citas=list(f.citas), lectura=lectura, matiz=matiz,
                     advertencias=list(advertencias), figuras=list(figuras), crudo=crudo or {})


# ---------------- piezas que comparten ANOVA y Kruskal-Wallis ----------------

def valores_grupos(etiquetas, datos) -> list[Valor]:
    return [Valor(f"Grupo {e}", float(np.mean(g)),
                  nota=(f"n = {len(g)}, DE {_f(np.std(g, ddof=1)) if len(g) > 1 else '—'}, "
                        f"mediana {_f(np.median(g))}"))
            for e, g in zip(etiquetas, datos)]


def paso_normalidad_grupos(etiquetas, datos, alternativa) -> tuple[Supuesto, bool]:
    pruebas = [(e, normality_test(g) if len(g) >= 3 and np.ptp(g) > 0 else None)
               for e, g in zip(etiquetas, datos)]
    no_normales = [e for e, t in pruebas if t is not None and not t["normal"]]
    sin_prueba = [e for e, t in pruebas if t is None]
    medicion = "; ".join(f"{e}: {p_token(t['p'])}" if t else f"{e}: no evaluable"
                         for e, t in pruebas)
    normales = not no_normales
    return Supuesto(
        "¿Cada grupo es normal?", f"Shapiro-Wilk — {medicion}",
        "Sí" if normales else "No en " + ", ".join(no_normales),
        ("Las pruebas de medias suponen normalidad en cada grupo: se cumple."
         + (f" (sin poder probar en {', '.join(sin_prueba)})" if sin_prueba else "")
         if normales else
         f"Con grupos no normales, las pruebas de medias pueden fallar: usá {alternativa}."),
        alternativa=(f"si alguno no lo fuera, convendría {alternativa}." if normales else
                     "con grupos normales, valdría la prueba de medias."),
        ok=normales), normales


def valores_posthoc(ph) -> list[Valor]:
    vals = []
    for c in ph.get("comparaciones", []):
        nota = f"{p_token(c['p_adj'])} ajustado; diferencia = primero − segundo"
        ic = c.get("ic95")
        diferencia = c.get("diferencia")
        if diferencia is None:
            vals.append(Valor(f"{ph['metodo']}: {c['par']}", fmt_p(c["p_adj"]),
                              nota=f"z = {_f(c.get('z'), 3)}" if c.get("z") is not None else ""))
        else:
            vals.append(Valor(f"{ph['metodo']}: {c['par']}", diferencia,
                              ic=tuple(ic) if ic else None, nota=nota))
    return vals


def figura_grupos(etiquetas, datos, titulo):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(max(6, 1.2 * len(datos) + 3), 5.5))
    ax.boxplot(datos, widths=0.45, showfliers=False)
    rng = np.random.default_rng(0)
    for i, g in enumerate(datos, start=1):
        ax.scatter(i + rng.uniform(-0.12, 0.12, len(g)), g, alpha=0.5, c='#4f6ef7',
                   edgecolors='white', s=30, zorder=3)
        ax.plot([i - 0.25, i + 0.25], [np.mean(g)] * 2, color='#ef4444', lw=2)
    ax.set_xticks(range(1, len(etiquetas) + 1), [str(e) for e in etiquetas])
    ax.set_title(titulo, fontweight='bold')
    fig.tight_layout()
    return fig


# ============================================================
#  Una vía
# ============================================================

def anova_una_via(df, respuesta, grupo, opciones=None) -> Resultado:
    """Variable 1 = respuesta, Variable 2 = grupo (formato largo)."""
    alfa = _alfa(opciones)
    titulo = f"ANOVA de una vía — {respuesta} por {grupo}"
    g = grupos(df, respuesta, grupo)
    if g.motivo:
        return Resultado.rechazo("anova_una_via", titulo, g.motivo, g.entrada)
    etiquetas, datos = g.etiquetas, g.datos
    k = len(datos)
    paso_normal, normales = paso_normalidad_grupos(etiquetas, datos, "Kruskal-Wallis")
    con_dos = all(len(x) >= 2 for x in datos)
    lev = stats.levene(*datos) if con_dos else None
    iguales = lev is None or lev.pvalue >= 0.05
    advertencias = []
    if iguales:
        r = anova_oneway(datos)
        if r is None:
            return Resultado.rechazo("anova_una_via", titulo, "No hay grupos con datos.",
                                     g.entrada)
        f_, p, gl = r["F"], r["p"], (r["df_between"], r["df_within"])
        nombre = "ANOVA de una vía"
    else:
        r = welch_anova(datos)
        falla = Resultado.rechazo_del_core("anova_una_via", titulo, r, g.entrada)
        if falla is not None:
            return falla
        f_, p, gl = r["f"], r["p"], (r["df1"], r["df2"])
        nombre = "ANOVA de Welch"
    detecta = p < alfa
    ph = None
    if detecta and k > 2:
        ph = tukey_hsd(datos, etiquetas, alfa) if iguales else games_howell(datos, etiquetas)
        if not ph or ph.get("error"):
            advertencias.append("No se pudo correr el post-hoc"
                                + (f": {ph['error']}" if ph else "."))
            ph = None
    valores = [*valores_grupos(etiquetas, datos),
               Valor(f"F ({nombre})", f_, nota=f"gl {_f(gl[0], 2)} y {_f(gl[1], 2)}"),
               Valor("p", fmt_p(p))]
    if ph:
        valores += valores_posthoc(ph)
    supuestos = [
        paso_normal,
        Supuesto("¿Los grupos dispersan igual?",
                 f"Levene: {p_token(lev.pvalue)}" if lev is not None else
                 "no evaluable (algún grupo con un solo dato)",
                 "Sí" if iguales else "No",
                 ("ANOVA clásico, que las supone iguales y así tiene más potencia; post-hoc de "
                  "Tukey." if iguales else
                  "ANOVA de Welch, que no supone varianzas iguales; post-hoc de Games-Howell. "
                  "Kruskal-Wallis no es la salida: con dispersiones distintas reacciona a la "
                  "dispersión, no solo a la posición."),
                 alternativa=("con varianzas distintas, ANOVA de Welch." if iguales else
                              "con varianzas iguales, ANOVA clásico."),
                 ok=True),
        Supuesto("¿Las medias de los grupos difieren?",
                 f"F = {_f(f_, 3)}, {p_token(p)} (α = {alfa:g})",
                 "Se detectó diferencia" if detecta else "No se detectó diferencia",
                 (("Al menos un grupo difiere. El post-hoc dice cuáles." if k > 2 else
                   "Los dos grupos difieren.") if detecta else
                  "Con estos datos no se puede afirmar que las medias difieran. Sin diferencia "
                  "global no se corre el post-hoc: haría falsos positivos.")),
    ]
    if ph:
        pares = [c["par"] for c in ph["comparaciones"] if c["p_adj"] < alfa]
        lectura = (f"Las medias de {respuesta} difieren según {grupo}. "
                   + (f"Pares que difieren ({ph['metodo']}): {', '.join(pares)}." if pares else
                      f"Ningún par por separado alcanza a diferir en el post-hoc ({ph['metodo']})."))
    elif detecta:
        lectura = f"Las medias de {respuesta} difieren según {grupo}."
    else:
        lectura = f"No se detectó diferencia en las medias de {respuesta} según {grupo}."
    if not normales and min(len(x) for x in datos) < 30:
        advertencias.append("Los grupos no son normales y son chicos: el análisis que corresponde "
                            "es Kruskal-Wallis (menú Pruebas no paramétricas).")
    return _armar(
        "anova_una_via", titulo, g.entrada, valores,
        Metodo(nombre, "Compara las medias de varios grupos a la vez; si difieren, el post-hoc "
                       "dice cuáles, con la multiplicidad controlada."),
        supuestos, lectura,
        ("Que las medias difieran no dice cuánto importa: mirá las diferencias del post-hoc con "
         "sus IC."), advertencias,
        [Figura("Grupos", lambda: figura_grupos(etiquetas, datos, f"{respuesta} por {grupo}"))],
        {"prueba": nombre, "F": f_, "p": p, "gl": gl, "posthoc": ph,
         "levene_p": None if lev is None else float(lev.pvalue)})


# ============================================================
#  Dos vías
# ============================================================

def anova_dos_vias(df, respuesta, factor_a, factor_b, opciones=None) -> Resultado:
    titulo = f"ANOVA de dos vías — {respuesta} por {factor_a} × {factor_b}"
    falta = columnas_faltantes(df, respuesta, factor_a, factor_b)
    if falta:
        return Resultado.rechazo("anova_dos_vias", titulo, falta)
    if len({respuesta, factor_a, factor_b}) < 3:
        return Resultado.rechazo("anova_dos_vias", titulo, "Elegí tres columnas distintas.")
    filas, entrada = filas_completas(df, respuesta, factor_a, factor_b)
    try:
        y = filas[respuesta].to_numpy(dtype=float)
    except (TypeError, ValueError):
        return Resultado.rechazo("anova_dos_vias", titulo, "La respuesta tiene texto.", entrada)
    for factor in (factor_a, factor_b):
        k = filas[factor].nunique()
        if k < 2:
            return Resultado.rechazo("anova_dos_vias", titulo,
                                     f"«{factor}» tiene un solo valor: no es un factor.", entrada)
        if k > 20 or k > len(filas) / 2:
            return Resultado.rechazo("anova_dos_vias", titulo,
                                     f"«{factor}» tiene {k} valores distintos para {len(filas)} "
                                     "filas: parece una medición, no un factor (1, 2, 3 o A, B).",
                                     entrada)
    try:
        r = two_way_anova(y, filas[factor_a].to_numpy(), filas[factor_b].to_numpy())
    except (ValueError, np.linalg.LinAlgError):
        r = None
    if r is None:
        return Resultado.rechazo("anova_dos_vias", titulo,
                                 "Datos insuficientes o sin réplicas por celda para estimar el "
                                 "error.", entrada)
    falla = Resultado.rechazo_del_core("anova_dos_vias", titulo, r, entrada)
    if falla is not None:
        return falla
    celdas = filas.groupby([factor_a, factor_b]).size()
    valores = [
        Valor(f"Factor {factor_a}", r["F_A"], nota=f"F, {r['df_A']} gl, {p_token(r['p_A'])}"),
        Valor(f"Factor {factor_b}", r["F_B"], nota=f"F, {r['df_B']} gl, {p_token(r['p_B'])}"),
        Valor(f"Interacción {factor_a} × {factor_b}", r["F_AB"],
              nota=f"F, {r['df_AB']} gl, {p_token(r['p_AB'])}"),
        Valor("gl del error", r["df_error"]),
        Valor("Celdas", len(celdas), nota=f"de {int(celdas.min())} a {int(celdas.max())} datos"),
    ]
    inter = r["p_AB"] < 0.05
    supuestos = [
        Supuesto("¿El efecto de un factor depende del otro?",
                 f"interacción: {p_token(r['p_AB'])}",
                 "Sí (hay interacción)" if inter else "No se detectó interacción",
                 ("Los efectos principales no se pueden leer solos: el efecto de "
                  f"{factor_a} cambia según {factor_b}. Mirá las medias por celda." if inter else
                  "Cada factor se puede leer por su cuenta."),
                 ok=not inter),
        Supuesto("¿Hay réplicas en cada celda?",
                 f"{len(celdas)} celdas, mínimo {int(celdas.min())} dato(s)",
                 "Sí" if celdas.min() >= 2 else "No",
                 ("Con réplicas se estima el error y la interacción." if celdas.min() >= 2 else
                  "Una celda con un solo dato debilita la estimación del error."),
                 ok=bool(celdas.min() >= 2)),
    ]
    efectos = [n for n, p in ((factor_a, r["p_A"]), (factor_b, r["p_B"])) if p < 0.05]
    return _armar(
        "anova_dos_vias", titulo, entrada, valores,
        Metodo("ANOVA de dos factores con interacción, sumas de cuadrados tipo II",
               "Separa cuánto de la variación de la respuesta se debe a cada factor y a su "
               "combinación."),
        supuestos,
        (("Hay interacción: " if inter else "") +
         (f"se detectó efecto de {', '.join(efectos)}." if efectos else
          "no se detectó efecto de ninguno de los dos factores por separado.")),
        "Con celdas de distinto tamaño, las sumas tipo II dependen del orden de los datos menos "
        "que las tipo I, pero ninguna reemplaza mirar las medias por celda.",
        crudo={"dos_vias": r})


# ============================================================
#  ANCOVA
# ============================================================

def ancova(df, respuesta, grupo, covariable, opciones=None) -> Resultado:
    titulo = f"ANCOVA — {respuesta} por {grupo}, ajustado por {covariable}"
    falta = columnas_faltantes(df, respuesta, grupo, covariable)
    if falta:
        return Resultado.rechazo("ancova", titulo, falta)
    if len({respuesta, grupo, covariable}) < 3:
        return Resultado.rechazo("ancova", titulo, "Elegí tres columnas distintas.")
    filas, entrada = filas_completas(df, respuesta, grupo, covariable)
    try:
        y = filas[respuesta].to_numpy(dtype=float)
        x = filas[covariable].to_numpy(dtype=float)
    except (TypeError, ValueError):
        return Resultado.rechazo("ancova", titulo,
                                 "La respuesta y la covariable tienen que ser números.", entrada)
    r = ancova_core(y, filas[grupo].to_numpy(), x)
    falla = Resultado.rechazo_del_core("ancova", titulo, r, entrada)
    if falla is not None:
        return falla
    entrada.n = r["n"]
    valores = [Valor(f"Grupo ({grupo}), ajustado", r["F"],
                     nota=f"F, {r['df_group']} y {r['df_error']} gl, {p_token(r['p'])}"),
               Valor(f"Covariable ({covariable})", r["F_covariate"],
                     nota=f"F, {p_token(r['p_covariate'])}; pendiente "
                          f"{_f(r['pendiente_covariable'])}"),
               Valor("η² parcial del grupo", r["eta_squared"])]
    for nivel, media in r["medias_ajustadas"].items():
        valores.append(Valor(f"Media ajustada — {nivel}", media,
                             nota=f"en {covariable} = {_f(r['media_covariable'])}"))
    paralelas = not (r["p_interaccion"] < 0.05)
    supuestos = [
        Supuesto(f"¿{covariable} pesa igual en todos los grupos?",
                 f"interacción grupo × covariable: {p_token(r['p_interaccion'])}",
                 "Sí" if paralelas else "No",
                 ("Las pendientes son paralelas: ajustar tiene un solo sentido." if paralelas else
                  "Las pendientes difieren: la diferencia entre grupos depende del valor de "
                  f"{covariable} en que se mire, y las medias ajustadas no la resumen."),
                 ok=paralelas),
        Supuesto(f"¿Los grupos difieren con {covariable} igualada?",
                 f"F = {_f(r['F'], 3)}, {p_token(r['p'])}",
                 "Se detectó diferencia" if r["p"] < 0.05 else "No se detectó diferencia",
                 "Se comparan las medias que tendría cada grupo con el mismo valor de "
                 "la covariable."),
    ]
    return _armar(
        "ancova", titulo, entrada, valores,
        Metodo("ANCOVA, sumas de cuadrados tipo II",
               f"Compara los grupos descontando lo que explica {covariable}: por ejemplo, "
               "comparar un analito entre grupos con edades distintas."),
        supuestos,
        (f"Con {covariable} igualada, " +
         ("los grupos difieren." if r["p"] < 0.05 else "no se detectó diferencia entre grupos.")),
        "Ajustar por una covariable no vuelve comparables a grupos que difieren en cosas que no se "
        "midieron.", advertencias=r.get("avisos", []), crudo={"ancova": r})


# ============================================================
#  Medidas repetidas
# ============================================================

def medidas_repetidas(df, columnas, opciones=None) -> Resultado:
    if isinstance(columnas, str):
        columnas = [columnas]
    columnas = list(dict.fromkeys(columnas))
    titulo = "ANOVA de medidas repetidas"
    if len(columnas) < 2:
        return Resultado.rechazo("medidas_repetidas", titulo,
                                 "Hacen falta al menos 2 tiempos: una columna por medición.")
    falta = columnas_faltantes(df, *columnas)
    if falta:
        return Resultado.rechazo("medidas_repetidas", titulo, falta)
    try:
        datos = df[columnas].to_numpy(dtype=float)
    except (TypeError, ValueError):
        return Resultado.rechazo("medidas_repetidas", titulo, "Alguna columna tiene texto.")
    r = repeated_measures_anova(datos)
    falla = Resultado.rechazo_del_core("medidas_repetidas", titulo, r)
    if falla is not None:
        return falla
    entrada = Entrada(columnas=tuple(columnas), n=r["n"])
    completos = datos[np.all(np.isfinite(datos), axis=1)]
    valores = [Valor(f"Media {c}", float(np.mean(completos[:, i])))
               for i, c in enumerate(columnas)]
    valores += [Valor("Sujetos completos", r["n"], nota=f"{r['n_excluidos']} excluidos"),
                Valor("F", r["F"], nota=f"{r['df_time']} y {r['df_error']} gl"),
                Valor("p sin corregir", fmt_p(r["p"])),
                Valor("ε de Greenhouse-Geisser", r["epsilon"]),
                Valor("p corregido (Greenhouse-Geisser)", fmt_p(r["p_gg"]))]
    esferica = r["epsilon"] > 0.75
    supuestos = [
        Supuesto("¿Las diferencias entre tiempos varían parejo? (esfericidad)",
                 f"ε de Greenhouse-Geisser = {_f(r['epsilon'], 3)} (1 = esfericidad perfecta)",
                 "Sí, aproximadamente" if esferica else "No",
                 "Se informa el p corregido por Greenhouse-Geisser, que vale haya o no "
                 "esfericidad: con ε cerca de 1 casi no cambia; lejos de 1, evita falsos "
                 "positivos.", ok=True),
        Supuesto("¿La respuesta cambia entre tiempos?",
                 f"p corregido {p_token(r['p_gg'])}",
                 "Se detectó cambio" if r["p_gg"] < 0.05 else "No se detectó cambio",
                 "Cada sujeto es su propio control: la variación entre sujetos no tapa el cambio."),
    ]
    return _armar(
        "medidas_repetidas", titulo, entrada, valores,
        Metodo("ANOVA de medidas repetidas con corrección de Greenhouse-Geisser",
               "Compara varias mediciones de los mismos sujetos (tiempos, condiciones)."),
        supuestos,
        ("La respuesta cambia entre tiempos." if r["p_gg"] < 0.05 else
         "No se detectó cambio entre tiempos."),
        "Sujetos con algún tiempo faltante quedan afuera enteros: si faltan por algo relacionado "
        "con la respuesta, el resultado se sesga.",
        advertencias=r.get("avisos", []),
        figuras=[Figura("Perfiles", lambda: _figura_perfiles(completos, columnas))],
        crudo={"medidas_repetidas": r})


def _figura_perfiles(datos, columnas):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(columnas))
    for fila in datos[:200]:
        ax.plot(x, fila, color='#4f6ef7', alpha=0.15, lw=1)
    ax.plot(x, datos.mean(axis=0), color='#ef4444', lw=2.5, marker='o', label="Media")
    ax.set_xticks(x, [str(c) for c in columnas])
    ax.set_title("Cada línea es un sujeto", fontweight='bold')
    ax.legend(framealpha=0.9)
    fig.tight_layout()
    return fig
