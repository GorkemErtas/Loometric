"""Frozen problem subset, exact processing time, units and shared interval utilities."""

from dataclasses import asdict, replace
from datetime import datetime, timedelta
from decimal import Decimal, localcontext

import pytest

from loometric.planning.availability import merge_intervals, subtract_intervals, union_minutes
from loometric.planning.domain import AvailabilityStatus, PlannedDowntime, Stage, TimeInterval
from loometric.planning.reporting import json_value
from loometric.planning.validation import PlanningError, utc
from loometric.scheduling.contracts import instance_fingerprint
from loometric.scheduling.resources import build_slots, eligible, processing_requirement


def test_exact_duration_and_capacity_units(scheduling_instance):
    instance = scheduling_instance
    slot = next(s for s in build_slots(instance) if s.line.line_id == "SEW-01")
    requirement = processing_requirement(instance, instance.planning.orders[0], Stage.SEWING, slot)
    assert requirement.duration_minutes == 225  # 60*12/(4*0.8), elapsed minutes.
    assert requirement.required_standard_minutes == 720
    assert requirement.consumed_worker_minutes == 900
    assert requirement.consumed_standard_minutes == 720
    assert sum(i.minutes for i in slot.working_intervals) == 480


def test_rational_ceil_reserves_rounding_slack(scheduling_instance):
    planning = scheduling_instance.planning
    order = replace(planning.orders[0], quantity=1)
    instance = replace(scheduling_instance, planning=replace(planning, orders=(order,)))
    slot = next(s for s in build_slots(instance) if s.line.line_id == "SEW-01")
    requirement = processing_requirement(instance, order, Stage.SEWING, slot)
    assert requirement.duration_minutes == 4  # exact 3.75 rounded UP, never to nearest.
    assert requirement.required_standard_minutes == 12
    assert requirement.consumed_worker_minutes == 16
    assert requirement.consumed_standard_minutes == Decimal("12.8")
    with localcontext() as context:
        context.prec = 2
        assert processing_requirement(instance, order, Stage.SEWING, slot) == requirement


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("schema_version", 2, "SCHEDULING_SCHEMA_MISMATCH"),
        ("schema_version", True, "INVALID_INTEGER"),
        ("policy_version", "split-stage", "SCHEDULING_SCHEMA_MISMATCH"),
        ("allocation_granularity_minutes", 5, "UNSUPPORTED_GRANULARITY"),
        ("allocation_granularity_minutes", True, "INVALID_INTEGER"),
        ("calendar_utc_offset_minutes", 1440, "INVALID_CALENDAR_OFFSET"),
        ("calendar_utc_offset_minutes", -1440, "INVALID_INTEGER"),
        ("calendar_utc_offset_minutes", 0, "CALENDAR_OFFSET_MISMATCH"),
        ("instance_id", " x", "INVALID_IDENTIFIER"),
    ],
)
def test_invalid_instance_contract(scheduling_instance, field, value, code):
    with pytest.raises(PlanningError) as caught:
        replace(scheduling_instance, **{field: value})
    assert caught.value.code == code


def test_horizon_grid_and_range(scheduling_instance):
    instance = scheduling_instance
    for delta in (timedelta(seconds=1), timedelta(microseconds=1)):
        with pytest.raises(PlanningError, match="UTC minutes"):
            replace(
                instance, horizon=TimeInterval(instance.horizon.start + delta, instance.horizon.end)
            )
    with pytest.raises(PlanningError, match="positive"):
        replace(instance, horizon=TimeInterval(instance.horizon.start, instance.horizon.start))


def test_calendar_endpoints_must_be_on_grid(scheduling_instance):
    instance = scheduling_instance
    shift = instance.planning.shifts[0]
    interval = TimeInterval(shift.interval.start, shift.interval.start + timedelta(seconds=30))
    shift = replace(shift, breaks=(interval,))
    with pytest.raises(PlanningError) as caught:
        replace(instance, planning=replace(instance.planning, shifts=(shift,)))
    assert caught.value.code == "UNSUPPORTED_TIME_GRID"


def test_release_and_soft_due_use_explicit_calendar_midnights(scheduling_instance):
    day = scheduling_instance.planning.orders[0].release_date
    assert scheduling_instance.release_at(day) == datetime.fromisoformat("2030-01-06T21:00:00Z")
    assert scheduling_instance.deadline_at(day) == datetime.fromisoformat("2030-01-07T21:00:00Z")


def test_horizon_clipping_and_full_window_diagnostics(scheduling_instance):
    instance = scheduling_instance
    clipped = replace(
        instance,
        horizon=TimeInterval(
            instance.horizon.start + timedelta(hours=1), instance.horizon.end - timedelta(hours=1)
        ),
    )
    assert all(
        sum(w.minutes for w in slot.working_intervals) == 360 for slot in build_slots(clipped)
    )
    assert all(
        sum(w.minutes for w in slot.working_intervals) == 480
        for slot in build_slots(clipped, within_horizon=False)
    )


def test_breaks_downtime_and_unavailability_union(scheduling_instance):
    instance = scheduling_instance
    shift = instance.planning.shifts[0]
    start = shift.interval.start
    interval = TimeInterval(start + timedelta(hours=1), start + timedelta(hours=2))
    downtime = PlannedDowntime("d", "A-DAY-SEW-01", interval, "synthetic")
    planning = replace(
        instance.planning,
        shifts=(replace(shift, breaks=(interval,)),),
        calendar=replace(instance.planning.calendar, planned_downtime=(downtime,)),
    )
    slot = next(
        s for s in build_slots(replace(instance, planning=planning)) if s.line.line_id == "SEW-01"
    )
    assert [window.minutes for window in slot.working_intervals] == [60, 360]
    assert all(not window.overlaps(interval) for window in slot.working_intervals)


@pytest.mark.parametrize(
    "field,value", [("worker_count", 0), ("availability", AvailabilityStatus.UNAVAILABLE)]
)
def test_zero_capacity_and_compatibility(scheduling_instance, field, value):
    instance = scheduling_instance
    lines = tuple(
        replace(line, **{field: value}) if line.line_id == "SEW-01" else line
        for line in instance.planning.lines
    )
    instance = replace(instance, planning=replace(instance.planning, lines=lines))
    slots = build_slots(instance)
    slot = next(s for s in slots if s.line.line_id == "SEW-01")
    if field == "availability":
        assert slot.working_intervals == ()
    else:
        with pytest.raises(PlanningError, match="Zero crew"):
            processing_requirement(instance, instance.planning.orders[0], Stage.SEWING, slot)
    other = next(s for s in slots if s.line.line_id == "FIN-01")
    assert not eligible(instance, instance.planning.orders[0], Stage.SEWING, other)


def test_interval_complement_and_timezone_adjacency(scheduling_instance):
    base = scheduling_instance.horizon
    start, end = utc(base.start), utc(base.end)
    blocked = (
        TimeInterval(start - timedelta(hours=1), start + timedelta(hours=1)),
        TimeInterval(start + timedelta(minutes=30), start + timedelta(hours=2)),
        TimeInterval(end, end + timedelta(hours=1)),
    )
    assert subtract_intervals(base, blocked) == (TimeInterval(start + timedelta(hours=2), end),)
    assert union_minutes(blocked) == 240
    assert len(merge_intervals(blocked)) == 2
    assert subtract_intervals(base, (base,)) == ()
    assert subtract_intervals(base, ()) == (TimeInterval(start, end),)


def test_stable_fingerprint_and_explicit_time_serialization(scheduling_instance):
    first = instance_fingerprint(scheduling_instance)
    assert first == instance_fingerprint(scheduling_instance) and len(first) == 64
    assert first != instance_fingerprint(replace(scheduling_instance, instance_id="other"))
    payload = json_value(asdict(scheduling_instance))
    assert payload["horizon"]["start"] == "2030-01-07T08:00:00+03:00"
    assert payload["planning"]["orders"][0]["release_date"] == "2030-01-07"
