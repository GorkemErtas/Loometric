"""Publish the frozen EXP-008 candidate for experimental inference."""

import json

from loometric.experimental_ml.artifacts import canonical, sha256
from loometric.experimental_ml_v2.constants import (
    ARTIFACT_DIRECTORY,
    CAPACITY_APPLICATION_AUTHORIZED,
    MAX_MODEL_BYTES,
    MODEL_NAME,
    MODEL_STATUS,
    PROMOTION_DECISION,
    SOURCE_DIRECTORY,
    SOURCE_EXPERIMENT,
    SOURCE_MANIFEST_SHA256,
    SOURCE_MODEL_SHA256,
    TRUSTED_MANIFEST_SHA256,
    VERSION,
)
from loometric.ml_research.artifacts import inspect_research
from loometric.synthetic_ml.features import FEATURE_COLUMNS
from loometric.synthetic_training.artifacts import environment


def publish() -> dict:
    """Create a separate, receipt-bound experimental artifact."""

    if ARTIFACT_DIRECTORY.exists():
        raise FileExistsError("Experimental v2 artifact already exists.")

    verification = inspect_research(
        SOURCE_DIRECTORY,
        SOURCE_MANIFEST_SHA256,
    )

    if (
        verification["status"] != "INTEGRITY_VERIFIED_METADATA_ONLY"
        or verification["artifact_model"] != MODEL_NAME
        or verification["artifact_status"] != MODEL_STATUS
        or verification["serving_authorized"] is not False
    ):
        raise ValueError("Unexpected research artifact identity.")

    source_manifest_bytes = (SOURCE_DIRECTORY / "manifest.json").read_bytes()

    if sha256(source_manifest_bytes) != SOURCE_MANIFEST_SHA256:
        raise ValueError("Source manifest digest mismatch.")

    source_manifest = json.loads(source_manifest_bytes)

    model_path = SOURCE_DIRECTORY / "research-model.joblib"

    if model_path.resolve() != (SOURCE_DIRECTORY.resolve() / "research-model.joblib"):
        raise ValueError("Unexpected source model path.")

    with model_path.open("rb") as source:
        model_bytes = source.read(MAX_MODEL_BYTES + 1)

    if len(model_bytes) > MAX_MODEL_BYTES:
        raise ValueError("Model exceeds the permitted size.")

    if sha256(model_bytes) != SOURCE_MODEL_SHA256:
        raise ValueError("Source model digest mismatch.")

    if source_manifest["files"]["research-model.joblib"] != SOURCE_MODEL_SHA256:
        raise ValueError("Source model receipt mismatch.")

    metadata = {
        "schema_version": 1,
        "model_version": VERSION,
        "model": MODEL_NAME,
        "model_status": MODEL_STATUS,
        "source_experiment": SOURCE_EXPERIMENT,
        "source_manifest_sha256": SOURCE_MANIFEST_SHA256,
        "source_model_sha256": SOURCE_MODEL_SHA256,
        "dataset_version": "synthetic-ml-v1",
        "target": "standard_capacity_attainment",
        "feature_order": list(FEATURE_COLUMNS),
        "training_partition": "train",
        "environment": environment(),
        "research_code": source_manifest["research_code"],
        "promotion_decision": PROMOTION_DECISION,
        "reserved_labels_decoded": False,
        "capacity_application_authorized": (CAPACITY_APPLICATION_AUTHORIZED),
        "experimental_only": True,
        "serving_authorized": False,
    }

    buffers = {
        "rf_physics.joblib": model_bytes,
        "metadata.json": canonical(metadata),
    }

    manifest = {
        "schema_version": 1,
        "model_version": VERSION,
        "model": MODEL_NAME,
        "promotion_decision": PROMOTION_DECISION,
        "capacity_application_authorized": False,
        "reserved_labels_decoded": False,
        "serving_authorized": False,
        "files": {name: sha256(value) for name, value in sorted(buffers.items())},
    }

    manifest_bytes = canonical(manifest)

    if sha256(manifest_bytes) != TRUSTED_MANIFEST_SHA256:
        raise ValueError("Prepared artifact does not match the independent serving receipt.")

    ARTIFACT_DIRECTORY.mkdir(parents=True, exist_ok=False)

    for name, value in buffers.items():
        with (ARTIFACT_DIRECTORY / name).open("xb") as output:
            output.write(value)

    with (ARTIFACT_DIRECTORY / "manifest.json").open("xb") as output:
        output.write(manifest_bytes)

    return {
        "status": "EXPERIMENTAL_ARTIFACT_PREPARED",
        "model": MODEL_NAME,
        "model_version": VERSION,
        "manifest_sha256": sha256(manifest_bytes),
        "model_sha256": sha256(model_bytes),
        "model_bytes": len(model_bytes),
        "serving_authorized": False,
        "promotion_decision": PROMOTION_DECISION,
    }


if __name__ == "__main__":
    print(json.dumps(publish(), indent=2))
