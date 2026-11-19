"""EXP-005: validate EXP-004 evidence and analyze saved training-period predictions."""

import argparse
import json
import platform
import sys
from dataclasses import asdict
from hashlib import sha256
from importlib.metadata import version
from math import isclose, isfinite
from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd

from loometric.data.loading import load_validated_csv
from loometric.data.profiling import fingerprint
from loometric.data.schema import TARGET
from loometric.data.splitting import (
    DEFAULT_CONFIG,
    SplitConfig,
    apply_split_config,
    load_split_config,
)
from loometric.data.temporal import DEFAULT_POLICY, make_expanding_folds
from loometric.error_analysis import ANALYZED_MODELS, analyze_errors
from loometric.evaluation import RegressionMetrics, regression_metrics
from loometric.experiments.temporal import FROZEN_FEATURES, FROZEN_FOREST
from loometric.features import SOURCE_COLUMNS, build_features
from loometric.forest import build_forest_pipeline
from loometric.linear import build_linear_pipeline


def _verify_metrics(actual: RegressionMetrics, stored: dict[str, Any]) -> None:
    expected = asdict(actual)
    if set(stored) != set(expected):
        raise ValueError("Saved metric schema differs from EXP-004.")
    for name, value in expected.items():
        recorded = stored[name]
        if value is None:
            valid = recorded is None
        elif name == "samples":
            valid = type(recorded) is int and recorded == value
        else:
            valid = (
                isinstance(recorded, (int, float))
                and isfinite(recorded)
                and isclose(value, recorded, rel_tol=0, abs_tol=1e-12)
            )
        if not valid:
            raise ValueError(f"Saved EXP-004 {name} disagrees with matched predictions.")


def validated_population(
    training: pd.DataFrame, config: SplitConfig, artifact: dict[str, Any], split_sha256: str
) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    """Reject artifact drift before joining metadata; no estimator is fitted here."""
    try:
        if (
            artifact["experiment"] != "EXP-004"
            or artifact["split_config_sha256"] != split_sha256
            or artifact["result"]["split"] != asdict(config)
            or artifact["result"]["policy"] != asdict(DEFAULT_POLICY)
        ):
            raise ValueError("Saved EXP-004 identity, split fingerprint, or policy differs.")
        result = artifact["result"]
        folds = make_expanding_folds(training, config.train)
        if [fold["fold"] for fold in result["folds"]] != [asdict(fold) for fold in folds]:
            raise ValueError("Saved folds do not match the original-training date policy.")
        frames = []
        for fold in folds:
            frame = training.loc[
                training["date"].between(fold.evaluation.start, fold.evaluation.end)
            ].copy()
            frame["fold"] = fold.name
            frames.append(frame)
        expected = pd.concat(frames)
        oof = result["out_of_fold"]
        if (
            not expected.index.is_unique
            or oof["row_indices"] != list(expected.index)
            or oof["dates"] != list(expected["date"].dt.strftime("%Y-%m-%d"))
            or oof["departments"] != list(expected["department"].astype(str))
            or len(oof["actuals"]) != len(expected)
        ):
            raise ValueError("OOF row identities, dates, departments, or counts differ.")
        actuals = pd.Series(oof["actuals"], index=expected.index, dtype="float64")
        mismatch = regression_metrics(expected[TARGET], actuals)
        if mismatch.mae > 1e-12 or (expected[TARGET] - actuals).abs().max() > 1e-12:
            raise ValueError("Saved targets do not match original-training observations.")
        columns = {
            "department_mean": ("department",),
            "linear_A": FROZEN_FEATURES["A"],
            "forest_B_RF-01": FROZEN_FEATURES["B"],
        }
        parameters = {
            "linear_A": build_linear_pipeline(columns["linear_A"])
            .named_steps["regression"]
            .get_params(),
            "forest_B_RF-01": build_forest_pipeline(columns["forest_B_RF-01"], FROZEN_FOREST)
            .named_steps["regression"]
            .get_params(),
        }
        predictions = {}
        for name in ANALYZED_MODELS:
            values = oof["predictions"][name]
            if len(values) != len(expected):
                raise ValueError("Every model must predict the identical OOF population.")
            predicted = pd.Series(values, index=expected.index, dtype="float64")
            _verify_metrics(
                regression_metrics(actuals, predicted), result["pooled"][name]["metrics"]
            )
            for saved_fold, fold in zip(result["folds"], folds, strict=True):
                saved_model = saved_fold["models"][name]
                if saved_model["columns"] != list(columns[name]):
                    raise ValueError(
                        "Saved model feature set differs from the fixed configuration."
                    )
                if name in parameters and saved_model["estimator_parameters"] != parameters[name]:
                    raise ValueError(
                        "Saved estimator parameters differ from the frozen configuration."
                    )
                index = expected.index[expected["fold"].eq(fold.name)]
                _verify_metrics(
                    regression_metrics(actuals.loc[index], predicted.loc[index]),
                    saved_model["evaluation_metrics"],
                )
            predictions[name] = predicted
        metadata = build_features(expected.loc[:, SOURCE_COLUMNS])
        population = pd.DataFrame(
            {
                "date": expected["date"],
                "fold": expected["fold"],
                "department": expected["department"],
                "team": metadata["team"],
                "actual": actuals,
            },
            index=expected.index,
        )
        return population, predictions
    except (KeyError, TypeError, IndexError, AttributeError) as exc:
        raise ValueError("Malformed EXP-004 saved prediction artifact.") from exc


def run_experiment(
    data: pd.DataFrame,
    config: SplitConfig,
    artifact: dict[str, Any],
    *,
    dataset_sha256: str,
    split_sha256: str,
) -> dict[str, object]:
    """Use only original training after existing source/split verification."""
    training = apply_split_config(data, config, dataset_sha256=dataset_sha256).train
    population, predictions = validated_population(training, config, artifact, split_sha256)
    return analyze_errors(population, predictions)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EXP-005: saved OOF errors, no model retraining.")
    parser.add_argument(
        "--dataset", type=Path, default=Path("data/raw/garments_worker_productivity.csv")
    )
    parser.add_argument("--split-config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--predictions", type=Path, default=Path("data/processed/exp-004-temporal-robustness.json")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/processed/exp-005-error-analysis.json")
    )
    args = parser.parse_args(argv)
    if args.output.resolve() in {
        args.dataset.resolve(),
        args.split_config.resolve(),
        args.predictions.resolve(),
    }:
        print("error: analysis output must not overwrite an input.", file=sys.stderr)
        return 2
    started = perf_counter()
    try:
        source_bytes = args.predictions.read_bytes()
        artifact = json.loads(source_bytes)
        data, validation = load_validated_csv(args.dataset)
        config = load_split_config(args.split_config)
        split_hash = fingerprint(args.split_config)
        analysis = run_experiment(
            data,
            config,
            artifact,
            dataset_sha256=fingerprint(args.dataset),
            split_sha256=split_hash,
        )
        elapsed = perf_counter() - started
        payload = {
            "experiment": "EXP-005",
            "dataset_sha256": config.dataset_sha256,
            "split_config_sha256": split_hash,
            "source_experiment": "EXP-004",
            "source_artifact_sha256": sha256(source_bytes).hexdigest(),
            "environment": {
                "python": platform.python_version(),
                **{name: version(name) for name in ("pandas", "numpy", "scikit-learn")},
            },
            "source_validation_issues": [asdict(issue) for issue in validation.issues],
            "runtime_seconds": elapsed,
            "analysis": analysis,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for entry in analysis["summaries"]["overall"]:
        model, summary = entry["group"]["model"], entry["summary"]
        print(
            f"{model}: n={summary['metrics']['samples']}, MAE={summary['metrics']['mae']:.9f}, "
            f"bias={summary['metrics']['bias']:+.9f}, high-error rows={summary['high_error_rows']}"
        )
    print(f"EXP-005 complete; no models fitted. Local artifact: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
