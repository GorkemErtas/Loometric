"""Strict specifications, atomic edits, same demand and unchanged temporal policy."""

import json
from dataclasses import asdict, replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from loometric.optimization.configuration import SolverConfiguration
from loometric.planning.domain import PlannedDowntime, ShiftAssignment, TimeInterval
from loometric.planning.validation import PlanningError
from loometric.scenarios.application import apply_scenario, demand_fingerprint
from loometric.scenarios.contracts import (
    AddAssignment,
    AddDowntime,
    RemoveAssignment,
    RemoveDowntime,
    ReplaceDowntime,
    SchedulingRequest,
    SetEfficiency,
    SetWorkers,
    specification_fingerprint,
)
from loometric.scenarios.loading import load_specification, parse_specification
from loometric.scheduling.contracts import instance_fingerprint

EXAMPLES = Path(__file__).resolve().parents[2] / "examples/scenarios"


@pytest.mark.parametrize(
    "name",
    [
        "additional-workers",
        "reduced-efficiency",
        "added-shift",
        "downtime-reduction",
        "downtime-removal",
        "downtime-addition",
        "unavailable-line",
        "multiple-changes",
        "removed-shift",
        "no-improvement",
    ],
)
def test_changes_preserve_baseline_and_fixed_demand(capacity_baseline, name):
    before = asdict(capacity_baseline)
    fingerprint = instance_fingerprint(capacity_baseline)
    spec = load_specification(EXAMPLES / f"{name}.json")
    first, second = apply_scenario(capacity_baseline, spec), apply_scenario(capacity_baseline, spec)
    assert first == second and instance_fingerprint(first.instance) == instance_fingerprint(
        second.instance
    )
    assert (
        asdict(capacity_baseline) == before
        and instance_fingerprint(capacity_baseline) == fingerprint
    )
    assert demand_fingerprint(first.instance) == demand_fingerprint(capacity_baseline)
    for field in ("orders", "styles", "shifts", "capabilities"):
        assert getattr(first.instance.planning, field) == getattr(capacity_baseline.planning, field)
    assert first.instance.horizon == capacity_baseline.horizon
    assert (
        first.instance.policy_version == capacity_baseline.policy_version == "whole-stage-minute-v1"
    )
    assert (
        first.instance.planning.calendar.working_dates
        == capacity_baseline.planning.calendar.working_dates
    )
    assert [entry.index for entry in first.audit] == list(range(1, len(spec.changes) + 1))


def test_baseline_identity_required_even_if_demand_matches(capacity_baseline, workers_spec):
    for spec in (
        replace(workers_spec, baseline_fingerprint="0" * 64),
        replace(workers_spec, baseline_instance_id="different"),
    ):
        with pytest.raises(PlanningError, match="exact baseline"):
            apply_scenario(capacity_baseline, spec)


def test_execution_settings_do_not_change_transformed_identity(capacity_baseline, workers_spec):
    cp = replace(
        workers_spec, scheduling=SchedulingRequest("greedy_with_cp_sat", SolverConfiguration())
    )
    assert apply_scenario(capacity_baseline, cp) == apply_scenario(capacity_baseline, workers_spec)
    assert specification_fingerprint(cp) != specification_fingerprint(workers_spec)


def test_audit_contains_before_after_and_noop(capacity_baseline, workers_spec):
    spec = replace(workers_spec, changes=(SetWorkers("LINE", 2),))
    audit = apply_scenario(capacity_baseline, spec).audit[0]
    assert not audit.changed and audit.before == audit.after
    changed = apply_scenario(capacity_baseline, workers_spec).audit[0]
    assert (
        changed.changed
        and changed.before["worker_count"] == 2
        and changed.after["worker_count"] == 3
    )


def test_efficiency_has_explicit_hypothetical_provenance(capacity_baseline, workers_spec):
    spec = replace(workers_spec, changes=(SetEfficiency("PROFILE", Decimal("0.25")),))
    profile = apply_scenario(capacity_baseline, spec).instance.planning.capacity_profiles[0]
    assert profile.source_id == spec.provenance.source_id and profile.evidence_status == "synthetic"
    assert profile.effective_date == capacity_baseline.planning.capacity_profiles[0].effective_date


@pytest.mark.parametrize(
    "changes",
    [
        (SetWorkers("LINE", 3), SetWorkers("LINE", 4)),
        (RemoveDowntime("STOP"), RemoveDowntime("STOP")),
        (
            RemoveAssignment("ASSIGNMENT"),
            AddAssignment(ShiftAssignment("ASSIGNMENT", "LINE", "SHIFT", "PROFILE")),
        ),
    ],
)
def test_conflicts_rejected_without_mutation(capacity_baseline, workers_spec, changes):
    before = instance_fingerprint(capacity_baseline)
    with pytest.raises(PlanningError) as caught:
        apply_scenario(capacity_baseline, replace(workers_spec, changes=changes))
    assert caught.value.code == "SCENARIO_CONFLICT"
    assert instance_fingerprint(capacity_baseline) == before


def test_atomic_final_validation_requires_explicit_cleanup(capacity_baseline, workers_spec):
    with pytest.raises(PlanningError) as caught:
        apply_scenario(
            capacity_baseline, replace(workers_spec, changes=(RemoveAssignment("ASSIGNMENT"),))
        )
    assert caught.value.code == "UNKNOWN_REFERENCE"
    changes = (RemoveAssignment("ASSIGNMENT"), RemoveDowntime("STOP"))
    result = apply_scenario(capacity_baseline, replace(workers_spec, changes=changes))
    assert not result.instance.planning.calendar.assignments
    assert not result.instance.planning.calendar.planned_downtime
    reverse = apply_scenario(capacity_baseline, replace(workers_spec, changes=changes[::-1]))
    assert result.instance.planning.calendar == reverse.instance.planning.calendar
    assert instance_fingerprint(result.instance) != instance_fingerprint(reverse.instance)


@pytest.mark.parametrize(
    "assignment,code",
    [
        (ShiftAssignment("NEW", "UNKNOWN", "RESERVE", "PROFILE"), "UNKNOWN_REFERENCE"),
        (ShiftAssignment("NEW", "LINE", "UNKNOWN", "PROFILE"), "UNKNOWN_REFERENCE"),
        (ShiftAssignment("NEW", "LINE", "SHIFT", "PROFILE"), "OVERLAPPING_ASSIGNMENTS"),
        (ShiftAssignment("ASSIGNMENT", "LINE", "RESERVE", "PROFILE"), "ENTITY_ALREADY_EXISTS"),
    ],
)
def test_assignment_integrity(capacity_baseline, workers_spec, assignment, code):
    with pytest.raises(PlanningError) as caught:
        apply_scenario(
            capacity_baseline, replace(workers_spec, changes=(AddAssignment(assignment),))
        )
    assert caught.value.code == code


def test_profile_effectiveness(capacity_baseline, workers_spec):
    old = capacity_baseline.planning
    future = replace(
        old.capacity_profiles[0],
        profile_id="FUTURE",
        effective_date=old.calendar.working_dates[0] + timedelta(days=1),
    )
    baseline = replace(
        capacity_baseline, planning=replace(old, capacity_profiles=(*old.capacity_profiles, future))
    )
    spec = replace(
        workers_spec,
        baseline_fingerprint=instance_fingerprint(baseline),
        changes=(AddAssignment(ShiftAssignment("NEW", "LINE", "RESERVE", "FUTURE")),),
    )
    with pytest.raises(PlanningError) as caught:
        apply_scenario(baseline, spec)
    assert caught.value.code == "PROFILE_NOT_EFFECTIVE"


@pytest.mark.parametrize(
    "minutes,seconds,code", [(61, 0, "DOWNTIME_OUTSIDE_SHIFT"), (10, 1, "UNSUPPORTED_TIME_GRID")]
)
def test_downtime_interval_constraints(capacity_baseline, workers_spec, minutes, seconds, code):
    start = capacity_baseline.horizon.start
    stop = PlannedDowntime(
        "STOP",
        "ASSIGNMENT",
        TimeInterval(start, start + timedelta(minutes=minutes, seconds=seconds)),
        "explicit",
    )
    with pytest.raises(PlanningError) as caught:
        apply_scenario(capacity_baseline, replace(workers_spec, changes=(ReplaceDowntime(stop),)))
    assert caught.value.code == code


def test_overlapping_stop_reasons_are_retained(capacity_baseline, workers_spec):
    stop = replace(capacity_baseline.planning.calendar.planned_downtime[0], downtime_id="SECOND")
    result = apply_scenario(capacity_baseline, replace(workers_spec, changes=(AddDowntime(stop),)))
    assert len(result.instance.planning.calendar.planned_downtime) == 2


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(schema_version=True),
        lambda d: d.update(schema_version=2),
        lambda d: d.update(extra="unsupported"),
        lambda d: d.update(orders=[]),
        lambda d: d["changes"][0].update(worker_count=True),
        lambda d: d["changes"][0].update(worker_count=-1),
        lambda d: d["changes"][0].update(quantity=1),
        lambda d: d["changes"][0].update(operation="set_quantity"),
        lambda d: d["provenance"].update(synthetic=False),
        lambda d: d.update(baseline_fingerprint="bad"),
        lambda d: d.update(scheduling={"method": "greedy", "solver": {}}),
        lambda d: d.update(scheduling={"method": "greedy_with_cp_sat", "solver": {"workers": 2}}),
        lambda d: d.update(
            scheduling={
                "method": "greedy_with_cp_sat",
                "solver": {"wall_time_seconds_per_phase": 11},
            }
        ),
        lambda d: d.update(
            scheduling={
                "method": "greedy_with_cp_sat",
                "solver": {"deterministic_time_per_phase": 2},
            }
        ),
    ],
)
def test_strict_schema(mutate):
    data = json.loads((EXAMPLES / "additional-workers.json").read_text())
    mutate(data)
    with pytest.raises(PlanningError):
        parse_specification(json.dumps(data))


@pytest.mark.parametrize("efficiency", ['"0.5"', "true", "NaN", "1.1", "-0.1"])
def test_efficiency_wire_values(efficiency):
    source = (EXAMPLES / "reduced-efficiency.json").read_text().replace("0.25", efficiency)
    with pytest.raises(PlanningError):
        parse_specification(source)


def test_duplicate_json_keys():
    with pytest.raises(PlanningError):
        parse_specification('{"schema_version":1,"schema_version":1}')
