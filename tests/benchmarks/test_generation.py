"""Generator contracts, frozen design, exact wire data and resource preflight."""

import random
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from loometric.benchmarks.design import load_design
from loometric.benchmarks.generation import (
    GenerationConfig,
    generate_instance,
    instance_json,
    static_dimensions,
)
from loometric.planning.validation import PlanningError
from loometric.scheduling.contracts import instance_fingerprint
from loometric.scheduling.dispatcher import dispatch
from loometric.scheduling.loading import parse_instance
from loometric.scheduling.verification import verify_schedule

ROOT = Path(__file__).resolve().parents[2]
DESIGN = load_design(ROOT / "configs/m03c_benchmark.json")


@pytest.mark.parametrize("case", DESIGN.cases, ids=lambda case: case.name)
def test_every_declared_case_validates_and_round_trips(case):
    instance = generate_instance(case.generation)
    assert parse_instance(instance_json(instance)) == instance
    assert instance.planning.synthetic and len(instance.planning.orders) == case.generation.orders
    assert len(instance.planning.lines) == case.generation.lines
    assert instance.policy_version == "whole-stage-minute-v1"


def test_frozen_design_is_bounded_and_retains_stress_cases():
    assert len(DESIGN.cases) == 36
    assert DESIGN.wall_budgets_seconds == (1, 5, 10)
    assert DESIGN.deterministic_budget == 1 and DESIGN.solver_seed == 42
    assert DESIGN.repetitions == 2
    assert {case.generation.seed for case in DESIGN.cases} == {19, 42, 73}
    stress = [case for case in DESIGN.cases if case.tier == "stress"]
    assert len(stress) == 9
    reason = DESIGN.resource_limits.rejection({"operations": 750})
    assert reason == "operations=750 exceeds declared limit 300"


def test_local_random_state_and_stable_identity():
    random.seed(101)
    before = random.getstate()
    first = generate_instance(GenerationConfig())
    second = generate_instance(GenerationConfig())
    assert random.getstate() == before
    assert first == second and instance_json(first) == instance_json(second)
    assert instance_fingerprint(first) == instance_fingerprint(second)
    different = generate_instance(GenerationConfig(seed=19))
    assert instance_fingerprint(first) != instance_fingerprint(different)


def test_representative_fixture_freezes_generator_content():
    fixture = ROOT / "examples/scheduling-scalability/representative.json"
    expected = generate_instance(GenerationConfig())
    assert parse_instance(fixture.read_text(encoding="utf-8")) == expected


def test_pressure_changes_standards_without_changing_orders_or_capacity():
    low = generate_instance(GenerationConfig(target_load_percent=45))
    high = generate_instance(GenerationConfig(target_load_percent=135))
    assert low.planning.orders == high.planning.orders
    assert low.planning.lines == high.planning.lines
    assert low.planning.calendar == high.planning.calendar
    assert low.planning.capacity_profiles == high.planning.capacity_profiles
    for instance, target in ((low, Decimal("0.45")), (high, Decimal("1.35"))):
        for ratio in static_dimensions(instance)["realized_load_by_stage"].values():
            assert abs(Decimal(ratio) - target) < Decimal("0.002")


def test_configurable_ranges_releases_priorities_and_no_pressure_scaling():
    config = GenerationConfig(
        orders=12,
        horizon_days=3,
        shifts_per_day=2,
        quantity_min=9,
        quantity_max=9,
        standard_min=3,
        standard_max=3,
        target_load_percent=None,
        release_spread_days=2,
        due_slack_days=0,
        priorities=(7,),
        break_minutes=0,
        downtime_minutes=0,
    )
    instance = generate_instance(config)
    assert len(instance.planning.shifts) == 6
    assert not instance.planning.calendar.planned_downtime
    assert all(not shift.breaks for shift in instance.planning.shifts)
    assert all(
        order.quantity == 9 and order.priority == 7 and order.release_date == order.due_date
        for order in instance.planning.orders
    )
    assert all(
        standard.standard_minutes_per_unit == 3
        for style in instance.planning.styles
        for standard in style.standards
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"orders": True},
        {"stages": 6},
        {"lines": 1},
        {"compatible_lines": 3},
        {"shift_minutes": 200},
        {"shifts_per_day": 3},
        {"break_minutes": 60},
        {"downtime_minutes": -1},
        {"quantity_min": 30},
        {"priorities": ()},
        {"release_spread_days": 1},
        {"target_load_percent": 0},
    ],
)
def test_invalid_generator_configuration_fails_explicitly(changes):
    with pytest.raises(PlanningError):
        replace(GenerationConfig(), **changes)


def test_large_generated_instance_passes_unchanged_reference_verifier():
    case = next(case for case in DESIGN.cases if case.tier == "large")
    instance = generate_instance(case.generation)
    assert verify_schedule(instance, dispatch(instance)).feasible
    dimensions = static_dimensions(instance)
    assert dimensions["operations"] == 180 and dimensions["working_fragments"] == 108
    assert DESIGN.resource_limits.rejection(dimensions) is None
