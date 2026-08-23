"""Que variables pide cada analisis.

MedCalc no tiene un panel con tres combos siempre visibles: cada procedimiento
abre su propio cuadro de dialogo y ahi pide exactamente lo que necesita. Para
armar ese dialogo hace falta saber, por analisis, cuales de las tres variables
y el alfa entran en juego.

Esta tabla sale de leer el `dispatch` de `AnalysisPanel._run` — es la unica
fuente de verdad de que recibe cada rutina. `tests/test_analysis_specs.py`
vuelve a leer ese dispatch y compara: si alguien agrega un analisis o le cambia
los argumentos y no toca esta tabla, el test lo cachea.

Los 29 analisis con tupla vacia no toman columnas sueltas: trabajan sobre toda
la hoja (tablas de contingencia, ANOVA de varias columnas) o piden sus datos en
campos propios (tamano de muestra). El dialogo se los avisa al usuario en vez de
mostrarle selectores que no hacen nada.
"""

# analisis -> variables que consume, en orden: "c1", "c2", "c3", "alpha"
VARIABLES = {
    'Estadisticas descriptivas': ('c1',),
    't-test pareado': ('c1', 'c2', 'alpha'),
    't-test independiente': ('c1', 'c2', 'alpha'),
    'ANOVA una via': ('alpha',),
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
    'Random Forest (clasificacion)': ('c1', 'c2'),
    'Random Forest (regresion)': ('c1', 'c2'),
    'Mann-Whitney U': ('c1', 'c2'),
    'Wilcoxon pareado': ('c1', 'c2'),
    'Chi-cuadrado': (),
    'Fisher exact': (),
    'McNemar': (),
    'Kruskal-Wallis': (),
    'Friedman': (),
    'F-test (varianzas)': ('c1', 'c2'),
    'Kappa': (),
    'ICC': ('c1', 'c2'),
    'Cronbach alfa': (),
    'Regresion lineal': ('c1', 'c2'),
    'Regresion multiple': (),
    'Regresion logistica': (),
    'Odds Ratio': (),
    'Riesgo Relativo': (),
    'Diagnostic test': (),
    'Outliers (Grubbs)': ('c1',),
    'Outliers (Tukey)': ('c1',),
    'Intervalos de referencia': ('c1',),
    'Asimetria y curtosis': ('c1',),
    'Media recortada': ('c1',),
    'Correlacion parcial': ('c1', 'c2', 'c3'),
    'Media geometrica': ('c1',),
    'Media armonica': ('c1',),
    't-test 1 muestra': ('c1',),
    'ANOVA una via (core)': (),
    'Sign test': ('c1', 'c2'),
    'Cochran Q': (),
    'Kappa ponderado': (),
    'Deming regression': ('c1', 'c2'),
    'CV duplicatas': ('c1', 'c2'),
    'Likelihood Ratios': (),
    'Comparar 2 medias': (),
    'Comparar 2 proporciones': (),
    'Comparar 2 AUC': (),
    'Tabla de percentiles': ('c1',),
    'Edad-relacionada': (),
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
    'Mountain plot': ('c1',),
    'Bland-Altman múltiple': (),
}


def variables(analisis):
    """Variables que pide un analisis. Tupla vacia = trabaja sobre toda la hoja."""
    return VARIABLES.get(analisis, ())


def usa(analisis, variable):
    return variable in VARIABLES.get(analisis, ())


def sobre_toda_la_hoja(analisis):
    """True si el analisis no toma columnas sueltas."""
    return not [v for v in VARIABLES.get(analisis, ()) if v != "alpha"]


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
            "graficar contra el promedio atenúa el sesgo proporcional "
            "(Krouwer 2008; recogido en CLSI EP09).",
        ),
    ),
}


def opciones(analisis):
    """Opciones de metodo de un analisis. Tupla vacia si no tiene."""
    return OPCIONES.get(analisis, ())


def opciones_por_defecto(analisis):
    """El dict que usa el panel cuando nadie eligio nada."""
    return {o.clave: o.defecto for o in OPCIONES.get(analisis, ())}
