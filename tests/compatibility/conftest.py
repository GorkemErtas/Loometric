import hashlib
from datetime import date
from pathlib import Path

import pytest

from loometric.compatibility.contracts import AssessmentRequest, ModelProfile
from loometric.scheduling.loading import load_instance

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def instance():
    return load_instance(ROOT / "examples/scheduling/competition.json")


@pytest.fixture
def request_context():
    return AssessmentRequest.from_json(
        (ROOT / "examples/compatibility/request.json").read_text(encoding="utf-8")
    )


@pytest.fixture
def model_profile(request_context):
    return ModelProfile(
        request_context.artifact_fingerprint,
        request_context.model_configuration_fingerprint,
        "a" * 64,
        "b" * 64,
        "c" * 64,
        date(2015, 2, 10),
        ("finishing", "sewing"),
        tuple(str(n) for n in range(1, 13)),
        ("0", "1", "2", "3", "5", "6"),
    )


@pytest.fixture
def metadata_files(tmp_path):
    """Synthetic integrity bytes, not a fitted/usable estimator or real ML evidence."""

    from loometric.prediction.artifacts import (
        canonical_json,
        digest,
        environment,
        model_configuration,
    )

    directory = tmp_path / "metadata"
    directory.mkdir()
    binary = b"synthetic non-pickle bytes; never deserialize"
    lineage = {
        "dataset_sha256": "a" * 64,
        "split_file_sha256": "b" * 64,
        "strategy": "distinct-date-floor-60-20-20-v1",
        "training": {"start": "2015-01-01", "end": "2015-02-10", "rows": 711, "distinct_dates": 35},
    }
    lineage["training_split_fingerprint"] = digest(lineage)
    configuration = model_configuration()
    manifest = {
        "artifact_schema_version": 1,
        "input_schema_version": 1,
        "configuration": configuration,
        "model_configuration_fingerprint": digest(configuration),
        "environment": environment(),
        "lineage": lineage,
        "pipeline_sha256": hashlib.sha256(binary).hexdigest(),
        "training_categories": {
            "department": ["finishing", "sewing"],
            "team": [str(n) for n in range(1, 13)],
            "day_of_week": ["0", "1", "2", "3", "5", "6"],
        },
    }
    (directory / "manifest.json").write_bytes(canonical_json(manifest))
    (directory / "pipeline.joblib").write_bytes(binary)
    return directory, manifest, digest(manifest)
