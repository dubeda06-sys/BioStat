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
    'CMH test': (),
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
    etiqueta: str
    minimo: int
    ayuda: str = ""


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


# ============================================================
#  Parametros numericos
# ============================================================
# Las calculadoras de tamano de muestra y poder no leen la hoja: piden numeros.
# Antes tenian los valores del ejemplo escritos en el codigo y el usuario no
# podia cambiarlos (auditoria 2026-09, K6).
@dataclass(frozen=True)
class Parametro:
    clave: str
    etiqueta: str
    defecto: float
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

OPCIONES["Poder estadistico"] = (
    Opcion("diseno", "Diseño",
           (("una", "Una muestra o datos pareados (t de una muestra)"),
            ("dos", "Dos grupos independientes (t de dos muestras)")),
           "Con dos grupos, n es el tamaño de CADA grupo."),
)
