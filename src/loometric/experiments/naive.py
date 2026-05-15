"""EXP-001: train-only mean estimation and validation-only performance evaluation."""

import argparse
import sys
from dataclasses import dataclass
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
from loometric.evaluation import RegressionMetrics, regression_metrics


@dataclass(frozen=True)
class DepartmentScores:
    training_samples: int
    validation_samples: int
    global_mae: float
    department_mae: float


@dataclass(frozen=True)
class ExperimentResult:
    split: SplitConfig
    global_mean: float
    department_means: dict[str, float]
    validation_metrics: dict[str, RegressionMetrics]
    department_scores: dict[str, DepartmentScores]


def run_experiment(
    data: pd.DataFrame, config: SplitConfig, *, dataset_sha256: str
) -> ExperimentResult:
    """Only training labels enter estimators; the final test frame is never scored."""
    splits = apply_split_config(data, config, dataset_sha256=dataset_sha256)
    training, validation = splits.train, splits.validation
    global_model = GlobalMeanBaseline.fit(training[TARGET])
    department_model = DepartmentMeanBaseline.fit(training["department"], training[TARGET])
    predictions = {
        "global_mean": global_model.predict(validation.index),
        "department_mean": department_model.predict(validation["department"]),
    }
    scores = {
        name: regression_metrics(validation[TARGET], predicted)
        for name, predicted in predictions.items()
    }
    department_scores = {}
    for department, group in validation.groupby("department", sort=True):
        department_scores[str(department)] = DepartmentScores(
            training_samples=int(training["department"].eq(department).sum()),
            validation_samples=len(group),
            global_mae=regression_metrics(
                group[TARGET], predictions["global_mean"].loc[group.index]
            ).mae,
            department_mae=regression_metrics(
                group[TARGET], predictions["department_mean"].loc[group.index]
            ).mae,
        )
    return ExperimentResult(
        config, global_model.mean, department_model.department_means, scores, department_scores
    )


def main(argv: list[str] | None = None) -> int:
    # Import rendering here to keep the numerical experiment independently usable.
    from loometric.experiments.reporting import render_report

    parser = argparse.ArgumentParser(
        description="EXP-001: naive baselines, validation metrics only."
    )
    parser.add_argument(
        "--dataset", type=Path, default=Path("data/raw/garments_worker_productivity.csv")
    )
    parser.add_argument("--split-config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--output", type=Path, default=Path("docs/experiments/EXP-001-naive-baseline.md")
    )
    args = parser.parse_args(argv)
    if args.output.resolve() in {args.dataset.resolve(), args.split_config.resolve()}:
        print(
            "error: report must not overwrite the dataset or frozen split configuration.",
            file=sys.stderr,
        )
        return 2
    started = perf_counter()
    try:
        data, validation = load_validated_csv(args.dataset)
        config = load_split_config(args.split_config)
        result = run_experiment(data, config, dataset_sha256=fingerprint(args.dataset))
        elapsed = perf_counter() - started
        report = render_report(
            result,
            validation,
            runtime_seconds=elapsed,
            dataset_path=args.dataset,
            config_path=args.split_config,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8", newline="\n")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(
        f"EXP-001 complete: {config.train.rows} training / {config.validation.rows} validation "
        f"rows; final test reserved. Report: {args.output}"
    )
    for name, metrics in result.validation_metrics.items():
        print(
            f"{name}: MAE={metrics.mae:.9f}, RMSE={metrics.rmse:.9f}, "
            f"R2={metrics.r2}, bias={metrics.bias:.9f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
