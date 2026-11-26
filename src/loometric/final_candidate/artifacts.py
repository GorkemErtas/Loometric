"""Create-only v3 publication and independently pinned buffers before executable loading."""

import io
from importlib.resources import files
from pathlib import Path

from loometric.experimental_ml.artifacts import ArtifactError
from loometric.prediction.contracts import read_json
from loometric.prospective_evaluation.protocol import ROOT
from loometric.prospective_evaluation.storage import encode, read_checked, sha256, write_new

ARTIFACT_DIRECTORY = ROOT / "data/processed/experimental_ml/v3"
VERSION = "synthetic-experimental-v3"


def trusted_policy() -> dict:
    return read_json(
        files("loometric.final_candidate").joinpath("trusted_v3.json").read_text(encoding="utf-8")
    )


def verified_bundle(
    *, directory: Path | None = None, policy: dict | None = None
) -> tuple[dict, bytes]:
    try:
        policy = policy if policy is not None else trusted_policy()
        directory = directory if directory is not None else ARTIFACT_DIRECTORY
        if (
            policy["directory"] != "data/processed/experimental_ml/v3"
            or policy["model"] != "history_boost"
            or policy["model_version"] != VERSION
            or policy["experimental_api_authorized"] is not True
            or policy["production_serving_authorized"] is not False
            or policy["capacity_application_authorized"] is not False
            or policy["promotion_decision"] != "NO_ML_PROMOTION"
            or directory.resolve() != directory.absolute()
            or {p.name for p in directory.iterdir()}
            != {"manifest.json", "metadata.json", "history_boost.joblib"}
        ):
            raise ArtifactError()
        raw = read_checked(directory / "manifest.json", 65536)
        if sha256(raw) != policy["manifest_sha256"]:
            raise ArtifactError()
        manifest = read_json(raw.decode())
        if (
            set(manifest) != {"schema_version", "model_version", "promotion_decision", "files"}
            or manifest["schema_version"] != 1
            or manifest["model_version"] != VERSION
            or set(manifest["files"]) != {"metadata.json", "history_boost.joblib"}
            or manifest["promotion_decision"] != "NO_ML_PROMOTION"
        ):
            raise ArtifactError()
        metadata_raw = read_checked(directory / "metadata.json", 1024**2)
        model_raw = read_checked(directory / "history_boost.joblib", 32 * 1024**2)
        if manifest["files"] != {
            "metadata.json": sha256(metadata_raw),
            "history_boost.joblib": sha256(model_raw),
        }:
            raise ArtifactError()
        metadata = read_json(metadata_raw.decode())
        from loometric.final_candidate.data import config, core_identity
        from loometric.final_candidate.model import MODEL_COLUMNS
        from loometric.synthetic_training.artifacts import environment

        if (
            metadata["model"] != "history_boost"
            or metadata["schema_version"] != 1
            or metadata["model_version"] != VERSION
            or metadata["model_status"] != "EXPERIMENTAL_HISTORY_CANDIDATE"
            or metadata["experiment_id"] != "EXP-010"
            or metadata["model_sha256"] != sha256(model_raw)
            or metadata["code"] != core_identity()
            or metadata["configuration_sha256"] != sha256(encode(config()))
            or metadata["environment"] != environment()
            or metadata["feature_columns"] != list(MODEL_COLUMNS)
            or metadata["target"] != "standard_capacity_attainment"
            or metadata["units"] != config()["units"]
            or metadata["integration_passed"] is not True
            or metadata["requires_mature_history"] is not True
            or metadata["minimum_uncensored_history"] != 2
            or metadata["maximum_history_age_hours"] != 72
            or metadata["experimental_api_authorized"] is not True
            or metadata["production_serving_authorized"] is not False
            or metadata["capacity_application_authorized"] is not False
            or metadata["promotion_decision"] != "NO_ML_PROMOTION"
        ):
            raise ArtifactError()
        return metadata, model_raw
    except (OSError, ValueError, KeyError, TypeError, ImportError):
        raise ArtifactError() from None


def load_trusted(*, directory: Path | None = None, policy: dict | None = None):
    metadata, raw = verified_bundle(directory=directory, policy=policy)
    import joblib
    from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
    from sklearn.pipeline import Pipeline

    from loometric.final_candidate.model import HistoryBoost

    try:
        model = joblib.load(io.BytesIO(raw))
        if (
            not isinstance(model, HistoryBoost)
            or model.code_identity != metadata["code"]
            or model.configuration_sha256 != metadata["configuration_sha256"]
            or not isinstance(model.foundation, Pipeline)
            or not isinstance(model.foundation.named_steps["regression"], RandomForestRegressor)
            or not isinstance(model.residual_model, Pipeline)
            or not isinstance(
                model.residual_model.named_steps["regression"], HistGradientBoostingRegressor
            )
            or model.input_profile != metadata["input_profile"]
        ):
            raise ArtifactError()
        return metadata, model
    except Exception:
        raise ArtifactError() from None


def publish(expected_model: str, expected_report: str) -> dict:
    from loometric.final_candidate import data
    from loometric.final_candidate.model import MODEL_COLUMNS
    from loometric.final_candidate.study import load_candidate, mean_metrics
    from loometric.synthetic_training.artifacts import environment

    if ARTIFACT_DIRECTORY.exists():
        raise ValueError("CREATE_ONLY_V3_PUBLICATION_REQUIRED")
    a = read_checked(data.DIRECTORY / "heldout/a.report.json", 32 * 1024**2)
    b = read_checked(data.DIRECTORY / "heldout/b.report.json", 32 * 1024**2)
    if sha256(a) != expected_report or a != b:
        raise ValueError("INDEPENDENT_REPRODUCED_REPORT_REQUIRED")
    report = read_json(a.decode())
    if report["integration"]["eligible_for_experimental_integration"] is not True or not all(
        v["passed"] for v in report["integration"]["guards"].values()
    ):
        raise ValueError("CANDIDATE_INTEGRATION_NOT_SUPPORTED")
    model = load_candidate(expected_model)
    receipt = read_json(read_checked(data.DIRECTORY / "candidate.receipt.json", 65536).decode())
    comparisons = {}
    for condition in ("baseline", "disruption"):
        cells = [v for k, v in report["cases"].items() if k.endswith(condition)]
        comparisons[condition] = {
            name: {
                **report["macro"][condition][name],
                "samples": sum(v["defined_targets"] for v in cells),
                "actual_worst_absolute_error": max(
                    v["models"][name]["metrics"]["worst_absolute_error"] for v in cells
                ),
                "stages": {
                    stage: {
                        **mean_metrics([v["models"][name]["stages"][stage] for v in cells]),
                        "samples": sum(v["models"][name]["stages"][stage]["rows"] for v in cells),
                    }
                    for stage in cells[0]["models"][name]["stages"]
                },
            }
            for name in report["macro"][condition]
            if name != "missing_history_control"
        }
    metadata = {
        "schema_version": 1,
        "model": "history_boost",
        "model_version": VERSION,
        "model_status": "EXPERIMENTAL_HISTORY_CANDIDATE",
        "model_sha256": expected_model,
        "code": receipt["code"],
        "configuration_sha256": receipt["configuration_sha256"],
        "environment": environment(),
        "feature_columns": list(MODEL_COLUMNS),
        "target": "standard_capacity_attainment",
        "units": data.config()["units"],
        "training": receipt,
        "input_profile": model.input_profile,
        "comparisons": comparisons,
        "experiment_id": "EXP-010",
        "report_sha256": expected_report,
        "integration_passed": True,
        "requires_mature_history": True,
        "minimum_uncensored_history": 2,
        "maximum_history_age_hours": 72,
        "experimental_api_authorized": True,
        "production_serving_authorized": False,
        "capacity_application_authorized": False,
        "promotion_decision": "NO_ML_PROMOTION",
    }
    model_raw = read_checked(data.DIRECTORY / "candidate.joblib", 32 * 1024**2)
    metadata_raw = encode(metadata)
    manifest = {
        "schema_version": 1,
        "model_version": VERSION,
        "promotion_decision": "NO_ML_PROMOTION",
        "files": {"metadata.json": sha256(metadata_raw), "history_boost.joblib": sha256(model_raw)},
    }
    for name, content in (
        ("history_boost.joblib", model_raw),
        ("metadata.json", metadata_raw),
        ("manifest.json", encode(manifest)),
    ):
        write_new(ARTIFACT_DIRECTORY, name, content)
    return {
        "directory": "data/processed/experimental_ml/v3",
        "model": "history_boost",
        "model_version": VERSION,
        "manifest_sha256": sha256(encode(manifest)),
        "experimental_api_authorized": True,
        "production_serving_authorized": False,
        "capacity_application_authorized": False,
        "promotion_decision": "NO_ML_PROMOTION",
    }
