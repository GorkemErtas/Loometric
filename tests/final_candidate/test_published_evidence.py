"""Published aggregates stay bound to the pre-holdout receipt; no actual labels/models loaded."""

import hashlib
import json
from itertools import combinations
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def read(name):
    return json.loads((ROOT / "docs/experiments" / name).read_bytes())


def test_independent_receipt_report_and_all_guards_are_consistent():
    receipt = read("EXP-010-candidate-receipt.json")["receipt"]
    execution = read("EXP-010-execution.json")
    path = ROOT / "docs/experiments/EXP-010-results.json"
    report = json.loads(path.read_bytes())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == execution["report_sha256"]
    assert report["candidate_sha256"] == receipt["model_sha256"]
    assert receipt["estimator_fits"] == 1 and receipt["fit_rows"] == 5700
    assert set(receipt["fit_seeds"]).isdisjoint({2503, 2609, 2707, 2801})
    assert len(report["cases"]) == 8 and len(report["integration"]["guards"]) == 41
    assert all(v["passed"] for v in report["integration"]["guards"].values())
    assert report["promotion_decision"] == "NO_ML_PROMOTION"
    assert report["integration"]["promotion_decision"] == "NO_ML_PROMOTION"
    assert report["prediction_sha256"] == execution["prediction_sha256"]
    for arm in ("baseline", "disruption"):
        cases = [v for k, v in report["cases"].items() if k.endswith(arm)]
        assert sum(v["defined_targets"] for v in cases) == 1426
        for name, metrics in report["macro"][arm].items():
            for key, value in metrics.items():
                assert value == pytest.approx(
                    sum(v["models"][name]["metrics"][key] for v in cases) / 4
                )
        assert len(report["world_bootstrap"][arm]) == len(list(combinations(range(6), 2)))
    for name, operation in execution["operations"].items():
        assert operation["execution"]["whole_child_wall_seconds"] < 1200
        assert operation["execution"]["peak_committed_bytes"] < 2048 * 1024**2
        assert operation["memory_backend"] == "windows-job-aggregate-commit", name


def test_negative_findings_and_spent_history_control_are_retained():
    report = read("EXP-010-results.json")
    baseline = [v for k, v in report["cases"].items() if k.endswith("baseline")]

    def worst(name):
        return max(v["models"][name]["metrics"]["worst_absolute_error"] for v in baseline)

    assert worst("history_boost") > worst("rf_physics")
    for arm in ("baseline", "disruption"):
        metrics = report["macro"][arm]
        assert metrics["missing_history_control"]["mae"] > metrics["rf_physics"]["mae"]
    assert report["macro"]["disruption"]["history_boost"]["bias"] > 0.06


@pytest.mark.parametrize("operation", ["develop", "evaluate", "reproduce"])
def test_reproduction_cli_supplies_only_independent_frozen_receipts(
    tmp_path, monkeypatch, operation, capsys
):
    from loometric.final_candidate import __main__ as cli
    from loometric.final_candidate import service

    docs = tmp_path / "docs/experiments"
    docs.mkdir(parents=True)
    for name in ("EXP-010-candidate-receipt.json", "EXP-010-execution.json"):
        (docs / name).write_bytes((ROOT / "docs/experiments" / name).read_bytes())
    heldout = tmp_path / "data/processed/final_candidate/exp-010/heldout"
    heldout.mkdir(parents=True)
    (heldout / "a.report.json").write_bytes(
        (ROOT / "docs/experiments/EXP-010-results.json").read_bytes()
    )
    monkeypatch.setattr(
        cli, "__file__", str(tmp_path / "src/loometric/final_candidate/__main__.py")
    )
    monkeypatch.setattr("sys.argv", ["final_candidate", operation])
    observed = []

    def execute(name, **kwargs):
        observed.append((name, kwargs))
        return {"status": "PRIVATE_MECHANICAL_CALL_ONLY"}

    monkeypatch.setattr(service, "execute", execute)
    assert cli.main() == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PRIVATE_MECHANICAL_CALL_ONLY"
    name, arguments = observed[0]
    assert name == operation
    if operation == "develop":
        assert arguments == {}
    else:
        assert (
            arguments["expected_model"]
            == read("EXP-010-candidate-receipt.json")["receipt"]["model_sha256"]
        )
        assert set(arguments) == (
            {"expected_model"}
            if operation == "evaluate"
            else {"expected_model", "source_receipts", "expected_report"}
        )
