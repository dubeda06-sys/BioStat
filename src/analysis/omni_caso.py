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
# El lenguaje llano vive en src/resultado/lenguaje.py, compartido con el panel
# manual: si cada lado tiene su copia, vuelven a divergir.
from src.resultado.lenguaje import (  # noqa: F401  (se re-exportan)
    ALPHA, donde_falla_ccc as _donde_falla_ccc, ic_texto as _ic, num as _num,
    pendiente_concluyente, probabilidad_en_palabras,
)


# ============================================================
#  Lenguaje llano
# ============================================================
def _si_no(condicion: bool) -> str:
    return "Sí" if condicion else "No"


def _p_de_la_prueba(pr: dict) -> str:
    """El p como se muestra: crudo, y corregido cuando la corrida hizo varias
    pruebas a la vez. Los dos a la vista: esconder el crudo haría parecer que
    el número cambió solo."""
    m = int(pr.get("n_familia") or 1)
    if m > 1 and pr.get("p_adj") is not None:
        return (f"{_p(pr.get('p'))} sin corregir; {_p(pr.get('p_adj'))} corregido por "
                f"las {m} pruebas de esta corrida")
    return _p(pr.get("p"))


def _consecuencia_del_p(pr: dict) -> str:
    """Qué significa el p con el que se decidió, y por qué es ese."""
    m = int(pr.get("n_familia") or 1)
    p = pr.get("p_adj") if pr.get("p_adj") is not None else pr.get("p")
    texto = probabilidad_en_palabras(p)
    if m > 1:
        texto += (f" Esta corrida hizo {m} pruebas a la vez, y con tantas alguna da un "
                  f"número chico por pura casualidad: por eso se decide con el p "
                  f"corregido y no con el crudo.")
    return texto


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
        caso.pasos.append(Paso(
            pregunta="¿Cuánto se mueven juntas?",
            medicion=f"{pr.get('prueba')}: coeficiente = {coef}, {_p_de_la_prueba(pr)}",
            respuesta=_fuerza_correlacion(coef),
            consecuencia=_consecuencia_del_p(pr),
            ok=bool(pr.get("detectado")),
        ))
        caso.veredicto = _veredicto_correlacion(par, coef, pr.get("detectado"))

    if pr and pr.get("detectado"):
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
            "Si además dispersan parejo, se compara por orden de los valores, "
            "que no exige campana. Si no, decide el paso siguiente."
        ),
        ok=todas_normales,
    ))

    lev = sup.get("levene") or {}
    if lev.get("p") is not None:
        iguales = bool(lev.get("equal_var"))
        if iguales:
            consecuencia = "Se puede usar la versión que asume dispersión pareja."
        elif todas_normales:
            consecuencia = ("Se usa la versión de Welch, que no supone dispersión pareja: "
                            "así la dispersión distinta no falsea el resultado.")
        else:
            consecuencia = ("Se usa la versión de Welch aunque no haya campana: la prueba "
                            "por orden reacciona cuando un grupo es más disperso que otro, "
                            "no solo cuando está corrido. Welch tolera la falta de campana; "
                            "con grupos chicos y muy asimétricos, el p es aproximado.")
        caso.pasos.append(Paso(
            pregunta="¿Los grupos son igual de dispersos entre sí?",
            medicion=f"Prueba de Levene: {_p(lev['p'])}",
            respuesta=_si_no(iguales),
            consecuencia=consecuencia,
            ok=iguales,
        ))

    if pr:
        caso.pasos.append(Paso(
            pregunta="¿La diferencia entre los grupos es más grande de lo que daría el azar?",
            medicion=f"{pr.get('prueba')}: {_p_de_la_prueba(pr)}",
            respuesta=("Sí, la diferencia es real" if pr.get("detectado")
                       else "No alcanza para afirmarlo"),
            consecuencia=_consecuencia_del_p(pr),
            ok=bool(pr.get("detectado")),
        ))

    ph = res.get("posthoc")
    if ph and ph.get("comparaciones"):
        difieren = [c["par"] for c in ph["comparaciones"] if c.get("detectado")]
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
            f"Los grupos de {par} difieren." if pr.get("detectado")
            else f"No hay evidencia de que los grupos de {par} difieran."
        )
    # El matiz tiene que hablar del resultado que hubo, no del otro: advertir
    # "no confundas real con importante" cuando no se encontro diferencia
    # suena a que si la hubo, y es al reves.
    if pr and pr.get("detectado"):
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
        forma = sup.get("forma") or (0, 0)
        if alcanza:
            consecuencia = "Se puede usar chi-cuadrado, que aproxima."
        elif sup.get("camino") == "fisher":
            consecuencia = ("Con casilleros tan flacos el chi-cuadrado miente. Como la "
                            "tabla es de 2×2, se calcula la probabilidad exacta en vez de "
                            "aproximarla.")
        else:
            # La tabla es más grande que 2×2: no hay probabilidad exacta a mano.
            # Decir "exacta" acá y mostrar un chi-cuadrado en el paso siguiente
            # era la contradicción que marcó la auditoría (A8).
            consecuencia = (f"Con casilleros tan flacos el chi-cuadrado miente, y la "
                            f"probabilidad exacta es para tablas de 2×2. Esta es de "
                            f"{forma[0]}×{forma[1]}: el p se calcula armando "
                            f"{sup.get('simulaciones', 9999)} tablas al azar con los "
                            f"mismos totales y viendo cuántas salen tan desparejas "
                            f"como la real.")
        caso.pasos.append(Paso(
            pregunta="¿Hay suficientes casos en cada casillero de la tabla?",
            medicion=(f"El casillero más flaco esperaría {esperada} caso(s); "
                      f"el mínimo para la prueba aproximada es {umbral}"),
            respuesta=_si_no(alcanza),
            consecuencia=consecuencia,
            ok=alcanza,
        ))

    if pr:
        caso.pasos.append(Paso(
            pregunta="¿La asociación es más marcada de lo que daría el azar?",
            medicion=f"{pr.get('prueba')}: {_p_de_la_prueba(pr)}",
            respuesta=("Sí" if pr.get("detectado") else "No alcanza para afirmarlo"),
            consecuencia=_consecuencia_del_p(pr),
            ok=bool(pr.get("detectado")),
        ))
        caso.veredicto = (
            f"Las categorías de {par} están asociadas." if pr.get("detectado")
            else f"No hay evidencia de asociación entre las categorías de {par}."
        )

    if pr and pr.get("detectado"):
        caso.matiz = "Asociación no es causa. Ninguna tabla de contingencia prueba causalidad."
    else:
        caso.matiz = ("No encontrar asociación no prueba que no la haya: con "
                      "tablas de pocos casos, una asociación real puede no "
                      "llegar a detectarse.")
    caso.advertencias = list(b.get("advertencias", []))
    return caso


_VARIABILIDAD_EN_PALABRAS = {
    "DE constante": (
        "Pareja",
        "El margen de desacuerdo es el mismo en valores bajos y altos: se expresa "
        "en unidades del analito.",
        "Si se hubiera abierto con la concentración, se habría expresado en "
        "porcentaje.",
    ),
    "CV constante": (
        "Crece con la concentración",
        "El margen se agranda en los valores altos pero se mantiene parejo en "
        "porcentaje: se expresa en %, y la recta pesa menos los puntos altos, que "
        "son los más ruidosos.",
        "Si hubiera sido pareja, se habría expresado en unidades del analito.",
    ),
    "mixta": (
        "Ni pareja ni proporcional",
        "No hay una sola escala que sirva para todo el rango: se usa una recta que "
        "no supone nada sobre la dispersión, y conviene mirar el gráfico por tramos "
        "de concentración.",
        "Si hubiera sido pareja o proporcional, se habría podido resumir con un "
        "solo margen, en unidades o en porcentaje.",
    ),
}


def _caso_concordancia(b: dict) -> Caso:
    res = b.get("resultados", {})
    sup = res.get("supuestos", {})
    ba = res.get("bland_altman", {})
    reg = res.get("regresion", {})
    orient = res.get("orientacion") or {}
    par = b.get("titulo", "").replace("Concordancia de métodos — ", "")
    nx, ny = orient.get("x", "X"), orient.get("y", "Y")
    en_pct = ba.get("escala") == "porcentaje"
    u = " %" if en_pct else ""

    caso = Caso(
        titulo=b.get("titulo", ""),
        tipo="¿Los dos métodos dan lo mismo?",
        pregunta=f"¿Se puede reemplazar un método por el otro en {par} sin cambiar la decisión clínica?",
    )

    # Paso de la tendencia del sesgo. Se guarda su número: el paso de la recta
    # lo nombra si las dos lecturas no coinciden.
    proporcional = bool(sup.get("proporcional"))
    paso_tendencia = None
    if sup.get("p_pendiente") is not None:
        caso.pasos.append(Paso(
            pregunta="¿El desacuerdo entre los métodos crece cuando sube la concentración?",
            medicion=(f"Pendiente de la diferencia{u} contra "
                      f"{sup.get('eje_estructura', 'el promedio')} = "
                      f"{sup.get('pendiente_estructura')}, {_p(sup.get('p_pendiente'))}"),
            respuesta=_si_no(proporcional),
            consecuencia=(
                "El sesgo no es el mismo en todo el rango: un solo sesgo promedio no "
                "lo resume, hay que mirarlo en los niveles donde se decide."
                if proporcional else
                "El sesgo es parejo en todo el rango: el sesgo promedio lo resume bien."
            ),
            ok=not proporcional,
        ))
        paso_tendencia = len(caso.pasos)

    var = sup.get("variabilidad") or {}
    clase = var.get("clase")
    if clase in _VARIABILIDAD_EN_PALABRAS:
        respuesta, consecuencia, alternativa = _VARIABILIDAD_EN_PALABRAS[clase]
        caso.pasos.append(Paso(
            pregunta=("¿La dispersión entre los dos métodos es pareja en todo el rango, o "
                      "se abre cuando sube la concentración?"),
            medicion=(f"Tamaño de las diferencias contra "
                      f"{sup.get('eje_estructura', 'el promedio')}: {_p(var.get('p_de'))} "
                      f"en unidades"
                      + (f", {_p(var.get('p_cv'))} en porcentaje"
                         if var.get("p_cv") is not None else "")),
            respuesta=respuesta,
            consecuencia=consecuencia,
            alternativa=alternativa,
            ok=(clase != "mixta"),
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
    caso.pasos[-1].medicion += ("  (la prueba va sobre las diferencias"
                                + (" en porcentaje" if en_pct else "")
                                + ", no sobre los valores de cada método)")

    sesgo = ba.get("sesgo", ba.get("sesgo_mediana"))
    lo = ba.get("loa_inferior", ba.get("loa_inferior_p2.5"))
    hi = ba.get("loa_superior", ba.get("loa_superior_p97.5"))
    if sesgo is not None:
        caso.pasos.append(Paso(
            pregunta="En promedio, ¿cuánto se separan los dos métodos?",
            medicion=(f"Sesgo ({ny} − {nx}) = {_num(sesgo)}{u}"
                      + (f"; entre {_num(lo)}{u} y {_num(hi)}{u} caen el 95% de las diferencias"
                         if lo is not None and hi is not None else "")),
            respuesta=f"{_num(sesgo)}{u}",
            consecuencia=(
                ("Está en porcentaje del valor, porque el margen crece con la "
                 "concentración. " if en_pct else "")
                + "Ese intervalo es lo que hay que mirar: dice cuánto puede llegar "
                "a diferir un resultado del otro en un paciente concreto. Si ese "
                "margen te cambia una conducta clínica, los métodos no son "
                "intercambiables — por más chico que sea el sesgo promedio."
            ),
        ))

    # Solo cuando se declaro una referencia. Sin declararla el eje es el
    # promedio y no hay nada que contrastar: eso queda en la auditoria como
    # descartado con su motivo, no hace falta un paso en cada caso.
    if ba.get("pendiente_vs_referencia") is not None:
        p_ref = ba.get("pendiente_vs_referencia")
        p_prom = ba.get("pendiente_vs_promedio")
        nombre_ref = str(ba.get("eje_x", "")).replace(" (método de referencia)", "")
        cambia = bool(ba.get("cambia_la_conclusion"))
        # El promedio falla en las dos direcciones y hay que decir cual, porque
        # el numero esta a la vista: si achica, tapa un desvio real; si agranda,
        # inventa uno. Describir siempre la primera contradice la medicion que
        # el propio paso muestra al lado.
        achica = bool(ba.get("promedio_atenua"))
        desvio_por_el_promedio = (
            (f"Contra el promedio el desvío queda más cerca de cero "
             f"({_num(p_prom)} en vez de {_num(p_ref)}) y la lectura se da "
             f"vuelta: por ese camino el problema no aparecía. Pasa porque el "
             f"promedio lleva adentro a la referencia, y eso le saca fuerza al "
             f"desvío.")
            if achica else
            (f"Contra el promedio aparece un desvío más grande ({_num(p_prom)} "
             f"en vez de {_num(p_ref)}) que contra la referencia no está: la "
             f"lectura se da vuelta, y hacia un problema inventado. Pasa porque "
             f"el promedio lleva adentro al método que estás probando, así que "
             f"su ruido queda de los dos lados de la cuenta y se hace pasar por "
             f"un desvío.")
        )
        caso.pasos.append(Paso(
            pregunta="¿Contra qué se midió el desvío: contra el promedio de los dos o contra el método bueno?",
            medicion=(f"Pendiente contra {nombre_ref} = {_num(p_ref)}; "
                      f"contra el promedio de ambos = {_num(p_prom)}"),
            respuesta=f"Contra {nombre_ref}",
            consecuencia=(
                (f"Dijiste que {nombre_ref} es el método de referencia, así que el "
                 f"desvío se midió contra ella — y menos mal. "
                 + desvio_por_el_promedio)
                if cambia else
                (f"Dijiste que {nombre_ref} es el método de referencia, así que el "
                 f"desvío se midió contra ella, que es lo que corresponde. Acá las "
                 f"dos formas llevan a la misma lectura, así que en este caso la "
                 f"elección del eje no te cambia nada.")
            ),
            alternativa=("Si ninguno de los dos fuera referencia — dos métodos "
                         "nuevos, sin uno que valga como verdad — correspondería "
                         "el promedio, que es el Bland-Altman clásico."),
            ok=not cambia,
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
        # El paso de la tendencia y este pueden discrepar: miran lo mismo por
        # caminos distintos. Si discrepan se dice, y sin darle la razón a
        # ninguno: la pendiente de las diferencias se deja engañar cuando un
        # método es más impreciso que el otro, cov(d, m) = (σ²ₐ − σ²_b)/2
        # (Bland y Altman 1999), y la recta depende del cociente de
        # imprecisiones que se le supone. "Vale la del paso 1" no tenía base
        # (auditoría 2026-09, A16).
        if paso_tendencia and proporcional != bool(prop):
            vio = "sí vio" if proporcional else "no vio"
            confirma = "no lo confirma" if proporcional else "sí lo ve"
            consecuencia += (
                f"  Ojo: el paso {paso_tendencia} {vio} que el desacuerdo cambia con la "
                f"concentración y esta recta {confirma}. Las dos miran lo mismo por "
                f"caminos distintos y ninguna manda sobre la otra: la del paso "
                f"{paso_tendencia} se deja engañar cuando un método es más impreciso "
                f"que el otro, y esta depende de suponer bien cuánto error tiene cada "
                f"método. Con estos datos, un error de escala no se puede afirmar ni "
                f"descartar."
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
        # La Cusum de Passing y Bablok (1983) dice si la recta de arriba se puede
        # leer: con la relación curva, pendiente e intercepto promedian tramos
        # que se comportan distinto. Mismo texto que el panel (_paso_cusum).
        if reg.get("cusum_p") is not None:
            curva = reg["cusum_p"] < 0.05
            caso.pasos.append(Paso(
                pregunta="¿La relación entre los dos métodos es una recta en todo el rango?",
                medicion=f"Cusum de linealidad: H = {_num(reg.get('cusum_h'))}, "
                         f"{_p(reg['cusum_p'])}",
                respuesta="No: se detectó desvío" if curva else "Sí, no se detectó desvío",
                consecuencia=(
                    "Los residuos de un mismo signo se agrupan a lo largo de la recta en "
                    "vez de alternarse: la relación es curva, y la pendiente y el "
                    "intercepto del paso anterior no se deben leer. Conviene comparar por "
                    "tramos de concentración. La prueba es algo liberal: un p apenas "
                    "debajo de 0,05 es evidencia débil."
                    if curva else
                    "Los residuos se alternan a los dos lados de la recta sin agruparse: "
                    "la recta del paso anterior es aplicable."),
                alternativa=("si los residuos se agruparan (arriba en los extremos y abajo "
                             "en el medio, o al revés), la relación sería curva."
                             if not curva else
                             "si se alternaran al azar, la recta sería aplicable."),
                ok=not curva,
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

    caso.veredicto = _veredicto_concordancia(par, ccc, sesgo, lo, hi, u)
    caso.matiz = (
        "El programa no sabe cuánta diferencia es tolerable para tu analito: eso "
        "lo pone el laboratorio, desde el requisito de calidad. Lo que sí dice es "
        "cuánto difieren, y con qué margen."
    )
    caso.advertencias = list(b.get("advertencias", []))
    return caso


def _regresion_concluyente(reg: dict) -> tuple[bool, str]:
    """¿El intervalo de la pendiente permite concluir algo? Ver
    `lenguaje.pendiente_concluyente`: un IC que incluye el 1 no prueba nada si
    es demasiado ancho."""
    return pendiente_concluyente(reg.get("ic_pendiente"))


def _veredicto_concordancia(par, ccc, sesgo, lo, hi, u="") -> str:
    if ccc is None:
        return f"No se pudo cerrar la comparación de {par}."
    margen = (f" Un resultado puede diferir del otro entre {_num(lo)}{u} y {_num(hi)}{u}."
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
            f"promedio de {sesgo}{u}.{margen} Si ese margen te cambia una conducta, "
            f"no son intercambiables.")


# ============================================================
#  Entrada
# ============================================================
def _caso_serie(b: dict) -> Caso:
    res = b.get("resultados", {})
    se = res.get("serie") or {}
    pruebas = b.get("pruebas", [])
    pr = pruebas[0] if pruebas else {}
    par = b.get("titulo", "").replace("Bivariado — ", "")
    caso = Caso(
        titulo=b.get("titulo", ""),
        tipo="¿Cambia con el tiempo?",
        pregunta=f"En {par}, ¿los valores suben o bajan con el tiempo, o varían al azar?",
    )
    if not se:
        return caso
    caso.pasos.append(Paso(
        pregunta="¿Cuántas mediciones hay, y en qué período?",
        medicion=f"{se['n']} puntos, {se['desde']} a {se['hasta']}",
        respuesta=f"{se['dias']:.0f} días",
        consecuencia=("Se ordenan por fecha: en una serie importa el orden, no solo "
                      "los valores."),
    ))
    ac = se.get("autocorrelacion")
    if ac:
        rachas = ac["p"] < 0.05
        caso.pasos.append(Paso(
            pregunta="¿Cada valor se parece al anterior más de lo que daría el azar?",
            medicion=f"Ljung-Box ({ac['rezagos']} rezago(s)): {_p(ac['p'])}; r₁={ac['r1']}",
            respuesta="Sí, vienen en rachas" if rachas else "No se detecta",
            consecuencia=("La prueba de tendencia supone mediciones independientes: con "
                          "rachas su p sale demasiado chico, y una racha se puede leer "
                          "como tendencia." if rachas else
                          "La prueba de tendencia puede tomar cada punto como "
                          "independiente."),
            ok=not rachas,
        ))
    if pr:
        lo, hi = se["ic95_dia"]
        caso.pasos.append(Paso(
            pregunta="¿Hay una tendencia más grande de lo que daría el azar?",
            medicion=f"Mann-Kendall: {_p_de_la_prueba(pr)}",
            respuesta=("Sí, hay tendencia" if pr.get("detectado")
                       else "No alcanza para afirmarlo"),
            consecuencia=(f"Cambia {se['pendiente_sen_dia']:.3g} por día según la "
                          f"pendiente de Sen (IC 95 %: {lo:.3g} a {hi:.3g}); en todo "
                          f"el período, {se['cambio_en_el_periodo']:.3g}. "
                          + _consecuencia_del_p(pr)),
            ok=bool(pr.get("detectado")),
        ))
    return caso


_CONSTRUCTORES = {
    "serie temporal": _caso_serie,
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
