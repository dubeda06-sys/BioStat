"""Fórmulas de cada ensayo del catálogo, en notación matemática.

Para cada ensayo (por id de `omni_catalogo`) guarda:

- `que`: qué calcula, en una o dos frases.
- `general`: las fórmulas que definen el cálculo, en LaTeX compatible con el
  mathtext de matplotlib (raíces con su línea, raya de fracción, sumatorias).
- `simbolos`: qué significa cada símbolo.
- `iterativo` + `pasos`: si el cálculo es un algoritmo (iteraciones, búsqueda,
  remuestreo), se describen los pasos en vez de volcar cada iteración, que sería
  ilegible.
- `sustituir(valores)`: si el motor guardó los números crudos de la corrida,
  devuelve las mismas fórmulas con esos números puestos ("cómo se hizo").

Es matemática estándar; las referencias de cada prueba están en el catálogo.
"""
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from scipy import stats


# ---------------------------------------------------------------- formato
def _f(v, d=4):
    """Número para LaTeX: sin ceros de más; notación científica si hace falta."""
    if v is None:
        return r"\mathrm{n/d}"
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    if not np.isfinite(v):
        if v == np.inf:
            return r"\infty"
        if v == -np.inf:
            return r"-\infty"
        return r"\mathrm{n/d}"  # NaN
    if v != 0 and (abs(v) < 1e-4 or abs(v) >= 1e6):
        mant, exp = f"{v:.3e}".split("e")
        return rf"{mant}\times 10^{{{int(exp)}}}"
    s = f"{v:.{d}f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def _fp(v, d=4):
    """Como _f, pero entre paréntesis si es negativo (para restar o elevar)."""
    s = _f(v, d)
    return f"({s})" if s.startswith("-") else s


def _p(p):
    if p is None:
        return r"p\ \mathrm{n/d}"
    p = float(p)
    return r"p < 0.0001" if p < 1e-4 else rf"p = {_f(p)}"


def _i(v):
    try:
        return str(int(round(float(v))))
    except (TypeError, ValueError):
        return r"\mathrm{n/d}"


# ---------------------------------------------------------------- modelo
@dataclass
class Formula:
    que: str
    general: list = field(default_factory=list)      # [(rótulo, latex)]
    simbolos: list = field(default_factory=list)     # [(latex, significado)]
    iterativo: bool = False
    pasos: list = field(default_factory=list)        # [str]
    sustituir: Callable | None = None                # valores -> [(rótulo, latex)]


# ---------------------------------------------------------------- sustituciones
def _s_desc(v):
    n = int(v["n"])
    return [
        ("Media", rf"\bar{{x}} = \dfrac{{\sum x_i}}{{n}} = \dfrac{{{_f(v['suma'])}}}{{{n}}}"
                  rf" = {_f(v['media'])}"),
        ("Desvío estándar",
         rf"s = \sqrt{{\dfrac{{\sum (x_i-\bar{{x}})^2}}{{n-1}}}} = "
         rf"\sqrt{{\dfrac{{{_f(v['ss'])}}}{{{n - 1}}}}} = {_f(v['ds'])}"),
    ]


def _s_media(v):
    n = int(v["n"])
    s, m = float(v["ds"]), float(v["media"])
    ee = s / np.sqrt(n)
    tc = float(stats.t.ppf(0.975, n - 1))
    return [
        ("Error estándar de la media",
         rf"EE = \dfrac{{s}}{{\sqrt{{n}}}} = \dfrac{{{_f(s)}}}{{\sqrt{{{n}}}}} = {_f(ee)}"),
        ("Intervalo de confianza 95 %",
         rf"\bar{{x}} \pm t_{{0.975,\,{n - 1}}}\cdot EE = {_f(m)} \pm {_f(tc)}\cdot{_f(ee)}"
         rf" = \left[{_f(m - tc * ee)},\ {_f(m + tc * ee)}\right]"),
    ]


def _s_mediana(v):
    q1, q3 = float(v["q1"]), float(v["q3"])
    return [
        ("Mediana", rf"\tilde{{x}} = {_f(v['mediana'])}"),
        ("Rango intercuartílico",
         rf"IQR = Q_3 - Q_1 = {_f(q3)} - {_fp(q1)} = {_f(q3 - q1)}"),
    ]


def _s_shapiro(v):
    return [("Resultado", rf"W = {_f(v['W'])},\quad n = {_i(v['n'])},\quad {_p(v['p'])}")]


def _s_levene(v):
    k, n = int(v["k"]), int(v["N"])
    return [("Resultado",
             rf"W = {_f(v['W'])}\qquad gl_1 = k-1 = {k - 1},\quad gl_2 = N-k = {n - k},"
             rf"\quad {_p(v['p'])}")]


def _s_student(v):
    n1, n2 = int(v["n1"]), int(v["n2"])
    return [
        ("Desvío combinado",
         rf"s_p = \sqrt{{\dfrac{{(n_1-1)s_1^2+(n_2-1)s_2^2}}{{n_1+n_2-2}}}} = "
         rf"\sqrt{{\dfrac{{{n1 - 1}\cdot {_f(v['s1'])}^2+{n2 - 1}\cdot {_f(v['s2'])}^2}}"
         rf"{{{n1 + n2 - 2}}}}} = {_f(v['sp'])}"),
        ("Estadístico t",
         rf"t = \dfrac{{\bar{{x}}_1-\bar{{x}}_2}}{{s_p\sqrt{{\dfrac{{1}}{{n_1}}+\dfrac{{1}}{{n_2}}}}}} = "
         rf"\dfrac{{{_f(v['m1'])}-{_fp(v['m2'])}}}"
         rf"{{{_f(v['sp'])}\sqrt{{\dfrac{{1}}{{{n1}}}+\dfrac{{1}}{{{n2}}}}}}} = {_f(v['t'])}"),
        ("Grados de libertad", rf"gl = n_1+n_2-2 = {_i(v['gl'])},\quad {_p(v['p'])}"),
    ]


def _s_welch(v):
    n1, n2 = int(v["n1"]), int(v["n2"])
    return [
        ("Estadístico t",
         rf"t = \dfrac{{\bar{{x}}_1-\bar{{x}}_2}}{{\sqrt{{\dfrac{{s_1^2}}{{n_1}}+\dfrac{{s_2^2}}{{n_2}}}}}} = "
         rf"\dfrac{{{_f(v['m1'])}-{_fp(v['m2'])}}}"
         rf"{{\sqrt{{\dfrac{{{_f(v['s1'])}^2}}{{{n1}}}+\dfrac{{{_f(v['s2'])}^2}}{{{n2}}}}}}} = {_f(v['t'])}"),
        ("Grados de libertad (Welch-Satterthwaite)",
         rf"gl = \dfrac{{\left(\dfrac{{s_1^2}}{{n_1}}+\dfrac{{s_2^2}}{{n_2}}\right)^2}}"
         rf"{{\dfrac{{(s_1^2/n_1)^2}}{{n_1-1}}+\dfrac{{(s_2^2/n_2)^2}}{{n_2-1}}}} = {_f(v['gl'], 2)},"
         rf"\quad {_p(v['p'])}"),
    ]


def _s_mw(v):
    n1 = int(v["ns"][0])
    r1 = float(v["R"][0])
    u1 = r1 - n1 * (n1 + 1) / 2
    return [
        ("U del primer grupo",
         rf"U_1 = R_1 - \dfrac{{n_1(n_1+1)}}{{2}} = {_f(r1)} - \dfrac{{{n1}\cdot{n1 + 1}}}{{2}}"
         rf" = {_f(u1)}"),
        ("Resultado", rf"U = {_f(v['U'])},\quad n_1 = {n1},\ n_2 = {_i(v['ns'][1])},\quad {_p(v['p'])}"),
    ]


def _s_anova(v):
    glb, glw = int(v["glb"]), int(v["glw"])
    return [
        ("Suma de cuadrados entre grupos",
         rf"SC_E = \sum_{{j=1}}^{{k}} n_j\left(\bar{{x}}_j-\bar{{x}}\right)^2 = {_f(v['ssb'])}"),
        ("Suma de cuadrados dentro de los grupos",
         rf"SC_D = \sum_{{j=1}}^{{k}}\sum_{{i=1}}^{{n_j}}\left(x_{{ij}}-\bar{{x}}_j\right)^2"
         rf" = {_f(v['ssw'])}"),
        ("Estadístico F",
         rf"F = \dfrac{{SC_E/(k-1)}}{{SC_D/(N-k)}} = \dfrac{{{_f(v['ssb'])}/{glb}}}"
         rf"{{{_f(v['ssw'])}/{glw}}} = \dfrac{{{_f(v['msb'])}}}{{{_f(v['msw'])}}} = {_f(v['F'])}"),
        ("Grados de libertad", rf"gl = ({glb},\ {glw}),\quad {_p(v['p'])}"),
    ]


def _s_welch_anova(v):
    return [("Resultado", rf"F^{{*}} = {_f(v['F'])},\quad k = {_i(v['k'])},\ N = {_i(v['N'])},"
                          rf"\quad {_p(v['p'])}")]


def _s_kruskal(v):
    n_tot = int(v["N"])
    rs, ns = v["R"], v["ns"]
    suma = sum(float(r) ** 2 / int(n) for r, n in zip(rs, ns))
    h_calc = 12 / (n_tot * (n_tot + 1)) * suma - 3 * (n_tot + 1)
    terminos = [rf"\dfrac{{{_f(r, 1)}^2}}{{{int(n)}}}" for r, n in zip(rs, ns)]
    if len(terminos) > 4:
        terminos = terminos[:3] + [r"\cdots"]
    filas = [("Estadístico H (sin empates)",
              rf"H = \dfrac{{12}}{{N(N+1)}}\sum_{{j=1}}^{{k}}\dfrac{{R_j^2}}{{n_j}} - 3(N+1) = "
              rf"\dfrac{{12}}{{{n_tot}\cdot{n_tot + 1}}}\left({' + '.join(terminos)}\right)"
              rf" - 3\cdot{n_tot + 1} = {_f(h_calc)}")]
    if abs(h_calc - float(v["H"])) > 1e-3:
        filas.append(("Con corrección por empates (la que usa el motor)",
                      rf"H = {_f(v['H'])},\quad {_p(v['p'])}"))
    else:
        filas.append(("Resultado", rf"H = {_f(v['H'])},\quad {_p(v['p'])}"))
    return filas


def _s_pearson(v):
    n = int(v["n"])
    filas = [("Coeficiente", rf"r = {_f(v['r'])},\quad n = {n}")]
    if v.get("t") is not None:
        filas.append(("Contraste de H0: ρ = 0",
                      rf"t = \dfrac{{r\sqrt{{n-2}}}}{{\sqrt{{1-r^2}}}} = "
                      rf"\dfrac{{{_f(v['r'])}\sqrt{{{n - 2}}}}}{{\sqrt{{1-{_fp(v['r'])}^2}}}}"
                      rf" = {_f(v['t'])},\quad {_p(v['p'])}"))
    return filas


def _s_spearman(v):
    return [("Resultado", rf"\rho = {_f(v['rho'])},\quad n = {_i(v['n'])},\quad {_p(v['p'])}")]


def _s_chi2(v):
    obs, esp = v["O"], v["E"]
    terminos = []
    for o, e in list(zip(obs, esp))[:4]:
        if v.get("yates"):
            terminos.append(rf"\dfrac{{(|{_f(o, 2)}-{_f(e, 2)}|-0.5)^2}}{{{_f(e, 2)}}}")
        else:
            terminos.append(rf"\dfrac{{({_f(o, 2)}-{_f(e, 2)})^2}}{{{_f(e, 2)}}}")
    if len(obs) > 4:
        terminos.append(r"\cdots")
    f_, c_ = int(v["filas"]), int(v["cols"])
    return [
        ("Esperado de cada celda", r"E_{ij} = \dfrac{\mathrm{total\ fila}_i\cdot"
                                    r"\mathrm{total\ columna}_j}{N}"),
        ("Estadístico χ²" + (" (corrección de Yates)" if v.get("yates") else ""),
         rf"\chi^2 = {' + '.join(terminos)} = {_f(v['chi2'])}"),
        ("Grados de libertad",
         rf"gl = (f-1)(c-1) = ({f_}-1)({c_}-1) = {_i(v['gl'])},\quad {_p(v['p'])}"),
    ]


def _s_fisher(v):
    a, b, c, d = (_i(v[x]) for x in "abcd")
    return [
        ("Odds ratio",
         rf"OR = \dfrac{{a\cdot d}}{{b\cdot c}} = \dfrac{{{a}\cdot{d}}}{{{b}\cdot{c}}} = {_f(v['OR'])}"),
        ("Resultado", _p(v["p"])),
    ]


def _s_ba(v):
    u = r"\ \%" if v.get("pct") else ""
    return [
        ("Sesgo (media de las diferencias)",
         rf"\bar{{d}} = \dfrac{{\sum d_i}}{{n}} = {_f(v['sesgo'])}{u}"),
        ("Límites de acuerdo 95 %",
         rf"\bar{{d}} \pm 1.96\,s_d = {_f(v['sesgo'])} \pm 1.96\cdot{_f(v['sd'])} = "
         rf"\left[{_f(v['loa_inf'])},\ {_f(v['loa_sup'])}\right]{u}"),
    ]


# ---------------------------------------------------------------- catálogo
_X = (r"x_i", "cada valor observado")
_N = (r"n", "cantidad de valores")
_XB = (r"\bar{x}", "media")

FORMULAS: dict[str, Formula] = {
    # ------------------------------------------------------ Perfilado
    "perfil_tipos": Formula(
        que="Clasifica cada columna (continua, discreta, nominal, ordinal, binaria, fecha) "
            "por reglas sobre sus valores.",
        iterativo=True,
        pasos=["Intenta leer la columna como número y como fecha.",
               "Cuenta valores distintos y su proporción sobre n.",
               "Aplica las reglas en orden (binaria → fecha → numérica → categórica).",
               "Si dos reglas empatan, la marca como ambigua."]),
    "perfil_estructura": Formula(
        que="Mide el tamaño y la calidad estructural de cada columna.",
        general=[("Faltantes", r"\%_{\mathrm{nulos}} = \dfrac{n_{\mathrm{nulos}}}{n}\times 100"),
                 ("Duplicados", r"\%_{\mathrm{dup}} = \dfrac{n_{\mathrm{dup}}}{n}\times 100")],
        simbolos=[(r"n", "filas totales")]),
    "perfil_temporal": Formula(
        que="Detecta si hay una columna de fecha/tiempo que ordene los datos (serie).",
        iterativo=True,
        pasos=["Busca columnas de tipo fecha o índices monótonos.",
               "Si existe, ordena por ella y marca la serie para el análisis temporal."]),
    # ------------------------------------------------------ Univariado
    "desc_numericos": Formula(
        que="Resume la columna: cuántos datos hay, su promedio y cuánto se dispersan.",
        general=[("Media", r"\bar{x} = \dfrac{1}{n}\sum_{i=1}^{n} x_i"),
                 ("Desvío estándar",
                  r"s = \sqrt{\dfrac{\sum_{i=1}^{n}\left(x_i-\bar{x}\right)^2}{n-1}}")],
        simbolos=[_X, _N, _XB, (r"s", "desvío estándar muestral")],
        sustituir=_s_desc),
    "shapiro": Formula(
        que="Prueba si los datos se reparten como una campana (normal). W cerca de 1 = normal.",
        general=[("Estadístico W",
                  r"W = \dfrac{\left(\sum_{i=1}^{n} a_i\,x_{(i)}\right)^2}"
                  r"{\sum_{i=1}^{n}\left(x_i-\bar{x}\right)^2}")],
        simbolos=[(r"x_{(i)}", "i-ésimo valor ordenado de menor a mayor"),
                  (r"a_i", "pesos tabulados de la normal (dependen de n)")],
        iterativo=True,
        pasos=["Ordena los datos de menor a mayor.",
               "Calcula los pesos a<sub>i</sub> con la aproximación de Royston (no hay forma cerrada).",
               "Arma W con la fórmula de arriba.",
               "Transforma W a una z normal y de ahí obtiene el p."],
        sustituir=_s_shapiro),
    "anderson": Formula(
        que="Prueba de normalidad que pesa más las colas; se usa con muestras grandes.",
        general=[("Estadístico A²",
                  r"A^2 = -n - \dfrac{1}{n}\sum_{i=1}^{n}(2i-1)\left[\ln F(x_{(i)})"
                  r" + \ln\left(1-F(x_{(n+1-i)})\right)\right]")],
        simbolos=[(r"F", "función de distribución normal con la media y s de la muestra"),
                  (r"x_{(i)}", "valores ordenados")]),
    "central_media": Formula(
        que="Con datos normales, el centro se resume con la media y su intervalo de confianza.",
        general=[("Error estándar", r"EE = \dfrac{s}{\sqrt{n}}"),
                 ("Intervalo de confianza 95 %", r"\bar{x} \pm t_{0.975,\,n-1}\cdot\dfrac{s}{\sqrt{n}}")],
        simbolos=[_XB, (r"s", "desvío estándar"), (r"t_{0.975,\,n-1}", "cuantil t de Student")],
        sustituir=_s_media),
    "central_mediana": Formula(
        que="Sin campana, el centro se resume con la mediana y el rango intercuartílico.",
        general=[("Mediana", r"\tilde{x} = x_{\left(\frac{n+1}{2}\right)}"),
                 ("Rango intercuartílico", r"IQR = Q_3 - Q_1")],
        simbolos=[(r"Q_1,\ Q_3", "percentiles 25 y 75")],
        sustituir=_s_mediana),
    "tukey_outliers": Formula(
        que="Marca como atípicos los valores muy alejados de la caja central.",
        general=[("Límites", r"\left[\,Q_1 - 1.5\,IQR,\ \ Q_3 + 1.5\,IQR\,\right]")],
        simbolos=[(r"IQR", "Q₃ − Q₁")]),
    "frecuencias": Formula(
        que="Cuenta cuántas veces aparece cada categoría.",
        general=[("Frecuencia relativa", r"f_i = \dfrac{n_i}{n}\times 100\ \%")]),
    "moda": Formula(
        que="La categoría más frecuente.",
        general=[("Moda", r"\mathrm{Mo} = \mathrm{arg\,max}_i\ n_i")]),
    "entropia": Formula(
        que="Mide qué tan repartidas están las categorías (0 = todo en una sola).",
        general=[("Entropía de Shannon", r"H = -\sum_{i=1}^{k} p_i\,\log_2 p_i")],
        simbolos=[(r"p_i", "proporción de la categoría i")]),
    # ------------------------------------------------------ Bivariado
    "pearson": Formula(
        que="Mide la relación lineal entre dos variables numéricas (−1 a 1).",
        general=[("Coeficiente r",
                  r"r = \dfrac{\sum (x_i-\bar{x})(y_i-\bar{y})}"
                  r"{\sqrt{\sum (x_i-\bar{x})^2}\,\sqrt{\sum (y_i-\bar{y})^2}}"),
                 ("Contraste", r"t = \dfrac{r\sqrt{n-2}}{\sqrt{1-r^2}}")],
        simbolos=[(r"\bar{x},\ \bar{y}", "medias de cada variable")],
        sustituir=_s_pearson),
    "spearman": Formula(
        que="Relación monótona por rangos; no exige campana.",
        general=[("ρ de Spearman (sin empates)", r"\rho = 1 - \dfrac{6\sum d_i^2}{n(n^2-1)}")],
        simbolos=[(r"d_i", "diferencia entre los rangos de x e y")],
        sustituir=_s_spearman),
    "levene": Formula(
        que="Prueba si los grupos tienen la misma dispersión (variante centrada en la mediana).",
        general=[("Distancias a la mediana", r"Z_{ij} = \left|x_{ij} - \tilde{x}_j\right|"),
                 ("Estadístico W",
                  r"W = \dfrac{N-k}{k-1}\cdot\dfrac{\sum_{j} n_j\left(\bar{Z}_{j}-\bar{Z}\right)^2}"
                  r"{\sum_{j}\sum_{i}\left(Z_{ij}-\bar{Z}_{j}\right)^2}")],
        simbolos=[(r"\tilde{x}_j", "mediana del grupo j"), (r"k", "número de grupos"),
                  (r"N", "total de observaciones")],
        sustituir=_s_levene),
    "t_student": Formula(
        que="Compara las medias de 2 grupos normales con la misma dispersión.",
        general=[("Desvío combinado",
                  r"s_p = \sqrt{\dfrac{(n_1-1)s_1^2+(n_2-1)s_2^2}{n_1+n_2-2}}"),
                 ("Estadístico t",
                  r"t = \dfrac{\bar{x}_1-\bar{x}_2}{s_p\sqrt{\dfrac{1}{n_1}+\dfrac{1}{n_2}}}")],
        simbolos=[(r"\bar{x}_j,\ s_j,\ n_j", "media, desvío y tamaño de cada grupo")],
        sustituir=_s_student),
    "t_welch": Formula(
        que="Compara las medias de 2 grupos sin suponer igual dispersión.",
        general=[("Estadístico t",
                  r"t = \dfrac{\bar{x}_1-\bar{x}_2}{\sqrt{\dfrac{s_1^2}{n_1}+\dfrac{s_2^2}{n_2}}}"),
                 ("Grados de libertad",
                  r"gl = \dfrac{\left(\dfrac{s_1^2}{n_1}+\dfrac{s_2^2}{n_2}\right)^2}"
                  r"{\dfrac{(s_1^2/n_1)^2}{n_1-1}+\dfrac{(s_2^2/n_2)^2}{n_2-1}}")],
        simbolos=[(r"\bar{x}_j,\ s_j,\ n_j", "media, desvío y tamaño de cada grupo")],
        sustituir=_s_welch),
    "mann_whitney": Formula(
        que="Compara 2 grupos por el orden de sus valores, sin exigir campana.",
        general=[("Estadístico U", r"U_1 = R_1 - \dfrac{n_1(n_1+1)}{2}")],
        simbolos=[(r"R_1", "suma de los rangos del grupo 1 en la muestra conjunta")],
        sustituir=_s_mw),
    "anova": Formula(
        que="Compara las medias de 3 o más grupos normales con igual dispersión.",
        general=[("Entre grupos", r"SC_E = \sum_{j=1}^{k} n_j\left(\bar{x}_j-\bar{x}\right)^2"),
                 ("Dentro de los grupos",
                  r"SC_D = \sum_{j=1}^{k}\sum_{i=1}^{n_j}\left(x_{ij}-\bar{x}_j\right)^2"),
                 ("Estadístico F", r"F = \dfrac{SC_E/(k-1)}{SC_D/(N-k)}")],
        simbolos=[(r"\bar{x}", "media general"), (r"\bar{x}_j", "media del grupo j")],
        sustituir=_s_anova),
    "anova_welch": Formula(
        que="ANOVA que no supone igual dispersión entre grupos.",
        general=[("Pesos", r"w_j = \dfrac{n_j}{s_j^2}"),
                 ("Media ponderada", r"\bar{x}_w = \dfrac{\sum w_j\bar{x}_j}{\sum w_j}"),
                 ("Estadístico F*",
                  r"F^{*} = \dfrac{\dfrac{1}{k-1}\sum w_j(\bar{x}_j-\bar{x}_w)^2}"
                  r"{1+\dfrac{2(k-2)}{k^2-1}\sum\dfrac{(1-w_j/\sum w)^2}{n_j-1}}")],
        sustituir=_s_welch_anova),
    "kruskal": Formula(
        que="Compara 3 o más grupos por rangos, sin exigir campana.",
        general=[("Estadístico H",
                  r"H = \dfrac{12}{N(N+1)}\sum_{j=1}^{k}\dfrac{R_j^2}{n_j} - 3(N+1)")],
        simbolos=[(r"R_j", "suma de rangos del grupo j"), (r"N", "total de observaciones")],
        sustituir=_s_kruskal),
    "tukey_hsd": Formula(
        que="Después del ANOVA, compara los grupos de a pares controlando el error global.",
        general=[("Estadístico q",
                  r"q = \dfrac{\bar{x}_i-\bar{x}_j}"
                  r"{\sqrt{\dfrac{MS_D}{2}\left(\dfrac{1}{n_i}+\dfrac{1}{n_j}\right)}}")],
        simbolos=[(r"MS_D", "cuadrado medio dentro de los grupos (del ANOVA)")]),
    "games_howell": Formula(
        que="Comparaciones de a pares cuando las dispersiones difieren.",
        general=[("Estadístico q",
                  r"q = \dfrac{\bar{x}_i-\bar{x}_j}"
                  r"{\sqrt{\dfrac{1}{2}\left(\dfrac{s_i^2}{n_i}+\dfrac{s_j^2}{n_j}\right)}}")]),
    "dunn": Formula(
        que="Comparaciones de a pares por rangos después de Kruskal-Wallis.",
        general=[("Estadístico z",
                  r"z = \dfrac{\bar{R}_i-\bar{R}_j}"
                  r"{\sqrt{\dfrac{N(N+1)}{12}\left(\dfrac{1}{n_i}+\dfrac{1}{n_j}\right)}}"),
                 ("Bonferroni", r"p_{\mathrm{aj}} = \min\left(1,\ m\cdot p\right)")],
        simbolos=[(r"m", "número de comparaciones")]),
    "autocorrelacion": Formula(
        que="Prueba si los valores de una serie dependen de los anteriores.",
        general=[("Estadístico Q de Ljung-Box",
                  r"Q = n(n+2)\sum_{k=1}^{h}\dfrac{\hat{\rho}_k^{\,2}}{n-k}")],
        simbolos=[(r"\hat{\rho}_k", "autocorrelación con retardo k")]),
    "mann_kendall": Formula(
        que="Prueba si una serie tiene tendencia y estima su pendiente.",
        general=[("Estadístico S", r"S = \sum_{i<j}\mathrm{sgn}\left(x_j - x_i\right)"),
                 ("Pendiente de Sen", r"\beta = \mathrm{mediana}\left(\dfrac{x_j-x_i}{j-i}\right)")]),
    "chi2": Formula(
        que="Prueba si dos variables categóricas están asociadas.",
        general=[("Esperado", r"E_{ij} = \dfrac{\mathrm{total\ fila}_i\cdot\mathrm{total\ columna}_j}{N}"),
                 ("Estadístico χ²",
                  r"\chi^2 = \sum_{i}\sum_{j}\dfrac{\left(O_{ij}-E_{ij}\right)^2}{E_{ij}}")],
        simbolos=[(r"O_{ij}", "observado en la celda"), (r"E_{ij}", "esperado si no hubiera asociación")],
        sustituir=_s_chi2),
    "fisher": Formula(
        que="Prueba exacta de asociación para tablas 2×2 con frecuencias chicas.",
        general=[("Probabilidad de una tabla",
                  r"P = \dfrac{\binom{a+b}{a}\binom{c+d}{c}}{\binom{n}{a+c}}"),
                 ("Odds ratio", r"OR = \dfrac{a\cdot d}{b\cdot c}")],
        simbolos=[(r"a,b,c,d", "las cuatro celdas de la tabla")],
        iterativo=True,
        pasos=["Fija los totales de filas y columnas.",
               "Calcula la probabilidad de cada tabla posible con esos totales.",
               "Suma las tablas igual o más extremas que la observada: ese es el p."],
        sustituir=_s_fisher),
    "chi2_montecarlo": Formula(
        que="χ² con el p estimado por simulación cuando la aproximación no es confiable.",
        general=[("p por simulación",
                  r"p = \dfrac{1 + \#\left\{\chi^2_{\mathrm{sim}} \geq \chi^2_{\mathrm{obs}}\right\}}{B+1}")],
        simbolos=[(r"B", "cantidad de tablas simuladas")],
        iterativo=True,
        pasos=["Calcula el χ² de la tabla observada.",
               "Simula B tablas con los mismos totales de fila y columna.",
               "Cuenta cuántas tienen un χ² igual o mayor y aplica la fórmula del p."]),
    # ------------------------------------------------------ Concordancia
    "score_comparacion": Formula(
        que="Puntaje que sugiere si dos columnas miden lo mismo (comparación de métodos).",
        general=[("Puntaje", r"S = \sum_{i} w_i\,c_i")],
        simbolos=[(r"c_i", "1 si se cumple la regla i"), (r"w_i", "peso configurable de la regla")]),
    "variabilidad_diferencias": Formula(
        que="Mide cuánto varían las diferencias entre métodos.",
        general=[("Diferencias", r"d_i = y_i - x_i"),
                 ("Desvío de las diferencias",
                  r"s_d = \sqrt{\dfrac{\sum\left(d_i-\bar{d}\right)^2}{n-1}}"),
                 ("CV de las diferencias", r"CV_d = \dfrac{s_d}{\bar{m}}\times 100\ \%")],
        simbolos=[(r"\bar{m}", "promedio de ambos métodos")]),
    "estructura_diferencia": Formula(
        que="Prueba si el sesgo cambia con la concentración.",
        general=[("Recta de las diferencias", r"d_i = \beta_0 + \beta_1\,m_i"),
                 ("Promedio", r"m_i = \dfrac{x_i+y_i}{2}")]),
    "ba_escala_porcentual": Formula(
        que="Bland-Altman con diferencias relativas, cuando el error crece con el nivel.",
        general=[("Diferencia porcentual", r"d_i^{\%} = \dfrac{y_i-x_i}{(x_i+y_i)/2}\times 100")]),
    "normalidad_diferencias": Formula(
        que="Prueba si las diferencias entre métodos siguen una campana.",
        general=[("Estadístico W sobre las diferencias",
                  r"W = \dfrac{\left(\sum a_i\,d_{(i)}\right)^2}{\sum\left(d_i-\bar{d}\right)^2}")],
        iterativo=True,
        pasos=["Calcula las diferencias d<sub>i</sub>.",
               "Aplica Shapiro-Wilk a las diferencias (pesos a<sub>i</sub> por aproximación de Royston)."]),
    "ba_parametrico": Formula(
        que="Sesgo y límites de acuerdo entre dos métodos, con diferencias normales.",
        general=[("Sesgo", r"\bar{d} = \dfrac{1}{n}\sum_{i=1}^{n} d_i"),
                 ("Límites de acuerdo", r"\bar{d} \pm 1.96\,s_d")],
        simbolos=[(r"d_i", "diferencia entre métodos"), (r"s_d", "desvío de las diferencias")],
        sustituir=_s_ba),
    "ba_no_parametrico": Formula(
        que="Sesgo y límites de acuerdo sin suponer campana.",
        general=[("Sesgo", r"\tilde{d} = \mathrm{mediana}(d_i)"),
                 ("Límites", r"\left[P_{2.5}(d),\ P_{97.5}(d)\right]")]),
    "ba_eje_referencia": Formula(
        que="Bland-Altman contra el método de referencia en el eje X (Krouwer).",
        general=[("Eje X", r"x_i\ \ \mathrm{(referencia)}\ \ \mathrm{en\ vez\ de}\ \ \dfrac{x_i+y_i}{2}")]),
    "deming": Formula(
        que="Recta entre dos métodos cuando ambos tienen error.",
        general=[("Pendiente",
                  r"\beta_1 = \dfrac{s_{yy} - \lambda s_{xx} + "
                  r"\sqrt{\left(s_{yy}-\lambda s_{xx}\right)^2 + 4\lambda s_{xy}^2}}{2\,s_{xy}}"),
                 ("Intercepto", r"\beta_0 = \bar{y} - \beta_1\bar{x}")],
        simbolos=[(r"\lambda", "cociente de varianzas de error de los métodos"),
                  (r"s_{xx},\ s_{yy},\ s_{xy}", "sumas de cuadrados y productos cruzados")]),
    "deming_ponderado": Formula(
        que="Deming con pesos, cuando el error es proporcional al nivel (CV constante).",
        general=[("Pesos", r"w_i = \dfrac{1}{\left(\frac{x_i+y_i}{2}\right)^2}")],
        iterativo=True,
        pasos=["Estima una recta inicial.",
               "Recalcula los pesos con los valores ajustados.",
               "Reestima la recta con esos pesos y repite hasta que no cambie."]),
    "passing_bablok": Formula(
        que="Recta robusta entre dos métodos basada en la mediana de las pendientes.",
        general=[("Pendientes de a pares", r"S_{ij} = \dfrac{y_j - y_i}{x_j - x_i}"),
                 ("Pendiente", r"b = \mathrm{mediana\ desplazada}\left(S_{ij}\right)"),
                 ("Intercepto", r"a = \mathrm{mediana}\left(y_i - b\,x_i\right)")],
        iterativo=True,
        pasos=["Calcula la pendiente de cada par de puntos (S<sub>ij</sub>).",
               "Descarta las pendientes iguales a −1.",
               "Desplaza la mediana según cuántas pendientes son menores que −1 (K).",
               "La pendiente es esa mediana desplazada; el intercepto, la mediana de y − b·x.",
               "El IC sale de rangos de las pendientes ordenadas."]),
    "sesgo_niveles": Formula(
        que="Sesgo esperado en los niveles de decisión médica.",
        general=[("Sesgo en el nivel X_c", r"\hat{y}_c - X_c = \beta_0 + (\beta_1 - 1)\,X_c")]),
    "ccc": Formula(
        que="Concordancia de Lin: precisión y exactitud a la vez (1 = acuerdo perfecto).",
        general=[("CCC", r"\rho_c = \dfrac{2\,s_{xy}}{s_x^2 + s_y^2 + \left(\bar{x}-\bar{y}\right)^2}")]),
    "ccc_descomposicion": Formula(
        que="Separa el CCC en correlación (precisión) y corrección de sesgo (exactitud).",
        general=[("Descomposición", r"\rho_c = \rho\cdot C_b"),
                 ("Exactitud",
                  r"C_b = \dfrac{2}{v + \dfrac{1}{v} + u^2},\quad v = \dfrac{s_x}{s_y},\quad "
                  r"u = \dfrac{\bar{x}-\bar{y}}{\sqrt{s_x s_y}}")]),
    # ------------------------------------------------------ Multivariado
    "matriz_correlacion": Formula(
        que="Correlación entre cada par de columnas, eligiendo Pearson o Spearman por celda.",
        general=[("Cada celda", r"r_{jk} = \mathrm{corr}\left(X_j,\ X_k\right)")]),
    "fdr_bh": Formula(
        que="Ajusta los p cuando se hacen muchas pruebas a la vez (Benjamini-Hochberg).",
        general=[("p ajustado",
                  r"p^{\mathrm{aj}}_{(i)} = \min_{j \geq i}\left(\dfrac{m}{j}\,p_{(j)}\right)")],
        simbolos=[(r"p_{(j)}", "p ordenados de menor a mayor"), (r"m", "número de pruebas")]),
    "regresion_multiple": Formula(
        que="Explica una variable objetivo con varias predictoras a la vez.",
        general=[("Modelo", r"y = \beta_0 + \beta_1 x_1 + \cdots + \beta_p x_p + \varepsilon"),
                 ("Estimación", r"\hat{\beta} = \left(X^{T}X\right)^{-1}X^{T}y")]),
    "vif": Formula(
        que="Detecta predictoras redundantes entre sí (multicolinealidad).",
        general=[("VIF", r"VIF_j = \dfrac{1}{1 - R_j^2}")],
        simbolos=[(r"R_j^2", "R² de explicar x_j con las demás predictoras")]),
    "pca": Formula(
        que="Resume muchas variables en pocos componentes que conservan la variabilidad.",
        general=[("Componentes", r"\Sigma\,v_k = \lambda_k\,v_k"),
                 ("Varianza explicada", r"\dfrac{\lambda_k}{\sum_j \lambda_j}")],
        iterativo=True,
        pasos=["Estandariza las variables.",
               "Calcula la matriz de correlación Σ.",
               "Obtiene sus autovalores λ y autovectores v (descomposición numérica).",
               "Ordena los componentes por varianza explicada."]),
    "clustering": Formula(
        que="Agrupa las filas en k grupos parecidos (exploratorio).",
        general=[("Objetivo", r"\min\ \sum_{j=1}^{k}\ \sum_{x\in C_j}\left\|x-\mu_j\right\|^2")],
        simbolos=[(r"\mu_j", "centro del grupo j")],
        iterativo=True,
        pasos=["Elige k centros iniciales.",
               "Asigna cada fila al centro más cercano.",
               "Recalcula cada centro como el promedio de su grupo.",
               "Repite hasta que los grupos no cambien; elige k por silueta."]),
}


# ---------------------------------------------------------------- texto → id
_CLAVES = [
    ("anderson", "anderson"), ("shapiro", "shapiro"), ("levene", "levene"),
    ("games", "games_howell"), ("tukey hsd", "tukey_hsd"), ("hsd", "tukey_hsd"),
    ("dunn", "dunn"), ("student", "t_student"),
    ("mann-whitney", "mann_whitney"), ("kruskal", "kruskal"),
    ("pearson", "pearson"), ("spearman", "spearman"),
    ("exacto de fisher", "fisher"), ("fisher", "fisher"),
    ("monte", "chi2_montecarlo"), ("simulaci", "chi2_montecarlo"),
    ("chi", "chi2"), ("χ²", "chi2"), ("ljung", "autocorrelacion"),
    ("mann-kendall", "mann_kendall"), ("passing", "passing_bablok"),
    ("deming", "deming"), ("ccc", "ccc"), ("benjamini", "fdr_bh"),
    ("vif", "vif"), ("regresión múltiple", "regresion_multiple"),
    ("pca", "pca"), ("kmeans", "clustering"),
]


def ensayo_de_texto(texto: str) -> str | None:
    """Adivina qué ensayo del catálogo describe un texto del árbol por caso."""
    t = (texto or "").lower()
    if "welch" in t:
        return "anova_welch" if "anova" in t else "t_welch"
    if "bland" in t:
        return "ba_no_parametrico" if "no param" in t else "ba_parametrico"
    for clave, id_ in _CLAVES:
        if clave in t:
            return id_
    if "anova" in t:
        return "anova"
    return None
