"""Synthetic artifact/inference acceptance cases; outer outcomes never enter training."""

import hashlib
import json
from datetime import datetime

import joblib
import pandas as pd
import pytest
from sklearn.pipeline import Pipeline

from loometric.baselines import DepartmentMeanBaseline
from loometric.data.loading import read_csv
from loometric.data.profiling import fingerprint
from loometric.data.splitting import make_split_config, save_split_config
from loometric.prediction import artifacts
from loometric.prediction.artifacts import (
    ArtifactError,
    digest,
    generate_artifact,
    load_artifact,
    load_training_partition,
)
from loometric.prediction.cli import main
from loometric.prediction.contracts import PredictionRequest
from loometric.prediction.inference import predict
from loometric.prediction.policy import ReviewPolicy


@pytest.fixture
def split_file(tmp_path, chronological_csv, chronological_data):
    path = tmp_path / "split.json"
    save_split_config(make_split_config(chronological_data, fingerprint(chronological_csv)), path)
    return path


@pytest.fixture
def artifact_files(tmp_path, chronological_csv, split_file):
    directory = tmp_path / "artifact"
    result = generate_artifact(chronological_csv, split_file, directory)
    return directory, result


@pytest.fixture
def prediction_request():
    return PredictionRequest.from_dict(
        {
            "input_schema_version": 1,
            "scheduled_date": "2030-01-03",
            "department": "sewing",
            "team": "1",
            "source_id": "synthetic:workflow-test",
            "prediction_cutoff": "2030-01-03T07:00:00+03:00",
            "source_snapshot_timestamp": "2030-01-03T06:30:00+03:00",
        }
    )


def loaded(artifact_files):
    directory, result = artifact_files
    return load_artifact(directory, expected_fingerprint=result["artifact_fingerprint"])


def test_artifact_roundtrip_and_baseline(artifact_files, chronological_data, prediction_request):
    artifact = loaded(artifact_files)
    result = predict(prediction_request, artifact, now=prediction_request.prediction_cutoff)
    expected = DepartmentMeanBaseline.fit(
        chronological_data.iloc[:12]["department"],
        chronological_data.iloc[:12]["actual_productivity"],
    )
    assert result.baseline_prediction == expected.department_means["sewing"]
    assert result.predicted_productivity is not None
    assert result.status == "REVIEW_REQUIRED"
    assert result.experimental and result.human_review_required
    assert result.decision_eligibility == "NOT_ELIGIBLE_FOR_AUTOMATED_DECISIONS"
    assert artifact.manifest["lineage"]["training"]["rows"] == 12
    config = artifact.manifest["configuration"]
    assert config["features"] == ["department", "team", "day_of_week", "day_of_month"]
    assert {
        key: config["regression"][key]
        for key in ("n_estimators", "max_depth", "min_samples_leaf", "random_state", "n_jobs")
    } == dict(n_estimators=100, max_depth=3, min_samples_leaf=20, random_state=42, n_jobs=1)


def test_reproducible_artifact_bytes_and_inference(
    artifact_files, tmp_path, chronological_csv, split_file, prediction_request
):
    directory, result = artifact_files
    second = tmp_path / "second-artifact"
    repeated = generate_artifact(chronological_csv, split_file, second)
    assert repeated["artifact_fingerprint"] == result["artifact_fingerprint"]
    for name in ("manifest.json", "pipeline.joblib"):
        assert (directory / name).read_bytes() == (second / name).read_bytes()
    first_prediction = predict(
        prediction_request, loaded(artifact_files), now=prediction_request.prediction_cutoff
    )
    assert first_prediction == predict(
        prediction_request, loaded(artifact_files), now=prediction_request.prediction_cutoff
    )


def test_training_only_selection_and_preprocessing(
    chronological_csv, split_file, monkeypatch, tmp_path
):
    captured = []
    original_fit = Pipeline.fit

    def spy(self, features, targets, **kwargs):
        captured.append((features.copy(), targets.copy()))
        return original_fit(self, features, targets, **kwargs)

    monkeypatch.setattr(Pipeline, "fit", spy)
    result = generate_artifact(chronological_csv, split_file, tmp_path / "model")
    features, labels = captured[0]
    assert len(captured) == 1 and len(labels) == len(features) == 12
    assert labels.max() < 0.7
    assert features["day_of_month"].max() == 6
    assert "2" not in result["manifest"]["training_categories"]["day_of_week"]


def test_outer_targets_and_features_not_interpreted(
    chronological_csv, chronological_data, tmp_path, monkeypatch
):
    raw = read_csv(chronological_csv)
    raw.loc[12:, "actual_productivity"] = "OUTER TARGET MUST NEVER BE PARSED"
    raw.loc[12:, "team"] = "OUTER FEATURE MUST NEVER BE PARSED"
    raw.to_csv(chronological_csv, index=False)
    path = tmp_path / "synthetic-frozen-split.json"
    save_split_config(make_split_config(chronological_data, fingerprint(chronological_csv)), path)
    original_validate = artifacts.validate_data
    seen = []

    def spy(raw, clean):
        seen.append(len(raw))
        assert len(raw) == 12
        return original_validate(raw, clean)

    monkeypatch.setattr(artifacts, "validate_data", spy)
    training, lineage = load_training_partition(chronological_csv, path)
    assert len(training) == lineage["training"]["rows"] == 12
    assert seen == [12]


def test_frozen_split_and_source_unchanged(chronological_csv, split_file, tmp_path):
    before = fingerprint(chronological_csv), fingerprint(split_file)
    generate_artifact(chronological_csv, split_file, tmp_path / "model")
    assert before == (fingerprint(chronological_csv), fingerprint(split_file))
    payload = json.loads(split_file.read_text())
    payload["train"]["end"] = "2015-01-05"
    split_file.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="Split configuration differs"):
        load_training_partition(chronological_csv, split_file)


def test_source_fingerprint_drift(chronological_csv, split_file):
    with chronological_csv.open("a") as stream:
        stream.write("\n")
    with pytest.raises(ValueError, match="fingerprint differs"):
        load_training_partition(chronological_csv, split_file)


def test_training_validation_preserved(chronological_csv, chronological_data, tmp_path):
    raw = read_csv(chronological_csv)
    raw.loc[0, "actual_productivity"] = "BAD TRAINING LABEL"
    raw.to_csv(chronological_csv, index=False)
    split = tmp_path / "split.json"
    save_split_config(make_split_config(chronological_data, fingerprint(chronological_csv)), split)
    with pytest.raises(ValueError, match="Training data validation failed"):
        load_training_partition(chronological_csv, split)


def test_no_implicit_training_or_data_read(artifact_files, prediction_request, monkeypatch):
    artifact = loaded(artifact_files)

    def forbidden(*args, **kwargs):
        pytest.fail("Inference attempted training or source loading")

    monkeypatch.setattr(Pipeline, "fit", forbidden)
    monkeypatch.setattr(DepartmentMeanBaseline, "fit", forbidden)
    monkeypatch.setattr(artifacts, "generate_artifact", forbidden)
    monkeypatch.setattr(artifacts, "read_csv", forbidden)
    assert (
        predict(
            prediction_request, artifact, now=prediction_request.prediction_cutoff
        ).predicted_productivity
        is not None
    )


@pytest.mark.parametrize("action,expected", [("review", "REVIEW_REQUIRED"), ("abstain", "ABSTAIN")])
def test_unknown_team_is_explicit(artifact_files, prediction_request, action, expected):
    from dataclasses import replace

    result = predict(
        replace(prediction_request, team="999"),
        loaded(artifact_files),
        now=prediction_request.prediction_cutoff,
        policy=ReviewPolicy(unknown_team_action=action),
    )
    assert result.status == expected
    assert "UNKNOWN_TEAM" in {item.code for item in result.validation_warnings}
    assert result.human_review_required
    if expected == "ABSTAIN":
        assert result.predicted_productivity is result.baseline_prediction is None


def test_missing_artifact_and_historical_request_abstain(artifact_files, prediction_request):
    from dataclasses import replace

    assert (
        predict(prediction_request, None, now=prediction_request.prediction_cutoff).status
        == "ABSTAIN"
    )
    historical = replace(
        prediction_request,
        scheduled_date=pd.Timestamp("2015-01-02").date(),
        prediction_cutoff=datetime.fromisoformat("2015-01-02T07:00:00+03:00"),
        source_snapshot_timestamp=datetime.fromisoformat("2015-01-02T06:00:00+03:00"),
    )
    result = predict(historical, loaded(artifact_files), now=historical.prediction_cutoff)
    assert result.status == "ABSTAIN"
    assert "MODEL_TEMPORAL_OVERLAP" in {item.code for item in result.validation_warnings}


def test_valid_experimental_never_authorizes_decisions(artifact_files, prediction_request):
    policy = ReviewPolicy(
        source_id=prediction_request.source_id,
        timing_evidence_reference="test-only:timing",
        maximum_snapshot_age_seconds=3600,
        freshness_evidence_reference="test-only:freshness",
    )
    artifact = loaded(artifact_files)
    result = predict(
        prediction_request, artifact, now=prediction_request.prediction_cutoff, policy=policy
    )
    assert result.status == "VALID_EXPERIMENTAL"
    assert result.human_review_required and result.experimental
    assert result.decision_eligibility == "NOT_ELIGIBLE_FOR_AUTOMATED_DECISIONS"
    replay = predict(
        prediction_request,
        artifact,
        now=prediction_request.prediction_cutoff,
        policy=policy,
        replay_at=prediction_request.prediction_cutoff,
    )
    assert replay.status == "REVIEW_REQUIRED"
    assert replay.execution_mode == "OFFLINE_REPLAY"


@pytest.mark.parametrize(
    "mode,code",
    [
        ("fingerprint", "ARTIFACT_FINGERPRINT_MISMATCH"),
        ("bytes", "ARTIFACT_INTEGRITY_MISMATCH"),
        ("schema", "ARTIFACT_SCHEMA_MISMATCH"),
        ("configuration", "MODEL_CONFIGURATION_MISMATCH"),
        ("environment", "ARTIFACT_ENVIRONMENT_MISMATCH"),
        ("lineage", "TRAINING_FINGERPRINT_MISMATCH"),
    ],
)
def test_checks_precede_deserialization(artifact_files, monkeypatch, mode, code):
    directory, result = artifact_files
    manifest = json.loads((directory / "manifest.json").read_text())
    if mode == "schema":
        manifest["artifact_schema_version"] = 2
    elif mode == "configuration":
        manifest["configuration"]["regression"]["max_depth"] = 4
    elif mode == "environment":
        manifest["environment"]["scikit-learn"] = "incompatible"
    elif mode == "lineage":
        manifest["lineage"]["training"]["rows"] += 1
    elif mode == "bytes":
        with (directory / "pipeline.joblib").open("ab") as stream:
            stream.write(b"drift")
    (directory / "manifest.json").write_text(json.dumps(manifest))
    expected = "wrong" if mode == "fingerprint" else digest(manifest)

    def forbidden(*args, **kwargs):
        pytest.fail("Deserialization occurred before integrity/schema validation")

    monkeypatch.setattr(joblib, "load", forbidden)
    with pytest.raises(ArtifactError) as caught:
        load_artifact(directory, expected_fingerprint=expected)
    assert caught.value.code == code


def test_serialized_configuration_checked(artifact_files):
    directory, result = artifact_files
    pipeline = joblib.load(directory / "pipeline.joblib")
    pipeline.named_steps["regression"].max_depth = 4
    joblib.dump(pipeline, directory / "pipeline.joblib")
    manifest = json.loads((directory / "manifest.json").read_text())
    manifest["pipeline_sha256"] = hashlib.sha256(
        (directory / "pipeline.joblib").read_bytes()
    ).hexdigest()
    (directory / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ArtifactError, match="parameters differ"):
        load_artifact(directory, expected_fingerprint=digest(manifest))


def test_artifact_refuses_overwrite_and_handles_missing(
    artifact_files, chronological_csv, split_file, tmp_path
):
    directory, _ = artifact_files
    before = fingerprint(directory / "manifest.json")
    with pytest.raises(FileExistsError):
        generate_artifact(chronological_csv, split_file, directory)
    assert before == fingerprint(directory / "manifest.json")
    with pytest.raises(ArtifactError) as caught:
        load_artifact(tmp_path / "missing", expected_fingerprint="x")
    assert caught.value.code == "ARTIFACT_MISSING"


def test_cli_predict_and_structured_abstention(
    artifact_files, prediction_request, tmp_path, capsys
):
    directory, result = artifact_files
    payload = {"input_schema_version": 1, **prediction_request.provenance()}
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(payload))
    arguments = [
        "predict",
        "--artifact",
        str(directory),
        "--expected-fingerprint",
        result["artifact_fingerprint"],
        "--request",
        str(request_path),
        "--at",
        prediction_request.prediction_cutoff.isoformat(),
    ]
    assert main(arguments) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "REVIEW_REQUIRED" and output["execution_mode"] == "OFFLINE_REPLAY"
    payload["department"] = "invalid"
    request_path.write_text(json.dumps(payload))
    assert main(arguments) == 2
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "ABSTAIN" and output["predicted_productivity"] is None
    assert "INVALID_DEPARTMENT" in {item["code"] for item in output["validation_warnings"]}


def test_cli_train_is_explicit_and_refuses_overwrite(
    chronological_csv, split_file, tmp_path, capsys
):
    arguments = [
        "train",
        "--dataset",
        str(chronological_csv),
        "--split",
        str(split_file),
        "--artifact",
        str(tmp_path / "model"),
    ]
    assert main(arguments) == 0
    assert json.loads(capsys.readouterr().out)["lineage"]["training"]["rows"] == 12
    assert main(arguments) == 2
    assert json.loads(capsys.readouterr().out)["error"] == "ARTIFACT_GENERATION_FAILED"


@pytest.mark.parametrize("value,expected", [(1.2, "REVIEW_REQUIRED"), (float("nan"), "ABSTAIN")])
def test_prediction_range_is_reported_without_clipping(
    artifact_files, prediction_request, monkeypatch, value, expected
):
    artifact = loaded(artifact_files)
    monkeypatch.setattr(artifact.pipeline, "predict", lambda _: [value])
    result = predict(prediction_request, artifact, now=prediction_request.prediction_cutoff)
    assert result.status == expected
    if expected == "REVIEW_REQUIRED":
        assert result.predicted_productivity == 1.2
        assert "PREDICTION_ABOVE_ONE" in {item.code for item in result.validation_warnings}
    else:
        assert result.predicted_productivity is result.baseline_prediction is None


def test_cli_missing_artifact_abstains(prediction_request, tmp_path, capsys):
    path = tmp_path / "request.json"
    path.write_text(json.dumps({"input_schema_version": 1, **prediction_request.provenance()}))
    assert (
        main(
            [
                "predict",
                "--artifact",
                str(tmp_path / "missing"),
                "--expected-fingerprint",
                "x",
                "--request",
                str(path),
                "--at",
                prediction_request.prediction_cutoff.isoformat(),
            ]
        )
        == 2
    )
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "ABSTAIN"
    assert "ARTIFACT_MISSING" in {item["code"] for item in result["validation_warnings"]}


def test_cli_invalid_text_encoding_abstains(tmp_path, capsys):
    path = tmp_path / "request.json"
    path.write_bytes(b"\xff")
    assert (
        main(
            [
                "predict",
                "--artifact",
                str(tmp_path / "missing"),
                "--expected-fingerprint",
                "x",
                "--request",
                str(path),
            ]
        )
        == 2
    )
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "ABSTAIN"
    assert result["predicted_productivity"] is None


@pytest.mark.parametrize("mode", ["stale", "source_mismatch"])
def test_policy_abstention_prevents_model_execution(
    artifact_files, prediction_request, monkeypatch, mode
):
    artifact = loaded(artifact_files)

    def forbidden(*args, **kwargs):
        pytest.fail("Model ran despite a blocking provenance policy")

    monkeypatch.setattr(artifact.pipeline, "predict", forbidden)
    policy = ReviewPolicy(
        source_id="other" if mode == "source_mismatch" else prediction_request.source_id,
        maximum_snapshot_age_seconds=1,
        freshness_evidence_reference="test-only:synthetic-acceptance",
    )
    result = predict(
        prediction_request, artifact, now=prediction_request.prediction_cutoff, policy=policy
    )
    assert result.status == "ABSTAIN"
    assert result.predicted_productivity is result.baseline_prediction is None
