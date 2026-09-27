"""Fórmula y referencias de cada análisis, en una tabla y no en cada rama.

Antes cada análisis escribía su fórmula a mano en `_set_formula`, sin cita, y
el informe guardado no la llevaba. Acá cada análisis migrado a `Resultado`
tiene su ficha, y `tests/test_bland_resultado.py` exige que exista.

Las referencias salen de `docs/referencia-medcalc/` (que trae la URL del manual
de MedCalc de donde se tomó cada fórmula) y de las que el core ya citaba en sus
docstrings. La fórmula describe lo que calcula el core, no lo que dice un libro:
si el core cambia, esta ficha cambia con él.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.resultado.modelo import Cita


@dataclass(frozen=True)
class Ficha:
    formula: str
    citas: tuple[Cita, ...]


BLAND_1986 = Cita("Bland JM, Altman DG (1986). Statistical methods for assessing "
                  "agreement between two methods of clinical measurement. "
                  "Lancet i:307-310.")
BLAND_1999 = Cita("Bland JM, Altman DG (1999). Measuring agreement in method "
                  "comparison studies. Stat Methods Med Res 8:135-160. Límites no "
                  "paramétricos e IC de los límites.")
KROUWER_2008 = Cita("Krouwer JS (2008). Why Bland-Altman plots should use X, not "
                    "(Y+X)/2 when X is a reference method. Stat Med 27:778-780.")
CLSI_EP09 = Cita("CLSI (2018). EP09c: Measurement procedure comparison and bias "
                 "estimation using patient samples, 3.ª ed.")
SHAPIRO_1965 = Cita("Shapiro SS, Wilk MB (1965). An analysis of variance test for "
                    "normality (complete samples). Biometrika 52:591-611.")
LIN_1989 = Cita("Lin LI (1989). A concordance correlation coefficient to evaluate "
                "reproducibility. Biometrics 45:255-268.")
MCBRIDE_2005 = Cita("McBride GB (2005). A proposal for strength-of-agreement criteria "
                    "for Lin's concordance correlation coefficient. NIWA Client Report "
                    "HAM2005-062.")
MEDCALC_BLAND = Cita("MedCalc, manual: Bland-Altman plot.",
                     "https://www.medcalc.org/en/manual/bland-altman-plot.php")
PASSING_1983 = Cita("Passing H, Bablok W (1983). A new biometrical procedure for testing "
                    "the equality of measurements from two different analytical methods. "
                    "J Clin Chem Clin Biochem 21:709-720.")
BABLOK_1985 = Cita("Bablok W, Passing H (1985). Application of statistical procedures in "
                   "analytical instrument testing. J Automat Chem 7:74-79. Tamaño de "
                   "muestra.")
MAYER_2016 = Cita("Mayer B, Gaus W, Braisch U (2016). The fallacy of the Passing-Bablok "
                  "regression. Jökull 66:95-106.")
MEDCALC_PASSING = Cita("MedCalc, manual: Passing-Bablok regression.",
                       "https://www.medcalc.org/en/manual/passing-bablok-regression.php")
NCSS_PASSING = Cita("NCSS, manual: Passing-Bablok Regression for Method Comparison "
                    "(cap. 313), prueba Cusum de linealidad.",
                    "https://www.ncss.com/wp-content/themes/ncss/pdf/Procedures/NCSS/"
                    "Passing-Bablok_Regression_for_Method_Comparison.pdf")
CORNBLEET_1979 = Cita("Cornbleet PJ, Gochman N (1979). Incorrect least-squares regression "
                      "coefficients in method-comparison analysis. Clin Chem 25:432-438.")
LINNET_1990 = Cita("Linnet K (1990). Estimation of the linear relationship between the "
                   "measurements of two methods with proportional errors. Stat Med "
                   "9:1463-1473.")
LINNET_1993 = Cita("Linnet K (1993). Evaluation of regression procedures for methods "
                   "comparison studies. Clin Chem 39:424-432.")
MEDCALC_DEMING = Cita("MedCalc, manual: Deming regression.",
                      "https://www.medcalc.org/en/manual/deming-regression.php")
HYSLOP_2009 = Cita("Hyslop NP, White WH (2009). Estimating precision using duplicate "
                   "measurements. J Air Waste Manag Assoc 59:1032-1039.")
BLAND_ALTMAN_1996 = Cita("Bland JM, Altman DG (1996). Statistics notes: measurement error "
                         "proportional to the mean. BMJ 313:106.")
BLAND_2006 = Cita("Bland M (2006). How should I calculate a within-subject coefficient of "
                  "variation?", "https://www-users.york.ac.uk/~mb55/meas/cv.htm")
JONES_1997 = Cita("Jones R, Payne B (1997). Clinical investigation and statistics in "
                  "laboratory medicine. London: ACB Venture Publications.")
MEDCALC_CVDUP = Cita("MedCalc, manual: Coefficient of variation from duplicate measurements.",
                     "https://www.medcalc.org/en/manual/cvfromduplicates.php")
MCGRAW_1996 = Cita("McGraw KO, Wong SP (1996). Forming inferences about some intraclass "
                   "correlation coefficients. Psychol Methods 1:30-46.")
SHROUT_1979 = Cita("Shrout PE, Fleiss JL (1979). Intraclass correlations: uses in assessing "
                   "rater reliability. Psychol Bull 86:420-428.")
KOO_2016 = Cita("Koo TK, Li MY (2016). A guideline of selecting and reporting intraclass "
                "correlation coefficients for reliability research. J Chiropr Med "
                "15:155-163.")
MEDCALC_ICC = Cita("MedCalc, manual: Intraclass correlation coefficient.",
                   "https://www.medcalc.org/en/manual/intraclass-correlation-coefficient.php")
MEDCALC_BA_MULTIPLE = Cita("MedCalc, manual: Bland-Altman plot with multiple methods.",
                           "https://www.medcalc.org/en/manual/blandaltmanmultiple.php")


FICHAS: dict[str, Ficha] = {
    # docs/referencia-medcalc/Comparacion de metodos y concordancia.md,
    # secciones "Bland-Altman plot"; core: src/core/bland_altman.py
    "bland_altman": Ficha(
        formula=(
            "d = método en prueba − referencia (sin referencia: Variable 1 − Variable 2)\n"
            "    en %: d = 100·(diferencia)/eje, cuando el CV es constante (EP09c §5.4.2)\n"
            "Sesgo = d̄ (media de d)    s = DE de d, con n − 1\n"
            "Sesgo % = d̄ / media de la referencia × 100 (sin referencia: del promedio)\n"
            "LoA paramétricos = d̄ ± 1,96·s\n"
            "IC 95 % del sesgo = d̄ ± t(n−1) · s/√n\n"
            "IC 95 % de cada LoA = LoA ± t(n−1) · s · √(1/n + 1,96²/(2(n−1)))\n"
            "LoA no paramétricos = percentiles 2,5 y 97,5 de d (centro: mediana de d)\n"
            "Sesgo proporcional = pendiente de d contra el eje X: el promedio\n"
            "    (x₁ + x₂)/2, o el método de referencia si se declaró uno\n"
            "CCC de Lin: ρc = 2·s₁₂ / (s₁² + s₂² + (x̄₁ − x̄₂)²) = ρ · Cb\n"
            "    con momentos poblacionales; IC 95 % por la z de Fisher"
        ),
        citas=(BLAND_1986, BLAND_1999, KROUWER_2008, CLSI_EP09, SHAPIRO_1965,
               LIN_1989, MCBRIDE_2005, MEDCALC_BLAND),
    ),
    # docs/referencia-medcalc/Comparacion de metodos y concordancia.md,
    # "Passing-Bablok regression"; core: src/core/passing_bablok.py
    "passing_bablok": Ficha(
        formula=(
            "y = A + B·x    x = comparativo (Variable 1), y = en prueba (Variable 2)\n"
            "Sᵢⱼ = (yⱼ − yᵢ)/(xⱼ − xᵢ) para cada par; pares con xᵢ = xⱼ: ±∞ según el\n"
            "    signo de yⱼ − yᵢ (EP09c, apéndice I2); se descartan las Sᵢⱼ = −1\n"
            "K = número de Sᵢⱼ < −1;  B = mediana de las Sᵢⱼ corrida K lugares\n"
            "A = mediana de (yᵢ − B·xᵢ)\n"
            "IC 95 % de B: estadísticos de orden M₁ + K y M₂ + K, con\n"
            "    C = 1,96·√(n(n−1)(2n+5)/18),  M₁ = redondeo((N − C)/2),  M₂ = N − M₁ + 1\n"
            "IC 95 % de A: mediana de (y − B·x) con los extremos del IC de B\n"
            "RSD = DE de los residuos;  sesgo en Xc = A + (B − 1)·Xc\n"
            "Cusum de linealidad: r = +√(n₋/n₊) arriba de la recta, −√(n₊/n₋) abajo;\n"
            "    orden por D = (y + x/B − A)/√(1 + 1/B²);  H = máx|Σr| / √(n₋ + 1)\n"
            "    contra la distribución de Kolmogorov-Smirnov (1,36 al 5 %)"
        ),
        citas=(PASSING_1983, BABLOK_1985, CLSI_EP09, MAYER_2016, MEDCALC_PASSING,
               NCSS_PASSING),
    ),
    # "Deming regression"; core: src/core/agreement.py
    "deming": Ficha(
        formula=(
            "λ = varianza del error de x / varianza del error de y (1 si no se conoce)\n"
            "b = [(λ·q − u) + √((u − λ·q)² + 4·λ·p²)] / (2·λ·p),  a = ȳ − b·x̄\n"
            "    u, q, p = sumas de cuadrados de x, de y y de productos cruzados\n"
            "Ponderado (CV constante): las mismas sumas con pesos wᵢ = 1/zᵢ²,\n"
            "    zᵢ = (X̂ᵢ + λ·Ŷᵢ)/(1 + λ), iterando hasta que b no cambia (EP09c, apéndice B)\n"
            "IC 95 %: jackknife, estimación ± t(N−2)·EE (EP09c, apéndice K1)\n"
            "Sesgo en Xc = a + (b − 1)·Xc"
        ),
        citas=(CORNBLEET_1979, LINNET_1990, LINNET_1993, CLSI_EP09, MEDCALC_DEMING),
    ),
    # docs/referencia-medcalc/Control de calidad y variabilidad analitica.md,
    # "Coefficient of variation from duplicate measurements"; core: agreement.py
    "cv_duplicados": Ficha(
        formula=(
            "d = x₁ − x₂,  m = (x₁ + x₂)/2,  n = número de pares\n"
            "DE intrasujeto = √(Σd² / 2n);  CV = 100·DE / media global\n"
            "CV, raíz cuadrática media = 100·√(Σ(d/m)² / 2n)\n"
            "CV, logarítmico = 100·(exp(√(Σ(ln x₁ − ln x₂)² / 2n)) − 1)\n"
            "IC 95 % de cada DE: s·√(n/χ²(0,975; n)) a s·√(n/χ²(0,025; n))"
        ),
        citas=(JONES_1997, HYSLOP_2009, BLAND_ALTMAN_1996, BLAND_2006, MEDCALC_CVDUP),
    ),
    # docs/referencia-medcalc/Correlacion, acuerdo y confiabilidad.md; core: pingouin
    "icc": Ficha(
        formula=(
            "ICC(A,1) = (MS_suj − MS_err) / (MS_suj + (k−1)·MS_err + k·(MS_mét − MS_err)/n)\n"
            "ICC(C,1) = (MS_suj − MS_err) / (MS_suj + (k−1)·MS_err)\n"
            "dos vías; k = 2 métodos, n = sujetos\n"
            "Lectura por el IC 95 % (Koo y Li 2016): < 0,5 pobre, 0,5-0,75 moderada,\n"
            "    0,75-0,9 buena, > 0,9 excelente"
        ),
        citas=(MCGRAW_1996, SHROUT_1979, KOO_2016, MEDCALC_ICC),
    ),
    # "Bland-Altman plot with multiple methods"; core: src/core/bland_altman.py
    "bland_altman_multiple": Ficha(
        formula=(
            "Para cada método: d = método − referencia, contra la referencia (Krouwer 2008)\n"
            "Sesgo = d̄;  LoA = d̄ ± 1,96·s\n"
            "IC 95 % del sesgo = d̄ ± t(n−1)·s/√n\n"
            "IC 95 % de cada LoA = LoA ± t(n−1)·s·√(1/n + 1,96²/(2(n−1)))"
        ),
        citas=(BLAND_1986, BLAND_1999, KROUWER_2008, MEDCALC_BA_MULTIPLE),
    ),
}


def ficha(analisis: str) -> Ficha:
    try:
        return FICHAS[analisis]
    except KeyError:
        raise KeyError(f"El análisis «{analisis}» no tiene ficha en src/resultado/citas.py: "
                       "todo análisis migrado a Resultado lleva fórmula y cita.") from None
