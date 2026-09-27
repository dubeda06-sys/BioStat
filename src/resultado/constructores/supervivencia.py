"""Supervivencia: Kaplan-Meier, log-rank y regresión de Cox.

Los números salen del core (`src/core/survival.py`, `src/core/cox_regression.py`)
y se verifican contra lifelines. Cambian a propósito, cada uno con su test:

- Kaplan-Meier ya no imprime una «supervivencia media» que era el promedio de
  los puntos de la curva, un número sin unidad ni sentido: da la mediana con su
  IC y los tiempos hasta el 25 % y el 75 % de eventos. El IC de la curva es el
  log-log (el de lifelines), no el lineal recortado a [0, 1].
- Log-rank compara dos o más grupos (antes, exactamente dos) y con dos da el
  hazard ratio. Prueba si los riesgos son proporcionales, que es cuando el
  log-rank tiene sentido.
- Cox usa las covariables tildadas (antes tomaba en silencio todas las columnas
  de la cuarta en adelante, y sin ninguna ajustaba una columna de unos), prueba
  los riesgos proporcionales con los residuos de Schoenfeld y ya no avisa «no
  convergió» en ajustes sanos.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.core.cox_regression import cox_regression
from src.core.survival import kaplan_meier as _kaplan_meier
from src.core.survival import log_rank_k
from src.resultado.citas import ficha
from src.resultado.datos import columnas_faltantes, filas_completas
from src.resultado.lenguaje import fmt_p, num, p_token
from src.resultado.modelo import Figura, Metodo, Resultado, Supuesto, Valor

MIN_KM = 5
MIN_POR_GRUPO = 3
MAX_GRUPOS = 10
POCOS_EN_RIESGO = 10     # Pocock et al. (2002): la cola con pocos en riesgo engaña
EPV_MINIMO = 10          # Peduzzi et al. (1995), eventos por covariable en Cox
COLORES = ['#4f6ef7', '#ef4444', '#22c55e', '#d97706', '#8b5cf6', '#0891b2', '#db2777',
           '#65a30d', '#78716c', '#0f766e']


def _f(x, dec=4) -> str:
    return Valor("", x, decimales=dec).texto()


def _lista(cols):
    if isinstance(cols, str):
        cols = [cols]
    return list(dict.fromkeys(cols or []))


def _armar(analisis, titulo, entrada, valores, metodo, supuestos, lectura, matiz,
           advertencias=(), figuras=(), crudo=None) -> Resultado:
    f = ficha(analisis)
    return Resultado(analisis=analisis, titulo=titulo, entrada=entrada, valores=valores,
                     metodo=metodo, supuestos=list(supuestos), formula=f.formula,
                     citas=list(f.citas), lectura=lectura, matiz=matiz,
                     advertencias=list(advertencias), figuras=list(figuras), crudo=crudo or {})


def _tiempo_evento(analisis, titulo, df, tiempo, evento, *otras):
    """(filas, t, e, entrada, rechazo): tiempo >= 0 numérico y evento 0/1."""
    falta = columnas_faltantes(df, tiempo, evento, *otras)
    if falta:
        return None, None, None, None, Resultado.rechazo(analisis, titulo, falta)
    if tiempo == evento:
        return None, None, None, None, Resultado.rechazo(
            analisis, titulo, "El tiempo y el evento son la misma columna.")
    filas, entrada = filas_completas(df, tiempo, evento, *otras)

    def rechazo(motivo):
        return None, None, None, None, Resultado.rechazo(analisis, titulo, motivo, entrada)

    t = pd.to_numeric(filas[tiempo], errors="coerce")
    if t.isna().any():
        return rechazo(f"«{tiempo}» (el tiempo) tiene valores que no son números.")
    e = pd.to_numeric(filas[evento], errors="coerce")
    if e.isna().any():
        return rechazo(f"«{evento}» (el evento) tiene texto: tiene que ser 1 = evento, "
                       "0 = censura (seguía sin evento al último control).")
    t, e = t.to_numpy(dtype=float), e.to_numpy(dtype=float)
    if np.any(t < 0):
        return rechazo(f"«{tiempo}» tiene tiempos negativos: el seguimiento no puede ser "
                       "menor que cero.")
    niveles = sorted(set(e.tolist()))
    if not set(niveles) <= {0.0, 1.0}:
        return rechazo(f"«{evento}» tiene que ser 0/1 (1 = evento, 0 = censura); tiene "
                       + ", ".join(f"{v:g}" for v in niveles[:6]) + ".")
    if e.sum() == 0:
        return rechazo("No hay ningún evento: todos los sujetos están censurados y la curva "
                       "no baja.")
    return filas, t, e, entrada, None


def _supuesto_censura(km) -> Supuesto:
    n, c = km["n_total"], km["n_censored"]
    return Supuesto(
        "¿La censura es independiente del pronóstico?",
        f"{c} de {n} censurados ({100 * c / n:.0f} %)", "Se supone",
        "Kaplan-Meier supone que quien sale del seguimiento tiene el mismo riesgo que quien "
        "sigue. Si los que se pierden son los más graves, la curva sobreestima la "
        "supervivencia. No se puede verificar con los datos: sale del diseño.")


def _supuesto_cola(km) -> Supuesto:
    quedan = km["en_riesgo_ultimo_evento"]
    ok = quedan >= POCOS_EN_RIESGO
    return Supuesto(
        "¿Quedan suficientes en riesgo al final de la curva?",
        f"en el último evento quedaban {quedan} en riesgo, de {km['n_total']}",
        "Sí" if ok else "No",
        ("La cola de la curva se apoya en bastantes sujetos." if ok else
         f"Con menos de {POCOS_EN_RIESGO} en riesgo cada evento hace caer la curva de a "
         "escalones grandes: la cola es poco confiable y conviene no leerla (Pocock et al. "
         "2002)."), ok=ok)


def _valores_cuantiles(km, sufijo="") -> list[Valor]:
    valores = []
    for q, nombre in ((0.5, "Mediana de supervivencia"), (0.25, "Tiempo hasta el 25 % de eventos"),
                      (0.75, "Tiempo hasta el 75 % de eventos")):
        t_q, lo, hi = km["cuantiles"][q]
        if t_q is None:
            valores.append(Valor(nombre + sufijo, "no se alcanzó",
                                 nota=f"la curva no bajó de {1 - q:.2f}".replace(".", ",")))
        elif lo is not None and hi is not None:
            valores.append(Valor(nombre + sufijo, t_q, ic=(lo, hi), decimales=2))
        else:
            valores.append(Valor(nombre + sufijo, t_q, decimales=2,
                                 nota=f"IC 95 %: {num(lo)} a — (el límite superior no se "
                                      "alcanzó en el seguimiento)"))
    return valores


def _texto_mediana(km) -> str:
    med, (lo, hi) = km["median_survival"], km["median_ci"]
    if med is None:
        ultimo = km["times"][-1]
        return (f"La curva no bajó de 0,5: más de la mitad sigue sin evento al final del "
                f"seguimiento (S = {km['survival'][-1]:.3f} a tiempo {num(ultimo)}), así que la "
                "mediana no se puede estimar.")
    ic = (f"IC 95 % {num(lo)} a {num(hi)}" if hi is not None else
          f"IC 95 % desde {num(lo)}, sin límite superior en el seguimiento")
    return f"La mitad de los sujetos tuvo el evento a tiempo {num(med)} ({ic})."


# ============================================================
#  Kaplan-Meier
# ============================================================

def kaplan_meier(df, tiempo, evento, opciones=None) -> Resultado:
    """Variable 1 = tiempo de seguimiento; Variable 2 = evento (1) o censura (0)."""
    titulo = f"Kaplan-Meier — {tiempo}"
    _, t, e, entrada, rechazo = _tiempo_evento("kaplan_meier", titulo, df, tiempo, evento)
    if rechazo is not None:
        return rechazo
    if len(t) < MIN_KM:
        return Resultado.rechazo("kaplan_meier", titulo,
                                 f"Hacen falta al menos {MIN_KM} sujetos; hay {len(t)}.", entrada)
    km = _kaplan_meier(t, e)
    falla = Resultado.rechazo_del_core("kaplan_meier", titulo, km, entrada)
    if falla is not None:
        return falla
    s_fin = km["survival"][-1]
    valores = [Valor("Sujetos", km["n_total"]), Valor("Eventos", km["n_events"]),
               Valor("Censurados", km["n_censored"])]
    valores += _valores_cuantiles(km)
    valores.append(Valor(f"Supervivencia al último tiempo ({num(km['times'][-1])})", s_fin,
                         ic=(km["ci_lower"][-1], km["ci_upper"][-1]), decimales=3))
    return _armar(
        "kaplan_meier", titulo, entrada, valores,
        Metodo("Kaplan-Meier con IC log-log",
               "La probabilidad de seguir sin el evento a lo largo del tiempo, usando también "
               "a los que salieron del seguimiento sin tenerlo (censurados) mientras "
               "estuvieron."),
        [_supuesto_censura(km), _supuesto_cola(km)],
        _texto_mediana(km),
        "La curva describe esta muestra: no compara nada. Para comparar grupos está el "
        "log-rank; para ajustar por otras variables, Cox. El promedio de supervivencia no se "
        "estima bien cuando hay censura, por eso se informa la mediana.",
        figuras=[Figura("Curva de Kaplan-Meier",
                        lambda: _figura_km([("", km)], tiempo, con_banda=True))],
        crudo={"km": km})


# ============================================================
#  Log-rank
# ============================================================

def _etiqueta(v) -> str:
    if isinstance(v, (float, np.floating)) and float(v).is_integer():
        return f"{int(v)}"
    return str(v)


def _niveles(serie):
    unicos = list(pd.unique(serie))
    try:
        return sorted(unicos)
    except TypeError:
        return sorted(unicos, key=str)


def _paso_ph(r, que) -> Supuesto:
    """Riesgos proporcionales por Schoenfeld (Grambsch-Therneau), del ajuste de Cox."""
    ph = r.get("riesgos_proporcionales") if isinstance(r, dict) else None
    if ph is None or "error" in ph:
        motivo = (ph or {}).get("error") or (r.get("error") if isinstance(r, dict) else None)
        return Supuesto(
            "¿Los riesgos son proporcionales?", "no se pudo evaluar",
            "Sin evaluar", (motivo or "El ajuste de Cox no convergió.")
            + " Mirá si las curvas se cruzan.", ok=False)
    ok = not (ph["p_global"] < 0.05)
    return Supuesto(
        "¿Los riesgos son proporcionales?",
        f"residuos de Schoenfeld contra el tiempo: χ² = {_f(ph['chi2_global'], 3)}, "
        f"{ph['gl_global']} gl, {p_token(ph['p_global'])}",
        "Sí" if ok else "No",
        (f"No se detecta que el efecto de {que} cambie con el tiempo." if ok else
         f"El efecto de {que} cambia con el tiempo (las curvas se acercan o se cruzan): un "
         "solo HR es un promedio que puede no representar ningún momento. Mirá las curvas y "
         "compará la supervivencia a un tiempo fijo."), ok=ok)


def log_rank(df, tiempo, evento, grupo, opciones=None) -> Resultado:
    """Variable 1 = tiempo; Variable 2 = evento (1) o censura (0); Variable 3 = grupo."""
    titulo = f"Log-rank — {tiempo} según {grupo}"
    if grupo in (tiempo, evento):
        return Resultado.rechazo("log_rank", titulo,
                                 "El grupo tiene que ser una columna distinta del tiempo y del "
                                 "evento.")
    filas, t, e, entrada, rechazo = _tiempo_evento("log_rank", titulo, df, tiempo, evento, grupo)
    if rechazo is not None:
        return rechazo
    niveles = _niveles(filas[grupo])
    k, n = len(niveles), len(t)
    if k < 2:
        return Resultado.rechazo("log_rank", titulo,
                                 f"«{grupo}» (el grupo) tiene un solo valor.", entrada)
    if k > MAX_GRUPOS or k > n / 2:
        return Resultado.rechazo("log_rank", titulo,
                                 f"«{grupo}» tiene {k} valores distintos para {n} filas: parece "
                                 "una medición, no un código de grupo (por ejemplo 1, 2 o A, B).",
                                 entrada)
    codigo = np.array([niveles.index(v) for v in filas[grupo]])
    etiquetas = [_etiqueta(v) for v in niveles]
    tamanos = np.bincount(codigo, minlength=k)
    if tamanos.min() < MIN_POR_GRUPO:
        chico = etiquetas[int(np.argmin(tamanos))]
        return Resultado.rechazo("log_rank", titulo,
                                 f"El grupo «{chico}» tiene {tamanos.min()} sujeto(s); hacen "
                                 f"falta al menos {MIN_POR_GRUPO} por grupo.", entrada)
    # log_rank_k numera los grupos por orden de aparición: ordenadas las filas
    # por grupo, su orden es el de los niveles y el HR es del 2.º sobre el 1.º.
    fila = np.argsort(codigo, kind="stable")
    lr = log_rank_k(t[fila], e[fila], codigo[fila])
    falla = Resultado.rechazo_del_core("log_rank", titulo, lr, entrada)
    if falla is not None:
        return falla
    E = lr["esperados"]
    curvas = [_kaplan_meier(t[codigo == i], e[codigo == i]) for i in range(k)]
    valores = []
    for i, (et, km) in enumerate(zip(etiquetas, curvas)):
        med, (lo, hi) = km["median_survival"], km["median_ci"]
        nota = f"n = {km['n_total']}, {km['n_events']} eventos (esperados {E[i]:.1f})"
        if med is None:
            valores.append(Valor(f"Mediana — {et}", "no se alcanzó", nota=nota))
        elif hi is None:
            valores.append(Valor(f"Mediana — {et}", med, decimales=2,
                                 nota=nota + f"; IC 95 % desde {num(lo)}, sin límite superior"))
        else:
            valores.append(Valor(f"Mediana — {et}", med, ic=(lo, hi), decimales=2, nota=nota))
    valores += [Valor("χ² (log-rank)", lr["chi2"], nota=f"{lr['gl']} gl"),
                Valor("p", fmt_p(lr["p"]))]
    hr = lr.get("hr") if k == 2 else None
    if hr is not None:
        valores.append(Valor(f"Hazard ratio {etiquetas[1]} / {etiquetas[0]}", hr,
                             ic=lr["hr_ic95"], decimales=3,
                             nota="por O/E de cada grupo (Altman 1991)"))
    detecta = lr["p"] < 0.05
    dummies = np.column_stack([(codigo == i).astype(float) for i in range(1, k)])
    cox = cox_regression(t, e, dummies)
    supuestos = [
        Supuesto(
            "¿Las curvas difieren?",
            f"χ² = {_f(lr['chi2'], 3)}, {lr['gl']} gl, {p_token(lr['p'])}",
            "Se detectó diferencia" if detecta else "No se detectó diferencia",
            (("Al menos una curva se separa de las otras. Con más de dos grupos el log-rank no "
              "dice cuál: compará de a pares." if k > 2 else
              "Las dos curvas se separan más de lo que explica el azar.") if detecta else
             "Con estos datos las curvas no se distinguen. No prueba que sean iguales: con "
             "pocos eventos el log-rank tiene poco poder.")),
        _paso_ph(cox, "el grupo"),
        _supuesto_censura(_kaplan_meier(t, e)),
    ]
    if detecta and hr is not None:
        lectura = (f"Las curvas difieren ({p_token(lr['p'])}): el riesgo del grupo "
                   f"{etiquetas[1]} es {hr:.2f} veces el de {etiquetas[0]}.")
    elif detecta:
        lectura = f"Al menos una de las {k} curvas difiere de las otras ({p_token(lr['p'])})."
    else:
        lectura = f"No se detectó diferencia entre las curvas ({p_token(lr['p'])})."
    return _armar(
        "log_rank", titulo, entrada, valores,
        Metodo("Log-rank (Mantel-Cox)" + (f", {k} grupos" if k > 2 else ""),
               "Compara las curvas de supervivencia enteras: en cada tiempo con evento cuenta "
               "cuántos eventos tuvo cada grupo contra los que le tocaban por su número en "
               "riesgo."),
        supuestos, lectura,
        "El log-rank compara las curvas enteras, no la supervivencia a un tiempo dado, y no "
        "ajusta por otras variables (para eso, Cox). Un p chico no dice cuánto difieren: "
        "mirá las medianas y el HR.",
        figuras=[Figura("Curvas de Kaplan-Meier por grupo",
                        lambda: _figura_km(list(zip(etiquetas, curvas)), tiempo,
                                           con_banda=k <= 3))],
        crudo={"log_rank": lr, "curvas": dict(zip(etiquetas, curvas)), "cox": cox})


# ============================================================
#  Regresión de Cox
# ============================================================

def regresion_cox(df, tiempo, evento, covariables, opciones=None) -> Resultado:
    """Variable 1 = tiempo; Variable 2 = evento (1) o censura (0); covariables tildadas."""
    covariables = [c for c in _lista(covariables) if c not in (tiempo, evento)]
    titulo = f"Regresión de Cox — {tiempo}"
    if not covariables:
        return Resultado.rechazo("regresion_cox", titulo,
                                 "Tildá al menos una covariable, distinta del tiempo y del "
                                 "evento.")
    filas, t, e, entrada, rechazo = _tiempo_evento("regresion_cox", titulo, df, tiempo, evento,
                                                   *covariables)
    if rechazo is not None:
        return rechazo
    try:
        X = filas[covariables].to_numpy(dtype=float)
    except (TypeError, ValueError):
        return Resultado.rechazo("regresion_cox", titulo,
                                 "Las covariables tienen que ser números. Una categórica de dos "
                                 "valores va como 0/1.", entrada)
    constantes = [c for j, c in enumerate(covariables) if np.ptp(X[:, j]) == 0]
    if constantes:
        return Resultado.rechazo("regresion_cox", titulo,
                                 f"«{constantes[0]}» vale lo mismo en todos los sujetos: no hay "
                                 "efecto que estimar.", entrada)
    r = cox_regression(t, e, X)
    falla = Resultado.rechazo_del_core("regresion_cox", titulo, r, entrada)
    if falla is not None:
        return falla
    entrada.n = r["n"]
    p = len(covariables)
    valores = [Valor("n", r["n"]), Valor("Eventos", r["events"]),
               Valor("Razón de verosimilitudes (χ²)", r["lr_chi2"],
                     nota=f"{r['lr_gl']} gl, {p_token(r['lr_p'])}")]
    for j, c in enumerate(covariables):
        valores.append(Valor(f"HR — {c}", r["hazard_ratios"][j],
                             ic=(r["hr_ci_low"][j], r["hr_ci_high"][j]),
                             nota=f"b = {_f(r['coefficients'][j])}, EE {_f(r['se'][j])}, "
                                  f"{p_token(r['p_values'][j])}"))
    valores += [Valor("Log-verosimilitud parcial", r["log_likelihood"]),
                Valor("AIC", r["aic"], decimales=2)]
    epv = r["events"] / p
    supuestos = [Supuesto(
        "¿Hay eventos suficientes para tantas covariables?",
        f"{r['events']} eventos, {p} covariable(s): {epv:.1f} por covariable",
        "Sí" if epv >= EPV_MINIMO else "No",
        ("Con 10 o más eventos por covariable los coeficientes son estables (Peduzzi et al. "
         "1995)." if epv >= EPV_MINIMO else
         "Con menos de 10 eventos por covariable los HR se sesgan y los IC fallan (Peduzzi et "
         "al. 1995): sacá covariables o juntá más eventos."), ok=epv >= EPV_MINIMO)]
    ph = r.get("riesgos_proporcionales")
    paso = _paso_ph(r, "alguna covariable")
    if ph is not None and "error" not in ph and not paso.ok:
        cuales = [c for c, pj in zip(covariables, ph["p"]) if pj < 0.05]
        if cuales:
            paso.consecuencia = paso.consecuencia.replace(
                "alguna covariable", ", ".join(f"«{c}»" for c in cuales))
            paso.medicion += "; por covariable: " + ", ".join(
                f"{c} {p_token(pj)}" for c, pj in zip(covariables, ph["p"]))
    supuestos.append(paso)
    # El aviso de eventos por covariable ya es un paso; el de separación se
    # rearma con los nombres (el core solo sabe el número de columna).
    advertencias = [a for a in r["avisos"] if "eventos para" not in a and "maximo finito" not in a]
    if r.get("separadas"):
        advertencias.insert(0, "La verosimilitud no tiene máximo finito para "
                            + ", ".join(f"«{covariables[j]}»" for j in r["separadas"])
                            + " (separación: por ejemplo, todos los eventos en un solo grupo). "
                            "El HR tiende a infinito o a cero, y su IC y su p no sirven.")
    aportan = [c for c, pj in zip(covariables, r["p_values"]) if pj < 0.05]
    lectura = (("Se asocian con el riesgo, con las demás en el modelo: "
                + ", ".join(f"{c} (HR {r['hazard_ratios'][covariables.index(c)]:.2f})"
                            for c in aportan) + ".") if aportan else
               "Ninguna covariable se asocia por sí sola con el riesgo, con las demás en el "
               "modelo.")
    figuras = [Figura("Hazard ratios con su IC 95 %",
                      lambda: _figura_hr(covariables, r))]
    if ph is not None and "error" not in ph:
        figuras.append(Figura("Residuos de Schoenfeld contra el tiempo",
                              lambda: _figura_schoenfeld(covariables, ph)))
    return _armar(
        "regresion_cox", titulo, entrada, valores,
        Metodo("Riesgos proporcionales de Cox, empates de Efron",
               "Cuánto se multiplica el riesgo instantáneo del evento por cada unidad de cada "
               "covariable, con las demás fijas, sin suponer la forma de la curva de base."),
        supuestos, lectura,
        "Cada HR es por unidad de la covariable: para una 0/1, el riesgo de 1 frente a 0; para "
        "una continua, por cada unidad (cambiar la unidad cambia el HR). El modelo supone que "
        "el log del riesgo cambia en línea recta con cada continua. Asociación no es causa.",
        advertencias, figuras, crudo={"cox": r, "covariables": covariables})


# ============================================================
#  Figuras
# ============================================================

def _figura_km(curvas, tiempo, con_banda=True):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 6))
    for i, (etiqueta, km) in enumerate(curvas):
        color = COLORES[i % len(COLORES)]
        ax.step(km["times"], km["survival"], where='post', color=color, lw=2,
                label=etiqueta or None)
        if con_banda:
            ax.fill_between(km["times"], km["ci_lower"], km["ci_upper"], step='post',
                            alpha=0.12, color=color)
        # Marcas de censura: el sujeto salió sin evento en ese tiempo.
        tc = km["censura_tiempos"]
        if len(tc):
            idx = np.searchsorted(km["times"], tc, side="right") - 1
            ax.plot(tc, km["survival"][idx], '|', color=color, ms=9, mew=1.4)
    ax.axhline(0.5, color='#9ca3af', ls=':', lw=1)
    ax.set_xlabel(f"Tiempo ({tiempo})")
    ax.set_ylabel("Probabilidad de seguir sin el evento")
    ax.set_ylim(0, 1.05)
    ax.set_xlim(left=0)
    ax.set_title("Kaplan-Meier" + (" por grupo" if len(curvas) > 1 else ""), fontweight='bold')
    if len(curvas) > 1:
        ax.legend(framealpha=0.9)
    ax.grid(True, alpha=0.25)
    ax.text(0.99, 0.01, "| = censura", transform=ax.transAxes, ha='right', va='bottom',
            fontsize=8, color='#6b7280')
    fig.tight_layout()
    return fig


def _figura_hr(covariables, r):
    import matplotlib.pyplot as plt

    k = len(covariables)
    fig, ax = plt.subplots(figsize=(8, 1.2 + 0.6 * k))
    y = np.arange(k)[::-1]
    hr, lo, hi = r["hazard_ratios"], r["hr_ci_low"], r["hr_ci_high"]
    ax.errorbar(hr, y, xerr=[hr - lo, hi - hr], fmt='s', color='#4f6ef7', ecolor='#4f6ef7',
                capsize=4, ms=7)
    ax.axvline(1, color='#9ca3af', ls='--', lw=1)
    ax.set_xscale('log')
    ax.set_yticks(y)
    ax.set_yticklabels(covariables)
    ax.set_xlabel("Hazard ratio (escala log)")
    ax.set_title("Hazard ratios con su IC 95 %", fontweight='bold')
    fig.tight_layout()
    return fig


def _figura_schoenfeld(covariables, ph):
    import matplotlib.pyplot as plt
    from statsmodels.nonparametric.smoothers_lowess import lowess

    k = len(covariables)
    fig, axes = plt.subplots(k, 1, figsize=(8, 3.2 * k), squeeze=False)
    orden = np.argsort(ph["g"])
    g = ph["g"][orden]
    for j, (ax, c) in enumerate(zip(axes[:, 0], covariables)):
        res = ph["residuos_escalados"][orden, j]
        ax.scatter(g, res, s=12, color='#4f6ef7', alpha=0.5)
        if len(g) >= 5:
            suave = lowess(res, g, frac=2 / 3, return_sorted=True)
            ax.plot(suave[:, 0], suave[:, 1], color='#ef4444', lw=2)
        ax.axhline(np.mean(res), color='#9ca3af', ls='--', lw=1)
        ax.set_ylabel(f"β(t) — {c}")
        ax.set_title(f"{c}: {p_token(ph['p'][j])} (una línea plana = riesgo proporcional)",
                     fontsize=10)
    axes[-1, 0].set_xlabel("Tiempo transformado: 1 − KM(t)")
    fig.tight_layout()
    return fig
