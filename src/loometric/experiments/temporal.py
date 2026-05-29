"""EXP-004: fixed-model temporal robustness using only the original training period."""

import argparse
import json
import platform
import sys
from dataclasses import asdict, dataclass, field
from importlib.metadata import version
from pathlib import Path
from statistics import fmean, pstdev
from time import perf_counter

import pandas as pd

from loometric.baselines import DepartmentMeanBaseline, GlobalMeanBaseline
from loometric.data.loading import load_validated_csv
from loometric.data.profiling import fingerprint
from loometric.data.schema import TARGET
from loometric.data.splitting import (
    DEFAULT_CONFIG,
    SplitConfig,
    apply_split_config,
    load_split_config,
)
from loometric.data.temporal import (
    DEFAULT_POLICY,
    ExpandingWindowPolicy,
    TemporalFold,
    make_expanding_folds,
)
from loometric.evaluation import (
    MaeChange,
    PredictionDiagnostics,
    RegressionMetrics,
    mae_change,
    prediction_diagnostics,
    regression_metrics,
)
from loometric.features import SOURCE_COLUMNS, build_features
from loometric.forest import FOREST_CONFIGURATIONS, FOREST_FEATURE_SETS, build_forest_pipeline
from loometric.linear import build_linear_pipeline
from loometric.preprocessing import FeatureMetadata, inspect_preprocessor

# Freeze the already selected EXP-003 profile. This audit has no model-selection step.
FROZEN_FOREST = next(profile for profile in FOREST_CONFIGURATIONS if profile.name == "RF-01")
FROZEN_FEATURES = dict(FOREST_FEATURE_SETS)
MODEL_NAMES = ("global_mean", "department_mean", "linear_A", "linear_B", "forest_B_RF-01")
FOREST_NAME = MODEL_NAMES[-1]


@dataclass(frozen=True)
class WindowModelResult:
    columns: tuple[str, ...]
    estimator_parameters: dict[str, object]
    training_mae: float
    evaluation_metrics: RegressionMetrics
    department_metrics: dict[str, RegressionMetrics]
    diagnostics: PredictionDiagnostics
    features: FeatureMetadata
    training_seconds: float = field(compare=False)
    training_inference_seconds: float = field(compare=False)
    inference_seconds: float = field(compare=False)


@dataclass(frozen=True)
class FoldResult:
    fold: TemporalFold
    training_target_mean: float
    evaluation_target_mean: float
    models: dict[str, WindowModelResult]
    changes_vs_department: dict[str, MaeChange]


@dataclass(frozen=True)
class PooledResult:
    metrics: RegressionMetrics
    department_metrics: dict[str, RegressionMetrics]
    mean_fold_mae: float
    std_fold_mae: float
    min_fold_mae: float
    max_fold_mae: float
    change_vs_department: MaeChange


@dataclass(frozen=True)
class ComparisonCounts:
    wins: int
    losses: int
    ties: int


def comparison_counts(changes: list[float]) -> ComparisonCounts:
    """Candidate-minus-reference MAE differences; absolute 1e-12 is a tie."""
    if not changes or any(not pd.notna(value) or abs(value) == float("inf") for value in changes):
        raise ValueError("Comparison counts require finite, nonempty MAE differences.")
    return ComparisonCounts(
        wins=sum(value < -1e-12 for value in changes),
        losses=sum(value > 1e-12 for value in changes),
        ties=sum(abs(value) <= 1e-12 for value in changes),
    )


@dataclass(frozen=True)
class OutOfFoldPredictions:
    row_indices: tuple[int, ...]
    dates: tuple[str, ...]
    departments: tuple[str, ...]
    actuals: tuple[float, ...]
    predictions: dict[str, tuple[float, ...]]


@dataclass(frozen=True)
class ExperimentResult:
    split: SplitConfig
    policy: ExpandingWindowPolicy
    folds: tuple[FoldResult, ...]
    pooled: dict[str, PooledResult]
    forest_vs_department: ComparisonCounts
    forest_department_comparisons: dict[str, ComparisonCounts]
    out_of_fold: OutOfFoldPredictions


def _department_metrics(
    actual: pd.Series, predicted: pd.Series, departments: pd.Series
) -> dict[str, RegressionMetrics]:
    return {
        str(department): regression_metrics(actual.loc[group.index], predicted.loc[group.index])
        for department, group in departments.groupby(departments, sort=True)
    }


def run_experiment(
    data: pd.DataFrame, config: SplitConfig, *, dataset_sha256: str
) -> ExperimentResult:
    """Original validation/test frames never enter feature construction or scoring."""
    original_training = apply_split_config(data, config, dataset_sha256=dataset_sha256).train
    folds = make_expanding_folds(original_training, config.train, DEFAULT_POLICY)
    fold_results: list[FoldResult] = []
    evaluation_frames: list[pd.DataFrame] = []
    collected: dict[str, list[pd.Series]] = {name: [] for name in MODEL_NAMES}
    for fold in folds:
        training = original_training.loc[
            original_training["date"].between(fold.train.start, fold.train.end)
        ]
        evaluation = original_training.loc[
            original_training["date"].between(fold.evaluation.start, fold.evaluation.end)
        ]
        train_features = build_features(training.loc[:, SOURCE_COLUMNS])
        evaluation_features = build_features(evaluation.loc[:, SOURCE_COLUMNS])
        models: dict[str, WindowModelResult] = {}
        for name in MODEL_NAMES:
            columns = (
                ()
                if name == "global_mean"
                else ("department",)
                if name == "department_mean"
                else FROZEN_FEATURES["A"]
                if name == "linear_A"
                else FROZEN_FEATURES["B"]
            )
            started = perf_counter()
            if name == "global_mean":
                global_model = GlobalMeanBaseline.fit(training[TARGET])
            elif name == "department_mean":
                department_model = DepartmentMeanBaseline.fit(
                    training["department"], training[TARGET]
                )
            else:
                pipeline = (
                    build_forest_pipeline(columns, FROZEN_FOREST)
                    if name == FOREST_NAME
                    else build_linear_pipeline(columns)
                )
                pipeline.fit(train_features.loc[:, columns], training[TARGET])
            training_seconds = perf_counter() - started
            predicted: list[pd.Series] = []
            durations: list[float] = []
            for frame, features in ((training, train_features), (evaluation, evaluation_features)):
                started = perf_counter()
                if name == "global_mean":
                    prediction = global_model.predict(frame.index)
                elif name == "department_mean":
                    prediction = department_model.predict(frame["department"])
                else:
                    prediction = pd.Series(
                        pipeline.predict(features.loc[:, columns]),
                        index=frame.index,
                        dtype="float64",
                    )
                predicted.append(prediction)
                durations.append(perf_counter() - started)
            metadata = FeatureMetadata((), {}, {})
            if name == "global_mean":
                parameters: dict[str, object] = {"training_mean": global_model.mean}
            elif name == "department_mean":
                parameters = {
                    "training_global_mean": department_model.global_mean,
                    "training_department_means": department_model.department_means,
                }
            else:
                metadata = inspect_preprocessor(
                    pipeline.named_steps["preprocessing"], evaluation_features
                )
                parameters = pipeline.named_steps["regression"].get_params()
            models[name] = WindowModelResult(
                columns=columns,
                estimator_parameters=parameters,
                training_mae=regression_metrics(training[TARGET], predicted[0]).mae,
                evaluation_metrics=regression_metrics(evaluation[TARGET], predicted[1]),
                department_metrics=_department_metrics(
                    evaluation[TARGET], predicted[1], evaluation["department"]
                ),
                diagnostics=prediction_diagnostics(
                    evaluation[TARGET], predicted[1], training[TARGET]
                ),
                features=metadata,
                training_seconds=training_seconds,
                training_inference_seconds=durations[0],
                inference_seconds=durations[1],
            )
            collected[name].append(predicted[1])
        fold_results.append(
            FoldResult(
                fold=fold,
                training_target_mean=float(training[TARGET].mean()),
                evaluation_target_mean=float(evaluation[TARGET].mean()),
                models=models,
                changes_vs_department={
                    name: mae_change(
                        model.evaluation_metrics.mae,
                        models["department_mean"].evaluation_metrics.mae,
                    )
                    for name, model in models.items()
                },
            )
        )
        evaluation_frames.append(evaluation)
    pooled_data = pd.concat(evaluation_frames)
    if not pooled_data.index.is_unique:
        raise ValueError("Temporal evaluation windows must not repeat rows.")
    predictions = {name: pd.concat(values) for name, values in collected.items()}
    metrics = {
        name: regression_metrics(pooled_data[TARGET], values)
        for name, values in predictions.items()
    }
    pooled = {}
    for name in MODEL_NAMES:
        errors = [result.models[name].evaluation_metrics.mae for result in fold_results]
        pooled[name] = PooledResult(
            metrics=metrics[name],
            department_metrics=_department_metrics(
                pooled_data[TARGET], predictions[name], pooled_data["department"]
            ),
            mean_fold_mae=fmean(errors),
            std_fold_mae=pstdev(errors),
            min_fold_mae=min(errors),
            max_fold_mae=max(errors),
            change_vs_department=mae_change(metrics[name].mae, metrics["department_mean"].mae),
        )
    return ExperimentResult(
        split=config,
        policy=DEFAULT_POLICY,
        folds=tuple(fold_results),
        pooled=pooled,
        forest_vs_department=comparison_counts(
            [result.changes_vs_department[FOREST_NAME].absolute for result in fold_results]
        ),
        forest_department_comparisons={
            department: comparison_counts(
                [
                    result.models[FOREST_NAME].department_metrics[department].mae
                    - result.models["department_mean"].department_metrics[department].mae
                    for result in fold_results
                    if department in result.models[FOREST_NAME].department_metrics
                ]
            )
            for department in pooled[FOREST_NAME].department_metrics
        },
        out_of_fold=OutOfFoldPredictions(
            row_indices=tuple(int(index) for index in pooled_data.index),
            dates=tuple(pooled_data["date"].dt.strftime("%Y-%m-%d")),
            departments=tuple(pooled_data["department"].astype(str)),
            actuals=tuple(float(value) for value in pooled_data[TARGET]),
            predictions={
                name: tuple(float(value) for value in values)
                for name, values in predictions.items()
            },
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="EXP-004: temporal audit inside original training only."
    )
    parser.add_argument(
        "--dataset", type=Path, default=Path("data/raw/garments_worker_productivity.csv")
    )
    parser.add_argument("--split-config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--output", type=Path, default=Path("data/processed/exp-004-temporal-robustness.json")
    )
    args = parser.parse_args(argv)
    if args.output.resolve() in {args.dataset.resolve(), args.split_config.resolve()}:
        print("error: output must not overwrite the dataset or frozen split.", file=sys.stderr)
        return 2
    started = perf_counter()
    try:
        data, validation = load_validated_csv(args.dataset)
        config = load_split_config(args.split_config)
        result = run_experiment(data, config, dataset_sha256=fingerprint(args.dataset))
        elapsed = perf_counter() - started
        payload = {
            "experiment": "EXP-004",
            "dataset": args.dataset.as_posix(),
            "split_config": args.split_config.as_posix(),
            "split_config_sha256": fingerprint(args.split_config),
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                **{
                    package: version(package)
                    for package in (
                        "pandas",
                        "numpy",
                        "scikit-learn",
                        "scipy",
                        "joblib",
                        "threadpoolctl",
                    )
                },
            },
            "preprocessing": {
                "handle_unknown": "ignore",
                "drop": None,
                "sparse_output": False,
                "numeric": "passthrough",
                "remainder": "drop",
            },
            "source_validation_issues": [asdict(issue) for issue in validation.issues],
            "runtime_seconds": elapsed,
            "result": asdict(result),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for fold in result.folds:
        scores = ", ".join(
            f"{name}={model.evaluation_metrics.mae:.9f}" for name, model in fold.models.items()
        )
        print(f"{fold.fold.name} evaluation MAE: {scores}")
    for name, model in result.pooled.items():
        print(
            f"Pooled {name}: MAE={model.metrics.mae:.9f}, RMSE={model.metrics.rmse:.9f}, "
            f"R2={model.metrics.r2}, bias={model.metrics.bias:+.9f}"
        )
    counts = result.forest_vs_department
    print(
        f"Forest vs department: {counts.wins} wins / {counts.losses} losses / {counts.ties} ties. "
        "Original validation and final test excluded."
    )
    print(f"Artifact: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
