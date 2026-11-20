"""Hand-calculated synthetic labor/capacity examples and interval invariants."""

from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal, localcontext

import pytest

from loometric.planning.availability import shift_availability, union_minutes
from loometric.planning.capacity import (
    assess_scenario,
    required_standard_minutes,
    required_worker_minutes,
)
from loometric.planning.domain import (
    AvailabilityStatus,
    PlannedDowntime,
    Shift,
    ShiftAssignment,
    Stage,
    TimeInterval,
    UnavailablePeriod,
)
from loometric.planning.reporting import report_to_dict
from loometric.planning.validation import PlanningError


def time_span(start: str, end: str) -> TimeInterval:
    return TimeInterval(
        datetime.fromisoformat("2030-01-07T" + start + ":00+03:00"),
        datetime.fromisoformat("2030-01-07T" + end + ":00+03:00"),
    )


def sewing_row(report):
    return next(
        row
        for row in report.assessments
        if row.assignment_id == "a-sew" and row.stage == Stage.SEWING
    )


def test_dimensions_and_hand_calculated_capacity(planning_scenario):
    report = assess_scenario(planning_scenario)
    slot = next(slot for slot in report.slots if slot.line_id == "sew")
    assert slot.availability.gross_elapsed_minutes == 480
    assert slot.availability.available_elapsed_minutes == 450
    assert slot.available_worker_minutes == 1800  # 450 elapsed minutes * 4 workers.
    assert slot.effective_capacity_standard_minutes == 1440  # 1800 * 0.8.
    row = sewing_row(report)
    assert row.potential_units == 120  # floor(1440 / 12).
    assert row.required_standard_minutes == 600  # 50 pieces * 12 labor minutes/piece.
    assert row.required_worker_minutes == 750  # 600 / 0.8.
    assert row.shortfall_standard_minutes == row.shortfall_worker_minutes == 0
    assert row.independent_slot_feasible and row.capacity_sufficient
    assert report.orders[0].required_standard_minutes_total == 800  # sewing + finishing.
    assert report.schedule_feasibility == "NOT_ASSESSED" and not report.allocation_performed


def test_exact_shortfall(planning_scenario):
    scenario = replace(
        planning_scenario, orders=(replace(planning_scenario.orders[0], quantity=200),)
    )
    row = sewing_row(assess_scenario(scenario))
    assert row.required_standard_minutes == 2400
    assert row.required_worker_minutes == 3000
    assert row.shortfall_standard_minutes == 960
    assert row.shortfall_worker_minutes == 1200
    assert row.reason_codes == ("INSUFFICIENT_CAPACITY",)


def test_overlapping_reasons_are_not_double_counted(planning_scenario):
    s = planning_scenario
    downtime = (
        PlannedDowntime("D1", "a-sew", time_span("11:30", "12:30"), "synthetic"),
        PlannedDowntime("D2", "a-sew", time_span("12:15", "13:00"), "synthetic"),
    )
    periods = (UnavailablePeriod("U1", "sew", time_span("12:45", "13:30"), "synthetic"),)
    scenario = replace(
        s, calendar=replace(s.calendar, planned_downtime=downtime, unavailable_periods=periods)
    )
    slot = next(slot for slot in assess_scenario(scenario).slots if slot.line_id == "sew")
    a = slot.availability
    assert (
        a.break_minutes,
        a.planned_downtime_additional_minutes,
        a.unavailable_additional_minutes,
    ) == (30, 60, 30)
    assert a.blocked_union_minutes == 120 and a.available_elapsed_minutes == 360
    assert slot.available_worker_minutes == 1440
    assert slot.effective_capacity_standard_minutes == 1152
    assert sewing_row(assess_scenario(scenario)).potential_units == 96


@pytest.mark.parametrize(
    "mode",
    [
        "zero_workers",
        "unavailable_line",
        "full_downtime",
        "full_break",
        "full_unavailable",
        "zero_efficiency",
    ],
)
def test_zero_capacity_is_explicit(planning_scenario, mode):
    s = planning_scenario
    if mode in ("zero_workers", "unavailable_line"):
        changes = (
            {"worker_count": 0}
            if mode == "zero_workers"
            else {"availability": AvailabilityStatus.UNAVAILABLE}
        )
        s = replace(s, lines=(replace(s.lines[0], **changes), s.lines[1]))
    elif mode == "full_downtime":
        s = replace(
            s,
            calendar=replace(
                s.calendar,
                planned_downtime=(
                    PlannedDowntime("D", "a-sew", s.shifts[0].interval, "synthetic"),
                ),
            ),
        )
    elif mode == "full_break":
        s = replace(s, shifts=(replace(s.shifts[0], breaks=(s.shifts[0].interval,)),))
    elif mode == "full_unavailable":
        s = replace(
            s,
            calendar=replace(
                s.calendar,
                unavailable_periods=(
                    UnavailablePeriod("U", "sew", s.shifts[0].interval, "synthetic"),
                ),
            ),
        )
    else:
        s = replace(
            s,
            capacity_profiles=(
                replace(s.capacity_profiles[0], assumed_efficiency=Decimal(0)),
                s.capacity_profiles[1],
            ),
        )
    row = sewing_row(assess_scenario(s))
    assert row.potential_units == 0 and not row.independent_slot_feasible
    assert "INSUFFICIENT_CAPACITY" in row.reason_codes
    if mode == "zero_efficiency":
        assert row.required_worker_minutes is row.shortfall_worker_minutes is None
        assert "ZERO_EFFICIENCY" in row.reason_codes


def test_incompatible_stage_and_style_do_not_get_hypothetical_units(planning_scenario):
    s = replace(planning_scenario, capabilities=(planning_scenario.capabilities[1],))
    report = assess_scenario(s)
    incompatible = sewing_row(report)
    assert incompatible.reason_codes == ("STYLE_NOT_SUPPORTED",)
    assert incompatible.potential_units is incompatible.shortfall_standard_minutes is None
    assert incompatible.required_worker_minutes is None
    wrong_stage = next(
        row for row in report.assessments if row.line_id == "finish" and row.stage == Stage.SEWING
    )
    assert wrong_stage.reason_codes == ("STAGE_MISMATCH",)
    assert not report.orders[0].all_stages_have_independent_slot


def test_independent_orders_never_reserve_or_double_sum_capacity(planning_scenario):
    first = assess_scenario(planning_scenario)
    scenario = replace(
        planning_scenario,
        orders=(
            planning_scenario.orders[0],
            replace(planning_scenario.orders[0], order_id="second", priority=5),
        ),
    )
    report = assess_scenario(scenario)
    assert report.slots == first.slots  # Slot inventory appears once, not once per order.
    assert all(order.all_stages_have_independent_slot for order in report.orders)
    assert report.schedule_feasibility == "NOT_ASSESSED" and report.allocation_performed is False
    assert len(report.assessments) == 2 * len(first.assessments)


def test_multiple_adjacent_shifts_and_overnight_due_boundary(planning_scenario):
    s = planning_scenario
    shift = Shift(
        "evening",
        TimeInterval(s.shifts[0].interval.end, datetime.fromisoformat("2030-01-08T00:00:00+03:00")),
        (),
    )
    s = replace(
        s,
        shifts=(*s.shifts, shift),
        calendar=replace(
            s.calendar,
            assignments=(
                *s.calendar.assignments,
                ShiftAssignment("a-evening", "sew", "evening", "p-sew"),
            ),
        ),
    )
    report = assess_scenario(s)
    evening = next(
        row
        for row in report.assessments
        if row.assignment_id == "a-evening" and row.stage == Stage.SEWING
    )
    assert evening.independent_slot_feasible
    assert len(report.slots) == 3


@pytest.mark.parametrize(
    "mode,reason", [("release", "BEFORE_RELEASE_DATE"), ("due", "AFTER_DUE_DATE")]
)
def test_full_slot_must_be_inside_order_date_window(planning_scenario, mode, reason):
    s = planning_scenario
    day = s.orders[0].due_date
    changes = (
        {"release_date": day + timedelta(days=1), "due_date": day + timedelta(days=1)}
        if mode == "release"
        else {"release_date": day - timedelta(days=1), "due_date": day - timedelta(days=1)}
    )
    report = assess_scenario(replace(s, orders=(replace(s.orders[0], **changes),)))
    assert reason in sewing_row(report).reason_codes
    assert not sewing_row(report).independent_slot_feasible


def test_empty_calendar_explains_missing_slots(planning_scenario):
    s = replace(planning_scenario, calendar=replace(planning_scenario.calendar, assignments=()))
    report = assess_scenario(s)
    assert report.slots == report.assessments == ()
    assert not report.orders[0].all_stages_have_independent_slot
    assert all(
        check.reason_codes == ("NO_CALENDAR_ASSIGNMENTS",)
        for check in report.orders[0].stage_checks
    )


def test_unavailable_periods_intersect_shift_and_ignore_outside_time(planning_scenario):
    shift = planning_scenario.shifts[0]
    available = shift_availability(
        shift,
        line_available=True,
        unavailable_periods=(time_span("07:00", "09:00"), time_span("16:00", "18:00")),
    )
    assert available.unavailable_additional_minutes == 60
    assert available.available_elapsed_minutes == 390
    with pytest.raises(PlanningError, match="cannot exceed"):
        shift_availability(
            shift, line_available=True, planned_downtime=(time_span("07:00", "09:00"),)
        )


def test_interval_union_offset_and_input_order_invariance():
    intervals = [
        time_span("08:00", "10:00"),
        time_span("09:00", "11:00"),
        time_span("11:00", "11:00"),
    ]
    equivalent = TimeInterval(
        datetime.fromisoformat("2030-01-07T05:00:00Z"),
        datetime.fromisoformat("2030-01-07T07:00:00Z"),
    )
    assert union_minutes(intervals) == union_minutes(list(reversed(intervals))) == 180
    assert union_minutes([*intervals, equivalent]) == 180
    assert union_minutes([]) == 0


def test_decimal_floor_boundary_and_context_independence(planning_scenario):
    s = planning_scenario
    style = replace(
        s.styles[0],
        standards=(
            replace(s.styles[0].standards[0], standard_minutes_per_unit=Decimal("0.3")),
            *s.styles[0].standards[1:],
        ),
    )
    s = replace(s, styles=(style,))
    expected = assess_scenario(s)
    assert sewing_row(expected).potential_units == 4800
    with localcontext() as context:
        context.prec = 3
        assert assess_scenario(s) == expected
    output = report_to_dict(expected)
    assert output["quantity_unit"] == "piece" and output["labor_unit"] == "worker_minute"
    assert all(isinstance(slot["available_worker_minutes"], str) for slot in output["slots"])


def test_demand_functions_reject_wrong_style_and_stage(planning_scenario):
    s = planning_scenario
    with pytest.raises(PlanningError):
        required_standard_minutes(s.orders[0], replace(s.styles[0], style_id="other"), Stage.SEWING)
    with pytest.raises(PlanningError):
        required_standard_minutes(s.orders[0], s.styles[0], Stage.PACKING)
    with pytest.raises(PlanningError):
        required_worker_minutes(Decimal(-1), s.capacity_profiles[0])


def test_microsecond_break_partition_cannot_create_negative_capacity():
    start = datetime.fromisoformat("2030-01-07T08:00:00+03:00")
    breaks = tuple(
        TimeInterval(start + timedelta(microseconds=i), start + timedelta(microseconds=i + 1))
        for i in range(3)
    )
    shift = Shift("microsecond", TimeInterval(start, start + timedelta(microseconds=3)), breaks)
    assert shift.break_minutes == shift.interval.minutes
    assert shift.effective_working_minutes == 0
    assert shift_availability(shift, line_available=True).available_elapsed_minutes == 0
