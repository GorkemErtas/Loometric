"""Offline fixed refits only; no search, promotion, validation refit or reserved-label parsing."""

import io
import json
from pathlib import Path

import joblib
import numpy as np
from threadpoolctl import threadpool_limits

from loometric.experimental_ml.artifacts import canonical, load_trusted, sha256
from loometric.experimental_ml.constants import (
    ARTIFACT_ROOT,
    LIMITATIONS,
    MODELS,
    ROOT,
    STUDY_CASE,
    STUDY_DIRECTORY,
    STUDY_RECEIPT,
    VERSION,
)
from loometric.synthetic_ml.features import FEATURE_COLUMNS
from loometric.synthetic_training.artifacts import environment, inspect_artifact
from loometric.synthetic_training.configuration import load_study
from loometric.synthetic_training.data import load_development, require
from loometric.synthetic_training.models import build_model, model_metadata
from loometric.synthetic_training.risk import support_profile


def global_importance(model) -> list[dict]:
    """Aggregate fitted RF impurity importance across its one-hot categories.

    These are global training statistics, biased by feature cardinality/correlation;
    neither causal effects nor explanations of an individual response.
    """
    names = model.named_steps["preprocess"].get_feature_names_out()
    values = model.named_steps["regression"].feature_importances_
    totals = {name: 0.0 for name in FEATURE_COLUMNS}
    for encoded, importance in zip(names, values, strict=True):
        matches = [
            c
            for c in FEATURE_COLUMNS
            if encoded == f"numeric__{c}" or encoded.startswith(f"categorical__{c}_")
        ]
        require(
            len(matches) == 1 and np.isfinite(importance) and importance >= 0,
            "IMPORTANCE_MAPPING_FAILED",
        )
        totals[matches[0]] += float(importance)
    require(abs(sum(totals.values()) - 1) < 1e-12, "NORMALIZED_IMPORTANCE_REQUIRED")
    return [
        {"feature": name, "importance": value}
        for name, value in sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    ]


def publish_models(data, report: dict, saved_predictions: list[dict], output: Path) -> dict:
    """Internal publication primitive, also exercised with private test datasets."""
    require(not output.exists(), "CREATE_ONLY_EXPERIMENTAL_ARTIFACT_REQUIRED")
    config = report["configuration"]
    require(report["selection"]["status"] == "NO_ML_PROMOTION", "UNCHANGED_M08B_DECISION_REQUIRED")
    require(
        report["reserved_label_values_decoded"] is False
        and report["final_test_evaluated"] is False,
        "NO_RESERVED_LABELS",
    )
    require(
        data.provenance == report["datasets"][STUDY_CASE]["provenance"],
        "EXACT_DATASET_PROVENANCE_REQUIRED",
    )
    specs = {spec["name"]: spec for spec in config["search"]}
    specs["grouped_mean"] = {"name": "grouped_mean", "family": "naive", "parameters": {}}
    metadata = {
        "schema_version": 1,
        "model_version": VERSION,
        "experiment_id": "EXP-006-M08C-FIXED-REFIT",
        "source_experiment": "EXP-006",
        "source_study_manifest_sha256": STUDY_RECEIPT,
        "dataset_version": "synthetic-ml-v1",
        "target": "standard_capacity_attainment",
        "units": "dimensionless_standard_worker_minutes_per_planned_worker_minute",
        "feature_order": list(FEATURE_COLUMNS),
        "promotion_decision": "NO_ML_PROMOTION",
        "training": {
            "case": STUDY_CASE,
            "partition": "train",
            "rows": len(data.train.X),
            "undefined_rows_excluded": len(data.train.excluded),
            "first_date": min(data.train.metadata.start_date).isoformat(),
            "last_date": max(data.train.metadata.start_date).isoformat(),
            "source": data.provenance,
        },
        "support": support_profile(data.train.X, data.train.y),
        "models": {},
        "environment": environment(),
        "limitations": LIMITATIONS,
        "reserved_labels_decoded": False,
        "capacity_application_authorized": False,
    }
    buffers = {}
    trained = {}
    before = canonical({"X": data.train.X.to_dict(orient="split"), "y": list(data.train.y)})
    with threadpool_limits(limits=1):
        for public_name, study_name in MODELS.items():
            model = build_model(specs[study_name], config["model_seed"])
            model.fit(data.train.X, data.train.y)
            require(
                before
                == canonical({"X": data.train.X.to_dict(orient="split"), "y": list(data.train.y)}),
                "TRAINING_MUTATION",
            )
            predicted = model.predict(data.validation.X)
            retained = [
                r for r in saved_predictions if r["case"] == STUDY_CASE and r["model"] == study_name
            ]
            require(
                len(retained) == len(data.validation.X)
                and {r["observation_id"] for r in retained} == set(data.validation.X.index),
                "EXACT_PARITY_ROWS_REQUIRED",
            )
            expected = {r["observation_id"]: r["prediction"] for r in retained}
            error = float(
                np.max(np.abs(predicted - [expected[oid] for oid in data.validation.X.index]))
            )
            require(np.isfinite(error) and error <= 1e-12, "M08B_PREDICTION_PARITY_FAILED")
            details = {
                "identity": study_name,
                "status": "BASELINE_COMPARISON_ONLY"
                if public_name == "grouped_mean"
                else "EXPERIMENTAL_NOT_PROMOTED",
                "estimator_kind": "TRANSPARENT_GROUP_MEANS"
                if public_name == "grouped_mean"
                else type(model.named_steps["regression"]).__name__,
                "specification": specs[study_name],
                "seed": config["model_seed"],
                "preprocessing": model_metadata(model),
                "validation": report["validation"][STUDY_CASE][study_name],
                "promotion_checks": report["selection"].get("candidate_checks", {}).get(study_name),
                "residual_reference": report["residual_references"][STUDY_CASE][study_name],
                "parity": {
                    "source": "RETAINED_EXP006_BENCHMARK_VALIDATION_PREDICTIONS",
                    "rows": len(retained),
                    "maximum_absolute_difference": error,
                    "tolerance": 1e-12,
                },
                "global_feature_importance": global_importance(model)
                if public_name == "random_forest"
                else None,
                "explanation_method": "GLOBAL_TRAINING_IMPURITY_IMPORTANCE_NOT_CAUSAL_OR_LOCAL"
                if public_name == "random_forest"
                else "NOT_COMPUTED",
            }
            metadata["models"][public_name] = details
            if public_name == "grouped_mean":
                buffers["grouped_mean.json"] = canonical(model.state())
            else:
                destination = io.BytesIO()
                joblib.dump(model, destination, compress=0)
                buffers[f"{public_name}.joblib"] = destination.getvalue()
            trained[public_name] = predicted
    buffers["metadata.json"] = canonical(metadata)
    manifest = {
        "schema_version": 1,
        "model_version": VERSION,
        "promotion_decision": "NO_ML_PROMOTION",
        "reserved_labels_decoded": False,
        "capacity_application_authorized": False,
        "files": {name: sha256(value) for name, value in sorted(buffers.items())},
    }
    output.mkdir(parents=True, exist_ok=False)
    for name, value in buffers.items():
        with (output / name).open("xb") as destination:
            destination.write(value)
    with (output / "manifest.json").open("xb") as destination:
        destination.write(canonical(manifest))
    receipt = sha256(canonical(manifest))
    # Serialized estimators must produce the same complete authorized validation vector.
    _, restored = load_trusted(receipt, directory=output.resolve())
    with threadpool_limits(limits=1):
        for name, model in restored.items():
            require(
                np.array_equal(model.predict(data.validation.X), trained[name]),
                "SERIALIZED_PREDICTION_DRIFT",
            )
    return {
        "manifest_sha256": receipt,
        "model_sha256": manifest["files"],
        "parity": {name: details["parity"] for name, details in metadata["models"].items()},
    }


def publish_version(version: str) -> dict:
    require(version in ("v1", "v1-reproduction"), "ALLOWLISTED_PUBLICATION_VERSION_REQUIRED")
    output = ARTIFACT_ROOT / version
    require(not output.exists(), "CREATE_ONLY_EXPERIMENTAL_ARTIFACT_REQUIRED")
    inspect_artifact(STUDY_DIRECTORY, expected_fingerprint=STUDY_RECEIPT)
    report = json.loads((STUDY_DIRECTORY / "report.json").read_text(encoding="utf-8"))
    config = load_study(ROOT / "configs/synthetic_training_v1.json")
    require(config == report["configuration"], "UNCHANGED_PREFIT_CONFIGURATION_REQUIRED")
    binding = next(d for d in config["datasets"] if d["case_id"] == STUDY_CASE)
    data = load_development(
        ROOT / binding["directory"], expected_fingerprint=binding["expected_manifest_fingerprint"]
    )
    rows = [
        json.loads(line)
        for line in (STUDY_DIRECTORY / "validation-predictions.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    return publish_models(data, report, rows, output)
