"""EXP-002: four predefined linear comparisons on frozen train/validation dates."""

import argparse
import json
import platform
import sys
from dataclasses import asdict, dataclass, field
from importlib.metadata import version
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
from loometric.features import FEATURE_SETS, SOURCE_COLUMNS, build_features
from loometric.linear import build_linear_pipeline
from loometric.preprocessing import inspect_preprocessor


@dataclass(frozen=True)
class ModelResult:
    columns: tuple[str, ...]
    metrics: RegressionMetrics
    department_mae: dict[str, float]
    diagnostics: PredictionDiagnostics
    encoded_columns: tuple[str, ...]
    training_categories: dict[str, tuple[str, ...]]
    unknown_validation_categories: dict[str, int]
    training_seconds: float = field(compare=False)
    inference_seconds: float = field(compare=False)


@dataclass(frozen=True)
class ExperimentResult:
    split: SplitConfig
    models: dict[str, ModelResult]
    baseline_comparisons: dict[str, dict[str, MaeChange]]
    feature_comparisons: dict[str, MaeChange]
    selected_linear: str
    feature_engineering_seconds: float = field(compare=False)


def run_experiment(
    data: pd.DataFrame, config: SplitConfig, *, dataset_sha256: str
) -> ExperimentResult:
    """Reuse verified splits. Never access the final test frame after partitioning.

    All four feature sets are fixed in FEATURE_SETS; no adaptive tuning. Rank linear
    candidates by validation MAE, breaking ties within 1e-12 in declared order.
    This is a development comparison, not authorization for final-test evaluation.
    """
    splits = apply_split_config(data, config, dataset_sha256=dataset_sha256)
    training, validation = splits.train, splits.validation
    started = perf_counter()
    train_features = build_features(training.loc[:, SOURCE_COLUMNS])
    validation_features = build_features(validation.loc[:, SOURCE_COLUMNS])
    feature_seconds = perf_counter() - started
    models: dict[str, ModelResult] = {}
    feature_sets = dict(FEATURE_SETS)
    for name in ("global_mean", "department_mean", *(name for name, _ in FEATURE_SETS)):
        columns = feature_sets.get(name, ("department",) if name == "department_mean" else ())
        categories: dict[str, tuple[str, ...]] = {}
        encoded: tuple[str, ...] = ()
        unknown: dict[str, int] = {}
        started = perf_counter()
        if name == "global_mean":
            global_model = GlobalMeanBaseline.fit(training[TARGET])
        elif name == "department_mean":
            department_model = DepartmentMeanBaseline.fit(training["department"], training[TARGET])
        else:
            pipeline = build_linear_pipeline(columns)
            pipeline.fit(train_features.loc[:, columns], training[TARGET])
        training_seconds = perf_counter() - started
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
        if name in feature_sets:
            metadata = inspect_preprocessor(
                pipeline.named_steps["preprocessing"], validation_features
            )
            categories = metadata.training_categories
            unknown = metadata.unknown_validation_categories
            encoded = metadata.encoded_columns
        models[name] = ModelResult(
            columns=columns,
            metrics=regression_metrics(validation[TARGET], predictions),
            department_mae={
                str(department): regression_metrics(group[TARGET], predictions.loc[group.index]).mae
                for department, group in validation.groupby("department", sort=True)
            },
            diagnostics=prediction_diagnostics(validation[TARGET], predictions, training[TARGET]),
            encoded_columns=encoded,
            training_categories=categories,
            unknown_validation_categories=unknown,
            training_seconds=training_seconds,
            inference_seconds=inference_seconds,
        )
    comparisons = {
        name: {
            reference: mae_change(models[name].metrics.mae, models[reference].metrics.mae)
            for reference in ("global_mean", "department_mean")
        }
        for name, _ in FEATURE_SETS
    }
    pairs = (
        ("team_added_to_department", "department_team", "department_only"),
        ("department_added_to_team", "department_team", "team_only"),
        ("calendar_added_to_department_team", "department_team_calendar", "department_team"),
    )
    feature_comparisons = {
        label: mae_change(models[candidate].metrics.mae, models[reference].metrics.mae)
        for label, candidate, reference in pairs
    }
    selected = FEATURE_SETS[0][0]
    for name, _ in FEATURE_SETS[1:]:
        if models[name].metrics.mae < models[selected].metrics.mae - 1e-12:
            selected = name
    return ExperimentResult(
        config, models, comparisons, feature_comparisons, selected, feature_seconds
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EXP-002: frozen splits, validation-only OLS.")
    parser.add_argument(
        "--dataset", type=Path, default=Path("data/raw/garments_worker_productivity.csv")
    )
    parser.add_argument("--split-config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--output", type=Path, default=Path("data/processed/exp-002-linear-regression.json")
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
            "experiment": "EXP-002",
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
            "seed": None,
            "seed_reason": "No random operation; deterministic ordinary least squares.",
            "pipeline_configuration": {
                "encoder": {"handle_unknown": "ignore", "drop": None, "sparse_output": False},
                "regression": build_linear_pipeline(FEATURE_SETS[0][1])
                .named_steps["regression"]
                .get_params(),
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
    for name, model in result.models.items():
        metrics = model.metrics
        print(
            f"{name}: MAE={metrics.mae:.9f}, RMSE={metrics.rmse:.9f}, "
            f"R2={metrics.r2}, bias={metrics.bias:+.9f}"
        )
    print(
        f"Lowest linear validation MAE: {result.selected_linear}. "
        f"Final test reserved. {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
