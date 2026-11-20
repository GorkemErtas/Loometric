"""Arbitrary proposals and deliberate corruptions, without a dispatcher dependency."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from loometric.planning.domain import PlannedDowntime, Stage, TimeInterval, UnavailablePeriod
from loometric.scheduling.contracts import (
    OperationAllocation,
    ProposedSchedule,
    UnscheduledOperation,
    UnscheduledReason,
    instance_fingerprint,
)
from loometric.scheduling.resources import build_slots, processing_requirement
from loometric.scheduling.verification import verify_schedule


def allocation(
    instance, order_id="A", stage=Stage.SEWING, assignment_id="A-DAY-SEW-01", start=None
):
    order = next(o for o in instance.planning.orders if o.order_id == order_id)
    slot = next(s for s in build_slots(instance) if s.assignment.assignment_id == assignment_id)
    requirement = processing_requirement(instance, order, stage, slot)
    start = start or instance.horizon.start
    return OperationAllocation(
        order_id,
        stage,
        assignment_id,
        slot.line.line_id,
        slot.shift.shift_id,
        slot.profile.profile_id,
        TimeInterval(start, start + timedelta(minutes=requirement.duration_minutes)),
        order.quantity,
        requirement.required_standard_minutes,
        requirement.consumed_worker_minutes,
        requirement.consumed_standard_minutes,
    )


def proposal(instance, allocations=(), unscheduled=()):
    return ProposedSchedule(
        instance.instance_id, instance_fingerprint(instance), tuple(allocations), tuple(unscheduled)
    )


def partial(instance):
    return proposal(
        instance,
        (allocation(instance),),
        (UnscheduledOperation("B", Stage.SEWING, 80, UnscheduledReason.CAPACITY_RESERVED),),
    )


def codes(instance, schedule):
    return {item.code for item in verify_schedule(instance, schedule).violations}


def test_valid_partial_is_not_invalid_or_complete(scheduling_instance):
    result = verify_schedule(scheduling_instance, partial(scheduling_instance))
    assert result.feasible and not result.complete and result.violations == ()
    assert result.status == "VALID_PARTIAL"


def test_complete_proposal_and_exact_adjacency(scheduling_instance):
    planning = scheduling_instance.planning
    orders = (planning.orders[0], replace(planning.orders[1], quantity=60))
    instance = replace(scheduling_instance, planning=replace(planning, orders=orders))
    first = allocation(instance)
    second = allocation(instance, "B", start=first.interval.end)
    result = verify_schedule(instance, proposal(instance, (first, second)))
    assert result.status == "VALID_COMPLETE"


@pytest.mark.parametrize(
    "field,value,expected",
    [
        ("order_id", "missing", "UNKNOWN_OPERATION"),
        ("stage", Stage.PACKING, "UNKNOWN_OPERATION"),
        ("assignment_id", "missing", "UNKNOWN_ASSIGNMENT"),
        ("line_id", "FIN-01", "ASSIGNMENT_REFERENCE_MISMATCH"),
        ("shift_id", "missing", "ASSIGNMENT_REFERENCE_MISMATCH"),
        ("profile_id", "missing", "ASSIGNMENT_REFERENCE_MISMATCH"),
        ("quantity", 30, "QUANTITY_MISMATCH"),
        ("required_standard_minutes", Decimal(1), "STANDARD_DEMAND_MISMATCH"),
        ("consumed_worker_minutes", Decimal(225), "WORKER_MINUTES_MISMATCH"),
        ("consumed_standard_minutes", Decimal(900), "STANDARD_CAPACITY_MISMATCH"),
    ],
)
def test_arbitrary_reference_quantity_and_unit_corruptions(
    scheduling_instance, field, value, expected
):
    schedule = partial(scheduling_instance)
    corrupted = replace(schedule.allocations[0], **{field: value})
    result = verify_schedule(scheduling_instance, replace(schedule, allocations=(corrupted,)))
    assert not result.feasible and result.status == "INVALID"
    assert expected in {v.code for v in result.violations}


def test_durations_grid_horizon_and_shift_are_recomputed(scheduling_instance):
    instance = scheduling_instance
    base = partial(instance)
    original = base.allocations[0]
    for interval, expected in [
        (
            TimeInterval(original.interval.start, original.interval.end - timedelta(minutes=1)),
            "PROCESSING_DURATION_MISMATCH",
        ),
        (
            TimeInterval(original.interval.start, original.interval.start),
            "PROCESSING_DURATION_MISMATCH",
        ),
        (
            TimeInterval(
                original.interval.start + timedelta(seconds=1),
                original.interval.end + timedelta(seconds=1),
            ),
            "TIME_GRID_VIOLATION",
        ),
        (
            TimeInterval(
                instance.horizon.end - timedelta(minutes=1),
                instance.horizon.end + timedelta(minutes=224),
            ),
            "OUTSIDE_HORIZON",
        ),
    ]:
        assert expected in codes(
            instance, replace(base, allocations=(replace(original, interval=interval),))
        )


def test_resource_overlap_detected_independently(scheduling_instance):
    instance = scheduling_instance
    first, second = allocation(instance), allocation(instance, "B")
    assert "RESOURCE_OVERLAP" in codes(instance, proposal(instance, (first, second)))


@pytest.mark.parametrize("mode", ["break", "downtime", "unavailable"])
def test_forbidden_calendar_intervals(scheduling_instance, mode):
    instance = scheduling_instance
    planning = instance.planning
    blocked = TimeInterval(
        instance.horizon.start + timedelta(hours=1), instance.horizon.start + timedelta(hours=2)
    )
    if mode == "break":
        planning = replace(planning, shifts=(replace(planning.shifts[0], breaks=(blocked,)),))
    elif mode == "downtime":
        planning = replace(
            planning,
            calendar=replace(
                planning.calendar,
                planned_downtime=(PlannedDowntime("d", "A-DAY-SEW-01", blocked, "synthetic"),),
            ),
        )
    else:
        planning = replace(
            planning,
            calendar=replace(
                planning.calendar,
                unavailable_periods=(UnavailablePeriod("u", "SEW-01", blocked, "synthetic"),),
            ),
        )
    instance = replace(instance, planning=planning)
    assert "UNAVAILABLE_INTERVAL" in codes(instance, partial(instance))


def test_release_is_hard_due_is_soft(scheduling_instance):
    instance = scheduling_instance
    planning = instance.planning
    future = replace(
        planning.orders[0],
        release_date=planning.orders[0].release_date + timedelta(days=1),
        due_date=planning.orders[0].due_date + timedelta(days=1),
    )
    instance = replace(instance, planning=replace(planning, orders=(future, planning.orders[1])))
    assert "BEFORE_RELEASE" in codes(instance, partial(instance))
    past = replace(
        future,
        release_date=future.release_date - timedelta(days=2),
        due_date=future.due_date - timedelta(days=2),
    )
    instance = replace(
        instance, planning=replace(instance.planning, orders=(past, planning.orders[1]))
    )
    assert verify_schedule(instance, partial(instance)).feasible


def test_missing_duplicate_and_unexpected_reporting(scheduling_instance):
    instance = scheduling_instance
    schedule = partial(instance)
    assert "UNREPORTED_OPERATION" in codes(instance, replace(schedule, unscheduled=()))
    assert "DUPLICATE_OPERATION" in codes(
        instance, replace(schedule, allocations=(*schedule.allocations, *schedule.allocations))
    )
    duplicate = UnscheduledOperation("A", Stage.SEWING, 60, UnscheduledReason.CAPACITY_RESERVED)
    assert "DUPLICATE_OPERATION" in codes(
        instance, replace(schedule, unscheduled=(*schedule.unscheduled, duplicate))
    )
    wrong = replace(schedule.unscheduled[0], quantity=40)
    assert "QUANTITY_MISMATCH" in codes(instance, replace(schedule, unscheduled=(wrong,)))


def test_precedence_and_missing_predecessor(scheduling_instance):
    planning = scheduling_instance.planning
    order = replace(planning.orders[0], required_stages=(Stage.SEWING, Stage.FINISHING))
    instance = replace(scheduling_instance, planning=replace(planning, orders=(order,)))
    sew = allocation(instance)
    finish = allocation(instance, stage=Stage.FINISHING, assignment_id="A-DAY-FIN-01")
    assert "PRECEDENCE_VIOLATION" in codes(instance, proposal(instance, (sew, finish)))
    un = UnscheduledOperation("A", Stage.SEWING, 60, UnscheduledReason.NO_AVAILABLE_CAPACITY)
    assert "MISSING_PREDECESSOR" in codes(instance, proposal(instance, (finish,), (un,)))
    finish = allocation(
        instance, stage=Stage.FINISHING, assignment_id="A-DAY-FIN-01", start=sew.interval.end
    )
    assert verify_schedule(instance, proposal(instance, (sew, finish))).complete


def test_instance_binding_and_all_unscheduled_are_checked(scheduling_instance):
    instance = scheduling_instance
    assert "INSTANCE_MISMATCH" in codes(
        instance, replace(partial(instance), instance_fingerprint="0" * 64)
    )
    unscheduled = tuple(
        UnscheduledOperation(o.order_id, s, o.quantity, UnscheduledReason.CAPACITY_RESERVED)
        for o in instance.planning.orders
        for s in o.required_stages
    )
    result = verify_schedule(instance, proposal(instance, unscheduled=unscheduled))
    assert result.feasible and not result.complete


def test_verifier_runs_when_dispatcher_import_is_forbidden(scheduling_instance, monkeypatch):
    import builtins
    import importlib

    import loometric.scheduling.verification as verification

    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name == "loometric.scheduling.dispatcher":
            pytest.fail("The independent verifier attempted to import a dispatcher.")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    module = importlib.reload(verification)
    assert module.verify_schedule(scheduling_instance, partial(scheduling_instance)).feasible
