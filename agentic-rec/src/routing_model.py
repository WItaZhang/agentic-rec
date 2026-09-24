"""Small full-information utility router architecture; fitting belongs to the trainer."""

from dataclasses import dataclass

import numpy as np


def build_quality_estimator(config, seed):
    if config["kind"] == "ridge":
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler

        return make_pipeline(StandardScaler(), Ridge(alpha=config["alpha"]))
    if config["kind"] == "histogram_boosting":
        from sklearn.ensemble import HistGradientBoostingRegressor
        from sklearn.multioutput import MultiOutputRegressor

        return MultiOutputRegressor(HistGradientBoostingRegressor(
            max_iter=config["max_iter"], max_leaf_nodes=config["max_leaf_nodes"],
            min_samples_leaf=config["min_samples_leaf"], l2_regularization=config["l2_regularization"],
            learning_rate=config["learning_rate"], early_stopping=False, random_state=seed), n_jobs=1)
    raise ValueError("Unknown router estimator")


@dataclass
class UtilityRouter:
    estimator: object
    plans: tuple
    feature_names: tuple
    expected_usd: tuple
    cost_weight: float

    def decide(self, feature_rows):
        if self.plans[0] != "R0" or self.expected_usd[0] != 0:
            raise ValueError("The first action must be the zero-incremental-API baseline")
        x = np.array([[row[name] for name in self.feature_names] for row in feature_rows])
        delta = np.clip(np.asarray(self.estimator.predict(x)), -1, 1)
        if delta.shape != (len(x), len(self.plans) - 1):
            raise ValueError("Estimator output does not match the frozen action space")
        gain = np.column_stack([np.zeros(len(x)), delta])
        utilities = gain - self.cost_weight * 1000 * np.asarray(self.expected_usd)
        # Deterministic tie preference uses configured action order, starting with R0.
        return [self.plans[int(index)] for index in np.argmax(utilities, axis=1)]
