"""Validated immutable entities; quantities are pieces and standards are labor minutes."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Context, Decimal, localcontext
from enum import StrEnum
from typing import Literal

from loometric.planning.validation import (
    PlanningError,
    calendar_date,
    decimal,
    enum_value,
    integer,
    members,
    text,
    utc,
)

ARITHMETIC_CONTEXT = Context(prec=28)


class Stage(StrEnum):
    CUTTING = "cutting"
    SEWING = "sewing"
    FINISHING = "finishing"
    QUALITY_CONTROL = "quality_control"
    PACKING = "packing"


class AvailabilityStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class EvidenceStatus(StrEnum):
    SYNTHETIC = "synthetic"
    VERIFIED = "verified"


@dataclass(frozen=True)
class TimeInterval:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if utc(self.end) < utc(self.start):
            raise PlanningError("INVALID_INTERVAL", "Interval end cannot precede start.")

    @property
    def minutes(self) -> Decimal:
        elapsed = utc(self.end) - utc(self.start)
        microseconds = (elapsed.days * 86400 + elapsed.seconds) * 1000000 + elapsed.microseconds
        with localcontext(ARITHMETIC_CONTEXT):
            return Decimal(microseconds) / Decimal(60000000)

    def contains(self, other: "TimeInterval") -> bool:
        return utc(self.start) <= utc(other.start) <= utc(other.end) <= utc(self.end)

    def overlaps(self, other: "TimeInterval") -> bool:
        return max(utc(self.start), utc(other.start)) < min(utc(self.end), utc(other.end))


@dataclass(frozen=True)
class StageStandard:
    stage: Stage
    standard_minutes_per_unit: Decimal
    measurement_unit: Literal["worker_minutes_per_piece"] = "worker_minutes_per_piece"

    def __post_init__(self) -> None:
        enum_value(self.stage, Stage, "stage")
        decimal(self.standard_minutes_per_unit, "standard_minutes_per_unit", positive=True)
        if self.measurement_unit != "worker_minutes_per_piece":
            raise PlanningError("UNSUPPORTED_UNIT", "Standards must be worker_minutes_per_piece.")


@dataclass(frozen=True)
class ProductStyle:
    style_id: str
    standards: tuple[StageStandard, ...]
    output_unit: Literal["piece"] = "piece"

    def __post_init__(self) -> None:
        text(self.style_id, "style_id")
        members(self.standards, StageStandard, "standards", nonempty=True)
        if len({standard.stage for standard in self.standards}) != len(self.standards):
            raise PlanningError(
                "DUPLICATE_STAGE", "A style has exactly one standard per eligible stage."
            )
        if self.output_unit != "piece":
            raise PlanningError("UNSUPPORTED_UNIT", "Only piece quantities are supported.")

    @property
    def eligible_stages(self) -> tuple[Stage, ...]:
        return tuple(standard.stage for standard in self.standards)

    def standard_for(self, stage: Stage) -> Decimal:
        for standard in self.standards:
            if standard.stage == stage:
                return standard.standard_minutes_per_unit
        raise PlanningError(
            "STYLE_STAGE_UNSUPPORTED", f"Style {self.style_id} has no {stage} standard."
        )


@dataclass(frozen=True)
class ProductionOrder:
    order_id: str
    style_id: str
    quantity: int
    priority: int
    release_date: date
    due_date: date
    required_stages: tuple[Stage, ...]

    def __post_init__(self) -> None:
        text(self.order_id, "order_id")
        text(self.style_id, "style_id")
        integer(self.quantity, "quantity", minimum=1)
        integer(self.priority, "priority", minimum=1)
        calendar_date(self.release_date, "release_date")
        calendar_date(self.due_date, "due_date")
        if self.release_date > self.due_date:
            raise PlanningError("INVALID_ORDER_DATES", "Release date cannot follow due date.")
        members(self.required_stages, Stage, "required_stages", nonempty=True)
        if len(set(self.required_stages)) != len(self.required_stages):
            raise PlanningError(
                "DUPLICATE_STAGE", "Stage revisits/rework are not supported in M02."
            )


@dataclass(frozen=True)
class ProductionLine:
    line_id: str
    stage: Stage
    worker_count: int
    availability: AvailabilityStatus

    def __post_init__(self) -> None:
        text(self.line_id, "line_id")
        enum_value(self.stage, Stage, "stage")
        integer(self.worker_count, "worker_count")
        enum_value(self.availability, AvailabilityStatus, "availability")


@dataclass(frozen=True)
class LineCapability:
    capability_id: str
    line_id: str
    style_id: str
    stage: Stage
    workforce_basis: str

    def __post_init__(self) -> None:
        for name in ("capability_id", "line_id", "style_id", "workforce_basis"):
            text(getattr(self, name), name)
        enum_value(self.stage, Stage, "stage")


@dataclass(frozen=True)
class Shift:
    shift_id: str
    interval: TimeInterval
    breaks: tuple[TimeInterval, ...]

    def __post_init__(self) -> None:
        text(self.shift_id, "shift_id")
        if not isinstance(self.interval, TimeInterval) or self.interval.minutes <= 0:
            raise PlanningError("INVALID_SHIFT", "Shift requires a positive elapsed interval.")
        members(self.breaks, TimeInterval, "breaks")
        for number, interval in enumerate(self.breaks):
            if not self.interval.contains(interval):
                raise PlanningError("BREAK_OUTSIDE_SHIFT", "Break must be contained in its shift.")
            if any(interval.overlaps(previous) for previous in self.breaks[:number]):
                raise PlanningError("OVERLAPPING_BREAKS", "Break intervals cannot overlap.")

    @property
    def break_minutes(self) -> Decimal:
        with localcontext(ARITHMETIC_CONTEXT):
            return sum((interval.minutes for interval in self.breaks), Decimal(0))

    @property
    def effective_working_minutes(self) -> Decimal:
        """Elapsed minutes after explicit breaks, before downtime/crew/efficiency."""
        with localcontext(ARITHMETIC_CONTEXT):
            return self.interval.minutes - self.break_minutes


@dataclass(frozen=True)
class CapacityProfile:
    profile_id: str
    line_id: str
    effective_date: date
    assumed_efficiency: Decimal
    source_id: str
    evidence_status: EvidenceStatus
    evidence_reference: str | None = None

    def __post_init__(self) -> None:
        for name in ("profile_id", "line_id", "source_id"):
            text(getattr(self, name), name)
        calendar_date(self.effective_date, "effective_date")
        decimal(self.assumed_efficiency, "assumed_efficiency")
        if self.assumed_efficiency > 1:
            raise PlanningError(
                "INVALID_EFFICIENCY", "Capacity derating fraction must be in [0, 1]."
            )
        enum_value(self.evidence_status, EvidenceStatus, "evidence_status")
        if self.evidence_reference is not None:
            text(self.evidence_reference, "evidence_reference")
        if self.evidence_status == EvidenceStatus.VERIFIED and self.evidence_reference is None:
            raise PlanningError(
                "MISSING_EVIDENCE", "Verified status requires an evidence reference."
            )


@dataclass(frozen=True)
class ShiftAssignment:
    assignment_id: str
    line_id: str
    shift_id: str
    profile_id: str

    def __post_init__(self) -> None:
        for name in ("assignment_id", "line_id", "shift_id", "profile_id"):
            text(getattr(self, name), name)


@dataclass(frozen=True)
class PlannedDowntime:
    downtime_id: str
    assignment_id: str
    interval: TimeInterval
    reason: str

    def __post_init__(self) -> None:
        for name in ("downtime_id", "assignment_id", "reason"):
            text(getattr(self, name), name)
        if not isinstance(self.interval, TimeInterval):
            raise PlanningError("INVALID_INTERVAL", "Downtime requires an explicit interval.")


@dataclass(frozen=True)
class UnavailablePeriod:
    period_id: str
    line_id: str
    interval: TimeInterval
    reason: str

    def __post_init__(self) -> None:
        for name in ("period_id", "line_id", "reason"):
            text(getattr(self, name), name)
        if not isinstance(self.interval, TimeInterval):
            raise PlanningError("INVALID_INTERVAL", "Unavailability requires an explicit interval.")


@dataclass(frozen=True)
class ProductionCalendar:
    calendar_id: str
    working_dates: tuple[date, ...]
    assignments: tuple[ShiftAssignment, ...]
    planned_downtime: tuple[PlannedDowntime, ...]
    unavailable_periods: tuple[UnavailablePeriod, ...]

    def __post_init__(self) -> None:
        text(self.calendar_id, "calendar_id")
        members(self.working_dates, date, "working_dates")
        for day in self.working_dates:
            calendar_date(day, "working_dates")
        if len(set(self.working_dates)) != len(self.working_dates):
            raise PlanningError("DUPLICATE_DATE", "Calendar working dates must be unique.")
        members(self.assignments, ShiftAssignment, "assignments")
        members(self.planned_downtime, PlannedDowntime, "planned_downtime")
        members(self.unavailable_periods, UnavailablePeriod, "unavailable_periods")
