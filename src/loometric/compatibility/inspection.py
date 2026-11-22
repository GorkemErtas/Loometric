"""Inspect saved EXP-004 inner validation predictions; never fit or predict."""

import hashlib
import platform
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
from typing import Any

from loometric.compatibility.contracts import bounded_json, require_digest, sha256_value


def inspect_saved_predictions(
    dataset: Path,
    split_path: Path,
    predictions_path: Path,
    *,
    expected_predictions_sha256: str,
    include_observations: bool = False,
) -> dict[str, Any]:
    """All scored targets are from original training; outer labels are not parsed.

    M01 selects training rows before converting non-date CSV values. EXP-005 then
    validates saved folds, row identities, targets, parameters and stored scores.
    There is deliberately no partition, estimator, refit or live-inference option.
    """
    from loometric.data.profiling import fingerprint
    from loometric.data.splitting import load_split_config
    from loometric.error_analysis import ANALYZED_MODELS, analyze_errors
    from loometric.evaluation import mae_change
    from loometric.experiments.errors import validated_population
    from loometric.features import CATEGORICAL_FEATURES, SOURCE_COLUMNS, build_features
    from loometric.prediction.artifacts import load_training_partition
    from loometric.prediction.contracts import read_json

    require_digest(expected_predictions_sha256)
    if type(include_observations) is not bool:
        raise ValueError("Observation inspection must be an explicit boolean.")
    with predictions_path.open("rb") as source:
        content = source.read(4 * 1024 * 1024 + 1)
    actual_hash = hashlib.sha256(content).hexdigest()
    if actual_hash != expected_predictions_sha256:
        raise ValueError("Saved prediction digest differs from the independently retained digest.")
    decoded = content.decode("utf-8", errors="strict")
    bounded_json(decoded, max_bytes=4 * 1024 * 1024)
    artifact = read_json(decoded)  # Existing EXP-004 metrics use finite machine floats.
    config = load_split_config(split_path)
    training, lineage = load_training_partition(dataset, split_path)
    split_hash = fingerprint(split_path)
    if (
        lineage["dataset_sha256"] != config.dataset_sha256
        or lineage["split_file_sha256"] != split_hash
    ):
        raise ValueError("Inspection input fingerprints changed during loading.")
    population, predictions = validated_population(training, config, artifact, split_hash)
    analysis = analyze_errors(population, predictions)
    # Reconstruct vocabularies from prior rows only, without fitting an encoder.
    all_features = build_features(training.loc[:, SOURCE_COLUMNS])
    coverage = []
    configurations: dict[str, str] = {}
    baseline_fitted_parameters = []
    for saved_fold in artifact["result"]["folds"]:
        descriptor = saved_fold["fold"]
        prefix = training["date"].between(descriptor["train"]["start"], descriptor["train"]["end"])
        evaluation = population.index[population["fold"].eq(descriptor["name"])]
        for model in ANALYZED_MODELS:
            stored = saved_fold["models"][model]
            configuration = {
                "columns": stored["columns"],
                "estimator_parameters": stored["estimator_parameters"]
                if model != "department_mean"
                else {"algorithm": "training_department_mean_with_training_global_fallback"},
            }
            model_hash = sha256_value(configuration)
            if model in configurations and configurations[model] != model_hash:
                raise ValueError("Frozen model configuration differs between saved folds.")
            configurations[model] = model_hash
            if model == "department_mean":
                baseline_fitted_parameters.append(
                    {"fold": descriptor["name"], "parameters": stored["estimator_parameters"]}
                )
                continue
            metadata = stored["features"]
            categorical = [column for column in stored["columns"] if column in CATEGORICAL_FEATURES]
            expected_categories = {
                column: sorted(all_features.loc[prefix, column].unique().tolist())
                for column in categorical
            }
            if metadata["training_categories"] != expected_categories:
                raise ValueError("Saved category vocabulary disagrees with its training prefix.")
            counts = {
                column: int(
                    (~all_features.loc[evaluation, column].isin(expected_categories[column])).sum()
                )
                for column in categorical
            }
            if metadata["unknown_validation_categories"] != counts:
                raise ValueError("Saved unknown-category counts disagree with evaluation inputs.")
            coverage.append(
                {
                    "fold": descriptor["name"],
                    "model": model,
                    "unknown_categories": counts,
                    "training_categories_fingerprint": sha256_value(expected_categories),
                }
            )
    overall = {
        entry["group"]["model"]: entry["summary"] for entry in analysis["summaries"]["overall"]
    }
    baseline_mae = overall["department_mean"]["metrics"]["mae"]
    rows = []
    if include_observations:
        for index, record in population.iterrows():
            rows.append(
                {
                    "row_index": int(index),
                    "date": record["date"].date().isoformat(),
                    "fold": str(record["fold"]),
                    "department": str(record["department"]),
                    "team": str(record["team"]),
                    "actual": float(record["actual"]),
                    "predictions": {
                        name: float(predictions[name].loc[index]) for name in ANALYZED_MODELS
                    },
                }
            )
    if fingerprint(dataset) != lineage["dataset_sha256"] or fingerprint(split_path) != split_hash:
        raise ValueError("Source or frozen split changed during inspection.")
    return {
        "schema_version": 1,
        "policy_version": "saved-training-oof-inspection-v1",
        "scope": "ORIGINAL_TRAINING_OOF",
        "source_experiment": "EXP-004",
        "dataset_sha256": config.dataset_sha256,
        "split_file_sha256": split_hash,
        "source_artifact_sha256": actual_hash,
        "training_lineage_fingerprint": lineage["training_split_fingerprint"],
        "configuration_fingerprints": configurations,
        "baseline_fitted_parameters": baseline_fitted_parameters,
        "model_artifact_fingerprint": None,
        "model_artifact_note": "Saved fold predictions; not M01 full-training artifact accuracy.",
        "population_rows": len(population),
        "observed_dates": int(population["date"].nunique()),
        "evaluation_start": population["date"].min().date().isoformat(),
        "evaluation_end": population["date"].max().date().isoformat(),
        "outer_validation_evaluated": False,
        "final_test_evaluated": False,
        "models_fitted": 0,
        "predictions_generated": 0,
        "overall": overall,
        "department": analysis["summaries"]["department"],
        "fold": analysis["summaries"]["fold"],
        "change_vs_department_mean": {
            name: asdict(mae_change(overall[name]["metrics"]["mae"], baseline_mae))
            for name in ANALYZED_MODELS
        },
        "prediction_ranges": {
            name: {
                "minimum": float(series.min()),
                "maximum": float(series.max()),
                "below_zero": int(series.lt(0).sum()),
                "above_one": int(series.gt(1).sum()),
            }
            for name, series in predictions.items()
        },
        "category_coverage": coverage,
        "unsupported_category_contexts": [
            entry for entry in coverage if any(entry["unknown_categories"].values())
        ],
        "observations_included": include_observations,
        "observations": rows,
        "limitations": [
            "Retrospective inner evaluation on previously used original-training records; "
            "not independent model confirmation.",
            "No calibrated prediction intervals, uncertainty guarantees, causal crew response "
            "or target-to-efficiency conversion.",
            "Zero unknown categories in saved rows does not validate unseen teams, stages, "
            "styles, dates or factories.",
            "Source bytes and all dates are scanned for integrity; outer non-date "
            "features/labels are not interpreted or evaluated.",
        ],
        "environment": {
            "python": platform.python_version(),
            **{name: version(name) for name in ("pandas", "numpy", "scikit-learn")},
        },
    }
