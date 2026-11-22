import copy
import json
from dataclasses import replace
from pathlib import Path

import joblib
import pytest

import loometric.synthetic_training.artifacts as artifacts
from loometric.synthetic_ml.storage import digest, encode
from loometric.synthetic_training.artifacts import inspect_artifact, publish
from loometric.synthetic_training.configuration import load_study
from loometric.synthetic_training.data import load_development
from loometric.synthetic_training.study import FitLedger, run_study


@pytest.fixture(scope="module")
def unit_study(request):
    # Source fixture generated here, never an authorized evaluation dataset.
    from tempfile import TemporaryDirectory
    from unittest.mock import patch

    import loometric.synthetic_ml.storage as source_storage
    from loometric.synthetic_ml.configuration import GenerationConfig
    from loometric.synthetic_ml.generation import generate

    temporary = TemporaryDirectory()
    request.addfinalizer(temporary.cleanup)
    base = Path(temporary.name)
    with patch.object(source_storage, "OUTPUT_ROOT", base):
        receipt = source_storage.write_bundle(
            generate(GenerationConfig()),
            GenerationConfig(),
            base / "source",
            configuration_sha256="c" * 64,
            profile="development",
        )
    source = load_development(base / "source", expected_fingerprint=receipt["manifest_fingerprint"])
    config = copy.deepcopy(
        load_study(Path(__file__).resolve().parents[2] / "configs/synthetic_training_v1.json")
    )
    for spec in config["search"]:
        if spec["family"] == "forest":
            spec["parameters"]["n_estimators"] = 3
        if spec["family"] == "hist":
            spec["parameters"]["max_iter"] = 3
    datasets = {
        b["case_id"]: replace(
            source,
            provenance={
                **source.provenance,
                "seed": b["seed"],
                "profile": b["profile"],
                "scenario": b["scenario"],
            },
        )
        for b in config["datasets"]
    }
    seen = []
    original = FitLedger.fit

    def guard(self, spec, seed, population, ids, case, scope):
        assert population is datasets[case].train
        assert set(ids) <= set(datasets[case].train.X.index)
        assert not set(ids) & set(datasets[case].validation.X.index)
        seen.append((case, scope, spec["name"]))
        return original(self, spec, seed, population, ids, case, scope)

    with patch.object(FitLedger, "fit", guard):
        result = run_study(config, datasets)
    assert len(seen) == 132
    return config, datasets, result


def test_full_private_study_reproduces_selection_predictions_and_metrics(unit_study):
    config, data, first = unit_study
    second = run_study(config, data)
    assert first.report == second.report
    assert first.oof_predictions == second.oof_predictions
    assert first.validation_predictions == second.validation_predictions
    assert first.report["model_fits"] == 132
    assert first.excluded_observations
    assert all(row["prediction_attempted"] is False for row in first.excluded_observations)
    assert (
        first.report["final_test_evaluated"]
        is first.report["reserved_label_values_decoded"]
        is False
    )
    assert first.report["stress_models_refitted"] is False
    assert first.measurements["operations"]
    assert all(row["samples"] > 0 for row in first.measurements["operations"])


def test_artifacts_are_create_only_inspected_without_loading(unit_study, tmp_path, monkeypatch):
    _, _, result = unit_study
    monkeypatch.setattr(artifacts, "OUTPUT_ROOT", tmp_path)

    def prohibited(*args, **kwargs):
        raise AssertionError("M08B must not automatically deserialize an executable artifact")

    monkeypatch.setattr(joblib, "load", prohibited)
    first = publish(result, tmp_path / "first")
    second = publish(result, tmp_path / "second")
    assert first == second
    summary = inspect_artifact(
        tmp_path / "first", expected_fingerprint=first["manifest_fingerprint"]
    )
    assert summary["executable_model_loaded"] is summary["serving_authorized"] is False
    files = {p.name: p.read_bytes() for p in (tmp_path / "first").iterdir()}
    with pytest.raises(ValueError):
        publish(result, tmp_path / "first")
    assert files == {p.name: p.read_bytes() for p in (tmp_path / "first").iterdir()}


@pytest.mark.parametrize(
    "kind", ["bytes", "environment", "feature_order", "training_partition", "application"]
)
def test_artifact_tampering_is_rejected(unit_study, tmp_path, monkeypatch, kind):
    monkeypatch.setattr(artifacts, "OUTPUT_ROOT", tmp_path)
    receipt = publish(unit_study[2], tmp_path / "artifact")
    directory = tmp_path / "artifact"
    manifest = json.loads((directory / "manifest.json").read_text())
    expected = receipt["manifest_fingerprint"]
    if kind == "bytes":
        model_file = next(
            name for name in manifest["files"] if name in ("model.json", "pipeline.joblib")
        )
        with (directory / model_file).open("ab") as destination:
            destination.write(b"tampered")
    else:
        if kind == "environment":
            manifest["environment"]["python"] = "unverified"
        elif kind == "feature_order":
            manifest["feature_order"].reverse()
        elif kind == "training_partition":
            manifest["training"]["training_partition"] = "test"
        else:
            manifest["capacity_application_authorized"] = True
        (directory / "manifest.json").write_bytes(encode(manifest))
        expected = digest(manifest)
    with pytest.raises(ValueError):
        inspect_artifact(directory, expected_fingerprint=expected)


def test_cli_inspection_and_existing_output_do_not_refit(unit_study, tmp_path, monkeypatch, capsys):
    import loometric.synthetic_training.cli as cli

    monkeypatch.setattr(artifacts, "OUTPUT_ROOT", tmp_path)
    receipt = publish(unit_study[2], tmp_path / "artifact")
    assert (
        cli.main(
            [
                "inspect",
                "--artifact",
                str(tmp_path / "artifact"),
                "--expected-fingerprint",
                receipt["manifest_fingerprint"],
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["executable_model_loaded"] is False

    def prohibited(*args, **kwargs):
        raise AssertionError("Existing output must fail before loading or fitting")

    monkeypatch.setattr(cli, "load_datasets", prohibited)
    assert cli.main(["run", "--output", str(tmp_path / "artifact")]) == 2
    assert json.loads(capsys.readouterr().err)["status"] == "INVALID_INPUT_OR_STUDY_FAILURE"


def test_artifact_output_cannot_replace_source_or_escape_root(unit_study, tmp_path):
    with pytest.raises(ValueError, match="NEW_IGNORED_TRAINING_OUTPUT_REQUIRED"):
        publish(unit_study[2], tmp_path / "outside")
    assert not (tmp_path / "outside").exists()
