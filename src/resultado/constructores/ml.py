"""Machine learning: Random Forest de clasificación y de regresión.

Los modelos son los de scikit-learn (`src/core/random_forest.py`). Cambian a
propósito, cada uno con su test:

- Todo el desempeño que se informa es fuera de muestra: cada caso se predice
  con un modelo que no lo vio (validación cruzada). El de entrenamiento queda
  solo como referencia de cuánto memoriza.
- Se compara contra lo que se logra sin modelo: adivinar siempre la clase más
  frecuente, o predecir siempre la media. Una exactitud de 0,90 con 90 % de
  una clase es no haber aprendido nada.
- La importancia de cada predictora es por permutación en la partición de
  prueba; la de impureza, la de antes, favorece a las continuas aunque sean
  ruido. El gráfico observado contra predicho usa las predicciones fuera de
  muestra (antes, las de entrenamiento).
"""
from __future__ import annotations

import numpy as np
from scipy import stats

from src.core.random_forest import RandomForestClassifier, RandomForestRegressor
from src.core.roc import auc_delong
from src.resultado.citas import ficha
from src.resultado.datos import columnas_faltantes, filas_completas
from src.resultado.lenguaje import num, p_token
from src.resultado.modelo import Figura, Metodo, Resultado, Supuesto, Valor

MAX_CLASES = 20
MIN_CASOS = 10
POR_PREDICTORA = 10


def _lista(cols):
    if isinstance(cols, str):
        cols = [cols]
    return list(dict.fromkeys(cols or []))


def _armar(analisis, titulo, entrada, valores, metodo, supuestos, lectura, matiz,
           advertencias=(), figuras=(), crudo=None) -> Resultado:
    f = ficha(analisis)
    return Resultado(analisis=analisis, titulo=titulo, entrada=entrada, valores=valores,
                     metodo=metodo, supuestos=list(supuestos), formula=f.formula,
                     citas=list(f.citas), lectura=lectura, matiz=matiz,
                     advertencias=list(advertencias), figuras=list(figuras), crudo=crudo or {})


def _datos(analisis, titulo, df, respuesta, predictoras):
    predictoras = [p for p in _lista(predictoras) if p != respuesta]
    if not predictoras:
        return None, None, None, None, Resultado.rechazo(
            analisis, titulo, "Tildá al menos una predictora, distinta de la respuesta.")
    falta = columnas_faltantes(df, respuesta, *predictoras)
    if falta:
        return None, None, None, None, Resultado.rechazo(analisis, titulo, falta)
    filas, entrada = filas_completas(df, respuesta, *predictoras)
    try:
        X = filas[predictoras].to_numpy(dtype=float)
        y = filas[respuesta].to_numpy(dtype=float)
    except (TypeError, ValueError):
        return None, None, None, None, Resultado.rechazo(
            analisis, titulo, "La respuesta y las predictoras tienen que ser números (una "
                              "categórica, codificada 0/1 o 1, 2, 3).", entrada)
    if len(y) < MIN_CASOS:
        return None, None, None, None, Resultado.rechazo(
            analisis, titulo, f"Hacen falta al menos {MIN_CASOS} casos; hay {len(y)}.", entrada)
    return X, y, predictoras, entrada, None


def _supuesto_tamano(n, p) -> Supuesto:
    ok = n >= POR_PREDICTORA * p
    return Supuesto(
        "¿Hay casos suficientes para tantas predictoras?",
        f"{n} casos, {p} predictora(s): {n / p:.0f} por predictora", "Sí" if ok else "No",
        ("La validación cruzada tiene datos para estimar el desempeño con algo de precisión."
         if ok else
         "Con pocos casos por predictora el bosque memoriza y la validación cruzada varía "
         "mucho de una partición a otra: el desempeño informado es poco preciso."), ok=ok)


def _valores_importancia(predictoras, ev) -> list[Valor]:
    orden = np.argsort(ev["importancia"])[::-1]
    return [Valor(f"Importancia — {predictoras[i]}", ev["importancia"][i],
                  nota=f"± {num(ev['importancia_de'][i], 2)} (caída del puntaje al desordenarla)")
            for i in orden[:10]]


MATIZ = ("La importancia dice cuánto usa el modelo cada predictora, no si la causa. Dos "
         "predictoras que se parecen se reparten la importancia. El modelo vale para casos "
         "como estos: en otra población, otro laboratorio u otro método, hay que volver a "
         "validarlo.")


# ============================================================
#  Clasificación
# ============================================================

def rf_clasificacion(df, clase, predictoras, opciones=None) -> Resultado:
    """Variable 1 = la clase (pocas categorías, codificadas con números)."""
    titulo = f"Random Forest (clasificación) — {clase}"
    X, y, predictoras, entrada, rechazo = _datos("rf_clasificacion", titulo, df, clase,
                                                 predictoras)
    if rechazo is not None:
        return rechazo
    clases, cuentas = np.unique(y, return_counts=True)
    if len(clases) < 2:
        return Resultado.rechazo("rf_clasificacion", titulo, "La clase tiene un solo valor.",
                                 entrada)
    if len(clases) > MAX_CLASES or not np.all(y == np.round(y)):
        return Resultado.rechazo("rf_clasificacion", titulo,
                                 f"«{clase}» tiene {len(clases)} valores distintos o decimales: "
                                 "parece una medición. Para una respuesta continua está Random "
                                 "Forest (regresión).", entrada)
    rf = RandomForestClassifier(n_trees=100, max_depth=8, random_state=42).fit(X, y)
    ev = rf.evaluar(X, y)
    falla = Resultado.rechazo_del_core("rf_clasificacion", titulo, ev, entrada)
    if falla is not None:
        return falla
    pred = ev["clases"][np.argmax(ev["oof"], axis=1)]
    aciertos = int(np.sum(pred == y))
    n = len(y)
    exactitud = aciertos / n
    base = cuentas.max() / n
    prueba = stats.binomtest(aciertos, n, base, alternative="greater")
    recalls = [np.mean(pred[y == c] == c) for c in clases]
    valores = [Valor("Casos", n), Valor("Clases", len(clases)),
               Valor("Exactitud (validación cruzada)", exactitud, decimales=3,
                     nota=f"k = {ev['k']} particiones"),
               Valor("Exactitud balanceada", float(np.mean(recalls)), decimales=3,
                     nota="promedio de la sensibilidad de cada clase"),
               Valor("Sin modelo (siempre la clase más frecuente)", base, decimales=3)]
    auc = None
    if len(clases) == 2:
        y01 = (y == clases[1]).astype(float)
        dl = auc_delong(y01, ev["oof"][:, 1])
        from sklearn.metrics import roc_auc_score
        auc = float(roc_auc_score(y01, ev["oof"][:, 1]))
        valores.append(Valor(f"AUC (validación cruzada, clase {num(clases[1])})", auc,
                             ic=dl.get("ci"), decimales=3))
    valores.append(Valor("Exactitud sobre el entrenamiento", rf.score(X, y), decimales=3,
                         nota="optimista: el modelo ya vio esos casos"))
    valores += _valores_importancia(predictoras, ev)
    supera = prueba.pvalue < 0.05
    supuestos = [
        Supuesto("¿Supera a adivinar siempre la clase más frecuente?",
                 f"exactitud {exactitud:.3f} contra {base:.3f}, {p_token(prueba.pvalue)}",
                 "Sí" if supera else "No",
                 ("El modelo aprende algo que la proporción de clases sola no da." if supera else
                  "Con estos datos el modelo no le gana a no tener modelo: la exactitud sale de "
                  "cuánto domina una clase, no de las predictoras."), ok=supera),
        _supuesto_tamano(n, len(predictoras)),
    ]
    if cuentas.min() / n < 0.10:
        supuestos.append(Supuesto(
            "¿Las clases están balanceadas?",
            f"la menos frecuente es el {100 * cuentas.min() / n:.0f} %", "No",
            "Con una clase rara la exactitud engaña: mirá la exactitud balanceada"
            + (" y el AUC." if auc is not None else "."), ok=False))
    return _armar(
        "rf_clasificacion", titulo, entrada, valores,
        Metodo("Random Forest de 100 árboles, validación cruzada estratificada",
               "Cada árbol se ajusta a un remuestreo de los casos con predictoras al azar en "
               "cada corte; la clase es el voto de los árboles. El desempeño se mide sobre "
               "casos que el modelo no vio."),
        supuestos,
        (f"Clasifica bien el {100 * exactitud:.0f} % de los casos que no vio, contra "
         f"{100 * base:.0f} % sin modelo."
         + (f" AUC {auc:.3f}." if auc is not None else "")),
        MATIZ,
        figuras=[Figura("Importancia por permutación",
                        lambda: _figura_importancia(predictoras, ev)),
                 Figura("Matriz de confusión (validación cruzada)",
                        lambda: _figura_confusion(y, pred, clases))],
        crudo={"evaluacion": ev, "predicho": pred, "base": base, "predictoras": predictoras})


# ============================================================
#  Regresión
# ============================================================

def rf_regresion(df, respuesta, predictoras, opciones=None) -> Resultado:
    """Variable 1 = la respuesta numérica."""
    titulo = f"Random Forest (regresión) — {respuesta}"
    X, y, predictoras, entrada, rechazo = _datos("rf_regresion", titulo, df, respuesta,
                                                 predictoras)
    if rechazo is not None:
        return rechazo
    if np.ptp(y) == 0:
        return Resultado.rechazo("rf_regresion", titulo, "La respuesta vale lo mismo en todos.",
                                 entrada)
    rf = RandomForestRegressor(n_trees=100, max_depth=8, random_state=42).fit(X, y)
    ev = rf.evaluar(X, y)
    falla = Resultado.rechazo_del_core("rf_regresion", titulo, ev, entrada)
    if falla is not None:
        return falla
    pred = ev["oof"]
    residuo = y - pred
    r2 = float(1 - np.sum(residuo ** 2) / np.sum((y - y.mean()) ** 2))
    valores = [Valor("Casos", len(y)),
               Valor("R² (validación cruzada)", r2, decimales=3,
                     nota=f"k = {ev['k']} particiones; 0 = predecir siempre la media"),
               Valor("Error absoluto medio (validación cruzada)", float(np.mean(np.abs(residuo)))),
               Valor("Raíz del error cuadrático medio", float(np.sqrt(np.mean(residuo ** 2)))),
               Valor("R² sobre el entrenamiento", rf.score(X, y), decimales=3,
                     nota="optimista: el modelo ya vio esos casos")]
    valores += _valores_importancia(predictoras, ev)
    supera = r2 > 0
    supuestos = [
        Supuesto("¿Predice mejor que la media?", f"R² fuera de muestra = {r2:.3f}",
                 "Sí" if supera else "No",
                 ("Las predictoras explican parte de la variación en casos que el modelo no vio."
                  if supera else
                  "En casos nuevos el modelo erra más que predecir siempre la media: no "
                  "aprendió nada útil de las predictoras."), ok=supera),
        _supuesto_tamano(len(y), len(predictoras)),
    ]
    return _armar(
        "rf_regresion", titulo, entrada, valores,
        Metodo("Random Forest de 100 árboles, validación cruzada",
               "Cada árbol se ajusta a un remuestreo de los casos; la predicción es el promedio "
               "de los árboles. El desempeño se mide sobre casos que el modelo no vio."),
        supuestos,
        (f"En casos que no vio, el modelo explica el {100 * r2:.0f} % de la variación de "
         f"{respuesta}." if supera else
         f"En casos que no vio, el modelo no predice {respuesta} mejor que su media."),
        "Un bosque no extrapola: fuera del rango de los datos predice el borde. " + MATIZ,
        figuras=[Figura("Observado contra predicho (validación cruzada)",
                        lambda: _figura_obs_pred(y, pred, respuesta)),
                 Figura("Importancia por permutación",
                        lambda: _figura_importancia(predictoras, ev))],
        crudo={"evaluacion": ev, "r2_cv": r2, "predictoras": predictoras})


# ============================================================
#  Figuras
# ============================================================

def _figura_importancia(predictoras, ev):
    import matplotlib.pyplot as plt

    orden = np.argsort(ev["importancia"])[::-1][:10]
    fig, ax = plt.subplots(figsize=(8, max(3, 0.5 * len(orden) + 1)))
    ax.barh(range(len(orden)), ev["importancia"][orden], xerr=ev["importancia_de"][orden],
            color='#4f6ef7', edgecolor='white', capsize=3)
    ax.set_yticks(range(len(orden)))
    ax.set_yticklabels([predictoras[i] for i in orden])
    ax.axvline(0, color='#9ca3af', lw=1)
    ax.invert_yaxis()
    ax.set_xlabel("Caída del puntaje al desordenarla")
    ax.set_title("Importancia por permutación", fontweight='bold')
    fig.tight_layout()
    return fig


def _figura_confusion(y, pred, clases):
    import matplotlib.pyplot as plt

    m = np.array([[np.sum((y == a) & (pred == b)) for b in clases] for a in clases])
    fig, ax = plt.subplots(figsize=(5 + 0.3 * len(clases), 4.5 + 0.3 * len(clases)))
    ax.imshow(m, cmap='Blues')
    for i in range(len(clases)):
        for j in range(len(clases)):
            ax.text(j, i, str(m[i, j]), ha='center', va='center',
                    color='white' if m[i, j] > m.max() / 2 else '#111827')
    etiquetas = [num(c) for c in clases]
    ax.set_xticks(range(len(clases)))
    ax.set_xticklabels(etiquetas)
    ax.set_yticks(range(len(clases)))
    ax.set_yticklabels(etiquetas)
    ax.set_xlabel("Predicha")
    ax.set_ylabel("Real")
    ax.set_title("Matriz de confusión (fuera de muestra)", fontweight='bold')
    fig.tight_layout()
    return fig


def _figura_obs_pred(y, pred, respuesta):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.5, 6))
    ax.scatter(y, pred, s=20, color='#4f6ef7', alpha=0.6)
    lims = [min(y.min(), pred.min()), max(y.max(), pred.max())]
    ax.plot(lims, lims, '--', color='#ef4444', lw=1.5, label="Predicción perfecta")
    ax.set_xlabel(f"{respuesta} observado")
    ax.set_ylabel("Predicho sin haberlo visto")
    ax.set_title("Observado contra predicho", fontweight='bold')
    ax.legend(framealpha=0.9)
    fig.tight_layout()
    return fig
