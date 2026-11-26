"""One fixed residual fit over the frozen foundation, with an explicit physical head."""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from loometric.final_candidate.history import HISTORY_COLUMNS
from loometric.ml_research.features import PlannedFeatures
from loometric.prospective_evaluation.source import require
from loometric.synthetic_ml.features import FEATURE_COLUMNS
from loometric.synthetic_training.data import CATEGORICAL
from loometric.synthetic_training.risk import support_profile

MODEL_COLUMNS = (*FEATURE_COLUMNS, *HISTORY_COLUMNS)


class HistoryBoost:
    def __init__(self, foundation, parameters: dict):
        self.foundation = foundation
        self.parameters = parameters

    def _matrix(self, X: pd.DataFrame) -> pd.DataFrame:
        require(
            tuple(X.columns) == MODEL_COLUMNS and not X.empty, "EXACT_HISTORY_FEATURES_REQUIRED"
        )
        base = X.loc[:, FEATURE_COLUMNS]
        result = PlannedFeatures().transform(base)
        for column in HISTORY_COLUMNS:
            result[column] = X[column].astype(float)
        result["foundation_prediction"] = self.foundation.predict(base)
        return result

    def fit(self, X: pd.DataFrame, y: pd.Series):
        require(not hasattr(self, "residual_model"), "SINGLE_ESTIMATOR_FIT_ONLY")
        require(X.index.equals(y.index) and np.isfinite(y).all(), "ALIGNED_TRAINING_REQUIRED")
        frame = self._matrix(X)
        numeric = [c for c in frame if c not in CATEGORICAL]
        self.residual_model = Pipeline(
            [
                (
                    "preprocess",
                    ColumnTransformer(
                        [
                            (
                                "categorical",
                                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                                list(CATEGORICAL),
                            ),
                            ("numeric", "passthrough", numeric),
                        ]
                    ),
                ),
                (
                    "regression",
                    HistGradientBoostingRegressor(**self.parameters, categorical_features=None),
                ),
            ]
        )
        self.residual_model.fit(frame, y.to_numpy() - frame.foundation_prediction.to_numpy())
        self.input_profile = support_profile(X.loc[:, FEATURE_COLUMNS], y)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        frame = self._matrix(X)
        raw = frame.foundation_prediction.to_numpy() + self.residual_model.predict(frame)
        require(np.isfinite(raw).all(), "FINITE_CANDIDATE_OUTPUT_REQUIRED")
        # A predeclared model head, not a post-hoc repair selected from evaluation errors.
        return np.minimum(np.maximum(raw, 0), frame.planned_load_ratio.to_numpy())
