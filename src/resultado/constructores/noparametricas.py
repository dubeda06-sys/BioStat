"""Pruebas no paramétricas: Mann-Whitney, Wilcoxon, Kruskal-Wallis, Friedman,
signos y Q de Cochran, migradas a `Resultado`.

Lo que se agrega al panel viejo: Mann-Whitney y Wilcoxon dan el corrimiento de
Hodges-Lehmann con su IC (cuánto, no solo si), cada prueba dice qué supone
(no ser paramétrica no es no suponer nada) y Kruskal-Wallis corre Dunn cuando
detecta, igual que el Omnianálisis.
"""
from __future__ import annotations

import numpy as np
from scipy import stats

from src.core.statistics import (
    cochran_q, dunn_test, friedman_test, hodges_lehmann, kruskal_wallis, mannwhitneyu,
    sign_test, skewness_test, wilcoxon_signed_rank,
)
from src.resultado.citas import ficha
from src.resultado.constructores.anova import (
    figura_grupos, valores_grupos, valores_posthoc,
)
from src.resultado.datos import columnas_faltantes, filas_completas, grupos, una
from src.resultado.lenguaje import fmt_p, p_token
from src.resultado.modelo import Entrada, Figura, Metodo, Resultado, Supuesto, Valor


def _f(x, dec=4) -> str:
    return Valor("", x, decimales=dec).texto()


def _armar(analisis, titulo, entrada, valores, metodo, supuestos, lectura, matiz,
           advertencias=(), figuras=(), crudo=None) -> Resultado:
    f = ficha(analisis)
    return Resultado(analisis=analisis, titulo=titulo, entrada=entrada, valores=valores,
                     metodo=metodo, supuestos=list(supuestos), formula=f.formula,
                     citas=list(f.citas), lectura=lectura, matiz=matiz,
                     advertencias=list(advertencias), figuras=list(figuras), crudo=crudo or {})


def _paso_detecta(pregunta, medicion, p, si, no) -> Supuesto:
    detecta = p < 0.05
    return Supuesto(pregunta, medicion,
                    "Se detectó diferencia" if detecta else "No se detectó diferencia",
                    si if detecta else no)


def _pares(analisis, titulo, df, c1, c2):
    falta = columnas_faltantes(df, c1, c2)
    if falta:
        return None, None, None, Resultado.rechazo(analisis, titulo, falta)
    if c1 == c2:
        return None, None, None, Resultado.rechazo(analisis, titulo, "Elegí dos columnas distintas.")
    pares, entrada = filas_completas(df, c1, c2)
    try:
        return (pares[c1].to_numpy(dtype=float), pares[c2].to_numpy(dtype=float), entrada, None)
    except (TypeError, ValueError):
        return None, None, None, Resultado.rechazo(analisis, titulo, "Alguna columna tiene texto.",
                                                   entrada)


def _lista(analisis, titulo, df, columnas, minimo):
    if isinstance(columnas, str):
        columnas = [columnas]
    columnas = list(dict.fromkeys(columnas or []))
    if len(columnas) < minimo:
        return None, None, Resultado.rechazo(analisis, titulo,
                                             f"Hacen falta al menos {minimo} columnas; hay "
                                             f"{len(columnas)}.")
    falta = columnas_faltantes(df, *columnas)
    if falta:
        return None, None, Resultado.rechazo(analisis, titulo, falta)
    filas, entrada = filas_completas(df, *columnas)
    try:
        return filas[columnas].to_numpy(dtype=float), entrada, None
    except (TypeError, ValueError):
        return None, None, Resultado.rechazo(analisis, titulo, "Alguna columna tiene texto.",
                                             entrada)


# ============================================================

def mann_whitney(df, c1, c2, opciones=None) -> Resultado:
    """Cada columna es un grupo independiente."""
    titulo = f"Mann-Whitney — {c1} y {c2}"
    g1, g2 = una(df, c1), una(df, c2)
    for g in (g1, g2):
        if g.motivo:
            return Resultado.rechazo("mann_whitney", titulo, g.motivo)
    entrada = Entrada(columnas=(c1, c2), n=g1.entrada.n + g2.entrada.n)
    r = mannwhitneyu(g1.valores, g2.valores)
    if r is None:
        return Resultado.rechazo("mann_whitney", titulo,
                                 "Hacen falta al menos 2 datos en cada grupo.", entrada)
    hl = hodges_lehmann(g1.valores, g2.valores)
    ic_ok = all(np.isfinite(hl["ic95"]))
    valores = [Valor(f"Mediana {c1}", r["median1"], nota=f"n = {r['n1']}"),
               Valor(f"Mediana {c2}", r["median2"], nota=f"n = {r['n2']}"),
               Valor("Corrimiento de Hodges-Lehmann", hl["estimacion"],
                     ic=hl["ic95"] if ic_ok else None,
                     nota=f"mediana de las diferencias {c1} − {c2}"),
               Valor("U", r["u"], decimales=1), Valor("p", fmt_p(r["p"]))]
    lev = stats.levene(g1.valores, g2.valores, center="median")
    misma_forma = lev.pvalue >= 0.05
    supuestos = [
        _paso_detecta("¿Un grupo tiende a dar valores más altos?",
                      f"U = {_f(r['u'], 1)}, {p_token(r['p'])}", r["p"],
                      f"Sí: el corrimiento típico es {_f(hl['estimacion'])}.",
                      "Con estos datos no se puede afirmar que un grupo tienda a valores más "
                      "altos que el otro."),
        Supuesto("¿Los dos grupos dispersan parecido?",
                 f"Brown-Forsythe: {p_token(lev.pvalue)}",
                 "Sí" if misma_forma else "No",
                 ("Con la misma forma, Mann-Whitney compara posición y el corrimiento de "
                  "Hodges-Lehmann se lee como diferencia de medianas." if misma_forma else
                  "Con dispersiones distintas Mann-Whitney también reacciona a la dispersión: "
                  "si detecta algo, no alcanza para decir que un grupo tiene valores más "
                  "altos."),
                 ok=bool(misma_forma)),
    ]
    return _armar(
        "mann_whitney", titulo, entrada, valores,
        Metodo("Mann-Whitney (Wilcoxon de suma de rangos)",
               "Compara dos grupos independientes por rangos: no supone normalidad y los "
               "valores extremos pesan como un rango más."),
        supuestos,
        (f"Se detectó diferencia: los valores de {c1} tienden a estar {_f(abs(hl['estimacion']))} "
         f"{'por encima' if hl['estimacion'] > 0 else 'por debajo'} de los de {c2}."
         if r["p"] < 0.05 else "No se detectó diferencia entre los dos grupos."),
        "No compara medias. Y no suponer normalidad no es no suponer nada: ver la dispersión.",
        figuras=[Figura("Grupos", lambda: figura_grupos([c1, c2], [g1.valores, g2.valores],
                                                         "Cada punto es un dato"))],
        crudo={"mann_whitney": r, "hodges_lehmann": hl})


def wilcoxon(df, c1, c2, opciones=None) -> Resultado:
    """Diferencia = Variable 1 − Variable 2, fila por fila."""
    titulo = f"Wilcoxon pareado — {c1} − {c2}"
    x, y, entrada, rechazo = _pares("wilcoxon", titulo, df, c1, c2)
    if rechazo is not None:
        return rechazo
    r = wilcoxon_signed_rank(x, y)
    d = (x - y)[np.isfinite(x - y)]
    ceros = int(np.sum(d == 0))
    if r is None:
        return Resultado.rechazo("wilcoxon", titulo,
                                 f"Hacen falta al menos 5 pares con diferencia distinta de 0; hay "
                                 f"{len(d) - ceros}.", entrada)
    hl = hodges_lehmann(d)
    ic_ok = all(np.isfinite(hl["ic95"]))
    valores = [Valor("Pares", len(d), nota=f"{ceros} con diferencia 0, que no entran a la prueba"
                     if ceros else ""),
               Valor("Mediana de las diferencias", float(np.median(d))),
               Valor("Pseudomediana de Hodges-Lehmann", hl["estimacion"],
                     ic=hl["ic95"] if ic_ok else None, nota=f"{c1} − {c2}"),
               Valor("W", r["w"], decimales=1), Valor("p", fmt_p(r["p"]))]
    sk = skewness_test(d)
    simetrica = sk is None or sk.get("error") or sk["p"] >= 0.05
    supuestos = [
        _paso_detecta("¿Los dos valores de cada fila difieren?",
                      f"W = {_f(r['w'], 1)}, {p_token(r['p'])}", r["p"],
                      f"Sí: la diferencia típica es {_f(hl['estimacion'])}.",
                      "Con estos datos no se puede afirmar una diferencia."),
        Supuesto("¿Las diferencias son simétricas?",
                 (f"D'Agostino: g₁ = {_f(sk['skewness'])}, {p_token(sk['p'])}"
                  if sk is not None and not sk.get("error") else "no evaluable (menos de 8)"),
                 "Sí" if simetrica else "No",
                 ("Wilcoxon supone diferencias simétricas: se cumple." if simetrica else
                  "Wilcoxon supone diferencias simétricas alrededor de su centro. Con una cola "
                  "larga, la prueba de los signos no lo supone."),
                 ok=bool(simetrica)),
    ]
    return _armar(
        "wilcoxon", titulo, entrada, valores,
        Metodo("Wilcoxon de rangos con signo",
               "Compara dos mediciones del mismo sujeto por los rangos de las diferencias: no "
               "supone normalidad."),
        supuestos,
        (f"Se detectó diferencia: {c1} − {c2} es típicamente {_f(hl['estimacion'])}."
         if r["p"] < 0.05 else "No se detectó diferencia entre las dos mediciones."),
        "Para comparar dos métodos de medición no alcanza: está Bland-Altman.",
        crudo={"wilcoxon": r, "hodges_lehmann": hl})


def kruskal(df, respuesta, grupo, opciones=None) -> Resultado:
    titulo = f"Kruskal-Wallis — {respuesta} por {grupo}"
    g = grupos(df, respuesta, grupo)
    if g.motivo:
        return Resultado.rechazo("kruskal", titulo, g.motivo, g.entrada)
    r = kruskal_wallis(g.datos)
    if r is None:
        return Resultado.rechazo("kruskal", titulo, "No hay grupos con datos.", g.entrada)
    detecta = r["p"] < 0.05
    ph = dunn_test(g.datos, g.etiquetas) if detecta and len(g.datos) > 2 else None
    valores = [*valores_grupos(g.etiquetas, g.datos),
               Valor("H", r["h"], nota=f"{r['k'] - 1} gl"), Valor("p", fmt_p(r["p"]))]
    if ph and not ph.get("error"):
        valores += valores_posthoc(ph)
    lev = stats.levene(*g.datos, center="median") if all(len(x) >= 2 for x in g.datos) else None
    misma = lev is None or lev.pvalue >= 0.05
    supuestos = [
        _paso_detecta("¿Algún grupo tiende a valores más altos?",
                      f"H = {_f(r['h'], 3)}, {p_token(r['p'])}", r["p"],
                      ("Al menos un grupo difiere; Dunn dice cuáles, con Bonferroni." if
                       len(g.datos) > 2 else "Los dos grupos difieren."),
                      "Con estos datos no se puede afirmar diferencia; sin ella no se corre Dunn."),
        Supuesto("¿Los grupos dispersan parecido?",
                 f"Brown-Forsythe: {p_token(lev.pvalue)}" if lev is not None else "no evaluable",
                 "Sí" if misma else "No",
                 ("Kruskal-Wallis compara posición." if misma else
                  "Con dispersiones distintas Kruskal-Wallis también reacciona a la dispersión; "
                  "si los grupos son normales, el ANOVA de Welch es la prueba que corresponde."),
                 ok=bool(misma)),
    ]
    pares = [c["par"] for c in (ph or {}).get("comparaciones", []) if c["p_adj"] < 0.05]
    return _armar(
        "kruskal", titulo, g.entrada, valores,
        Metodo("Kruskal-Wallis, con Dunn si detecta",
               "Compara varios grupos por rangos, sin suponer normalidad."),
        supuestos,
        ((f"Se detectó diferencia. Pares que difieren (Dunn): {', '.join(pares)}." if pares else
          "Se detectó diferencia en conjunto.") if detecta else
         f"No se detectó diferencia en {respuesta} según {grupo}."),
        "No compara medias ni medianas en sentido estricto: compara la tendencia a valores "
        "altos.",
        figuras=[Figura("Grupos", lambda: figura_grupos(g.etiquetas, g.datos,
                                                         f"{respuesta} por {grupo}"))],
        crudo={"kruskal": r, "posthoc": ph})


def friedman(df, columnas, opciones=None) -> Resultado:
    titulo = "Friedman"
    datos, entrada, rechazo = _lista("friedman", titulo, df, columnas, 3)
    if rechazo is not None:
        return rechazo
    cols = list(dict.fromkeys([columnas] if isinstance(columnas, str) else columnas))
    r = friedman_test(*[datos[:, i] for i in range(datos.shape[1])])
    if r is None:
        return Resultado.rechazo("friedman", titulo,
                                 "No se pudo calcular: hacen falta sujetos completos en las tres "
                                 "condiciones o más.", entrada)
    n, k = r["n"], r["k"]
    w = r["chi2"] / (n * (k - 1)) if n and k > 1 else np.nan
    valores = [Valor(f"Mediana {c}", float(np.median(datos[:, i]))) for i, c in enumerate(cols)]
    valores += [Valor("Sujetos completos", n), Valor("χ² de Friedman", r["chi2"],
                                                     nota=f"{k - 1} gl"),
                Valor("p", fmt_p(r["p"])),
                Valor("W de Kendall", w, nota="0 = sin concordancia, 1 = total")]
    supuestos = [_paso_detecta(
        "¿La respuesta cambia entre condiciones?", f"χ² = {_f(r['chi2'], 3)}, {p_token(r['p'])}",
        r["p"], "Al menos una condición difiere de otra.",
        "Con estos datos no se puede afirmar un cambio entre condiciones.")]
    return _armar(
        "friedman", titulo, entrada, valores,
        Metodo("Friedman", "La versión por rangos del ANOVA de medidas repetidas: cada sujeto se "
                           "rankea contra sí mismo."),
        supuestos,
        ("Se detectó diferencia entre condiciones." if r["p"] < 0.05 else
         "No se detectó diferencia entre condiciones."),
        "Si detecta, no dice entre cuáles condiciones: para eso, Wilcoxon por pares con "
        "corrección por multiplicidad.",
        crudo={"friedman": r, "w_kendall": w})


def signos(df, c1, c2, opciones=None) -> Resultado:
    titulo = f"Prueba de los signos — {c1} − {c2}"
    x, y, entrada, rechazo = _pares("signos", titulo, df, c1, c2)
    if rechazo is not None:
        return rechazo
    r = sign_test(x, y)
    if r is None:
        return Resultado.rechazo("signos", titulo,
                                 "Hacen falta al menos 5 pares con diferencia distinta de 0.",
                                 entrada)
    empates = entrada.n - r["n"]
    valores = [Valor(f"{c1} mayor", r["n_pos"]), Valor(f"{c1} menor", r["n_neg"]),
               Valor("Empates (no entran)", empates), Valor("p (binomial exacta)", fmt_p(r["p"]))]
    supuestos = [_paso_detecta(
        f"¿{c1} tiende a superar a {c2} (o al revés)?",
        f"{r['n_pos']} a favor, {r['n_neg']} en contra, {p_token(r['p'])}", r["p"],
        "Sí: los signos no se reparten mitad y mitad.",
        "Con estos datos los signos se reparten como al azar.")]
    return _armar(
        "signos", titulo, entrada, valores,
        Metodo("Prueba de los signos",
               "Cuenta cuántas veces una medición supera a la otra. No supone ni normalidad ni "
               "simetría; a cambio, usa solo el signo y tiene poca potencia."),
        supuestos,
        (f"{c1} supera a {c2} en {r['n_pos']} de {r['n']} pares: " +
         ("se detectó diferencia." if r["p"] < 0.05 else "no se detectó diferencia.")),
        "No dice cuánto difieren: para eso, Wilcoxon con su pseudomediana.",
        crudo={"signos": r})


def cochran(df, columnas, opciones=None) -> Resultado:
    titulo = "Q de Cochran"
    datos, entrada, rechazo = _lista("cochran", titulo, df, columnas, 2)
    if rechazo is not None:
        return rechazo
    if not np.all(np.isin(datos, (0, 1))):
        return Resultado.rechazo("cochran", titulo,
                                 "Cochran Q necesita columnas 0/1 (fracaso/éxito).", entrada)
    r = cochran_q(datos)
    if r is None:
        return Resultado.rechazo("cochran", titulo, "Hacen falta al menos 2 sujetos completos.",
                                 entrada)
    cols = list(dict.fromkeys([columnas] if isinstance(columnas, str) else columnas))
    valores = [Valor(f"Proporción de 1 — {c}", float(np.mean(datos[:, i])), decimales=3)
               for i, c in enumerate(cols)]
    valores += [Valor("Sujetos completos", r["n"]), Valor("Q", r["Q"], nota=f"{r['df']} gl"),
                Valor("p", fmt_p(r["p"]))]
    supuestos = [_paso_detecta(
        "¿La proporción de éxitos difiere entre tratamientos?", f"Q = {_f(r['Q'], 3)}, "
        f"{p_token(r['p'])}", r["p"], "Al menos un tratamiento difiere de otro.",
        "Con estos datos no se puede afirmar que las proporciones difieran.")]
    return _armar(
        "cochran", titulo, entrada, valores,
        Metodo("Q de Cochran",
               "Compara proporciones de éxito entre varios tratamientos aplicados a los mismos "
               "sujetos (la extensión de McNemar a más de dos)."),
        supuestos,
        ("Se detectó diferencia entre tratamientos." if r["p"] < 0.05 else
         "No se detectó diferencia entre tratamientos."),
        "Si detecta, no dice cuáles difieren: McNemar por pares, con corrección por "
        "multiplicidad.",
        crudo={"cochran": r})
