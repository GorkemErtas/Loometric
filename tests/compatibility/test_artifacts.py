import pytest

from loometric.compatibility.artifacts import inspect_model_profile


def test_metadata_and_byte_inspection_never_deserializes_or_fits(metadata_files, monkeypatch):
    import joblib
    from sklearn.pipeline import Pipeline

    def forbidden(*args, **kwargs):
        pytest.fail("Metadata inspection must not load, fit or execute a model")

    monkeypatch.setattr(joblib, "load", forbidden)
    monkeypatch.setattr(Pipeline, "fit", forbidden)
    monkeypatch.setattr(Pipeline, "predict", forbidden)
    directory, manifest, digest = metadata_files
    result = inspect_model_profile(directory, expected_fingerprint=digest)
    assert result.artifact_fingerprint == digest
    assert result.dataset_sha256 == manifest["lineage"]["dataset_sha256"]
    assert result.pipeline_sha256 == manifest["pipeline_sha256"]


@pytest.mark.parametrize(
    "change", ["receipt", "manifest", "binary", "environment", "configuration", "lineage"]
)
def test_drift_is_rejected_before_any_model_load(metadata_files, change):
    from loometric.prediction.artifacts import canonical_json, digest

    directory, manifest, expected = metadata_files
    if change == "receipt":
        expected = "f" * 64
    elif change == "binary":
        (directory / "pipeline.joblib").write_bytes(b"drift")
    else:
        if change == "environment":
            manifest["environment"]["python"] = "0.0"
        elif change == "configuration":
            manifest["configuration"]["regression"]["max_depth"] = 20
        elif change == "lineage":
            manifest["lineage"]["training"]["rows"] = 1
        else:
            manifest["input_schema_version"] = 2
        (directory / "manifest.json").write_bytes(canonical_json(manifest))
        if change != "manifest":
            expected = digest(manifest)
    with pytest.raises(ValueError):
        inspect_model_profile(directory, expected_fingerprint=expected)
