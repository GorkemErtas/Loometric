"""Fixed EXP-003 forest profiles and the shared pre-shift preprocessing pipeline."""

from collections.abc import Sequence
from dataclasses import dataclass
from math import fsum, isfinite

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline

from loometric.features import FEATURE_SETS
from loometric.preprocessing import build_preprocessor

FOREST_FEATURE_SETS = (
    ("A", dict(FEATURE_SETS)["department_team"]),
    ("B", dict(FEATURE_SETS)["department_team_calendar"]),
)


@dataclass(frozen=True)
class ForestConfiguration:
    name: str
    n_estimators: int
    max_depth: int | None
    min_samples_leaf: int


# Declared before observing EXP-003 validation results; never adapt in the runner.
FOREST_CONFIGURATIONS = (
    ForestConfiguration("RF-01", n_estimators=100, max_depth=3, min_samples_leaf=20),
    ForestConfiguration("RF-02", n_estimators=200, max_depth=6, min_samples_leaf=10),
    ForestConfiguration("RF-03", n_estimators=300, max_depth=None, min_samples_leaf=2),
)


def build_forest_pipeline(columns: tuple[str, ...], config: ForestConfiguration) -> Pipeline:
    """Training-only fitting is the caller's responsibility; no random partitioning."""
    return Pipeline(
        [
            ("preprocessing", build_preprocessor(columns)),
            (
                "regression",
                RandomForestRegressor(
                    n_estimators=config.n_estimators,
                    max_depth=config.max_depth,
                    min_samples_leaf=config.min_samples_leaf,
                    random_state=42,
                    n_jobs=1,
                    criterion="squared_error",
                    max_features=1.0,
                    bootstrap=True,
                    min_samples_split=2,
                    max_samples=None,
                    oob_score=False,
                    warm_start=False,
                ),
            ),
        ]
    )


@dataclass(frozen=True)
class FeatureImportance:
    encoded: dict[str, float]
    grouped: dict[str, float]


def summarize_importance(
    preprocessing: ColumnTransformer, values: Sequence[float]
) -> FeatureImportance:
    """Sum training impurity importance across each feature's encoded columns.

    This is descriptive training attribution, never causal or a selection criterion.
    Cardinality, split opportunities, redundant indicators, and correlation affect it.
    """
    names = preprocessing.get_feature_names_out()
    importance = [float(value) for value in values]
    if len(names) != len(importance) or not all(
        isfinite(value) and value >= 0 for value in importance
    ):
        raise ValueError("Importance must be finite, nonnegative, and match encoded columns.")
    grouped: dict[str, float] = {}
    for name, transformer, columns in preprocessing.transformers_:
        if name == "categorical":
            position = preprocessing.output_indices_[name].start
            for column, categories in zip(columns, transformer.categories_, strict=True):
                width = len(categories)
                grouped[str(column)] = fsum(importance[position : position + width])
                position += width
        elif name == "numeric":
            position = preprocessing.output_indices_[name].start
            for offset, column in enumerate(columns):
                grouped[str(column)] = importance[position + offset]
    return FeatureImportance(dict(zip(names, importance, strict=True)), grouped)
