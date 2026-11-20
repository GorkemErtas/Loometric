"""Audit correctness, proof-status preservation and independent result rejection."""

import json
import subprocess
import sys
from dataclasses import asdict, replace
from pathlib import Path

import pytest
from ortools.sat.python import cp_model

import loometric.benchmarks.runner as runner
import loometric.optimization.solver as engine
from loometric.benchmarks.cli import main
from loometric.benchmarks.design import BenchmarkDesign, Case, ResourceLimits, load_design
from loometric.benchmarks.generation import GenerationConfig
from loometric.benchmarks.worker import run_case
from loometric.planning.reporting import json_value
from loometric.planning.validation import PlanningError

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def request_data():
    return json_value(
        {
            "case": "test",
            "generation": asdict(GenerationConfig(orders=3, target_load_percent=30)),
            "resource_limits": asdict(ResourceLimits()),
            "wall_budget_seconds": 5,
            "deterministic_budget": 1,
            "solver_seed": 42,
        }
    )


def test_audited_result_is_reproducible_and_measurements_are_separate(request_data):
    first, second = run_case(request_data), run_case(request_data)
    assert first["deterministic"] == second["deterministic"]
    result = first["deterministic"]
    assert result["optimizer"]["full_lexicographic_optimal"]
    assert (
        result["audit_verification"]["feasible"] and result["reference"]["verification"]["feasible"]
    )
    dimensions = result["dimensions"]
    assert dimensions["eligible_alternatives"] == dimensions["optional_intervals"]
    assert dimensions["model_variables"] > dimensions["operations"]
    assert "runtime" not in result["optimizer"]
    assert first["measurements"]["audit_verification_seconds"] >= 0


def test_zero_budget_is_unknown_not_infeasible_or_fabricated(request_data):
    result = run_case({**request_data, "wall_budget_seconds": 0})["deterministic"]
    assert result["status"] == "UNKNOWN" and result["comparison"] == "NO_COMPARABLE_INCUMBENT"
    assert result["optimizer"]["schedule"] is result["optimizer"]["metrics"] is None
    assert result["reference"]["verification"]["feasible"]


@pytest.mark.parametrize("terminal,phase", [(cp_model.FEASIBLE, 1), (cp_model.UNKNOWN, 2)])
def test_audit_preserves_unproven_and_retained_incumbents(
    request_data, monkeypatch, terminal, phase
):
    original = engine._solve_phase

    def inject(built, config, number):
        actual = original(built, config, number)
        return replace(actual, status=terminal) if number == phase else actual

    monkeypatch.setattr(engine, "_solve_phase", inject)
    result = run_case(request_data)["deterministic"]
    optimized = result["optimizer"]
    assert (
        result["audit_verification"]["feasible"]
        and result["comparison"] != "NO_COMPARABLE_INCUMBENT"
    )
    assert optimized["proven_optimal_objectives"] == phase - 1
    assert not optimized["full_lexicographic_optimal"] and len(optimized["phases"]) == phase
    assert optimized["used_previous_phase_incumbent"] == (terminal == cp_model.UNKNOWN)


@pytest.mark.parametrize("corruption", ["quantity", "metrics", "absent"])
def test_independent_audit_suppresses_invalid_candidate_quality(
    request_data, monkeypatch, corruption
):
    original = engine.optimize

    def corrupt(*args):
        result = original(*args)
        if corruption == "quantity":
            bad = replace(result.schedule.allocations[0], quantity=999)
            return replace(result, schedule=replace(result.schedule, allocations=(bad,)))
        if corruption == "metrics":
            return replace(result, metrics=replace(result.metrics, unscheduled_units=999))
        return replace(result, schedule=None)

    monkeypatch.setattr(engine, "optimize", corrupt)
    result = run_case(request_data)["deterministic"]
    assert result["status"] == "INVALID" and result["comparison"] == "NO_COMPARABLE_INCUMBENT"
    assert result["optimizer"]["metrics"] is result["optimizer"]["objectives"] is None


def test_model_guard_runs_reference_but_never_constructs_solver(request_data, monkeypatch):
    import loometric.optimization.model as model

    def forbidden(*args):
        pytest.fail("Resource-skipped case created a native model")

    monkeypatch.setattr(model, "build_model", forbidden)
    request_data["resource_limits"]["max_operations"] = 1
    result = run_case(request_data)["deterministic"]
    assert result["status"] == "SKIPPED_RESOURCE_LIMIT"
    assert result["reference"]["verification"]["feasible"] and result["optimizer"] is None


def test_summary_records_all_statuses_and_repeat_mismatches():
    rows = [
        {
            "case": "one",
            "wall_budget_seconds": 1,
            "repetition": i + 1,
            "deterministic": {
                "comparison": "TIE",
                "status": "VALID_PARTIAL",
                "optimizer": {"proven_optimal_objectives": i, "full_lexicographic_optimal": False},
            },
        }
        for i in range(2)
    ]
    result = runner.summarize(rows)
    assert result["status_counts"] == {"VALID_PARTIAL": 2}
    assert len(result["repeated_result_mismatches"]) == 1 and result["full_proofs"] == 0


def test_runner_retains_all_resource_skips_without_fabricated_repeated_timings(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    design = BenchmarkDesign(
        (Case("case", "stress", GenerationConfig()),), (1, 5), 1, 42, 2, ResourceLimits()
    )
    calls = []

    def fake(*args):
        calls.append(args)
        return {
            "deterministic": {
                "status": "SKIPPED_RESOURCE_LIMIT",
                "reason": "declared size",
                "comparison": "NO_COMPARABLE_INCUMBENT",
            },
            "measurements": {},
        }, {"peak_committed_bytes": 17}

    monkeypatch.setattr(runner, "guarded_child", fake)
    output = tmp_path / ".tmp" / "audit"
    report = runner.run_benchmark(design, output, progress=False)
    assert len(calls) == 1 and len(report["rows"]) == 4
    assert "reused_resource_skip_source" in report["rows"][1]["measurements"]
    assert len((output / "runs.jsonl").read_text().splitlines()) == 4
    assert json.loads((output / "results.json").read_text())["summary"]["rows"] == 4
    with pytest.raises(PlanningError, match="not overwritten"):
        runner.run_benchmark(design, output, progress=False)


def test_runner_batch_deadline_retains_unexecuted_cells(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runner, "perf_counter", iter([0, 2, 3, 4]).__next__)
    design = BenchmarkDesign(
        (Case("case", "small", GenerationConfig()),),
        (1,),
        1,
        42,
        1,
        ResourceLimits(batch_wall_seconds=1),
    )
    report = runner.run_benchmark(design, tmp_path / ".tmp" / "audit", progress=False)
    assert report["rows"][0]["deterministic"]["status"] == "SKIPPED_RESOURCE_LIMIT"
    assert "exhausted" in report["rows"][0]["deterministic"]["reason"]


def test_cli_rejects_bulk_output_outside_ignored_directories(tmp_path, capsys):
    assert (
        main(
            [
                "--config",
                str(ROOT / "configs/m03c_benchmark.json"),
                "--output-dir",
                str(tmp_path / "untracked-bulk"),
            ]
        )
        == 2
    )
    assert "INVALID_INPUT" in capsys.readouterr().err


def test_native_offline_cli_writes_instances_results_and_repeated_audit(
    tmp_path, monkeypatch, capsys
):
    raw = json.loads((ROOT / "configs/m03c_benchmark.json").read_text())
    raw.update(seeds=[19], pressures_percent=[45], wall_budgets_seconds=[1])
    raw["tiers"] = [{**raw["tiers"][0], "orders": 2}]
    config = tmp_path / "smoke.json"
    config.write_text(json.dumps(raw))
    monkeypatch.chdir(tmp_path)
    output = tmp_path / ".tmp" / "native"
    assert main(["--config", str(config), "--output-dir", str(output)]) == 0
    report = json.loads((output / "results.json").read_text())
    assert report["summary"]["rows"] == 2
    assert not report["summary"]["repeated_result_mismatches"]
    assert len(list((output / "instances").glob("*.json"))) == 1
    assert all(
        row["deterministic"]["reference"]["verification"]["feasible"] for row in report["rows"]
    )


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": True},
        {"repetitions": 10},
        {"wall_budgets_seconds": [11]},
        {"seeds": [42, 42]},
        {"extra": 1},
    ],
)
def test_invalid_designs_fail_before_launch(tmp_path, change):
    raw = json.loads((ROOT / "configs/m03c_benchmark.json").read_text())
    raw.update(change)
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(raw))
    with pytest.raises(PlanningError):
        load_design(path)


def test_benchmark_worker_has_no_protected_data_or_ml_imports():
    code = r"""
import json,pathlib,sys
repo=pathlib.Path.cwd().as_posix().lower()
def guard(event,args):
    if event=='open' and isinstance(args[0],str):
        path=args[0].replace(chr(92),'/').lower()
        assert not path.startswith(repo+'/data/'),path
        assert not path.startswith(repo+'/src/loometric/prediction/'),path
sys.addaudithook(guard)
from dataclasses import asdict
from loometric.benchmarks.worker import run_case
from loometric.benchmarks.generation import GenerationConfig
from loometric.benchmarks.design import ResourceLimits
from loometric.planning.reporting import json_value
request=json_value(dict(case='guard',generation=asdict(GenerationConfig(orders=2,target_load_percent=20)),
    resource_limits=asdict(ResourceLimits()),wall_budget_seconds=0,deterministic_budget=1,solver_seed=42))
result=run_case(request)
assert result['deterministic']['status']=='UNKNOWN'
forbidden=('sklearn','joblib','loometric.prediction','loometric.data')
assert not any(name.startswith(forbidden) for name in sys.modules)
"""
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
