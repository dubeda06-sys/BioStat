"""Random Forest para clasificacion y regresion."""
import numpy as np
from collections import Counter


class DecisionTree:
    """Arbol de decision simple."""

    def __init__(self, max_depth=10, min_samples_split=5, min_samples_leaf=2):
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.tree = None

    def fit(self, X, y):
        self.n_features = X.shape[1]
        self.tree = self._build_tree(X, y, depth=0)
        return self

    def _build_tree(self, X, y, depth):
        n_samples = len(y)
        n_classes = len(np.unique(y))

        if depth >= self.max_depth or n_classes == 1 or n_samples < self.min_samples_split:
            if len(y) == 0:
                return {"leaf": True, "value": 0}
            vals, counts = np.unique(y, return_counts=True)
            return {"leaf": True, "value": vals[np.argmax(counts)], "proba": counts / counts.sum()}

        best_feat, best_thresh = self._best_split(X, y)
        if best_feat is None:
            vals, counts = np.unique(y, return_counts=True)
            return {"leaf": True, "value": vals[np.argmax(counts)], "proba": counts / counts.sum()}

        left_mask = X[:, best_feat] <= best_thresh
        right_mask = ~left_mask

        left = self._build_tree(X[left_mask], y[left_mask], depth + 1)
        right = self._build_tree(X[right_mask], y[right_mask], depth + 1)

        return {"leaf": False, "feature": best_feat, "threshold": best_thresh,
                "left": left, "right": right}

    def _best_split(self, X, y):
        best_gini = float("inf")
        best_feat, best_thresh = None, None

        features = np.random.choice(X.shape[1], size=max(1, int(np.sqrt(X.shape[1]))), replace=False)

        for feat in features:
            thresholds = np.unique(X[:, feat])
            for thresh in thresholds:
                left = y[X[:, feat] <= thresh]
                right = y[X[:, feat] > thresh]
                if len(left) < self.min_samples_leaf or len(right) < self.min_samples_leaf:
                    continue
                gini = self._gini_split(left, right, len(y))
                if gini < best_gini:
                    best_gini = gini
                    best_feat = feat
                    best_thresh = thresh

        return best_feat, best_thresh

    def _gini(self, y):
        if len(y) == 0:
            return 0
        _, counts = np.unique(y, return_counts=True)
        probs = counts / len(y)
        return 1 - np.sum(probs**2)

    def _gini_split(self, left, right, n_total):
        return (len(left)/n_total * self._gini(left) +
                len(right)/n_total * self._gini(right))

    def predict(self, X):
        return np.array([self._predict_one(x, self.tree) for x in X])

    def _predict_one(self, x, node):
        if node["leaf"]:
            return node["value"]
        if x[node["feature"]] <= node["threshold"]:
            return self._predict_one(x, node["left"])
        return self._predict_one(x, node["right"])

    def predict_proba(self, X):
        return np.array([self._predict_proba_one(x, self.tree) for x in X])

    def _predict_proba_one(self, x, node):
        if node["leaf"]:
            return node.get("proba", np.array([1.0]))
        if x[node["feature"]] <= node["threshold"]:
            return self._predict_proba_one(x, node["left"])
        return self._predict_proba_one(x, node["right"])


class RandomForestClassifier:
    """Random Forest para clasificacion."""

    def __init__(self, n_trees=100, max_depth=10, min_samples_split=5,
                 min_samples_leaf=2, max_features="sqrt", random_state=42):
        self.n_trees = n_trees
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.max_features = max_features
        self.random_state = random_state
        self.trees = []
        self.feature_importances_ = None

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y)
        self.classes_ = np.unique(y)
        self.n_features = X.shape[1]
        rng = np.random.RandomState(self.random_state)

        self.trees = []
        importances = np.zeros(self.n_features)

        for _ in range(self.n_trees):
            n_samples = len(y)
            idx = rng.choice(n_samples, size=n_samples, replace=True)
            X_boot, y_boot = X[idx], y[idx]

            tree = DecisionTree(
                max_depth=self.max_depth,
                min_samples_split=self.min_samples_split,
                min_samples_leaf=self.min_samples_leaf
            )
            tree.fit(X_boot, y_boot)
            self.trees.append(tree)

            preds = tree.predict(X)
            for i in range(self.n_features):
                correct_before = np.sum(preds == y)
                perm_idx = rng.permutation(n_samples)
                X_perm = X.copy()
                X_perm[:, i] = X[perm_idx, i]
                preds_perm = tree.predict(X_perm)
                importances[i] += correct_before - np.sum(preds_perm == y)

        self.feature_importances_ = importances / np.sum(importances) if np.sum(importances) > 0 else importances / self.n_trees
        return self

    def predict(self, X):
        X = np.asarray(X, dtype=float)
        predictions = np.array([t.predict(X) for t in self.trees])
        result = []
        for i in range(X.shape[0]):
            votes = predictions[:, i]
            vals, counts = np.unique(votes, return_counts=True)
            result.append(vals[np.argmax(counts)])
        return np.array(result)

    def score(self, X, y):
        return np.mean(self.predict(X) == y)

    def get_feature_importance(self):
        return self.feature_importances_


class RandomForestRegressor:
    """Random Forest para regresion."""

    def __init__(self, n_trees=100, max_depth=10, min_samples_split=5,
                 min_samples_leaf=2, random_state=42):
        self.n_trees = n_trees
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.random_state = random_state
        self.trees = []
        self.feature_importances_ = None

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        self.n_features = X.shape[1]
        rng = np.random.RandomState(self.random_state)

        self.trees = []
        importances = np.zeros(self.n_features)

        for _ in range(self.n_trees):
            idx = rng.choice(len(y), size=len(y), replace=True)
            X_boot, y_boot = X[idx], y[idx]

            tree = DecisionTreeRegressor(
                max_depth=self.max_depth,
                min_samples_split=self.min_samples_split,
                min_samples_leaf=self.min_samples_leaf
            )
            tree.fit(X_boot, y_boot)
            self.trees.append(tree)

        self.feature_importances_ = np.ones(self.n_features) / self.n_features
        return self

    def predict(self, X):
        X = np.asarray(X, dtype=float)
        preds = np.array([t.predict(X) for t in self.trees])
        return np.mean(preds, axis=0)

    def score(self, X, y):
        y = np.asarray(y, dtype=float)
        y_pred = self.predict(X)
        ss_res = np.sum((y - y_pred)**2)
        ss_tot = np.sum((y - np.mean(y))**2)
        return 1 - ss_res / ss_tot if ss_tot > 0 else 0

    def get_feature_importance(self):
        # TODO(Fase 2): importancias placeholder (uniformes). Migrar a sklearn.ensemble.
        return self.feature_importances_


class DecisionTreeRegressor:
    """Arbol de decision para regresion."""

    def __init__(self, max_depth=10, min_samples_split=5, min_samples_leaf=2):
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.tree = None

    def fit(self, X, y):
        self.tree = self._build_tree(X, y, 0)
        return self

    def _build_tree(self, X, y, depth):
        n = len(y)
        if depth >= self.max_depth or n < self.min_samples_split:
            return {"leaf": True, "value": np.mean(y) if n > 0 else 0}

        best_feat, best_thresh, best_var = None, None, float("inf")
        features = np.random.choice(X.shape[1], size=max(1, int(np.sqrt(X.shape[1]))), replace=False)

        for feat in features:
            for thresh in np.unique(X[:, feat]):
                left = y[X[:, feat] <= thresh]
                right = y[X[:, feat] > thresh]
                if len(left) < self.min_samples_leaf or len(right) < self.min_samples_leaf:
                    continue
                var = (len(left)/n * np.var(left) + len(right)/n * np.var(right))
                if var < best_var:
                    best_var = var
                    best_feat = feat
                    best_thresh = thresh

        if best_feat is None:
            return {"leaf": True, "value": np.mean(y)}

        mask = X[:, best_feat] <= best_thresh
        return {"leaf": False, "feature": best_feat, "threshold": best_thresh,
                "left": self._build_tree(X[mask], y[mask], depth+1),
                "right": self._build_tree(X[~mask], y[~mask], depth+1)}

    def predict(self, X):
        return np.array([self._predict_one(x, self.tree) for x in X])

    def _predict_one(self, x, node):
        if node["leaf"]:
            return node["value"]
        if x[node["feature"]] <= node["threshold"]:
            return self._predict_one(x, node["left"])
        return self._predict_one(x, node["right"])
