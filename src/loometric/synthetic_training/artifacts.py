"""Create-only experiment outputs and metadata/byte inspection, never automatic unpickling."""

import platform
from importlib.metadata import version
from pathlib import Path

from loometric.prediction.contracts import read_json
from loometric.synthetic_ml.features import FEATURE_COLUMNS
from loometric.synthetic_ml.storage import digest, encode
from loometric.synthetic_training.data import fingerprint, require
from loometric.synthetic_training.models import MeanModel
from loometric.synthetic_training.study import StudyResult

OUTPUT_ROOT = Path(__file__).resolve().parents[3] / "data/processed/synthetic_training"


def environment() -> dict:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "loometric": "0.1.0",
        "dependencies": {
            name: version(name)
            for name in ("pandas", "numpy", "scikit-learn", "scipy", "joblib", "threadpoolctl")
        },
    }


def checked_output(output: Path) -> Path:
    output, base = output.resolve(), OUTPUT_ROOT.resolve()
    require(
        output != base and output.is_relative_to(base) and not output.exists(),
        "NEW_IGNORED_TRAINING_OUTPUT_REQUIRED",
    )
    return output


def publish(result: StudyResult, output: Path) -> dict:
    output = checked_output(output)
    require(
        result.report["final_test_evaluated"] is False
        and result.report["capacity_application_authorized"] is False
        and result.selected_metadata["training_partition"] == "train",
        "NON_OPERATIONAL_TRAIN_ONLY_ARTIFACT_REQUIRED",
    )
    output.mkdir(parents=True, exist_ok=False)
    files = {}
    for name, values in (
        ("report.json", [result.report]),
        ("measurements.json", [result.measurements]),
        ("training-oof.jsonl", result.oof_predictions),
        ("validation-predictions.jsonl", result.validation_predictions),
        ("undefined-label-exclusions.jsonl", result.excluded_observations),
    ):
        with (output / name).open("xb") as destination:
            for value in values:
                destination.write(encode(value))
        if name != "measurements.json":
            files[name] = fingerprint(output / name)
    if isinstance(result.selected_model, MeanModel):
        model_name = "model.json"
        with (output / model_name).open("xb") as destination:
            destination.write(encode(result.selected_model.state()))
        format_name = "TRANSPARENT_TRAINING_MEANS_JSON"
    else:
        import joblib

        model_name = "pipeline.joblib"
        with (output / model_name).open("xb") as destination:
            joblib.dump(result.selected_model, destination, compress=0)
        format_name = "TRUSTED_LOCAL_ONLY_JOBLIB_NO_AUTOMATIC_LOAD"
    files[model_name] = fingerprint(output / model_name)
    manifest = {
        "artifact_schema_version": 1,
        "policy_version": "synthetic-training-v1",
        "experiment_id": "EXP-006",
        "dataset_version": "synthetic-ml-v1",
        "target": "standard_capacity_attainment",
        "model_id": "synthetic-productivity-experimental-v1",
        "model_format": format_name,
        "configuration_fingerprint": result.report["configuration_fingerprint"],
        "feature_order": list(FEATURE_COLUMNS),
        "training": result.selected_metadata,
        "selection": result.report["selection"],
        "files": files,
        "environment": environment(),
        "deterministic_report_fingerprint": digest(result.report),
        "final_test_evaluated": False,
        "reserved_label_values_decoded": False,
        "capacity_application_authorized": False,
        "target_to_efficiency": "NOT_IMPLEMENTED",
        "serving_authorized": False,
        "limitations": [
            "Synthetic demand-censored attainment; "
            "not factory performance or intrinsic efficiency.",
            "Residual bands are not calibrated; unseen entity evaluation remains reserved.",
            "Hidden distribution shift may be undetectable from available features.",
            "No trusted executable loading or live input contract is implemented in M08B.",
        ],
    }
    with (output / "manifest.json").open("xb") as destination:
        destination.write(encode(manifest))
    return {
        "manifest_fingerprint": digest(manifest),
        "selected_model": result.report["selection"]["selected_model"],
        "selection_status": result.report["selection"]["status"],
        "model_sha256": files[model_name],
        "deterministic_report_fingerprint": digest(result.report),
    }


def inspect_artifact(directory: Path, *, expected_fingerprint: str) -> dict:
    path = directory / "manifest.json"
    require(path.stat().st_size <= 2 * 1024 * 1024, "ARTIFACT_MANIFEST_BYTE_LIMIT")
    manifest = read_json(path.read_text(encoding="utf-8"))
    require(digest(manifest) == expected_fingerprint, "ARTIFACT_RECEIPT_MISMATCH")
    require(
        type(manifest["artifact_schema_version"]) is int
        and manifest["artifact_schema_version"] == 1
        and manifest["policy_version"] == "synthetic-training-v1"
        and manifest["dataset_version"] == "synthetic-ml-v1"
        and manifest["target"] == "standard_capacity_attainment"
        and manifest["model_format"]
        in ("TRANSPARENT_TRAINING_MEANS_JSON", "TRUSTED_LOCAL_ONLY_JOBLIB_NO_AUTOMATIC_LOAD")
        and manifest["feature_order"] == list(FEATURE_COLUMNS)
        and manifest["environment"] == environment()
        and manifest["final_test_evaluated"] is False
        and manifest["reserved_label_values_decoded"] is False
        and manifest["capacity_application_authorized"] is False
        and manifest["serving_authorized"] is False
        and manifest["training"]["training_partition"] == "train",
        "ARTIFACT_POLICY_OR_ENVIRONMENT_MISMATCH",
    )
    model_file = (
        "model.json"
        if manifest["model_format"] == "TRANSPARENT_TRAINING_MEANS_JSON"
        else "pipeline.joblib"
    )
    require(
        set(manifest["files"])
        == {
            "report.json",
            "training-oof.jsonl",
            "validation-predictions.jsonl",
            "undefined-label-exclusions.jsonl",
            model_file,
        },
        "CLOSED_ARTIFACT_FILE_SET_REQUIRED",
    )
    for name, expected in manifest["files"].items():
        path = directory / name
        require(
            path.resolve().parent == directory.resolve()
            and path.stat().st_size <= 256 * 1024 * 1024
            and fingerprint(path) == expected,
            "ARTIFACT_CONTENT_DRIFT",
        )
    return {
        "status": "INTEGRITY_VERIFIED_METADATA_ONLY",
        "manifest_fingerprint": expected_fingerprint,
        "selected_model": manifest["training"]["name"],
        "model_sha256": manifest["files"][model_file],
        "executable_model_loaded": False,
        "capacity_application_authorized": False,
        "serving_authorized": False,
    }
