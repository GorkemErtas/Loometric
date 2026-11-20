"""Frozen whole-stage-minute-v1 problem and solver-independent proposal contracts."""

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from enum import StrEnum

from loometric.planning.domain import Stage, TimeInterval
from loometric.planning.reporting import json_value
from loometric.planning.scenario import PlanningScenario
from loometric.planning.validation import (
    PlanningError,
    decimal,
    enum_value,
    integer,
    members,
    text,
    utc,
)

POLICY_VERSION = "whole-stage-minute-v1"


def on_grid(value: datetime) -> bool:
    return utc(value).second == 0 and utc(value).microsecond == 0


@dataclass(frozen=True)
class SchedulingInstance:
    instance_id: str
    planning: PlanningScenario
    horizon: TimeInterval
    calendar_utc_offset_minutes: int
    allocation_granularity_minutes: int
    schema_version: int = 1
    policy_version: str = POLICY_VERSION

    def __post_init__(self) -> None:
        text(self.instance_id, "instance_id")
        integer(self.schema_version, "schema_version", minimum=1)
        if self.schema_version != 1 or self.policy_version != POLICY_VERSION:
            raise PlanningError(
                "SCHEDULING_SCHEMA_MISMATCH", "Unsupported scheduling schema/policy."
            )
        if not isinstance(self.planning, PlanningScenario):
            raise PlanningError(
                "INVALID_PLANNING_SCENARIO", "A validated M02 scenario is required."
            )
        integer(self.allocation_granularity_minutes, "allocation_granularity_minutes", minimum=1)
        if self.allocation_granularity_minutes != 1:
            raise PlanningError(
                "UNSUPPORTED_GRANULARITY", "M03A supports exactly one-minute allocations."
            )
        integer(self.calendar_utc_offset_minutes, "calendar_utc_offset_minutes", minimum=-1439)
        if self.calendar_utc_offset_minutes > 1439:
            raise PlanningError(
                "INVALID_CALENDAR_OFFSET", "Calendar offset must be less than 24 hours."
            )
        if not isinstance(self.horizon, TimeInterval) or self.horizon.minutes <= 0:
            raise PlanningError("INVALID_HORIZON", "Horizon must have a positive aware interval.")
        intervals = [self.horizon]
        for shift in self.planning.shifts:
            if shift.interval.start.utcoffset() != timedelta(
                minutes=self.calendar_utc_offset_minutes
            ):
                raise PlanningError(
                    "CALENDAR_OFFSET_MISMATCH",
                    "Shift starts must use the declared calendar offset.",
                )
            intervals.extend((shift.interval, *shift.breaks))
        intervals.extend(item.interval for item in self.planning.calendar.planned_downtime)
        intervals.extend(item.interval for item in self.planning.calendar.unavailable_periods)
        if any(
            not on_grid(point) for interval in intervals for point in (interval.start, interval.end)
        ):
            raise PlanningError(
                "UNSUPPORTED_TIME_GRID", "All scheduling boundaries must align to UTC minutes."
            )
        for order in self.planning.orders:
            self.release_at(order.release_date)
            self.deadline_at(order.due_date)

    @property
    def calendar_timezone(self) -> timezone:
        return timezone(timedelta(minutes=self.calendar_utc_offset_minutes))

    def release_at(self, day: date) -> datetime:
        try:
            return utc(datetime.combine(day, time.min, tzinfo=self.calendar_timezone))
        except (ValueError, OverflowError) as exc:
            raise PlanningError(
                "UNSUPPORTED_DATE_RANGE", "Calendar date is outside the UTC timestamp range."
            ) from exc

    def deadline_at(self, day: date) -> datetime:
        try:
            return self.release_at(day + timedelta(days=1))
        except OverflowError as exc:
            raise PlanningError(
                "UNSUPPORTED_DATE_RANGE", "Due date requires a representable following midnight."
            ) from exc


def instance_fingerprint(instance: SchedulingInstance) -> str:
    """Hash canonical typed inputs; collection order remains part of declared identity."""
    payload = json.dumps(
        json_value(asdict(instance)), sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class OperationAllocation:
    order_id: str
    stage: Stage
    assignment_id: str
    line_id: str
    shift_id: str
    profile_id: str
    interval: TimeInterval
    quantity: int
    required_standard_minutes: Decimal
    consumed_worker_minutes: Decimal
    consumed_standard_minutes: Decimal

    def __post_init__(self) -> None:
        for name in ("order_id", "assignment_id", "line_id", "shift_id", "profile_id"):
            text(getattr(self, name), name)
        enum_value(self.stage, Stage, "stage")
        integer(self.quantity, "quantity", minimum=1)
        if not isinstance(self.interval, TimeInterval):
            raise PlanningError(
                "INVALID_INTERVAL", "Allocations require an explicit aware interval."
            )
        for name in (
            "required_standard_minutes",
            "consumed_worker_minutes",
            "consumed_standard_minutes",
        ):
            decimal(getattr(self, name), name)

    @property
    def key(self) -> tuple[str, Stage]:
        return self.order_id, self.stage


class UnscheduledReason(StrEnum):
    NO_ELIGIBLE_LINE = "NO_ELIGIBLE_LINE"
    NO_AVAILABLE_CAPACITY = "NO_AVAILABLE_CAPACITY"
    RELEASE_AFTER_HORIZON = "RELEASE_AFTER_HORIZON"
    REQUIRES_SPLITTING_OR_PREEMPTION = "REQUIRES_SPLITTING_OR_PREEMPTION"
    HORIZON_EXHAUSTED = "HORIZON_EXHAUSTED"
    CAPACITY_RESERVED = "CAPACITY_RESERVED"
    PREDECESSOR_UNSCHEDULED = "PREDECESSOR_UNSCHEDULED"


@dataclass(frozen=True)
class UnscheduledOperation:
    order_id: str
    stage: Stage
    quantity: int
    reason: UnscheduledReason

    def __post_init__(self) -> None:
        text(self.order_id, "order_id")
        enum_value(self.stage, Stage, "stage")
        integer(self.quantity, "quantity", minimum=1)
        enum_value(self.reason, UnscheduledReason, "reason")

    @property
    def key(self) -> tuple[str, Stage]:
        return self.order_id, self.stage


@dataclass(frozen=True)
class ProposedSchedule:
    instance_id: str
    instance_fingerprint: str
    allocations: tuple[OperationAllocation, ...]
    unscheduled: tuple[UnscheduledOperation, ...]
    schema_version: int = 1
    policy_version: str = POLICY_VERSION

    def __post_init__(self) -> None:
        text(self.instance_id, "instance_id")
        if not isinstance(self.instance_fingerprint, str) or not re.fullmatch(
            "[0-9a-f]{64}", self.instance_fingerprint
        ):
            raise PlanningError(
                "INVALID_FINGERPRINT", "Schedule needs a lowercase SHA-256 instance digest."
            )
        integer(self.schema_version, "schema_version", minimum=1)
        if self.schema_version != 1 or self.policy_version != POLICY_VERSION:
            raise PlanningError("SCHEDULING_SCHEMA_MISMATCH", "Unsupported result schema/policy.")
        members(self.allocations, OperationAllocation, "allocations")
        members(self.unscheduled, UnscheduledOperation, "unscheduled")
