"""Small declared mean/Ridge/forest/histogram models; fitted inputs are features only."""

from math import fsum

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from loometric.synthetic_ml.features import FEATURE_COLUMNS
from loometric.synthetic_training.configuration import BASELINES
from loometric.synthetic_training.data import CATEGORICAL, NUMERIC, require


def validate_matrix(X: pd.DataFrame) -> None:
    require(
        isinstance(X, pd.DataFrame)
        and tuple(X.columns) == FEATURE_COLUMNS
        and not X.empty
        and X.index.is_unique
        and not X.isna().any().any(),
        "EXACT_FEATURE_MATRIX_REQUIRED",
    )
    require(
        np.isfinite(X.loc[:, NUMERIC].to_numpy(dtype=float)).all(), "FINITE_FEATURE_MATRIX_REQUIRED"
    )
    require(
        all(isinstance(v, str) and v for c in CATEGORICAL for v in X[c]),
        "CANONICAL_CATEGORICAL_FEATURES_REQUIRED",
    )


class SchemaGuard(TransformerMixin, BaseEstimator):
    def fit(self, X, y=None):
        validate_matrix(X)
        if y is not None:
            require(
                isinstance(y, pd.Series)
                and X.index.equals(y.index)
                and np.isfinite(y).all()
                and y.ge(0).all(),
                "ALIGNED_FINITE_TRAINING_LABELS_REQUIRED",
            )
        self.n_features_in_ = len(FEATURE_COLUMNS)
        self.feature_names_in_ = np.array(FEATURE_COLUMNS, dtype=object)
        return self

    def transform(self, X):
        validate_matrix(X)
        return X

    def get_feature_names_out(self, input_features=None):
        return self.feature_names_in_


def workload_band(row) -> str:
    require(
        row["available_minutes"] * row["planned_workers"] > 0, "ZERO_CAPACITY_REQUIRES_ABSTENTION"
    )
    load = (
        row["order_quantity"]
        * row["standard_worker_minutes_per_piece"]
        / (row["available_minutes"] * row["planned_workers"])
    )
    return "low" if load <= 0.6 else "nominal" if load <= 1 else "high"


class MeanModel:
    """Transparent train-only means; sparse/unseen group fallback is explicit."""

    def __init__(self, name: str):
        require(name in BASELINES, "UNKNOWN_NAIVE_MODEL")
        self.name = name

    def fit(self, X: pd.DataFrame, y: pd.Series):
        validate_matrix(X)
        require(
            X.index.equals(y.index) and np.isfinite(y).all(),
            "ALIGNED_FINITE_TRAINING_LABELS_REQUIRED",
        )
        self.global_mean = fsum(float(v) for v in y) / len(y)
        self.groups = {}
        frame = X.loc[:, ["stage", "shift_kind"]].copy()
        frame["load_band"] = X.apply(workload_band, axis=1)
        frame["target"] = y
        for columns in (("stage",), ("stage", "shift_kind"), ("stage", "shift_kind", "load_band")):
            values = {}
            for key, group in frame.groupby(list(columns), sort=True):
                key = key if isinstance(key, tuple) else (key,)
                values[key] = (fsum(float(v) for v in group.target) / len(group), len(group))
            self.groups[columns] = values
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        validate_matrix(X)
        predictions = []
        for _, row in X.iterrows():
            point = self.global_mean
            keys = (str(row["stage"]), str(row["shift_kind"]), workload_band(row))
            depths = (
                ()
                if self.name == "global_mean"
                else (1,)
                if self.name == "stage_mean"
                else (3, 2, 1)
            )
            for depth in depths:
                columns = ("stage", "shift_kind", "load_band")[:depth]
                match = self.groups[columns].get(keys[:depth])
                if match and (self.name == "stage_mean" or match[1] >= 10):
                    point = match[0]
                    break
            predictions.append(point)
        return np.asarray(predictions, dtype=float)

    def state(self) -> dict:
        return {
            "model": self.name,
            "global_mean": self.global_mean,
            "minimum_group_support": 10,
            "groups": [
                {
                    "columns": list(columns),
                    "values": [
                        {"key": list(key), "mean": mean, "count": count}
                        for key, (mean, count) in values.items()
                    ],
                }
                for columns, values in self.groups.items()
            ],
        }


def build_model(spec: dict, seed: int):
    if spec["name"] in BASELINES:
        return MeanModel(spec["name"])
    family, parameters = spec["family"], spec["parameters"]
    preprocessor = ColumnTransformer(
        [
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False, drop=None),
                list(CATEGORICAL),
            ),
            ("numeric", StandardScaler() if family == "ridge" else "passthrough", list(NUMERIC)),
        ],
        remainder="drop",
    )
    if family == "ridge":
        estimator = Ridge(**parameters, solver="svd")
    elif family == "forest":
        estimator = RandomForestRegressor(**parameters, random_state=seed, n_jobs=1)
    elif family == "hist":
        estimator = HistGradientBoostingRegressor(
            **parameters,
            random_state=seed,
            learning_rate=0.05,
            early_stopping=False,
            categorical_features=None,
        )
    else:
        raise ValueError("UNSUPPORTED_MODEL_FAMILY")
    return Pipeline(
        [("schema", SchemaGuard()), ("preprocess", preprocessor), ("regression", estimator)]
    )


def model_metadata(model) -> dict:
    if isinstance(model, MeanModel):
        return {
            "preprocessing": "TRAINING_ONLY_GROUP_MEANS_WITH_EXPLICIT_FALLBACK",
            "state": model.state(),
        }
    preprocessor = model.named_steps["preprocess"]
    encoder = preprocessor.named_transformers_["categorical"]
    result = {
        "encoded_columns": list(preprocessor.get_feature_names_out()),
        "training_categories": {
            column: list(values)
            for column, values in zip(CATEGORICAL, encoder.categories_, strict=True)
        },
        "estimator_parameters": model.named_steps["regression"].get_params(),
    }
    scaler = preprocessor.named_transformers_["numeric"]
    if isinstance(scaler, StandardScaler):
        result["numeric_training_mean"] = list(scaler.mean_)
        result["numeric_training_scale"] = list(scaler.scale_)
    return result
