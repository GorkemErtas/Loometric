"""Common observations, descriptive tails/slices and explicit support counts."""

from dataclasses import asdict

import numpy as np
import pandas as pd

from loometric.evaluation import regression_metrics


def error_summary(actual: pd.Series, prediction: pd.Series) -> dict:
    metrics = asdict(regression_metrics(actual, prediction))
    residual = prediction.to_numpy() - actual.to_numpy()
    absolute = np.abs(residual)
    return {
        **metrics,
        "median_absolute_error": float(np.quantile(absolute, 0.5)),
        "p90_absolute_error": float(np.quantile(absolute, 0.9)),
        "p95_absolute_error": float(np.quantile(absolute, 0.95)),
        "worst_absolute_error": float(absolute.max()),
        "p95_positive_error": float(np.quantile(np.maximum(residual, 0), 0.95)),
        "signed_error_p05": float(np.quantile(residual, 0.05)),
        "signed_error_p95": float(np.quantile(residual, 0.95)),
        "predictions_below_zero": int(prediction.lt(0).sum()),
        "predictions_above_one": int(prediction.gt(1).sum()),
        "predictions_above_physical_envelope": int(prediction.gt(3).sum()),
    }


def analyze(actual: pd.Series, prediction: pd.Series, metadata: pd.DataFrame) -> dict:
    if not metadata.index.equals(actual.index):
        raise ValueError("ALIGNED_ERROR_METADATA_REQUIRED")
    groups = {}
    for column in (
        "stage",
        "shift_kind",
        "staffing_band",
        "workload_band",
        "interruption_band",
        "low_demand",
        "demand_censored",
    ):
        groups[column] = {}
        for value in sorted(metadata[column].unique(), key=str):
            index = metadata.index[metadata[column].eq(value)]
            groups[column][str(value)] = {
                **error_summary(actual.loc[index], prediction.loc[index]),
                "low_support": len(index) < 30,
            }
    periods = metadata.start_date.map(
        lambda day: f"{day.isocalendar().year}-W{day.isocalendar().week:02}"
    )
    groups["calendar_period"] = {
        period: error_summary(actual.loc[index], prediction.loc[index])
        for period in sorted(set(periods))
        for index in [periods.index[periods.eq(period)]]
    }
    ranked = sorted(actual.index, key=lambda oid: (-abs(prediction[oid] - actual[oid]), str(oid)))[
        :10
    ]
    return {
        "overall": error_summary(actual, prediction),
        "slices": groups,
        "worst_observations": [
            {
                "observation_id": oid,
                "actual": float(actual[oid]),
                "prediction": float(prediction[oid]),
                "error": float(prediction[oid] - actual[oid]),
                "stage": metadata.loc[oid, "stage"],
                "shift_kind": metadata.loc[oid, "shift_kind"],
            }
            for oid in ranked
        ],
    }
