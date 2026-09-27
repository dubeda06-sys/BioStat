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
           "mediana. Por encima de 5000 datos el p de Shapiro-Wilk deja de ser "
           "confiable en scipy.",
           alternativa="anderson"),
    Ensayo("anderson", "Normalidad: Anderson-Darling", UNIVARIADO,
           "Columna numérica con n > SHAPIRO_MAX (5000).",
           "Reemplaza a Shapiro-Wilk cuando el n supera lo que su p aguanta. No "
           "es más indulgente: con n tan grande cualquier prueba de normalidad "
           "rechaza por desviaciones mínimas, sin importancia práctica. Antes de "
           "descartar la media conviene mirar el histograma.",
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
           "de Student y t de Welch, y entre ANOVA clásico y ANOVA de Welch.",
           incondicional=True),
    Ensayo("t_student", "t de Student (varianzas iguales)", BIVARIADO,
           "2 grupos, ambos normales, Levene no rechazó.",
           "Compara dos medias asumiendo varianzas iguales.",
           alternativa="t_welch"),
    Ensayo("t_welch", "t de Welch (varianzas distintas)", BIVARIADO,
           "2 grupos, Levene rechazó (normales o no).",
           "Misma comparación sin asumir varianzas iguales: corrige los grados "
           "de libertad. Es lo correcto cuando los grupos dispersan distinto, "
           "aunque no sean normales: ahí la prueba por rangos rechaza por la "
           "dispersión, y Welch tolera la falta de normalidad.",
           alternativa="t_student"),
    Ensayo("mann_whitney", "U de Mann-Whitney", BIVARIADO,
           "2 grupos, al menos uno no normal, y Levene no rechazó.",
           "Compara distribuciones por rangos. No compara medias: compara la "
           "probabilidad de que un valor de un grupo supere al del otro. Si los "
           "grupos dispersan distinto, también reacciona a eso.",
           alternativa="t_student"),
    Ensayo("anova", "ANOVA de una vía", BIVARIADO,
           "3 o más grupos, todos normales, y Levene no rechazó.",
           "Prueba global: dice si al menos un grupo difiere, no cuál.",
           alternativa="anova_welch"),
    Ensayo("anova_welch", "ANOVA de Welch", BIVARIADO,
           "3 o más grupos y Levene rechazó (normales o no).",
           "Compara medias sin suponer varianzas iguales: pondera cada grupo por "
           "su varianza. Kruskal-Wallis no sirve para este caso: con dispersiones "
           "distintas rechaza por la dispersión, no por la posición. Sin "
           "normalidad, Welch sigue siendo el que menos infla los falsos "
           "positivos (auditoría 2026-09, K10).",
           alternativa="kruskal", norma="Welch 1951"),
    Ensayo("kruskal", "Kruskal-Wallis", BIVARIADO,
           "3 o más grupos, alguno no normal, y Levene no rechazó.",
           "El equivalente por rangos del ANOVA. Supone la misma forma de "
           "distribución en todos los grupos: si dispersan distinto, también "
           "reacciona a eso.",
           alternativa="anova"),
    Ensayo("tukey_hsd", "Post-hoc: Tukey HSD", BIVARIADO,
           "El ANOVA detectó diferencia.",
           "Solo después de que el ANOVA detecta algo: identifica QUÉ pares "
           "difieren, controlando las comparaciones múltiples. Correrlo cuando el "
           "ANOVA no detectó nada infla los falsos positivos.",
           alternativa="games_howell"),
    Ensayo("games_howell", "Post-hoc: Games-Howell", BIVARIADO,
           "El ANOVA de Welch detectó diferencia.",
           "El post-hoc del camino de Welch: cada par con su propio error "
           "estándar y sus grados de libertad, sin suponer varianzas iguales.",
           alternativa="dunn", norma="Games & Howell 1976"),
    Ensayo("dunn", "Post-hoc: Dunn (Bonferroni)", BIVARIADO,
           "Kruskal-Wallis detectó diferencia.",
           "Compara los rangos medios de cada par dentro del ranking conjunto de "
           "Kruskal-Wallis, corregido por empates, con Bonferroni sobre los "
           "pares. No es Mann-Whitney de a pares: ese re-rankea cada par y "
           "pierde a los demás grupos.",
           alternativa="tukey_hsd", norma="Dunn 1964"),

    # ---------------- Bivariado: categorica x categorica ----------------
    Ensayo("chi2", "Chi-cuadrado", BIVARIADO,
           "Tabla de contingencia con todas las frecuencias esperadas ≥ 5.",
           "Prueba de asociación. La aproximación chi-cuadrado necesita "
           "frecuencias esperadas suficientes; si no, miente. En 2×2 lleva la "
           "corrección de Yates.",
           alternativa="fisher"),
    Ensayo("fisher", "Test exacto de Fisher", BIVARIADO,
           "Tabla 2×2 con alguna frecuencia esperada < 5.",
           "Calcula la probabilidad exacta en vez de aproximarla. Es la salida "
           "correcta cuando el chi-cuadrado no aplica y la tabla es 2×2.",
           alternativa="chi2"),
    Ensayo("chi2_montecarlo", "Chi-cuadrado con p por simulación", BIVARIADO,
           "Tabla mayor que 2×2 con alguna frecuencia esperada < 5.",
           "Con casilleros flacos la aproximación del chi-cuadrado no vale, y "
           "Fisher es para 2×2. El p se calcula permutando una variable contra "
           "la otra, que deja fijos los totales de filas y columnas: 9999 "
           "tablas, con semilla fija para que la misma tabla dé siempre el "
           "mismo p.",
           alternativa="chi2", norma="Hope 1968"),

    # ---------------- Deteccion de comparacion de metodos ----------------
    Ensayo("score_comparacion", "Puntaje de sospecha de comparación", CONCORDANCIA,
           "Todos los pares numéricos, siempre que haya 2 o más.",
           "Reglas duras (unidad declarada, rango, escala, correlación, nombres, "
           "faltantes en las mismas filas) que PROPONEN pares que podrían ser dos "
           "mediciones de lo mismo. Nunca deciden solas: el usuario confirma. La "
           "auditoría muestra el puntaje de cada par con sus motivos."),

    # ---------------- Subarbol de concordancia ----------------
    Ensayo("variabilidad_diferencias", "Variabilidad de las diferencias (DE, CV o mixta)",
           CONCORDANCIA,
           "Par confirmado como comparación de métodos.",
           "¿La dispersión de las diferencias es pareja en todo el rango (DE "
           "constante), crece con la concentración (CV constante) o ninguna de "
           "las dos (mixta)? Se mide con los residuos absolutos contra el eje. "
           "Decide si el Bland-Altman va en unidades o en % y qué regresión "
           "corresponde.",
           norma="CLSI EP09c §5.4 / Bland & Altman 1999"),
    Ensayo("estructura_diferencia", "Tendencia del sesgo (¿cambia con la concentración?)",
           CONCORDANCIA,
           "Par confirmado como comparación de métodos.",
           "Regresión de la diferencia contra el eje: la referencia, o el "
           "promedio si no se declaró una. Si la pendiente no es cero, el sesgo "
           "cambia con la concentración. Es una lectura de apoyo: la que decide "
           "sobre el sesgo proporcional es la recta de comparación. No mide la "
           "dispersión; eso lo hace la variabilidad de las diferencias.",
           norma="Bland & Altman 1999"),
    Ensayo("ba_escala_porcentual", "Bland-Altman en porcentaje", CONCORDANCIA,
           "La dispersión de las diferencias crece con la concentración y en % "
           "queda pareja (CV constante).",
           "Con CV constante, un solo par de límites en unidades sería demasiado "
           "ancho abajo y demasiado angosto arriba. En porcentaje el margen vale "
           "para todo el rango.",
           norma="CLSI EP09c §5.4.2"),
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
    Ensayo("ba_eje_referencia", "Eje X: promedio vs método de referencia (Krouwer)", CONCORDANCIA,
           "Se declaró que una de las dos columnas es el método de referencia.",
           "Bland-Altman clásico grafica la diferencia contra el promedio de "
           "ambos métodos, porque ninguno de los dos es verdad. Pero si uno ES "
           "la referencia (valor asignado, consenso, material de control), el "
           "promedio contiene a los dos métodos y distorsiona la pendiente en "
           "las dos direcciones: la achica cuando el sesgo proporcional es real "
           "y la infla con el ruido del método en prueba. Cuando se declara una "
           "referencia se contrastan las dos pendientes para dejar ver si el "
           "promedio habría cambiado la conclusión.",
           norma="Krouwer 2008 / CLSI EP09"),
    Ensayo("deming", "Regresión de Deming", CONCORDANCIA,
           "Diferencias normales con dispersión pareja (DE constante).",
           "Regresión con error en ambos ejes. A diferencia de OLS, no asume "
           "que el método del eje X mide sin error. Es la recta por defecto de "
           "EP09c cuando la DE es constante.",
           alternativa="deming_ponderado", norma="CLSI EP09c §6.2.1"),
    Ensayo("deming_ponderado", "Regresión de Deming ponderada (CV constante)", CONCORDANCIA,
           "Diferencias en % normales, CV constante y todos los valores positivos.",
           "Deming con cada punto pesado por 1/concentración²: los puntos altos, "
           "más ruidosos, pesan menos. Sin ponderar, esos puntos arrastran la "
           "recta.",
           alternativa="passing_bablok",
           norma="Linnet 1990 / CLSI EP09c §6.2.2 y apéndice B"),
    Ensayo("passing_bablok", "Regresión de Passing-Bablok", CONCORDANCIA,
           "Diferencias no normales, o dispersión mixta.",
           "Regresión no paramétrica basada en medianas de pendientes: no "
           "asume distribución y aguanta valores atípicos.",
           alternativa="deming", norma="Passing & Bablok 1983 / CLSI EP09c §6.2.3"),
    Ensayo("sesgo_niveles", "Sesgo en niveles de decisión médica", CONCORDANCIA,
           "Se obtuvo una recta de comparación (Deming, Deming ponderado o "
           "Passing-Bablok).",
           "Traduce la recta a la pregunta que importa en el laboratorio: "
           "cuánto se desvía el método en prueba justo en la concentración de "
           "la referencia donde se toma la decisión clínica.",
           norma="CLSI EP09c §6.3"),
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
           "Resume los pares numéricos en una tabla: Pearson o Spearman CELDA POR "
           "CELDA según la normalidad de ese par, con el mismo p corregido que "
           "su bloque. Asumir Pearson para toda la matriz es un error común."),
    Ensayo("fdr_bh", "Corrección por multiplicidad (Benjamini-Hochberg)", MULTIVARIADO,
           "Rama C, con 2 o más pruebas bivariadas.",
           "Con muchas comparaciones a la vez, alguna da un p chico por azar. "
           "Todos los p bivariados de la corrida se corrigen juntos, y cada "
           "bloque, la matriz y el caso deciden con el mismo p corregido.",
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
