"""Los sueltos del menú: meta-análisis, mediciones seriales y las pruebas diagnósticas.

Cambian a propósito, cada uno con su test:

- El meta-análisis informa τ² y el intervalo de predicción (dónde caería un
  estudio nuevo), prueba el efecto de estudios pequeños con Egger desde 10
  estudios y dibuja el funnel plot. Con τ² = 0 ya no cambia la etiqueta a
  «efectos fijos» por su cuenta: el modelo es el elegido.
- La prueba diagnóstica recalcula VPP y VPN para la prevalencia que se cargue
  (dependen de ella, no de la prueba) y trae las razones de verosimilitud con
  su IC. Las razones de verosimilitud dan la probabilidad post-test.
"""
from __future__ import annotations

import numpy as np

from src.core.diagnostic_tests import diagnostic_test, likelihood_ratios
from src.core.meta_analysis import meta_analysis
from src.core.serial_measurements import serial_measurements_summary
from src.resultado.citas import ficha
from src.resultado.datos import columnas_faltantes, filas_completas, tabla_2x2
from src.resultado.lenguaje import fmt_p, num, p_token
from src.resultado.modelo import Entrada, Figura, Metodo, Resultado, Supuesto, Valor


def _armar(analisis, titulo, entrada, valores, metodo, supuestos, lectura, matiz,
           advertencias=(), figuras=(), crudo=None) -> Resultado:
    f = ficha(analisis)
    return Resultado(analisis=analisis, titulo=titulo, entrada=entrada, valores=valores,
                     metodo=metodo, supuestos=list(supuestos), formula=f.formula,
                     citas=list(f.citas), lectura=lectura, matiz=matiz,
                     advertencias=list(advertencias), figuras=list(figuras), crudo=crudo or {})


# ============================================================
#  Meta-análisis
# ============================================================

def meta_analisis(df, efecto, ee, opciones=None) -> Resultado:
    """Variable 1 = el efecto de cada estudio; Variable 2 = su error estándar.

    `opciones["modelo"]`: "aleatorio" (DerSimonian-Laird, por defecto) | "fijo".
    """
    opciones = opciones or {}
    fijo = opciones.get("modelo") == "fijo"
    titulo = f"Meta-análisis — {efecto}"
    falta = columnas_faltantes(df, efecto, ee)
    if falta:
        return Resultado.rechazo("meta_analisis", titulo, falta)
    if efecto == ee:
        return Resultado.rechazo("meta_analisis", titulo, "El efecto y su error estándar son "
                                                          "la misma columna.")
    filas, entrada = filas_completas(df, efecto, ee)
    try:
        e, s = filas[efecto].to_numpy(dtype=float), filas[ee].to_numpy(dtype=float)
    except (TypeError, ValueError):
        return Resultado.rechazo("meta_analisis", titulo, "El efecto y el error estándar "
                                                          "tienen que ser números.", entrada)
    if np.any(s <= 0):
        return Resultado.rechazo("meta_analisis", titulo,
                                 f"«{ee}» tiene errores estándar de 0 o negativos: cada estudio "
                                 "necesita el suyo, mayor que 0.", entrada)
    if len(e) < 2:
        return Resultado.rechazo("meta_analisis", titulo, "Hacen falta al menos 2 estudios.",
                                 entrada)
    r = meta_analysis(e, s, labels=[f"Fila {i + 1}" for i in filas.index],
                      model="fixed" if fijo else "random")
    falla = Resultado.rechazo_del_core("meta_analisis", titulo, r, entrada)
    if falla is not None:
        return falla
    valores = [Valor("Estudios (k)", r["k"]),
               Valor("Efecto combinado", r["effect"], ic=(r["ci_lower"], r["ci_upper"]),
                     nota=r["model"]),
               Valor("p (efecto = 0)", fmt_p(r["p"])),
               Valor("Q de Cochran", r["q"], nota=f"{r['df']} gl, {p_token(r['p_heterogeneity'])}"),
               Valor("I²", r["i2"], decimales=1, unidad="%")]
    if not fijo:
        valores.append(Valor("τ² (varianza entre estudios)", r["tau2"]))
        if r["prediccion"] is not None:
            valores.append(Valor("Intervalo de predicción 95 %",
                                 f"{num(r['prediccion'][0])} a {num(r['prediccion'][1])}",
                                 nota="dónde caería el efecto de un estudio nuevo"))
    i2 = r["i2"]
    nivel = "baja" if i2 < 25 else "moderada" if i2 < 75 else "alta"
    supuestos = [Supuesto(
        "¿Los estudios miden lo mismo (heterogeneidad)?",
        f"I² = {i2:.0f} %, Q con {p_token(r['p_heterogeneity'])}", f"Heterogeneidad {nivel}",
        ("Los estudios son parecidos entre sí: un solo efecto los resume bien." if i2 < 25 else
         "Parte de la variación entre estudios es real, no azar: el efecto combinado es un "
         "promedio, y el intervalo de predicción dice cuánto puede variar en otro contexto."
         + (" Con efectos fijos esa variación se ignora y el IC sale angosto de más." if fijo
            else "")), ok=i2 < 75,
        alternativa="con aleatorios, si se eligieron fijos." if fijo and i2 >= 25 else "")]
    eg = r["egger"]
    if eg is None:
        supuestos.append(Supuesto(
            "¿Hay efecto de estudios pequeños (sesgo de publicación)?",
            f"{r['k']} estudios", "Sin evaluar",
            "Egger no tiene poder con menos de 10 estudios (Sterne et al. 2011): mirá el funnel "
            "plot, pero sin sacar conclusiones fuertes.", ok=True))
    else:
        sesgo = eg["p"] < 0.10
        supuestos.append(Supuesto(
            "¿Hay efecto de estudios pequeños (sesgo de publicación)?",
            f"Egger: intercepto {num(eg['intercepto'])}, {p_token(eg['p'])} (se usa α = 0,10)",
            "Se detectó asimetría" if sesgo else "No se detectó asimetría",
            ("Los estudios chicos dan efectos distintos a los grandes: puede faltar publicar "
             "estudios chicos negativos, y el efecto combinado estar inflado." if sesgo else
             "El funnel plot es razonablemente simétrico."), ok=not sesgo))
    supuestos.append(Supuesto(
        "¿Los efectos están en la misma escala?", "lo supone el cálculo", "Se supone",
        "Diferencias de medias con diferencias de medias; los OR y RR, en logaritmo con su EE "
        "en logaritmo. Mezclar escalas da un número sin sentido."))
    return _armar(
        "meta_analisis", titulo, entrada, valores,
        Metodo("Efectos fijos (inverso de la varianza)" if fijo else
               "Efectos aleatorios (DerSimonian-Laird)",
               "Promedia los efectos de los estudios pesando cada uno por su precisión"
               + ("." if fijo else ", sumando la variación real entre estudios (τ²).")),
        supuestos,
        f"Efecto combinado {num(r['effect'])} (IC 95 % {num(r['ci_lower'])} a "
        f"{num(r['ci_upper'])}, {p_token(r['p'])}), heterogeneidad {nivel} (I² = {i2:.0f} %).",
        "Un meta-análisis no mejora a los estudios que junta: si comparten un sesgo, el "
        "combinado lo hereda con más precisión. Con logaritmos (OR, RR) el efecto y su IC se "
        "vuelven a la escala original con exp.",
        figuras=[Figura("Forest plot", lambda: _figura_forest(r)),
                 Figura("Funnel plot", lambda: _figura_funnel(r))],
        crudo={"meta": r})


def _figura_forest(r):
    import matplotlib.pyplot as plt

    k = r["k"]
    fig, ax = plt.subplots(figsize=(8, max(3, 0.45 * k + 1.5)))
    y = np.arange(k)[::-1] + 1
    tam = 30 + 170 * r["weights_pct"] / r["weights_pct"].max()
    ax.errorbar(r["effects"], y, xerr=1.96 * r["se_effects"], fmt='none', ecolor='#9ca3af',
                capsize=3)
    ax.scatter(r["effects"], y, s=tam, marker='s', color='#4f6ef7', zorder=3)
    ax.errorbar(r["effect"], 0, xerr=[[r["effect"] - r["ci_lower"]], [r["ci_upper"] - r["effect"]]],
                fmt='D', color='#ef4444', capsize=5, ms=8)
    if r["prediccion"] is not None:
        ax.hlines(-0.5, *r["prediccion"], color='#ef4444', lw=1, ls=':')
    ax.axvline(0, color='#d1d5e0', ls='--', lw=1)
    ax.set_yticks(list(y) + [0])
    ax.set_yticklabels(list(r["labels"]) + ["Combinado"])
    ax.set_xlabel("Efecto")
    ax.set_title("Forest plot (tamaño = peso)", fontweight='bold')
    fig.tight_layout()
    return fig


def _figura_funnel(r):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 5.5))
    se_max = r["se_effects"].max() * 1.1
    ax.scatter(r["effects"], r["se_effects"], color='#4f6ef7', zorder=3)
    grilla = np.linspace(0, se_max, 50)
    ax.plot(r["effect"] - 1.96 * grilla, grilla, color='#9ca3af', ls='--')
    ax.plot(r["effect"] + 1.96 * grilla, grilla, color='#9ca3af', ls='--')
    ax.axvline(r["effect"], color='#ef4444', lw=1.5)
    ax.set_ylim(se_max, 0)
    ax.set_xlabel("Efecto")
    ax.set_ylabel("Error estándar (arriba, los más precisos)")
    ax.set_title("Funnel plot", fontweight='bold')
    fig.tight_layout()
    return fig


# ============================================================
#  Mediciones seriales
# ============================================================

def mediciones_seriales(df, columnas, opciones=None) -> Resultado:
    """Una columna por tiempo, en orden; una fila por sujeto."""
    columnas = [columnas] if isinstance(columnas, str) else list(dict.fromkeys(columnas or []))
    titulo = "Mediciones seriales"
    falta = columnas_faltantes(df, *columnas)
    if falta:
        return Resultado.rechazo("mediciones_seriales", titulo, falta)
    if len(columnas) < 2:
        return Resultado.rechazo("mediciones_seriales", titulo,
                                 f"Hacen falta al menos 2 tiempos (columnas); hay {len(columnas)}.")
    sub = df[columnas]
    try:
        datos = sub.to_numpy(dtype=float)
    except (TypeError, ValueError):
        return Resultado.rechazo("mediciones_seriales", titulo,
                                 "Las columnas de los tiempos tienen que ser números.")
    datos = datos[np.any(np.isfinite(datos), axis=1)]
    entrada = Entrada(columnas=tuple(columnas), n=len(datos))
    r = serial_measurements_summary(datos)
    if r["n_con_pendiente"] < 2 or not np.isfinite(r["p_tendencia"]):
        return Resultado.rechazo("mediciones_seriales", titulo,
                                 "Hacen falta al menos 2 sujetos con 2 mediciones y pendientes "
                                 "distintas para probar si hay tendencia.", entrada)
    ic = r["ic_pendiente_media"]
    detecta = r["p_tendencia"] < 0.05
    valores = [Valor("Sujetos", r["n_subjects"]), Valor("Tiempos", r["n_timepoints"]),
               Valor("Pendiente media por sujeto", r["mean_slope"], ic=ic,
                     nota="cambio por intervalo entre tiempos"),
               Valor("DE de las pendientes", r["sd_slope"]),
               Valor("p (pendiente media = 0)", fmt_p(r["p_tendencia"]),
                     nota=f"t = {num(r['t_tendencia'])}, {r['n_con_pendiente'] - 1} gl")]
    valores += [Valor(f"Media — {c}", m, nota=f"DE {num(s)}, n = {k}")
                for c, m, s, k in zip(columnas, r["means"], r["sds"], r["n_por_tiempo"])]
    supuestos = [
        Supuesto("¿Hay tendencia en el tiempo?",
                 f"t sobre las {r['n_con_pendiente']} pendientes, {p_token(r['p_tendencia'])}",
                 "Se detectó tendencia" if detecta else "No se detectó tendencia",
                 ("Los sujetos cambian en promedio con el tiempo." if detecta else
                  "Con estos datos no se puede afirmar que cambien; tampoco descartarlo.")),
        Supuesto("¿Los tiempos están equiespaciados?",
                 f"se toman 0, 1, …, {r['n_timepoints'] - 1} en el orden elegido", "Se supone",
                 "Si los controles no son parejos (día 1, 2, 7, 30), la pendiente por «paso» no "
                 "es por unidad de tiempo: el signo vale, la magnitud no."),
        Supuesto("¿El cambio es más o menos lineal?", "una recta por sujeto", "Se supone",
                 "Si sube y después baja, la pendiente promedia las dos cosas y puede dar cero: "
                 "mirá las trayectorias. Otra medida resumen (el máximo, el área bajo la curva) "
                 "puede contestar mejor (Matthews et al. 1990)."),
    ]
    return _armar(
        "mediciones_seriales", titulo, entrada, valores,
        Metodo("Medidas resumen (Matthews et al. 1990)",
               "Cada sujeto se resume en su pendiente contra el tiempo; la tendencia se prueba "
               "con esas pendientes, una por sujeto, que sí son independientes."),
        supuestos,
        f"Pendiente media {num(r['mean_slope'])} por paso (IC 95 % {num(ic[0])} a {num(ic[1])}): "
        + ("se detectó tendencia." if detecta else "no se detectó tendencia."),
        "Ajustar una sola recta a todas las mediciones como si fueran independientes da p "
        "falsamente chicos: las de un mismo sujeto se parecen entre sí.",
        list(r.get("avisos", [])),
        [Figura("Trayectorias por sujeto", lambda: _figura_trayectorias(datos, r, columnas))],
        crudo={"seriales": r})


def _figura_trayectorias(datos, r, columnas):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5))
    t = np.arange(datos.shape[1])
    for fila in datos[:200]:
        ax.plot(t, fila, color='#9ca3af', lw=0.8, alpha=0.6)
    ax.plot(t, r["means"], color='#ef4444', lw=2.5, marker='o', label="Media por tiempo")
    ax.set_xticks(t)
    ax.set_xticklabels([str(c) for c in columnas])
    ax.set_ylabel("Valor")
    ax.set_title("Trayectorias por sujeto", fontweight='bold')
    ax.legend(framealpha=0.9)
    fig.tight_layout()
    return fig


# ============================================================
#  Pruebas diagnósticas
# ============================================================

def _tabla_diagnostica(analisis, titulo, df, prueba, verdad):
    t = tabla_2x2(df, prueba, verdad)
    if t.motivo:
        return None, Resultado.rechazo(analisis, titulo, t.motivo, t.entrada)
    return t, None


def _celdas(t) -> list[Valor]:
    return [Valor("Verdaderos positivos (a)", t.a, nota=f"{t.filas[0]} · {t.columnas[0]}"),
            Valor("Falsos positivos (b)", t.b, nota=f"{t.filas[0]} · {t.columnas[1]}"),
            Valor("Falsos negativos (c)", t.c, nota=f"{t.filas[1]} · {t.columnas[0]}"),
            Valor("Verdaderos negativos (d)", t.d, nota=f"{t.filas[1]} · {t.columnas[1]}")]


def _predictivos(sens, spec, prev):
    """VPP y VPN para una prevalencia dada (Bayes)."""
    vpp_den = sens * prev + (1 - spec) * (1 - prev)
    vpn_den = spec * (1 - prev) + (1 - sens) * prev
    return (sens * prev / vpp_den if vpp_den > 0 else np.nan,
            spec * (1 - prev) / vpn_den if vpn_den > 0 else np.nan)


def _escala_lr(lr, positiva) -> str:
    """Jaeschke, Guyatt y Sackett (1994)."""
    if not np.isfinite(lr):
        return "grande"
    x = lr if positiva else 1 / lr if lr > 0 else np.inf
    return ("grande" if x > 10 else "moderado" if x > 5 else "chico" if x > 2
            else "casi nulo")


def prueba_diagnostica(df, prueba, verdad, opciones=None) -> Resultado:
    """Variable 1 = resultado de la prueba; Variable 2 = el estándar de oro.

    `opciones["prevalencia"]`: la de la población donde se va a usar (None = la
    de la muestra).
    """
    opciones = opciones or {}
    titulo = f"Prueba diagnóstica — {prueba} contra {verdad}"
    t, rechazo = _tabla_diagnostica("prueba_diagnostica", titulo, df, prueba, verdad)
    if rechazo is not None:
        return rechazo
    r = diagnostic_test(*t.celdas)
    lr = likelihood_ratios(*t.celdas)
    valores = _celdas(t)
    for nombre, clave in (("Sensibilidad", "sens"), ("Especificidad", "spec"),
                          ("VPP (en la muestra)", "ppv"), ("VPN (en la muestra)", "npv"),
                          ("Exactitud", "acc"), ("Prevalencia en la muestra", "prev")):
        ic = r.get(f"ci_{clave}")
        valores.append(Valor(nombre, r[clave], decimales=4,
                             ic=ic if ic is not None and np.all(np.isfinite(ic)) else None,
                             nota="IC de Wilson" if clave in ("sens", "spec") else ""))
    valores += [Valor("LR+", lr["plr"] if np.isfinite(lr["plr"]) else "infinito", decimales=2,
                      ic=lr["ci_plr"]),
                Valor("LR−", lr["nlr"] if np.isfinite(lr["nlr"]) else "infinito", decimales=3,
                      ic=lr["ci_nlr"])]
    prev = opciones.get("prevalencia")
    if prev is not None and np.isfinite(r["sens"]) and np.isfinite(r["spec"]):
        vpp, vpn = _predictivos(r["sens"], r["spec"], prev)
        valores += [Valor(f"VPP con prevalencia {num(prev)}", vpp, decimales=3),
                    Valor(f"VPN con prevalencia {num(prev)}", vpn, decimales=3)]
    enfermos, sanos = t.a + t.c, t.b + t.d
    pocos = min(enfermos, sanos) < 30
    supuestos = [
        Supuesto("¿Hay enfermos y sanos suficientes?", f"{enfermos} enfermos, {sanos} sanos",
                 "No" if pocos else "Sí",
                 ("Con menos de 30 en un grupo el IC de la sensibilidad o la especificidad es "
                  "ancho: mirálo antes que el número." if pocos else
                  "Los IC de sensibilidad y especificidad tienen un ancho razonable."),
                 ok=not pocos),
        Supuesto("¿La prevalencia de la muestra es la de tu población?",
                 f"en la muestra, {num(r['prev'])}"
                 + (f"; se cargó {num(prev)}" if prev is not None else ""),
                 "Se recalculó" if prev is not None else "Se supone",
                 "La sensibilidad y la especificidad son de la prueba; el VPP y el VPN dependen "
                 "de cuántos enfermos hay. Con una prevalencia menor el VPP cae: cargá la de tu "
                 "población en el diálogo."),
        Supuesto("¿A todos se les hizo el estándar de oro?", "lo supone el cálculo", "Se supone",
                 "Si solo se confirmó a los positivos (sesgo de verificación), la sensibilidad "
                 "sale inflada y la especificidad baja (Bossuyt et al. 2015)."),
    ]
    return _armar(
        "prueba_diagnostica", titulo, t.entrada, valores,
        Metodo("Tabla 2×2 contra el estándar de oro, IC de Wilson",
               "Cuántos enfermos detecta la prueba (sensibilidad), cuántos sanos descarta "
               "(especificidad) y qué tan creíble es cada resultado (valores predictivos)."),
        supuestos,
        f"Sensibilidad {r['sens']:.3f} y especificidad {r['spec']:.3f}: un positivo multiplica "
        f"las chances de enfermedad por {num(lr['plr'])} y un negativo por {num(lr['nlr'])}.",
        "La sensibilidad y la especificidad se estimaron con el mismo punto de corte y en esta "
        "muestra: en pacientes con otra gravedad o espectro de enfermedad cambian.",
        list(t.avisos or []) + list(r.get("avisos", [])),
        [Figura("Sensibilidad, especificidad y valores predictivos",
                lambda: _figura_diag(r))],
        crudo={"diagnostico": r, "lr": lr, "tabla": t.celdas})


def razones_verosimilitud(df, prueba, verdad, opciones=None) -> Resultado:
    """Variable 1 = resultado de la prueba; Variable 2 = el estándar de oro.

    `opciones["pretest"]`: probabilidad pre-test (None = la prevalencia de la muestra).
    """
    opciones = opciones or {}
    titulo = f"Razones de verosimilitud — {prueba}"
    t, rechazo = _tabla_diagnostica("razones_verosimilitud", titulo, df, prueba, verdad)
    if rechazo is not None:
        return rechazo
    lr = likelihood_ratios(*t.celdas)
    a, b, c, d = t.celdas
    pre = opciones.get("pretest")
    de_muestra = pre is None
    if de_muestra:
        pre = (a + c) / (a + b + c + d)
    odds = pre / (1 - pre) if pre < 1 else np.inf

    def post(razon):
        o = odds * razon
        return o / (1 + o) if np.isfinite(o) else 1.0

    valores = [*_celdas(t),
               Valor("LR+", lr["plr"] if np.isfinite(lr["plr"]) else "infinito", decimales=2,
                     ic=lr["ci_plr"], nota=f"cambio {_escala_lr(lr['plr'], True)}"),
               Valor("LR−", lr["nlr"] if np.isfinite(lr["nlr"]) else "infinito", decimales=3,
                     ic=lr["ci_nlr"], nota=f"cambio {_escala_lr(lr['nlr'], False)}"),
               Valor("Probabilidad pre-test", pre, decimales=3,
                     nota="la prevalencia de la muestra" if de_muestra else "cargada"),
               Valor("Probabilidad si da positivo", post(lr["plr"]), decimales=3),
               Valor("Probabilidad si da negativo", post(lr["nlr"]), decimales=3)]
    supuestos = [
        Supuesto("¿Cuánto cambia la probabilidad un resultado?",
                 f"LR+ = {num(lr['plr'])}, LR− = {num(lr['nlr'])}",
                 f"Positivo: {_escala_lr(lr['plr'], True)}; negativo: "
                 f"{_escala_lr(lr['nlr'], False)}",
                 "LR+ > 10 o LR− < 0,1 cambian mucho la probabilidad; entre 2 y 5 (o 0,2 y 0,5), "
                 "poco; cerca de 1, nada (Jaeschke et al. 1994)."),
        Supuesto("¿De dónde sale la probabilidad pre-test?",
                 "la prevalencia de la muestra" if de_muestra else f"cargada: {num(pre)}",
                 "Se supone" if de_muestra else "Se cargó",
                 ("Con la prevalencia de la muestra, la probabilidad post-test positiva es el VPP "
                  "de la muestra. Para un paciente, cargá su probabilidad antes de la prueba."
                  if de_muestra else
                  "Es la probabilidad del paciente antes de la prueba; las razones de "
                  "verosimilitud no cambian con ella.")),
    ]
    return _armar(
        "razones_verosimilitud", titulo, t.entrada, valores,
        Metodo("Razones de verosimilitud con IC (Simel et al. 1991)",
               "Cuánto multiplica cada resultado las chances de enfermedad, sin depender de la "
               "prevalencia."),
        supuestos,
        f"Con probabilidad pre-test {num(pre)}, un positivo la lleva a {num(post(lr['plr']))} y "
        f"un negativo a {num(post(lr['nlr']))}.",
        "Las razones de verosimilitud suponen que la prueba rinde igual en el paciente que en "
        "la muestra del estudio: con otro espectro de enfermedad cambian.",
        list(t.avisos or []),
        crudo={"lr": lr, "pretest": pre})


def _figura_diag(r):
    import matplotlib.pyplot as plt

    nombres = ["Sensibilidad", "Especificidad", "VPP", "VPN"]
    claves = ["sens", "spec", "ppv", "npv"]
    fig, ax = plt.subplots(figsize=(7, 4))
    for i, (nombre, k) in enumerate(zip(nombres, claves)):
        v, ic = r[k], r.get(f"ci_{k}")
        if not np.isfinite(v):
            continue
        err = ([[v - ic[0]], [ic[1] - v]] if ic is not None and np.all(np.isfinite(ic)) else None)
        ax.errorbar(v, i, xerr=err, fmt='o', color='#4f6ef7', capsize=4, ms=7)
    ax.set_yticks(range(4))
    ax.set_yticklabels(nombres)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.02)
    ax.set_xlabel("Proporción (IC 95 % de Wilson)")
    ax.set_title("Desempeño de la prueba", fontweight='bold')
    fig.tight_layout()
    return fig
