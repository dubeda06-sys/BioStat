# Referencia MedCalc dentro del repo

Estas notas viven normalmente en el vault de Obsidian, que **no se versiona**
(`Obsidian/` está en `.gitignore` del repo de notas). Se copiaron acá porque el
primer ciclo de trabajo —la capa de guía sobre validación de métodos— las necesita
y de otro modo no viajan a otra máquina.

| Archivo | Qué trae |
|---|---|
| `Comparacion de metodos y concordancia.md` | Bland-Altman completo (LoA paramétricos y no paramétricos, LoA dependientes de la magnitud, LoAA, coeficiente de repetibilidad, máxima diferencia permitida), Passing-Bablok, Deming, comparación de múltiples métodos |
| `Correlacion, acuerdo y confiabilidad.md` | CCC de Lin, ICC, kappa |
| `Control de calidad y variabilidad analitica.md` | Westgard, CV, imprecisión |
| `Brechas contra MedCalc.md` | Qué cubre BioStat de los 109 procedimientos de MedCalc y qué no |

**Cada fórmula lleva la URL del manual de donde salió.** Verificadas contra
`medcalc.org/en/manual/`. Ojo: la versión en español del manual (`/es/manual/`)
devuelve **HTTP 403** desde la red del laboratorio; la terminología en castellano se
sacó del binario, no de la web.

No edites estos archivos acá: son una copia. La fuente está en el vault.
