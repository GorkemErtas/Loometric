"""A small ordinary least-squares pipeline; callers fit it on training rows only."""

from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline

from loometric.preprocessing import build_preprocessor


def build_linear_pipeline(columns: tuple[str, ...]) -> Pipeline:
    """Keep train-learned category vocabularies inside the estimator pipeline.

    Full dense one-hot coding retains symmetric unknown-category behavior (all
    zero for that feature). Redundant columns with an intercept are handled by
    least squares; individual coefficients are not identifiable causal effects.
    Unselected columns are explicitly dropped; no imputer, scaling, or clipping.
    """
    return Pipeline(
        [
            ("preprocessing", build_preprocessor(columns)),
            ("regression", LinearRegression(fit_intercept=True, copy_X=True, positive=False)),
        ]
    )
