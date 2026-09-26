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
