"""Cada análisis, contado como un caso que una persona puede seguir.

El árbol general dice *qué ensayos corrieron*. No dice qué dieron ni qué
significan, y agrega todo en un `×3` que esconde cuál columna fue cuál. Este
módulo hace lo contrario: toma un bloque del informe y lo reescribe como una
secuencia de preguntas con su respuesta, su número y su consecuencia.

La regla que ordena todo esto: **quien lee no sabe estadística y tiene que
poder confiar**. Confiar no es que le digan "significativo". Confiar es ver:

  1. la pregunta que se hizo, en castellano;
  2. con qué se la contestó y qué dio;
  3. qué decidió el motor por esa respuesta;
  4. **qué habría pasado si el número hubiera dado distinto** — sin eso, la
     decisión parece un veredicto en vez de una regla, y una regla es lo único
     que se puede auditar.

No parsea la prosa de la traza. Lee `resultados["supuestos"]` y `pruebas`, que
el motor deja estructurados: la prosa cambia con cualquier reescritura, un dict
no.
"""
from dataclasses import dataclass, field

from src.analysis.omni_analyzer import _fmt_p, _p

ALPHA = 0.05


# ============================================================
#  Lenguaje llano
# ============================================================
def probabilidad_en_palabras(p) -> str:
    """Traduce un p a una frase, sin la palabra 'significativo'.

    'Significativo' es el término que más se malentiende de toda la
    estadística: se lee como 'importante' o como 'probado'. Acá se dice qué
    mide el número y qué NO dice.
    """
    if p is None:
        return "No se pudo calcular la probabilidad."
    p = float(p)
    if p != p:
        return "No se pudo calcular la probabilidad."
    if p < 0.0001:
        veces = "menos de 1 de cada 10.000 veces"
    elif p < 0.001:
        veces = f"alrededor de {round(p * 10000)} de cada 10.000 veces"
    elif p < 0.01:
        veces = f"alrededor de {round(p * 1000)} de cada 1.000 veces"
    else:
        veces = f"alrededor de {round(p * 100)} de cada 100 veces"

    if p < ALPHA:
        return (
            f"Si en realidad no hubiera ninguna diferencia, un resultado así de "
            f"marcado aparecería {veces} solo por azar. Es lo bastante raro como "
            f"para tomar la diferencia en serio."
        )
    return (
        f"Aunque no hubiera ninguna diferencia real, un resultado así aparecería "
        f"{veces} solo por azar. No alcanza para afirmar que hay diferencia — "
        f"y ojo: tampoco prueba que no la haya. Puede faltar cantidad de datos."
    )


def _si_no(condicion: bool) -> str:
    return "Sí" if condicion else "No"


def _num(x, decimales=4) -> str:
    """Un número para mostrar.

    Los intervalos vienen del core como tuplas de `np.float64`, y su `repr` es
    `np.float64(1.23)`. Formateado a mano en vez de interpolar el objeto.
    """
    if x is None:
        return "—"
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    if v != v:
        return "—"
    return f"{v:.{decimales}g}"


def _ic(par) -> str:
    """Un intervalo de confianza como `1.23 a 4.56`."""
    if not par or len(par) != 2:
        return "—"
    return f"{_num(par[0])} a {_num(par[1])}"


def _normalidad_en_palabras(norm: dict) -> tuple[str, str]:
    """(respuesta, medición) para una prueba de normalidad."""
    if not norm:
        return ("No evaluable", "sin datos suficientes")
    if norm.get("p") is None:
        return (_si_no(norm.get("normal", True)),
                f"{norm.get('test', 'prueba')} — estadístico {norm.get('stat')}")
    return (_si_no(norm["normal"]),
            f"{norm['test']}: {_p(norm['p'])}")


# ============================================================
#  Estructuras
# ============================================================
@dataclass
class Paso:
    """Un nodo del camino, ya traducido."""
    pregunta: str        # en castellano, sin jerga
    medicion: str        # con qué se contestó y qué dio
    respuesta: str       # "Sí" / "No" / el valor
    consecuencia: str    # qué decidió el motor por eso
    alternativa: str = ""  # qué habría hecho si el número daba distinto
    ok: bool = True      # colorea el paso: verde si el supuesto se cumplió


@dataclass
class Caso:
    """Un análisis concreto, sobre columnas concretas."""
    titulo: str
    tipo: str
    pregunta: str                       # qué se quiso averiguar
    pasos: list[Paso] = field(default_factory=list)
    veredicto: str = ""                 # la respuesta, en una frase
    matiz: str = ""                     # qué NO prueba este resultado
    advertencias: list[str] = field(default_factory=list)

    @property
    def n_pasos(self) -> int:
        return len(self.pasos)


# ============================================================
#  Constructores por tipo de bloque
# ============================================================
def _caso_univariado_numerico(b: dict) -> Caso:
    res = b.get("resultados", {})
    d = res.get("descriptivos", {})
    norm = res.get("normalidad", {})
    nombre = b.get("titulo", "").replace("Univariado — ", "")

    caso = Caso(
        titulo=b.get("titulo", ""),
        tipo="Descripción de una variable",
        pregunta=f"¿Cómo se reparten los valores de {nombre}, y con qué número se resume?",
    )

    respuesta, medicion = _normalidad_en_palabras(norm)
    es_normal = bool(norm.get("normal"))
    caso.pasos.append(Paso(
        pregunta="¿Los valores se agrupan en forma de campana, simétricos alrededor del centro?",
        medicion=medicion,
        respuesta=respuesta,
        consecuencia=(
            "Como son simétricos, el promedio cae en el medio y describe bien al "
            "caso típico: se resume con media ± desvío."
            if es_normal else
            "Como están corridos hacia un lado, el promedio se va detrás de la "
            "cola y describe mal al caso típico: se resume con la mediana."
        ),
        alternativa=(
            "Si hubieran salido asimétricos, el resumen habría sido mediana + rango intercuartílico."
            if es_normal else
            "Si hubieran salido simétricos, el resumen habría sido media ± desvío."
        ),
        ok=es_normal,
    ))

    if res.get("tendencia_central"):
        caso.pasos.append(Paso(
            pregunta="¿Cuál es el valor típico?",
            medicion=str(res["tendencia_central"]),
            respuesta="—",
            consecuencia=f"Sobre {int(d.get('n') or 0)} dato(s) válido(s).",
        ))

    out = res.get("outliers")
    if out:
        n_raros = int(out.get("n_leves", 0)) + int(out.get("n_extremos", 0))
        lim = out.get("limites_internos")
        caso.pasos.append(Paso(
            pregunta="¿Hay valores que se despegan del resto?",
            medicion=(f"Se consideran despegados los que caen fuera de "
                      f"{lim[0]} a {lim[1]}" if lim else "regla de Tukey"),
            respuesta=f"{n_raros} valor(es)",
            consecuencia=(
                "No se borran: quedan señalados para que vos decidas si son un "
                "error de carga o un dato real."
                if n_raros else
                "Ninguno queda fuera del rango esperable."
            ),
            ok=(n_raros == 0),
        ))

    caso.veredicto = b.get("conclusion", "")
    caso.matiz = (
        "Esto describe los datos que cargaste. No dice si el método es correcto "
        "ni compara contra nada."
    )
    caso.advertencias = list(b.get("advertencias", []))
    return caso


def _caso_univariado_categorico(b: dict) -> Caso:
    res = b.get("resultados", {})
    freq = res.get("frecuencias", {})
    nombre = b.get("titulo", "").replace("Univariado — ", "")
    caso = Caso(
        titulo=b.get("titulo", ""),
        tipo="Descripción de una variable",
        pregunta=f"¿Cómo se reparten las categorías de {nombre}?",
    )
    if freq:
        detalle = "; ".join(f"{k}: {v['n']} ({v['%']}%)" for k, v in list(freq.items())[:6])
        caso.pasos.append(Paso(
            pregunta="¿Cuántos casos hay en cada categoría?",
            medicion=detalle,
            respuesta=f"{len(freq)} categoría(s)",
            consecuencia=(
                "Ojo con las categorías de muy pocos casos: son las que después "
                "hacen fallar las pruebas de asociación."
            ),
        ))
    if res.get("moda") is not None:
        caso.pasos.append(Paso(
            pregunta="¿Cuál es la categoría más frecuente?",
            medicion=str(res["moda"]),
            respuesta=str(res["moda"]),
            consecuencia="Es el resumen que tiene sentido cuando no hay orden numérico.",
        ))
    caso.veredicto = b.get("conclusion", "")
    caso.matiz = "Es un recuento. No compara grupos ni prueba ninguna hipótesis."
    caso.advertencias = list(b.get("advertencias", []))
    return caso


def _caso_correlacion(b: dict) -> Caso:
    res = b.get("resultados", {})
    sup = res.get("supuestos", {})
    pruebas = b.get("pruebas", [])
    pr = pruebas[0] if pruebas else {}
    par = b.get("titulo", "").replace("Bivariado — ", "")

    caso = Caso(
        titulo=b.get("titulo", ""),
        tipo="¿Se mueven juntas?",
        pregunta=f"Cuando una de las dos variables de {par} sube, ¿la otra tiende a subir también?",
    )

    ambas = bool(sup.get("ambas_normales"))
    detalles = []
    for col, norm in (sup.get("normalidad") or {}).items():
        resp, med = _normalidad_en_palabras(norm)
        detalles.append(f"{col}: {resp.lower()} ({med})")
    caso.pasos.append(Paso(
        pregunta="¿Las dos variables se reparten en forma de campana?",
        medicion="; ".join(detalles) or "no evaluable",
        respuesta=_si_no(ambas),
        consecuencia=(
            "Con las dos simétricas se puede usar Pearson, que mide si la "
            "relación sigue una línea recta."
            if ambas else
            "Como al menos una no lo es, se usa Spearman, que solo mira el orden "
            "de los valores: aguanta asimetría y valores despegados."
        ),
        alternativa=(
            "Si alguna no hubiera sido simétrica, se habría usado Spearman."
            if ambas else
            "Si las dos hubieran sido simétricas, se habría usado Pearson."
        ),
        ok=ambas,
    ))

    if pr:
        coef = pr.get("r", pr.get("rho"))
        p = pr.get("p")
        caso.pasos.append(Paso(
            pregunta="¿Cuánto se mueven juntas?",
            medicion=f"{pr.get('prueba')}: coeficiente = {coef}, {_p(p)}",
            respuesta=_fuerza_correlacion(coef),
            consecuencia=probabilidad_en_palabras(p),
            ok=bool(pr.get("significativo")),
        ))
        caso.veredicto = _veredicto_correlacion(par, coef, pr.get("significativo"))

    if pr and pr.get("significativo"):
        caso.matiz = (
            "Que dos cosas se muevan juntas no quiere decir que una cause la otra, "
            "ni que midan lo mismo. Para saber si dos métodos concuerdan hace falta "
            "el análisis de concordancia, no la correlación."
        )
    else:
        caso.matiz = (
            "No detectar asociación no prueba que no exista. Y al revés: aunque "
            "hubiera salido fuerte, correlación no es acuerdo ni es causa."
        )
    caso.advertencias = list(b.get("advertencias", []))
    return caso


def _fuerza_correlacion(coef) -> str:
    if coef is None:
        return "—"
    a = abs(float(coef))
    if a >= 0.9:
        etiqueta = "Muy fuerte"
    elif a >= 0.7:
        etiqueta = "Fuerte"
    elif a >= 0.4:
        etiqueta = "Moderada"
    elif a >= 0.2:
        etiqueta = "Débil"
    else:
        etiqueta = "Casi nula"
    sentido = "en el mismo sentido" if float(coef) >= 0 else "en sentido opuesto"
    return f"{etiqueta}, {sentido}"


def _veredicto_correlacion(par, coef, sig) -> str:
    if coef is None:
        return "No se pudo calcular la asociación."
    if sig:
        sentido = "sube" if float(coef) >= 0 else "baja"
        return (f"Las dos variables de {par} se mueven juntas: cuando una sube, "
                f"la otra {sentido} (coeficiente {coef}).")
    return (f"No hay evidencia de que las variables de {par} se muevan juntas "
            f"(coeficiente {coef}).")


def _caso_grupos(b: dict) -> Caso:
    res = b.get("resultados", {})
    sup = res.get("supuestos", {})
    pruebas = b.get("pruebas", [])
    pr = pruebas[0] if pruebas else {}
    par = b.get("titulo", "").replace("Bivariado — ", "")

    k = sup.get("k_grupos", 0)
    etiquetas = sup.get("etiquetas", [])
    tamanos = sup.get("tamanos", [])

    caso = Caso(
        titulo=b.get("titulo", ""),
        tipo="¿Los grupos difieren?",
        pregunta=f"En {par}, ¿los grupos tienen valores distintos, o la diferencia que se ve es azar?",
    )

    if etiquetas:
        caso.pasos.append(Paso(
            pregunta="¿Qué grupos se comparan, y con cuántos casos cada uno?",
            medicion="; ".join(f"{e}: n={n}" for e, n in zip(etiquetas, tamanos)),
            respuesta=f"{k} grupo(s)",
            consecuencia=(
                "Con 2 grupos se comparan de a uno; con 3 o más hace falta una "
                "prueba global primero, para no inflar los falsos positivos."
            ),
        ))

    todas_normales = bool(sup.get("todas_normales"))
    detalle_norm = "; ".join(
        f"{lab}: {'sí' if nn.get('normal') else 'no'} ({_p(nn.get('p'))})"
        for lab, nn in (sup.get("normalidad_por_grupo") or {}).items()
    )
    caso.pasos.append(Paso(
        pregunta="¿Los valores de cada grupo se reparten en forma de campana?",
        medicion=detalle_norm or "no evaluable",
        respuesta=_si_no(todas_normales),
        consecuencia=(
            "Habilita las pruebas que comparan promedios."
            if todas_normales else
            "Se usa una prueba que compara por orden de los valores, no por "
            "promedio: no exige campana."
        ),
        ok=todas_normales,
    ))

    lev = sup.get("levene") or {}
    if lev.get("p") is not None:
        iguales = bool(lev.get("equal_var"))
        caso.pasos.append(Paso(
            pregunta="¿Los grupos son igual de dispersos entre sí?",
            medicion=f"Prueba de Levene: {_p(lev['p'])}",
            respuesta=_si_no(iguales),
            consecuencia=(
                "Se puede usar la versión que asume dispersión pareja."
                if iguales else
                "Se corrige la prueba para que la dispersión distinta no falsee "
                "el resultado."
            ),
            ok=iguales,
        ))

    if pr:
        p = pr.get("p")
        caso.pasos.append(Paso(
            pregunta="¿La diferencia entre los grupos es más grande de lo que daría el azar?",
            medicion=f"{pr.get('prueba')}: {_p(p)}",
            respuesta=("Sí, la diferencia es real" if pr.get("significativo")
                       else "No alcanza para afirmarlo"),
            consecuencia=probabilidad_en_palabras(p),
            ok=bool(pr.get("significativo")),
        ))

    ph = res.get("posthoc")
    if ph and ph.get("comparaciones"):
        difieren = [c["par"] for c in ph["comparaciones"] if c.get("significativo")]
        caso.pasos.append(Paso(
            pregunta="¿Entre cuáles grupos, exactamente, está la diferencia?",
            medicion=f"{ph.get('metodo','post-hoc')}, {len(ph['comparaciones'])} par(es) comparado(s)",
            respuesta=("; ".join(difieren) if difieren else "En ninguno en particular"),
            consecuencia=(
                "La prueba global dice que alguien difiere; esto dice quién, "
                "corrigiendo por haber mirado varios pares a la vez."
            ),
            ok=bool(difieren),
        ))

    if pr:
        caso.veredicto = (
            f"Los grupos de {par} difieren." if pr.get("significativo")
            else f"No hay evidencia de que los grupos de {par} difieran."
        )
    # El matiz tiene que hablar del resultado que hubo, no del otro: advertir
    # "no confundas real con importante" cuando no se encontro diferencia
    # suena a que si la hubo, y es al reves.
    if pr and pr.get("significativo"):
        caso.matiz = (
            "Que la diferencia sea real no quiere decir que sea grande ni que "
            "importe clínicamente: eso se decide mirando cuánto difieren, no el p."
        )
    else:
        caso.matiz = (
            "No encontrar diferencia no es lo mismo que probar que no la hay. "
            "Con pocos casos por grupo, una diferencia real chica pasa "
            "desapercibida."
        )
    caso.advertencias = list(b.get("advertencias", []))
    return caso


def _caso_contingencia(b: dict) -> Caso:
    res = b.get("resultados", {})
    sup = res.get("supuestos", {})
    pruebas = b.get("pruebas", [])
    pr = pruebas[0] if pruebas else {}
    par = b.get("titulo", "").replace("Bivariado — ", "")

    caso = Caso(
        titulo=b.get("titulo", ""),
        tipo="¿Las categorías se asocian?",
        pregunta=f"En {par}, ¿pertenecer a una categoría cambia la probabilidad de caer en la otra?",
    )

    esperada = sup.get("esperada_minima")
    umbral = sup.get("umbral", 5)
    if esperada is not None:
        alcanza = esperada >= umbral
        caso.pasos.append(Paso(
            pregunta="¿Hay suficientes casos en cada casillero de la tabla?",
            medicion=(f"El casillero más flaco esperaría {esperada} caso(s); "
                      f"el mínimo para la prueba aproximada es {umbral}"),
            respuesta=_si_no(alcanza),
            consecuencia=(
                "Se puede usar chi-cuadrado, que aproxima."
                if alcanza else
                "Con casilleros tan flacos el chi-cuadrado miente: se calcula la "
                "probabilidad exacta en vez de aproximarla."
            ),
            ok=alcanza,
        ))

    if pr:
        p = pr.get("p")
        caso.pasos.append(Paso(
            pregunta="¿La asociación es más marcada de lo que daría el azar?",
            medicion=f"{pr.get('prueba')}: {_p(p)}",
            respuesta=("Sí" if pr.get("significativo") else "No alcanza para afirmarlo"),
            consecuencia=probabilidad_en_palabras(p),
            ok=bool(pr.get("significativo")),
        ))
        caso.veredicto = (
            f"Las categorías de {par} están asociadas." if pr.get("significativo")
            else f"No hay evidencia de asociación entre las categorías de {par}."
        )

    if pr and pr.get("significativo"):
        caso.matiz = "Asociación no es causa. Ninguna tabla de contingencia prueba causalidad."
    else:
        caso.matiz = ("No encontrar asociación no prueba que no la haya: con "
                      "tablas de pocos casos, una asociación real puede no "
                      "llegar a detectarse.")
    caso.advertencias = list(b.get("advertencias", []))
    return caso


def _caso_concordancia(b: dict) -> Caso:
    res = b.get("resultados", {})
    sup = res.get("supuestos", {})
    ba = res.get("bland_altman", {})
    reg = res.get("regresion", {})
    par = b.get("titulo", "").replace("Concordancia de métodos — ", "")

    caso = Caso(
        titulo=b.get("titulo", ""),
        tipo="¿Los dos métodos dan lo mismo?",
        pregunta=f"¿Se puede reemplazar un método por el otro en {par} sin cambiar la decisión clínica?",
    )

    proporcional = bool(sup.get("proporcional"))
    if sup.get("p_pendiente") is not None:
        caso.pasos.append(Paso(
            pregunta="¿El desacuerdo entre los métodos crece cuando sube la concentración?",
            medicion=(f"Pendiente de la diferencia contra el promedio = "
                      f"{sup.get('pendiente_diff_mean')}, {_p(sup.get('p_pendiente'))}"),
            respuesta=_si_no(proporcional),
            consecuencia=(
                "El desacuerdo se agranda en los valores altos: hay que mirarlo "
                "en porcentaje, no en unidades fijas."
                if proporcional else
                "El desacuerdo es parejo en todo el rango: se puede expresar en "
                "unidades absolutas."
            ),
            ok=not proporcional,
        ))

    norm_diff = sup.get("normalidad_diferencias") or {}
    diferencias_normales = bool(norm_diff.get("normal"))
    resp, med = _normalidad_en_palabras(norm_diff)
    caso.pasos.append(Paso(
        pregunta="¿Las diferencias entre los dos métodos se reparten en forma de campana?",
        medicion=med,
        respuesta=resp,
        consecuencia=(
            "Se pueden calcular los límites de acuerdo con la fórmula habitual."
            if diferencias_normales else
            "La fórmula habitual daría límites equivocados: se usan percentiles "
            "medidos directamente sobre los datos."
        ),
        alternativa=(
            "Si no hubieran sido simétricas, se habrían usado percentiles."
            if diferencias_normales else
            "Si hubieran sido simétricas, se habría usado la fórmula habitual."
        ),
        ok=diferencias_normales,
    ))
    # La prueba va sobre las DIFERENCIAS, no sobre los datos crudos. Es el error
    # clasico de Bland-Altman y conviene que se lea, no que se sobreentienda.
    caso.pasos[-1].medicion += "  (la prueba va sobre las diferencias, no sobre los valores de cada método)"

    sesgo = ba.get("sesgo", ba.get("sesgo_mediana"))
    lo = ba.get("loa_inferior", ba.get("loa_inferior_p2.5"))
    hi = ba.get("loa_superior", ba.get("loa_superior_p97.5"))
    if sesgo is not None:
        caso.pasos.append(Paso(
            pregunta="En promedio, ¿cuánto se separan los dos métodos?",
            medicion=(f"Sesgo = {_num(sesgo)}"
                      + (f"; entre {_num(lo)} y {_num(hi)} caen el 95% de las diferencias"
                         if lo is not None and hi is not None else "")),
            respuesta=_num(sesgo),
            consecuencia=(
                "Ese intervalo es lo que hay que mirar: dice cuánto puede llegar "
                "a diferir un resultado del otro en un paciente concreto. Si ese "
                "margen te cambia una conducta clínica, los métodos no son "
                "intercambiables — por más chico que sea el sesgo promedio."
            ),
        ))

    if reg:
        prop = reg.get("sesgo_proporcional")
        const = reg.get("sesgo_constante")
        concluyente, nota_ancho = _regresion_concluyente(reg)
        if not prop and not const and concluyente:
            consecuencia = (
                "El intervalo de la pendiente incluye el 1 y el del intercepto "
                "incluye el 0: no se detecta ni corrimiento ni error de escala."
            )
        elif not prop and not const:
            consecuencia = nota_ancho
        else:
            consecuencia = (
                "Se detecta desvío sistemático: apunta a recalibración, no a "
                "ruido de la medición."
            )
        # Paso 1 y este paso pueden discrepar: miden lo mismo con pruebas de
        # sensibilidad distinta. Si discrepan, decirlo — para el lector es una
        # contradiccion, y una contradiccion sin explicar destruye la confianza.
        if proporcional and not prop:
            consecuencia += (
                "  Ojo: el paso 1 sí detectó que el desacuerdo crece con la "
                "concentración. Las dos pruebas miran lo mismo, pero la de acá "
                "es menos sensible; con estos datos no llega a confirmarlo. "
                "Vale la del paso 1."
            )
        caso.pasos.append(Paso(
            pregunta="¿El desacuerdo es un corrimiento parejo o un error de escala?",
            medicion=(f"{reg.get('metodo')}: pendiente {_num(reg.get('pendiente'))} "
                      f"(IC 95% {_ic(reg.get('ic_pendiente'))}), "
                      f"intercepto {_num(reg.get('intercepto'))} "
                      f"(IC 95% {_ic(reg.get('ic_intercepto'))})"),
            respuesta=(
                ("error de escala" if prop else "")
                + (" y " if prop and const else "")
                + ("corrimiento parejo" if const else "")
            ) or ("ninguno de los dos" if concluyente else "no concluyente"),
            consecuencia=consecuencia,
            ok=(not prop and not const and concluyente),
        ))

    ccc = res.get("ccc")
    if ccc is not None:
        rho, cb = res.get("ccc_rho"), res.get("ccc_cb")
        caso.pasos.append(Paso(
            pregunta="En una sola cifra, ¿cuánto concuerdan?",
            medicion=(f"CCC de Lin = {ccc}"
                      + (f" — {res['ccc_fuerza']}" if res.get("ccc_fuerza") else "")
                      + (f"  (dispersión {rho} × veracidad {cb})"
                         if rho is not None and cb is not None else "")),
            respuesta=str(res.get("ccc_fuerza") or ccc),
            consecuencia=_donde_falla_ccc(rho, cb),
            ok=(float(ccc) >= 0.90),
        ))

    caso.veredicto = _veredicto_concordancia(par, ccc, sesgo, lo, hi)
    caso.matiz = (
        "El programa no sabe cuánta diferencia es tolerable para tu analito: eso "
        "lo pone el laboratorio, desde el requisito de calidad. Lo que sí dice es "
        "cuánto difieren, y con qué margen."
    )
    caso.advertencias = list(b.get("advertencias", []))
    return caso


def _regresion_concluyente(reg: dict) -> tuple[bool, str]:
    """¿El intervalo de la pendiente permite concluir algo?

    Un IC de pendiente que va de −3 a 5 **incluye el 1**, así que la regla
    mecánica dice "no hay sesgo proporcional". Es falso: con ese intervalo la
    regresión no puede descartar nada. Ausencia de evidencia no es evidencia de
    ausencia, y con pocos datos es la trampa más fácil de comer.

    Umbral: un IC de pendiente más ancho que 0,5 (o sea, ±25% alrededor del 1)
    ya no sirve para decidir si un método está bien calibrado.
    """
    ic = reg.get("ic_pendiente")
    if not ic or len(ic) != 2:
        return True, ""
    try:
        ancho = abs(float(ic[1]) - float(ic[0]))
    except (TypeError, ValueError):
        return True, ""
    if ancho <= 0.5:
        return True, ""
    return False, (
        f"Cuidado: el intervalo de la pendiente es muy ancho ({_ic(ic)}). "
        "Con estos datos la regresión no puede ni afirmar ni descartar un "
        "desvío — que no lo detecte NO significa que no exista. Para concluir "
        "algo hacen falta más muestras, o un rango de concentraciones más amplio."
    )


def _donde_falla_ccc(rho, cb) -> str:
    if rho is None or cb is None:
        return "Mide acuerdo, no correlación: penaliza estar corrido de la recta ideal."
    if cb < 0.95 and rho >= 0.95:
        return ("Los puntos siguen bien la línea pero están corridos: el problema "
                "es de calibración, no de ruido. Se arregla recalibrando.")
    if rho < 0.95 and cb >= 0.95:
        return ("Los puntos están centrados pero dispersos: el problema es de "
                "imprecisión de la medición, no de calibración.")
    if rho < 0.95 and cb < 0.95:
        return "Hay las dos cosas: dispersión y corrimiento."
    return "Los dos componentes están bien: ni corrimiento apreciable ni dispersión."


def _veredicto_concordancia(par, ccc, sesgo, lo, hi) -> str:
    if ccc is None:
        return f"No se pudo cerrar la comparación de {par}."
    margen = (f" Un resultado puede diferir del otro entre {_num(lo)} y {_num(hi)}."
              if lo is not None and hi is not None else "")
    sesgo = _num(sesgo)
    if float(ccc) >= 0.99:
        nivel = "Concordancia casi perfecta"
    elif float(ccc) >= 0.95:
        nivel = "Concordancia sustancial"
    elif float(ccc) >= 0.90:
        nivel = "Concordancia moderada"
    else:
        nivel = "Concordancia pobre"
    return (f"{nivel} entre los métodos de {par} (CCC = {ccc}), con un sesgo "
            f"promedio de {sesgo}.{margen} Si ese margen te cambia una conducta, "
            f"no son intercambiables.")


# ============================================================
#  Entrada
# ============================================================
_CONSTRUCTORES = {
    "correlación": _caso_correlacion,
    "comparación de grupos": _caso_grupos,
    "tabla de contingencia": _caso_contingencia,
    "concordancia": _caso_concordancia,
}


def caso_de_bloque(b: dict) -> Caso | None:
    """Traduce un bloque del informe a un caso. None si no hay nada que contar."""
    tipo = b.get("tipo", "")
    constructor = _CONSTRUCTORES.get(tipo)
    if constructor is not None:
        return constructor(b)
    # Univariado: el `tipo` del bloque es el tipo de la columna.
    if b.get("titulo", "").startswith("Univariado"):
        if "numérica" in tipo:
            return _caso_univariado_numerico(b)
        return _caso_univariado_categorico(b)
    return None


def casos(report: dict) -> list[Caso]:
    """Todos los casos del informe, en el orden en que corrieron."""
    if not isinstance(report, dict) or "error" in report:
        return []
    salida = []
    for b in report.get("blocks", []) or []:
        c = caso_de_bloque(b)
        if c is not None and c.pasos:
            salida.append(c)
    return salida
