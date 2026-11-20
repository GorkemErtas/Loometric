"""Aggregate validation: references, explicit capabilities and complete calendars."""

from dataclasses import dataclass
from typing import TypeVar

from loometric.planning.domain import (
    CapacityProfile,
    LineCapability,
    ProductionCalendar,
    ProductionLine,
    ProductionOrder,
    ProductStyle,
    Shift,
)
from loometric.planning.validation import PlanningError, integer, members, text

T = TypeVar("T")


def index_by(items: tuple[T, ...], attribute: str) -> dict[str, T]:
    result: dict[str, T] = {}
    for item in items:
        key = getattr(item, attribute)
        if key in result:
            raise PlanningError("DUPLICATE_IDENTIFIER", f"Duplicate {attribute}: {key}")
        result[key] = item
    return result


def reference(mapping: dict[str, T], key: str, kind: str) -> T:
    if key not in mapping:
        raise PlanningError("UNKNOWN_REFERENCE", f"Unknown {kind}: {key}")
    return mapping[key]


@dataclass(frozen=True)
class PlanningScenario:
    scenario_id: str
    synthetic: bool
    assumptions: tuple[str, ...]
    styles: tuple[ProductStyle, ...]
    orders: tuple[ProductionOrder, ...]
    lines: tuple[ProductionLine, ...]
    shifts: tuple[Shift, ...]
    capacity_profiles: tuple[CapacityProfile, ...]
    capabilities: tuple[LineCapability, ...]
    calendar: ProductionCalendar
    schema_version: int = 1

    def __post_init__(self) -> None:
        text(self.scenario_id, "scenario_id")
        integer(self.schema_version, "schema_version", minimum=1)
        if self.schema_version != 1:
            raise PlanningError("SCHEMA_MISMATCH", "Supported planning schema version is 1.")
        if type(self.synthetic) is not bool:
            raise PlanningError("INVALID_SYNTHETIC_FLAG", "synthetic must be an explicit boolean.")
        members(self.assumptions, str, "assumptions", nonempty=True)
        for assumption in self.assumptions:
            text(assumption, "assumption")
        for name, item_type in (
            ("styles", ProductStyle),
            ("orders", ProductionOrder),
            ("lines", ProductionLine),
            ("shifts", Shift),
            ("capacity_profiles", CapacityProfile),
            ("capabilities", LineCapability),
        ):
            members(
                getattr(self, name), item_type, name, nonempty=name in ("styles", "orders", "lines")
            )
        if not isinstance(self.calendar, ProductionCalendar):
            raise PlanningError("INVALID_CALENDAR", "Scenario requires a ProductionCalendar.")
        validate_scenario(self)


def validate_scenario(scenario: PlanningScenario) -> None:
    styles = index_by(scenario.styles, "style_id")
    index_by(scenario.orders, "order_id")
    lines = index_by(scenario.lines, "line_id")
    shifts = index_by(scenario.shifts, "shift_id")
    profiles = index_by(scenario.capacity_profiles, "profile_id")
    index_by(scenario.capabilities, "capability_id")
    assignments = index_by(scenario.calendar.assignments, "assignment_id")
    index_by(scenario.calendar.planned_downtime, "downtime_id")
    index_by(scenario.calendar.unavailable_periods, "period_id")
    for order in scenario.orders:
        style = reference(styles, order.style_id, "style")
        if set(order.required_stages) - set(style.eligible_stages):
            raise PlanningError(
                "STYLE_STAGE_UNSUPPORTED", f"Order {order.order_id} requires unsupported stages."
            )
    seen_capabilities: set[tuple[str, str, str]] = set()
    for capability in scenario.capabilities:
        line = reference(lines, capability.line_id, "line")
        style = reference(styles, capability.style_id, "style")
        if capability.stage != line.stage or capability.stage not in style.eligible_stages:
            raise PlanningError(
                "CAPABILITY_STAGE_MISMATCH", "Capability must match its line and style stage."
            )
        key = (line.line_id, style.style_id, capability.stage)
        if key in seen_capabilities:
            raise PlanningError("DUPLICATE_CAPABILITY", "Repeated line/style/stage capability.")
        seen_capabilities.add(key)
    for profile in scenario.capacity_profiles:
        reference(lines, profile.line_id, "profile line")
        if scenario.synthetic and profile.evidence_status != "synthetic":
            raise PlanningError(
                "INCONSISTENT_EVIDENCE", "Synthetic scenarios must label profiles synthetic."
            )
    by_line: dict[str, list[Shift]] = {}
    for assignment in scenario.calendar.assignments:
        reference(lines, assignment.line_id, "assignment line")
        shift = reference(shifts, assignment.shift_id, "shift")
        profile = reference(profiles, assignment.profile_id, "capacity profile")
        if profile.line_id != assignment.line_id:
            raise PlanningError(
                "PROFILE_LINE_MISMATCH", "Assigned capacity profile belongs to another line."
            )
        if profile.effective_date > shift.interval.start.date():
            raise PlanningError(
                "PROFILE_NOT_EFFECTIVE", "Capacity profile is not yet effective at shift start."
            )
        if shift.interval.start.date() not in scenario.calendar.working_dates:
            raise PlanningError(
                "NONWORKING_DATE", "Assigned shift must start on an explicit working date."
            )
        if any(
            shift.interval.overlaps(previous.interval)
            for previous in by_line.get(assignment.line_id, [])
        ):
            raise PlanningError(
                "OVERLAPPING_ASSIGNMENTS", "Shift assignments on the same line cannot overlap."
            )
        by_line.setdefault(assignment.line_id, []).append(shift)
    for downtime in scenario.calendar.planned_downtime:
        assignment = reference(assignments, downtime.assignment_id, "downtime assignment")
        shift = shifts[assignment.shift_id]
        if not shift.interval.contains(downtime.interval):
            raise PlanningError(
                "DOWNTIME_OUTSIDE_SHIFT", "Planned downtime must lie within its assigned shift."
            )
    for period in scenario.calendar.unavailable_periods:
        reference(lines, period.line_id, "unavailable line")
