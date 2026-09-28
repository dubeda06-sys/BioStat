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
WESTGARD_1974 = Cita("Westgard JO, Carey RN, Wold S (1974). Criteria for judging "
                     "precision and accuracy in method development and evaluation. "
                     "Clin Chem 20:825-833.")
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
FISHER_1921 = Cita("Fisher RA (1921). On the probable error of a coefficient of correlation "
                   "deduced from a small sample. Metron 1:3-32.")
SPEARMAN_1904 = Cita("Spearman C (1904). The proof and measurement of association between "
                     "two things. Am J Psychol 15:72-101.")
BONETT_2000 = Cita("Bonett DG, Wright TA (2000). Sample size requirements for estimating "
                   "Pearson, Kendall and Spearman correlations. Psychometrika 65:23-28.")
MUKAKA_2012 = Cita("Mukaka MM (2012). A guide to appropriate use of correlation coefficient "
                   "in medical research. Malawi Med J 24:69-71.")
MEDCALC_CORRELACION = Cita("MedCalc, manual: Correlation.",
                           "https://www.medcalc.org/en/manual/correlation.php")
MEDCALC_RANGOS = Cita("MedCalc, manual: Rank correlation.",
                      "https://www.medcalc.org/en/manual/rank-correlation.php")
MEDCALC_PARCIAL = Cita("MedCalc, manual: Partial correlation.",
                       "https://www.medcalc.org/en/manual/partialcorrelation.php")
RAMSEY_1969 = Cita("Ramsey JB (1969). Tests for specification errors in classical linear "
                   "least-squares regression analysis. J R Stat Soc B 31:350-371.")
BREUSCH_1979 = Cita("Breusch TS, Pagan AR (1979). A simple test for heteroscedasticity and "
                    "random coefficient variation. Econometrica 47:1287-1294.")
DRAPER_1998 = Cita("Draper NR, Smith H (1998). Applied regression analysis, 3.ª ed. New York: "
                   "Wiley.")
PEDUZZI_1996 = Cita("Peduzzi P, Concato J, Kemper E, Holford TR, Feinstein AR (1996). A "
                    "simulation study of the number of events per variable in logistic "
                    "regression analysis. J Clin Epidemiol 49:1373-1379.")
HOSMER_1980 = Cita("Hosmer DW, Lemeshow S (1980). Goodness of fit tests for the multiple "
                   "logistic regression model. Commun Stat A 9:1043-1069.")
FINNEY_1971 = Cita("Finney DJ (1971). Probit analysis, 3.ª ed. Cambridge University Press.")
VENABLES_2002 = Cita("Venables WN, Ripley BD (2002). Modern applied statistics with S, 4.ª ed. "
                     "Springer. `dose.p`: dosis efectiva con IC por el método delta.")
CLSI_EP17 = Cita("CLSI (2012). EP17-A2: Evaluation of detection capability for clinical "
                 "laboratory measurement procedures, 2.ª ed. LoD por probit.")
STUDENT_1908 = Cita("Student (1908). The probable error of a mean. Biometrika 6:1-25.")
WELCH_1947 = Cita("Welch BL (1947). The generalization of «Student's» problem when several "
                  "different population variances are involved. Biometrika 34:28-35.")
DELACRE_2017 = Cita("Delacre M, Lakens D, Leys C (2017). Why psychologists should by default "
                    "use Welch's t-test instead of Student's t-test. Int Rev Soc Psychol "
                    "30:92-101.")
BROWN_FORSYTHE_1974 = Cita("Brown MB, Forsythe AB (1974). Robust tests for the equality of "
                           "variances. J Am Stat Assoc 69:364-367.")
SNEDECOR_1989 = Cita("Snedecor GW, Cochran WG (1989). Statistical methods, 8.ª ed. Ames: Iowa "
                     "State University Press.")
WELCH_1951 = Cita("Welch BL (1951). On the comparison of several mean values: an alternative "
                  "approach. Biometrika 38:330-336.")
LEVENE_1960 = Cita("Levene H (1960). Robust tests for equality of variances. En Olkin I (ed). "
                   "Contributions to probability and statistics. Stanford University Press, "
                   "278-292.")
TUKEY_1949 = Cita("Tukey JW (1949). Comparing individual means in the analysis of variance. "
                  "Biometrics 5:99-114.")
GAMES_1976 = Cita("Games PA, Howell JF (1976). Pairwise multiple comparison procedures with "
                  "unequal n's and/or variances: a Monte Carlo study. J Educ Stat 1:113-125.")
DELACRE_2019 = Cita("Delacre M, Leys C, Mora YL, Lakens D (2019). Taking parametric assumptions "
                    "seriously: arguments for the use of Welch's F-test instead of the "
                    "classical F-test in one-way ANOVA. Int Rev Soc Psychol 32:13.")
LANGSRUD_2003 = Cita("Langsrud Ø (2003). ANOVA for unbalanced data: use type II instead of type "
                     "III sums of squares. Stat Comput 13:163-167.")
HUITEMA_2011 = Cita("Huitema BE (2011). The analysis of covariance and alternatives, 2.ª ed. "
                    "Hoboken: Wiley.")
GREENHOUSE_1959 = Cita("Greenhouse SW, Geisser S (1959). On methods in the analysis of profile "
                       "data. Psychometrika 24:95-112.")
MANN_1947 = Cita("Mann HB, Whitney DR (1947). On a test of whether one of two random variables "
                 "is stochastically larger than the other. Ann Math Stat 18:50-60.")
WILCOXON_1945 = Cita("Wilcoxon F (1945). Individual comparisons by ranking methods. Biometrics "
                     "Bull 1:80-83.")
HODGES_1963 = Cita("Hodges JL, Lehmann EL (1963). Estimates of location based on rank tests. "
                   "Ann Math Stat 34:598-611.")
CONOVER_1999 = Cita("Conover WJ (1999). Practical nonparametric statistics, 3.ª ed. New York: "
                    "Wiley. IC de Hodges-Lehmann por el método de Moses.")
KRUSKAL_1952 = Cita("Kruskal WH, Wallis WA (1952). Use of ranks in one-criterion variance "
                    "analysis. J Am Stat Assoc 47:583-621.")
DUNN_1964 = Cita("Dunn OJ (1964). Multiple comparisons using rank sums. Technometrics "
                 "6:241-252.")
FRIEDMAN_1937 = Cita("Friedman M (1937). The use of ranks to avoid the assumption of normality "
                     "implicit in the analysis of variance. J Am Stat Assoc 32:675-701.")
KENDALL_1939 = Cita("Kendall MG, Babington Smith B (1939). The problem of m rankings. Ann Math "
                    "Stat 10:275-287. W de Kendall.")
DIXON_1946 = Cita("Dixon WJ, Mood AM (1946). The statistical sign test. J Am Stat Assoc "
                  "41:557-566.")
COCHRAN_1950 = Cita("Cochran WG (1950). The comparison of percentages in matched samples. "
                    "Biometrika 37:256-266.")
PEARSON_1900 = Cita("Pearson K (1900). On the criterion that a given system of deviations from "
                    "the probable in the case of a correlated system of variables is such that "
                    "it can be reasonably supposed to have arisen from random sampling. Philos "
                    "Mag 50:157-175.")
YATES_1934 = Cita("Yates F (1934). Contingency tables involving small numbers and the χ² test. "
                  "J R Stat Soc Suppl 1:217-235.")
FISHER_1922 = Cita("Fisher RA (1922). On the interpretation of χ² from contingency tables, and "
                   "the calculation of P. J R Stat Soc 85:87-94.")
HOPE_1968 = Cita("Hope ACA (1968). A simplified Monte Carlo significance test procedure. J R "
                 "Stat Soc B 30:582-598.")
CRAMER_1946 = Cita("Cramér H (1946). Mathematical methods of statistics. Princeton University "
                   "Press.")
AGRESTI_2002 = Cita("Agresti A (2002). Categorical data analysis, 2.ª ed. Hoboken: Wiley.")
MCNEMAR_1947 = Cita("McNemar Q (1947). Note on the sampling error of the difference between "
                    "correlated proportions or percentages. Psychometrika 12:153-157.")
EDWARDS_1948 = Cita("Edwards AL (1948). Note on the «correction for continuity» in testing the "
                    "significance of the difference between correlated proportions. "
                    "Psychometrika 13:185-187.")
NEWCOMBE_1998 = Cita("Newcombe RG (1998). Interval estimation for the difference between "
                     "independent proportions: comparison of eleven methods. Stat Med "
                     "17:873-890.")
WOOLF_1955 = Cita("Woolf B (1955). On estimating the relation between blood group and disease. "
                  "Ann Hum Genet 19:251-253.")
HALDANE_1956 = Cita("Haldane JBS (1956). The estimation and significance of the logarithm of a "
                    "ratio of frequencies. Ann Hum Genet 20:309-311.")
KATZ_1978 = Cita("Katz D, Baptista J, Azen SP, Pike MC (1978). Obtaining confidence intervals "
                 "for the risk ratio in cohort studies. Biometrics 34:469-474.")
MANTEL_1959 = Cita("Mantel N, Haenszel W (1959). Statistical aspects of the analysis of data "
                   "from retrospective studies of disease. J Natl Cancer Inst 22:719-748.")
ROBINS_1986 = Cita("Robins J, Breslow N, Greenland S (1986). Estimators of the Mantel-Haenszel "
                   "variance consistent in both sparse data and large-strata limiting models. "
                   "Biometrics 42:311-323.")
BRESLOW_1980 = Cita("Breslow NE, Day NE (1980). Statistical methods in cancer research, vol. I. "
                    "Lyon: IARC. Prueba de homogeneidad de los OR.")
COHEN_1960 = Cita("Cohen J (1960). A coefficient of agreement for nominal scales. Educ Psychol "
                  "Meas 20:37-46.")
COHEN_1968 = Cita("Cohen J (1968). Weighted kappa: nominal scale agreement with provision for "
                  "scaled disagreement or partial credit. Psychol Bull 70:213-220.")
FLEISS_1969 = Cita("Fleiss JL, Cohen J, Everitt BS (1969). Large sample standard errors of kappa "
                   "and weighted kappa. Psychol Bull 72:323-327.")
FEINSTEIN_1990 = Cita("Feinstein AR, Cicchetti DV (1990). High agreement but low kappa: I. The "
                      "problems of two paradoxes. J Clin Epidemiol 43:543-549.")
CRONBACH_1951 = Cita("Cronbach LJ (1951). Coefficient alpha and the internal structure of tests. "
                     "Psychometrika 16:297-334.")
FELDT_1965 = Cita("Feldt LS (1965). The approximate sampling distribution of Kuder-Richardson "
                  "reliability coefficient twenty. Psychometrika 30:357-370.")
TAVAKOL_2011 = Cita("Tavakol M, Dennick R (2011). Making sense of Cronbach's alpha. Int J Med "
                    "Educ 2:53-55.")
KROUWER_1995 = Cita("Krouwer JS, Monti KL (1995). A simple, graphical method to evaluate "
                     "laboratory assays. Eur J Clin Chem Clin Biochem 33:525-527.")
YOUDEN_1959 = Cita("Youden WJ (1959). Graphical diagnosis of interlaboratory test results. Ind "
                   "Qual Control 15:24-28.")
MEDCALC_YOUDEN = Cita("MedCalc, manual: Youden plot.",
                      "https://www.medcalc.org/en/manual/youdenplot.php")
SAARY_2008 = Cita("Saary MJ (2008). Radar plots: a useful way for presenting multivariate "
                  "health care data. J Clin Epidemiol 61:311-317.")
GILLESPIE_2012 = Cita("Gillespie TW (2012). Understanding waterfall plots. J Adv Pract Oncol "
                      "3:106-111.")
EISENHAUER_2009 = Cita("Eisenhauer EA et al. (2009). New response evaluation criteria in solid "
                       "tumours: revised RECIST guideline (version 1.1). Eur J Cancer "
                       "45:228-247.")
HANLEY_1982 = Cita("Hanley JA, McNeil BJ (1982). The meaning and use of the area under a "
                   "receiver operating characteristic (ROC) curve. Radiology 143:29-36.")
HANLEY_1983 = Cita("Hanley JA, McNeil BJ (1983). A method of comparing the areas under receiver "
                   "operating characteristic curves derived from the same cases. Radiology "
                   "148:839-843.")
DELONG_1988 = Cita("DeLong ER, DeLong DM, Clarke-Pearson DL (1988). Comparing the areas under "
                   "two or more correlated receiver operating characteristic curves: a "
                   "nonparametric approach. Biometrics 44:837-845.")
YOUDEN_1950 = Cita("Youden WJ (1950). Index for rating diagnostic tests. Cancer 3:32-35.")
HOSMER_2000 = Cita("Hosmer DW, Lemeshow S (2000). Applied logistic regression, 2.ª ed. New "
                   "York: Wiley. Escala de discriminación del AUC.")
EFRON_1993 = Cita("Efron B, Tibshirani RJ (1993). An introduction to the bootstrap. New "
                  "York: Chapman & Hall. Cap. 11: el jackknife no sirve para la mediana.")
KAPLAN_1958 = Cita("Kaplan EL, Meier P (1958). Nonparametric estimation from incomplete "
                   "observations. J Am Stat Assoc 53:457-481.")
GREENWOOD_1926 = Cita("Greenwood M (1926). The natural duration of cancer. Reports on Public "
                      "Health and Medical Subjects 33:1-26. London: HMSO.")
KALBFLEISCH_2002 = Cita("Kalbfleisch JD, Prentice RL (2002). The statistical analysis of failure "
                        "time data, 2.ª ed. Hoboken: Wiley. IC log-log de la curva.")
BROOKMEYER_1982 = Cita("Brookmeyer R, Crowley J (1982). A confidence interval for the median "
                       "survival time. Biometrics 38:29-41.")
POCOCK_2002 = Cita("Pocock SJ, Clayton TC, Altman DG (2002). Survival plots of time-to-event "
                   "outcomes in clinical trials: good practice and pitfalls. Lancet "
                   "359:1686-1689.")
MANTEL_1966 = Cita("Mantel N (1966). Evaluation of survival data and two new rank order "
                   "statistics arising in its consideration. Cancer Chemother Rep 50:163-170.")
BLAND_2004_LOGRANK = Cita("Bland JM, Altman DG (2004). The logrank test. BMJ 328:1073.")
GRAMBSCH_1994 = Cita("Grambsch PM, Therneau TM (1994). Proportional hazards tests and "
                     "diagnostics based on weighted residuals. Biometrika 81:515-526.")
COX_1972 = Cita("Cox DR (1972). Regression models and life-tables. J R Stat Soc B "
                "34:187-220.")
EFRON_1977 = Cita("Efron B (1977). The efficiency of Cox's likelihood function for censored "
                  "data. J Am Stat Assoc 72:557-565.")
REED_1971 = Cita("Reed AH, Henry RJ, Mason WB (1971). Influence of statistical method used on "
                 "the resulting estimate of normal range. Clin Chem 17:275-284. Regla D/R > 1/3.")
SOLBERG_1987 = Cita("Solberg HE (1987). Approved recommendation (1987) on the theory of "
                    "reference values. Part 5. Statistical treatment of collected reference "
                    "values. J Clin Chem Clin Biochem 25:645-656.")
ALTMAN_1993 = Cita("Altman DG (1993). Construction of age-related reference centiles using "
                   "absolute residuals. Stat Med 12:917-924.")
ALTMAN_CHITTY_1994 = Cita("Altman DG, Chitty LS (1994). Charts of fetal size: 1. Methodology. "
                          "Br J Obstet Gynaecol 101:29-34.")
CHOW_2008 = Cita("Chow SC, Shao J, Wang H (2008). Sample size calculations in clinical "
                 "research, 2.ª ed. Boca Raton: Chapman & Hall/CRC.")
HODGES_LEHMANN_1956 = Cita("Hodges JL, Lehmann EL (1956). The efficiency of some nonparametric "
                           "competitors of the t-test. Ann Math Stat 27:324-335.")
HOENIG_2001 = Cita("Hoenig JM, Heisey DM (2001). The abuse of power: the pervasive fallacy of "
                   "power calculations for data analysis. Am Stat 55:19-24.")
FLEISS_2003 = Cita("Fleiss JL, Levin B, Paik MC (2003). Statistical methods for rates and "
                   "proportions, 3.ª ed. Hoboken: Wiley. Cap. 4.")
HULLEY_2013 = Cita("Hulley SB, Cummings SR, Browner WS, Grady DG, Newman TB (2013). Designing "
                   "clinical research, 4.ª ed. Philadelphia: Lippincott Williams & Wilkins. "
                   "Cap. 6.")
EFRON_1987 = Cita("Efron B (1987). Better bootstrap confidence intervals. J Am Stat Assoc "
                  "82:171-185. El IC BCa.")
EFRON_1993_BOOT = Cita("Efron B, Tibshirani RJ (1993). An introduction to the bootstrap. New "
                       "York: Chapman & Hall. Cap. 13 y 14: IC percentil y BCa.")
CAMPBELL_1988 = Cita("Campbell MJ, Gardner MJ (1988). Calculating confidence intervals for "
                     "some non-parametric analyses. BMJ 296:1454-1456.")
BREIMAN_2001 = Cita("Breiman L (2001). Random forests. Mach Learn 45:5-32.")
STROBL_2007 = Cita("Strobl C, Boulesteix AL, Zeileis A, Hothorn T (2007). Bias in random forest "
                   "variable importance measures: illustrations, sources and a solution. BMC "
                   "Bioinformatics 8:25.")
HASTIE_2009 = Cita("Hastie T, Tibshirani R, Friedman J (2009). The elements of statistical "
                   "learning, 2.ª ed. New York: Springer. Cap. 7.10: validación cruzada.")
DERSIMONIAN_1986 = Cita("DerSimonian R, Laird N (1986). Meta-analysis in clinical trials. "
                        "Control Clin Trials 7:177-188.")
HIGGINS_2003 = Cita("Higgins JPT, Thompson SG, Deeks JJ, Altman DG (2003). Measuring "
                    "inconsistency in meta-analyses. BMJ 327:557-560.")
HIGGINS_2009 = Cita("Higgins JPT, Thompson SG, Spiegelhalter DJ (2009). A re-evaluation of "
                    "random-effects meta-analysis. J R Stat Soc A 172:137-159. Intervalo de "
                    "predicción.")
EGGER_1997 = Cita("Egger M, Davey Smith G, Schneider M, Minder C (1997). Bias in meta-analysis "
                  "detected by a simple, graphical test. BMJ 315:629-634.")
STERNE_2011 = Cita("Sterne JAC, Sutton AJ, Ioannidis JPA et al. (2011). Recommendations for "
                   "examining and interpreting funnel plot asymmetry in meta-analyses of "
                   "randomised controlled trials. BMJ 343:d4002.")
MATTHEWS_1990 = Cita("Matthews JNS, Altman DG, Campbell MJ, Royston P (1990). Analysis of serial "
                     "measurements in medical research. BMJ 300:230-235.")
CLSI_EP12 = Cita("CLSI (2023). EP12: Evaluation of qualitative, binary output examination "
                 "performance, 3.ª ed. IC de Wilson para sensibilidad y especificidad.")
BOSSUYT_2015 = Cita("Bossuyt PM, Reitsma JB, Bruns DE et al. (2015). STARD 2015: an updated "
                    "list of essential items for reporting diagnostic accuracy studies. BMJ "
                    "351:h5527.")
SIMEL_1991 = Cita("Simel DL, Samsa GP, Matchar DB (1991). Likelihood ratios with confidence: "
                  "sample size estimation for diagnostic test studies. J Clin Epidemiol "
                  "44:763-770.")
JAESCHKE_1994 = Cita("Jaeschke R, Guyatt GH, Sackett DL (1994). Users' guides to the medical "
                     "literature. III. How to use an article about a diagnostic test. B. What "
                     "are the results and will they help me in caring for my patients? JAMA "
                     "271:703-707.")
PEDUZZI_1995 = Cita("Peduzzi P, Concato J, Feinstein AR, Holford TR (1995). Importance of "
                    "events per independent variable in proportional hazards regression "
                    "analysis. II. Accuracy and precision of regression estimates. J Clin "
                    "Epidemiol 48:1503-1510.")
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
            "UVL = F·σ declarada,  F de la tabla 7 (gl × nMuestras)\n"
            "    fuera de la tabla: F = √(χ²(1 − α/nMuestras; gl)/gl)  (ap. B5)\n"
            "    gl de s_R = N − D; gl de s_WL de la tabla 6 con ρ = σWL/σR declarados\n"
            "    (fuera de la tabla: Satterthwaite con esa ρ, ap. B4)\n"
            "Atípico: Grubbs de dos colas al 99 %, G de la tabla B4 (tabla 3)\n"
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
            "Error total en Xc = |sesgo| + 1,65·s_WL  (Westgard, Carey y Wold 1974)\n"
            "    s_WL de EP15, llevada a Xc con CV constante (TEa en %) o DE constante\n"
            "    Cumple: con el extremo del IC del sesgo más lejos de 0, TE ≤ TEa\n"
            "Precisión (si hay corridas): EP15-A3, ver su ficha\n"
            "Sesgo contra el valor asignado: EP15-A3 §3; fuera del intervalo de\n"
            "    verificación se compara con el sesgo permitido (§3.6)"
        ),
        citas=(CLSI_EP09, CLSI_EP15, KROUWER_2008, PASSING_1983, LINNET_1990, EFRON_1993,
               WESTGARD_1974),
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

    # ---------------- Correlación: src/resultado/constructores/correlacion.py
    # docs/referencia-medcalc/Correlacion, acuerdo y confiabilidad.md; core:
    # src/core/statistics.py (pearson_r, spearman_rho, partial_correlation)
    "pearson": Ficha(
        formula=(
            "r = Σ(x − x̄)(y − ȳ) / √(Σ(x − x̄)²·Σ(y − ȳ)²)\n"
            "p: t = r·√(n − 2)/√(1 − r²), con n − 2 gl\n"
            "IC 95 %: tanh(atanh(r) ± 1,96/√(n − 3))  (z de Fisher)\n"
            "Palabras para |r| (Mukaka 2012): ≥ 0,9 muy alta; 0,7 alta; 0,5 moderada;\n"
            "    0,3 baja; menos, despreciable"
        ),
        citas=(FISHER_1921, MUKAKA_2012, BLAND_1986, MEDCALC_CORRELACION),
    ),
    "spearman": Ficha(
        formula=(
            "ρ = r de Pearson entre los rangos (empates: rango promedio)\n"
            "    sin empates, 1 − 6·Σd² / (n(n² − 1))\n"
            "p: aproximación t con n − 2 gl\n"
            "IC 95 %: tanh(atanh(ρ) ± 1,96·√((1 + ρ²/2)/(n − 3)))  (Bonett y Wright)"
        ),
        citas=(SPEARMAN_1904, BONETT_2000, MUKAKA_2012, MEDCALC_RANGOS),
    ),
    "parcial": Ficha(
        formula=(
            "r_xy·z = (r_xy − r_xz·r_yz) / √((1 − r_xz²)(1 − r_yz²))\n"
            "    = correlación entre los residuos de x sobre z y de y sobre z\n"
            "p: t = r·√(n − 3)/√(1 − r²), con n − 3 gl\n"
            "IC 95 %: tanh(atanh(r) ± 1,96/√(n − 4))"
        ),
        citas=(FISHER_1921, ALTMAN_1991, MEDCALC_PARCIAL),
    ),

    # ---------------- Regresión: src/resultado/constructores/regresion.py
    # core: src/core/regression.py, src/core/probit.py; diagnósticos: statsmodels
    "regresion_lineal": Ficha(
        formula=(
            "y = b₀ + b₁·x;  b₁ = Σ(x − x̄)(y − ȳ) / Σ(x − x̄)²;  b₀ = ȳ − b₁·x̄\n"
            "IC 95 % de cada coeficiente: b ± t(0,975; n − 2)·EE\n"
            "R² = 1 − SS_res/SS_tot;  error estándar residual = √(SS_res/(n − 2))\n"
            "Diagnósticos: RESET (curvatura), Shapiro-Wilk y Breusch-Pagan de los residuos"
        ),
        citas=(DRAPER_1998, RAMSEY_1969, BREUSCH_1979, CORNBLEET_1979),
    ),
    "regresion_multiple": Ficha(
        formula=(
            "y = b₀ + b₁·x₁ + … + b_k·x_k;  b = (X'X)⁻¹ X'y\n"
            "EE(b) = √diag(s²·(X'X)⁻¹),  s² = SS_res/(n − k − 1)\n"
            "IC 95 %: b ± t(0,975; n − k − 1)·EE;  F = (SS_reg/k)/(SS_res/(n − k − 1))\n"
            "VIF_j = 1/(1 − R²_j), con R²_j de x_j sobre las demás predictoras"
        ),
        citas=(DRAPER_1998, BREUSCH_1979, RAMSEY_1969),
    ),
    "regresion_logistica": Ficha(
        formula=(
            "ln(p/(1 − p)) = b₀ + b₁·x₁ + … ;  máxima verosimilitud\n"
            "OR = exp(b);  IC 95 % = exp(b ± 1,96·EE)  (Wald)\n"
            "Hosmer-Lemeshow: H = Σ (O − E)² / (E·(1 − E/n_g)) en deciles de riesgo,\n"
            "    chi² con g − 2 gl;  eventos por variable = clase menos frecuente / k"
        ),
        citas=(HOSMER_1980, PEDUZZI_1996),
    ),
    "probit": Ficha(
        formula=(
            "P(y = 1) = Φ(b₀ + b₁·x);  máxima verosimilitud\n"
            "Dosis con respuesta p: x_p = (Φ⁻¹(p) − b₀)/b₁  (ED50, ED95)\n"
            "IC 95 % de x_p por el método delta: EE² = g'·Cov(b)·g,  g = (−1/b₁, −x_p/b₁)\n"
            "En log10, x = log10(dosis) y el resultado se retransforma"
        ),
        citas=(FINNEY_1971, VENABLES_2002, CLSI_EP17),
    ),

    # ---------------- Comparación de medias: src/resultado/constructores/medias.py
    # core: src/core/statistics.py (scipy.stats), src/core/diagnostic_tests.py
    "t_una_muestra": Ficha(
        formula=(
            "t = (x̄ − μ₀) / (s/√n),  n − 1 gl\n"
            "IC 95 % de la media: x̄ ± t(0,975; n − 1)·s/√n"
        ),
        citas=(STUDENT_1908, ALTMAN_1991),
    ),
    "t_pareada": Ficha(
        formula=(
            "dᵢ = x₁ᵢ − x₂ᵢ;  t = d̄ / (s_d/√n),  n − 1 gl\n"
            "IC 95 % de d̄: d̄ ± t(0,975; n − 1)·s_d/√n"
        ),
        citas=(STUDENT_1908, ALTMAN_1991),
    ),
    "t_independiente": Ficha(
        formula=(
            "t = (x̄₁ − x̄₂) / √(s₁²/n₁ + s₂²/n₂)\n"
            "gl de Welch-Satterthwaite = (s₁²/n₁ + s₂²/n₂)² / ((s₁²/n₁)²/(n₁−1) + (s₂²/n₂)²/(n₂−1))\n"
            "IC 95 %: (x̄₁ − x̄₂) ± t(0,975; gl)·√(s₁²/n₁ + s₂²/n₂)"
        ),
        citas=(WELCH_1947, DELACRE_2017),
    ),
    "comparar_medias": Ficha(
        formula=(
            "Con m, DE y n de cada grupo: t = (m₁ − m₂) / √(DE₁²/n₁ + DE₂²/n₂)\n"
            "gl de Welch-Satterthwaite; IC 95 % = (m₁ − m₂) ± t(0,975; gl)·EE"
        ),
        citas=(WELCH_1947, ALTMAN_1991),
    ),
    "f_varianzas": Ficha(
        formula=(
            "F = s²_mayor / s²_menor, con (n_mayor − 1, n_menor − 1) gl\n"
            "p a dos colas = 2·mín(P(F ≥ f), P(F ≤ f))\n"
            "Brown-Forsythe: ANOVA de |x − mediana del grupo|, no supone normalidad"
        ),
        citas=(SNEDECOR_1989, BROWN_FORSYTHE_1974),
    ),

    # ---------------- ANOVA: src/resultado/constructores/anova.py
    # core: statistics.py (scipy, pingouin, statsmodels), two_way_anova.py, ancova.py,
    # repeated_measures.py
    "anova_una_via": Ficha(
        formula=(
            "F = MS_entre / MS_dentro,  (k − 1, N − k) gl\n"
            "Levene p ≥ 0,05 → ANOVA clásico + Tukey HSD;  p < 0,05 → ANOVA de Welch\n"
            "    (cada grupo pesado por nᵢ/sᵢ²) + Games-Howell\n"
            "El post-hoc solo corre si la prueba global detecta diferencia"
        ),
        citas=(LEVENE_1960, WELCH_1951, TUKEY_1949, GAMES_1976, DELACRE_2019),
    ),
    "anova_dos_vias": Ficha(
        formula=(
            "y ~ A + B + A×B;  sumas de cuadrados tipo II (statsmodels)\n"
            "F de cada efecto = MS_efecto / MS_error"
        ),
        citas=(LANGSRUD_2003, SNEDECOR_1989),
    ),
    "ancova": Ficha(
        formula=(
            "y = b₀ + efecto del grupo + b·x + error;  sumas de cuadrados tipo II\n"
            "Media ajustada de cada grupo: predicción en la media general de x\n"
            "Paralelismo: término grupo × x;  η² parcial = SS_grupo/(SS_grupo + SS_error)"
        ),
        citas=(HUITEMA_2011, LANGSRUD_2003),
    ),
    "medidas_repetidas": Ficha(
        formula=(
            "F = MS_tiempo / MS_error (sujetos como bloque)\n"
            "ε de Greenhouse-Geisser = tr(S*)² / ((k − 1)·ΣS*²),  S* = covarianza doblemente\n"
            "    centrada;  p corregido con gl·ε"
        ),
        citas=(GREENHOUSE_1959, SNEDECOR_1989),
    ),

    # ---------------- No paramétricas: src/resultado/constructores/noparametricas.py
    # core: src/core/statistics.py (scipy, statsmodels)
    "mann_whitney": Ficha(
        formula=(
            "U = R₁ − n₁(n₁ + 1)/2,  R₁ = suma de rangos del grupo 1 (empates: rango medio)\n"
            "Hodges-Lehmann: mediana de todas las diferencias xᵢ − yⱼ\n"
            "IC 95 % (Moses): estadísticos de orden k y n₁n₂ − k + 1 de esas diferencias,\n"
            "    k = ⌊n₁n₂/2 − 1,96·√(n₁n₂(n₁ + n₂ + 1)/12)⌋"
        ),
        citas=(MANN_1947, HODGES_1963, CONOVER_1999),
    ),
    "wilcoxon": Ficha(
        formula=(
            "dᵢ = x₁ᵢ − x₂ᵢ (los ceros no entran);  W = suma de rangos de |d| con signo\n"
            "Pseudomediana: mediana de los promedios de Walsh (dᵢ + dⱼ)/2, i ≤ j\n"
            "IC 95 %: órdenes k y M − k + 1,  k = ⌊M/2 − 1,96·√(n(n + 1)(2n + 1)/24)⌋"
        ),
        citas=(WILCOXON_1945, HODGES_1963, CONOVER_1999),
    ),
    "kruskal": Ficha(
        formula=(
            "H = (12/(N(N + 1)))·Σ Rᵢ²/nᵢ − 3(N + 1), corregido por empates;  k − 1 gl\n"
            "Dunn: z = (R̄ᵢ − R̄ⱼ)/√((N(N + 1)/12 − Σ(t³ − t)/(12(N − 1)))(1/nᵢ + 1/nⱼ)),\n"
            "    con Bonferroni"
        ),
        citas=(KRUSKAL_1952, DUNN_1964),
    ),
    "friedman": Ficha(
        formula=(
            "χ²_r = (12/(n·k(k + 1)))·Σ Rⱼ² − 3n(k + 1), corregido por empates;  k − 1 gl\n"
            "W de Kendall = χ²_r / (n(k − 1))"
        ),
        citas=(FRIEDMAN_1937, KENDALL_1939),
    ),
    "signos": Ficha(
        formula=(
            "n₊ = pares con x₁ > x₂, n₋ = con x₁ < x₂ (empates afuera)\n"
            "p = prueba binomial exacta de n₊ en n₊ + n₋ con probabilidad 1/2"
        ),
        citas=(DIXON_1946,),
    ),
    "cochran": Ficha(
        formula=(
            "Q = (k − 1)·[k·ΣCⱼ² − T²] / [k·T − ΣRᵢ²],  k − 1 gl\n"
            "Cⱼ = éxitos por tratamiento, Rᵢ = éxitos por sujeto, T = total"
        ),
        citas=(COCHRAN_1950,),
    ),

    # ---------------- Proporciones y tablas: src/resultado/constructores/tablas.py
    "chi_cuadrado": Ficha(
        formula=(
            "χ² = Σ (O − E)²/E,  E = total de fila × total de columna / n;  (r−1)(c−1) gl\n"
            "2×2: corrección de Yates, Σ (|O − E| − 0,5)²/E\n"
            "Esperada mínima < 5: Fisher en 2×2; en r×c, p por permutación (9999 tablas con\n"
            "    los mismos totales, semilla fija)\n"
            "V de Cramér = √(χ² / (n·(mín(r, c) − 1)))"
        ),
        citas=(PEARSON_1900, YATES_1934, FISHER_1922, HOPE_1968, CRAMER_1946),
    ),
    "fisher": Ficha(
        formula=(
            "p = suma de las probabilidades hipergeométricas de las tablas con los mismos\n"
            "    totales tan o más extremas que la observada\n"
            "OR condicional (máxima verosimilitud) con su IC exacto"
        ),
        citas=(FISHER_1922, AGRESTI_2002),
    ),
    "mcnemar": Ficha(
        formula=(
            "b, c = pares discordantes\n"
            "b + c < 25: p binomial exacta, B(b + c; 0,5)\n"
            "b + c ≥ 25: χ² = (|b − c| − 1)²/(b + c), 1 gl (Edwards)"
        ),
        citas=(MCNEMAR_1947, EDWARDS_1948),
    ),
    "dos_proporciones": Ficha(
        formula=(
            "z = (p₁ − p₂) / √(p̂(1 − p̂)(1/n₁ + 1/n₂)),  p̂ agrupada\n"
            "IC 95 % de p₁ − p₂: Newcombe (método 10, Wilson híbrido)"
        ),
        citas=(NEWCOMBE_1998, ALTMAN_1991),
    ),
    "odds_ratio": Ficha(
        formula=(
            "OR = (a·d)/(b·c);  IC 95 % = exp(ln OR ± 1,96·√(1/a + 1/b + 1/c + 1/d))\n"
            "Con alguna celda en 0 se suma 0,5 a todas (Haldane)"
        ),
        citas=(WOOLF_1955, HALDANE_1956),
    ),
    "riesgo_relativo": Ficha(
        formula=(
            "RR = (a/(a + b)) / (c/(c + d))\n"
            "IC 95 % = exp(ln RR ± 1,96·√(1/a − 1/(a + b) + 1/c − 1/(c + d)))\n"
            "NNT (o NNH) = 1/|riesgo₀ − riesgo₁|"
        ),
        citas=(KATZ_1978, ALTMAN_1991),
    ),
    "cmh": Ficha(
        formula=(
            "χ²_CMH = (Σ(aₖ − E[aₖ]))² / Σ Var(aₖ), 1 gl\n"
            "OR_MH = Σ(aₖdₖ/nₖ) / Σ(bₖcₖ/nₖ);  IC por la varianza de Robins-Breslow-Greenland\n"
            "Homogeneidad de los OR entre estratos: Breslow-Day"
        ),
        citas=(MANTEL_1959, ROBINS_1986, BRESLOW_1980),
    ),

    # ---------------- Concordancia: src/resultado/constructores/concordancia.py
    "kappa": Ficha(
        formula=(
            "κ = (Po − Pe) / (1 − Pe);  Po = acuerdo observado, Pe = esperado por azar\n"
            "IC 95 %: EE de Fleiss, Cohen y Everitt;  p con el EE bajo κ = 0\n"
            "Escala de Altman (1991): < 0,2 pobre; 0,2-0,4 débil; 0,4-0,6 moderada;\n"
            "    0,6-0,8 buena; > 0,8 muy buena"
        ),
        citas=(COHEN_1960, FLEISS_1969, ALTMAN_1991, FEINSTEIN_1990),
    ),
    "kappa_ponderado": Ficha(
        formula=(
            "κ_w = 1 − Σ wᵢⱼ·Oᵢⱼ / Σ wᵢⱼ·Eᵢⱼ\n"
            "Pesos lineales wᵢⱼ = |i − j|/(k − 1);  cuadráticos (i − j)²/(k − 1)²\n"
            "IC y p: Fleiss, Cohen y Everitt (statsmodels)"
        ),
        citas=(COHEN_1968, FLEISS_1969, ALTMAN_1991),
    ),
    "cronbach": Ficha(
        formula=(
            "α = (k/(k − 1))·(1 − Σ s²ᵢ / s²_total)\n"
            "IC 95 % de Feldt: 1 − (1 − α)·F(0,975 y 0,025; n − 1, (n − 1)(k − 1))\n"
            "Por ítem: correlación con la suma de los demás y α sin ese ítem"
        ),
        citas=(CRONBACH_1951, FELDT_1965, TAVAKOL_2011),
    ),

    # ---------------- Gráficos de comparación: src/resultado/constructores/graficos.py
    "mountain": Ficha(
        formula=(
            "d = método 1 − método 2, ordenadas;  percentil = 100·rango/(n + 1)\n"
            "Plegado: si pasa de 50, 100 − percentil;  el pico cae en la mediana"
        ),
        citas=(KROUWER_1995, CLSI_EP09),
    ),
    "youden": Ficha(
        formula=(
            "Mediana de Manhattan = (mediana de x, mediana de y), sin los valores a más de\n"
            "    3 RIC de los cuartiles\n"
            "Distancia a la recta de 45°: (x − Mx − (y − My))/√2;  s = su DE\n"
            "Círculo del 95 %: radio = s·√(−2 ln 0,05) = 2,448·s (normal circular)"
        ),
        citas=(YOUDEN_1959, MEDCALC_YOUDEN),
    ),
    "polar": Ficha(
        formula="Un eje por variable, a ángulos iguales; el radio es la media de la variable",
        citas=(SAARY_2008,),
    ),
    "cascada": Ficha(
        formula="Una barra por sujeto con su valor (el cambio), ordenadas de mayor a menor",
        citas=(GILLESPIE_2012, EISENHAUER_2009),
    ),

    # ---------------- Curvas ROC: src/resultado/constructores/roc.py
    "curva_roc": Ficha(
        formula=(
            "AUC = área bajo la curva (trapecios, empates agrupados) = P(enfermo > sano)\n"
            "EE de DeLong: varianza de los valores de colocación de enfermos y de sanos\n"
            "IC 95 % = AUC ± 1,96·EE;  p de AUC = 0,5 con ese EE\n"
            "Umbral de Youden: máximo de J = sensibilidad + especificidad − 1\n"
            "Sensibilidad y especificidad en el umbral con IC de Wilson"
        ),
        citas=(HANLEY_1982, DELONG_1988, YOUDEN_1950, HOSMER_2000),
    ),
    "comparar_auc": Ficha(
        formula=(
            "z = (AUC₁ − AUC₂) / √(EE₁² + EE₂²)  (curvas de pacientes distintos)\n"
            "IC 95 % de la diferencia = (AUC₁ − AUC₂) ± 1,96·√(EE₁² + EE₂²)"
        ),
        citas=(HANLEY_1983, DELONG_1988),
    ),

    # ---------------- Supervivencia: src/resultado/constructores/supervivencia.py
    "kaplan_meier": Ficha(
        formula=(
            "S(t) = Π (1 − dᵢ/nᵢ) sobre los tiempos con evento tᵢ ≤ t\n"
            "Greenwood: Var[S(t)] = S(t)² · Σ dᵢ / (nᵢ(nᵢ − dᵢ))\n"
            "IC 95 % log-log: S(t)^exp(±1,96 · √Σ dᵢ/(nᵢ(nᵢ − dᵢ)) / |ln S(t)|)\n"
            "Mediana: primer t con S(t) ≤ 0,5; su IC, donde las bandas del IC cruzan 0,5\n"
            "(dᵢ eventos y nᵢ en riesgo en tᵢ; los censurados cuentan en riesgo hasta que salen)"
        ),
        citas=(KAPLAN_1958, GREENWOOD_1926, KALBFLEISCH_2002, BROOKMEYER_1982, POCOCK_2002),
    ),
    "log_rank": Ficha(
        formula=(
            "En cada tiempo con evento: Eⱼ += d · nⱼ/n  (lo que le tocaba al grupo j)\n"
            "χ² = (O − E)ᵀ V⁻¹ (O − E) sobre k − 1 grupos, gl = k − 1\n"
            "HR (dos grupos) = (O₂/E₂) / (O₁/E₁);  IC 95 % = exp(ln HR ± 1,96·√(1/E₁ + 1/E₂))\n"
            "Riesgos proporcionales: Cox con el grupo y residuos de Schoenfeld"
        ),
        citas=(MANTEL_1966, BLAND_2004_LOGRANK, ALTMAN_1991, GRAMBSCH_1994),
    ),
    "regresion_cox": Ficha(
        formula=(
            "h(t | x) = h₀(t) · exp(β₁x₁ + … + βₚxₚ)\n"
            "β por verosimilitud parcial con empates de Efron; EE de la información observada\n"
            "HR = exp(β);  IC 95 % = exp(β ± 1,96·EE);  razón de verosimilitudes 2(ℓ − ℓ₀), gl = p\n"
            "Schoenfeld: residuos escalados contra g(t) = 1 − KM(t⁻); χ² por covariable (1 gl)\n"
            "y global (p gl), aproximación de Grambsch y Therneau"
        ),
        citas=(COX_1972, EFRON_1977, GRAMBSCH_1994, PEDUZZI_1995),
    ),

    # ---------------- Valores de referencia: src/resultado/constructores/referencia.py
    "intervalo_referencia": Ficha(
        formula=(
            "Límites = datos de rango 0,025·(n + 1) y 0,975·(n + 1), interpolados (EP28 §9.4.1)\n"
            "IC 90 % de cada límite: rangos de orden de la tabla 8 (§9.5.1), desde n = 119\n"
            "Dixon: un extremo es sospechoso si D/R > 1/3 (D, distancia al vecino; R, rango)\n"
            "Verificación de uno publicado: 20 sujetos, se adopta con 2 o menos afuera"
        ),
        citas=(CLSI_EP28, SOLBERG_1987, REED_1971),
    ),
    "intervalos_edad": Ficha(
        formula=(
            "Media(edad) = polinomio de grado 1 a 3 (se baja mientras el más alto dé p ≥ 0,05)\n"
            "DE(edad) = √(π/2) · (a + b·edad), recta de los residuos absolutos (constante si\n"
            "la pendiente no aporta); centiles = media ± 1,96·DE a cada edad\n"
            "Por grupos: percentiles 2,5 y 97,5 con el rango p(n + 1) de EP28 en cada grupo"
        ),
        citas=(ALTMAN_1993, ALTMAN_CHITTY_1994, CLSI_EP28),
    ),

    # ---------------- Tamaño de muestra y poder: src/resultado/constructores/tamano.py
    "tam_una_media": Ficha(
        formula=(
            "n = el más chico con poder exacto ≥ el pedido\n"
            "poder = P(|T| > t(1 − α/2; n − 1)),  T ~ t no central(gl = n − 1, λ = (Δ/DE)·√n)"
        ),
        citas=(CHOW_2008, HODGES_LEHMANN_1956),
    ),
    "tam_dos_medias": Ficha(
        formula=(
            "n₁ = el más chico con poder exacto ≥ el pedido, n₂ = ⌈razón·n₁⌉\n"
            "T ~ t no central(gl = n₁ + n₂ − 2, λ = (Δ/DE) / √(1/n₁ + 1/n₂))"
        ),
        citas=(CHOW_2008, HODGES_LEHMANN_1956),
    ),
    "poder_t": Ficha(
        formula=(
            "poder = P(|T| > t crítico) con T ~ t no central\n"
            "una muestra o pareada: gl = n − 1, λ = (Δ/DE)·√n\n"
            "dos grupos de n: gl = 2n − 2, λ = (Δ/DE)·√(n/2)"
        ),
        citas=(CHOW_2008, HOENIG_2001),
    ),
    "tam_dos_proporciones": Ficha(
        formula=(
            "n por grupo = [z(1 − α/2)·√(2·p̄·q̄) + z(poder)·√(p₁q₁ + p₂q₂)]² / (p₁ − p₂)²\n"
            "p̄ = (p₁ + p₂)/2; sin corrección de continuidad"
        ),
        citas=(FLEISS_2003,),
    ),
    "tam_correlacion": Ficha(
        formula=(
            "n = [(z(1 − α/2) + z(poder)) / atanh(r)]² + 3\n"
            "poder(n) = Φ(atanh(r)·√(n − 3) − z(1 − α/2))  (z de Fisher)"
        ),
        citas=(HULLEY_2013, HOENIG_2001),
    ),

    # ---------------- Bootstrap: src/resultado/constructores/bootstrap.py
    **{nombre: Ficha(
        formula=(
            f"{que} en B = 10.000 remuestreos con reposición (semilla fija)\n"
            "IC percentil: percentiles 2,5 y 97,5 de la distribución bootstrap\n"
            "IC BCa: percentiles Φ(z₀ + (z₀ + z)/(1 − a(z₀ + z))), con z₀ = Φ⁻¹(fracción\n"
            "de remuestreos debajo del estimado) y a, la aceleración, por jackknife"
            + extra
        ),
        citas=(EFRON_1987, EFRON_1993_BOOT) + citas_extra,
    ) for nombre, que, extra, citas_extra in (
        ("boot_media", "La media", "", ()),
        ("boot_mediana", "La mediana",
         "\nIC exacto por rangos: r y n − r + 1, r el mayor con P(X ≤ r − 1) ≤ 0,025,"
         "\nX ~ Binomial(n, 1/2)", (CAMPBELL_1988,)),
        ("boot_diferencia", "x̄₁ − x̄₂, cada grupo remuestreado por separado,", "", ()),
        ("boot_correlacion", "r de los pares (x, y) remuestreados juntos,", "", ()),
        ("boot_regresion", "Pendiente e intercepto de mínimos cuadrados de los pares,", "", ()),
    )},

    # ---------------- Machine learning: src/resultado/constructores/ml.py
    "rf_clasificacion": Ficha(
        formula=(
            "100 árboles, cada uno sobre un remuestreo de los casos, √p predictoras por corte (Gini)\n"
            "Desempeño: predicción de cada caso por un modelo que no lo vio (validación cruzada\n"
            "estratificada, k = 5); contra la exactitud de adivinar siempre la clase más frecuente\n"
            "(binomial a una cola). AUC de las probabilidades fuera de muestra, IC de DeLong\n"
            "Importancia: caída de la exactitud al desordenar la predictora en la partición de prueba"
        ),
        citas=(BREIMAN_2001, HASTIE_2009, STROBL_2007, DELONG_1988),
    ),
    "rf_regresion": Ficha(
        formula=(
            "100 árboles, cada uno sobre un remuestreo de los casos; predicción = promedio\n"
            "R² fuera de muestra = 1 − Σ(y − ŷ_cv)² / Σ(y − ȳ)²  (0 = predecir siempre la media)\n"
            "Importancia: caída del R² al desordenar la predictora en la partición de prueba"
        ),
        citas=(BREIMAN_2001, HASTIE_2009, STROBL_2007),
    ),

    # ---------------- Sueltos: src/resultado/constructores/sueltos.py
    "meta_analisis": Ficha(
        formula=(
            "Fijos: θ = Σwᵢθᵢ / Σwᵢ, wᵢ = 1/EEᵢ²;  EE(θ) = 1/√Σwᵢ\n"
            "Q = Σwᵢ(θᵢ − θ)², gl = k − 1;  I² = máx(0, (Q − gl)/Q)\n"
            "Aleatorios (DerSimonian-Laird): τ² = máx(0, (Q − gl)/(Σw − Σw²/Σw)), wᵢ* = 1/(EEᵢ² + τ²)\n"
            "Predicción: θ ± t(0,975; k − 2)·√(τ² + EE(θ)²);  Egger: (θᵢ/EEᵢ) contra 1/EEᵢ, intercepto"
        ),
        citas=(DERSIMONIAN_1986, HIGGINS_2003, HIGGINS_2009, EGGER_1997, STERNE_2011),
    ),
    "mediciones_seriales": Ficha(
        formula=(
            "Pendiente de cada sujeto contra el tiempo (0, 1, …, k − 1), por mínimos cuadrados\n"
            "Tendencia: t de una muestra sobre las pendientes (H₀: media = 0), gl = sujetos − 1"
        ),
        citas=(MATTHEWS_1990,),
    ),
    "prueba_diagnostica": Ficha(
        formula=(
            "a = VP, b = FP, c = FN, d = VN\n"
            "Sensibilidad = a/(a + c), especificidad = d/(b + d), VPP = a/(a + b), VPN = d/(c + d)\n"
            "IC 95 %: Wilson (CLSI EP12)\n"
            "VPP para una prevalencia π = S·π / (S·π + (1 − E)(1 − π)); VPN, análogo"
        ),
        citas=(CLSI_EP12, BOSSUYT_2015, SIMEL_1991),
    ),
    "razones_verosimilitud": Ficha(
        formula=(
            "LR+ = S/(1 − E), LR− = (1 − S)/E\n"
            "Var(ln LR+) = 1/a − 1/(a + c) + 1/b − 1/(b + d);  Var(ln LR−) = 1/c − 1/(a + c) + 1/d − 1/(b + d)\n"
            "Odds post-test = odds pre-test × LR;  probabilidad = odds/(1 + odds)"
        ),
        citas=(SIMEL_1991, JAESCHKE_1994),
    ),
}


def ficha(analisis: str) -> Ficha:
    try:
        return FICHAS[analisis]
    except KeyError:
        raise KeyError(f"El análisis «{analisis}» no tiene ficha en src/resultado/citas.py: "
                       "todo análisis migrado a Resultado lleva fórmula y cita.") from None
