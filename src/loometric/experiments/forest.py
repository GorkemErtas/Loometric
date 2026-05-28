"""EXP-003: six predefined forests; training diagnostics and validation-only selection."""

import argparse
import json
import platform
import sys
from dataclasses import asdict, dataclass, field
from importlib.metadata import version
from math import isfinite
from pathlib import Path
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
from loometric.evaluation import (
    MaeChange,
    PredictionDiagnostics,
    RegressionMetrics,
    mae_change,
    prediction_diagnostics,
    regression_metrics,
)
from loometric.features import SOURCE_COLUMNS, build_features
from loometric.forest import (
    FOREST_CONFIGURATIONS,
    FOREST_FEATURE_SETS,
    FeatureImportance,
    build_forest_pipeline,
    summarize_importance,
)
from loometric.linear import build_linear_pipeline
from loometric.preprocessing import FeatureMetadata, inspect_preprocessor


@dataclass(frozen=True)
class ModelResult:
    columns: tuple[str, ...]
    estimator_parameters: dict[str, object]
    training_mae: float
    validation_metrics: RegressionMetrics
    validation_minus_training_mae: float
    department_mae: dict[str, float]
    diagnostics: PredictionDiagnostics
    features: FeatureMetadata
    impurity_importance: FeatureImportance | None
    training_seconds: float = field(compare=False)
    training_inference_seconds: float = field(compare=False)
    inference_seconds: float = field(compare=False)


@dataclass(frozen=True)
class ExperimentResult:
    split: SplitConfig
    references: dict[str, ModelResult]
    forests: dict[str, ModelResult]
    comparisons: dict[str, dict[str, MaeChange]]
    calendar_mae_changes: dict[str, MaeChange]
    best_forest: str
    preferred_model: str
    feature_engineering_seconds: float = field(compare=False)


def select_preferred_model(
    validation_mae: dict[str, float], department_baseline_mae: float
) -> tuple[str, str]:
    """Select solely by validation MAE; ties within 1e-12 preserve declared order."""
    if not validation_mae or not all(
        isfinite(value) and value >= 0
        for value in (*validation_mae.values(), department_baseline_mae)
    ):
        raise ValueError("Selection requires nonempty, finite, nonnegative validation MAEs.")
    best = next(iter(validation_mae))
    for name, score in validation_mae.items():
        if score < validation_mae[best] - 1e-12:
            best = name
    preferred = (
        best if validation_mae[best] < department_baseline_mae - 1e-12 else "department_mean"
    )
    return best, preferred


def run_experiment(
    data: pd.DataFrame, config: SplitConfig, *, dataset_sha256: str
) -> ExperimentResult:
    """Never consume the final test frame; training scores are diagnostic only."""
    splits = apply_split_config(data, config, dataset_sha256=dataset_sha256)
    training, validation = splits.train, splits.validation
    started = perf_counter()
    train_features = build_features(training.loc[:, SOURCE_COLUMNS])
    validation_features = build_features(validation.loc[:, SOURCE_COLUMNS])
    feature_seconds = perf_counter() - started
    references: dict[str, ModelResult] = {}
    forests: dict[str, ModelResult] = {}
    plan = (
        ("global_mean", (), None),
        ("department_mean", ("department",), None),
        *((f"linear_{name}", columns, None) for name, columns in FOREST_FEATURE_SETS),
        *(
            (f"{name}_{profile.name}", columns, profile)
            for name, columns in FOREST_FEATURE_SETS
            for profile in FOREST_CONFIGURATIONS
        ),
    )
    for name, columns, profile in plan:
        started = perf_counter()
        if name == "global_mean":
            global_model = GlobalMeanBaseline.fit(training[TARGET])
        elif name == "department_mean":
            department_model = DepartmentMeanBaseline.fit(training["department"], training[TARGET])
        else:
            pipeline = (
                build_forest_pipeline(columns, profile)
                if profile is not None
                else build_linear_pipeline(columns)
            )
            pipeline.fit(train_features.loc[:, columns], training[TARGET])
        training_seconds = perf_counter() - started
        started = perf_counter()
        if name == "global_mean":
            training_predictions = global_model.predict(training.index)
        elif name == "department_mean":
            training_predictions = department_model.predict(training["department"])
        else:
            training_predictions = pd.Series(
                pipeline.predict(train_features.loc[:, columns]),
                index=training.index,
                dtype="float64",
            )
        training_inference_seconds = perf_counter() - started
        started = perf_counter()
        if name == "global_mean":
            predictions = global_model.predict(validation.index)
        elif name == "department_mean":
            predictions = department_model.predict(validation["department"])
        else:
            predictions = pd.Series(
                pipeline.predict(validation_features.loc[:, columns]),
                index=validation.index,
                dtype="float64",
            )
        inference_seconds = perf_counter() - started
        metadata = FeatureMetadata((), {}, {})
        importance = None
        if name == "global_mean":
            parameters: dict[str, object] = {"training_mean": global_model.mean}
        elif name == "department_mean":
            parameters = {
                "training_global_mean": department_model.global_mean,
                "training_department_means": department_model.department_means,
            }
        else:
            preprocessing = pipeline.named_steps["preprocessing"]
            estimator = pipeline.named_steps["regression"]
            metadata = inspect_preprocessor(preprocessing, validation_features)
            parameters = estimator.get_params()
            if profile is not None:
                importance = summarize_importance(preprocessing, estimator.feature_importances_)
        training_mae = regression_metrics(training[TARGET], training_predictions).mae
        metrics = regression_metrics(validation[TARGET], predictions)
        result = ModelResult(
            columns=columns,
            estimator_parameters=parameters,
            training_mae=training_mae,
            validation_metrics=metrics,
            validation_minus_training_mae=metrics.mae - training_mae,
            department_mae={
                str(department): regression_metrics(group[TARGET], predictions.loc[group.index]).mae
                for department, group in validation.groupby("department", sort=True)
            },
            diagnostics=prediction_diagnostics(validation[TARGET], predictions, training[TARGET]),
            features=metadata,
            impurity_importance=importance,
            training_seconds=training_seconds,
            training_inference_seconds=training_inference_seconds,
            inference_seconds=inference_seconds,
        )
        (forests if profile is not None else references)[name] = result
    comparisons = {
        name: {
            reference: mae_change(model.validation_metrics.mae, baseline.validation_metrics.mae)
            for reference, baseline in references.items()
        }
        for name, model in forests.items()
    }
    best, preferred = select_preferred_model(
        {name: model.validation_metrics.mae for name, model in forests.items()},
        references["department_mean"].validation_metrics.mae,
    )
    calendar_changes = {
        profile.name: mae_change(
            forests[f"B_{profile.name}"].validation_metrics.mae,
            forests[f"A_{profile.name}"].validation_metrics.mae,
        )
        for profile in FOREST_CONFIGURATIONS
    }
    return ExperimentResult(
        config, references, forests, comparisons, calendar_changes, best, preferred, feature_seconds
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EXP-003: six fixed forests, final test reserved.")
    parser.add_argument(
        "--dataset", type=Path, default=Path("data/raw/garments_worker_productivity.csv")
    )
    parser.add_argument("--split-config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--output", type=Path, default=Path("data/processed/exp-003-random-forest.json")
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
            "experiment": "EXP-003",
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
            "random_state": 42,
            "n_jobs": 1,
            "predefined_profiles": [asdict(profile) for profile in FOREST_CONFIGURATIONS],
            "predefined_feature_sets": dict(FOREST_FEATURE_SETS),
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
    for name, model in result.forests.items():
        metrics = model.validation_metrics
        change = result.comparisons[name]["department_mean"]
        relative = (
            f"{change.relative_percent:+.4f}%"
            if change.relative_percent is not None
            else "undefined relative change"
        )
        print(
            f"{name}: train MAE={model.training_mae:.9f}, validation MAE={metrics.mae:.9f}, "
            f"RMSE={metrics.rmse:.9f}, R2={metrics.r2}, bias={metrics.bias:+.9f}, "
            f"MAE change vs department={change.absolute:+.9f} ({relative})"
        )
    print(
        f"Best forest: {result.best_forest}; preferred: {result.preferred_model}. "
        "Final test reserved."
    )
    print(f"Artifact: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
