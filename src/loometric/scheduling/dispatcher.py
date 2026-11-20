"""Deterministic serial priority dispatcher; finite reservations and no optimality claim."""

from collections import defaultdict
from datetime import datetime, timedelta

from loometric.planning.availability import subtract_intervals
from loometric.planning.domain import ProductionOrder, Stage, TimeInterval
from loometric.planning.validation import utc
from loometric.scheduling.contracts import (
    OperationAllocation,
    ProposedSchedule,
    SchedulingInstance,
    UnscheduledOperation,
    UnscheduledReason,
    instance_fingerprint,
)
from loometric.scheduling.resources import (
    ProcessingRequirement,
    SchedulingSlot,
    build_slots,
    eligible,
    processing_requirement,
)

ALGORITHM = "serial-priority-due-id-v1"


def _earliest_interval(
    slot: SchedulingSlot,
    requirement: ProcessingRequirement,
    earliest: datetime,
    occupied: tuple[TimeInterval, ...],
) -> TimeInterval | None:
    for window in slot.working_intervals:
        for gap in subtract_intervals(window, occupied):
            start = max(utc(gap.start), utc(earliest))
            if (
                start >= utc(gap.end)
                or (utc(gap.end) - start) // timedelta(minutes=1) < requirement.duration_minutes
            ):
                continue
            return TimeInterval(start, start + timedelta(minutes=requirement.duration_minutes))
    return None


def _positive(slot: SchedulingSlot) -> bool:
    return slot.line.worker_count > 0 and slot.profile.assumed_efficiency > 0


def _failure_reason(
    instance: SchedulingInstance,
    order: ProductionOrder,
    stage: Stage,
    earliest: datetime,
    slots: tuple[SchedulingSlot, ...],
    full_slots: tuple[SchedulingSlot, ...],
) -> UnscheduledReason:
    if not any(
        c.style_id == order.style_id and c.stage == stage for c in instance.planning.capabilities
    ):
        return UnscheduledReason.NO_ELIGIBLE_LINE
    if instance.release_at(order.release_date) >= utc(instance.horizon.end):
        return UnscheduledReason.RELEASE_AFTER_HORIZON
    full = [
        slot for slot in full_slots if eligible(instance, order, stage, slot) and _positive(slot)
    ]
    if not any(slot.working_intervals for slot in full):
        return UnscheduledReason.NO_AVAILABLE_CAPACITY
    if not any(
        window.minutes >= processing_requirement(instance, order, stage, slot).duration_minutes
        for slot in full
        for window in slot.working_intervals
    ):
        return UnscheduledReason.REQUIRES_SPLITTING_OR_PREEMPTION
    if not any(
        _earliest_interval(slot, processing_requirement(instance, order, stage, slot), earliest, ())
        for slot in slots
        if eligible(instance, order, stage, slot) and _positive(slot)
    ):
        return UnscheduledReason.HORIZON_EXHAUSTED
    return UnscheduledReason.CAPACITY_RESERVED


def dispatch(instance: SchedulingInstance) -> ProposedSchedule:
    slots = build_slots(instance)
    full_slots = build_slots(instance, within_horizon=False)
    occupied: dict[str, list[TimeInterval]] = defaultdict(list)
    allocations: list[OperationAllocation] = []
    unscheduled: list[UnscheduledOperation] = []
    orders = sorted(
        instance.planning.orders, key=lambda order: (order.priority, order.due_date, order.order_id)
    )
    for order in orders:
        earliest = max(utc(instance.horizon.start), instance.release_at(order.release_date))
        blocked_predecessor = False
        for stage in order.required_stages:
            if blocked_predecessor:
                unscheduled.append(
                    UnscheduledOperation(
                        order.order_id,
                        stage,
                        order.quantity,
                        UnscheduledReason.PREDECESSOR_UNSCHEDULED,
                    )
                )
                continue
            candidates = []
            for slot in slots:
                if not eligible(instance, order, stage, slot) or not _positive(slot):
                    continue
                requirement = processing_requirement(instance, order, stage, slot)
                interval = _earliest_interval(
                    slot, requirement, earliest, tuple(occupied[slot.line.line_id])
                )
                if interval is not None:
                    key = (
                        utc(interval.start),
                        utc(interval.end),
                        slot.line.line_id,
                        slot.shift.shift_id,
                        slot.assignment.assignment_id,
                    )
                    candidates.append((key, slot, requirement, interval))
            if not candidates:
                reason = _failure_reason(instance, order, stage, earliest, slots, full_slots)
                unscheduled.append(
                    UnscheduledOperation(order.order_id, stage, order.quantity, reason)
                )
                blocked_predecessor = True
                continue
            _, slot, requirement, interval = min(candidates, key=lambda candidate: candidate[0])
            allocation = OperationAllocation(
                order.order_id,
                stage,
                slot.assignment.assignment_id,
                slot.line.line_id,
                slot.shift.shift_id,
                slot.profile.profile_id,
                interval,
                order.quantity,
                requirement.required_standard_minutes,
                requirement.consumed_worker_minutes,
                requirement.consumed_standard_minutes,
            )
            allocations.append(allocation)
            occupied[slot.line.line_id].append(interval)
            earliest = utc(interval.end)
    return ProposedSchedule(
        instance.instance_id, instance_fingerprint(instance), tuple(allocations), tuple(unscheduled)
    )
