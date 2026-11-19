"""Pure retrospective diagnostics over aligned saved predictions; no model fitting."""

from dataclasses import asdict, dataclass
from math import ceil, fsum

import pandas as pd

from loometric.evaluation import RegressionMetrics, regression_metrics

ANALYZED_MODELS = ("department_mean", "linear_A", "forest_B_RF-01")
HIGH_ERROR_THRESHOLD = 0.30
MIN_GROUP_ROWS = 20
TAIL_FRACTIONS = (0.01, 0.05, 0.10)


@dataclass(frozen=True)
class ErrorConcentration:
    rows: int
    absolute_error_share: float | None
    squared_error_share: float | None
    remaining_mae: float | None


@dataclass(frozen=True)
class ErrorSummary:
    metrics: RegressionMetrics
    observed_dates: int
    low_support: bool
    absolute_quantiles: dict[str, float]
    signed_quantiles: dict[str, float]
    high_error_rows: int
    high_error_fraction: float
    concentration: dict[str, ErrorConcentration]


def build_error_rows(population: pd.DataFrame, predictions: dict[str, pd.Series]) -> pd.DataFrame:
    """Preserve identical observation identities across the three fixed models."""
    required = {"date", "fold", "department", "team", "actual"}
    if not required.issubset(population.columns) or population.empty:
        raise ValueError("Error analysis requires a nonempty, complete observation population.")
    if (
        not population.index.is_unique
        or population.loc[:, sorted(required)].isna().any().any()
        or not pd.api.types.is_datetime64_any_dtype(population["date"])
        or set(predictions) != set(ANALYZED_MODELS)
    ):
        raise ValueError("Observation identities, dates, groups, and fixed models must be valid.")
    frames = []
    for model in ANALYZED_MODELS:
        predicted = predictions[model]
        regression_metrics(population["actual"], predicted)
        frame = population.copy(deep=True)
        frame["row_index"] = population.index
        frame["model"] = model
        frame["prediction"] = predicted
        frame["error"] = predicted - frame["actual"]
        frame["absolute_error"] = frame["error"].abs()
        frame["squared_error"] = frame["error"] ** 2
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def summarize_errors(frame: pd.DataFrame) -> ErrorSummary:
    """Quantiles and tails are descriptive; no rows leave the primary metrics."""
    metrics = regression_metrics(frame["actual"], frame["prediction"])
    ranked = frame.sort_values(["absolute_error", "row_index"], ascending=[False, True])
    absolute = frame["absolute_error"]
    total_absolute = fsum(absolute)
    total_squared = fsum(frame["squared_error"])
    concentration = {}
    for fraction in TAIL_FRACTIONS:
        count = ceil(len(frame) * fraction)
        tail = ranked.iloc[:count]
        remaining = ranked.iloc[count:]
        concentration[str(fraction)] = ErrorConcentration(
            rows=count,
            absolute_error_share=fsum(tail["absolute_error"]) / total_absolute
            if total_absolute
            else None,
            squared_error_share=fsum(tail["squared_error"]) / total_squared
            if total_squared
            else None,
            remaining_mae=fsum(remaining["absolute_error"]) / len(remaining)
            if len(remaining)
            else None,
        )
    high_error_rows = int(absolute.ge(HIGH_ERROR_THRESHOLD).sum())
    return ErrorSummary(
        metrics=metrics,
        observed_dates=int(frame["date"].nunique()),
        low_support=len(frame) < MIN_GROUP_ROWS,
        absolute_quantiles={
            str(q): float(absolute.quantile(q))
            for q in (0.0, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0)
        },
        signed_quantiles={str(q): float(frame["error"].quantile(q)) for q in (0.05, 0.5, 0.95)},
        high_error_rows=high_error_rows,
        high_error_fraction=high_error_rows / len(frame),
        concentration=concentration,
    )


def grouped_error_summaries(frame: pd.DataFrame, keys: tuple[str, ...]) -> list[dict[str, object]]:
    """Always retain support counts; missing group cells are never invented."""
    summaries = []
    for key, group in frame.groupby(list(keys), sort=True, observed=True, dropna=False):
        values = key if isinstance(key, tuple) else (key,)
        summaries.append(
            {
                "group": {name: str(value) for name, value in zip(keys, values, strict=True)},
                "summary": asdict(summarize_errors(group)),
            }
        )
    return summaries


def target_distribution(frame: pd.DataFrame) -> dict[str, object]:
    """Use one copy of each target, not one copy per forecast model."""
    values = frame["actual"].astype(float)
    return {
        "samples": len(frame),
        "observed_dates": int(frame["date"].nunique()),
        "low_support": len(frame) < MIN_GROUP_ROWS,
        "mean": float(values.mean()),
        "std": float(values.std(ddof=0)),
        "quantiles": {
            str(q): float(values.quantile(q)) for q in (0.0, 0.05, 0.25, 0.5, 0.75, 0.95, 1.0)
        },
    }


def target_profiles(population: pd.DataFrame, keys: tuple[str, ...]) -> list[dict[str, object]]:
    profiles = []
    for key, group in population.groupby(list(keys), sort=True, observed=True, dropna=False):
        values = key if isinstance(key, tuple) else (key,)
        profiles.append(
            {
                "group": {name: str(value) for name, value in zip(keys, values, strict=True)},
                "distribution": target_distribution(group),
            }
        )
    return profiles


def team_stability(population: pd.DataFrame, errors: pd.DataFrame) -> list[dict[str, object]]:
    """Track the same stored department/team ID without assuming an unchanged roster."""
    result = []
    total_windows = int(population["fold"].nunique())
    for (department, team), group in population.groupby(["department", "team"], sort=True):
        windows = group.groupby("fold", sort=True)["actual"].agg(["count", "mean"])
        cell_errors = errors.loc[errors["department"].eq(department) & errors["team"].eq(team)]
        models = {}
        for model, subset in cell_errors.groupby("model", sort=True):
            by_window = subset.groupby("fold", sort=True).agg(
                mae=("absolute_error", "mean"), bias=("error", "mean")
            )
            models[str(model)] = {
                "min_fold_mae": float(by_window["mae"].min()),
                "max_fold_mae": float(by_window["mae"].max()),
                "fold_mae_range": float(by_window["mae"].max() - by_window["mae"].min()),
                "min_fold_bias": float(by_window["bias"].min()),
                "max_fold_bias": float(by_window["bias"].max()),
            }
        result.append(
            {
                "department": str(department),
                "team": str(team),
                "samples": len(group),
                "windows_present": len(windows),
                "total_windows": total_windows,
                "min_window_samples": int(windows["count"].min()),
                "low_window_support": bool(windows["count"].min() < MIN_GROUP_ROWS),
                "target_fold_mean_range": float(windows["mean"].max() - windows["mean"].min()),
                "window_targets": {
                    str(name): {"samples": int(row["count"]), "mean": float(row["mean"])}
                    for name, row in windows.iterrows()
                },
                "models": models,
            }
        )
    return result


def analyze_errors(
    population: pd.DataFrame, predictions: dict[str, pd.Series]
) -> dict[str, object]:
    errors = build_error_rows(population, predictions)
    slices = {
        "overall": ("model",),
        "department": ("model", "department"),
        "fold": ("model", "fold"),
        "date": ("model", "date"),
        "fold_department": ("model", "fold", "department"),
        "team": ("model", "department", "team"),
        "fold_team": ("model", "fold", "department", "team"),
    }
    baseline = errors.loc[errors["model"].eq("department_mean")].sort_values(
        ["absolute_error", "row_index"], ascending=[False, True]
    )
    excluded = set(baseline.iloc[: ceil(len(population) * 0.10)]["row_index"])
    retained = errors.loc[~errors["row_index"].isin(excluded)]
    worst = {}
    for model, group in errors.groupby("model", sort=True):
        ranked = group.sort_values(["absolute_error", "row_index"], ascending=[False, True]).head(
            10
        )
        local = ranked[
            [
                "row_index",
                "date",
                "fold",
                "department",
                "team",
                "actual",
                "prediction",
                "error",
                "absolute_error",
            ]
        ].copy()
        local["date"] = local["date"].dt.strftime("%Y-%m-%d")
        worst[str(model)] = local.to_dict(orient="records")
    return {
        "policy": {
            "high_error_threshold": HIGH_ERROR_THRESHOLD,
            "min_group_rows": MIN_GROUP_ROWS,
            "tail_fractions": TAIL_FRACTIONS,
            "common_tail_fraction": 0.10,
        },
        "population_rows": len(population),
        "summaries": {name: grouped_error_summaries(errors, keys) for name, keys in slices.items()},
        "target_distribution": target_distribution(population),
        "target_profiles": {
            "fold": target_profiles(population, ("fold",)),
            "department": target_profiles(population, ("department",)),
            "fold_department": target_profiles(population, ("fold", "department")),
        },
        "team_stability": team_stability(population, errors),
        "common_tail_sensitivity": {
            "selector": "department_mean largest absolute errors; row ID breaks ties",
            "excluded_rows": len(excluded),
            "remaining_rows": len(population) - len(excluded),
            "remaining_metrics": {
                str(model): asdict(regression_metrics(group["actual"], group["prediction"]))
                for model, group in retained.groupby("model", sort=True)
            },
        },
        "worst_observations_local_only": worst,
    }
