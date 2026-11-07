"""Textos de los modos guía: pasos del asistente, lecciones de docencia y
explicaciones de cada prueba.

Las explicaciones de cada prueba se arman desde el catálogo del motor
(`omni_catalogo`: cuándo corre, para qué sirve, alternativa) y desde las
fórmulas (`omni_formulas`): hay una sola fuente de verdad por ensayo.
"""
from src.analysis.omni_catalogo import POR_ID
from src.analysis.omni_formulas import FORMULAS, ensayo_de_texto

# ------------------------------------------------------------------ glosario
GLOSARIO = {
    "Valor p": (
        "Si en realidad no hubiera ningún efecto, el p es la probabilidad de ver "
        "un resultado tan extremo como el tuyo (o más) solo por azar.",
        "p = 0,03: si no hubiera diferencia real, algo así aparecería por casualidad "
        "3 de cada 100 veces. Por eso se sospecha que la diferencia es real."),
    "Nivel de significación (α)": (
        "El límite que se fija ANTES de analizar para decidir. Lo habitual es 0,05.",
        "Si p < 0,05 se dice «estadísticamente significativo»."),
    "Hipótesis nula": (
        "La suposición de partida: «no hay diferencia» o «no hay relación». La prueba "
        "mide cuánto se contradicen tus datos con esa suposición.",
        "En una comparación de grupos: «los dos grupos tienen la misma media»."),
    "Normalidad (campana)": (
        "Que los valores se repartan con forma de campana: la mayoría cerca del centro "
        "y pocos en los extremos. Muchas pruebas la necesitan.",
        "La talla de adultos suele ser normal; los ingresos, no."),
    "Homocedasticidad": (
        "Que los grupos tengan una dispersión parecida entre sí.",
        "Si un grupo varía entre 90 y 110 y otro entre 50 y 200, no la cumplen."),
    "Paramétrica / no paramétrica": (
        "Las paramétricas usan medias y piden campana; las no paramétricas usan el "
        "orden de los valores y no la piden, a cambio de algo menos de potencia.",
        "t de Student (paramétrica) ↔ Mann-Whitney (no paramétrica)."),
    "Intervalo de confianza 95 %": (
        "El rango donde, con un método que acierta 95 de cada 100 veces, está el valor "
        "verdadero. Cuanto más angosto, más precisa la estimación.",
        "Media 100 [IC 95 %: 96 a 104]."),
    "Tamaño del efecto": (
        "CUÁNTO difieren o se relacionan las cosas, más allá de si es «significativo». "
        "Con muchos datos, una diferencia mínima puede dar p chico.",
        "Una diferencia de 0,5 mg/dL puede ser significativa y clínicamente irrelevante."),
    "Comparaciones múltiples": (
        "Al hacer muchas pruebas a la vez, alguna sale significativa por azar. Por eso "
        "se ajustan los p (por ejemplo, Bonferroni o Benjamini-Hochberg).",
        "Con 20 pruebas al 0,05, se espera en promedio 1 falso positivo."),
    "Sesgo (en comparación de métodos)": (
        "Cuánto se corre en promedio un método respecto del otro.",
        "El equipo nuevo da, en promedio, 2 mg/dL más que el de referencia."),
}

COMO_LEER_P = (
    "<b>Cómo leer el p:</b> si es <b>menor que 0,05</b>, el resultado sería raro si no "
    "hubiera efecto, así que se concluye que hay diferencia o relación. Si es <b>mayor</b>, "
    "no alcanza para afirmarlo, lo que <i>no</i> prueba que no haya: puede faltar tamaño "
    "de muestra. El p no dice cuán grande es el efecto."
)

# ------------------------------------------------------------------ lecciones por pestaña
LECCIONES = {
    "datos": (
        "La tabla es la base de todo",
        "<p>En estadística, cada <b>fila es un caso</b> (un paciente, una muestra) y cada "
        "<b>columna es una variable</b> (algo que se midió u observó).</p>"
        "<p>Las variables son de dos grandes familias:</p>"
        "<ul><li><b>Numéricas</b>: se miden con números que se pueden promediar (glucosa, "
        "edad).</li><li><b>Categóricas</b>: clasifican en grupos (sexo, tratamiento, "
        "sí/no).</li></ul>"
        "<p>El tipo de cada variable decide qué pruebas tienen sentido: el encabezado de "
        "cada columna te muestra cómo la ve BioStat.</p>"),
    "analisis": (
        "Elegir la prueba correcta",
        "<p>La prueba depende de tres preguntas:</p>"
        "<ol><li>¿Qué querés saber? (comparar, relacionar, describir)</li>"
        "<li>¿Qué tipo de variables tenés?</li>"
        "<li>¿Se cumplen los supuestos? (campana, dispersión pareja)</li></ol>"
        "<p>Si no estás seguro, el <b>Omnianálisis</b> se hace estas preguntas por vos y "
        "te muestra el camino que siguió.</p>"),
    "graficos": (
        "Mirar antes de calcular",
        "<p>Un gráfico muestra cosas que un número esconde: valores atípicos, "
        "asimetrías, grupos que se superponen.</p>"
        "<p><b>Histograma</b>: la forma de una variable. <b>Caja</b>: compara grupos. "
        "<b>Dispersión</b>: relación entre dos numéricas.</p>"),
    "omni": (
        "El árbol de decisión",
        "<p>El Omnianálisis hace lo que haría un estadístico: primero <b>describe</b> cada "
        "variable, después <b>verifica supuestos</b> y recién entonces elige la prueba.</p>"
        "<p>En la pestaña <b>Árbol</b>, cada caja es una decisión o una prueba. Verde = se "
        "ejecutó; gris = se descartó con un motivo. <b>Hacé click en una prueba</b> para ver "
        "su fórmula y cómo se calculó con tus datos.</p>"),
}


# ------------------------------------------------------------------ explicar una prueba
def explicar_ensayo(id_: str) -> dict:
    """Para qué sirve una prueba, cuándo se usa y qué la reemplaza."""
    ens = POR_ID.get(id_)
    form = FORMULAS.get(id_)
    alt = POR_ID.get(ens.alternativa) if ens and ens.alternativa else None
    return {
        "id": id_,
        "nombre": ens.nombre if ens else id_,
        "que": form.que if form else "",
        "para_que": ens.porque if ens else "",
        "cuando": ens.gatillo if ens else "",
        "alternativa": alt.nombre if alt else "",
        "norma": ens.norma if ens else "",
        "iterativo": bool(form and form.iterativo),
    }


def narrar_caso(caso) -> list[dict]:
    """El camino de un caso contado como una clase: qué se preguntó, por qué,
    qué dio y qué decidió."""
    salida = []
    for i, p in enumerate(caso.pasos, 1):
        id_ = ensayo_de_texto(p.medicion) or ensayo_de_texto(p.pregunta)
        salida.append({
            "n": i,
            "pregunta": p.pregunta,
            "medicion": p.medicion,
            "respuesta": p.respuesta,
            "consecuencia": p.consecuencia,
            "alternativa": p.alternativa,
            "ok": p.ok,
            "ensayo": explicar_ensayo(id_) if id_ else None,
        })
    return salida


# ------------------------------------------------------------------ pasos del asistente
def pasos_asistente(hay_datos: bool, diagnostico_listo: bool, analizado: bool,
                    pestana: str) -> list[dict]:
    """La lista de pasos con su estado: hecho, actual o pendiente."""
    pasos = [
        {"clave": "cargar", "titulo": "Cargá tus datos",
         "texto": "Importá un CSV o un Excel con los botones de la pestaña Datos, o probá "
                  "con un ejemplo. También podés escribir directo en la tabla.",
         "hecho": hay_datos, "resaltar": "importar", "pestana": 0},
        {"clave": "revisar", "titulo": "Revisá la forma de la tabla",
         "texto": "Una fila por caso y una columna por variable. Abajo te marco lo que "
                  "conviene corregir.",
         "hecho": hay_datos and diagnostico_listo, "resaltar": "tabla", "pestana": 0},
        {"clave": "elegir", "titulo": "Elegí las variables",
         "texto": "En Omnianálisis, tildá las columnas que querés estudiar. Si tenés una "
                  "variable que querés explicar, ponela como objetivo.",
         "hecho": analizado, "resaltar": "omni_variables", "pestana": 3},
        {"clave": "correr", "titulo": "Ejecutá el análisis",
         "texto": "El motor revisa supuestos y elige las pruebas solo.",
         "hecho": analizado, "resaltar": "omni_ejecutar", "pestana": 3},
        {"clave": "leer", "titulo": "Leé el resultado",
         "texto": "Empezá por el Resumen. En Árbol ves por qué eligió cada prueba y, con un "
                  "click, la fórmula con tus números.",
         "hecho": False, "resaltar": "omni_pestanas", "pestana": 3},
    ]
    actual_marcado = False
    for p in pasos:
        p["actual"] = (not p["hecho"]) and not actual_marcado
        actual_marcado = actual_marcado or p["actual"]
    return pasos
