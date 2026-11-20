"""CP-SAT values to the existing producer-neutral ProposedSchedule, without dispatch imports."""

from datetime import timedelta

from ortools.sat.python import cp_model

from loometric.optimization.model import SchedulingModel
from loometric.planning.domain import TimeInterval
from loometric.planning.validation import PlanningError, utc
from loometric.scheduling.contracts import (
    OperationAllocation,
    ProposedSchedule,
    SchedulingInstance,
    UnscheduledOperation,
    UnscheduledReason,
    instance_fingerprint,
)


def adapt_solution(
    instance: SchedulingInstance, built: SchedulingModel, solver: cp_model.CpSolver
) -> ProposedSchedule:
    origin = utc(instance.horizon.start)
    allocations, unscheduled = [], []
    for order in sorted(instance.planning.orders, key=lambda order: order.order_id):
        previous_present = True
        for stage in order.required_stages:
            operation = built.operations[order.order_id, stage]
            present = bool(solver.value(operation.present))
            selected = [a for a in operation.alternatives if solver.value(a.selected)]
            if present:
                if len(selected) != 1:
                    raise PlanningError(
                        "CP_ADAPTER_INCONSISTENCY",
                        "Present operation must select exactly one alternative.",
                    )
                alternative = selected[0].specification
                slot, requirement = alternative.slot, alternative.requirement
                span = TimeInterval(
                    origin + timedelta(minutes=solver.value(operation.start)),
                    origin + timedelta(minutes=solver.value(operation.end)),
                )
                allocations.append(
                    OperationAllocation(
                        order.order_id,
                        stage,
                        slot.assignment.assignment_id,
                        slot.line.line_id,
                        slot.shift.shift_id,
                        slot.profile.profile_id,
                        span,
                        order.quantity,
                        requirement.required_standard_minutes,
                        requirement.consumed_worker_minutes,
                        requirement.consumed_standard_minutes,
                    )
                )
            else:
                if selected:
                    raise PlanningError(
                        "CP_ADAPTER_INCONSISTENCY", "Absent operation cannot select alternatives."
                    )
                reason = (
                    UnscheduledReason.PREDECESSOR_UNSCHEDULED
                    if not previous_present
                    else (
                        operation.specification.unavailable_reason
                        or UnscheduledReason.CAPACITY_RESERVED
                    )
                )
                unscheduled.append(
                    UnscheduledOperation(order.order_id, stage, order.quantity, reason)
                )
            previous_present = present
    return ProposedSchedule(
        instance.instance_id, instance_fingerprint(instance), tuple(allocations), tuple(unscheduled)
    )
