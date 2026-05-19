"""A small ordinary least-squares pipeline; callers fit it on training rows only."""

from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from loometric.features import CATEGORICAL_FEATURES, NUMERIC_FEATURES, validate_feature_names


def build_linear_pipeline(columns: tuple[str, ...]) -> Pipeline:
    """Keep train-learned category vocabularies inside the estimator pipeline.

    Full dense one-hot coding retains symmetric unknown-category behavior (all
    zero for that feature). Redundant columns with an intercept are handled by
    least squares; individual coefficients are not identifiable causal effects.
    Unselected columns are explicitly dropped; no imputer, scaling, or clipping.
    """
    validate_feature_names(columns)
    categorical = [name for name in columns if name in CATEGORICAL_FEATURES]
    numeric = [name for name in columns if name in NUMERIC_FEATURES]
    transformers = []
    if categorical:
        transformers.append(
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", drop=None, sparse_output=False),
                categorical,
            )
        )
    if numeric:
        transformers.append(("numeric", "passthrough", numeric))
    return Pipeline(
        [
            ("preprocessing", ColumnTransformer(transformers, remainder="drop")),
            ("regression", LinearRegression(fit_intercept=True, copy_X=True, positive=False)),
        ]
    )
