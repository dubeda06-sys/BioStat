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
