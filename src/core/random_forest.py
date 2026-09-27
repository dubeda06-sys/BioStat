"""Random Forest (wrappers sobre scikit-learn).

Antes había una implementación casera de árboles cuyas importancias de
variables eran un placeholder uniforme (1/n). Ahora se delega en scikit-learn,
que da importancias reales (basadas en la reducción de impureza), manteniendo
la misma API que usa la UI: constructor(n_trees, max_depth, random_state),
fit / predict / score / get_feature_importance (+ predict_proba en el clasificador).
"""
from sklearn.ensemble import (
    RandomForestClassifier as _SKRFClassifier,
    RandomForestRegressor as _SKRFRegressor,
)


class RandomForestClassifier:
    def __init__(self, n_trees=100, max_depth=8, min_samples_split=5,
                 min_samples_leaf=2, random_state=42):
        self._model = _SKRFClassifier(
            n_estimators=n_trees, max_depth=max_depth,
            min_samples_split=min_samples_split, min_samples_leaf=min_samples_leaf,
            random_state=random_state, n_jobs=-1,
        )

    def fit(self, X, y):
        self._model.fit(X, y)
        return self

    def predict(self, X):
        return self._model.predict(X)

    def predict_proba(self, X):
        return self._model.predict_proba(X)

    def score(self, X, y):
        return self._model.score(X, y)

    def get_feature_importance(self):
        return self._model.feature_importances_

    def validacion_cruzada(self, X, y, k=5):
        """Exactitud por validacion cruzada estratificada. Ver _validar."""
        return _validar(self._model, X, y, k, clasificacion=True)

    def evaluar(self, X, y, k=5):
        """Predicciones fuera de muestra e importancia por permutacion."""
        return evaluar_fuera_de_muestra(self._model, X, y, clasificacion=True, k=k)


class RandomForestRegressor:
    def __init__(self, n_trees=100, max_depth=8, min_samples_split=5,
                 min_samples_leaf=2, random_state=42):
        self._model = _SKRFRegressor(
            n_estimators=n_trees, max_depth=max_depth,
            min_samples_split=min_samples_split, min_samples_leaf=min_samples_leaf,
            random_state=random_state, n_jobs=-1,
        )

    def fit(self, X, y):
        self._model.fit(X, y)
        return self

    def predict(self, X):
        return self._model.predict(X)

    def score(self, X, y):
        return self._model.score(X, y)

    def get_feature_importance(self):
        return self._model.feature_importances_

    def validacion_cruzada(self, X, y, k=5):
        """R2 por validacion cruzada. Ver _validar."""
        return _validar(self._model, X, y, k, clasificacion=False)

    def evaluar(self, X, y, k=5):
        """Predicciones fuera de muestra e importancia por permutacion."""
        return evaluar_fuera_de_muestra(self._model, X, y, clasificacion=False, k=k)


def _validar(modelo, X, y, k, clasificacion):
    """Desempeno sobre datos que el modelo NO vio al entrenarse.

    `score(X, y)` sobre los mismos datos del ajuste es optimista hasta el
    absurdo: con 5 predictoras de ruido puro daba exactitud 0,95, y la
    validacion cruzada da 0,56 (azar = 0,50) (auditoria 2026-09, K8). Se ajusta
    un clon en k-1 particiones y se evalua en la que quedo afuera, k veces.

    Returns: dict con media, de, k y el nombre de la metrica, o error.
    """
    import numpy as np
    from sklearn.base import clone
    from sklearn.model_selection import KFold, StratifiedKFold, cross_val_score

    y = np.asarray(y)
    if clasificacion:
        _, cuentas = np.unique(y, return_counts=True)
        k = int(min(k, cuentas.min()))
        if k < 2:
            return {"error": "Alguna clase tiene un solo caso: no se puede validar."}
        particion = StratifiedKFold(n_splits=k, shuffle=True, random_state=42)
        metrica = "exactitud"
    else:
        k = int(min(k, len(y) // 2))
        if k < 2:
            return {"error": "Muy pocos casos para validar."}
        particion = KFold(n_splits=k, shuffle=True, random_state=42)
        metrica = "R2"
    puntajes = cross_val_score(clone(modelo), X, y, cv=particion,
                               scoring="accuracy" if clasificacion else "r2")
    return {"media": float(np.mean(puntajes)), "de": float(np.std(puntajes, ddof=1)),
            "k": k, "metrica": metrica}


def _particion(y, k, clasificacion, semilla=42):
    import numpy as np
    from sklearn.model_selection import KFold, StratifiedKFold

    if clasificacion:
        _, cuentas = np.unique(y, return_counts=True)
        k = int(min(k, cuentas.min()))
        if k < 2:
            return None, "Alguna clase tiene un solo caso: no se puede validar."
        return StratifiedKFold(n_splits=k, shuffle=True, random_state=semilla), None
    k = int(min(k, len(y) // 2))
    if k < 2:
        return None, "Muy pocos casos para validar."
    return KFold(n_splits=k, shuffle=True, random_state=semilla), None


def evaluar_fuera_de_muestra(modelo, X, y, clasificacion, k=5, n_repeticiones=5, semilla=42):
    """Predicciones de validacion cruzada e importancia por permutacion.

    Cada caso se predice con un modelo que no lo vio (`oof`: out of fold). La
    importancia de una predictora es cuanto empeora el puntaje en la particion
    de prueba al desordenarla, promediado sobre particiones y repeticiones: la
    de impureza (`feature_importances_`) se mide sobre el entrenamiento y
    favorece a las continuas con muchos valores distintos aunque sean ruido
    (Strobl et al. 2007).
    """
    import numpy as np
    from sklearn.base import clone

    X, y = np.asarray(X, dtype=float), np.asarray(y)
    particion, error = _particion(y, k, clasificacion, semilla)
    if error:
        return {"error": error}
    rng = np.random.default_rng(semilla)
    clases = np.unique(y) if clasificacion else None
    oof = (np.zeros((len(y), len(clases))) if clasificacion else np.zeros(len(y)))

    def puntaje(real, pred):
        if clasificacion:
            return np.mean(pred == real, axis=-1)
        return 1 - (np.sum((real - pred) ** 2, axis=-1)
                    / np.sum((real - real.mean()) ** 2))

    p = X.shape[1]
    importancias = []
    for entreno, prueba in particion.split(X, y):
        # Un hilo: con n_jobs=-1 cada fit y cada predict abren su pool de hilos,
        # y con n de laboratorio eso cuesta mas que el calculo (x2 medido).
        m = clone(modelo).set_params(n_jobs=1).fit(X[entreno], y[entreno])
        Xt, yt = X[prueba], y[prueba]
        if clasificacion:
            proba = m.predict_proba(Xt)
            oof[np.ix_(prueba, np.searchsorted(clases, m.classes_))] = proba
            base = puntaje(yt, m.classes_[np.argmax(proba, axis=1)])
        else:
            oof[prueba] = m.predict(Xt)
            base = puntaje(yt, oof[prueba])
        # Todas las permutaciones del pliegue en un solo predict: cada llamada
        # a un bosque de 100 arboles cuesta ~90 ms fijos, y eran p x repeticiones.
        bloques = []
        for j in range(p):
            for _ in range(n_repeticiones):
                Xp = Xt.copy()
                Xp[:, j] = rng.permutation(Xp[:, j])
                bloques.append(Xp)
        pred = m.predict(np.vstack(bloques)).reshape(p, n_repeticiones, len(yt))
        importancias.append(base - puntaje(yt, pred))          # (p, repeticiones)
    todas = np.concatenate(importancias, axis=1)
    return {"oof": oof, "clases": clases, "k": particion.get_n_splits(),
            "importancia": todas.mean(axis=1), "importancia_de": todas.std(axis=1, ddof=1)}
