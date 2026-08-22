---
tags: [medcalc, formulas, estadistica, referencia]
tipo: referencia
version: 23.6.5.0
grupo: correlacion-y-acuerdo
formulas: 5
paginas: 10
fecha_extraccion: 2026-08-13
metodo_extraccion: manual (WebFetch directo)
---

# MedCalc - Formulas - Correlacion, acuerdo y confiabilidad

Volver a [[MedCalc - Mapa]] | indice de procedimientos: [[MedCalc - Procedimientos estadisticos]]

**10 paginas leidas. Solo 5 formulas publicadas.** Este grupo lo lei yo pagina por pagina
(los subagentes murieron por limite de gasto), con la misma disciplina: transcripcion literal o
declaracion explicita de que la pagina no publica la formula.

> [!important] El hallazgo principal de este grupo
> El manual de MedCalc **no publica** la matematica de casi ningun estadistico de correlacion ni de
> acuerdo. En lugar de la formula, **atribuye el calculo a una fuente**: "calculates ... according to
> Cohen, 1960", "according to Fleiss et al., 2003", "the method described in Conover, 1999 (p. 281)".
> Eso no es un hueco de esta nota: es como esta escrito el manual. Para auditar un ICC o un kappa de
> MedCalc hay que ir al paper citado, no a medcalc.org.
> Manual leido: el **ingles** (`/en/manual/`); las frases entre comillas quedan en ingles.
> Estado de verificacion de la cosecha completa: ver [[MedCalc - Mapa]].

---

## Comparison of correlation coefficients

`comparison-of-correlation-coefficients.php` - https://www.medcalc.org/en/manual/comparison-of-correlation-coefficients.php

**La unica pagina del grupo que publica las formulas completas del procedimiento.** Compara dos
coeficientes de correlacion independientes mediante una prueba z sobre coeficientes transformados
por Fisher.

**Referencias que cita la pagina:** Hinkle DE, Wiersma W, Jurs SG (1988) Applied statistics for the behavioral sciences. 2nd ed. Boston: Houghton Mifflin Company.

### Transformacion z de Fisher

```
z_r = (1/2) * ln( (1+r) / (1-r) )
```

**Simbolos / literal de la pagina.** `r` = coeficiente de correlacion observado; `z_r` = coeficiente
transformado. La pagina lo introduce como el paso previo al analisis: los coeficientes se transforman
antes de compararse.

### Error estandar de la diferencia entre dos z

```
se( z_r1 - z_r2 ) = sqrt( 1/(n1-3) + 1/(n2-3) )
```

**Simbolos / literal de la pagina.** `n1` y `n2` = tamanos de muestra de cada coeficiente.
**Ojo con el `-3`**: la pagina imprime `n-3`, no el `n-1` ni el `n-2` que aparecen en otras
formulaciones del error estandar de Fisher z. Se transcribe tal cual esta publicado.

### Estadistico de prueba

```
z = ( z_r1 - z_r2 ) / se( z_r1 - z_r2 )
```

**Simbolos / literal de la pagina.** La pagina remite para los valores criticos a
"Values of the Normal distribution". Caracteriza el metodo como
"a z-test on Fisher z-transformed correlation coefficients (Hinkle et al, 1988)".

**Supuestos / condiciones.** La pagina **no enuncia supuestos explicitos** ni da metodo de intervalo
de confianza para la diferencia.

---

## Cohen's kappa

`kappa.php` - https://www.medcalc.org/en/manual/kappa.php

Unico otro lugar del grupo con algebra impresa: los **esquemas de ponderacion** del kappa ponderado.
La formula general del kappa (ponderado o no) **no esta en la pagina**; remite a Altman, 1991,
p. 406-407.

**Referencias que cita la pagina:** Cohen J (1960) | Cohen J (1968) | Altman DG (1991) | Fleiss JL, Levin B, Paik MC (2003).

### Pesos lineales (kappa ponderado)

```
w_i = 1 - i / (k - 1)
```

**Simbolos / literal de la pagina.** `i` = la diferencia en categorias entre las dos calificaciones;
`k` = numero total de categorias.

### Pesos cuadraticos (kappa ponderado)

```
w_i = 1 - i^2 / (k - 1)^2
```

**Simbolos / literal de la pagina.** Mismos simbolos que el caso lineal. Penaliza mas fuerte los
desacuerdos grandes.

### Kappa (sin ponderar) y kappa ponderado — atribucion, sin formula

```
La pagina NO publica la formula.
```

**Simbolos / literal de la pagina.** Texto literal: "MedCalc calculates the inter-rater agreement
statistic Kappa according to Cohen, 1960; and weighted Kappa according to Cohen, 1968." Para el
detalle computacional remite a Altman, 1991, p. 406-407.

**Intervalo de confianza.** "The standard error and 95% confidence interval are calculated according
to Fleiss et al., 2003." Sin formula.

### Tabla de interpretacion de kappa que publica la pagina

| Valor de K | Fuerza del acuerdo |
|---|---|
| < 0.20 | Poor |
| 0.21 - 0.40 | Fair |
| 0.41 - 0.60 | Moderate |
| 0.61 - 0.80 | Good |
| 0.81 - 1.00 | Very good |

---

## Inter-rater agreement

`inter-rater-agreement.php` - https://www.medcalc.org/en/manual/inter-rater-agreement.php

Pagina hermana de `kappa.php`. **No publica ninguna formula.** Da la lectura del estadistico
(K = 1 acuerdo perfecto; K = 0 acuerdo no mejor que el azar; K < 0 acuerdo peor que el azar), la
misma tabla de interpretacion de Altman 1991, y menciona pesos lineales y cuadraticos sin escribirlos.
Error estandar e IC 95 % "according to Fleiss et al., 2003", incluido el error estandar para
contrastar kappa ponderado contra un valor prefijado distinto de cero — todo sin formula.

**Referencias que cita la pagina:** Altman DG (1991) | Cohen J (1960) | Cohen J (1968) | Fleiss JL, Levin B, Paik MC (2003).

---

## Intraclass correlation coefficient (ICC)

`intraclass-correlation-coefficient.php` - https://www.medcalc.org/en/manual/intraclass-correlation-coefficient.php

**No publica ninguna formula.** Lo que si define, y es lo que hace falta para elegir bien el ICC:

- **Modelo de estudio 1:** "Each subject is rated by a different and random selection of a pool of
  raters" → el ICC mide **Absolute agreement**.
- **Modelo de estudio 2:** "Each subject is rated by the same raters" → se elige entre
  **Consistency** o **Absolute agreement**.
- Salidas: **Single measures ICC** y **Average measures ICC**; la pagina afirma que el Average
  measures ICC es "always higher than the Single measures ICC", sin formula.
- Ejemplo numerico que da la pagina para separar los dos conceptos: los pares (2,4), (4,6) y (6,8)
  tienen **consistency = 1.0** pero **absolute agreement = 0.6667**.
- IC 95 % reportado, sin metodo publicado.

**Referencias que cita la pagina:** McGraw KO, Wong SP (1996) Forming inferences about some intraclass correlation coefficients. Psychological Methods 1:30-46. | Shrout PE, Fleiss JL (1979) Intraclass correlations: uses in assessing rater reliability. Psychological Bulletin 86:420-428.

> [!tip] Para el laboratorio
> La eleccion consistency vs. absolute agreement es la que cambia el numero, y el ejemplo de la
> pagina lo muestra crudo: 1.0 contra 0.6667 con los mismos datos. Para repetibilidad entre
> operadores del mismo equipo (modelo 2) va **absolute agreement**.

---

## Cronbach's alpha

`cronbach-alpha.php` - https://www.medcalc.org/en/manual/cronbach-alpha.php

**No publica ninguna formula.** Define en palabras:

- alpha: "a widely used measure of internal consistency reliability", "ranges from 0 to 1",
  "calculates the average correlation among all items in a scale or questionnaire".
- **Inter-Item correlation:** "The average of these is the Inter-Item correlation".
- **Item-Total correlation:** "examines the correlation between each variable i and the totals
  obtained by summing all **other** variables" — tambien llamada "Item-Rest" o "Item-Remainder".
- Calcula ademas el alpha con cada item descartado por turno.
- Umbral que publica, citando Bland & Altman 1997: "For research purposes alpha should be more than
  0.7 to 0.8, but for clinical purposes alpha should at least be 0.90".

**Intervalo de confianza.** "Cronbach's alpha is given with its lower confidence limit (Feldt, 1965)."
Solo limite inferior, y sin metodo publicado.

**Referencias que cita la pagina:** Cronbach LJ (1951) | Bland JM, Altman DG (1997) | Feldt LS (1965).

---

## Correlation (Pearson)

`correlation.php` - https://www.medcalc.org/en/manual/correlation.php

**No publica la formula de r.** Lo que si dice:

- "The Pearson correlation coefficient is a number between -1 and 1"; "correlation expresses the
  degree that, on an average, two variables change correspondingly".
- **Supuesto, literal:** "The two variables should be random samples, and should have a Normal
  distribution (possibly after transformation)."
- P-value: "the probability that you would have found the current result if the correlation
  coefficient were in fact zero (null hypothesis)", con umbral convencional 5 % (P<0.05).
  Sin estadistico de prueba publicado.
- Reporta "95% Confidence interval for r" **sin decir el metodo** — la pagina no menciona la
  transformacion z de Fisher.

**Referencias que cita la pagina:** Armitage P, Berry G, Matthews JNS (2002) | Bland M (2000) | Altman DG (1991).

---

## Rank correlation (Spearman rho / Kendall tau)

`rank-correlation.php` - https://www.medcalc.org/en/manual/rank-correlation.php

**No publica formulas.** Describe el metodo: "Instead of using the precise values of the variables,
the data are ranked in order of size, and calculations are based on the differences between the ranks
of corresponding values X and Y."

**Intervalo de confianza — dato util y especifico:** solo para Kendall tau, y por bootstrap:
"The confidence interval for Kendall's *tau* is estimated using the bias-corrected and accelerated
(BCa) bootstrap (Efron, 1987; Efron & Tibshirani, 1993)." Para Spearman rho **no declara metodo de IC**.
Manejo de empates: no lo trata.

**Referencias que cita la pagina:** Efron B (1987) Better Bootstrap Confidence Intervals. JASA 82:171-185. | Efron B, Tibshirani RJ (1993) An introduction to the Bootstrap. Chapman & Hall/CRC. | Altman, Armitage, Bland.

---

## Partial correlation

`partialcorrelation.php` - https://www.medcalc.org/en/manual/partialcorrelation.php

**No publica ninguna formula**, ni grados de libertad, ni prueba de significacion, ni metodo de IC,
ni supuestos. Solo el proposito — "Use Partial correlation when you suspect the relationship between
2 variables to be influenced by other variables" — y que el coeficiente "is said to be adjusted or
corrected for the influence by the different covariates". Remite a Wikipedia para la definicion.

**Referencias que cita la pagina:** Altman DG (1991) Practical statistics for medical research. London: Chapman and Hall.

---

## Correlation coefficient significance test

`test-correlation.php` - https://www.medcalc.org/en/manual/test-correlation.php

Calculadora independiente: se le entrega un `r` observado y un `n` (minimo > 3 pares) y devuelve
P y el IC 95 % de r. **No publica el estadistico de prueba ni el metodo del IC.** El P-value se
define como "the probability to find the observed correlation coefficient (or larger) in the sample,
under the hypothesis that the population correlation coefficient is 0".

**Referencias que cita la pagina:** Bland M (2000) | Altman DG (1991).

---

## Correlation table

`correlationtable.php` - https://www.medcalc.org/en/manual/correlationtable.php

Utilidad de presentacion, no procedimiento inferencial nuevo. **Sin formulas y sin referencias.**
Ofrece Pearson (parametrica) o Spearman (no parametrica), opcion de mostrar P-values y tamanos de
muestra, ocultar el triangulo superior redundante, y un **correlograma** con celdas coloreadas
"from dark red for positive correlations to dark blue for negative correlations".

> [!warning] Sin correccion por comparaciones multiples
> La pagina **no menciona ningun ajuste** por multiplicidad. Una tabla de correlaciones de k
> variables son k(k-1)/2 pruebas simultaneas y los P-values salen sin corregir.

---

## Enlaces

- [[MedCalc - Mapa]]
- [[MedCalc - Procedimientos estadisticos]]
- [[MedCalc - Formulas - Comparacion de metodos y concordancia]] — el ICC y el CCC son los que se usan al lado del Bland-Altman
- [[MedCalc - Funciones (referencia completa)]]
