"""Native optimization, independent small enumeration and injected phase/status faults."""

import builtins
import importlib
import itertools
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
from ortools.sat.python import cp_model

import loometric.optimization.solver as engine
from loometric.optimization.configuration import SolverConfiguration
from loometric.scheduling.contracts import UnscheduledReason
from loometric.scheduling.loading import load_instance
from loometric.scheduling.verification import verify_schedule

EXAMPLES = Path(__file__).resolve().parents[2] / "examples/scheduling"


@pytest.mark.parametrize(
    "name",
    [
        "competition",
        "parallel-routing",
        "calendar-fragments",
        "limits",
        "zero-capacity",
        "hand-enumerated",
    ],
)
def test_native_three_phase_results_pass_existing_verifier(name):
    instance = load_instance(EXAMPLES / f"{name}.json")
    result = engine.optimize(instance)
    assert result.full_lexicographic_optimal and result.proven_optimal_objectives == 3
    assert [phase.solver_status for phase in result.phases] == ["OPTIMAL"] * 3
    assert all(phase.proven_optimal and phase.prior_objectives_proven for phase in result.phases)
    assert verify_schedule(instance, result.schedule).feasible and result.metrics is not None
    assert (
        result.objectives.as_tuple()
        == engine.ObjectiveValues.from_metrics(result.metrics).as_tuple()
    )
    assert result.absolute_gap_limit == result.relative_gap_limit == 0


def test_analytical_optimum_by_independent_exhaustive_enumeration():
    # No model-builder/processing/metric helper calculates the oracle. Integers are
    # declared here from the case's independent one-worker, efficiency-one physics.
    quantities = (6, 5, 5)
    weights = (3, 2, 1)
    horizon = 10
    candidates = []
    for starts in itertools.product(*(tuple([None, *range(horizon - q + 1)]) for q in quantities)):
        active = [i for i, start in enumerate(starts) if start is not None]
        if any(
            max(starts[i], starts[j]) < min(starts[i] + quantities[i], starts[j] + quantities[j])
            for i, j in itertools.combinations(active, 2)
        ):
            continue
        vector = (
            sum(q for i, q in enumerate(quantities) if starts[i] is None),
            sum(weights[i] * (480 + starts[i] + quantities[i]) for i in active),
            max((starts[i] + quantities[i] for i in active), default=0),
        )
        candidates.append(vector)
    assert min(candidates) == (6, 1460, 10)
    result = engine.optimize(load_instance(EXAMPLES / "hand-enumerated.json"))
    assert result.objectives.as_tuple() == min(candidates)
    assert {item.order_id for item in result.schedule.allocations} == {"B", "C"}


def test_third_objective_removes_idle_time_when_higher_objectives_tie():
    instance = load_instance(EXAMPLES / "hand-enumerated.json")
    planning = instance.planning
    day = planning.calendar.working_dates[0]
    orders = tuple(
        replace(order, quantity=2, release_date=day, due_date=day) for order in planning.orders[:2]
    )
    instance = replace(instance, planning=replace(planning, orders=orders))
    # Independent two-batch enumeration: all4 pieces fit, no due penalty, then
    # compact placement is4 minutes instead of arbitrary idle placement within10.
    candidates = []
    for left, right in itertools.product([None, *range(9)], repeat=2):
        if left is not None and right is not None and max(left, right) < min(left + 2, right + 2):
            continue
        candidates.append(
            (
                2 * (left is None) + 2 * (right is None),
                0,
                max((start + 2 for start in (left, right) if start is not None), default=0),
            )
        )
    assert min(candidates) == (0, 0, 4)
    result = engine.optimize(instance)
    assert result.full_lexicographic_optimal and result.objectives.as_tuple() == min(candidates)


def test_real_zero_wall_budget_returns_unknown_without_fabricated_schedule(optimization_instance):
    result = engine.optimize(
        optimization_instance, SolverConfiguration(wall_time_seconds_per_phase=0)
    )
    assert result.status == result.terminal_solver_status == "UNKNOWN"
    assert result.schedule is result.metrics is result.objectives is result.verification is None
    assert not result.full_lexicographic_optimal and len(result.phases) == 1


@pytest.mark.parametrize("phase_index", [1, 2])
def test_feasible_phase_stops_without_freezing_or_running_lower_objectives(
    optimization_instance, monkeypatch, phase_index
):
    original = engine._solve_phase
    calls = []

    def injected(built, config, phase):
        calls.append(phase)
        run = original(built, config, phase)
        # Synthetic status injection uses a real native incumbent to test the proof
        # state machine, not a claimed real timeout measurement.
        return replace(run, status=cp_model.FEASIBLE) if phase == phase_index else run

    monkeypatch.setattr(engine, "_solve_phase", injected)
    result = engine.optimize(optimization_instance)
    assert calls == list(range(1, phase_index + 1))
    assert result.proven_optimal_objectives == phase_index - 1
    assert result.terminal_solver_status == "FEASIBLE" and not result.full_lexicographic_optimal
    assert not result.phases[-1].proven_optimal and result.verification.feasible


def test_later_unknown_retains_only_an_actual_previous_incumbent(
    optimization_instance, monkeypatch
):
    original = engine._solve_phase

    def injected(built, config, phase):
        run = original(built, config, phase)
        return replace(run, status=cp_model.UNKNOWN) if phase == 2 else run

    monkeypatch.setattr(engine, "_solve_phase", injected)
    result = engine.optimize(optimization_instance)
    assert result.used_previous_phase_incumbent and result.incumbent_phase == 1
    assert result.terminal_solver_status == "UNKNOWN" and result.proven_optimal_objectives == 1
    assert not result.full_lexicographic_optimal and result.verification.feasible
    assert result.phases[-1].objective_value is None


@pytest.mark.parametrize("status", [cp_model.UNKNOWN, cp_model.INFEASIBLE, cp_model.MODEL_INVALID])
def test_first_phase_no_solution_statuses_never_read_a_fabricated_incumbent(
    optimization_instance, monkeypatch, status
):
    original = engine._solve_phase

    def injected(built, config, phase):
        run = original(built, config, phase)
        return replace(run, status=status)

    monkeypatch.setattr(engine, "_solve_phase", injected)

    def forbidden(*args):
        pytest.fail("Adapter called for solver status without a solution")

    monkeypatch.setattr(engine, "adapt_solution", forbidden)
    result = engine.optimize(optimization_instance)
    assert result.status in ("UNKNOWN", "INFEASIBLE", "MODEL_INVALID")
    assert result.schedule is result.metrics is None
    assert result.proven_optimal_objectives == 0


def test_actual_native_infeasible_model_returns_no_schedule(optimization_instance, monkeypatch):
    original = engine.build_model

    def impossible(instance):
        built = original(instance)
        built.model.add(0 == 1)
        return built

    monkeypatch.setattr(engine, "build_model", impossible)
    result = engine.optimize(optimization_instance)
    assert result.status == "INFEASIBLE" and result.schedule is None and result.metrics is None


def test_later_infeasibility_is_reported_as_a_contradiction(optimization_instance, monkeypatch):
    original = engine._solve_phase

    def injected(built, config, phase):
        run = original(built, config, phase)
        return replace(run, status=cp_model.INFEASIBLE) if phase == 2 else run

    monkeypatch.setattr(engine, "_solve_phase", injected)
    result = engine.optimize(optimization_instance)
    assert result.status == "INFEASIBLE" and result.schedule is result.metrics is None
    assert result.diagnostics[0].code == "CONTRADICTORY_PHASE_RESULT"
    assert not result.full_lexicographic_optimal


def test_invalid_adapter_shape_returns_invalid_without_quality_claim(
    optimization_instance, monkeypatch
):
    from loometric.planning.validation import PlanningError

    def invalid(*args):
        raise PlanningError("CP_ADAPTER_INCONSISTENCY", "Synthetic adapter fault")

    monkeypatch.setattr(engine, "adapt_solution", invalid)
    result = engine.optimize(optimization_instance)
    assert result.status == "INVALID" and result.schedule is result.metrics is None
    assert result.diagnostics[0].code == "CP_ADAPTER_INCONSISTENCY"


def test_unchanged_independent_verifier_rejects_corrupted_adapter_output(
    optimization_instance, monkeypatch
):
    original = engine.adapt_solution

    def corrupted(*args):
        schedule = original(*args)
        first = replace(schedule.allocations[0], consumed_worker_minutes=Decimal(1))
        return replace(schedule, allocations=(first, *schedule.allocations[1:]))

    monkeypatch.setattr(engine, "adapt_solution", corrupted)
    result = engine.optimize(optimization_instance)
    assert result.status == "INVALID" and result.metrics is result.objectives is None
    assert not result.full_lexicographic_optimal
    assert "WORKER_MINUTES_MISMATCH" in {v.code for v in result.verification.violations}


def test_objective_consistency_gate_rejects_feasible_but_misreported_model(
    optimization_instance, monkeypatch
):
    original = engine.calculate_metrics

    def inconsistent(*args):
        return replace(original(*args), unscheduled_units=123)

    monkeypatch.setattr(engine, "calculate_metrics", inconsistent)
    result = engine.optimize(optimization_instance)
    assert result.status == "INVALID" and result.metrics is None
    assert result.verification.feasible
    assert result.diagnostics[0].code == "OBJECTIVE_MISMATCH"


def test_zero_capacity_is_a_real_verified_empty_optimum():
    result = engine.optimize(load_instance(EXAMPLES / "zero-capacity.json"))
    assert result.full_lexicographic_optimal and result.schedule.allocations == ()
    assert result.metrics.makespan_minutes is None and result.objectives.makespan_minutes == 0
    assert result.schedule.unscheduled[0].reason == UnscheduledReason.NO_AVAILABLE_CAPACITY


def test_optimizer_core_never_imports_reference_dispatcher(optimization_instance, monkeypatch):
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.startswith(
            ("loometric.scheduling.dispatcher", "loometric.prediction", "loometric.data", "sklearn")
        ):
            pytest.fail(f"Optimizer attempted forbidden dependency: {name}")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    reloaded = importlib.reload(engine)
    assert reloaded.optimize(optimization_instance).verification.feasible


def test_reproducible_result_excludes_runtime_measurements(optimization_instance):
    first = engine.optimize(optimization_instance)
    second = engine.optimize(optimization_instance)
    assert replace(first, runtime=second.runtime) == second
