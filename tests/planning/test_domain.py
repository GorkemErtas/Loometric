"""Entity, unit, reference and calendar invariants before capacity calculation."""

from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

import pytest

from loometric.planning.domain import (
    EvidenceStatus,
    PlannedDowntime,
    ProductStyle,
    Shift,
    ShiftAssignment,
    Stage,
    StageStandard,
    TimeInterval,
    UnavailablePeriod,
)
from loometric.planning.validation import PlanningError


def test_explicit_units_route_and_break_minutes(planning_scenario):
    style = planning_scenario.styles[0]
    assert style.output_unit == "piece"
    assert style.standard_for(Stage.SEWING) == Decimal(12)
    assert style.eligible_stages == (Stage.SEWING, Stage.FINISHING)
    assert planning_scenario.orders[0].required_stages == (Stage.SEWING, Stage.FINISHING)
    shift = planning_scenario.shifts[0]
    assert shift.break_minutes == Decimal(30)
    assert shift.effective_working_minutes == Decimal(450)


@pytest.mark.parametrize(
    "field,value",
    [
        ("order_id", ""),
        ("order_id", " x"),
        ("style_id", "a\nb"),
        ("quantity", 0),
        ("quantity", -1),
        ("quantity", True),
        ("quantity", 1.5),
        ("priority", 0),
        ("priority", True),
        ("release_date", "2030-01-07"),
        ("release_date", datetime(2030, 1, 7)),
        ("due_date", date(2029, 1, 1)),
        ("required_stages", ()),
        ("required_stages", [Stage.SEWING]),
        ("required_stages", ("sewing",)),
        ("required_stages", (Stage.SEWING, Stage.SEWING)),
    ],
)
def test_invalid_orders(planning_scenario, field, value):
    with pytest.raises(PlanningError):
        replace(planning_scenario.orders[0], **{field: value})


@pytest.mark.parametrize(
    "value", [Decimal(0), Decimal(-1), Decimal("NaN"), Decimal("Infinity"), 1.5]
)
def test_positive_finite_decimal_standards(value):
    with pytest.raises(PlanningError):
        StageStandard(Stage.SEWING, value)


@pytest.mark.parametrize("unit", ["elapsed_minutes_per_piece", "hours", "worker_minutes"])
def test_no_implicit_unit_conversion(unit):
    with pytest.raises(PlanningError, match="worker_minutes_per_piece"):
        StageStandard(Stage.SEWING, Decimal(12), unit)


def test_duplicate_style_stage_and_unsupported_output_unit(planning_scenario):
    standard = planning_scenario.styles[0].standards[0]
    with pytest.raises(PlanningError):
        ProductStyle("A", (standard, standard))
    with pytest.raises(PlanningError):
        ProductStyle("A", (standard,), output_unit="kilogram")


@pytest.mark.parametrize(
    "field,value",
    [
        ("worker_count", -1),
        ("worker_count", 2.5),
        ("worker_count", True),
        ("availability", "available"),
        ("stage", "sewing"),
    ],
)
def test_line_validation(planning_scenario, field, value):
    with pytest.raises(PlanningError):
        replace(planning_scenario.lines[0], **{field: value})


@pytest.mark.parametrize("value", [Decimal("-0.1"), Decimal("1.01"), Decimal("NaN"), 0.8])
def test_invalid_efficiency(planning_scenario, value):
    with pytest.raises(PlanningError):
        replace(planning_scenario.capacity_profiles[0], assumed_efficiency=value)


def test_efficiency_endpoints_and_evidence_status(planning_scenario):
    profile = planning_scenario.capacity_profiles[0]
    for value in (Decimal(0), Decimal(1)):
        assert replace(profile, assumed_efficiency=value).assumed_efficiency == value
    with pytest.raises(PlanningError, match="evidence reference"):
        replace(profile, evidence_status=EvidenceStatus.VERIFIED)
    verified = replace(
        profile, evidence_status=EvidenceStatus.VERIFIED, evidence_reference="test-only:assertion"
    )
    with pytest.raises(PlanningError, match="label profiles synthetic"):
        replace(
            planning_scenario, capacity_profiles=(verified, planning_scenario.capacity_profiles[1])
        )


def test_aware_intervals_compare_instants_not_wall_clock():
    interval = TimeInterval(
        datetime.fromisoformat("2030-01-07T08:00:00+03:00"),
        datetime.fromisoformat("2030-01-07T06:00:00Z"),
    )
    assert interval.minutes == Decimal(60)
    with pytest.raises(PlanningError, match="timezone-aware"):
        TimeInterval(datetime(2030, 1, 7, 8), datetime(2030, 1, 7, 9))
    with pytest.raises(PlanningError, match="precede"):
        TimeInterval(interval.end, interval.start)
    assert TimeInterval(interval.start, interval.start).minutes == 0
    with pytest.raises(PlanningError, match="positive elapsed"):
        Shift("zero", TimeInterval(interval.start, interval.start), ())


def test_break_containment_and_overlap(planning_scenario):
    shift = planning_scenario.shifts[0]
    with pytest.raises(PlanningError, match="cannot overlap"):
        replace(shift, breaks=shift.breaks + shift.breaks)
    outside = TimeInterval(
        datetime.fromisoformat("2030-01-07T07:00:00+03:00"), shift.interval.start
    )
    with pytest.raises(PlanningError, match="contained"):
        replace(shift, breaks=(outside,))


@pytest.mark.parametrize(
    "collection", ["styles", "orders", "lines", "shifts", "capacity_profiles", "capabilities"]
)
def test_duplicate_ids(planning_scenario, collection):
    items = getattr(planning_scenario, collection)
    with pytest.raises(PlanningError) as caught:
        replace(planning_scenario, **{collection: (*items, items[0])})
    assert caught.value.code == "DUPLICATE_IDENTIFIER"


@pytest.mark.parametrize(
    "case,code",
    [
        ("order_style", "UNKNOWN_REFERENCE"),
        ("order_stage", "STYLE_STAGE_UNSUPPORTED"),
        ("capability_line", "UNKNOWN_REFERENCE"),
        ("capability_style", "UNKNOWN_REFERENCE"),
        ("capability_stage", "CAPABILITY_STAGE_MISMATCH"),
        ("duplicate_capability", "DUPLICATE_CAPABILITY"),
        ("profile_line", "UNKNOWN_REFERENCE"),
        ("assignment_line", "UNKNOWN_REFERENCE"),
        ("assignment_shift", "UNKNOWN_REFERENCE"),
        ("assignment_profile", "UNKNOWN_REFERENCE"),
        ("profile_wrong_line", "PROFILE_LINE_MISMATCH"),
        ("future_profile", "PROFILE_NOT_EFFECTIVE"),
        ("nonworking", "NONWORKING_DATE"),
        ("overlap", "OVERLAPPING_ASSIGNMENTS"),
        ("duplicate_assignment", "DUPLICATE_IDENTIFIER"),
        ("unavailable_line", "UNKNOWN_REFERENCE"),
    ],
)
def test_scenario_constraints(planning_scenario, case, code):
    s = planning_scenario
    calendar = s.calendar
    with pytest.raises(PlanningError) as caught:
        if case.startswith("order_"):
            order = replace(
                s.orders[0],
                **(
                    {"style_id": "unknown"}
                    if case == "order_style"
                    else {"required_stages": (Stage.PACKING,)}
                ),
            )
            replace(s, orders=(order,))
        elif case.startswith("capability_"):
            field = case.removeprefix("capability_")
            changes = {"stage": Stage.FINISHING} if field == "stage" else {field + "_id": "unknown"}
            replace(s, capabilities=(replace(s.capabilities[0], **changes),))
        elif case == "duplicate_capability":
            replace(
                s, capabilities=(*s.capabilities, replace(s.capabilities[0], capability_id="other"))
            )
        elif case in ("profile_line", "future_profile"):
            changes = (
                {"line_id": "unknown"}
                if case == "profile_line"
                else {"effective_date": date(2031, 1, 1)}
            )
            replace(
                s,
                capacity_profiles=(
                    replace(s.capacity_profiles[0], **changes),
                    s.capacity_profiles[1],
                ),
            )
        elif case.startswith("assignment_"):
            field = case.removeprefix("assignment_") + "_id"
            replace(
                s,
                calendar=replace(
                    calendar, assignments=(replace(calendar.assignments[0], **{field: "unknown"}),)
                ),
            )
        elif case == "profile_wrong_line":
            replace(
                s,
                calendar=replace(
                    calendar, assignments=(replace(calendar.assignments[0], profile_id="p-finish"),)
                ),
            )
        elif case == "nonworking":
            replace(s, calendar=replace(calendar, working_dates=()))
        elif case in ("overlap", "duplicate_assignment"):
            assignment = calendar.assignments[0]
            if case == "overlap":
                assignment = replace(assignment, assignment_id="another")
            replace(s, calendar=replace(calendar, assignments=(*calendar.assignments, assignment)))
        else:
            period = UnavailablePeriod(
                "unavailable", "unknown", s.shifts[0].interval, "synthetic:test"
            )
            replace(s, calendar=replace(calendar, unavailable_periods=(period,)))
    assert caught.value.code == code


def test_downtime_references_containment_and_zero_duration(planning_scenario):
    s = planning_scenario
    interval = s.shifts[0].interval
    downtime = PlannedDowntime(
        "d", "a-sew", TimeInterval(interval.start, interval.start), "synthetic:zero"
    )
    replace(s, calendar=replace(s.calendar, planned_downtime=(downtime,)))
    with pytest.raises(PlanningError) as caught:
        replace(
            s,
            calendar=replace(
                s.calendar, planned_downtime=(replace(downtime, assignment_id="missing"),)
            ),
        )
    assert caught.value.code == "UNKNOWN_REFERENCE"
    with pytest.raises(PlanningError) as caught:
        outside = TimeInterval(datetime.fromisoformat("2030-01-07T07:00:00+03:00"), interval.start)
        replace(
            s, calendar=replace(s.calendar, planned_downtime=(replace(downtime, interval=outside),))
        )
    assert caught.value.code == "DOWNTIME_OUTSIDE_SHIFT"


def test_adjacent_shifts_are_allowed(planning_scenario):
    s = planning_scenario
    first = s.shifts[0]
    second = Shift(
        "evening",
        TimeInterval(first.interval.end, datetime.fromisoformat("2030-01-08T00:00:00+03:00")),
        (),
    )
    result = replace(
        s,
        shifts=(*s.shifts, second),
        calendar=replace(
            s.calendar,
            assignments=(
                *s.calendar.assignments,
                ShiftAssignment("evening", "sew", "evening", "p-sew"),
            ),
        ),
    )
    assert len(result.calendar.assignments) == 3


def test_distinct_order_routes_are_supported(planning_scenario):
    standards = tuple(StageStandard(stage, Decimal(1)) for stage in Stage)
    style = ProductStyle("all-stages", standards)
    orders = (
        replace(
            planning_scenario.orders[0],
            order_id="cut-pack",
            style_id=style.style_id,
            required_stages=(Stage.CUTTING, Stage.PACKING),
        ),
        replace(
            planning_scenario.orders[0],
            order_id="qc",
            style_id=style.style_id,
            required_stages=(Stage.QUALITY_CONTROL,),
        ),
    )
    result = replace(planning_scenario, styles=(*planning_scenario.styles, style), orders=orders)
    assert result.orders[0].required_stages != result.orders[1].required_stages
