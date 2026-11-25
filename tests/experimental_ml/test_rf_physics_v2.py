"""RF Physics contract, trust, authorization and train-only support regressions."""

import copy
import json
from itertools import combinations

import numpy as np
import pytest
from pydantic import ValidationError
from threadpoolctl import threadpool_limits

from loometric.api.prediction_schemas import SyntheticPredictionRequest
from loometric.api.prediction_schemas_v2 import SyntheticPredictionRequestV2
from loometric.experimental_ml.artifacts import ArtifactError, canonical, load_trusted, sha256
from loometric.experimental_ml.inference import predict
from loometric.experimental_ml_v2 import artifacts, serving
from loometric.experimental_ml_v2.inference import predict_v2
from loometric.synthetic_training.risk import support_profile


def contract(models=None, **updates):
    from pathlib import Path

    body = json.loads(
        (
            Path(__file__).resolve().parents[2] / "examples/api/synthetic-prediction.json"
        ).read_bytes()
    )
    body.update(
        schema_version=2, models=models if models is not None else [*body["models"], "rf_physics"]
    )
    body.update(updates)
    return SyntheticPredictionRequestV2.model_validate(body)


def legacy_bundle(fixture):
    return load_trusted(fixture["receipt"], directory=fixture["directory"])


def test_verified_candidate_parity_uses_the_checked_buffer(
    private_v2_bundle, v2_publication_fixture, publication_fixture, monkeypatch
):
    import joblib

    original = joblib.load

    def replace_after_verification(buffer):
        assert hasattr(buffer, "read")
        (private_v2_bundle / "rf_physics.joblib").write_bytes(b"replacement after verification")
        return original(buffer)

    monkeypatch.setattr(joblib, "load", replace_after_verification)
    metadata, model = artifacts.load_trusted_offline()
    X = publication_fixture["data"].validation.X
    with threadpool_limits(limits=1):
        assert np.array_equal(model.predict(X), v2_publication_fixture["model"].predict(X))
    assert metadata["experimental_only"] is True
    assert metadata["serving_authorized"] is False
    assert metadata["promotion_decision"] == "NO_ML_PROMOTION"


@pytest.mark.parametrize("name", ["manifest.json", "metadata.json", "rf_physics.joblib"])
def test_v2_tampering_rejected_before_unpickling(private_v2_bundle, monkeypatch, name):
    path = private_v2_bundle / name
    path.write_bytes(path.read_bytes() + b" ")
    monkeypatch.setattr("joblib.load", lambda *a, **k: pytest.fail("Unverified model executed"))
    with pytest.raises(ArtifactError):
        artifacts.load_trusted_offline()


@pytest.mark.parametrize(
    "field,value",
    [
        ("environment", {}),
        ("research_code", {}),
        ("feature_order", []),
        ("dataset_version", "synthetic-ml-v2"),
        ("target", "actual_productivity"),
        ("training_partition", "validation"),
        ("source_experiment", "EXP-006"),
        ("source_manifest_sha256", "a" * 64),
        ("source_model_sha256", "a" * 64),
        ("experimental_only", False),
        ("serving_authorized", True),
        ("promotion_decision", "PROMOTED"),
        ("capacity_application_authorized", True),
        ("reserved_labels_decoded", True),
    ],
)
def test_v2_metadata_policy_checked_even_with_a_trusted_test_receipt(
    private_v2_bundle, monkeypatch, field, value
):
    metadata = json.loads((private_v2_bundle / "metadata.json").read_bytes())
    metadata[field] = value
    metadata_bytes = canonical(metadata)
    (private_v2_bundle / "metadata.json").write_bytes(metadata_bytes)
    manifest = json.loads((private_v2_bundle / "manifest.json").read_bytes())
    manifest["files"]["metadata.json"] = sha256(metadata_bytes)
    manifest_bytes = canonical(manifest)
    (private_v2_bundle / "manifest.json").write_bytes(manifest_bytes)
    monkeypatch.setattr(artifacts, "TRUSTED_MANIFEST_SHA256", sha256(manifest_bytes))
    monkeypatch.setattr("joblib.load", lambda *a, **k: pytest.fail("Incompatible model loaded"))
    with pytest.raises(ArtifactError):
        artifacts.load_trusted_offline()


def test_v2_model_size_and_noncanonical_directory_fail_before_unpickling(
    private_v2_bundle, monkeypatch
):
    monkeypatch.setattr("joblib.load", lambda *a, **k: pytest.fail("Unsafe artifact loaded"))
    monkeypatch.setattr(artifacts, "MAX_MODEL_BYTES", 1)
    with pytest.raises(ArtifactError):
        artifacts.load_trusted_offline()
    monkeypatch.setattr(artifacts, "ARTIFACT_DIRECTORY", private_v2_bundle / ".." / "v2")
    with pytest.raises(ArtifactError):
        artifacts.load_trusted_offline()


@pytest.mark.parametrize(
    "field,value",
    [
        ("experimental_api_authorized", False),
        ("experimental_api_authorized", 1),
        ("production_serving_authorized", True),
        ("capacity_application_authorized", True),
        ("manifest_sha256", "a" * 64),
        ("model", "random_forest"),
        ("model_version", "synthetic-experimental-v1"),
        ("source_experiment", "EXP-006"),
        ("promotion_decision", "PROMOTED"),
        ("prediction_context", "MEASURED_FACTORY"),
    ],
)
def test_serving_requires_complete_explicit_experimental_policy(
    private_v2_bundle, monkeypatch, field, value
):
    monkeypatch.setattr(
        serving, "load_trusted_offline", lambda: pytest.fail("Unauthorized deserialization")
    )
    monkeypatch.setitem(serving.EXPERIMENTAL_SERVING_RECEIPT, field, value)
    with pytest.raises(ArtifactError):
        serving.load_experimental_model(contract())
    monkeypatch.delitem(serving.EXPERIMENTAL_SERVING_RECEIPT, field)
    with pytest.raises(ArtifactError):
        serving.load_experimental_model(contract())


@pytest.mark.parametrize(
    "updates",
    [
        {"schema_version": 1},
        {"synthetic": False},
        {"prediction_context": "MEASURED_FACTORY"},
        {"models": ["random_forest"]},
    ],
)
def test_serving_rejects_wrong_context_before_loading(private_v2_bundle, monkeypatch, updates):
    monkeypatch.setattr(
        serving, "load_trusted_offline", lambda: pytest.fail("Unauthorized deserialization")
    )
    with pytest.raises(ArtifactError):
        serving.load_experimental_model(contract().model_copy(update=updates))


def test_four_models_share_inputs_preserve_v1_and_have_separate_provenance(
    private_v2_bundle, publication_fixture, v2_publication_fixture, monkeypatch
):
    metadata, models = legacy_bundle(publication_fixture)
    research_metadata, candidate = serving.load_experimental_model(contract())
    seen = []
    for model in [*models.values(), candidate]:
        original = model.predict

        def spy(X, original=original):
            seen.append(X.copy(deep=True))
            return original(X)

        monkeypatch.setattr(model, "predict", spy)
        monkeypatch.setattr(model, "fit", lambda *a, **k: pytest.fail("Inference trained a model"))
    request = contract()
    before = request.model_dump()
    result = predict_v2(request, metadata, models, publication_fixture["receipt"], candidate)
    assert len(seen) == 4 and all(frame.equals(seen[0]) for frame in seen)
    assert request.model_dump() == before
    legacy_request = SyntheticPredictionRequest(
        schema_version=1,
        synthetic=True,
        prediction_context=request.prediction_context,
        models=request.models[:-1],
        inputs=request.inputs,
    )
    legacy = predict(legacy_request, metadata, models, publication_fixture["receipt"])
    assert result["results"][:3] == legacy["results"]
    assert result["input_fingerprint"] == legacy["input_fingerprint"]
    assert result["provenance"]["manifest_sha256"] == publication_fixture["receipt"]
    assert (
        result["provenance"]["research_candidate"]["manifest_sha256"]
        == v2_publication_fixture["receipt"]
    )
    assert result["schema_version"] == 2
    assert result["capacity_application_authorized"] is False
    assert (
        result["promotion_decision"] == research_metadata["promotion_decision"] == "NO_ML_PROMOTION"
    )
    research = result["results"][3]
    assert research["provenance"] == {
        "experiment_id": "EXP-008",
        "manifest_sha256": v2_publication_fixture["receipt"],
        "validation_rows": 4833,
        "fresh_validation": False,
        "support_profile_source": "V1_BENCHMARK_TRAINING",
    }
    assert research["descriptive_band"] is research["promotion_checks"] is None
    assert research["validation_stage_metrics"] is research["global_feature_importance"] is None
    assert len(result["differences"]) == 6
    for diff, (a, b) in zip(result["differences"], combinations(result["results"], 2), strict=True):
        assert (diff["left"], diff["right"]) == (a["model"], b["model"])
        assert diff["left_minus_right"] == a["prediction"] - b["prediction"]


def test_legacy_only_v2_never_requires_candidate_artifacts(publication_fixture):
    metadata, models = legacy_bundle(publication_fixture)
    result = predict_v2(
        contract(["grouped_mean", "random_forest"]), metadata, models, "receipt", None
    )
    assert result["provenance"]["research_candidate"] is None
    assert [r["model"] for r in result["results"]] == ["grouped_mean", "random_forest"]
    assert len(result["differences"]) == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"planned_workers": 0},
        {"available_minutes": 0},
        {"planned_machine_available": False},
        {"stage": "unknown"},
        {"weekday": 6},
    ],
)
def test_v2_abstains_before_candidate_execution(
    private_v2_bundle, publication_fixture, monkeypatch, changes
):
    metadata, models = legacy_bundle(publication_fixture)
    candidate = serving.load_experimental_model(contract())[1]
    for model in [*models.values(), candidate]:
        monkeypatch.setattr(
            model, "predict", lambda *a, **k: pytest.fail("Abstention reached estimator")
        )
    request = contract()
    inputs = request.inputs.model_copy(update=changes)
    result = predict_v2(
        request.model_copy(update={"inputs": inputs}), metadata, models, "receipt", candidate
    )
    assert all(
        r["prediction"] is None and r["support"]["status"] == "ABSTAIN" for r in result["results"]
    )
    assert all(d["left_minus_right"] is None for d in result["differences"])


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.1, 3.1, 1.2])
def test_candidate_output_support_and_above_one_values(
    private_v2_bundle, publication_fixture, monkeypatch, value
):
    metadata, models = legacy_bundle(publication_fixture)
    candidate = serving.load_experimental_model(contract())[1]
    monkeypatch.setattr(candidate, "predict", lambda X: [value])
    request = contract(["rf_physics"])
    request = request.model_copy(
        update={"inputs": request.inputs.model_copy(update={"planned_workers": 30})}
    )
    result = predict_v2(request, metadata, models, "receipt", candidate)["results"][0]
    if value == 1.2:
        assert result["prediction"] == 1.2 and result["support"]["status"] == "REVIEW_REQUIRED"
        assert "OUTSIDE_TRAINING_SUPPORT:planned_workers" in result["support"]["reason_codes"]
    else:
        assert result["prediction"] is None and result["support"]["status"] == "ABSTAIN"
    assert result["descriptive_band"] is None


@pytest.mark.parametrize(
    "section,field,value",
    [
        ("training", "partition", "validation"),
        ("training", "case", "other-training-case"),
        ("source", "train_fingerprint", "a" * 64),
        ("support", "training_label_maximum", 3.0),
        ("support", "categories", {}),
    ],
)
def test_candidate_rejects_unmatched_training_support_before_predicting(
    private_v2_bundle, publication_fixture, monkeypatch, section, field, value
):
    metadata, models = legacy_bundle(publication_fixture)
    metadata = copy.deepcopy(metadata)
    target = metadata["training"]["source"] if section == "source" else metadata[section]
    target[field] = value
    candidate = serving.load_experimental_model(contract())[1]
    for model in [*models.values(), candidate]:
        monkeypatch.setattr(
            model, "predict", lambda *a, **k: pytest.fail("Mismatched support reached estimator")
        )
    with pytest.raises(ArtifactError):
        predict_v2(contract(), metadata, models, "receipt", candidate)


def test_support_profile_is_exactly_original_training_only(private_v2_bundle, publication_fixture):
    metadata, _ = legacy_bundle(publication_fixture)
    data = publication_fixture["data"]
    expected = support_profile(data.train.X, data.train.y)
    assert metadata["support"] == expected
    assert metadata["training"]["source"] == data.provenance
    assert metadata["training"]["rows"] == len(data.train.X)
    # A validation-derived profile is detectably different; a combined or
    # validation-only profile cannot silently satisfy this regression.
    assert expected != support_profile(data.validation.X, data.validation.y)


@pytest.mark.parametrize(
    "updates",
    [
        {"schema_version": 1},
        {"schema_version": True},
        {"synthetic": 1},
        {"synthetic": False},
        {"models": []},
        {"models": ["rf_physics"] * 2},
        {"models": ["unknown"]},
        {"models": ["rf_physics"] * 5},
        {"path": "model.joblib"},
        {"receipt": "a" * 64},
        {"train": True},
    ],
)
def test_v2_closed_envelope_retains_v1_validation(updates):
    with pytest.raises(ValidationError):
        contract(**updates)
