import pandas as pd
import pytest
from threadpoolctl import threadpool_limits

import loometric.synthetic_ml.storage as storage
from loometric.experimental_ml.constants import MODELS, ROOT, STUDY_CASE
from loometric.experimental_ml.publish import publish_models
from loometric.synthetic_ml.configuration import GenerationConfig
from loometric.synthetic_ml.generation import generate
from loometric.synthetic_training.configuration import load_study
from loometric.synthetic_training.data import load_development
from loometric.synthetic_training.metrics import analyze
from loometric.synthetic_training.models import build_model
from loometric.synthetic_training.risk import band_diagnostics, residual_reference


@pytest.fixture(scope="module")
def publication_fixture(tmp_path_factory):
    root = tmp_path_factory.mktemp("experimental")
    patch = pytest.MonkeyPatch()
    patch.setattr(storage, "OUTPUT_ROOT", root)
    config = GenerationConfig(calendar_days=35, factories=2, styles=3)
    source = root / "source"
    receipt = storage.write_bundle(
        generate(config), config, source, configuration_sha256="a" * 64, profile="private-test"
    )
    # The fixture generator can construct private tests. The publisher's reader
    # must not decode their reserved/gap/global-outcome target values.
    data = load_development(source, expected_fingerprint=receipt["manifest_fingerprint"])
    study = load_study(ROOT / "configs/synthetic_training_v1.json")
    specs = {s["name"]: s for s in study["search"]}
    specs["grouped_mean"] = {"name": "grouped_mean", "family": "naive", "parameters": {}}
    report = {
        "configuration": study,
        "selection": {"status": "NO_ML_PROMOTION"},
        "reserved_label_values_decoded": False,
        "final_test_evaluated": False,
        "datasets": {STUDY_CASE: {"provenance": data.provenance}},
        "validation": {STUDY_CASE: {}},
        "residual_references": {STUDY_CASE: {}},
    }
    rows = []
    with threadpool_limits(limits=1):
        for name in MODELS.values():
            model = build_model(specs[name], 42).fit(data.train.X, data.train.y)
            predicted = pd.Series(model.predict(data.validation.X), index=data.validation.X.index)
            report["validation"][STUDY_CASE][name] = analyze(
                data.validation.y, predicted, data.validation.metadata
            )
            # Private fixture residuals are only mechanical test data; actual
            # production metadata uses retained benchmark training-OOF residuals.
            report["residual_references"][STUDY_CASE][name] = residual_reference(
                [{"stage": "cutting", "actual": 0.4, "prediction": 0.5}]
            )
            report["validation"][STUDY_CASE][name]["risk_band"] = band_diagnostics(
                data.validation.y,
                predicted,
                data.validation.metadata,
                report["residual_references"][STUDY_CASE][name],
            )
            rows.extend(
                {
                    "case": STUDY_CASE,
                    "model": name,
                    "observation_id": oid,
                    "prediction": float(value),
                }
                for oid, value in predicted.items()
            )
    output = root / "models"
    result = publish_models(data, report, rows, output)
    yield {
        "directory": output,
        "receipt": result["manifest_sha256"],
        "result": result,
        "data": data,
        "report": report,
        "rows": rows,
        "root": root,
    }
    patch.undo()


@pytest.fixture
def private_bundle(publication_fixture, tmp_path):
    import shutil

    directory = tmp_path / "models"
    shutil.copytree(publication_fixture["directory"], directory)
    return directory, publication_fixture["receipt"]


@pytest.fixture(scope="module")
def v2_publication_fixture(publication_fixture):
    """Private fitted candidate; no dependency on ignored real research artifacts."""
    import io

    import joblib

    from loometric.experimental_ml.artifacts import canonical, sha256
    from loometric.experimental_ml_v2.constants import MODEL_STATUS, VERSION
    from loometric.ml_research.artifacts import code_identity
    from loometric.ml_research.models import pipeline
    from loometric.synthetic_ml.features import FEATURE_COLUMNS
    from loometric.synthetic_training.artifacts import environment

    fixture = publication_fixture
    spec = next(s for s in fixture["report"]["configuration"]["search"] if s["name"] == "forest-12")
    with threadpool_limits(limits=1):
        model = pipeline(spec, 42, engineered=True).fit(
            fixture["data"].train.X, fixture["data"].train.y
        )
    buffer = io.BytesIO()
    joblib.dump(model, buffer, compress=0)
    model_bytes = buffer.getvalue()
    source_receipt = "b" * 64
    metadata = {
        "schema_version": 1,
        "model_version": VERSION,
        "model": "rf_physics",
        "model_status": MODEL_STATUS,
        "source_experiment": "EXP-008",
        "source_manifest_sha256": source_receipt,
        "source_model_sha256": sha256(model_bytes),
        "dataset_version": "synthetic-ml-v1",
        "target": "standard_capacity_attainment",
        "feature_order": list(FEATURE_COLUMNS),
        "training_partition": "train",
        "environment": environment(),
        "research_code": code_identity(),
        "promotion_decision": "NO_ML_PROMOTION",
        "reserved_labels_decoded": False,
        "capacity_application_authorized": False,
        "experimental_only": True,
        "serving_authorized": False,
    }
    buffers = {"rf_physics.joblib": model_bytes, "metadata.json": canonical(metadata)}
    manifest = {
        "schema_version": 1,
        "model_version": VERSION,
        "model": "rf_physics",
        "promotion_decision": "NO_ML_PROMOTION",
        "capacity_application_authorized": False,
        "reserved_labels_decoded": False,
        "serving_authorized": False,
        "files": {name: sha256(value) for name, value in sorted(buffers.items())},
    }
    directory = fixture["root"] / "v2-models"
    directory.mkdir()
    for name, value in {**buffers, "manifest.json": canonical(manifest)}.items():
        (directory / name).write_bytes(value)
    return {
        "directory": directory,
        "receipt": sha256(canonical(manifest)),
        "model_receipt": sha256(model_bytes),
        "source_receipt": source_receipt,
        "model": model,
    }


@pytest.fixture
def private_v2_bundle(v2_publication_fixture, publication_fixture, tmp_path, monkeypatch):
    import shutil

    from loometric.experimental_ml.artifacts import canonical, sha256
    from loometric.experimental_ml_v2 import artifacts, constants, inference, serving
    from loometric.synthetic_training.risk import support_profile

    fixture = v2_publication_fixture
    directory = tmp_path / "v2"
    shutil.copytree(fixture["directory"], directory)
    monkeypatch.setattr(artifacts, "ARTIFACT_DIRECTORY", directory)
    monkeypatch.setattr(artifacts, "TRUSTED_MANIFEST_SHA256", fixture["receipt"])
    monkeypatch.setattr(artifacts, "SOURCE_MANIFEST_SHA256", fixture["source_receipt"])
    monkeypatch.setattr(artifacts, "SOURCE_MODEL_SHA256", fixture["model_receipt"])
    monkeypatch.setattr(constants, "TRUSTED_MANIFEST_SHA256", fixture["receipt"])
    monkeypatch.setattr(inference, "TRUSTED_MANIFEST_SHA256", fixture["receipt"])
    data = publication_fixture["data"]
    monkeypatch.setattr(inference, "TRAINING_FINGERPRINT", data.provenance["train_fingerprint"])
    monkeypatch.setattr(
        inference,
        "SUPPORT_PROFILE_SHA256",
        sha256(canonical(support_profile(data.train.X, data.train.y))),
    )
    monkeypatch.setattr(
        serving,
        "EXPERIMENTAL_SERVING_RECEIPT",
        {
            **serving.EXPERIMENTAL_SERVING_RECEIPT,
            "manifest_sha256": fixture["receipt"],
        },
    )
    return directory
