"""Recomputed static inputs shared by dispatchers, verifiers and future solver adapters."""

from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction

from loometric.planning.availability import subtract_intervals
from loometric.planning.domain import (
    ARITHMETIC_CONTEXT,
    AvailabilityStatus,
    CapacityProfile,
    ProductionLine,
    ProductionOrder,
    Shift,
    ShiftAssignment,
    Stage,
    TimeInterval,
)
from loometric.planning.scenario import index_by
from loometric.planning.validation import PlanningError, utc
from loometric.scheduling.contracts import SchedulingInstance


@dataclass(frozen=True)
class SchedulingSlot:
    assignment: ShiftAssignment
    line: ProductionLine
    shift: Shift
    profile: CapacityProfile
    working_intervals: tuple[TimeInterval, ...]


def build_slots(
    instance: SchedulingInstance, *, within_horizon: bool = True
) -> tuple[SchedulingSlot, ...]:
    scenario = instance.planning
    lines, shifts, profiles = (
        index_by(getattr(scenario, collection), field)
        for collection, field in (
            ("lines", "line_id"),
            ("shifts", "shift_id"),
            ("capacity_profiles", "profile_id"),
        )
    )
    slots = []
    for assignment in sorted(scenario.calendar.assignments, key=lambda a: a.assignment_id):
        line, shift, profile = (
            lines[assignment.line_id],
            shifts[assignment.shift_id],
            profiles[assignment.profile_id],
        )
        start, end = utc(shift.interval.start), utc(shift.interval.end)
        if within_horizon:
            start, end = (
                max(start, utc(instance.horizon.start)),
                min(end, utc(instance.horizon.end)),
            )
        blocked = [
            *shift.breaks,
            *(
                item.interval
                for item in scenario.calendar.planned_downtime
                if item.assignment_id == assignment.assignment_id
            ),
            *(
                item.interval
                for item in scenario.calendar.unavailable_periods
                if item.line_id == line.line_id
            ),
        ]
        if line.availability == AvailabilityStatus.UNAVAILABLE:
            blocked.append(shift.interval)
        windows = subtract_intervals(TimeInterval(start, end), blocked) if start < end else ()
        slots.append(SchedulingSlot(assignment, line, shift, profile, windows))
    return tuple(slots)


def eligible(
    instance: SchedulingInstance, order: ProductionOrder, stage: Stage, slot: SchedulingSlot
) -> bool:
    return stage == slot.line.stage and any(
        capability.line_id == slot.line.line_id
        and capability.style_id == order.style_id
        and capability.stage == stage
        for capability in instance.planning.capabilities
    )


@dataclass(frozen=True)
class ProcessingRequirement:
    duration_minutes: int
    required_standard_minutes: Decimal
    consumed_worker_minutes: Decimal
    consumed_standard_minutes: Decimal


def processing_requirement(
    instance: SchedulingInstance, order: ProductionOrder, stage: Stage, slot: SchedulingSlot
) -> ProcessingRequirement:
    """Ceil the exact rational labor requirement; no binary floats or rounded division."""
    if stage not in order.required_stages or not eligible(instance, order, stage, slot):
        raise PlanningError(
            "INCOMPATIBLE_OPERATION", "Operation is not eligible for this line/stage."
        )
    if slot.line.worker_count == 0 or slot.profile.assumed_efficiency == 0:
        raise PlanningError(
            "ZERO_PROCESSING_CAPACITY", "Zero crew or efficiency cannot process an operation."
        )
    style = next(style for style in instance.planning.styles if style.style_id == order.style_id)
    required = Fraction(order.quantity) * Fraction(style.standard_for(stage))
    rate = Fraction(slot.line.worker_count) * Fraction(slot.profile.assumed_efficiency)
    elapsed = required / rate
    minutes = (elapsed.numerator + elapsed.denominator - 1) // elapsed.denominator
    with localcontext(ARITHMETIC_CONTEXT):
        return ProcessingRequirement(
            minutes,
            Decimal(required.numerator) / Decimal(required.denominator),
            Decimal(minutes * slot.line.worker_count),
            Decimal(minutes * slot.line.worker_count) * slot.profile.assumed_efficiency,
        )
