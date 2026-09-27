"""Resumen y distribución: la primera familia del menú, migrada a `Resultado`.

Descriptivas, asimetría y curtosis, percentiles, medias recortada, geométrica y
armónica, normalidad y valores atípicos (Grubbs, Tukey y ESD generalizado).
Todos toman una sola columna (`datos.una`) y ninguno tira datos en silencio:
una celda con texto rechaza el análisis, y los infinitos se sacan y se avisan.
"""
from __future__ import annotations

import numpy as np

from src.core.outliers import generalized_esd, grubbs_test, tukey_outliers
from src.core.reference import percentile_table
from src.core.statistics import (
    descriptive_stats, geometric_mean, harmonic_mean, kurtosis_test, normality_test,
    skewness_test, trimmed_mean,
)
from src.resultado.citas import ficha
from src.resultado.datos import una
from src.resultado.lenguaje import fmt_p, num, p_token
from src.resultado.modelo import Figura, Metodo, Resultado, Supuesto, Valor

RECORTE = 0.10          # media recortada: 10 % de cada cola
ESD_MAXIMO = 10         # atípicos que busca el ESD generalizado, como máximo


def _f(x, dec=4) -> str:
    return Valor("", x, decimales=dec).texto()


def _columna(analisis, titulo, df, col):
    """(columna, None) o (None, rechazo)."""
    c = una(df, col)
    if c.motivo:
        return None, Resultado.rechazo(analisis, titulo, c.motivo)
    return c, None


def _avisos(c, extra=()) -> list[str]:
    avisos = list(extra or [])
    if c.no_finitos:
        avisos.append(f"Se sacaron {c.no_finitos} valor(es) infinito(s) (±∞): no son "
                      "mediciones, suelen ser una división por cero en la planilla.")
    return avisos


def _armar(analisis, titulo, c, valores, metodo, supuestos, lectura, matiz, avisos=(),
           figuras=(), crudo=None) -> Resultado:
    f = ficha(analisis)
    return Resultado(analisis=analisis, titulo=titulo, entrada=c.entrada, valores=valores,
                     metodo=metodo, supuestos=list(supuestos), formula=f.formula,
                     citas=list(f.citas), lectura=lectura, matiz=matiz,
                     advertencias=_avisos(c, avisos), figuras=list(figuras),
                     crudo=crudo or {})


def _normalidad(valores):
    """(normal, medición) con Shapiro-Wilk; normal=None si no se puede probar."""
    r = normality_test(valores) if len(valores) >= 3 and np.ptp(valores) > 0 else None
    if r is None:
        return None, "no evaluable (menos de 3 datos o todos iguales)"
    return bool(r["normal"]), f"Shapiro-Wilk: W = {_f(r['w'])}, {p_token(r['p'])}"


# ============================================================
#  Descriptivas
# ============================================================

def descriptivas(df, col, opciones=None) -> Resultado:
    """Media, mediana, dispersión y cuartiles; y cuál de los dos resúmenes usar."""
    titulo = f"Estadísticas descriptivas — {col}"
    c, rechazo = _columna("descriptivas", titulo, df, col)
    if rechazo is not None:
        return rechazo
    r = descriptive_stats(c.valores)
    if r is None:
        return Resultado.rechazo("descriptivas", titulo,
                                 f"La columna «{col}» no tiene datos numéricos.", c.entrada)
    n = r["n"]
    valores = [
        Valor("n", n),
        Valor("Media", r["mean"], ic=r["ci95"] if n >= 2 else None),
        Valor("Mediana", r["median"]),
        Valor("DE", r["std"]),
        Valor("Varianza", r["var"]),
        Valor("Error estándar de la media", r["sem"]),
        Valor("Mínimo", r["min"]),
        Valor("Máximo", r["max"]),
        Valor("CV", r["cv"], decimales=2, unidad="%"),
        Valor("P25", r["q25"]),
        Valor("P75", r["q75"]),
        Valor("Rango intercuartílico", r["iqr"]),
    ]
    if np.isfinite(r["skewness"]):
        valores += [Valor("Asimetría", r["skewness"]), Valor("Exceso de curtosis", r["kurtosis"])]

    normal, medicion = _normalidad(c.valores)
    pregunta = "¿Con qué conviene resumir estos datos?"
    if normal is None:
        paso = Supuesto(pregunta, medicion, "No evaluable",
                        "Sin poder probar la normalidad, se muestran los dos resúmenes.",
                        ok=False)
        lectura = (f"Media {_f(r['mean'])} (DE {_f(r['std'])}); mediana {_f(r['median'])} "
                   f"(P25 a P75: {_f(r['q25'])} a {_f(r['q75'])}).")
    elif normal:
        lo, hi = r["mean"] - 1.96 * r["std"], r["mean"] + 1.96 * r["std"]
        valores.append(Valor("Rango del 95 % de los datos", f"{_f(lo)} a {_f(hi)}",
                             nota="media ± 1,96·DE: vale porque la distribución es normal"))
        paso = Supuesto(pregunta, medicion, "Media y DE",
                        "No se detectó que se aparten de la normal: la media y la DE los "
                        "describen bien (Altman 1980).",
                        alternativa="si se apartaran, convendría la mediana con el rango "
                                    "intercuartílico.")
        lectura = (f"Resumen: media {_f(r['mean'])} ± DE {_f(r['std'])} (n = {n}). El 95 % "
                   f"de los datos cae entre {_f(lo)} y {_f(hi)}.")
    else:
        paso = Supuesto(pregunta, medicion, "Mediana y rango intercuartílico",
                        "Los datos se apartan de la normal: la media y la DE los describen mal "
                        "(una cola larga arrastra a la media). La mediana y los cuartiles no "
                        "dependen de la forma (Altman 1980; MedCalc).",
                        alternativa="si fueran normales, alcanzaría con media y DE.",
                        ok=False)
        lectura = (f"Resumen: mediana {_f(r['median'])} (P25 a P75: {_f(r['q25'])} a "
                   f"{_f(r['q75'])}, n = {n}). La media, {_f(r['mean'])}, queda "
                   f"{'arriba' if r['mean'] > r['median'] else 'abajo'} de la mediana por la "
                   "forma de la distribución.")
    return _armar(
        "descriptivas", titulo, c, valores,
        Metodo("Estadísticas descriptivas",
               "Tendencia central, dispersión y forma de una variable, antes de cualquier "
               "prueba."),
        [paso], lectura,
        ("El IC 95 % es de la MEDIA, no de los datos: dice dónde está el promedio "
         "verdadero, y es mucho más angosto que el rango donde cae un paciente."),
        avisos=r.get("avisos"),
        figuras=[Figura("Distribución", lambda: _figura_histograma(
            c.valores, col, r["mean"], r["std"], r["median"]))],
        crudo={"descriptivas": r})


# ============================================================
#  Asimetría y curtosis
# ============================================================

def asimetria_curtosis(df, col, opciones=None) -> Resultado:
    titulo = f"Asimetría y curtosis — {col}"
    c, rechazo = _columna("asimetria_curtosis", titulo, df, col)
    if rechazo is not None:
        return rechazo
    sk, ku = skewness_test(c.valores), kurtosis_test(c.valores)
    if sk is None or ku is None:
        return Resultado.rechazo("asimetria_curtosis", titulo,
                                 f"Hacen falta al menos 8 datos; hay {c.entrada.n}.", c.entrada)
    for r in (sk, ku):
        falla = Resultado.rechazo_del_core("asimetria_curtosis", titulo, r, c.entrada)
        if falla is not None:
            return falla
    valores = [
        Valor("n", sk["n"]),
        Valor("Asimetría (g₁)", sk["skewness"], nota=f"z = {_f(sk['z'], 3)}, {p_token(sk['p'])}"),
        Valor("Exceso de curtosis (g₂)", ku["kurtosis"],
              nota=f"z = {_f(ku['z'], 3)}, {p_token(ku['p'])}"),
    ]
    asim = sk["p"] < 0.05
    colas = ku["p"] < 0.05
    lado = "a la derecha (cola larga de valores altos)" if sk["skewness"] > 0 else \
        "a la izquierda (cola larga de valores bajos)"
    forma = "más pesadas" if ku["kurtosis"] > 0 else "más livianas"
    supuestos = [
        Supuesto("¿La distribución es simétrica?",
                 f"D'Agostino: g₁ = {_f(sk['skewness'])}, {p_token(sk['p'])}",
                 "Se detectó asimetría" if asim else "No se detectó asimetría",
                 (f"Se inclina {lado}." if asim else
                  "Con estos datos no se distingue de una distribución simétrica."),
                 alternativa=("sin asimetría, g₁ no se distinguiría de 0." if asim else
                              "con asimetría, la media se correría hacia la cola."),
                 ok=not asim),
        Supuesto("¿Las colas son como las de una normal?",
                 f"Anscombe-Glynn: g₂ = {_f(ku['kurtosis'])}, {p_token(ku['p'])}",
                 "Se detectó curtosis" if colas else "No se detectó curtosis",
                 (f"Las colas son {forma} que las de una normal: más o menos valores "
                  "extremos de los que se esperan." if colas else
                  "Las colas no se distinguen de las de una normal."),
                 alternativa=("colas normales darían g₂ cerca de 0." if colas else
                              "colas pesadas darían más valores extremos."),
                 ok=not colas),
    ]
    if asim or colas:
        lectura = ("La forma se aparta de la normal: " +
                   " y ".join(t for t, hay in ((f"asimetría {lado}", asim),
                                               (f"colas {forma}", colas)) if hay) +
                   ". Para resumir, la mediana; para comparar, pruebas que no supongan "
                   "normalidad.")
    else:
        lectura = "No se detectó que la forma se aparte de la normal, ni en simetría ni en colas."
    return _armar(
        "asimetria_curtosis", titulo, c, valores,
        Metodo("Pruebas de D'Agostino (asimetría) y Anscombe-Glynn (curtosis)",
               "Miden la forma de la distribución por separado: hacia dónde se inclina y "
               "cuán pesadas son sus colas. El exceso de curtosis mide colas, no «picos» "
               "(Westfall 2014)."),
        supuestos, lectura,
        ("Con muchos datos cualquier apartamiento mínimo se detecta, y con pocos casi "
         "ninguno: mirá los valores de g₁ y g₂, no solo el p."),
        avisos=ku.get("avisos"),
        figuras=[Figura("Distribución", lambda: _figura_histograma(
            c.valores, col, float(np.mean(c.valores)), float(np.std(c.valores, ddof=1))))],
        crudo={"asimetria": sk, "curtosis": ku})


# ============================================================
#  Percentiles
# ============================================================

def percentiles(df, col, opciones=None) -> Resultado:
    titulo = f"Tabla de percentiles — {col}"
    c, rechazo = _columna("percentiles", titulo, df, col)
    if rechazo is not None:
        return rechazo
    r = percentile_table(c.valores)
    if r is None:
        return Resultado.rechazo("percentiles", titulo,
                                 f"Hacen falta al menos 5 datos; hay {c.entrada.n}.", c.entrada)
    n = r["n"]
    valores, faltan = [Valor("n", n)], []
    for fila in r["percentiles"]:
        p = fila["percentile"]
        if np.isfinite(fila["value"]):
            valores.append(Valor(f"P{p}", fila["value"], ic=(fila["ci_low"], fila["ci_high"])))
        else:
            faltan.append(p)
            minimo = int(np.ceil(100 / min(p, 100 - p))) - 1
            valores.append(Valor(f"P{p}", None, nota=f"hacen falta al menos {minimo} datos"))
    paso = Supuesto(
        "¿Alcanzan los datos para cada percentil?",
        f"n = {n}; un percentil p existe si 1 ≤ p·(n + 1)/100 ≤ n",
        "Sí, para todos" if not faltan else "No para " + ", ".join(f"P{p}" for p in faltan),
        ("Todos caen entre el primer y el último dato." if not faltan else
         "Esos percentiles caerían fuera de los datos: extrapolarlos sería inventarlos. "
         "MedCalc aconseja no citar P5 y P95 con menos de 20 datos."),
        ok=not faltan)
    medio = next((f for f in r["percentiles"] if f["percentile"] == 50), None)
    lectura = (f"La mitad de los datos está por debajo de {_f(medio['value'])} (P50)."
               if medio and np.isfinite(medio["value"]) else
               "Cada percentil p deja el p % de los datos por debajo.")
    return _armar(
        "percentiles", titulo, c, valores,
        Metodo("Percentiles por rango p(n + 1), IC por bootstrap",
               "La misma definición de percentil que usan EP28 y el intervalo de referencia "
               "de la app; el IC sale de remuestrear los datos."),
        [paso], lectura,
        ("Estos percentiles describen esta muestra; para un intervalo de referencia (con "
         "sus requisitos de n y de selección de sujetos) está el análisis dedicado, que "
         "sigue EP28."),
        crudo={"percentiles": r})


# ============================================================
#  Medias
# ============================================================

def media_recortada(df, col, opciones=None) -> Resultado:
    titulo = f"Media recortada ({RECORTE:.0%} por cola) — {col}"
    c, rechazo = _columna("media_recortada", titulo, df, col)
    if rechazo is not None:
        return rechazo
    r = trimmed_mean(c.valores, RECORTE)
    if r is None:
        return Resultado.rechazo("media_recortada", titulo,
                                 f"Hacen falta al menos 5 datos; hay {c.entrada.n}.", c.entrada)
    n = c.entrada.n
    k = (n - r["n_trimmed"]) // 2
    media = float(np.mean(c.valores))
    valores = [
        Valor("Media recortada", r["mean"], ic=r["ci95"]),
        Valor("Error estándar", r["se"], nota="de la varianza winsorizada"),
        Valor("Media sin recortar", media),
        Valor("Datos que quedan", r["n_trimmed"], nota=f"de {n}: {k} fuera de cada cola"),
    ]
    paso = Supuesto(
        "¿Cuánto se recortó?", f"{RECORTE:.0%} de cada cola de {n} datos",
        f"{k} de cada lado",
        ("Sin datos recortados la media recortada es la media común: con menos de "
         f"{int(np.ceil(1 / RECORTE))} datos no hay nada que sacar." if k == 0 else
         "Los extremos no mueven esta media; el error estándar sale de la muestra "
         "winsorizada (los extremos reemplazados por el último valor que quedó), así el IC "
         "cubre lo que dice (Tukey y McLaughlin 1963)."),
        ok=k > 0)
    dif = r["mean"] - media
    lectura = (f"La media recortada es {_f(r['mean'])}, contra {_f(media)} de la media común. "
               + ("Casi no cambia: las colas no están arrastrando al promedio."
                  if abs(dif) <= r["se"] else
                  "La diferencia es mayor que su error estándar: las colas (o algún atípico) "
                  "sí están moviendo la media común."))
    return _armar(
        "media_recortada", titulo, c, valores,
        Metodo("Media recortada con IC de Tukey-McLaughlin",
               "Un promedio que no se deja arrastrar por los extremos, sin decidir a mano "
               "cuáles sacar."),
        [paso], lectura,
        ("No reemplaza investigar un atípico: si un valor es un error de carga, se corrige; "
         "si es real, pertenece a los datos."),
        crudo={"media_recortada": r})


def media_geometrica(df, col, opciones=None) -> Resultado:
    titulo = f"Media geométrica — {col}"
    c, rechazo = _columna("media_geometrica", titulo, df, col)
    if rechazo is not None:
        return rechazo
    r = geometric_mean(c.valores)
    if r is None:
        return Resultado.rechazo("media_geometrica", titulo,
                                 f"La columna «{col}» no tiene datos numéricos.", c.entrada)
    falla = Resultado.rechazo_del_core("media_geometrica", titulo, r, c.entrada)
    if falla is not None:
        return falla
    media = float(np.mean(c.valores))
    valores = [Valor("Media geométrica", r["gm"], ic=r["ci95"] if r["n"] >= 2 else None),
               Valor("Media aritmética", media), Valor("n", r["n"])]
    normal, medicion = _normalidad(np.log(c.valores))
    paso = Supuesto(
        "¿Los logaritmos se reparten como una normal?", medicion,
        {True: "Sí", False: "No", None: "No evaluable"}[normal],
        ("El IC sale de los logaritmos y se retransforma: vale, y es asimétrico como los "
         "datos (Altman et al. 1983)." if normal else
         "El IC supone logaritmos normales; con estos datos es aproximado."),
        alternativa=("si no lo fueran, el IC sería aproximado." if normal else
                     "con logaritmos normales, el IC sería exacto."),
        ok=bool(normal))
    return _armar(
        "media_geometrica", titulo, c, valores,
        Metodo("Media geométrica",
               "El promedio que corresponde a datos que crecen multiplicando (títulos, "
               "concentraciones con distribución lognormal): la media de los logaritmos, "
               "retransformada."),
        [paso],
        (f"Media geométrica {_f(r['gm'])}, por debajo de la aritmética ({_f(media)}): la "
         "cola de valores altos pesa menos."),
        "Solo existe con valores positivos: un cero o un negativo la vuelve indefinida.",
        crudo={"media_geometrica": r})


def media_armonica(df, col, opciones=None) -> Resultado:
    titulo = f"Media armónica — {col}"
    c, rechazo = _columna("media_armonica", titulo, df, col)
    if rechazo is not None:
        return rechazo
    r = harmonic_mean(c.valores)
    if r is None:
        return Resultado.rechazo("media_armonica", titulo,
                                 f"La columna «{col}» no tiene datos numéricos.", c.entrada)
    falla = Resultado.rechazo_del_core("media_armonica", titulo, r, c.entrada)
    if falla is not None:
        return falla
    valores = [Valor("Media armónica", r["hm"]), Valor("Media aritmética", float(np.mean(c.valores))),
               Valor("n", r["n"])]
    paso = Supuesto("¿Todos los valores son positivos?", f"{r['n']} valores, todos > 0", "Sí",
                    "La media armónica existe.",
                    alternativa="con un cero o un negativo no estaría definida.")
    return _armar(
        "media_armonica", titulo, c, valores,
        Metodo("Media armónica",
               "El promedio de tasas o razones (velocidades, rendimientos por unidad): la "
               "inversa del promedio de las inversas."),
        [paso], f"Media armónica {_f(r['hm'])}.",
        "Es la media que corresponde a razones; para concentraciones, rara vez es la indicada.",
        crudo={"media_armonica": r})


# ============================================================
#  Normalidad
# ============================================================

def shapiro_wilk(df, col, opciones=None) -> Resultado:
    titulo = f"Prueba de normalidad (Shapiro-Wilk) — {col}"
    c, rechazo = _columna("shapiro_wilk", titulo, df, col)
    if rechazo is not None:
        return rechazo
    if c.entrada.n < 3:
        return Resultado.rechazo("shapiro_wilk", titulo,
                                 f"Hacen falta al menos 3 datos; hay {c.entrada.n}.", c.entrada)
    if np.ptp(c.valores) == 0:
        return Resultado.rechazo("shapiro_wilk", titulo,
                                 f"Todos los valores son iguales a {c.valores[0]:g}: no hay "
                                 "distribución que probar.", c.entrada)
    r = normality_test(c.valores)
    avisos = []
    if c.entrada.n > 5000:
        avisos.append(f"Con {c.entrada.n} datos se probó una submuestra de 5000 (semilla fija): "
                      "el algoritmo de Shapiro-Wilk vale hasta ese tamaño.")
    se_aparta = r["p"] < 0.05
    paso = Supuesto(
        "¿Los datos se apartan de una distribución normal?",
        f"W = {_f(r['w'])}, {p_token(r['p'])} (n = {r['n']})",
        "Se detectó apartamiento" if se_aparta else "No se detectó apartamiento",
        ("Conviene resumir con mediana y cuartiles, y comparar con pruebas que no supongan "
         "normalidad (Wilcoxon, Mann-Whitney, Spearman)." if se_aparta else
         "Se pueden usar la media, la DE y las pruebas paramétricas."),
        alternativa=("sin apartamiento, servirían la media y las pruebas paramétricas."
                     if se_aparta else "con apartamiento, convendría la mediana."),
        ok=not se_aparta)
    return _armar(
        "shapiro_wilk", titulo, c,
        [Valor("n", r["n"]), Valor("W", r["w"]), Valor("p", fmt_p(r["p"]))],
        Metodo("Shapiro-Wilk",
               "Compara los datos ordenados con los que daría una normal: W cerca de 1 es "
               "compatible con la normal."),
        [paso],
        ("Los datos se apartan de la normal." if se_aparta else
         "No se detectó que los datos se aparten de la normal."),
        ("No rechazar no prueba que sea normal: con pocos datos la prueba casi nunca rechaza, y "
         "con miles rechaza por diferencias sin importancia. Mirá el gráfico Q-Q: si los "
         "puntos siguen la recta, la normal describe bien los datos."),
        avisos=avisos,
        figuras=[Figura("Gráfico Q-Q normal", lambda: _figura_qq(c.valores, col))],
        crudo={"shapiro": r})


# ============================================================
#  Valores atípicos
# ============================================================

_MATIZ_ATIPICOS = ("Un atípico no se borra porque la prueba lo marque: se investiga (error de "
                   "carga, de muestra, de medición). Si es real, pertenece a los datos. Y "
                   "siempre se informa cuáles se sacaron y por qué (MedCalc).")


def _paso_normal_resto(valores, sacar, metodo) -> Supuesto:
    """Grubbs y ESD suponen que, sin los atípicos, los datos son normales."""
    resto = np.delete(valores, sacar) if len(sacar) else valores
    normal, medicion = _normalidad(resto)
    return Supuesto(
        "¿Sin los candidatos, los datos son normales?",
        medicion + (f" (sin {len(sacar)} candidato(s))" if len(sacar) else ""),
        {True: "Sí", False: "No", None: "No evaluable"}[normal],
        (f"{metodo} supone una normal para el resto de los datos: se cumple." if normal else
         f"{metodo} supone una normal para el resto de los datos, y no se cumple: puede "
         "marcar como atípicos los valores de una cola larga que son normales para esta "
         "variable. Probá con los logaritmos, o usá Tukey, que no supone una distribución."),
        alternativa=("si no lo fueran, las marcas no serían confiables." if normal else
                     "con datos normales, las marcas serían confiables."),
        ok=bool(normal))


def grubbs(df, col, opciones=None) -> Resultado:
    titulo = f"Valores atípicos — Grubbs — {col}"
    c, rechazo = _columna("grubbs", titulo, df, col)
    if rechazo is not None:
        return rechazo
    r = grubbs_test(c.valores)
    if r is None:
        return Resultado.rechazo("grubbs", titulo,
                                 "Hacen falta al menos 3 datos que no sean todos iguales.",
                                 c.entrada)
    falla = Resultado.rechazo_del_core("grubbs", titulo, r, c.entrada)
    if falla is not None:
        return falla
    atipico = r["is_outlier"]
    valores = [
        Valor("Valor más alejado de la media", r["outlier_value"]),
        Valor("G", r["g"]), Valor("G crítico (α = 0,05)", r["g_crit"]),
        Valor("p", fmt_p(r["p"])),
        Valor("¿Atípico?", "Sí" if atipico else "No"),
    ]
    paso = Supuesto(
        "¿El valor más alejado es atípico?",
        f"G = {_f(r['g'])} contra G crítico {_f(r['g_crit'])}, {p_token(r['p'])}",
        "Sí" if atipico else "No",
        (f"{_f(r['outlier_value'])} está más lejos de la media de lo que el azar explica en "
         f"{r['n']} datos normales." if atipico else
         "Ningún valor está más lejos de lo esperable."),
        alternativa=("si G no pasara el crítico, no se marcaría." if atipico else
                     "si G pasara el crítico, se marcaría."),
        ok=not atipico)
    supuestos = [paso, _paso_normal_resto(c.valores, [r["outlier_index"]] if atipico else [],
                                          "Grubbs")]
    lectura = (f"{_f(r['outlier_value'])} es un valor atípico según Grubbs." if atipico else
               "Grubbs no detectó un valor atípico.")
    return _armar(
        "grubbs", titulo, c, valores,
        Metodo("Prueba de Grubbs, dos colas",
               "Prueba si el valor más alejado de la media es demasiado extremo para una "
               "muestra normal de este tamaño. Busca UN atípico: para más, el ESD "
               "generalizado (repetir Grubbs no vale)."),
        supuestos, lectura, _MATIZ_ATIPICOS,
        figuras=[Figura("Datos", lambda: _figura_puntos(
            c.valores, col, [r["outlier_value"]] if atipico else [],
            [(r["mean"] - r["g_crit"] * r["sd"], "G crítico"),
             (r["mean"] + r["g_crit"] * r["sd"], None)]))],
        crudo={"grubbs": r})


def tukey(df, col, opciones=None) -> Resultado:
    titulo = f"Valores atípicos — Tukey — {col}"
    c, rechazo = _columna("tukey", titulo, df, col)
    if rechazo is not None:
        return rechazo
    r = tukey_outliers(c.valores)
    if r is None:
        return Resultado.rechazo("tukey", titulo,
                                 f"Hacen falta al menos 4 datos; hay {c.entrada.n}.", c.entrada)
    lista = lambda v: ", ".join(num(x) for x in sorted(v)[:10]) + (" …" if len(v) > 10 else "")
    valores = [
        Valor("P25", r["q25"]), Valor("P75", r["q75"]), Valor("Rango intercuartílico", r["iqr"]),
        Valor("Vallas internas", f"{_f(r['lower_inner'])} a {_f(r['upper_inner'])}"),
        Valor("Vallas externas", f"{_f(r['lower_outer'])} a {_f(r['upper_outer'])}"),
        Valor("Fuera de las internas («outside»)", r["n_mild"],
              nota=lista(r["outliers_mild"]) if r["n_mild"] else ""),
        Valor("Fuera de las externas («far out»)", r["n_extreme"],
              nota=lista(r["outliers_extreme"]) if r["n_extreme"] else ""),
    ]
    sk = skewness_test(c.valores)
    asimetrica = sk is not None and not sk.get("error") and sk["p"] < 0.05
    paso = Supuesto(
        "¿La distribución es simétrica?",
        (f"D'Agostino: g₁ = {_f(sk['skewness'])}, {p_token(sk['p'])}"
         if sk is not None and not sk.get("error") else "no evaluable (menos de 8 datos)"),
        "No" if asimetrica else ("Sí" if sk is not None and not sk.get("error") else
                                 "No evaluable"),
        ("Las vallas de Tukey son simétricas: en una distribución inclinada marcan de más en "
         "la cola larga valores que son normales para esta variable. Probá con los "
         "logaritmos." if asimetrica else
         "Las vallas simétricas son adecuadas."),
        ok=not asimetrica)
    if r["n_mild"]:
        lectura = (f"{r['n_mild']} valor(es) fuera de las vallas internas"
                   + (f", {r['n_extreme']} de ellos fuera de las externas (muy lejos)."
                      if r["n_extreme"] else "; ninguno fuera de las externas."))
    else:
        lectura = "Ningún valor cae fuera de las vallas de Tukey."
    return _armar(
        "tukey", titulo, c, valores,
        Metodo("Vallas de Tukey",
               "Marca los valores que caen lejos de la caja central, medidos en rangos "
               "intercuartílicos. No supone ninguna distribución y detecta varios a la vez."),
        [paso], lectura, _MATIZ_ATIPICOS,
        figuras=[Figura("Caja y vallas", lambda: _figura_caja(c.valores, col, r))],
        crudo={"tukey": r})


def esd(df, col, opciones=None) -> Resultado:
    titulo = f"Valores atípicos — ESD generalizado — {col}"
    c, rechazo = _columna("esd", titulo, df, col)
    if rechazo is not None:
        return rechazo
    r = generalized_esd(c.valores, max_outliers=ESD_MAXIMO, alpha=0.05)
    if r is None:
        return Resultado.rechazo("esd", titulo,
                                 f"Hacen falta al menos 5 datos; hay {c.entrada.n}.", c.entrada)
    k = r["n_outliers"]
    valores = [Valor("Atípicos detectados", k),
               Valor("Valores", ", ".join(_f(v) for v in r["outliers"]) if k else "—"),
               Valor("Se buscaron hasta", len(r["test_stats"]))]
    for i, (ri, lam) in enumerate(zip(r["test_stats"], r["critical_vals"]), start=1):
        valores.append(Valor(f"Paso {i}: R", ri,
                             nota=f"λ = {_f(lam)}; candidato {_f(r['candidatos'][i - 1])}"
                                  + (" → pasa" if ri > lam else "")))
    marcados = [np.flatnonzero(c.valores == v)[0] for v in r["outliers"]]
    paso = Supuesto(
        "¿Cuántos atípicos hay?",
        f"el mayor paso con R > λ es el {k}" if k else "ningún paso con R > λ",
        str(k),
        (f"Se declaran los {k} primeros candidatos, aunque alguno de los pasos anteriores no "
         "haya pasado solo: así el ESD resuelve el enmascaramiento, cuando dos atípicos "
         "juntos se esconden entre sí (Rosner 1983)." if k else
         "Ningún candidato se aparta más de lo esperable."),
        ok=k == 0)
    return _armar(
        "esd", titulo, c, valores,
        Metodo("ESD generalizado de Rosner",
               "Busca varios atípicos en un solo paso, sin el enmascaramiento de repetir "
               "Grubbs."),
        [paso, _paso_normal_resto(c.valores, marcados, "El ESD")],
        (f"{k} atípico(s): {', '.join(_f(v) for v in r['outliers'])}." if k else
         "El ESD generalizado no detectó atípicos."),
        _MATIZ_ATIPICOS,
        figuras=[Figura("Datos", lambda: _figura_puntos(c.valores, col, r["outliers"], []))],
        crudo={"esd": r})


# ============================================================
#  Figuras
# ============================================================

def _figura_histograma(valores, col, media, de, mediana=None):
    import matplotlib.pyplot as plt
    from scipy import stats

    fig, ax = plt.subplots(figsize=(8, 5))
    v = np.asarray(valores, dtype=float)
    barras = max(1, min(30, int(np.sqrt(len(v))) + 1)) if np.ptp(v) > 0 else 1
    ax.hist(v, bins=barras, density=True, color='#4f6ef7', alpha=0.45, edgecolor='white')
    if de and np.isfinite(de) and de > 0:
        xs = np.linspace(v.min(), v.max(), 200)
        ax.plot(xs, stats.norm.pdf(xs, media, de), color='#2c3650', lw=1.8,
                label="Normal con la misma media y DE")
    ax.axvline(media, color='#22c55e', lw=1.8, label=f"Media {media:.4g}")
    if mediana is not None:
        ax.axvline(mediana, color='#d97706', lw=1.8, ls='--', label=f"Mediana {mediana:.4g}")
    ax.set_xlabel(str(col))
    ax.set_ylabel("Densidad")
    ax.set_title(f"Distribución de {col}", fontweight='bold')
    ax.legend(framealpha=0.9)
    fig.tight_layout()
    return fig


def _figura_qq(valores, col):
    import matplotlib.pyplot as plt
    from scipy import stats

    fig, ax = plt.subplots(figsize=(7, 6))
    (teoricos, ordenados), (pend, inter, _) = stats.probplot(valores, dist="norm")
    ax.scatter(teoricos, ordenados, color='#4f6ef7', alpha=0.6, edgecolors='white', s=40)
    ax.plot(teoricos, pend * np.asarray(teoricos) + inter, color='#ef4444', lw=1.6,
            label="Lo que daría una normal")
    ax.set_xlabel("Cuantiles de la normal")
    ax.set_ylabel(f"{col}, ordenados")
    ax.set_title("Gráfico Q-Q normal", fontweight='bold')
    ax.legend(framealpha=0.9)
    fig.tight_layout()
    return fig


def _figura_puntos(valores, col, atipicos, lineas):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4.5))
    v = np.asarray(valores, dtype=float)
    rng = np.random.default_rng(0)
    y = rng.uniform(-0.25, 0.25, len(v))
    marcado = np.isin(v, np.asarray(atipicos, dtype=float))
    ax.scatter(v[~marcado], y[~marcado], color='#4f6ef7', alpha=0.6, edgecolors='white', s=45)
    if marcado.any():
        ax.scatter(v[marcado], y[marcado], color='#ef4444', s=70, edgecolors='white',
                   label="Atípico", zorder=3)
    for x, rotulo in lineas:
        ax.axvline(x, color='#d97706', ls='--', lw=1.3, label=rotulo)
    ax.set_yticks([])
    ax.set_ylim(-1, 1)
    ax.set_xlabel(str(col))
    ax.set_title(f"{col}: cada punto es un dato", fontweight='bold')
    if marcado.any() or any(r for _, r in lineas):
        ax.legend(framealpha=0.9)
    fig.tight_layout()
    return fig


def _figura_caja(valores, col, r):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.boxplot(valores, vert=False, whis=1.5, widths=0.5,
               flierprops=dict(marker='o', markerfacecolor='#ef4444', markeredgecolor='white'))
    for x in (r["lower_inner"], r["upper_inner"]):
        ax.axvline(x, color='#d97706', ls='--', lw=1.2)
    for x in (r["lower_outer"], r["upper_outer"]):
        ax.axvline(x, color='#ef4444', ls=':', lw=1.2)
    ax.set_yticks([])
    ax.set_xlabel(str(col))
    ax.set_title("Caja de Tukey: vallas internas (--) y externas (···)", fontweight='bold')
    fig.tight_layout()
    return fig
