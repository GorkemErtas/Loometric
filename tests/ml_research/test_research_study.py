import copy
from dataclasses import replace
from datetime import timedelta

import numpy as np
import pandas as pd
import pytest
from threadpoolctl import threadpool_limits

import loometric.ml_research.artifacts as artifacts
from loometric.ml_research.artifacts import inspect_research, publish
from loometric.ml_research.protocol import ROOT, load_protocol
from loometric.ml_research.study import run_research
from loometric.synthetic_training.configuration import load_study
from loometric.synthetic_training.data import DevelopmentData, Population
from loometric.synthetic_training.metrics import analyze
from loometric.synthetic_training.models import build_model
from loometric.synthetic_training.risk import residual_reference


@pytest.fixture
def private_inputs(research_population):
    p = research_population
    config = copy.deepcopy(load_protocol())
    config["candidates"] = [
        c for c in config["candidates"] if c["name"] in ("rf_physics", "hist_physics_regularized")
    ]
    for spec in config["candidates"]:
        spec["parameters"]["n_estimators" if spec["family"] == "forest" else "max_iter"] = 3
    config["permutation"].update(repeats=1, max_evaluation_rows=20)
    config["bootstrap"]["repeats"] = 10
    original_config = copy.deepcopy(load_study(ROOT / "configs/synthetic_training_v1.json"))
    for spec in original_config["search"]:
        if spec["family"] == "forest":
            spec["parameters"]["n_estimators"] = 3
        if spec["family"] == "hist":
            spec["parameters"]["max_iter"] = 3
    X, y, metadata = p.X.iloc[:60].copy(), p.y.iloc[:60].copy(), p.metadata.iloc[:60].copy()
    X.index = y.index = metadata.index = pd.Index(
        ["VAL-" + oid for oid in X.index], name="observation_id"
    )
    metadata["start_date"] = metadata.start_date.map(lambda d: d + timedelta(days=42))
    for c in ("cutoff", "label_available_at"):
        metadata[c] += timedelta(days=42)
    validation = Population(X, y, metadata, (), "b" * 64)
    datasets, contexts = {}, {}
    for binding in original_config["datasets"]:
        case = binding["case_id"]
        val = (
            replace(validation, y=validation.y * 0.8)
            if binding["scenario"] == "disruption"
            else validation
        )
        datasets[case] = DevelopmentData(
            p,
            val,
            {key: binding[key] for key in ("seed", "profile", "scenario")},
            {"reserved_labels_decoded": False},
        )
        ctx = pd.concat([p.metadata, val.metadata])
        contexts[case] = pd.DataFrame(
            {
                "factory_id": "PRIVATE-F",
                "line_id": ctx.stage,
                "crew_id": ctx.stage + ctx.shift_kind,
                "style_id": "PRIVATE-S",
            },
            index=ctx.index,
        )
    specs = {s["name"]: s for s in original_config["search"]}
    specs["grouped_mean"] = {"name": "grouped_mean", "family": "naive", "parameters": {}}
    original = {"configuration": original_config, "validation": {}, "residual_references": {}}
    retained = []
    with threadpool_limits(limits=1):
        models = {name: build_model(specs[name], 42).fit(p.X, p.y) for name in config["references"]}
        for case, data in datasets.items():
            original["validation"][case], original["residual_references"][case] = {}, {}
            for name, model in models.items():
                predicted = pd.Series(
                    model.predict(data.validation.X), index=data.validation.X.index
                )
                original["validation"][case][name] = analyze(
                    data.validation.y, predicted, data.validation.metadata
                )
                original["residual_references"][case][name] = residual_reference(
                    [{"stage": "packing", "actual": 0.4, "prediction": 0.5}]
                )
                retained.extend(
                    {
                        "case": case,
                        "model": name,
                        "observation_id": oid,
                        "actual": float(data.validation.y[oid]),
                        "prediction": float(predicted[oid]),
                    }
                    for oid in predicted.index
                )
    return config, datasets, contexts, original, retained


def test_private_full_workflow_seals_selection_and_reproduces(
    private_inputs, tmp_path, monkeypatch
):
    config, data, contexts, original, retained = private_inputs
    events = []
    first = run_research(config, data, contexts, original, retained, progress=events.append)
    second = run_research(config, data, contexts, original, retained)
    assert first.report == second.report
    assert (
        first.historical == second.historical
        and first.importance == second.importance
        and first.ablations == second.ablations
    )
    assert first.oof_predictions == second.oof_predictions
    assert first.diagnostic_predictions == second.diagnostic_predictions
    assert first.report["estimator_fits"] == 152
    sealed = next(
        i for i, e in enumerate(events) if e["stage"] == "selection_sealed_before_outer_diagnostics"
    )
    assert all(
        i > sealed for i, e in enumerate(events) if e["stage"] == "spent_diagnostic_complete"
    )
    assert first.report["selection"]["validation_used_for_selection"] is False
    assert all(
        p["maximum_absolute_difference"] == 0
        for p in first.report["frozen_reference_parity"].values()
    )
    assert (
        first.historical["hidden_shift_pairs"]["development-19-disruption"][
            "identical_feature_vectors"
        ]
        is True
    )
    assert (
        first.historical["hidden_shift_pairs"]["development-19-disruption"][
            "balanced_pair_empirical_mae_lower_bound"
        ]
        > 0
    )
    assert all(row["case"].endswith("-baseline") for row in first.report["fit_provenance"])
    monkeypatch.setattr(artifacts, "OUTPUT_ROOT", tmp_path)
    a, b = publish(first, tmp_path / "first"), publish(second, tmp_path / "second")
    assert a == b
    import joblib

    restored = joblib.load(tmp_path / "first/research-model.joblib")
    with threadpool_limits(limits=1):
        X = data["benchmark-42-baseline"].validation.X
        assert np.array_equal(restored.predict(X), first.artifact_model.predict(X))
    assert all(
        path.read_bytes() == (tmp_path / "second" / path.name).read_bytes()
        for path in (tmp_path / "first").iterdir()
        if path.name != "measurements.json"
    )
    monkeypatch.setattr(
        "joblib.load", lambda *a, **k: pytest.fail("Inspector loaded executable model")
    )
    assert inspect_research(tmp_path / "first", a["manifest_sha256"])["executable_loaded"] is False
    with monkeypatch.context() as changed:
        changed.setattr(artifacts, "code_identity", lambda: {"unexpected.py": "0" * 64})
        with pytest.raises(ValueError, match="PROVENANCE_DRIFT"):
            inspect_research(tmp_path / "first", a["manifest_sha256"])
    (tmp_path / "first/research-model.joblib").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="CONTENT_DRIFT"):
        inspect_research(tmp_path / "first", a["manifest_sha256"])
    with pytest.raises(ValueError, match="NEW_IGNORED_RESEARCH"):
        publish(first, tmp_path / "second")
