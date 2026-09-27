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
CLSI_EP15 = Cita("CLSI (2014). EP15-A3: User verification of precision and estimation of "
                 "bias, 3.ª ed.")
CLSI_EP15_ERRATA_2015 = Cita("CLSI (2015). EP15-A3, fe de erratas del 22 oct: tabla 10 y "
                             "ejemplos resueltos 1A a 4.",
                             "https://clsi.org/media/1664/ep15_correction_notice_20151008_pdf_web.pdf")
CLSI_EP15_ERRATA_2017 = Cita("CLSI (2017). EP15-A3, fe de erratas del 23 may: ecuación (11) "
                             "y apéndice B5.",
                             "https://clsi.org/media/1649/ep15_correction_notice_20170523_web.pdf")
GRUBBS_1969 = Cita("Grubbs FE (1969). Procedures for detecting outlying observations in "
                   "samples. Technometrics 11:1-21.")
MEDCALC_SUMMARY = Cita("MedCalc, manual: Summary statistics.",
                       "https://www.medcalc.org/en/manual/summary-statistics.php")
MEDCALC_OUTLIERS = Cita("MedCalc, manual: Outlier detection.",
                        "https://www.medcalc.org/en/manual/outliers.php")
ALTMAN_1980 = Cita("Altman DG (1980). Statistics and ethics in medical research. VI - "
                   "Presentation of results. BMJ 281:1542-1544.")
ALTMAN_1983 = Cita("Altman DG, Gore SM, Gardner MJ, Pocock SJ (1983). Statistical guidelines "
                   "for contributors to medical journals. BMJ 286:1489-1493.")
ALTMAN_1991 = Cita("Altman DG (1991). Practical statistics for medical research. London: "
                   "Chapman and Hall.")
DAGOSTINO_1990 = Cita("D'Agostino RB, Belanger A, D'Agostino RB Jr (1990). A suggestion for "
                      "using powerful and informative tests of normality. Am Stat 44:316-321.")
ANSCOMBE_1983 = Cita("Anscombe FJ, Glynn WJ (1983). Distribution of the kurtosis statistic b2 "
                     "for normal samples. Biometrika 70:227-234.")
WESTFALL_2014 = Cita("Westfall PH (2014). Kurtosis as peakedness, 1905-2014. R.I.P. Am Stat "
                     "68:191-195.")
HYNDMAN_1996 = Cita("Hyndman RJ, Fan Y (1996). Sample quantiles in statistical packages. Am "
                    "Stat 50:361-365. Definición 6: rango p(n+1).")
CLSI_EP28 = Cita("CLSI (2010). EP28-A3c: Defining, establishing, and verifying reference "
                 "intervals in the clinical laboratory, 3.ª ed.")
TUKEY_1963 = Cita("Tukey JW, McLaughlin DH (1963). Less vulnerable confidence and significance "
                  "procedures for location based on a single sample: trimming/winsorization. "
                  "Sankhyā A 25:331-352.")
WILCOX_2012 = Cita("Wilcox RR (2012). Introduction to robust estimation and hypothesis "
                   "testing, 3.ª ed. Academic Press.")
ROYSTON_1995 = Cita("Royston P (1995). Remark AS R94: a remark on algorithm AS 181, the "
                    "W-test for normality. Appl Stat 44:547-551.")
ROSNER_1983 = Cita("Rosner B (1983). Percentage points for a generalized ESD many-outlier "
                   "procedure. Technometrics 25:165-172.")
TUKEY_1977 = Cita("Tukey JW (1977). Exploratory data analysis. Reading, MA: Addison-Wesley.")
NIST_OUTLIERS = Cita("NIST/SEMATECH e-Handbook of Statistical Methods, §1.3.5.17: Grubbs y "
                     "ESD generalizado.",
                     "https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm")
EFRON_1993 = Cita("Efron B, Tibshirani RJ (1993). An introduction to the bootstrap. New "
                  "York: Chapman & Hall. Cap. 11: el jackknife no sirve para la mediana.")
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
    # core: src/core/ep15.py; tests contra la tabla 10 y los ejemplos 1A, 3A y 4
    "precision_ep15": Ficha(
        formula=(
            "D corridas, nᵢ réplicas, N = Σnᵢ;  MS1 = entre corridas (D − 1 gl),\n"
            "    MS2 = dentro de la corrida (N − D gl)\n"
            "n0 = (N − Σnᵢ²/N) / (D − 1)  (= réplicas por corrida si está balanceado)\n"
            "V_B = (MS1 − MS2)/n0, 0 si sale negativa;  s_R = √MS2;  s_WL = √(MS2 + V_B)\n"
            "UVL = F·σ declarada,  F = √(χ²(1 − α/nMuestras; gl)/gl)\n"
            "    gl de s_R = N − D; gl de s_WL por Satterthwaite con ρ = σWL/σR (ap. B)\n"
            "se(x̿) = √((s_WL² − ((n0 − 1)/n0)·s_R²)/D),  D − 1 gl\n"
            "se_c = √(se_VA² + se(x̿)²), gl por Satterthwaite\n"
            "Intervalo de verificación = VA ± t(1 − α/(2·nMuestras); gl)·se_c"
        ),
        citas=(CLSI_EP15, CLSI_EP15_ERRATA_2015, CLSI_EP15_ERRATA_2017, GRUBBS_1969),
    ),
    # core: src/core/ep09.py; arma: src/resultado/constructores/validacion.py
    "validar_metodo": Ficha(
        formula=(
            "x = comparativo, y = en prueba, sesgo = y − x (EP09c, tabla 1)\n"
            "Recta (EP09c §6.2): DE constante y diferencias normales → Deming;\n"
            "    CV constante y diferencias normales → Deming ponderado;\n"
            "    variabilidad mixta o diferencias no normales → Passing-Bablok\n"
            "Sesgo en Xc = a + (b − 1)·Xc  (EP09c §6.3)\n"
            "IC 95 %: Deming, jackknife con t(N−2); Passing-Bablok, bootstrap percentil\n"
            "Permitido en Xc = permitido % · Xc / 100 (o fijo, en unidades)\n"
            "Cumple: IC entero dentro de ±permitido; no cumple: IC entero afuera;\n"
            "    no concluyente: el IC cruza el límite\n"
            "Precisión (si hay corridas): EP15-A3, ver su ficha"
        ),
        citas=(CLSI_EP09, CLSI_EP15, KROUWER_2008, PASSING_1983, LINNET_1990, EFRON_1993),
    ),

    # ---------------- Resumen y distribución: src/resultado/constructores/resumen.py
    # docs/referencia-medcalc/Control de calidad y variabilidad analitica.md,
    # "Summary statistics" y "Outlier detection"; core: src/core/statistics.py,
    # src/core/reference.py, src/core/outliers.py
    "descriptivas": Ficha(
        formula=(
            "x̄ = Σx / n;  s = √(Σ(x − x̄)² / (n − 1));  EE = s / √n\n"
            "IC 95 % de la media = x̄ ± t(0,975; n − 1)·EE\n"
            "CV = 100·s / x̄;  RIC = P75 − P25, percentiles por rango p(n + 1) como en EP28\n"
            "Rango del 95 % de los datos, si son normales: x̄ ± 1,96·s"
        ),
        citas=(MEDCALC_SUMMARY, ALTMAN_1980, ALTMAN_1991, SHAPIRO_1965),
    ),
    "asimetria_curtosis": Ficha(
        formula=(
            "g₁ = m₃ / m₂^(3/2);  exceso de curtosis g₂ = m₄ / m₂² − 3\n"
            "    mₖ = Σ(x − x̄)ᵏ / n  (0 en los dos para una normal)\n"
            "Asimetría: z de D'Agostino (normal ya con n ≥ 8)\n"
            "Curtosis: z de Anscombe y Glynn (poco confiable con n < 20)"
        ),
        citas=(DAGOSTINO_1990, ANSCOMBE_1983, WESTFALL_2014, MEDCALC_SUMMARY),
    ),
    "percentiles": Ficha(
        formula=(
            "Pₚ = valor en el rango p·(n + 1)/100, interpolando entre vecinos\n"
            "    (definición 6 de Hyndman y Fan; la de EP28)\n"
            "Solo existe si 1 ≤ p·(n + 1)/100 ≤ n: P5 y P95 piden n ≥ 19\n"
            "IC 95 %: bootstrap percentil, 2000 remuestras, semilla fija"
        ),
        citas=(HYNDMAN_1996, CLSI_EP28, MEDCALC_SUMMARY, EFRON_1993),
    ),
    "media_recortada": Ficha(
        formula=(
            "g = 10 % de cada cola;  k = ⌊g·n⌋ datos fuera de cada lado;  h = n − 2k\n"
            "Media recortada = media de los h datos del medio\n"
            "EE = s_w / ((1 − 2g)·√n),  s_w = DE de la muestra winsorizada\n"
            "IC 95 % = media recortada ± t(0,975; h − 1)·EE"
        ),
        citas=(TUKEY_1963, WILCOX_2012),
    ),
    "media_geometrica": Ficha(
        formula=(
            "MG = exp(Σ ln x / n) = (x₁·x₂·…·xₙ)^(1/n);  solo con x > 0\n"
            "IC 95 % = exp(media(ln x) ± t(0,975; n − 1)·DE(ln x)/√n)"
        ),
        citas=(MEDCALC_SUMMARY, ALTMAN_1983),
    ),
    "media_armonica": Ficha(
        formula="MH = n / Σ(1/x);  solo con x > 0",
        citas=(MEDCALC_SUMMARY,),
    ),
    "shapiro_wilk": Ficha(
        formula=(
            "W = (Σ aᵢ·x₍ᵢ₎)² / Σ(xᵢ − x̄)²,  x₍ᵢ₎ = datos ordenados\n"
            "aᵢ y el p: algoritmo de Royston (AS R94), válido de 3 a 5000 datos\n"
            "Con más de 5000, se prueba una submuestra de 5000 (semilla fija)"
        ),
        citas=(SHAPIRO_1965, ROYSTON_1995, MEDCALC_SUMMARY),
    ),
    "grubbs": Ficha(
        formula=(
            "G = máx |xᵢ − x̄| / s  (dos colas)\n"
            "G crítico = ((n − 1)/√n)·√(t² / (n − 2 + t²)),  t = t(1 − α/(2n); n − 2)\n"
            "p: la misma relación invertida, con la cota de Bonferroni 2n"
        ),
        citas=(GRUBBS_1969, NIST_OUTLIERS, MEDCALC_OUTLIERS),
    ),
    "tukey": Ficha(
        formula=(
            "RIC = P75 − P25\n"
            "Vallas internas («outside»): P25 − 1,5·RIC y P75 + 1,5·RIC\n"
            "Vallas externas («far out»): P25 − 3·RIC y P75 + 3·RIC"
        ),
        citas=(TUKEY_1977, MEDCALC_OUTLIERS),
    ),
    "esd": Ficha(
        formula=(
            "Para i = 1…r:  Rᵢ = máx |x − x̄| / s sobre los datos que quedan, y se saca ese\n"
            "λᵢ = (n − i)·t / √((n − i − 1 + t²)(n − i + 1)),  t = t(1 − α/(2(n − i + 1)); n − i − 1)\n"
            "Atípicos = los primeros k, con k el MAYOR i tal que Rᵢ > λᵢ\n"
            "r = mín(10, ⌊(n − 2)/2⌋), α = 0,05"
        ),
        citas=(ROSNER_1983, NIST_OUTLIERS, MEDCALC_OUTLIERS),
    ),
}


def ficha(analisis: str) -> Ficha:
    try:
        return FICHAS[analisis]
    except KeyError:
        raise KeyError(f"El análisis «{analisis}» no tiene ficha en src/resultado/citas.py: "
                       "todo análisis migrado a Resultado lleva fórmula y cita.") from None
