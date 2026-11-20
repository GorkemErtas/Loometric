"""Native guarded integration plus explicitly injected solver/failure outcomes."""

import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest
from ortools.sat.python import cp_model

import loometric.optimization.solver as native
import loometric.scenarios.selection as selection
from loometric.execution import ResourceLimits
from loometric.optimization.configuration import SolverConfiguration
from loometric.planning.reporting import json_value
from loometric.scenarios.application import apply_scenario
from loometric.scenarios.contracts import SchedulingRequest
from loometric.scenarios.engine import compare_scenario
from loometric.scenarios.loading import load_specification
from loometric.scheduling.contracts import (
    ProposedSchedule,
    UnscheduledOperation,
    UnscheduledReason,
    instance_fingerprint,
)
from loometric.scheduling.loading import load_instance, parse_instance
from loometric.scheduling.metrics import calculate_metrics

EXAMPLES = Path(__file__).resolve().parents[2] / "examples/scenarios"
CP_REQUEST = SchedulingRequest("greedy_with_cp_sat", SolverConfiguration())


@pytest.fixture
def routing_scenario():
    baseline = load_instance(EXAMPLES / "routing-baseline.json")
    spec = load_specification(EXAMPLES / "capacity-greedy-regression.json")
    return apply_scenario(baseline, spec).instance


def native_payload(request, *args, **kwargs):
    """Test-only native execution/injection in this process, not a timed benchmark."""
    parsed = json.loads(request)
    instance = parse_instance(parsed["instance_json"])
    result = json_value(
        asdict(native.optimize(instance, SolverConfiguration(**parsed["solver_configuration"])))
    )
    runtime = result.pop("runtime")
    return {
        "status": result["status"],
        "optimization": result,
        "dimensions": {},
        "runtime": runtime,
    }, {}


def test_native_guarded_recovery_and_tie_keep_proof_with_its_producer():
    baseline = load_instance(EXAMPLES / "routing-baseline.json")
    report = compare_scenario(
        baseline, load_specification(EXAMPLES / "capacity-optimizer-recovery.json")
    )
    before, after = (report[key]["evaluation"] for key in ("baseline", "scenario"))
    assert before["selected_producer"] == "greedy" and before["selected_proven_objectives"] == 0
    assert before["optimizer"]["full_lexicographic_optimal"]
    assert before["fallback_reason"] == "CP_SAT_NOT_STRICTLY_BETTER"
    assert after["selected_producer"] == "cp_sat" and after["selected_proven_objectives"] == 3
    assert (
        after["selected_full_lexicographic_optimal"] and after["metrics"]["scheduled_units"] == 28
    )
    assert after["greedy_metrics"]["scheduled_units"] == 18
    assert report["greedy_comparison"]["relation"] == "WORSE"
    assert report["selected_comparison"]["relation"] == "BETTER"
    assert report["runtime"]["scenario"]["worker"]["memory_backend"]


def test_actual_zero_budget_unknown_uses_verified_greedy(capacity_baseline, workers_spec):
    spec = replace(
        workers_spec,
        scheduling=SchedulingRequest(
            "greedy_with_cp_sat", SolverConfiguration(wall_time_seconds_per_phase=0)
        ),
    )
    report = compare_scenario(capacity_baseline, spec)
    for key in ("baseline", "scenario"):
        result = report[key]["evaluation"]
        assert result["selected_producer"] == "greedy" and result["verification"]["feasible"]
        assert result["fallback_reason"] == "UNKNOWN"
        assert (
            result["optimizer"]["metrics"] is None
            and not result["selected_full_lexicographic_optimal"]
        )


@pytest.mark.parametrize(
    "terminal,phase,proof", [(cp_model.FEASIBLE, 1, 0), (cp_model.UNKNOWN, 2, 1)]
)
def test_feasible_or_retained_better_incumbent_is_selected_without_full_proof(
    routing_scenario, monkeypatch, terminal, phase, proof
):
    original = native._solve_phase

    def inject(built, config, number):
        run = original(built, config, number)
        return replace(run, status=terminal) if number == phase else run

    monkeypatch.setattr(native, "_solve_phase", inject)
    monkeypatch.setattr(selection, "guarded_child", native_payload)
    result, _ = selection.evaluate_instance(routing_scenario, CP_REQUEST)
    assert result.selected_producer == "cp_sat" and result.metrics.unscheduled_units == 0
    assert (
        result.selected_proven_objectives == proof
        and not result.selected_full_lexicographic_optimal
    )
    assert result.optimizer.used_previous_phase_incumbent == (terminal == cp_model.UNKNOWN)


@pytest.mark.parametrize(
    "terminal", [cp_model.UNKNOWN, cp_model.INFEASIBLE, cp_model.MODEL_INVALID]
)
def test_no_native_incumbent_never_replaces_greedy(routing_scenario, monkeypatch, terminal):
    original = native._solve_phase

    def inject(built, config, number):
        return replace(original(built, config, number), status=terminal)

    monkeypatch.setattr(native, "_solve_phase", inject)
    monkeypatch.setattr(selection, "guarded_child", native_payload)
    result, _ = selection.evaluate_instance(routing_scenario, CP_REQUEST)
    assert result.selected_producer == "greedy" and result.optimizer.metrics is None
    assert result.fallback_reason in ("UNKNOWN", "INFEASIBLE", "MODEL_INVALID")
    assert result.verification.feasible


def test_valid_but_worse_feasible_candidate_is_rejected(routing_scenario, monkeypatch):
    def worse(request, *args, **kwargs):
        payload, runtime = native_payload(request)
        raw = payload["optimization"]
        empty = ProposedSchedule(
            routing_scenario.instance_id,
            instance_fingerprint(routing_scenario),
            (),
            tuple(
                UnscheduledOperation(
                    order.order_id, stage, order.quantity, UnscheduledReason.CAPACITY_RESERVED
                )
                for order in routing_scenario.planning.orders
                for stage in order.required_stages
            ),
        )
        metrics = calculate_metrics(routing_scenario, empty)
        phase = {
            **raw["phases"][0],
            "solver_status": "FEASIBLE",
            "objective_value": 28,
            "best_objective_bound": 0.0,
            "proven_optimal": False,
        }
        raw.update(
            status="VALID_PARTIAL",
            schedule=json_value(asdict(empty)),
            metrics=json_value(asdict(metrics)),
            objectives=selection.objective_values(metrics),
            phases=[phase],
            proven_optimal_objectives=0,
            full_lexicographic_optimal=False,
            terminal_solver_status="FEASIBLE",
            incumbent_phase=1,
            used_previous_phase_incumbent=False,
        )
        return payload, runtime

    monkeypatch.setattr(selection, "guarded_child", worse)
    result, _ = selection.evaluate_instance(routing_scenario, CP_REQUEST)
    assert (
        result.selected_producer == "greedy"
        and result.optimizer.comparison_with_greedy["relation"] == "WORSE"
    )
    assert (
        result.fallback_reason == "CP_SAT_NOT_STRICTLY_BETTER"
        and result.optimizer.verification.feasible
    )


@pytest.mark.parametrize("corruption", ["schedule", "metrics", "proof", "configuration"])
def test_invalid_native_evidence_is_suppressed(routing_scenario, monkeypatch, corruption):
    def bad(request, *args, **kwargs):
        payload, runtime = native_payload(request)
        raw = payload["optimization"]
        if corruption == "schedule":
            raw["schedule"]["allocations"][0]["quantity"] = 999
        elif corruption == "metrics":
            raw["metrics"]["scheduled_units"] = 999
        elif corruption == "proof":
            raw["proven_optimal_objectives"] = 0
        else:
            raw["configuration"]["random_seed"] = 43
        return payload, runtime

    monkeypatch.setattr(selection, "guarded_child", bad)
    result, _ = selection.evaluate_instance(routing_scenario, CP_REQUEST)
    assert result.selected_producer == "greedy" and result.fallback_reason == "INVALID"
    assert result.optimizer.metrics is None and result.optimizer.proven_objectives == 0
    assert result.optimizer.diagnostics


@pytest.mark.parametrize(
    "status", ["TERMINATED_RESOURCE_LIMIT", "SKIPPED_RESOURCE_LIMIT", "WORKER_FAILED"]
)
def test_resource_and_process_failures_keep_greedy(routing_scenario, monkeypatch, status):
    monkeypatch.setattr(
        selection,
        "guarded_child",
        lambda *args, **kwargs: (None, {"status": status, "reason": "injected"}),
    )
    result, _ = selection.evaluate_instance(routing_scenario, CP_REQUEST)
    assert result.selected_producer == "greedy" and result.fallback_reason == status


def test_spawn_error_keeps_greedy(routing_scenario, monkeypatch):
    def unavailable(*args, **kwargs):
        raise OSError("injected spawn failure")

    monkeypatch.setattr(selection, "guarded_child", unavailable)
    result, _ = selection.evaluate_instance(routing_scenario, CP_REQUEST)
    assert result.selected_producer == "greedy" and result.fallback_reason == "WORKER_FAILED"


def test_operation_guard_prevents_native_launch(routing_scenario, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Oversized request launched native worker")

    monkeypatch.setattr(selection, "guarded_child", forbidden)
    result, _ = selection.evaluate_instance(
        routing_scenario, CP_REQUEST, ResourceLimits(max_operations=1)
    )
    assert (
        result.fallback_reason == "SKIPPED_RESOURCE_LIMIT" and result.metrics.scheduled_units == 18
    )
    with pytest.raises(ValueError, match="resource envelope"):
        selection.evaluate_instance(
            routing_scenario, CP_REQUEST, ResourceLimits(process_memory_mib=1024)
        )


def test_nonobject_worker_report_is_invalid(routing_scenario, monkeypatch):
    monkeypatch.setattr(selection, "guarded_child", lambda *args, **kwargs: ([], {}))
    result, _ = selection.evaluate_instance(routing_scenario, CP_REQUEST)
    assert result.selected_producer == "greedy" and result.fallback_reason == "INVALID"
