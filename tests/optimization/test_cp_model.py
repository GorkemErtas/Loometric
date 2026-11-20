"""Direct satisfiability and arithmetic tests for the integer scheduling formulation."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from ortools.sat.python import cp_model

from loometric.optimization.configuration import SolverConfiguration
from loometric.optimization.model import SAFE_INTEGER, build_model
from loometric.planning.domain import Stage
from loometric.planning.validation import PlanningError
from loometric.scheduling.loading import load_instance

EXAMPLES = Path(__file__).resolve().parents[2] / "examples/scheduling"


def solve(built):
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 42
    solver.parameters.max_time_in_seconds = 2
    return solver, solver.solve(built.model)


def test_competing_whole_batches_cannot_both_reserve_the_line(optimization_instance):
    built = build_model(optimization_instance)
    for operation in built.operations.values():
        built.model.add(operation.present == 1)
    _, status = solve(built)
    assert status == cp_model.INFEASIBLE  # 225 + 300 > 480 minutes, no splitting.


def test_optional_intervals_select_exactly_one_or_none(optimization_instance):
    built = build_model(optimization_instance)
    built.model.minimize(built.objectives[0])
    solver, status = solve(built)
    assert status == cp_model.OPTIMAL and solver.value(built.objectives[0]) == 60
    for operation in built.operations.values():
        assert sum(solver.value(a.selected) for a in operation.alternatives) == solver.value(
            operation.present
        )
        if not solver.value(operation.present):
            assert solver.value(operation.start) == solver.value(operation.end) == 0


def test_multiple_eligible_lines_allow_parallel_complete_operations():
    built = build_model(load_instance(EXAMPLES / "parallel-routing.json"))
    for operation in built.operations.values():
        built.model.add(operation.present == 1)
    solver, status = solve(built)
    assert status == cp_model.OPTIMAL
    high = built.operations["HIGH", Stage.SEWING]
    assert {a.specification.slot.line.line_id for a in high.alternatives} == {"SEW-01", "SEW-02"}
    assert sum(solver.value(a.selected) for a in high.alternatives) == 1


@pytest.mark.parametrize("mode", ["precedence", "missing_prefix"])
def test_stage_precedence_and_presence_prefix(mode):
    built = build_model(load_instance(EXAMPLES / "parallel-routing.json"))
    sewing = built.operations["HIGH", Stage.SEWING]
    finish = built.operations["HIGH", Stage.FINISHING]
    built.model.add(finish.present == 1)
    if mode == "precedence":
        built.model.add(finish.start == 0)
    else:
        built.model.add(sewing.present == 0)
    assert solve(built)[1] == cp_model.INFEASIBLE


def test_calendar_fragment_containment_and_nonpreemption():
    built = build_model(load_instance(EXAMPLES / "calendar-fragments.json"))
    unsupported = built.operations["FRAGMENTED", Stage.SEWING]
    assert unsupported.alternatives == ()
    assert str(unsupported.specification.unavailable_reason) == "REQUIRES_SPLITTING_OR_PREEMPTION"
    small = built.operations["SMALL", Stage.SEWING]
    built.model.add(small.present == 1)
    built.model.add(small.start == 200)  # Would cross excluded time at minute210.
    assert solve(built)[1] == cp_model.INFEASIBLE


def test_release_horizon_zero_capacity_and_empty_solution():
    built = build_model(load_instance(EXAMPLES / "limits.json"))
    for key in ("A-LARGE", "B-HORIZON", "C-ZERO", "D-QC", "E-FUTURE"):
        stages = [op for op in built.operations.values() if op.specification.order.order_id == key]
        assert not any(op.alternatives for op in stages)
    zero = build_model(load_instance(EXAMPLES / "zero-capacity.json"))
    zero.model.minimize(zero.objectives[0])
    solver, status = solve(zero)
    assert status == cp_model.OPTIMAL
    assert tuple(solver.value(o) for o in zero.objectives) == (10, 0, 0)


def test_exact_duration_rounding_comes_from_existing_helper(optimization_instance):
    planning = optimization_instance.planning
    instance = replace(
        optimization_instance,
        planning=replace(planning, orders=(replace(planning.orders[0], quantity=1),)),
    )
    built = build_model(instance)
    operation = next(iter(built.operations.values()))
    assert {a.specification.requirement.duration_minutes for a in operation.alternatives} == {4}
    built.model.add(operation.present == 1)
    solver, status = solve(built)
    assert status == cp_model.OPTIMAL
    assert solver.value(operation.end) - solver.value(operation.start) == 4


def test_soft_due_and_completed_order_tardiness():
    built = build_model(load_instance(EXAMPLES / "parallel-routing.json"))
    for operation in built.operations.values():
        built.model.add(operation.present == 1)
    built.model.minimize(built.objectives[1])
    solver, status = solve(built)
    assert status == cp_model.OPTIMAL
    assert solver.value(built.objectives[1]) > 0  # Past due dates are not hard infeasibility.


@pytest.mark.parametrize("mode", ["quantity", "weighted_tardiness"])
def test_bounds_fail_before_cp_model_creation(optimization_instance, monkeypatch, mode):
    planning = optimization_instance.planning
    if mode == "quantity":
        orders = (replace(planning.orders[0], quantity=SAFE_INTEGER + 1),)
    else:
        orders = tuple(
            replace(
                order,
                release_date=order.release_date - timedelta(days=1),
                due_date=order.due_date - timedelta(days=1),
            )
            for order in (planning.orders[0], replace(planning.orders[1], priority=SAFE_INTEGER))
        )
    instance = replace(optimization_instance, planning=replace(planning, orders=orders))

    def forbidden():
        pytest.fail("CpModel was created before checking integer bounds")

    monkeypatch.setattr(cp_model, "CpModel", forbidden)
    with pytest.raises(PlanningError, match="integer bound"):
        build_model(instance)


def test_extreme_duration_is_excluded_without_inconsistent_rounding(optimization_instance):
    planning = optimization_instance.planning
    style = planning.styles[0]
    standards = tuple(
        replace(s, standard_minutes_per_unit=Decimal("1e25")) if s.stage == Stage.SEWING else s
        for s in style.standards
    )
    instance = replace(
        optimization_instance,
        planning=replace(planning, styles=(replace(style, standards=standards),)),
    )
    built = build_model(instance)
    assert all(not op.alternatives for op in built.operations.values())
    assert solve(built)[1] == cp_model.OPTIMAL


@pytest.mark.parametrize(
    "kwargs",
    [
        {"random_seed": True},
        {"random_seed": 2**31},
        {"workers": 0},
        {"workers": 2},
        {"wall_time_seconds_per_phase": -1},
        {"deterministic_time_per_phase": float("inf")},
        {"benchmark_mode": "yes"},
    ],
)
def test_invalid_solver_configuration(kwargs):
    with pytest.raises(PlanningError):
        SolverConfiguration(**kwargs)


def test_zero_budgets_and_explicit_parallel_mode_are_representable():
    assert SolverConfiguration(wall_time_seconds_per_phase=0).wall_time_seconds_per_phase == 0
    assert SolverConfiguration(workers=2, benchmark_mode=False).workers == 2
