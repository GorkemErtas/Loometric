"""Half-open absolute-time interval unions; overlapping stoppages are counted once."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, localcontext

from loometric.planning.domain import ARITHMETIC_CONTEXT, Shift, TimeInterval, duration_minutes
from loometric.planning.validation import PlanningError, utc


def union_minutes(intervals: Sequence[TimeInterval]) -> Decimal:
    ordered = sorted((utc(item.start), utc(item.end)) for item in intervals)
    merged: list[TimeInterval] = []
    for start, end in ordered:
        if start == end:
            continue
        if merged and start <= merged[-1].end:
            merged[-1] = TimeInterval(merged[-1].start, max(merged[-1].end, end))
        else:
            merged.append(TimeInterval(start, end))
    return duration_minutes(sum((item.end - item.start for item in merged), timedelta()))


@dataclass(frozen=True)
class ShiftAvailability:
    gross_elapsed_minutes: Decimal
    break_minutes: Decimal
    planned_downtime_additional_minutes: Decimal
    unavailable_additional_minutes: Decimal
    blocked_union_minutes: Decimal
    available_elapsed_minutes: Decimal


def shift_availability(
    shift: Shift,
    *,
    line_available: bool,
    planned_downtime: Sequence[TimeInterval] = (),
    unavailable_periods: Sequence[TimeInterval] = (),
) -> ShiftAvailability:
    """Downtime must be contained; global unavailability is explicitly intersected."""
    if type(line_available) is not bool:
        raise PlanningError("INVALID_AVAILABILITY", "line_available must be a boolean.")
    for interval in planned_downtime:
        if not shift.interval.contains(interval):
            raise PlanningError(
                "DOWNTIME_OUTSIDE_SHIFT", "Planned downtime cannot exceed its shift."
            )
    unavailable: list[TimeInterval] = []
    for interval in unavailable_periods:
        start = max(utc(interval.start), utc(shift.interval.start))
        end = min(utc(interval.end), utc(shift.interval.end))
        if start < end:
            unavailable.append(TimeInterval(start, end))
    if not line_available:
        unavailable.append(shift.interval)
    breaks = union_minutes(shift.breaks)
    with_downtime = union_minutes((*shift.breaks, *planned_downtime))
    total_blocked = union_minutes((*shift.breaks, *planned_downtime, *unavailable))
    with localcontext(ARITHMETIC_CONTEXT):
        return ShiftAvailability(
            gross_elapsed_minutes=shift.interval.minutes,
            break_minutes=breaks,
            planned_downtime_additional_minutes=with_downtime - breaks,
            unavailable_additional_minutes=total_blocked - with_downtime,
            blocked_union_minutes=total_blocked,
            available_elapsed_minutes=shift.interval.minutes - total_blocked,
        )
