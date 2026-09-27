"""Que variables pide cada analisis.

MedCalc no tiene un panel con tres combos siempre visibles: cada procedimiento
abre su propio cuadro de dialogo y ahi pide exactamente lo que necesita. Para
armar ese dialogo hace falta saber, por analisis, cuales de las tres variables
y el alfa entran en juego.

Esta tabla sale de leer el `dispatch` de `AnalysisPanel._run` — es la unica
fuente de verdad de que recibe cada rutina. `tests/test_analysis_specs.py`
vuelve a leer ese dispatch y compara: si alguien agrega un analisis o le cambia
los argumentos y no toca esta tabla, el test lo cachea.

Los analisis con tupla vacia no toman columnas sueltas: o eligen una LISTA de
columnas (ver MULTI: Friedman, Cronbach, medidas repetidas...), o piden sus datos
en campos propios (ver PARAMETROS: tamano de muestra), o leen una tabla ya
armada en la hoja (CMH, calculadoras). El dialogo se los dice al usuario en vez
de mostrarle selectores que no hacen nada.

Auditoria 2026-09 (K2, K3): la ANOVA, Kruskal-Wallis y las tablas 2x2 tomaban
columnas de la hoja sin preguntar — todas las numericas, o las dos primeras
filas como si fueran conteos — y devolvian basura sin avisar. Ahora usan las
variables elegidas.
"""

# analisis -> variables que consume, en orden: "c1", "c2", "c3", "alpha"
VARIABLES = {
    'Estadisticas descriptivas': ('c1',),
    't-test pareado': ('c1', 'c2', 'alpha'),
    't-test independiente': ('c1', 'c2', 'alpha'),
    'ANOVA una via': ('c1', 'c2', 'alpha'),
    'Correlacion de Pearson': ('c1', 'c2'),
    'Correlacion de Spearman': ('c1', 'c2'),
    'Shapiro-Wilk': ('c1',),
    'Curva ROC': ('c1', 'c3'),
    'Bland-Altman': ('c1', 'c2'),
    'Passing-Bablok': ('c1', 'c2'),
    'Kaplan-Meier': ('c1', 'c2'),
    'Log-rank test': ('c1', 'c2', 'c3'),
    'Meta-analisis': ('c1', 'c2'),
    'Tamano muestral (1 media)': (),
    'Tamano muestral (2 medias)': (),
    'Tamano muestral (2 proporciones)': (),
    'Poder estadistico': (),
    'Bootstrap (media)': ('c1',),
    'Bootstrap (diferencia)': ('c1', 'c2'),
    'Bootstrap (correlacion)': ('c1', 'c2'),
    'Random Forest (clasificacion)': ('c1',),
    'Random Forest (regresion)': ('c1',),
    'Mann-Whitney U': ('c1', 'c2'),
    'Wilcoxon pareado': ('c1', 'c2'),
    'Chi-cuadrado': ('c1', 'c2'),
    'Fisher exact': ('c1', 'c2'),
    'McNemar': ('c1', 'c2'),
    'Kruskal-Wallis': ('c1', 'c2'),
    'Friedman': (),
    'F-test (varianzas)': ('c1', 'c2'),
    'Kappa': ('c1', 'c2'),
    'ICC': ('c1', 'c2'),
    'Cronbach alfa': (),
    'Regresion lineal': ('c1', 'c2'),
    'Regresion multiple': ('c1',),
    'Regresion logistica': ('c1',),
    'Odds Ratio': ('c1', 'c2'),
    'Riesgo Relativo': ('c1', 'c2'),
    'Diagnostic test': ('c1', 'c2'),
    'Outliers (Grubbs)': ('c1',),
    'Outliers (Tukey)': ('c1',),
    'Intervalos de referencia': ('c1',),
    'Asimetria y curtosis': ('c1',),
    'Media recortada': ('c1',),
    'Correlacion parcial': ('c1', 'c2', 'c3'),
    'Media geometrica': ('c1',),
    'Media armonica': ('c1',),
    't-test 1 muestra': ('c1',),
    'ANOVA una via (core)': ('c1', 'c2', 'alpha'),
    'Sign test': ('c1', 'c2'),
    'Cochran Q': (),
    'Kappa ponderado': ('c1', 'c2'),
    'Deming regression': ('c1', 'c2'),
    'CV duplicatas': ('c1', 'c2'),
    'Likelihood Ratios': ('c1', 'c2'),
    'Comparar 2 medias': (),
    'Comparar 2 proporciones': (),
    'Comparar 2 AUC': (),
    'Tabla de percentiles': ('c1',),
    'Edad-relacionada': ('c1', 'c2'),
    'Outliers (ESD)': ('c1',),
    'Bootstrap (mediana)': ('c1',),
    'Bootstrap (regresion)': ('c1', 'c2'),
    'Tamaño muestral (correlacion)': ('c1', 'c2'),
    'ANOVA dos vias': ('c1', 'c2', 'c3'),
    'ANCOVA': ('c1', 'c2', 'c3'),
    'Medidas repetidas': (),
    'Cox regression': ('c1', 'c2'),
    'Probit regression': ('c1', 'c2'),
    'CMH test': ('c1', 'c2', 'c3'),
    'Mediciones seriales': (),
    'Youden plot': ('c1', 'c3'),
    'Polar plot': (),
    'Waterfall chart': ('c1',),
    'Mountain plot': ('c1', 'c2'),
    'Bland-Altman múltiple': ('c1',),
}


def variables(analisis):
    """Variables que pide un analisis. Tupla vacia = trabaja sobre toda la hoja."""
    return VARIABLES.get(analisis, ())


def usa(analisis, variable):
    return variable in VARIABLES.get(analisis, ())


def sobre_toda_la_hoja(analisis):
    """True si el analisis lee la hoja tal cual: sin columnas sueltas, sin lista
    de columnas elegidas y sin parametros propios (CMH, calculadoras)."""
    return (not [v for v in VARIABLES.get(analisis, ()) if v != "alpha"]
            and analisis not in MULTI and analisis not in PARAMETROS)


# ============================================================
#  Opciones de metodo (mas alla de que columnas usa)
# ============================================================
# Algunos analisis no solo piden variables: piden decidir COMO se calculan.
# Bland-Altman es el caso claro — el mismo par de columnas admite limites
# parametricos o no parametricos, y el eje X puede ser el promedio o el metodo
# de referencia. Esas decisiones no las puede tomar el programa solo: cual de
# los dos metodos es el de referencia es contexto que solo tiene la persona.
#
# La tabla es declarativa por la misma razon que VARIABLES: el dialogo la lee
# para armar los selectores, y `tests/test_analysis_specs.py` verifica que no
# se desincronice.
from dataclasses import dataclass


@dataclass(frozen=True)
class Opcion:
    """Una decision de metodo que el usuario toma antes de correr el analisis.

    clave:    como llega al panel (`self._opciones[clave]`).
    etiqueta: rotulo del selector.
    valores:  [(valor, texto)] — el primero es el que viene por defecto.
    ayuda:    una linea que explica que cambia, para el pie del selector.
    """
    clave: str
    etiqueta: str
    valores: tuple
    ayuda: str = ""

    @property
    def defecto(self):
        return self.valores[0][0]


OPCIONES = {
    'Bland-Altman': (
        Opcion(
            "limites", "Límites de acuerdo",
            (("auto", "Automático — según normalidad de las diferencias"),
             ("parametrico", "Paramétrico — sesgo ± 1,96·DE"),
             ("no_parametrico", "No paramétrico — percentiles 2,5 y 97,5")),
            "Los paramétricos exigen que las diferencias sean normales. "
            "En automático se verifica con Shapiro-Wilk y se elige solo.",
        ),
        Opcion(
            "referencia", "Eje X del gráfico",
            (("promedio", "Promedio de ambos métodos — Bland-Altman clásico"),
             ("x", "Variable 1 es el método de referencia — Krouwer"),
             ("y", "Variable 2 es el método de referencia — Krouwer")),
            "Si uno de los dos es método de referencia o valor asignado, "
            "graficar contra el promedio distorsiona la pendiente de las "
            "diferencias, y la resta pasa a ser método en prueba − referencia "
            "(Krouwer 2008; CLSI EP09c).",
        ),
        Opcion(
            "escala", "Escala de las diferencias",
            (("auto", "Automática — según cómo se abre la dispersión (EP09c §5.4)"),
             ("unidades", "Unidades del analito — DE constante"),
             ("porcentaje", "Porcentaje — CV constante")),
            "Si la dispersión de las diferencias crece con la concentración, "
            "en unidades un solo par de límites no sirve para todo el rango; "
            "en porcentaje sí (CLSI EP09c §5.4.2).",
        ),
    ),
}


def opciones(analisis):
    """Opciones de metodo de un analisis. Tupla vacia si no tiene."""
    return OPCIONES.get(analisis, ())


def opciones_por_defecto(analisis):
    """El dict que usa el panel cuando nadie eligio nada."""
    return {o.clave: o.defecto for o in OPCIONES.get(analisis, ())}


# ============================================================
#  Listas de columnas
# ============================================================
# Analisis que trabajan sobre VARIAS columnas elegidas a la vez (condiciones,
# items, tiempos, predictoras, metodos). En el dialogo se eligen tildando una
# lista; desde el panel, sin dialogo, se usan todas las columnas numericas y el
# informe las nombra una por una.
@dataclass(frozen=True)
class Multi:
    """`tildadas=False`: la lista arranca vacia. Para listas opcionales, donde
    tildar todo de entrada meteria columnas que no corresponden (las corridas de
    EP15 en el asistente de validacion)."""
    etiqueta: str
    minimo: int
    ayuda: str = ""
    tildadas: bool = True


MULTI = {
    "Friedman": Multi("Condiciones (una columna por condición)", 3,
                      "Cada fila es un sujeto medido en todas las condiciones."),
    "Cronbach alfa": Multi("Ítems de la escala", 2),
    "Cochran Q": Multi("Tratamientos (columnas 0/1)", 2,
                       "Cada fila es un sujeto; 1 = éxito, 0 = fracaso."),
    "Medidas repetidas": Multi("Tiempos (una columna por medición)", 2,
                               "Cada fila es un sujeto medido en todos los tiempos."),
    "Mediciones seriales": Multi("Tiempos, en orden", 2,
                                 "Se toman equiespaciados, en el orden de la lista."),
    "Regresion multiple": Multi("Predictoras", 1),
    "Regresion logistica": Multi("Predictoras", 1),
    "Random Forest (clasificacion)": Multi("Predictoras", 1),
    "Random Forest (regresion)": Multi("Predictoras", 1),
    "Bland-Altman múltiple": Multi("Métodos a comparar contra la referencia", 1,
                                   "La Variable 1 es el método de referencia."),
}


def multi(analisis):
    return MULTI.get(analisis)


# Rotulos propios de las variables, cuando «Variable 1» no dice que va ahi.
ETIQUETAS = {
    "Validar un método": {"c1": "Método en uso (comparativo)", "c2": "Método en prueba"},
}


def etiqueta(analisis, variable, defecto):
    return ETIQUETAS.get(analisis, {}).get(variable, defecto)


# ============================================================
#  Parametros numericos
# ============================================================
# Las calculadoras de tamano de muestra y poder no leen la hoja: piden numeros.
# Antes tenian los valores del ejemplo escritos en el codigo y el usuario no
# podia cambiarlos (auditoria 2026-09, K6).
@dataclass(frozen=True)
class Parametro:
    """Un numero que pide el dialogo. `defecto=None`: opcional, el campo arranca
    vacio y vacio quiere decir «no se declaro» (lo que declara un fabricante, un
    valor asignado)."""
    clave: str
    etiqueta: str
    defecto: float | None
    minimo: float = float("-inf")
    maximo: float = float("inf")
    entero: bool = False


_ALFA = Parametro("alpha", "Alfa (dos colas)", 0.05, 0.0001, 0.5)
_PODER = Parametro("poder", "Poder buscado", 0.80, 0.5, 0.999)

PARAMETROS = {
    "Tamano muestral (1 media)": (
        Parametro("delta", "Diferencia a detectar", 5.0),
        Parametro("sd", "DE esperada", 10.0, 1e-12), _ALFA, _PODER),
    "Tamano muestral (2 medias)": (
        Parametro("delta", "Diferencia entre medias a detectar", 5.0),
        Parametro("sd", "DE común esperada", 10.0, 1e-12),
        Parametro("ratio", "Razón n2/n1", 1.0, 0.01, 100), _ALFA, _PODER),
    "Tamano muestral (2 proporciones)": (
        Parametro("p1", "Proporción esperada, grupo 1", 0.30, 0.0001, 0.9999),
        Parametro("p2", "Proporción esperada, grupo 2", 0.50, 0.0001, 0.9999), _ALFA, _PODER),
    "Poder estadistico": (
        Parametro("n", "n (por grupo si son dos)", 100, 2, 10_000_000, entero=True),
        Parametro("delta", "Diferencia a detectar", 5.0),
        Parametro("sd", "DE esperada", 10.0, 1e-12), _ALFA),
}


def parametros(analisis):
    return PARAMETROS.get(analisis, ())


def parametros_por_defecto(analisis):
    return {p.clave: p.defecto for p in PARAMETROS.get(analisis, ())}


PARAMETROS["Deming regression"] = (
    Parametro("lambda", "λ = var. del error de Variable 1 / de Variable 2 (1 si no se conoce)",
              1.0, 1e-6, 1e6),
)

OPCIONES["Deming regression"] = (
    Opcion("tipo", "Ponderación",
           (("auto", "Automática — según cómo se abre la dispersión (EP09c §6.2)"),
            ("constante", "Sin ponderar — DE constante"),
            ("ponderado", "Ponderada — CV constante (EP09c, apéndice B)")),
           "Con CV constante, sin ponderar los puntos altos arrastran la recta."),
)

# EP15-A3: una columna por corrida (dia), las replicas en las filas. Lo
# declarado por el fabricante y el valor asignado son opcionales: sin ellos se
# estima la precision y no hay nada que verificar.
VARIABLES["Precisión EP15"] = ()
MULTI["Precisión EP15"] = Multi(
    "Corridas (una columna por día)", 2,
    "Cada columna es una corrida y sus filas, las réplicas de ese día. La norma pide "
    "5 corridas con 5 réplicas.")
PARAMETROS["Precisión EP15"] = (
    Parametro("sigma_r", "Repetibilidad declarada por el fabricante (vacío = no hay)",
              None, 0.0),
    Parametro("sigma_wl", "Intralaboratorio declarada por el fabricante (vacío = no hay)",
              None, 0.0),
    Parametro("n_muestras", "Materiales (niveles) en el estudio", 1, 1, 20, entero=True),
    Parametro("valor_asignado", "Valor asignado del material (vacío = no hay)", None),
    Parametro("u", "Incertidumbre del valor asignado (u, U o DE del grupo)", None, 0.0),
    Parametro("k", "Factor de cobertura k (si es U)", 2.0, 0.1, 10),
    Parametro("n_lab", "Laboratorios del grupo de pares", 0, 0, 100_000, entero=True),
)
OPCIONES["Precisión EP15"] = (
    Opcion("declaracion", "La declaración del fabricante viene como",
           (("de", "DE, en unidades del analito"),
            ("cv", "CV %")),
           "Se compara en la misma escala: DE con DE, CV con CV."),
    Opcion("incertidumbre", "Incertidumbre del valor asignado",
           (("ninguna", "No se conoce — control comercial o valor convencional (D, E)"),
            ("u", "Incertidumbre estándar u (material de referencia, A)"),
            ("U", "Incertidumbre expandida U, con su k (A)"),
            ("pares", "Grupo de pares: DE y número de laboratorios (B, C)")),
           "Escenarios de EP15-A3 §3.3. Solo cuenta si hay valor asignado."),
)

# El asistente B: EP09c + EP15-A3 en un veredicto (src/resultado/constructores/
# validacion.py). Sin sesgo permitido no hay veredicto; sin corridas, no hay
# precision. Los niveles vacios se reemplazan por los cuartiles del comparativo.
VARIABLES["Validar un método"] = ("c1", "c2")
MULTI["Validar un método"] = Multi(
    "Corridas de EP15 (opcional, una columna por día)", 0,
    "Para verificar además la precisión: 5 columnas con 5 réplicas de un control cada una.",
    tildadas=False)
PARAMETROS["Validar un método"] = (
    Parametro("sesgo_permitido", "Sesgo permitido (vacío = sin veredicto)", None, 0.0),
    Parametro("nivel_1", "Nivel de decisión 1 (vacío = cuartiles)", None),
    Parametro("nivel_2", "Nivel de decisión 2", None),
    Parametro("nivel_3", "Nivel de decisión 3", None),
    Parametro("lambda", "λ de Deming = var. del error del comparativo / del método en prueba",
              1.0, 1e-6, 1e6),
    Parametro("sigma_r", "Repetibilidad declarada (EP15; vacío = no hay)", None, 0.0),
    Parametro("sigma_wl", "Intralaboratorio declarada (EP15; vacío = no hay)", None, 0.0),
    Parametro("n_muestras", "Materiales en el estudio de precisión", 1, 1, 20, entero=True),
)
OPCIONES["Validar un método"] = (
    Opcion("escala_permitido", "El sesgo permitido viene en",
           (("porcentaje", "Porcentaje del nivel (p. ej., el deseable por variabilidad biológica)"),
            ("unidades", "Unidades del analito, igual en todos los niveles")),
           "En porcentaje, el permitido de cada nivel es ese % del nivel."),
    Opcion("declaracion", "La precisión declarada viene como",
           (("de", "DE, en unidades del analito"), ("cv", "CV %")),
           "Solo cuenta si se tildaron corridas de EP15."),
)

OPCIONES["Probit regression"] = (
    Opcion("escala", "Escala de la dosis (Variable 1)",
           (("lineal", "Lineal — la dosis tal como está"),
            ("log10", "Logarítmica (log10) — lo habitual en dosis-respuesta y en el LoD")),
           "En log10 la curva queda simétrica; las dosis efectivas se informan en la escala "
           "original."),
)

# t de una muestra: el valor de referencia lo pone el usuario (antes era 0 fijo).
PARAMETROS["t-test 1 muestra"] = (
    Parametro("mu", "Valor de referencia μ₀ (el valor asignado, el objetivo…)", 0.0),
)
# Medias resumidas: seis campos en vez de seis celdas de la primera columna.
PARAMETROS["Comparar 2 medias"] = (
    Parametro("m1", "Media del grupo 1", 5.2),
    Parametro("de1", "DE del grupo 1", 1.1, 0.0),
    Parametro("n1", "n del grupo 1", 30, 2, 10_000_000, entero=True),
    Parametro("m2", "Media del grupo 2", 4.6),
    Parametro("de2", "DE del grupo 2", 1.3, 0.0),
    Parametro("n2", "n del grupo 2", 28, 2, 10_000_000, entero=True),
)

PARAMETROS["Comparar 2 proporciones"] = (
    Parametro("x1", "Eventos del grupo 1", 24, 0, 10_000_000, entero=True),
    Parametro("n1", "Total del grupo 1", 80, 1, 10_000_000, entero=True),
    Parametro("x2", "Eventos del grupo 2", 12, 0, 10_000_000, entero=True),
    Parametro("n2", "Total del grupo 2", 75, 1, 10_000_000, entero=True),
)
ETIQUETAS["CMH test"] = {"c1": "Exposición", "c2": "Evento", "c3": "Estrato"}

OPCIONES["Kappa ponderado"] = (
    Opcion("pesos", "Pesos de los desacuerdos",
           (("linear", "Lineales — un salto de dos categorías pesa el doble"),
            ("quadratic", "Cuadráticos — pesa cuatro veces; cercano al ICC")),
           "Las categorías se ordenan de menor a mayor (numéricas) o alfabéticamente."),
)

OPCIONES["Poder estadistico"] = (
    Opcion("diseno", "Diseño",
           (("una", "Una muestra o datos pareados (t de una muestra)"),
            ("dos", "Dos grupos independientes (t de dos muestras)")),
           "Con dos grupos, n es el tamaño de CADA grupo."),
)
