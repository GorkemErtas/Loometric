"""Solver-independent feasibility gate. Never imports or trusts a dispatcher."""

from collections import Counter, defaultdict
from dataclasses import dataclass

from loometric.planning.domain import Stage
from loometric.planning.validation import PlanningError, utc
from loometric.scheduling.contracts import (
    OperationAllocation,
    ProposedSchedule,
    SchedulingInstance,
    instance_fingerprint,
    on_grid,
)
from loometric.scheduling.resources import build_slots, eligible, processing_requirement


@dataclass(frozen=True)
class Violation:
    code: str
    message: str
    order_id: str | None = None
    stage: Stage | None = None
    assignment_id: str | None = None


@dataclass(frozen=True)
class VerificationResult:
    feasible: bool
    complete: bool
    violations: tuple[Violation, ...]

    @property
    def status(self) -> str:
        return (
            "INVALID"
            if not self.feasible
            else "VALID_COMPLETE"
            if self.complete
            else "VALID_PARTIAL"
        )


def verify_schedule(instance: SchedulingInstance, schedule: ProposedSchedule) -> VerificationResult:
    """Rebuild availability/requirements from the instance and check an arbitrary proposal.

    Unscheduled reason labels are diagnostics, not mathematical infeasibility proofs.
    A valid partial proposal need not be maximal or achieve the dispatcher's order.
    """
    violations: list[Violation] = []
    if (
        schedule.instance_id != instance.instance_id
        or schedule.instance_fingerprint != instance_fingerprint(instance)
    ):
        violations.append(
            Violation("INSTANCE_MISMATCH", "Schedule is not bound to these exact versioned inputs.")
        )
    orders = {order.order_id: order for order in instance.planning.orders}
    expected = {
        (order.order_id, stage)
        for order in instance.planning.orders
        for stage in order.required_stages
    }
    counts = Counter(item.key for item in (*schedule.allocations, *schedule.unscheduled))
    allocations: dict[tuple[str, Stage], list[OperationAllocation]] = defaultdict(list)
    by_line: dict[str, list[OperationAllocation]] = defaultdict(list)
    slots = {slot.assignment.assignment_id: slot for slot in build_slots(instance)}

    def issue(code: str, message: str, item: OperationAllocation) -> None:
        violations.append(Violation(code, message, item.order_id, item.stage, item.assignment_id))

    for item in (*schedule.allocations, *schedule.unscheduled):
        if item.key not in expected:
            violations.append(
                Violation(
                    "UNKNOWN_OPERATION",
                    "Order/stage is not required by this instance.",
                    item.order_id,
                    item.stage,
                )
            )
        elif item.quantity != orders[item.order_id].quantity:
            violations.append(
                Violation(
                    "QUANTITY_MISMATCH",
                    "Full order quantity is required; partial batches are unsupported.",
                    item.order_id,
                    item.stage,
                )
            )
    for key in sorted(expected):
        if counts[key] == 0:
            violations.append(
                Violation(
                    "UNREPORTED_OPERATION",
                    "Required stage is neither allocated nor explicitly unscheduled.",
                    *key,
                )
            )
        elif counts[key] > 1:
            violations.append(
                Violation(
                    "DUPLICATE_OPERATION",
                    "An operation must appear once; splitting/duplicate reporting is unsupported.",
                    *key,
                )
            )

    for allocation in schedule.allocations:
        allocations[allocation.key].append(allocation)
        slot = slots.get(allocation.assignment_id)
        if slot is None:
            issue(
                "UNKNOWN_ASSIGNMENT",
                "Allocation references an unknown calendar assignment.",
                allocation,
            )
            continue
        by_line[slot.line.line_id].append(allocation)
        if (allocation.line_id, allocation.shift_id, allocation.profile_id) != (
            slot.line.line_id,
            slot.shift.shift_id,
            slot.profile.profile_id,
        ):
            issue(
                "ASSIGNMENT_REFERENCE_MISMATCH",
                "Reported line/shift/profile differs from the assignment.",
                allocation,
            )
        if not on_grid(allocation.interval.start) or not on_grid(allocation.interval.end):
            issue(
                "TIME_GRID_VIOLATION",
                "Allocation boundaries must align to whole UTC minutes.",
                allocation,
            )
        if not instance.horizon.contains(allocation.interval):
            issue("OUTSIDE_HORIZON", "Allocation lies outside the scheduling horizon.", allocation)
        if not slot.shift.interval.contains(allocation.interval):
            issue("OUTSIDE_SHIFT", "An operation cannot span shifts.", allocation)
        if not any(window.contains(allocation.interval) for window in slot.working_intervals):
            issue(
                "UNAVAILABLE_INTERVAL",
                "Allocation crosses a break, downtime, unavailable period or horizon boundary.",
                allocation,
            )
        order = orders.get(allocation.order_id)
        if order is None or allocation.stage not in order.required_stages:
            continue
        if utc(allocation.interval.start) < instance.release_at(order.release_date):
            issue(
                "BEFORE_RELEASE", "Allocation starts before the hard release timestamp.", allocation
            )
        if not eligible(instance, order, allocation.stage, slot):
            issue(
                "INCOMPATIBLE_LINE_STAGE",
                "No exact declared line/style/stage capability.",
                allocation,
            )
            continue
        try:
            requirement = processing_requirement(instance, order, allocation.stage, slot)
        except PlanningError as exc:
            issue(exc.code, str(exc), allocation)
            continue
        if allocation.interval.minutes != requirement.duration_minutes:
            issue(
                "PROCESSING_DURATION_MISMATCH",
                "Elapsed time differs from exact upward-rounded processing requirement.",
                allocation,
            )
        if allocation.required_standard_minutes != requirement.required_standard_minutes:
            issue(
                "STANDARD_DEMAND_MISMATCH",
                "Reported standard work differs from the instance's quantity and stage standard.",
                allocation,
            )
        if allocation.consumed_worker_minutes != requirement.consumed_worker_minutes:
            issue(
                "WORKER_MINUTES_MISMATCH",
                "Reported raw labor differs from reserved time times dedicated workers.",
                allocation,
            )
        if allocation.consumed_standard_minutes != requirement.consumed_standard_minutes:
            issue(
                "STANDARD_CAPACITY_MISMATCH",
                "Reported standard capacity differs from reserved labor times efficiency.",
                allocation,
            )

    for line_id in sorted(by_line):
        entries = sorted(
            by_line[line_id],
            key=lambda item: (utc(item.interval.start), utc(item.interval.end), item.key),
        )
        for position, current in enumerate(entries):
            for previous in entries[:position]:
                if previous.interval.overlaps(current.interval):
                    issue(
                        "RESOURCE_OVERLAP",
                        f"Line {line_id} is also reserved by {previous.order_id}/{previous.stage}.",
                        current,
                    )
    for order in sorted(instance.planning.orders, key=lambda order: order.order_id):
        for previous_stage, stage in zip(
            order.required_stages[:-1], order.required_stages[1:], strict=True
        ):
            current = allocations.get((order.order_id, stage), [])
            if len(current) != 1:
                continue
            previous = allocations.get((order.order_id, previous_stage), [])
            if len(previous) != 1:
                issue(
                    "MISSING_PREDECESSOR",
                    "A scheduled stage requires its full predecessor operation.",
                    current[0],
                )
            elif utc(previous[0].interval.end) > utc(current[0].interval.start):
                issue(
                    "PRECEDENCE_VIOLATION",
                    "Predecessor must finish before the next stage starts.",
                    current[0],
                )
    feasible = not violations
    return VerificationResult(feasible, feasible and not schedule.unscheduled, tuple(violations))
