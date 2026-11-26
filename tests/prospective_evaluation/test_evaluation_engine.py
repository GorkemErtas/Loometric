"""Private mechanical regression checks; no actual EXP-009 generation, fit or experiment."""

import hashlib
import json
import random
import shutil
from itertools import product

import numpy as np
import pytest

from loometric.prospective_evaluation import (
    acceptance,
    diagnostics,
    evaluation_access,
    evaluation_service,
    evaluator,
    frozen_models,
    receipts,
    storage,
)
from loometric.prospective_evaluation.protocol import load_protocol, verify_frozen_sources
from loometric.synthetic_training.data import NUMERIC

NAMES = [m["name"] for m in load_protocol()["models"]]


class MechanicalPredictor:
    def __init__(self, value=0.8):
        self.value, self.calls = value, 0

    def fit(self, *args, **kwargs):
        raise AssertionError("No estimator fitting is allowed")

    def predict(self, frame):
        self.calls += 1
        assert list(frame) == load_protocol()["contract"]["feature_columns"]
        assert frame.available_minutes.gt(0).all() and frame.planned_workers.gt(0).all()
        return np.full(len(frame), self.value)


@pytest.fixture
def frozen():
    profile = {
        "categories": {
            "stage": [s for s in ("cutting", "sewing", "finishing", "quality_control", "packing")],
            "shift_kind": ["day", "night"],
            "weekday": list("012345"),
        },
        "numeric_bounds": {c: {"minimum": 0, "maximum": 100000} for c in NUMERIC},
        "training_label_minimum": 0,
        "training_label_maximum": 2,
    }
    return frozen_models.FrozenModels(
        {name: MechanicalPredictor(0.8 + i * 0.01) for i, name in enumerate(NAMES)},
        profile,
        {"private_mechanical_models": True},
    )


@pytest.fixture(scope="module")
def registered(prepared, designs, history, tmp_path_factory):
    root = tmp_path_factory.mktemp("private-registered") / "sources"
    shutil.copytree(prepared[0], root)
    result = receipts._register_batch(root, designs, prepared[1], history)
    return root, result["ledger_sha256"]


@pytest.fixture
def eval_bundle(registered, tmp_path):
    root = tmp_path / "private-evaluation"
    shutil.copytree(registered[0], root)
    return root, registered[1]


@pytest.fixture(scope="module")
def completed(registered, designs, history, tmp_path_factory):
    # Invoke the same private fixture constructor without requesting actual frozen bundles.
    profile = {
        "categories": {
            "stage": [s.value for s in diagnostics.Stage],
            "shift_kind": ["day", "night"],
            "weekday": list("012345"),
        },
        "numeric_bounds": {c: {"minimum": 0, "maximum": 100000} for c in NUMERIC},
        "training_label_minimum": 0,
        "training_label_maximum": 2,
    }
    root = tmp_path_factory.mktemp("private-complete") / "sources"
    shutil.copytree(registered[0], root)

    def loader():
        return frozen_models.FrozenModels(
            {name: MechanicalPredictor(0.8 + i * 0.01) for i, name in enumerate(NAMES)},
            profile,
            {"private_mechanical_models": True},
        )

    a = evaluator._evaluate(root, designs, history, registered[1], loader)
    b = evaluator._evaluate(
        root, designs, history, registered[1], loader, run="b", expected_a=a["manifest_sha256"]
    )
    return root, registered[1], a, b


def test_private_complete_run_is_sealed_reproduced_and_never_promoted(completed):
    root, ledger, a, b = completed
    assert a["decision"] == "PENDING_REPRODUCTION"
    verified = evaluator.verify_reproduction(
        root, a["manifest_sha256"], b["manifest_sha256"], ledger
    )
    assert verified == {
        "status": "REPRODUCTION_VERIFIED",
        "decision": "INCONCLUSIVE",
        "promotion_decision": "NO_ML_PROMOTION",
    }
    report = json.loads((root / "runs/a/report.json").read_bytes())
    assert report["resource_counts"]["calls"] == 32
    assert report["resource_counts"]["predictions"] <= 1600
    assert report["validity"]["fits"] == 0
    assert len(report["diagnostics"]) == 8
    assert report["comparisons"]["primary"]["ordered_resamples"] == 256
    assert len(report["comparisons"]["model_pairs"]["baseline"]) == 6
    assert len(report["comparisons"]["condition_world_bootstrap"]) == 4
    assert all(
        v["repeats"] == 500 and v["used_for_acceptance"] is False
        for v in report["date_sensitivity"].values()
    )
    assert all(set(d["models"]) == set(NAMES) for d in report["diagnostics"].values())
    errors = [json.loads(line) for line in (root / "runs/a/errors.jsonl").read_text().splitlines()]
    assert len(errors) == 400 and all(set(e["signed_errors"]) == set(NAMES) for e in errors)
    verify_frozen_sources(load_protocol())
    assert not storage.output_root().exists()


def test_all_cases_predict_and_disk_seal_precede_first_label(
    eval_bundle, designs, history, frozen, monkeypatch
):
    root, ledger = eval_bundle
    original = evaluator.read_validation_labels
    reads = []

    def checked(root, design, source, seal_check, **kwargs):
        assert sum(m.calls for m in frozen.models.values()) == 32
        sealed = seal_check()
        assert len(sealed) == 400 and len({r["case_id"] for r in sealed}) == 8
        assert all("actual" not in r for r in sealed)
        reads.append(design.case.case_id)
        return original(root, design, source, seal_check, **kwargs)

    monkeypatch.setattr(evaluator, "read_validation_labels", checked)
    evaluator._evaluate(root, designs, history, ledger, lambda: frozen)
    assert len(reads) == 8


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_prediction_aborts_without_labels_or_completion(
    eval_bundle, designs, history, frozen, monkeypatch, value
):
    root, ledger = eval_bundle
    frozen.models["rf_physics"].value = value
    monkeypatch.setattr(
        evaluator, "read_validation_labels", lambda *a: pytest.fail("Early label read")
    )
    with pytest.raises(ValueError, match="NONFINITE"):
        evaluator._evaluate(root, designs, history, ledger, lambda: frozen)
    assert (root / "runs/a/attempt.json").exists()
    assert not (root / "runs/a/manifest.json").exists()
    assert not (root / "runs/a/predictions.receipt.json").exists()


def test_pair_drift_fails_before_labels(eval_bundle, designs, history, frozen, monkeypatch):
    root, ledger = eval_bundle
    model = frozen.models["rf_physics"]

    def unstable(frame):
        model.calls += 1
        return np.full(len(frame), model.calls)

    monkeypatch.setattr(model, "predict", unstable)
    monkeypatch.setattr(
        evaluator, "read_validation_labels", lambda *a: pytest.fail("Early label read")
    )
    with pytest.raises(ValueError, match="PAIRED_FROZEN_PREDICTION_DRIFT"):
        evaluator._evaluate(root, designs, history, ledger, lambda: frozen)


def test_bad_independent_ledger_fails_before_models_or_labels(eval_bundle, designs, history):
    root, _ = eval_bundle
    with pytest.raises(ValueError, match="LEDGER_RECEIPT_DRIFT"):
        evaluator._evaluate(
            root,
            designs,
            history,
            "0" * 64,
            lambda: pytest.fail("Model loaded before verification"),
        )


@pytest.mark.parametrize("name", ["predictions.jsonl", "predictions.receipt.json"])
def test_broken_seal_prevents_validation_decode(completed, designs, tmp_path, name):
    root = tmp_path / "broken-seal"
    shutil.copytree(completed[0], root)
    receipt_path = root / "runs/a/predictions.receipt.json"
    raw = receipt_path.read_bytes()
    seal = json.loads(raw)
    path = root / f"runs/a/{name}"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="DRIFT"):
        evaluation_access.read_validation_labels(
            root,
            designs[0],
            None,
            lambda: evaluation_access.verify_seal(root, "runs/a", storage.sha256(raw), seal),
            expected_manifest_sha="0" * 64,
        )


@pytest.mark.parametrize(
    "mutation", ["ids", "status", "denominator", "time", "target", "earned", "extra"]
)
def test_strict_label_semantics_reject_rehashed_tampering(eval_bundle, designs, mutation):
    root, _ = eval_bundle
    design = designs[0]
    directory = root / f"datasets/{design.case.case_id}"
    path = directory / "labels.validation.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    label = rows[0]
    if mutation == "ids":
        label["observation_id"] = "reserved-train-id"
    elif mutation == "status":
        label["status"] = "ZERO_PLANNED_CAPACITY"
    elif mutation == "denominator":
        label["planned_available_worker_minutes"] += 1
    elif mutation == "time":
        label["available_at"] = "2030-01-01T00:00:00+00:00"
    elif mutation == "target":
        label["standard_capacity_attainment"] = "99"
    elif mutation == "earned":
        label["earned_standard_worker_minutes"] = "-1"
    else:
        label["extra"] = "outcome"
    content = b"".join(storage.encode(r) for r in rows)
    path.write_bytes(content)
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["files"][path.name] = storage.identity(content)
    manifest_path.write_bytes(storage.encode(manifest))
    with pytest.raises(ValueError):
        evaluation_access.read_validation_labels(
            root,
            design,
            evaluator.expected_source(design.configuration),
            lambda: [],
            expected_manifest_sha=storage.sha256(manifest_path.read_bytes()),
        )


@pytest.mark.parametrize("run", ["a", "b", "c", "../escape"])
def test_no_retries_or_third_runs(completed, run):
    root, _, a, _ = completed
    with pytest.raises(ValueError):
        evaluator._admit_run(root, run, a["manifest_sha256"] if run == "b" else None)


def test_reproduction_changed_predictions_fail_before_labels(
    completed, designs, history, frozen, tmp_path, monkeypatch
):
    root = tmp_path / "reproduction-drift"
    shutil.copytree(completed[0], root, ignore=shutil.ignore_patterns("b"))
    for model in frozen.models.values():
        model.value = 0.99
    monkeypatch.setattr(
        evaluator, "read_validation_labels", lambda *a: pytest.fail("Drift before label access")
    )
    with pytest.raises(ValueError, match="REPRODUCTION_PREDICTION_DRIFT_BEFORE_LABELS"):
        evaluator._evaluate(
            root,
            designs,
            history,
            completed[1],
            lambda: frozen,
            run="b",
            expected_a=completed[2]["manifest_sha256"],
        )
    assert not (root / "runs/b/manifest.json").exists()


@pytest.mark.parametrize(
    "name", ["errors.jsonl", "report.json", "attempt.json", "manifest.json", "unexpected.txt"]
)
def test_independent_reproduction_inspection_rejects_tampering(completed, tmp_path, name):
    root = tmp_path / "tampered-reproduction"
    shutil.copytree(completed[0], root)
    with (root / f"runs/b/{name}").open("ab") as stream:
        stream.write(b" ")
    with pytest.raises(ValueError):
        evaluator.verify_reproduction(
            root, completed[2]["manifest_sha256"], completed[3]["manifest_sha256"], completed[1]
        )


def test_metrics_exact_definition_empty_constant_and_positive_tail():
    rows = [{"actual": y, "predictions": {"m": p}} for y, p in [(0.0, 1.0), (2.0, 0.0), (4.0, 4.0)]]
    result = diagnostics.metrics(rows, "m")
    assert result["mae"] == 1 and result["rmse"] == pytest.approx(np.sqrt(5 / 3))
    assert result["r2"] == 0.375 and result["bias"] == pytest.approx(-1 / 3)
    assert result["p95_positive_error"] == pytest.approx(0.9)
    assert result["p95_absolute_error"] == pytest.approx(1.9)
    assert result["worst_absolute_error"] == 2
    assert diagnostics.metrics([], "m") == {"rows": 0, **dict.fromkeys(diagnostics.METRICS)}
    assert diagnostics.metrics([rows[0]], "m")["r2"] is None
    assert diagnostics.metrics([rows[0], rows[0]], "m")["r2"] is None


def test_world_bootstrap_enumerates_exact_ordered_blocks():
    values = [-1.0, 0.0, 2.0, 5.0]
    expected = [sum(values[i] for i in draw) / 4 for draw in product(range(4), repeat=4)]
    result = diagnostics.bootstrap_interval(values)
    assert result["ordered_resamples"] == 256
    assert result["interval"] == [
        float(np.quantile(expected, 0.025)),
        float(np.quantile(expected, 0.975)),
    ]
    assert result["resamples_sha256"] == storage.sha256(storage.encode(expected))
    with pytest.raises(ValueError, match="FOUR_WORLD"):
        diagnostics.bootstrap_interval(values[:3])


def test_date_blocks_use_declared_rng_and_matched_whole_dates(designs):
    cases = {}
    world = designs[0].case.world_id
    for design in designs:
        rows = []
        for date, count, left, right in (("2032-03-11", 1, 0.1, 0.4), ("2032-03-12", 3, 0.6, 0.5)):
            rows.extend(
                {
                    "date": date,
                    "actual": 0.0,
                    "predictions": {
                        "grouped_mean": 0.7,
                        "random_forest": right,
                        "histogram_gradient_boosting": 0.3,
                        "rf_physics": left,
                    },
                }
                for _ in range(count)
            )
        cases[design.case.case_id] = rows
    result = diagnostics.date_sensitivity(cases, designs, NAMES, load_protocol())[world]
    dates = ["2032-03-11", "2032-03-12"]
    draws, differences = [], []
    for replicate in range(500):
        key = f"EXP-009|date-bootstrap-v1|20261126|{world}|{replicate}"
        rng = random.Random(int.from_bytes(hashlib.sha256(key.encode()).digest(), "big"))
        draw = [rng.choice(dates) for _ in dates]
        draws.append(draw)
        n1, n2 = draw.count(dates[0]), draw.count(dates[1]) * 3
        a = (n1 * 0.1 + n2 * 0.6) / (n1 + n2)
        b = (n1 * 0.4 + n2 * 0.5) / (n1 + n2)
        differences.append(b - a)
    assert result["draws_sha256"] == storage.sha256(storage.encode(draws))
    interval = result["contrasts"]["baseline|random_forest_minus_rf_physics"]["interval"]
    assert interval == pytest.approx(
        [np.quantile(differences, 0.025), np.quantile(differences, 0.975)]
    )
    assert result["used_for_acceptance"] is False


def test_finite_out_of_policy_values_stay_in_raw_metrics_and_zero_capacity_is_excluded(
    designs, frozen
):
    rows = evaluator.feature_observations(
        designs[0], evaluator.expected_source(designs[0].configuration)
    )
    rows = rows[:3]
    rows[0]["defined_target"] = False
    rows[0]["inputs"]["planned_workers"] = 0
    rows[0]["offered_ceiling"] = None
    frozen.models["rf_physics"].value = 4.0
    frozen.models["random_forest"].value = -1.0
    counter = {"calls": 0, "predictions": 0}
    evaluator._infer_case(rows, frozen, counter, load_protocol()["budget"])
    assert counter == {"calls": 4, "predictions": 8}
    assert all(v is None for v in rows[0]["predictions"].values())
    for row in rows:
        row["actual"] = 0.5 if row["defined_target"] else None
    report = diagnostics.case_diagnostics(rows, NAMES, load_protocol())
    candidate = report["models"]["rf_physics"]
    assert candidate["metrics"]["rows"] == 2 and candidate["metrics"]["mae"] == 3.5
    assert candidate["raw_output"]["above_three"] == 2
    assert candidate["support"]["all_planned"]["input_abstentions"] == 1
    assert candidate["support"]["all_planned"]["output_added_abstentions"] == 2
    assert candidate["support"]["defined_targets"]["abstention_rate"] == 1
    assert report["common_nonabstained_secondary"]["ids"] == []
    assert len(candidate["subgroups"]["stage"]) == 5
    assert (
        candidate["subgroups"]["workload_band"]["undefined_zero_capacity"]["planned_counts"]["rows"]
        == 1
    )
    assert sum(m.calls for m in frozen.models.values()) == 4


@pytest.mark.parametrize(
    "candidate,reference,percent,gain,passed,change",
    [
        (0, 0, 5, False, True, None),
        (1, 0, 5, False, False, None),
        (0, 0, 5, True, False, None),
        (95, 100, 5, True, True, 5),
        (105, 100, 5, False, True, 5),
        (105.01, 100, 5, False, False, 5.01),
        (None, 100, 5, False, False, None),
    ],
)
def test_zero_reference_and_acceptance_boundaries(
    candidate, reference, percent, gain, passed, change
):
    result = acceptance.relative_check(candidate, reference, percent, gain=gain)
    assert result["passed"] is passed
    assert (
        result["percent"] == pytest.approx(change)
        if change is not None
        else result["percent"] is None
    )


def test_service_default_denies_execution_and_uses_one_whole_run_budget(monkeypatch):
    with pytest.raises(ValueError, match="SEPARATE_PROSPECTIVE"):
        evaluation_service.evaluate_frozen_models("0" * 64)
    calls = []

    def supervised(raw, memory, timeout, **kwargs):
        calls.append((json.loads(raw), memory, timeout, kwargs))
        return {"status": "PRIVATE_MECHANICAL_SPY"}, {"peak_committed_bytes": 1}

    monkeypatch.setattr(evaluation_service, "guarded_child", supervised)
    evaluation_service.evaluate_frozen_models("0" * 64, evaluation_authorized=True)
    assert len(calls) == 1 and calls[0][1:3] == (2048, 1200)
    assert calls[0][3]["worker_module"] == "loometric.prospective_evaluation.evaluation_worker"
    assert calls[0][0]["run"] == "a"


@pytest.mark.parametrize(
    "payload,measurement",
    [
        (None, {"status": "TERMINATED_RESOURCE_LIMIT"}),
        ({"error": {"code": "MEMORYERROR"}}, {}),
    ],
)
def test_resource_failure_cannot_be_successful_evaluation(monkeypatch, payload, measurement):
    monkeypatch.setattr(evaluation_service, "guarded_child", lambda *a, **k: (payload, measurement))
    with pytest.raises(ValueError, match="INVALID_EVALUATION"):
        evaluation_service.evaluate_frozen_models("0" * 64, evaluation_authorized=True)
