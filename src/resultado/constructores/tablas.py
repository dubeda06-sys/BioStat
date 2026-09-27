"""Proporciones y tablas de contingencia, migradas a `Resultado`.

Chi-cuadrado, Fisher, McNemar, dos proporciones (calculadora), odds ratio,
riesgo relativo y Cochran-Mantel-Haenszel. El chi-cuadrado sigue el mismo
camino que el Omnianálisis: con frecuencias esperadas chicas, Fisher en 2×2 y p
por simulación en tablas más grandes.
"""
from __future__ import annotations

import numpy as np
from scipy import stats
from scipy.stats.contingency import association, odds_ratio as or_scipy

from src.analysis.omni_config import DEFAULT_CONFIG as _CFG
from src.core.cmh import cmh_test
from src.core.diagnostic_tests import compare_two_proportions, odds_ratio, relative_risk
from src.core.statistics import chi_square_test, mcnemar_test
from src.resultado.citas import ficha
from src.resultado.datos import columnas_faltantes, filas_completas, tabla_2x2, tabla_rxc
from src.resultado.lenguaje import fmt_p, p_token
from src.resultado.modelo import Metodo, Resultado, Supuesto, Valor

EJEMPLOS = {"dos_proporciones": {"x1": 24, "n1": 80, "x2": 12, "n2": 75}}


def _f(x, dec=4) -> str:
    return Valor("", x, decimales=dec).texto()


def _armar(analisis, titulo, entrada, valores, metodo, supuestos, lectura, matiz,
           advertencias=(), crudo=None) -> Resultado:
    f = ficha(analisis)
    return Resultado(analisis=analisis, titulo=titulo, entrada=entrada, valores=valores,
                     metodo=metodo, supuestos=list(supuestos), formula=f.formula,
                     citas=list(f.citas), lectura=lectura, matiz=matiz,
                     advertencias=list(advertencias), crudo=crudo or {})


def _celdas(t) -> list[Valor]:
    return [Valor(f"{t.filas[0]} · {t.columnas[0]}", t.a), Valor(f"{t.filas[0]} · {t.columnas[1]}", t.b),
            Valor(f"{t.filas[1]} · {t.columnas[0]}", t.c), Valor(f"{t.filas[1]} · {t.columnas[1]}", t.d)]


def _tabla(analisis, titulo, df, c1, c2):
    t = tabla_2x2(df, c1, c2)
    if t.motivo:
        return None, Resultado.rechazo(analisis, titulo, t.motivo, t.entrada)
    return t, None


def _paso_asociacion(p, que="asociación") -> Supuesto:
    detecta = p < 0.05
    return Supuesto(f"¿Hay {que}?", p_token(p),
                    f"Se detectó {que}" if detecta else f"No se detectó {que}",
                    ("Las dos variables no se reparten independientes." if detecta else
                     "Con estos datos no se puede afirmar que estén asociadas — tampoco "
                     "descartarlo."))


# ============================================================

def chi_cuadrado(df, c1, c2, opciones=None) -> Resultado:
    titulo = f"Chi-cuadrado — {c1} × {c2}"
    tabla, entrada, motivo = tabla_rxc(df, c1, c2)
    if motivo:
        return Resultado.rechazo("chi_cuadrado", titulo, motivo, entrada)
    r = chi_square_test(tabla.values)
    if r is None:
        return Resultado.rechazo("chi_cuadrado", titulo, "La tabla no se puede analizar.", entrada)
    esperadas = np.asarray(r["expected"])
    minima = float(esperadas.min())
    es_2x2 = tabla.shape == (2, 2)
    alcanza = minima >= _CFG.FISHER_MIN_FREQ
    v = float(association(tabla.values, method="cramer"))
    valores = [Valor(f"{f} · {c}", int(tabla.loc[f, c])) for f in tabla.index for c in tabla.columns]
    if alcanza:
        nombre = "Chi-cuadrado" + (" con corrección de Yates" if es_2x2 else "")
        p = r["p"]
        valores += [Valor("χ²", r["chi2"], nota=f"{r['df']} gl"), Valor("p", fmt_p(p))]
    elif es_2x2:
        nombre = "Prueba exacta de Fisher"
        p = float(stats.fisher_exact(tabla.values).pvalue)
        valores += [Valor("p (Fisher)", fmt_p(p))]
    else:
        nombre = "Chi-cuadrado con p por simulación"
        mc = stats.chi2_contingency(
            tabla.values, correction=False,
            method=stats.PermutationMethod(n_resamples=_CFG.MONTECARLO_N,
                                           rng=np.random.default_rng(_CFG.MONTECARLO_SEMILLA)))
        p = float(mc.pvalue)
        valores += [Valor("χ²", float(mc.statistic), nota=f"{r['df']} gl"),
                    Valor("p (simulación)", fmt_p(p), nota=f"{_CFG.MONTECARLO_N} tablas")]
    valores += [Valor("V de Cramér", v, nota="0 = independencia, 1 = asociación total"),
                Valor("Frecuencia esperada mínima", minima, decimales=2)]
    supuestos = [
        Supuesto("¿Alcanzan las frecuencias esperadas para la aproximación?",
                 f"esperada mínima {minima:.2f} (umbral {_CFG.FISHER_MIN_FREQ:g})",
                 "Sí" if alcanza else "No",
                 (f"{nombre}." if alcanza else
                  ("Con casilleros flacos la aproximación chi-cuadrado no vale: en 2×2, la "
                   "prueba exacta de Fisher." if es_2x2 else
                   "Con casilleros flacos la aproximación no vale: el p sale de permutar los "
                   "datos con los totales fijos (semilla fija, siempre el mismo p).")),
                 alternativa=("con esperadas chicas, Fisher o simulación." if alcanza else
                              "con esperadas de 5 o más, el chi-cuadrado común."),
                 ok=True),
        _paso_asociacion(p),
    ]
    return _armar(
        "chi_cuadrado", titulo, entrada, valores,
        Metodo(nombre, "Compara la tabla observada con la que se esperaría si las dos variables "
                       "fueran independientes."),
        supuestos,
        (f"Se detectó asociación entre {c1} y {c2} (V de Cramér {v:.3f})." if p < 0.05 else
         f"No se detectó asociación entre {c1} y {c2}."),
        "Asociación no es causa, y el p no mide su fuerza: para eso, la V de Cramér o el OR.",
        crudo={"chi2": r, "camino": nombre, "p": p, "cramer": v})


def fisher(df, c1, c2, opciones=None) -> Resultado:
    titulo = f"Prueba exacta de Fisher — {c1} × {c2}"
    t, rechazo = _tabla("fisher", titulo, df, c1, c2)
    if rechazo is not None:
        return rechazo
    tabla = [[t.a, t.b], [t.c, t.d]]
    p = float(stats.fisher_exact(tabla).pvalue)
    orc = or_scipy(tabla, kind="conditional")
    ic = orc.confidence_interval()
    valores = [*_celdas(t), Valor("OR (máxima verosimilitud condicional)", float(orc.statistic),
                                  ic=(float(ic.low), float(ic.high))), Valor("p", fmt_p(p))]
    return _armar(
        "fisher", titulo, t.entrada, valores,
        Metodo("Prueba exacta de Fisher",
               "Calcula la probabilidad exacta de tablas tan o más extremas con los mismos "
               "totales: no depende de aproximaciones, sirve con casilleros chicos."),
        [_paso_asociacion(p)],
        ("Se detectó asociación." if p < 0.05 else "No se detectó asociación.") + " " + t.lectura,
        "El OR condicional es el que va con Fisher; puede diferir un poco del OR de la tabla.",
        advertencias=t.avisos, crudo={"p": p, "or": float(orc.statistic)})


def mcnemar(df, c1, c2, opciones=None) -> Resultado:
    titulo = f"McNemar — {c1} y {c2}"
    t, rechazo = _tabla("mcnemar", titulo, df, c1, c2)
    if rechazo is not None:
        return rechazo
    r = mcnemar_test(t.b, t.c)
    n = t.a + t.b + t.c + t.d
    p1, p2 = (t.a + t.b) / n if n else np.nan, (t.a + t.c) / n if n else np.nan
    valores = [*_celdas(t), Valor("Discordantes", f"b = {t.b}, c = {t.c}"),
               Valor(f"Proporción positiva según {c1}", p1, decimales=3),
               Valor(f"Proporción positiva según {c2}", p2, decimales=3),
               Valor("p", fmt_p(r["p"]), nota=r["metodo"])]
    supuestos = [
        Supuesto("¿Cuántos pares discordantes hay?", f"b + c = {t.b + t.c}",
                 "Pocos" if t.b + t.c < 25 else "Suficientes",
                 ("Con menos de 25 discordantes, p binomial exacta." if t.b + t.c < 25 else
                  "Con 25 o más, chi-cuadrado con la corrección de Edwards."), ok=True),
        _paso_asociacion(r["p"], "cambio entre las dos clasificaciones"),
    ]
    return _armar(
        "mcnemar", titulo, t.entrada, valores,
        Metodo("McNemar", "La misma clasificación binaria en dos momentos o por dos métodos, en "
                          "los mismos sujetos: solo cuentan los pares que cambian."),
        supuestos,
        (f"La proporción de positivos cambia: {p1:.3f} según {c1} y {p2:.3f} según {c2}."
         if r["p"] < 0.05 else "No se detectó cambio en la proporción de positivos."),
        "Para medir cuánto concuerdan dos métodos cualitativos, además está kappa.",
        advertencias=t.avisos, crudo={"mcnemar": r})


def dos_proporciones(opciones) -> Resultado:
    """Calculadora: eventos y total de cada grupo."""
    titulo = "Comparar dos proporciones"
    try:
        x1, n1, x2, n2 = (float(opciones[k]) for k in ("x1", "n1", "x2", "n2"))
    except KeyError as e:
        return Resultado.rechazo("dos_proporciones", titulo, f"Falta el dato {e.args[0]}.")
    except (TypeError, ValueError):
        return Resultado.rechazo("dos_proporciones", titulo, "Los datos tienen que ser números.")
    if any(v != int(v) or v < 0 for v in (x1, n1, x2, n2)):
        return Resultado.rechazo("dos_proporciones", titulo,
                                 "Eventos y totales son conteos: enteros no negativos.")
    if x1 > n1 or x2 > n2 or n1 < 1 or n2 < 1:
        return Resultado.rechazo("dos_proporciones", titulo,
                                 "Los eventos no pueden superar al total, y cada total es al "
                                 "menos 1.")
    r = compare_two_proportions(x1 / n1, int(n1), x2 / n2, int(n2))
    falla = Resultado.rechazo_del_core("dos_proporciones", titulo, r)
    if falla is not None:
        return falla
    valores = [Valor("Grupo 1", x1 / n1, decimales=4, nota=f"{int(x1)} de {int(n1)}"),
               Valor("Grupo 2", x2 / n2, decimales=4, nota=f"{int(x2)} de {int(n2)}"),
               Valor("Diferencia (1 − 2)", r["diff"], ic=r["ci95"], nota="IC de Newcombe"),
               Valor("z", r["z"]), Valor("p", fmt_p(r["p"]))]
    return _armar(
        "dos_proporciones", titulo, None, valores,
        Metodo("Prueba z de dos proporciones, IC de Newcombe",
               "Compara dos proporciones de grupos independientes a partir de sus conteos."),
        [_paso_asociacion(r["p"], "diferencia")],
        (f"La diferencia es {_f(r['diff'])} (IC 95 % {_f(r['ci95'][0])} a {_f(r['ci95'][1])}): "
         + ("se detectó." if r["p"] < 0.05 else "no se detectó.")),
        "Con conteos chicos, mejor la prueba exacta de Fisher sobre la tabla.",
        crudo={"comparacion": r})


def _paso_or_rr(nombre, ic) -> Supuesto:
    uno = ic[0] <= 1 <= ic[1]
    return Supuesto(
        f"¿El {nombre} se aparta de 1?", f"IC 95 % {_f(ic[0])} a {_f(ic[1])}",
        "No se detectó" if uno else "Sí",
        ("El intervalo incluye el 1: con estos datos no se puede afirmar asociación." if uno else
         "El intervalo excluye el 1: la exposición se asocia con el evento."))


def odds_ratio_tabla(df, c1, c2, opciones=None) -> Resultado:
    """Variable 1 = exposición, Variable 2 = evento."""
    titulo = f"Odds ratio — {c2} según {c1}"
    t, rechazo = _tabla("odds_ratio", titulo, df, c1, c2)
    if rechazo is not None:
        return rechazo
    r = odds_ratio(*t.celdas)
    ic = (r["ci_lower"], r["ci_upper"])
    haldane = min(t.celdas) == 0
    valores = [*_celdas(t), Valor("OR", r["or"], ic=ic), Valor("p", fmt_p(r["p"]))]
    avisos = list(t.avisos or [])
    if haldane:
        avisos.append("Una celda vale 0: se sumó 0,5 a todas (Haldane) para poder calcular el OR "
                      "y su IC.")
    return _armar(
        "odds_ratio", titulo, t.entrada, valores,
        Metodo("Odds ratio con IC de Woolf",
               "Cuántas veces más chances de evento tienen los expuestos. En estudios de casos "
               "y controles es la única medida de asociación que se puede estimar."),
        [_paso_or_rr("OR", ic)],
        (f"OR = {_f(r['or'])}: " + ("los expuestos tienen más chances de evento." if ic[0] > 1
                                    else "los expuestos tienen menos chances de evento."
                                    if ic[1] < 1 else "no se detectó asociación.")),
        "Con eventos frecuentes el OR exagera el riesgo relativo: no se lee como «veces más "
        "riesgo».", advertencias=avisos, crudo={"or": r})


def riesgo_relativo(df, c1, c2, opciones=None) -> Resultado:
    """Variable 1 = exposición, Variable 2 = evento."""
    titulo = f"Riesgo relativo — {c2} según {c1}"
    t, rechazo = _tabla("riesgo_relativo", titulo, df, c1, c2)
    if rechazo is not None:
        return rechazo
    r = relative_risk(*t.celdas)
    falla = Resultado.rechazo_del_core("riesgo_relativo", titulo, r, t.entrada)
    if falla is not None:
        return falla
    ic = (r["ci_lower"], r["ci_upper"])
    valores = [*_celdas(t), Valor("Riesgo en expuestos", r["risk1"], decimales=4),
               Valor("Riesgo en no expuestos", r["risk0"], decimales=4),
               Valor("RR", r["rr"], ic=ic), Valor("p", fmt_p(r["p"])),
               Valor(r["nnt_tipo"], r["nnt"] if np.isfinite(r["nnt"]) else None, decimales=1)]
    avisos = list(t.avisos or [])
    if r["haldane"]:
        avisos.append("Ningún expuesto tuvo el evento: se sumó 0,5 a todas las celdas (Haldane).")
    return _armar(
        "riesgo_relativo", titulo, t.entrada, valores,
        Metodo("Riesgo relativo con IC por el logaritmo",
               "Cuántas veces más riesgo de evento tienen los expuestos. Exige que los riesgos "
               "se puedan estimar: cohortes o ensayos, no casos y controles."),
        [_paso_or_rr("RR", ic)],
        (f"RR = {_f(r['rr'])}. {r['nnt_tipo']} = "
         + (f"{r['nnt']:.1f}: hay que exponer a esa cantidad para un evento de diferencia."
            if np.isfinite(r["nnt"]) else "sin efecto.")),
        "El NNT es un promedio de este grupo; no dice nada de un paciente en particular.",
        advertencias=avisos, crudo={"rr": r})


def cmh(df, exposicion, evento, estrato, opciones=None) -> Resultado:
    """Datos crudos: exposición (V1), evento (V2) y estrato (V3), una fila por sujeto."""
    titulo = f"Cochran-Mantel-Haenszel — {evento} según {exposicion}, por {estrato}"
    falta = columnas_faltantes(df, exposicion, evento, estrato)
    if falta:
        return Resultado.rechazo("cmh", titulo, falta)
    if len({exposicion, evento, estrato}) < 3:
        return Resultado.rechazo("cmh", titulo, "Elegí tres columnas distintas.")
    filas, entrada = filas_completas(df, exposicion, evento, estrato)
    estratos = list(dict.fromkeys(filas[estrato]))
    if len(estratos) < 2 or len(estratos) > 20:
        return Resultado.rechazo("cmh", titulo,
                                 f"«{estrato}» tiene {len(estratos)} valores: el estrato es un "
                                 "código de grupo, con entre 2 y 20 valores.", entrada)
    tablas, avisos = [], []
    for e in estratos:
        sub = filas[filas[estrato] == e]
        t = tabla_2x2(sub, exposicion, evento)
        if t.motivo:
            return Resultado.rechazo("cmh", titulo, f"Estrato {e}: {t.motivo}", entrada)
        tablas.append([[t.a, t.b], [t.c, t.d]])
    tablas = np.asarray(tablas, dtype=float)
    r = cmh_test(tablas)
    from statsmodels.stats.contingency_tables import StratifiedTable
    bd = StratifiedTable(np.transpose(tablas, (1, 2, 0))).test_equal_odds()
    homogeneo = bd.pvalue >= 0.05
    ic = (r["or_ci_low"], r["or_ci_high"])
    valores = [Valor("Estratos", r["K"]),
               Valor("OR común de Mantel-Haenszel", r["common_odds_ratio"], ic=ic),
               Valor("χ² de CMH", r["cmh_statistic"], nota="1 gl"),
               Valor("p", fmt_p(r["p_value"])),
               Valor("Homogeneidad (Breslow-Day)", fmt_p(bd.pvalue))]
    for e, tb in zip(estratos, tablas):
        (a, b), (c, d) = tb
        valores.append(Valor(f"Estrato {e}", f"{int(a)}, {int(b)} / {int(c)}, {int(d)}"))
    supuestos = [
        Supuesto("¿El OR es parecido en todos los estratos?",
                 f"Breslow-Day: {p_token(bd.pvalue)}", "Sí" if homogeneo else "No",
                 ("Un OR común resume bien los estratos." if homogeneo else
                  "El OR cambia de un estrato a otro: un OR común esconde esa diferencia "
                  "(modificación de efecto). Mirá cada estrato."),
                 ok=bool(homogeneo)),
        _paso_or_rr("OR común", ic),
    ]
    return _armar(
        "cmh", titulo, entrada, valores,
        Metodo("Cochran-Mantel-Haenszel",
               f"La asociación entre exposición y evento, ajustada por {estrato}: compara dentro "
               "de cada estrato y combina."),
        supuestos,
        (f"Ajustado por {estrato}, OR = {_f(r['common_odds_ratio'])}: "
         + ("se detectó asociación." if r["p_value"] < 0.05 else "no se detectó asociación.")),
        "Ajustar por un estrato no ajusta por lo que no se midió.",
        advertencias=avisos, crudo={"cmh": r, "breslow_day_p": float(bd.pvalue)})
