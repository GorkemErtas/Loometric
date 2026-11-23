import copy
import json

import numpy as np
import pytest
from threadpoolctl import threadpool_limits

from loometric.experimental_ml.artifacts import ArtifactError, load_trusted, verified_bundle
from loometric.experimental_ml.constants import MODELS
from loometric.experimental_ml.publish import publish_models, publish_version
from loometric.synthetic_training.models import model_metadata


def test_reproducible_publication_and_actual_fitted_pipeline_parity(publication_fixture):
    fixture = publication_fixture
    result = publish_models(
        fixture["data"], fixture["report"], fixture["rows"], fixture["root"] / "repeat"
    )
    assert result == fixture["result"]
    assert all(p["maximum_absolute_difference"] == 0 for p in result["parity"].values())
    metadata, models = load_trusted(fixture["receipt"], directory=fixture["directory"])
    X = fixture["data"].validation.X
    expected = {(r["model"], r["observation_id"]): r["prediction"] for r in fixture["rows"]}
    with threadpool_limits(limits=1):
        for name, model in models.items():
            assert np.array_equal(
                model.predict(X), [expected[MODELS[name], oid] for oid in X.index]
            )
            assert metadata["models"][name]["preprocessing"] == model_metadata(model)
    importance = metadata["models"]["random_forest"]["global_feature_importance"]
    assert len(importance) == 13
    assert sum(r["importance"] for r in importance) == pytest.approx(1)
    assert metadata["models"]["grouped_mean"]["estimator_kind"] == "TRANSPARENT_GROUP_MEANS"
    assert metadata["promotion_decision"] == "NO_ML_PROMOTION"


def test_changed_saved_validation_prediction_blocks_publication(publication_fixture):
    fixture = publication_fixture
    rows = copy.deepcopy(fixture["rows"])
    rows[0]["prediction"] += 0.001
    output = fixture["root"] / "bad-parity"
    with pytest.raises(ValueError, match="M08B_PREDICTION_PARITY_FAILED"):
        publish_models(fixture["data"], fixture["report"], rows, output)
    assert not output.exists()


def test_existing_output_rejected_before_fit(publication_fixture, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Existing publication must not fit or load data")

    monkeypatch.setattr("loometric.experimental_ml.publish.build_model", forbidden)
    f = publication_fixture
    with pytest.raises(ValueError, match="CREATE_ONLY"):
        publish_models(f["data"], f["report"], f["rows"], f["directory"])
    with pytest.raises(ValueError, match="ALLOWLISTED"):
        publish_version("../../anything")


@pytest.mark.parametrize(
    "name",
    [
        "manifest.json",
        "metadata.json",
        "random_forest.joblib",
        "histogram_gradient_boosting.joblib",
        "grouped_mean.json",
    ],
)
def test_any_tampering_fails_before_deserialization(private_bundle, monkeypatch, name):
    directory, receipt = private_bundle
    (directory / name).write_bytes((directory / name).read_bytes() + b" ")
    monkeypatch.setattr(
        "joblib.load", lambda *args, **kwargs: pytest.fail("Unverified pickle loaded")
    )
    with pytest.raises(ArtifactError, match="EXPERIMENTAL_ARTIFACT_UNAVAILABLE"):
        load_trusted(receipt, directory=directory)


@pytest.mark.parametrize("receipt", ["", "a" * 64, "../manifest", None])
def test_missing_or_wrong_trust_receipt_rejected(private_bundle, monkeypatch, receipt):
    monkeypatch.setattr(
        "joblib.load", lambda *args, **kwargs: pytest.fail("Unverified pickle loaded")
    )
    with pytest.raises(ArtifactError):
        verified_bundle(private_bundle[0], receipt)


def test_loading_uses_the_verified_buffer_even_if_file_changes(private_bundle, monkeypatch):
    import joblib

    original = joblib.load
    directory, receipt = private_bundle
    calls = []

    def replace_after_verification(buffer):
        assert hasattr(buffer, "read")
        (directory / "histogram_gradient_boosting.joblib").write_bytes(b"untrusted replacement")
        calls.append(True)
        return original(buffer)

    monkeypatch.setattr(joblib, "load", replace_after_verification)
    _, models = load_trusted(receipt, directory=directory)
    assert len(calls) == 2 and set(models) == set(MODELS)


def test_environment_mismatch_is_checked_before_unpickle(private_bundle, monkeypatch):
    from loometric.experimental_ml.artifacts import canonical, sha256

    directory, _ = private_bundle
    metadata = json.loads((directory / "metadata.json").read_bytes())
    metadata["environment"]["python"] = "0.0"
    (directory / "metadata.json").write_bytes(canonical(metadata))
    manifest = json.loads((directory / "manifest.json").read_bytes())
    manifest["files"]["metadata.json"] = sha256(canonical(metadata))
    (directory / "manifest.json").write_bytes(canonical(manifest))
    monkeypatch.setattr(
        "joblib.load", lambda *args, **kwargs: pytest.fail("Wrong environment loaded")
    )
    with pytest.raises(ArtifactError):
        load_trusted(sha256(canonical(manifest)), directory=directory)
