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


FICHAS: dict[str, Ficha] = {
    # docs/referencia-medcalc/Comparacion de metodos y concordancia.md,
    # secciones "Bland-Altman plot"; core: src/core/bland_altman.py
    "bland_altman": Ficha(
        formula=(
            "d = método 1 − método 2, una diferencia por par\n"
            "Sesgo = d̄ (media de d)    s = DE de d, con n − 1\n"
            "Sesgo % = d̄ / x̄₁ × 100\n"
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
}


def ficha(analisis: str) -> Ficha:
    try:
        return FICHAS[analisis]
    except KeyError:
        raise KeyError(f"El análisis «{analisis}» no tiene ficha en src/resultado/citas.py: "
                       "todo análisis migrado a Resultado lleva fórmula y cita.") from None
