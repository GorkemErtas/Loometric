"""Mean-only reference predictors. Prediction APIs cannot consume shift outcomes."""

from dataclasses import dataclass
from math import fsum, isfinite

import pandas as pd


def _mean(target: pd.Series) -> float:
    try:
        values = [float(value) for value in target]
    except (TypeError, ValueError) as exc:
        raise ValueError("Training targets must be numeric and complete.") from exc
    if not values or not all(isfinite(value) for value in values):
        raise ValueError("Training targets must be nonempty and finite.")
    return fsum(values) / len(values)


@dataclass(frozen=True)
class GlobalMeanBaseline:
    mean: float

    @classmethod
    def fit(cls, training_target: pd.Series) -> "GlobalMeanBaseline":
        return cls(_mean(training_target))

    def predict(self, index: pd.Index) -> pd.Series:
        """No feature values are needed; preserve row alignment."""
        return pd.Series(self.mean, index=index, dtype="float64", name="prediction")


@dataclass(frozen=True)
class DepartmentMeanBaseline:
    global_mean: float
    department_means: dict[str, float]

    @classmethod
    def fit(cls, departments: pd.Series, training_target: pd.Series) -> "DepartmentMeanBaseline":
        if not departments.index.equals(training_target.index) or departments.isna().any():
            raise ValueError("Training departments must be complete and aligned with targets.")
        global_mean = _mean(training_target)
        means = {
            str(department): _mean(training_target.loc[departments.eq(department)])
            for department in sorted(departments.unique())
        }
        return cls(global_mean, means)

    def predict(self, departments: pd.Series) -> pd.Series:
        """Unknown or missing departments fall back to the global training mean."""
        return (
            departments.map(self.department_means)
            .fillna(self.global_mean)
            .astype("float64")
            .rename("prediction")
        )
