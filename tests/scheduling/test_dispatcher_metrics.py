"""Finite reservations, precedence, deterministic choices and hand-calculated quality."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from loometric.planning.capacity import assess_scenario
from loometric.planning.domain import (
    AvailabilityStatus,
    Shift,
    ShiftAssignment,
    Stage,
    TimeInterval,
)
from loometric.planning.validation import PlanningError, utc
from loometric.scheduling.contracts import UnscheduledReason
from loometric.scheduling.dispatcher import dispatch
from loometric.scheduling.metrics import calculate_metrics
from loometric.scheduling.verification import verify_schedule


def second_sewing_line(instance, workers=4):
    planning = instance.planning
    line = next(line for line in planning.lines if line.line_id == "SEW-01")
    profile = next(p for p in planning.capacity_profiles if p.line_id == line.line_id)
    capability = next(c for c in planning.capabilities if c.line_id == line.line_id)
    planning = replace(
        planning,
        lines=(*planning.lines, replace(line, line_id="SEW-02", worker_count=workers)),
        capacity_profiles=(
            *planning.capacity_profiles,
            replace(profile, profile_id="P2", line_id="SEW-02"),
        ),
        capabilities=(
            *planning.capabilities,
            replace(capability, capability_id="C2", line_id="SEW-02"),
        ),
        calendar=replace(
            planning.calendar,
            assignments=(
                *planning.calendar.assignments,
                ShiftAssignment("A2", "SEW-02", "DAY", "P2"),
            ),
        ),
    )
    return replace(instance, planning=planning)


def test_independent_capacity_does_not_establish_global_feasibility(scheduling_instance):
    instance = scheduling_instance
    independent = assess_scenario(instance.planning)
    assert all(order.all_stages_have_independent_slot for order in independent.orders)
    schedule = dispatch(instance)
    assert [item.order_id for item in schedule.allocations] == ["A"]
    assert schedule.unscheduled[0].order_id == "B"
    assert schedule.unscheduled[0].reason == UnscheduledReason.CAPACITY_RESERVED
    assert verify_schedule(instance, schedule).status == "VALID_PARTIAL"


def test_hand_calculated_completed_goods_and_resource_metrics(scheduling_instance):
    metrics = calculate_metrics(scheduling_instance, dispatch(scheduling_instance))
    assert (metrics.scheduled_orders, metrics.unscheduled_orders, metrics.partial_orders) == (
        1,
        1,
        0,
    )
    assert (metrics.scheduled_units, metrics.unscheduled_units) == (60, 80)
    assert (metrics.scheduled_operations, metrics.unscheduled_operations) == (1, 1)
    assert metrics.on_time_completed_orders == 1 and metrics.late_completed_orders == 0
    assert metrics.total_tardiness_minutes == metrics.priority_weighted_tardiness_minutes == 0
    assert metrics.makespan_minutes == 225
    assert metrics.available_line_minutes == 960 and metrics.occupied_line_minutes == 225
    assert metrics.line_utilization == Decimal("0.234375")
    assert metrics.available_worker_minutes == 2880 and metrics.consumed_worker_minutes == 900
    assert metrics.available_standard_minutes == 2400 and metrics.consumed_standard_minutes == 720
    assert metrics.unused_standard_minutes == 1680 and metrics.unused_worker_minutes == 1980
    assert metrics.standard_capacity_utilization == Decimal("0.3")
    sewing = next(r for r in metrics.resources if r.line_id == "SEW-01")
    assert sewing.line_utilization == Decimal("0.46875")


def test_multiple_lines_earliest_finish_and_stable_ties(scheduling_instance):
    instance = second_sewing_line(scheduling_instance)
    result = dispatch(instance)
    assert [allocation.line_id for allocation in result.allocations] == ["SEW-01", "SEW-02"]
    assert verify_schedule(instance, result).complete
    faster = second_sewing_line(scheduling_instance, workers=8)
    assert dispatch(faster).allocations[0].line_id == "SEW-02"
    assert dispatch(faster).allocations[0].interval.minutes == 113


def test_priority_due_date_and_order_id_ties(scheduling_instance):
    planning = scheduling_instance.planning
    orders = tuple(replace(order, priority=1) for order in planning.orders)
    instance = replace(scheduling_instance, planning=replace(planning, orders=orders[::-1]))
    assert dispatch(instance).allocations[0].order_id == "A"
    b = replace(
        orders[1],
        due_date=orders[1].due_date - timedelta(days=1),
        release_date=orders[1].release_date - timedelta(days=1),
    )
    instance = replace(instance, planning=replace(planning, orders=(orders[0], b)))
    assert dispatch(instance).allocations[0].order_id == "B"


def test_precedence_and_stage_units_are_not_finished_goods(scheduling_instance):
    planning = scheduling_instance.planning
    order = replace(planning.orders[0], required_stages=(Stage.SEWING, Stage.FINISHING))
    instance = replace(
        scheduling_instance, planning=replace(planning, orders=(order, planning.orders[1]))
    )
    schedule = dispatch(instance)
    sew, finish = schedule.allocations
    assert utc(sew.interval.end) == utc(finish.interval.start)
    assert finish.interval.minutes == 134
    assert verify_schedule(instance, schedule).feasible
    metrics = calculate_metrics(instance, schedule)
    assert metrics.scheduled_units == 60 and metrics.allocated_stage_units == 120
    assert metrics.rounding_slack_standard_minutes == Decimal("1.2")


def test_upstream_partial_work_stays_visible_without_completion_credit(scheduling_instance):
    planning = scheduling_instance.planning
    order = replace(
        planning.orders[0],
        quantity=100,
        required_stages=(Stage.SEWING, Stage.FINISHING, Stage.QUALITY_CONTROL),
    )
    instance = replace(scheduling_instance, planning=replace(planning, orders=(order,)))
    schedule = dispatch(instance)
    assert len(schedule.allocations) == 1 and len(schedule.unscheduled) == 2
    assert schedule.unscheduled[0].reason == UnscheduledReason.HORIZON_EXHAUSTED
    assert schedule.unscheduled[1].reason == UnscheduledReason.PREDECESSOR_UNSCHEDULED
    metrics = calculate_metrics(instance, schedule)
    assert (
        metrics.partial_orders == 1
        and metrics.scheduled_units == 0
        and metrics.unscheduled_units == 100
    )
    assert metrics.allocated_stage_units == 100 and metrics.orders[0].tardiness_minutes is None


@pytest.mark.parametrize(
    "mode,reason",
    [
        ("large", UnscheduledReason.REQUIRES_SPLITTING_OR_PREEMPTION),
        ("fragmented", UnscheduledReason.REQUIRES_SPLITTING_OR_PREEMPTION),
        ("short_horizon", UnscheduledReason.HORIZON_EXHAUSTED),
        ("release", UnscheduledReason.RELEASE_AFTER_HORIZON),
        ("zero_workers", UnscheduledReason.NO_AVAILABLE_CAPACITY),
        ("zero_efficiency", UnscheduledReason.NO_AVAILABLE_CAPACITY),
        ("unavailable", UnscheduledReason.NO_AVAILABLE_CAPACITY),
        ("incompatible", UnscheduledReason.NO_ELIGIBLE_LINE),
    ],
)
def test_explicit_unscheduled_reasons(scheduling_instance, mode, reason):
    instance = scheduling_instance
    planning = instance.planning
    order = planning.orders[0]
    if mode == "large":
        order = replace(order, quantity=129)
    elif mode == "fragmented":
        order = replace(order, quantity=80)
        start = planning.shifts[0].interval.start
        shift = replace(
            planning.shifts[0],
            breaks=(TimeInterval(start + timedelta(hours=4), start + timedelta(hours=5)),),
        )
        planning = replace(planning, shifts=(shift,))
    elif mode == "short_horizon":
        instance = replace(
            instance,
            horizon=TimeInterval(
                instance.horizon.start, instance.horizon.start + timedelta(hours=3)
            ),
        )
    elif mode == "release":
        order = replace(
            order,
            release_date=order.release_date + timedelta(days=1),
            due_date=order.due_date + timedelta(days=1),
        )
    elif mode in ("zero_workers", "unavailable"):
        changes = (
            {"worker_count": 0}
            if mode == "zero_workers"
            else {"availability": AvailabilityStatus.UNAVAILABLE}
        )
        planning = replace(
            planning,
            lines=tuple(
                replace(line, **changes) if line.stage == Stage.SEWING else line
                for line in planning.lines
            ),
        )
    elif mode == "zero_efficiency":
        planning = replace(
            planning,
            capacity_profiles=tuple(
                replace(p, assumed_efficiency=Decimal(0)) if p.line_id == "SEW-01" else p
                for p in planning.capacity_profiles
            ),
        )
    else:
        order = replace(order, required_stages=(Stage.QUALITY_CONTROL,))
    instance = replace(instance, planning=replace(planning, orders=(order,)))
    schedule = dispatch(instance)
    assert schedule.allocations == () and schedule.unscheduled[0].reason == reason
    assert verify_schedule(instance, schedule).feasible


def test_working_fragments_and_reserved_gaps(scheduling_instance):
    planning = scheduling_instance.planning
    start = planning.shifts[0].interval.start
    shift = replace(
        planning.shifts[0],
        breaks=(TimeInterval(start + timedelta(hours=1), start + timedelta(hours=2)),),
    )
    orders = (replace(planning.orders[0], quantity=20), replace(planning.orders[1], quantity=10))
    instance = replace(
        scheduling_instance, planning=replace(planning, shifts=(shift,), orders=orders)
    )
    schedule = dispatch(instance)
    assert utc(schedule.allocations[0].interval.start) == utc(start + timedelta(hours=2))
    assert utc(schedule.allocations[1].interval.start) == utc(start)
    assert verify_schedule(instance, schedule).complete


def test_future_release_reservation_leaves_earlier_gaps(scheduling_instance):
    planning = scheduling_instance.planning
    shift = planning.shifts[0]
    next_day = Shift(
        "NEXT",
        TimeInterval(
            shift.interval.start + timedelta(days=1), shift.interval.end + timedelta(days=1)
        ),
        (),
    )
    day = planning.orders[0].release_date + timedelta(days=1)
    orders = (replace(planning.orders[0], release_date=day, due_date=day), planning.orders[1])
    planning = replace(
        planning,
        orders=orders,
        shifts=(*planning.shifts, next_day),
        calendar=replace(
            planning.calendar,
            working_dates=(*planning.calendar.working_dates, day),
            assignments=(
                *planning.calendar.assignments,
                ShiftAssignment("NEXT", "SEW-01", "NEXT", "P-SEW-01"),
            ),
        ),
    )
    instance = replace(
        scheduling_instance,
        planning=planning,
        horizon=TimeInterval(scheduling_instance.horizon.start, next_day.interval.end),
    )
    result = dispatch(instance)
    assert result.allocations[0].interval.start.date() > result.allocations[1].interval.start.date()
    assert verify_schedule(instance, result).complete


def test_late_completion_and_priority_weighted_tardiness(scheduling_instance):
    planning = scheduling_instance.planning
    a = planning.orders[0]
    a = replace(
        a, release_date=a.release_date - timedelta(days=1), due_date=a.due_date - timedelta(days=1)
    )
    instance = replace(
        scheduling_instance, planning=replace(planning, orders=(a, planning.orders[1]))
    )
    metrics = calculate_metrics(instance, dispatch(instance))
    assert metrics.total_tardiness_minutes == 705  # Local 11:45 after a midnight deadline.
    assert metrics.priority_weighted_tardiness_minutes == 1410  # priority 1 weight 2.
    assert metrics.late_completed_orders == 1 and metrics.on_time_completed_orders == 0
    assert metrics.orders[1].tardiness_minutes is None


def test_invalid_metrics_are_refused(scheduling_instance):
    schedule = dispatch(scheduling_instance)
    corrupt = replace(
        schedule,
        allocations=(replace(schedule.allocations[0], consumed_worker_minutes=Decimal(1)),),
    )
    with pytest.raises(PlanningError, match="independent feasibility"):
        calculate_metrics(scheduling_instance, corrupt)


def test_completion_exactly_at_due_midnight_is_on_time(scheduling_instance):
    planning = scheduling_instance.planning
    shift = planning.shifts[0]
    delta = timedelta(hours=12, minutes=15)
    interval = TimeInterval(shift.interval.start + delta, shift.interval.end + delta)
    planning = replace(planning, shifts=(replace(shift, interval=interval),))
    instance = replace(scheduling_instance, planning=planning, horizon=interval)
    schedule = dispatch(instance)
    assert utc(schedule.allocations[0].interval.end) == instance.deadline_at(
        planning.orders[0].due_date
    )
    assert verify_schedule(instance, schedule).feasible
    metrics = calculate_metrics(instance, schedule)
    assert metrics.on_time_completed_orders == 1 and metrics.total_tardiness_minutes == 0


def test_zero_denominators_and_empty_makespan(scheduling_instance):
    planning = scheduling_instance.planning
    lines = tuple(
        replace(line, availability=AvailabilityStatus.UNAVAILABLE) for line in planning.lines
    )
    instance = replace(scheduling_instance, planning=replace(planning, lines=lines))
    metrics = calculate_metrics(instance, dispatch(instance))
    assert metrics.makespan_minutes is None and metrics.line_utilization is None
    assert metrics.standard_capacity_utilization is None and metrics.unused_standard_minutes == 0
    assert metrics.scheduled_units == 0 and metrics.unscheduled_units == 140


def test_reproducibility_and_collection_order_invariance(scheduling_instance):
    first = dispatch(scheduling_instance)
    assert first == dispatch(scheduling_instance)
    planning = scheduling_instance.planning
    altered = replace(
        planning,
        orders=planning.orders[::-1],
        lines=planning.lines[::-1],
        calendar=replace(planning.calendar, assignments=planning.calendar.assignments[::-1]),
    )
    other = replace(scheduling_instance, planning=altered)
    second = dispatch(other)
    assert (first.allocations, first.unscheduled) == (second.allocations, second.unscheduled)
    assert calculate_metrics(scheduling_instance, first) == calculate_metrics(other, second)
