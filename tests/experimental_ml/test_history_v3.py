"""Private mechanical v3 artifacts and additive contracts; never actual experiment data."""

import copy
import io
import json
from pathlib import Path

import joblib
import pytest
from pydantic import ValidationError
from test_api import native_app as native_app
from test_api import native_app_v2 as native_app_v2
from threadpoolctl import threadpool_limits

from loometric.api.prediction_schemas import SyntheticPredictionRequest
from loometric.api.prediction_schemas_v2 import SyntheticPredictionRequestV2
from loometric.api.prediction_schemas_v3 import MatureHistory, SyntheticPredictionRequestV3
from loometric.experimental_ml.artifacts import ArtifactError, load_trusted
from loometric.experimental_ml_v2.inference import predict_v2
from loometric.final_candidate import artifacts, inference
from loometric.final_candidate.data import config, core_identity
from loometric.final_candidate.model import MODEL_COLUMNS, HistoryBoost
from loometric.prospective_evaluation.storage import encode, sha256
from loometric.synthetic_training.artifacts import environment

READY = {
    "recent_attainment_mean": 0.85,
    "recent_attainment_std": 0.1,
    "history_count": 7,
    "uncensored_history_count": 4,
    "history_age_hours": 16.0,
}
NAMES = ["random_forest", "histogram_gradient_boosting", "grouped_mean", "rf_physics"]


def body(**updates):
    value = json.loads(Path("examples/api/synthetic-prediction.json").read_bytes())
    value.update(schema_version=3, models=[*NAMES, "history_boost"], history=READY)
    value.update(updates)
    return value


@pytest.fixture(scope="module")
def private_history_model(publication_fixture, v2_publication_fixture):
    data = publication_fixture["data"]
    X = data.train.X.copy()
    for key, value in READY.items():
        X[key] = value
    with threadpool_limits(limits=1):
        model = HistoryBoost(
            v2_publication_fixture["model"],
            {"max_iter": 3, "min_samples_leaf": 5, "random_state": 42},
        ).fit(X.loc[:, MODEL_COLUMNS], data.train.y)
    model.code_identity = core_identity()
    model.configuration_sha256 = sha256(encode(config()))
    buf = io.BytesIO()
    joblib.dump(model, buf, compress=0)
    metric = {
        "mae": 0.2,
        "rmse": 0.3,
        "r2": 0.1,
        "samples": 10,
        "bias": 0.01,
        "p95_absolute_error": 0.5,
        "actual_worst_absolute_error": 0.7,
    }
    metadata = {
        "schema_version": 1,
        "model": "history_boost",
        "model_version": artifacts.VERSION,
        "model_status": "EXPERIMENTAL_HISTORY_CANDIDATE",
        "experiment_id": "EXP-010",
        "model_sha256": sha256(buf.getvalue()),
        "code": model.code_identity,
        "configuration_sha256": model.configuration_sha256,
        "environment": environment(),
        "feature_columns": list(MODEL_COLUMNS),
        "target": "standard_capacity_attainment",
        "units": config()["units"],
        "input_profile": model.input_profile,
        "integration_passed": True,
        "requires_mature_history": True,
        "minimum_uncensored_history": 2,
        "maximum_history_age_hours": 72,
        "experimental_api_authorized": True,
        "production_serving_authorized": False,
        "capacity_application_authorized": False,
        "promotion_decision": "NO_ML_PROMOTION",
        "training": {"fit_rows": len(X)},
        "comparisons": {
            arm: {n: metric for n in [*NAMES, "history_boost"]}
            for arm in ("baseline", "disruption")
        },
    }
    return metadata, buf.getvalue()


@pytest.fixture
def history_bundle(private_history_model, tmp_path, monkeypatch):
    metadata, binary = private_history_model
    directory = tmp_path / "v3"
    directory.mkdir()
    (directory / "metadata.json").write_bytes(encode(metadata))
    (directory / "history_boost.joblib").write_bytes(binary)
    policy = {**artifacts.trusted_policy()}
    monkeypatch.setattr(artifacts, "ARTIFACT_DIRECTORY", directory)
    monkeypatch.setattr(artifacts, "trusted_policy", lambda: policy)
    monkeypatch.setattr(inference, "trusted_policy", lambda: policy)

    def reseal():
        manifest = {
            "schema_version": 1,
            "model_version": artifacts.VERSION,
            "promotion_decision": "NO_ML_PROMOTION",
            "files": {
                n: sha256((directory / n).read_bytes())
                for n in ("metadata.json", "history_boost.joblib")
            },
        }
        raw = encode(manifest)
        (directory / "manifest.json").write_bytes(raw)
        policy["manifest_sha256"] = sha256(raw)

    reseal()
    return directory, policy, reseal


def test_v3_additive_schema_preserves_old_contracts():
    new = SyntheticPredictionRequestV3.model_validate(body())
    assert len(new.models) == 5 and new.inputs.model_dump() == body()["inputs"]
    for old in (SyntheticPredictionRequest, SyntheticPredictionRequestV2):
        with pytest.raises(ValidationError):
            old.model_validate(body())
    assert (
        SyntheticPredictionRequestV3.model_validate(
            body(history=MatureHistory().model_dump())
        ).history.history_count
        == 0
    )


@pytest.mark.parametrize(
    "patch",
    [
        {"models": ["history_boost", "history_boost"]},
        {"synthetic": False},
        {"schema_version": 2},
        {"fit": True},
        {"artifact_path": "untrusted.joblib"},
        {"history": {**READY, "actual": 1}},
        {"history": {**READY, "uncensored_history_count": 8}},
        {"history": {**READY, "history_count": 1}},
        {"history": {**READY, "history_age_hours": -1}},
        {"history": {**READY, "recent_attainment_mean": float("nan")}},
        {"history": {**READY, "uncensored_history_count": 1}},
        {"history": {**READY, "recent_attainment_std": None}},
        {"history": {"recent_attainment_mean": 0.5}},
        {"history": {"history_age_hours": 2}},
        {"history": {"history_count": True}},
    ],
)
def test_closed_history_and_serving_controls_reject_contradictions(patch):
    with pytest.raises(ValidationError):
        SyntheticPredictionRequestV3.model_validate(body(**patch))


@pytest.mark.parametrize("name", ["manifest.json", "metadata.json", "history_boost.joblib"])
def test_each_tampered_file_rejected_before_unpickling(history_bundle, monkeypatch, name):
    directory, _, _ = history_bundle
    path = directory / name
    path.write_bytes(path.read_bytes() + b" ")
    monkeypatch.setattr(joblib, "load", lambda *a, **k: pytest.fail("Unverified executable"))
    with pytest.raises(ArtifactError):
        artifacts.load_trusted()


@pytest.mark.parametrize(
    "field,value",
    [
        ("environment", {}),
        ("code", {}),
        ("configuration_sha256", "0" * 64),
        ("feature_columns", []),
        ("target", "actual_productivity"),
        ("units", "percent"),
        ("model_status", "APPROVED"),
        ("integration_passed", False),
        ("experimental_api_authorized", False),
        ("production_serving_authorized", True),
        ("capacity_application_authorized", True),
        ("promotion_decision", "PROMOTED"),
        ("requires_mature_history", False),
        ("minimum_uncensored_history", 1),
        ("maximum_history_age_hours", 999),
    ],
)
def test_even_resealed_metadata_must_satisfy_policy(history_bundle, monkeypatch, field, value):
    directory, _, reseal = history_bundle
    path = directory / "metadata.json"
    metadata = json.loads(path.read_bytes())
    metadata[field] = value
    path.write_bytes(encode(metadata))
    reseal()
    monkeypatch.setattr(joblib, "load", lambda *a, **k: pytest.fail("Invalid policy executed"))
    with pytest.raises(ArtifactError):
        artifacts.load_trusted()


def test_closed_publication_and_executable_limits(history_bundle, monkeypatch):
    directory, policy, reseal = history_bundle
    (directory / "extra.json").write_text("{}")
    with pytest.raises(ArtifactError):
        artifacts.verified_bundle()
    (directory / "extra.json").unlink()
    policy["experimental_api_authorized"] = False
    with pytest.raises(ArtifactError):
        artifacts.verified_bundle()
    policy["experimental_api_authorized"] = True
    with (directory / "history_boost.joblib").open("wb") as stream:
        stream.truncate(32 * 1024**2 + 1)
    reseal()
    monkeypatch.setattr(joblib, "load", lambda *a, **k: pytest.fail("Oversize executable"))
    with pytest.raises(ArtifactError):
        artifacts.load_trusted()


def test_verified_buffer_survives_path_replacement(history_bundle, monkeypatch):
    directory, _, _ = history_bundle
    original = joblib.load

    def replace(buffer):
        assert isinstance(buffer, io.BytesIO)
        (directory / "history_boost.joblib").write_bytes(b"untrusted replacement")
        return original(buffer)

    monkeypatch.setattr(joblib, "load", replace)
    metadata, model = artifacts.load_trusted()
    assert isinstance(model, HistoryBoost) and model.input_profile == metadata["input_profile"]


@pytest.mark.parametrize("name", ["manifest.json", "metadata.json", "history_boost.joblib"])
def test_incomplete_publication_never_executes(history_bundle, monkeypatch, name):
    directory, _, _ = history_bundle
    (directory / name).unlink()
    monkeypatch.setattr(joblib, "load", lambda *a, **k: pytest.fail("Incomplete publication"))
    with pytest.raises(ArtifactError):
        artifacts.load_trusted()


@pytest.mark.parametrize("field", ["code_identity", "configuration_sha256", "input_profile"])
def test_loaded_state_must_match_verified_metadata(history_bundle, monkeypatch, field):
    original = joblib.load

    def changed(buffer):
        model = original(buffer)
        setattr(model, field, {})
        return model

    monkeypatch.setattr(joblib, "load", changed)
    with pytest.raises(ArtifactError):
        artifacts.load_trusted()


@pytest.mark.parametrize(
    "history,zero",
    [
        ({}, False),
        ({**READY, "history_age_hours": 73}, False),
        (READY, False),
        (READY, True),
    ],
)
def test_fifth_model_parity_admission_and_matched_evidence(
    history_bundle, private_v2_bundle, publication_fixture, v2_publication_fixture, history, zero
):
    value = body(history=history)
    if zero:
        value["inputs"]["planned_workers"] = 0
    request = SyntheticPredictionRequestV3.model_validate(value)
    metadata, models = load_trusted(
        publication_fixture["receipt"], directory=publication_fixture["directory"]
    )
    legacy = copy.deepcopy(value)
    legacy.update(schema_version=2, models=NAMES)
    legacy.pop("history")
    with threadpool_limits(limits=1):
        before = predict_v2(
            SyntheticPredictionRequestV2.model_validate(legacy),
            metadata,
            models,
            publication_fixture["receipt"],
            v2_publication_fixture["model"],
        )
        result = inference.predict_v3(
            request,
            metadata,
            models,
            publication_fixture["receipt"],
            v2_publication_fixture["model"],
        )
    for actual, expected in zip(result["results"][:4], before["results"], strict=True):
        assert {k: v for k, v in actual.items() if k != "matched_metrics"} == expected
    candidate = result["results"][4]
    should_abstain = not history or history["history_age_hours"] > 72 or zero
    assert (candidate["prediction"] is None) == should_abstain
    assert (candidate["support"]["status"] == "ABSTAIN") == should_abstain
    if not should_abstain:
        assert candidate["support"]["status"] == "REVIEW_REQUIRED"
        assert "HYPOTHETICAL_HISTORY_NOT_SOURCE_VERIFIED" in candidate["support"]["reason_codes"]
    assert len(result["differences"]) == 10
    assert all(set(r["matched_metrics"]) == {"baseline", "disruption"} for r in result["results"])
    assert result["promotion_decision"] == "NO_ML_PROMOTION"
    assert result["capacity_application_authorized"] is False
    assert result["provenance"]["history_candidate"]["fresh_validation"] is False
    assert candidate["descriptive_band"] is None


@pytest.mark.parametrize("selected", [["history_boost"], ["random_forest"]])
def test_v3_candidate_only_and_legacy_only_selections(
    history_bundle, publication_fixture, selected, monkeypatch
):
    metadata, models = load_trusted(
        publication_fixture["receipt"], directory=publication_fixture["directory"]
    )
    if "history_boost" not in selected:
        monkeypatch.setattr(
            inference, "verified_bundle", lambda: pytest.fail("Unselected v3 loaded")
        )
    request = SyntheticPredictionRequestV3.model_validate(body(models=selected))
    with threadpool_limits(limits=1):
        result = inference.predict_v3(
            request, metadata, models, publication_fixture["receipt"], None
        )
    assert [v["model"] for v in result["results"]] == selected
    assert result["results"][0]["prediction"] is not None
    assert result["differences"] == []


def test_publication_cannot_overwrite_existing_bundle(history_bundle):
    with pytest.raises(ValueError, match="CREATE_ONLY"):
        artifacts.publish("0" * 64, "0" * 64)


def test_native_v3_authentication_limits_and_no_training_or_reserved_reads(
    native_app_v2, private_history_model, monkeypatch
):
    import anyio
    import httpx

    import loometric.api.prediction_service as supervisor

    # This test's sitecustomize imports inference to install private trust seams.
    # Set the same production controls before that earlier-than-worker import.
    for variable in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        monkeypatch.setenv(variable, "1")
    child = supervisor.guarded_child
    observations = []

    def observed_child(*args, **kwargs):
        payload, measurements = child(*args, **kwargs)
        observations.append((payload, measurements))
        return payload, measurements

    monkeypatch.setattr(supervisor, "guarded_child", observed_child)

    app, settings, root = native_app_v2
    directory = root / "v3"
    directory.mkdir()
    metadata, model_raw = private_history_model
    (directory / "metadata.json").write_bytes(encode(metadata))
    (directory / "history_boost.joblib").write_bytes(model_raw)
    manifest = {
        "schema_version": 1,
        "model_version": artifacts.VERSION,
        "promotion_decision": "NO_ML_PROMOTION",
        "files": {
            n: sha256((directory / n).read_bytes())
            for n in ("metadata.json", "history_boost.joblib")
        },
    }
    (directory / "manifest.json").write_bytes(encode(manifest))
    policy = {**artifacts.trusted_policy(), "manifest_sha256": sha256(encode(manifest))}
    with (root.parent / "sitecustomize.py").open("a", encoding="utf-8") as stream:
        stream.write(
            "import loometric.final_candidate.artifacts as v3\n"
            f"v3.ARTIFACT_DIRECTORY=pathlib.Path({str(directory)!r})\n"
            f"v3.trusted_policy=lambda: {policy!r}\n"
            "import loometric.final_candidate.inference as v3i\n"
            "v3i.trusted_policy=v3.trusted_policy\n"
            "from loometric.final_candidate.model import HistoryBoost\n"
            "def forbidden_fit(*a,**k): raise AssertionError('Serving fitted a model')\n"
            "HistoryBoost.fit=forbidden_fit\n"
        )

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1234)),
            base_url="http://127.0.0.1:8000",
        ) as client:
            route = "/api/v1/predictions/synthetic/v3"
            assert (await client.post(route, json=body())).status_code == 401
            client.headers["Authorization"] = "Bearer " + settings.token.get_secret_value()
            oversized = await client.post(
                route, content=" " * 8193, headers={"Content-Type": "application/json"}
            )
            assert oversized.status_code == 413
            bad = await client.post(route, json=body(history={**READY, "actual": 1}))
            assert bad.status_code == 422, (bad.text, observations)
            for history in ({}, READY):
                response = await client.post(route, json=body(history=history))
                assert response.status_code == 200, response.text
                result = response.json()["data"]
                assert len(result["results"]) == 5 and result["schema_version"] == 3
                assert (result["results"][4]["prediction"] is None) == (not history)
                assert result["execution"]["memory_limit_mib"] == 768
                assert result["execution"]["deadline_seconds"] == 10
                assert result["promotion_decision"] == "NO_ML_PROMOTION"
                assert response.headers["cache-control"] == "no-store"
            path = directory / "history_boost.joblib"
            path.write_bytes(path.read_bytes() + b"tampering")
            rejected = await client.post(route, json=body())
            assert rejected.status_code == 503
            assert rejected.json()["error"]["code"] == "EXPERIMENTAL_ARTIFACT_UNAVAILABLE"
            legacy = body(schema_version=2, models=NAMES)
            legacy.pop("history")
            assert (
                await client.post("/api/v1/predictions/synthetic/v2", json=legacy)
            ).status_code == 200

    anyio.run(run)
