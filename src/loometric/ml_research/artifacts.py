"""Ignored create-only research outputs; inspect hashes/metadata without executing models."""

import json
from pathlib import Path

import joblib

from loometric.ml_research.protocol import ROOT
from loometric.ml_research.study import ResearchResult
from loometric.synthetic_ml.storage import digest, encode
from loometric.synthetic_training.artifacts import environment
from loometric.synthetic_training.data import fingerprint, require

OUTPUT_ROOT = ROOT / "data/processed/ml_research"
FILES = {
    "report.json",
    "historical-diagnosis.json",
    "permutation-importance.json",
    "ablations.json",
    "training-oof.jsonl",
    "spent-diagnostics.jsonl",
    "research-model.joblib",
}


def checked_output(path: Path) -> Path:
    path, base = path.resolve(), OUTPUT_ROOT.resolve()
    require(
        path != base and path.is_relative_to(base) and not path.exists(),
        "NEW_IGNORED_RESEARCH_OUTPUT_REQUIRED",
    )
    return path


def code_identity() -> dict:
    return {path.name: fingerprint(path) for path in sorted(Path(__file__).parent.glob("*.py"))}


def publish(result: ResearchResult, directory: Path) -> dict:
    directory = checked_output(directory)
    require(
        result.report["reserved_labels_decoded"] is False
        and result.report["serving_artifacts_changed"] is False
        and result.report["promotion_decision"] == "NO_ML_PROMOTION",
        "RESEARCH_ONLY_ARTIFACT_REQUIRED",
    )
    directory.mkdir(parents=True, exist_ok=False)
    for name, rows in (
        ("report.json", [result.report]),
        ("historical-diagnosis.json", [result.historical]),
        ("permutation-importance.json", [result.importance]),
        ("ablations.json", [result.ablations]),
        ("training-oof.jsonl", result.oof_predictions),
        ("spent-diagnostics.jsonl", result.diagnostic_predictions),
        ("measurements.json", [result.measurements]),
    ):
        with (directory / name).open("xb") as output:
            for row in rows:
                output.write(encode(row))
    with (directory / "research-model.joblib").open("xb") as output:
        joblib.dump(result.artifact_model, output, compress=0)
    manifest = {
        "schema_version": 1,
        "experiment_id": "EXP-008",
        "policy_version": "ml-improvement-research-v1",
        "configuration_sha256": result.report["configuration_sha256"],
        "research_code": code_identity(),
        "files": {name: fingerprint(directory / name) for name in sorted(FILES)},
        "environment": environment(),
        "sealed_selection_sha256": result.report["sealed_selection_sha256"],
        "artifact_model": result.report["artifact_model"],
        "artifact_status": result.report["artifact_status"],
        "training_partition": "train",
        "promotion_decision": "NO_ML_PROMOTION",
        "serving_authorized": False,
        "reserved_labels_decoded": False,
        "capacity_application_authorized": False,
    }
    with (directory / "manifest.json").open("xb") as output:
        output.write(encode(manifest))
    return {
        "manifest_sha256": digest(manifest),
        "model_sha256": manifest["files"]["research-model.joblib"],
        "selection": result.report["selection"],
        "estimator_fits": result.report["estimator_fits"],
    }


def inspect_research(directory: Path, receipt: str) -> dict:
    directory = directory.resolve()
    require(
        directory.is_relative_to(OUTPUT_ROOT.resolve()) and directory != OUTPUT_ROOT.resolve(),
        "RESEARCH_ARTIFACT_PATH_REQUIRED",
    )
    manifest_path = directory / "manifest.json"
    require(
        manifest_path.stat().st_size <= 1024 * 1024
        and manifest_path.resolve().parent == directory
        and fingerprint(manifest_path) == receipt,
        "RESEARCH_MANIFEST_RECEIPT_MISMATCH",
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(
        manifest["schema_version"] == 1
        and manifest["experiment_id"] == "EXP-008"
        and manifest["policy_version"] == "ml-improvement-research-v1"
        and manifest["promotion_decision"] == "NO_ML_PROMOTION"
        and manifest["serving_authorized"] is False
        and manifest["reserved_labels_decoded"] is False
        and manifest["capacity_application_authorized"] is False
        and manifest["training_partition"] == "train"
        and manifest["environment"] == environment()
        and set(manifest["files"]) == FILES,
        "RESEARCH_MANIFEST_POLICY_MISMATCH",
    )
    for name, expected in manifest["files"].items():
        path = directory / name
        require(
            path.resolve().parent == directory
            and path.stat().st_size <= 128 * 1024 * 1024
            and fingerprint(path) == expected,
            "RESEARCH_ARTIFACT_CONTENT_DRIFT",
        )
    report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
    require(
        digest(report["selection"]) == manifest["sealed_selection_sha256"]
        and report["configuration_sha256"] == manifest["configuration_sha256"]
        and digest(report["configuration"]) == manifest["configuration_sha256"]
        and manifest["research_code"] == code_identity(),
        "RESEARCH_REPORT_PROVENANCE_DRIFT",
    )
    return {
        "status": "INTEGRITY_VERIFIED_METADATA_ONLY",
        "manifest_sha256": receipt,
        "artifact_model": manifest["artifact_model"],
        "artifact_status": manifest["artifact_status"],
        "executable_loaded": False,
        "serving_authorized": False,
    }
