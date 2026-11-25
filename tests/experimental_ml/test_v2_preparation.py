"""Create-only v2 preparation and retained-prediction parity, using private fixtures."""

import json

import pytest
from threadpoolctl import threadpool_limits

from loometric.experimental_ml.artifacts import canonical, sha256
from loometric.experimental_ml_v2 import parity, publish


@pytest.fixture
def candidate_source(v2_publication_fixture, tmp_path, monkeypatch):
    fixture = v2_publication_fixture
    source = tmp_path / "research"
    source.mkdir()
    model_bytes = (fixture["directory"] / "rf_physics.joblib").read_bytes()
    (source / "research-model.joblib").write_bytes(model_bytes)
    metadata = json.loads((fixture["directory"] / "metadata.json").read_bytes())
    manifest_bytes = canonical(
        {
            "files": {"research-model.joblib": sha256(model_bytes)},
            "research_code": metadata["research_code"],
        }
    )
    (source / "manifest.json").write_bytes(manifest_bytes)
    source_receipt = sha256(manifest_bytes)
    monkeypatch.setattr(publish, "SOURCE_DIRECTORY", source)
    monkeypatch.setattr(publish, "SOURCE_MANIFEST_SHA256", source_receipt)
    monkeypatch.setattr(publish, "SOURCE_MODEL_SHA256", sha256(model_bytes))
    metadata["source_manifest_sha256"] = source_receipt
    expected = canonical(
        {
            "schema_version": 1,
            "model_version": "synthetic-experimental-v2",
            "model": "rf_physics",
            "promotion_decision": "NO_ML_PROMOTION",
            "capacity_application_authorized": False,
            "reserved_labels_decoded": False,
            "serving_authorized": False,
            "files": {
                "metadata.json": sha256(canonical(metadata)),
                "rf_physics.joblib": sha256(model_bytes),
            },
        }
    )
    monkeypatch.setattr(publish, "TRUSTED_MANIFEST_SHA256", sha256(expected))
    output = tmp_path / "prepared"
    monkeypatch.setattr(publish, "ARTIFACT_DIRECTORY", output)

    def verified(directory, receipt):
        # The full source inspector is tested under tests/ml_research. This seam
        # isolates publication's own checks after successful metadata inspection.
        assert directory == source and receipt == source_receipt
        return {
            "status": "INTEGRITY_VERIFIED_METADATA_ONLY",
            "artifact_model": "rf_physics",
            "artifact_status": "RESEARCH_CANDIDATE",
            "serving_authorized": False,
        }

    monkeypatch.setattr(publish, "inspect_research", verified)
    monkeypatch.setattr("joblib.load", lambda *a, **k: pytest.fail("Publication unpickled a model"))
    return source, output, expected


def test_preparation_reproduces_exact_bytes_without_loading_or_fitting(
    candidate_source, monkeypatch
):
    source, output, expected = candidate_source
    result = publish.publish()
    assert (output / "manifest.json").read_bytes() == expected
    assert (output / "rf_physics.joblib").read_bytes() == (
        source / "research-model.joblib"
    ).read_bytes()
    assert result["manifest_sha256"] == sha256(expected)
    assert result["serving_authorized"] is False
    assert result["promotion_decision"] == "NO_ML_PROMOTION"
    repeat = output.with_name("repeat")
    monkeypatch.setattr(publish, "ARTIFACT_DIRECTORY", repeat)
    assert publish.publish() == result
    assert {p.name for p in repeat.iterdir()} == {
        "manifest.json",
        "metadata.json",
        "rf_physics.joblib",
    }
    assert all(p.read_bytes() == (output / p.name).read_bytes() for p in repeat.iterdir())
    monkeypatch.setattr(
        publish, "inspect_research", lambda *a: pytest.fail("Existing output inspected sources")
    )
    with pytest.raises(FileExistsError):
        publish.publish()


@pytest.mark.parametrize("failure", ["source_manifest", "model", "serving_receipt"])
def test_preparation_drift_rejected_before_creating_output(candidate_source, monkeypatch, failure):
    source, output, _ = candidate_source
    if failure == "serving_receipt":
        monkeypatch.setattr(publish, "TRUSTED_MANIFEST_SHA256", "a" * 64)
    else:
        name = "manifest.json" if failure == "source_manifest" else "research-model.joblib"
        (source / name).write_bytes(b"tampered")
    with pytest.raises(ValueError):
        publish.publish()
    assert not output.exists()


def test_parity_matches_retained_rows_and_rejects_prediction_drift(
    private_v2_bundle, publication_fixture, v2_publication_fixture, tmp_path, monkeypatch
):
    data = publication_fixture["data"]
    candidate = v2_publication_fixture["model"]
    with threadpool_limits(limits=1):
        predicted = candidate.predict(data.validation.X)
    rows = [
        {
            "case": "benchmark-42-baseline",
            "model": "rf_physics",
            "observation_id": oid,
            "prediction": float(value),
        }
        for oid, value in zip(data.validation.X.index, predicted, strict=True)
    ]
    path = tmp_path / "spent-diagnostics.jsonl"
    path.write_bytes(b"".join(canonical(row) for row in rows))
    monkeypatch.setattr(parity, "SOURCE_DIRECTORY", tmp_path)
    monkeypatch.setattr(parity, "inspect_research", lambda *a: None)

    def development(directory, *, expected_fingerprint):
        assert expected_fingerprint == (
            "7e7dae049270675c2eac4f8ad05d55a9ac84cc9c1160e0a6b7e9f4010a64f7eb"
        )
        return data

    monkeypatch.setattr(parity, "load_development", development)
    result = parity.verify_parity()
    assert result["validation_rows"] == len(data.validation.X)
    assert result["maximum_absolute_difference"] == 0
    assert result["fresh_validation"] is False
    assert result["promotion_decision"] == "NO_ML_PROMOTION"
    rows[0]["prediction"] += 0.01
    path.write_bytes(b"".join(canonical(row) for row in rows))
    with pytest.raises(ValueError, match="Prediction parity failed"):
        parity.verify_parity()
    path.write_bytes(b"".join(canonical(row) for row in rows[1:]))
    with pytest.raises(ValueError, match="Validation row mismatch"):
        parity.verify_parity()
