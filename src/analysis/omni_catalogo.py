"""Catalogo de ensayos del Omnianalisis — que puede correr el motor, y por que.

El motor es un arbol de decisiones: en cada nodo verifica un supuesto y elige
una rama. Eso significa que **la mayoria de los ensayos posibles NO se corren**,
y esa es la conducta correcta. Pero desde afuera no se distingue "no se corrio
porque el supuesto fallo" de "no se corrio porque me olvide".

Este archivo es el inventario declarativo que permite esa distincion. Cada
entrada describe un ensayo: cuando se gatilla, que decide, contra que
alternativa compite, y por que existe. `omni_auditoria` cruza este catalogo
contra lo que realmente ejecuto una corrida y emite el estado de cada uno.

Fuente de verdad: los `id` de aca tienen que coincidir uno a uno con las marcas
`_marcar(..., "id")` de `omni_analyzer`. `tests/test_omni_catalogo.py` lee el
codigo del analizador y lo verifica — sin eso, agregar un ensayo al motor y
olvidarlo aca lo deja invisible en la auditoria, que es justo el defecto que
esta capa viene a tapar.
"""
from dataclasses import dataclass


# Etapas del arbol, en orden de ejecucion. El orden importa: es el que usan la
# auditoria y el dibujo del arbol para agrupar.
PERFILADO = "Perfilado"
UNIVARIADO = "Univariado"
BIVARIADO = "Bivariado"
CONCORDANCIA = "Concordancia de métodos"
MULTIVARIADO = "Multivariado"

ETAPAS = (PERFILADO, UNIVARIADO, BIVARIADO, CONCORDANCIA, MULTIVARIADO)


@dataclass(frozen=True)
class Ensayo:
    """Un ensayo del catalogo.

    id:          clave estable; la usa `_marcar` en el analizador.
    nombre:      como se muestra.
    etapa:       una de ETAPAS.
    gatillo:     la condicion que lo hace correr, en castellano.
    porque:      para que sirve / que responde. Es el texto didactico.
    alternativa: id del ensayo hermano que corre si el supuesto falla.
                 Vacio si el ensayo no compite con nadie (corre o no corre).
    norma:       cita o referencia, si la tiene.
    incondicional: corre siempre que su etapa se active, sin depender de un
                 supuesto. La auditoria no lo cuenta como "descartado".
    """
    id: str
    nombre: str
    etapa: str
    gatillo: str
    porque: str
    alternativa: str = ""
    norma: str = ""
    incondicional: bool = False


ENSAYOS: tuple[Ensayo, ...] = (
    # ---------------- Perfilado (nodo raiz, corre siempre) ----------------
    Ensayo("perfil_tipos", "Clasificación de tipo por columna", PERFILADO,
           "Siempre, antes de cualquier estadística.",
           "Es la decisión más importante del motor: el tipo de cada columna "
           "define qué ramas del árbol se abren. Una numérica mal leída como "
           "categórica cambia todos los tests que siguen.",
           incondicional=True),
    Ensayo("perfil_estructura", "Métricas estructurales (n, nulos, duplicados)", PERFILADO,
           "Siempre.",
           "n condiciona qué tests tienen potencia; los nulos y duplicados "
           "explican por qué un par pareado pierde casos.",
           incondicional=True),
    Ensayo("perfil_temporal", "Detección de estructura temporal", PERFILADO,
           "Hay al menos una columna fecha/hora.",
           "Si los datos son una serie de tiempo, el análisis transversal no "
           "vale: las observaciones no son independientes. El motor avisa y no "
           "lo fuerza."),

    # ---------------- Univariado numerico ----------------
    Ensayo("desc_numericos", "Descriptivos", UNIVARIADO,
           "Columna numérica.",
           "n, media, DS, mediana, cuartiles, IC 95%. Base de todo lo demás.",
           incondicional=True),
    Ensayo("shapiro", "Normalidad: Shapiro-Wilk", UNIVARIADO,
           "Columna numérica con n ≤ SHAPIRO_MAX (5000).",
           "Es el nodo que decide si la variable se resume con media o con "
           "mediana. Shapiro-Wilk pierde validez con n muy grande.",
           alternativa="anderson"),
    Ensayo("anderson", "Normalidad: Anderson-Darling", UNIVARIADO,
           "Columna numérica con n > SHAPIRO_MAX (5000).",
           "Reemplaza a Shapiro cuando el n es tan grande que Shapiro rechaza "
           "por desviaciones triviales.",
           alternativa="shapiro"),
    Ensayo("central_media", "Tendencia central: media ± DS", UNIVARIADO,
           "La prueba de normalidad no rechazó.",
           "Con distribución normal la media es el mejor resumen y la DS "
           "describe la dispersión de forma interpretable.",
           alternativa="central_mediana"),
    Ensayo("central_mediana", "Tendencia central: mediana + IQR", UNIVARIADO,
           "La prueba de normalidad rechazó.",
           "Con distribución asimétrica la media se corre hacia la cola y "
           "describe mal al caso típico. La mediana no.",
           alternativa="central_media"),
    Ensayo("tukey_outliers", "Valores atípicos por regla de Tukey", UNIVARIADO,
           "Columna numérica con dispersión evaluable.",
           "Marca valores fuera de [Q1−1,5·IQR, Q3+1,5·IQR]. No los borra: los "
           "señala para que el analista decida."),

    # ---------------- Univariado categorico ----------------
    Ensayo("frecuencias", "Tabla de frecuencias", UNIVARIADO,
           "Columna categórica o binaria.",
           "Absolutas y relativas. Además expone categorías con n muy chico, "
           "que después rompen el chi-cuadrado.",
           incondicional=True),
    Ensayo("moda", "Moda", UNIVARIADO,
           "Columna categórica o binaria.",
           "La categoría más frecuente: el resumen de tendencia central que sí "
           "tiene sentido cuando no hay orden numérico.",
           incondicional=True),
    Ensayo("entropia", "Entropía de Shannon", UNIVARIADO,
           "Columna categórica o binaria.",
           "Mide cuán repartida está la variable entre sus categorías. Cerca de "
           "0 = casi todo cae en una sola; alta = reparto parejo.",
           incondicional=True),

    # ---------------- Bivariado: numerica x numerica ----------------
    Ensayo("pearson", "Correlación de Pearson", BIVARIADO,
           "Par numérico × numérico con ambas normales.",
           "Mide asociación LINEAL. Ojo: asociación no es acuerdo — para "
           "comparar métodos hace falta el subárbol de concordancia.",
           alternativa="spearman"),
    Ensayo("spearman", "Correlación de Spearman", BIVARIADO,
           "Par numérico × numérico donde al menos una no es normal.",
           "Mide asociación MONÓTONA sobre rangos: no exige normalidad ni "
           "linealidad y aguanta valores atípicos.",
           alternativa="pearson"),

    # ---------------- Bivariado: numerica x categorica ----------------
    Ensayo("levene", "Homocedasticidad: prueba de Levene", BIVARIADO,
           "Par numérico × categórico con 2 o más grupos.",
           "Verifica si los grupos tienen varianzas comparables. Decide entre t "
           "de Student y t de Welch, y entre ANOVA y Kruskal-Wallis.",
           incondicional=True),
    Ensayo("t_student", "t de Student (varianzas iguales)", BIVARIADO,
           "2 grupos, ambos normales, Levene no rechazó.",
           "Compara dos medias asumiendo varianzas iguales.",
           alternativa="t_welch"),
    Ensayo("t_welch", "t de Welch (varianzas distintas)", BIVARIADO,
           "2 grupos, ambos normales, Levene rechazó.",
           "Misma comparación sin asumir varianzas iguales: corrige los grados "
           "de libertad. Es lo correcto cuando los grupos dispersan distinto.",
           alternativa="t_student"),
    Ensayo("mann_whitney", "U de Mann-Whitney", BIVARIADO,
           "2 grupos donde al menos uno no es normal.",
           "Compara distribuciones por rangos. No compara medias: compara la "
           "probabilidad de que un valor de un grupo supere al del otro.",
           alternativa="t_student"),
    Ensayo("anova", "ANOVA de una vía", BIVARIADO,
           "3 o más grupos, todos normales y homocedásticos.",
           "Prueba global: dice si al menos un grupo difiere, no cuál.",
           alternativa="kruskal"),
    Ensayo("kruskal", "Kruskal-Wallis", BIVARIADO,
           "3 o más grupos con normalidad u homocedasticidad incumplida.",
           "El equivalente no paramétrico del ANOVA, sobre rangos.",
           alternativa="anova"),
    Ensayo("tukey_hsd", "Post-hoc: Tukey HSD", BIVARIADO,
           "ANOVA significativo.",
           "Solo después de un ANOVA significativo: identifica QUÉ pares "
           "difieren, corrigiendo por las comparaciones múltiples. Correrlo sin "
           "ANOVA significativo infla los falsos positivos.",
           alternativa="dunn"),
    Ensayo("dunn", "Post-hoc: Dunn (Bonferroni)", BIVARIADO,
           "Kruskal-Wallis significativo.",
           "El post-hoc del camino no paramétrico, con Bonferroni sobre los "
           "pares.",
           alternativa="tukey_hsd"),

    # ---------------- Bivariado: categorica x categorica ----------------
    Ensayo("chi2", "Chi-cuadrado", BIVARIADO,
           "Tabla de contingencia con todas las frecuencias esperadas ≥ 5.",
           "Prueba de asociación. La aproximación chi-cuadrado necesita "
           "frecuencias esperadas suficientes; si no, miente.",
           alternativa="fisher"),
    Ensayo("fisher", "Test exacto de Fisher", BIVARIADO,
           "Tabla 2×2 con alguna frecuencia esperada < 5.",
           "Calcula la probabilidad exacta en vez de aproximarla. Es la salida "
           "correcta cuando el chi-cuadrado no aplica.",
           alternativa="chi2"),

    # ---------------- Deteccion de comparacion de metodos ----------------
    Ensayo("score_comparacion", "Puntaje de sospecha de comparación", CONCORDANCIA,
           "Todos los pares numéricos, siempre que haya 2 o más.",
           "Reglas duras (rango, escala, correlación, nombres) que PROPONEN "
           "pares que podrían ser dos mediciones de lo mismo. Nunca deciden "
           "solas: el usuario confirma."),

    # ---------------- Subarbol de concordancia ----------------
    Ensayo("estructura_diferencia", "Estructura de la diferencia (dif. ~ promedio)", CONCORDANCIA,
           "Par confirmado como comparación de métodos.",
           "Regresión de la diferencia contra el promedio. Si la pendiente es "
           "significativa, el sesgo crece con la concentración: hay que "
           "trabajar en % o en log, no en unidades absolutas.",
           norma="Bland & Altman 1999"),
    Ensayo("normalidad_diferencias", "Normalidad de las DIFERENCIAS", CONCORDANCIA,
           "Par confirmado como comparación de métodos.",
           "El test va sobre la serie de diferencias, NUNCA sobre los datos "
           "crudos de cada método. Es el error clásico de Bland-Altman.",
           norma="Bland & Altman 1999"),
    Ensayo("ba_parametrico", "Bland-Altman paramétrico", CONCORDANCIA,
           "Las diferencias pasaron la prueba de normalidad.",
           "Sesgo medio con límites de acuerdo en ±1,96·DS y su IC. Solo "
           "vale si las diferencias son normales.",
           alternativa="ba_no_parametrico", norma="CLSI EP09"),
    Ensayo("ba_no_parametrico", "Bland-Altman no paramétrico", CONCORDANCIA,
           "Las diferencias NO son normales.",
           "Límites de acuerdo por percentiles empíricos 2,5 y 97,5. Este es el "
           "nodo que evita publicar LoA paramétricos sobre diferencias "
           "asimétricas.",
           alternativa="ba_parametrico", norma="CLSI EP09"),
    Ensayo("deming", "Regresión de Deming", CONCORDANCIA,
           "Diferencias normales y homocedásticas.",
           "Regresión con error en ambos ejes. A diferencia de OLS, no asume "
           "que el método del eje X mide sin error.",
           alternativa="passing_bablok", norma="CLSI EP09"),
    Ensayo("passing_bablok", "Regresión de Passing-Bablok", CONCORDANCIA,
           "Diferencias no normales o error heterocedástico.",
           "Regresión no paramétrica basada en medianas de pendientes: no "
           "asume distribución y aguanta valores atípicos.",
           alternativa="deming", norma="Passing & Bablok 1983 / CLSI EP09"),
    Ensayo("sesgo_niveles", "Sesgo en niveles de decisión médica", CONCORDANCIA,
           "Se obtuvo una recta de comparación (Deming o Passing-Bablok).",
           "Traduce la recta a la pregunta que importa en el laboratorio: "
           "cuánto se desvía el método justo en la concentración donde se toma "
           "la decisión clínica.",
           norma="CLSI EP09"),
    Ensayo("ccc", "CCC de Lin (concordancia)", CONCORDANCIA,
           "Par confirmado como comparación de métodos.",
           "Mide ACUERDO, no asociación: penaliza el corrimiento respecto de la "
           "recta de identidad. Es lo que Pearson no hace.",
           norma="Lin 1989 / McBride 2005"),
    Ensayo("ccc_descomposicion", "Descomposición CCC = rho × Cb", CONCORDANCIA,
           "El CCC se pudo calcular.",
           "Separa el desacuerdo en precisión (rho, dispersión) y veracidad "
           "(Cb, sesgo). Dice DÓNDE está el problema: recalibrar o mejorar la "
           "imprecisión son arreglos distintos.",
           norma="Lin 1989"),

    # ---------------- Rama C: multivariado ----------------
    Ensayo("matriz_correlacion", "Matriz de correlación (método por celda)", MULTIVARIADO,
           "3 o más columnas, con 2 o más numéricas.",
           "Elige Pearson o Spearman CELDA POR CELDA según la normalidad de ese "
           "par. Asumir Pearson para toda la matriz es un error común."),
    Ensayo("fdr_bh", "Corrección por multiplicidad (Benjamini-Hochberg)", MULTIVARIADO,
           "Se calculó una matriz de correlación.",
           "Con muchas comparaciones a la vez, algunas dan significativas por "
           "azar. Se informan p crudo y p ajustado.",
           norma="Benjamini & Hochberg 1995"),
    Ensayo("regresion_multiple", "Regresión múltiple", MULTIVARIADO,
           "Se eligió una variable objetivo numérica y hay predictoras.",
           "Modela el objetivo en función de varias predictoras a la vez, "
           "aislando el aporte de cada una.",
           alternativa="pca"),
    Ensayo("vif", "Diagnóstico de multicolinealidad (VIF)", MULTIVARIADO,
           "Se corrió una regresión múltiple.",
           "VIF alto = predictoras que dicen lo mismo. Los coeficientes se "
           "vuelven inestables y cambian de signo con poco ruido."),
    Ensayo("pca", "PCA (exploratorio)", MULTIVARIADO,
           "3 o más numéricas sin objetivo declarado.",
           "Cuántas dimensiones hacen falta para explicar el 90% de la "
           "variación. Exploratorio: no prueba hipótesis.",
           alternativa="regresion_multiple"),
    Ensayo("clustering", "Clustering KMeans (exploratorio)", MULTIVARIADO,
           "Se corrió PCA exploratorio.",
           "Agrupa casos parecidos y elige k por silueta. Los grupos que salen "
           "NO son grupos clínicos hasta que alguien los valide."),
)


# Indice por id, para no recorrer la tupla en cada consulta.
POR_ID: dict[str, Ensayo] = {e.id: e for e in ENSAYOS}


def ensayo(id_: str) -> Ensayo | None:
    return POR_ID.get(id_)


def por_etapa(etapa: str) -> list[Ensayo]:
    return [e for e in ENSAYOS if e.etapa == etapa]


def total() -> int:
    return len(ENSAYOS)
