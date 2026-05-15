"""Regression arithmetic with explicit alignment and undefined-R² behavior."""

from dataclasses import dataclass
from math import fsum, isfinite, sqrt

import pandas as pd


@dataclass(frozen=True)
class RegressionMetrics:
    samples: int
    mae: float
    rmse: float
    r2: float | None
    bias: float


def regression_metrics(actual: pd.Series, predicted: pd.Series) -> RegressionMetrics:
    """Bias = mean(prediction - actual); R² is undefined for n<2 or constant actuals."""
    if not actual.index.equals(predicted.index) or actual.empty:
        raise ValueError("Metrics require nonempty, equally indexed actuals and predictions.")
    try:
        observed = [float(value) for value in actual]
        estimates = [float(value) for value in predicted]
    except (TypeError, ValueError) as exc:
        raise ValueError("Metric inputs must be numeric and complete.") from exc
    if not all(isfinite(value) for value in (*observed, *estimates)):
        raise ValueError("Metric inputs must be finite; no rows are silently dropped.")
    n = len(observed)
    residuals = [
        prediction - target for target, prediction in zip(observed, estimates, strict=True)
    ]
    squared_error = fsum(value * value for value in residuals)
    mean = fsum(observed) / n
    total_variation = fsum((value - mean) ** 2 for value in observed)
    return RegressionMetrics(
        samples=n,
        mae=fsum(abs(value) for value in residuals) / n,
        rmse=sqrt(squared_error / n),
        r2=1 - squared_error / total_variation if n >= 2 and total_variation > 0 else None,
        bias=fsum(residuals) / n,
    )
