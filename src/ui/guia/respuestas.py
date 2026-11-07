"""Respuestas en criollo para el modo Rueditas.

Corre el mismo motor que el Omnianálisis sobre las columnas elegidas, toma el
caso que responde la pregunta del usuario y lo traduce a: un semáforo, una
frase, qué quiere decir, qué NO quiere decir y qué hacer después.
"""
from dataclasses import dataclass, field

from src.analysis.omni_analyzer import run_omnianalysis
from src.analysis.omni_caso import caso_de_bloque
from src.ui.guia.ejemplos import OBJETIVOS

# verde = se encontró el efecto; ambar = no alcanza para afirmarlo;
# azul = respuesta descriptiva (no hay sí/no); gris = no se pudo responder.
COLORES = {"verde": "#16a34a", "ambar": "#d97706", "rojo": "#dc2626",
           "azul": "#2563eb", "gris": "#64748b"}

# Fuerza del CCC según la escala que ya usa el motor (McBride 2005).
_CONCORDANCIA = {
    "Casi perfecta": ("verde", "Los dos métodos dan resultados casi iguales."),
    "Sustancial": ("verde", "Los dos métodos dan resultados muy parecidos."),
    "Moderada": ("ambar", "Los dos métodos se parecen, pero no tanto."),
    "Pobre": ("rojo", "Los dos métodos dan resultados distintos."),
}


def _n(v, d=1):
    """Número legible con coma decimal."""
    try:
        return f"{float(v):.{d}f}".replace(".", ",")
    except (TypeError, ValueError):
        return str(v)


def _llano_describir(bloque):
    res = bloque.get("resultados", {})
    de = res.get("descriptivos") or {}
    normal = bool((res.get("normalidad") or {}).get("normal"))
    try:
        n = int(de.get("n"))
    except (TypeError, ValueError):
        n = "los"
    if normal:
        m, s = float(de["mean"]), float(de["std"])
        titular = f"En promedio, los valores rondan {_n(m)}."
        texto = (f"Tenés {n} valores. La mayoría (unos 2 de cada 3) está entre {_n(m - s)} "
                 f"y {_n(m + s)}. Tienen forma de campana, así que el promedio los "
                 f"representa bien.")
    else:
        titular = f"La mitad de los valores está por debajo de {_n(de['median'])}."
        texto = (f"Tenés {n} valores. La mitad del medio va de {_n(de['q25'])} a "
                 f"{_n(de['q75'])}. No tienen forma de campana, por eso uso el valor del "
                 f"medio (mediana) en vez del promedio, que se dejaría llevar por los extremos.")
    atipicos = res.get("outliers") or {}
    k = int(atipicos.get("n_leves", 0) or 0) + int(atipicos.get("n_extremos", 0) or 0)
    aviso = ([f"Hay {k} valor(es) muy alejado(s) del resto: revisá que no sean errores "
              f"de carga."] if k else [])
    return "azul", titular, texto, aviso


def _llano_metodos(bloque):
    res = bloque.get("resultados", {})
    fuerza = res.get("ccc_fuerza")
    color, titular = _CONCORDANCIA.get(fuerza, ("azul", "Así se comparan los dos métodos."))
    ori = res.get("orientacion") or {}
    ba = res.get("bland_altman") or {}
    x, y = ori.get("x", "el primero"), ori.get("y", "el segundo")
    texto = ""
    if "sesgo" in ba:
        sesgo = float(ba["sesgo"])
        unidad = " %" if ba.get("escala") == "porcentaje" else ""
        sentido = "más" if sesgo > 0 else "menos"
        texto = (f"En promedio, «{y}» da {_n(abs(sesgo), 2)}{unidad} {sentido} que «{x}». "
                 f"Para una muestra cualquiera, la diferencia suele quedar entre "
                 f"{_n(ba['loa_inferior'], 2)}{unidad} y {_n(ba['loa_superior'], 2)}{unidad}.")
    return color, titular, texto, []

_TITULARES = {
    "grupos": {"verde": "Sí: los grupos son distintos.",
               "ambar": "No se encontró diferencia entre los grupos."},
    "relacion": {"verde": "Sí: las dos medidas se mueven juntas.",
                 "ambar": "No se encontró relación entre las dos medidas."},
    "asociacion": {"verde": "Sí: las dos características van de la mano.",
                   "ambar": "No se encontró asociación entre las dos características."},
}
_EFECTO = {"grupos": "diferencia entre los grupos", "relacion": "relación",
           "asociacion": "asociación"}
_SIGUIENTE = {
    "grupos": {
        "verde": ["Mirá cuánto difieren (no solo si difieren): en el detalle está la "
                  "diferencia de medias o medianas.",
                  "Pensá si esa diferencia importa clínicamente, no solo estadísticamente."],
        "ambar": ["Si esperabas una diferencia, puede que falten casos: con más datos una "
                  "diferencia chica se vuelve detectable.",
                  "Revisá que cada caso esté en el grupo correcto."],
    },
    "relacion": {
        "verde": ["Relación no es causa: que suban juntas no prueba que una cause la otra.",
                  "Mirá el gráfico de dispersión para ver la forma de la relación."],
        "ambar": ["Puede haber una relación que no sea en línea recta: miralo en un gráfico.",
                  "Con pocos casos cuesta detectar relaciones débiles."],
    },
    "asociacion": {
        "verde": ["Mirá la tabla cruzada para ver en qué categoría se concentra.",
                  "Asociación no es causa: puede haber un tercer factor."],
        "ambar": ["Con grupos chicos cuesta detectar asociaciones: revisá cuántos casos hay "
                  "en cada combinación."],
    },
    "metodos": {
        "azul": ["Compará el sesgo y los límites de acuerdo con lo que tu laboratorio "
                 "acepta como error total.",
                 "En el detalle (Omnianálisis → Árbol) está el gráfico de Bland-Altman."],
    },
    "describir": {
        "azul": ["Mirá el histograma para ver la forma de los datos.",
                 "Si hay valores atípicos, revisá que no sean errores de carga."],
    },
}


@dataclass
class Respuesta:
    color: str
    titular: str
    explicacion: str = ""
    ojo: str = ""
    p_llano: str = ""
    siguiente: list = field(default_factory=list)
    advertencias: list = field(default_factory=list)
    caso: object = None
    columnas: list = field(default_factory=list)

    @property
    def color_hex(self) -> str:
        return COLORES[self.color]


def _p_en_palabras(p: float, clave: str) -> str:
    efecto = _EFECTO.get(clave, "efecto")
    if p < 0.001:
        veces = "menos de 1 vez cada 1000"
    elif p < 0.01:
        veces = f"unas {p * 1000:.0f} veces cada 1000"
    else:
        veces = f"unas {p * 100:.0f} veces cada 100"
    return (f"Si en realidad no hubiera {efecto}, un resultado así de marcado aparecería "
            f"por pura casualidad {veces}.")


def columnas_de(clave: str, eleccion: dict) -> list[str]:
    """Las columnas elegidas, en el orden de los roles del objetivo."""
    return [eleccion[r.clave] for r in OBJETIVOS[clave].roles]


def validar(df, clave: str, eleccion: dict) -> list[str]:
    """Problemas de la elección, en palabras. Vacío si está todo bien."""
    problemas = []
    obj = OBJETIVOS[clave]
    vistos = set()
    for rol in obj.roles:
        col = eleccion.get(rol.clave)
        if not col:
            problemas.append(f"Falta elegir: {rol.pregunta}")
            continue
        if col in vistos:
            problemas.append("Elegiste la misma columna dos veces.")
        vistos.add(col)
        if col not in df.columns:
            problemas.append(f"La columna «{col}» ya no está en la tabla.")
    return problemas


def responder(df, clave: str, eleccion: dict) -> Respuesta:
    obj = OBJETIVOS[clave]
    problemas = validar(df, clave, eleccion)
    if problemas:
        return Respuesta("gris", "Todavía no puedo responder.", explicacion=" ".join(problemas))

    cols = columnas_de(clave, eleccion)
    pares = [(cols[0], cols[1])] if clave == "metodos" else []
    refs = {(cols[0], cols[1]): cols[0]} if clave == "metodos" else None
    try:
        rep = run_omnianalysis(df, cols, confirmed_comparisons=pares, referencias=refs)
    except Exception as exc:  # noqa: BLE001 — se muestra, no se revienta
        return Respuesta("gris", "No se pudo hacer el cálculo.", explicacion=str(exc),
                         columnas=cols)
    if not isinstance(rep, dict) or "error" in rep:
        return Respuesta("gris", "No se pudo hacer el cálculo.",
                         explicacion=str((rep or {}).get("error", "")), columnas=cols)

    bloque = caso = None
    for b in rep.get("blocks", []) or []:
        c = caso_de_bloque(b)
        if c is not None and c.tipo == obj.tipo_caso:
            bloque, caso = b, c
            break
    if caso is None:
        avisos = [a for b in rep.get("blocks", []) or [] for a in b.get("advertencias", [])]
        return Respuesta("gris", "Con estas columnas no se puede responder esa pregunta.",
                         explicacion="Revisá que cada columna sea del tipo que se pide "
                                     "(números o categorías).",
                         advertencias=avisos[:3], columnas=cols)

    # La decisión es la del motor (`detectado`, con el p ya corregido si hubo
    # varias pruebas): Rueditas no decide por su cuenta.
    pruebas = bloque.get("pruebas") or []
    pr = pruebas[0] if pruebas else {}
    p = pr.get("p_adj", pr.get("p"))
    detectado = pr.get("detectado")
    if clave in _TITULARES:
        if p is None or detectado is None:
            color, titular = "gris", "No se pudo calcular si hay efecto."
        else:
            color = "verde" if detectado else "ambar"
            titular = _TITULARES[clave][color]
        explicacion, extra = caso.veredicto, []
    elif clave == "describir":
        color, titular, explicacion, extra = _llano_describir(bloque)
    elif clave == "metodos":
        color, titular, explicacion, extra = _llano_metodos(bloque)
    else:
        color, titular, explicacion, extra = "azul", (caso.veredicto or "Listo."), "", []

    siguiente = (_SIGUIENTE.get(clave, {}).get(color)
                 or _SIGUIENTE.get(clave, {}).get("azul", []))
    # Los avisos del motor están escritos para quien sabe estadística ("OLS es
    # inapropiado…"). En Rueditas van solo los propios, en criollo; los técnicos
    # siguen a mano en «Ver cómo lo calculé». Si no se pudo responder, sí se
    # muestran, porque explican por qué.
    tecnicos = list(caso.advertencias) if color == "gris" else []
    return Respuesta(
        color=color,
        titular=titular,
        explicacion=explicacion,
        ojo=caso.matiz,
        p_llano=_p_en_palabras(p, clave) if (p is not None and clave in _TITULARES) else "",
        siguiente=siguiente,
        advertencias=(extra + tecnicos)[:3],
        caso=caso,
        columnas=cols,
    )
