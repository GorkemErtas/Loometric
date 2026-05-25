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


@dataclass(frozen=True)
class MaeChange:
    absolute: float
    relative_percent: float | None


def mae_change(candidate: float, reference: float) -> MaeChange:
    """Candidate minus reference; negative is improvement; zero reference is undefined."""
    return MaeChange(
        candidate - reference, 100 * (candidate - reference) / reference if reference else None
    )


@dataclass(frozen=True)
class PredictionDiagnostics:
    residual_quantiles: dict[str, float]
    residual_std: float
    residual_bins: dict[str, int]
    prediction_min: float
    prediction_max: float
    below_zero: int
    above_one: int
    outside_training_target_range: int


def prediction_diagnostics(
    actual: pd.Series, predicted: pd.Series, training_target: pd.Series
) -> PredictionDiagnostics:
    """Residual = prediction - actual; 1 is a review threshold, not a proven upper bound."""
    regression_metrics(actual, predicted)  # Validate alignment/completeness before arithmetic.
    residuals = predicted - actual
    edges = [-float("inf"), -0.2, -0.1, 0.0, 0.1, 0.2, float("inf")]
    labels = ("(-inf,-0.2]", "(-0.2,-0.1]", "(-0.1,0]", "(0,0.1]", "(0.1,0.2]", "(0.2,inf)")
    bins = pd.cut(residuals, edges, labels=labels).value_counts(sort=False)
    return PredictionDiagnostics(
        residual_quantiles={
            str(q): float(residuals.quantile(q)) for q in (0.0, 0.05, 0.25, 0.5, 0.75, 0.95, 1.0)
        },
        residual_std=float(residuals.std(ddof=0)),
        residual_bins={str(label): int(count) for label, count in bins.items()},
        prediction_min=float(predicted.min()),
        prediction_max=float(predicted.max()),
        below_zero=int(predicted.lt(0).sum()),
        above_one=int(predicted.gt(1).sum()),
        outside_training_target_range=int(
            (predicted.lt(training_target.min()) | predicted.gt(training_target.max())).sum()
        ),
    )
