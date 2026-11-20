"""Integer optional-interval model, with every numeric bound checked before construction."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from ortools.sat.python import cp_model

from loometric.planning.domain import ProductionOrder, Stage
from loometric.planning.validation import PlanningError, utc
from loometric.scheduling.contracts import SchedulingInstance, UnscheduledReason
from loometric.scheduling.resources import (
    ProcessingRequirement,
    SchedulingSlot,
    build_slots,
    eligible,
    processing_requirement,
)

SAFE_INTEGER = 2**53 - 1
OBJECTIVE_NAMES = ("unfinished_units", "priority_weighted_tardiness_minutes", "makespan_minutes")


def minute_offset(origin: datetime, point: datetime) -> int:
    delta = utc(point) - utc(origin)
    return delta.days * 1440 + delta.seconds // 60


def _bound(value: int, name: str) -> int:
    if abs(value) > SAFE_INTEGER:
        raise PlanningError(
            "INTEGER_RANGE_UNSUPPORTED", f"{name} exceeds the exact supported integer bound 2^53-1."
        )
    return value


@dataclass(frozen=True)
class Alternative:
    slot: SchedulingSlot
    earliest_start: int
    latest_start: int
    requirement: ProcessingRequirement


@dataclass(frozen=True)
class OperationSpec:
    order: ProductionOrder
    stage: Stage
    alternatives: tuple[Alternative, ...]
    unavailable_reason: UnscheduledReason | None

    @property
    def key(self) -> tuple[str, Stage]:
        return self.order.order_id, self.stage


@dataclass(frozen=True)
class PreparedProblem:
    horizon_minutes: int
    operations: tuple[OperationSpec, ...]
    due_offsets: dict[str, int]
    priority_weights: dict[str, int]
    tardiness_bounds: dict[str, int]
    total_units: int
    weighted_tardiness_bound: int


def prepare_problem(instance: SchedulingInstance) -> PreparedProblem:
    origin = utc(instance.horizon.start)
    horizon = _bound(minute_offset(origin, instance.horizon.end), "horizon")
    orders = sorted(instance.planning.orders, key=lambda order: order.order_id)
    total_units = _bound(sum(order.quantity for order in orders), "total finished-goods quantity")
    maximum_priority = max(order.priority for order in orders)
    weights = {
        order.order_id: _bound(maximum_priority + 1 - order.priority, "priority weight")
        for order in orders
    }
    due = {
        order.order_id: _bound(
            minute_offset(origin, instance.deadline_at(order.due_date)), "deadline offset"
        )
        for order in orders
    }
    tardiness_bounds = {
        order.order_id: _bound(max(0, horizon - due[order.order_id]), "tardiness bound")
        for order in orders
    }
    weighted_bound = _bound(
        sum(weights[key] * value for key, value in tardiness_bounds.items()),
        "aggregate weighted tardiness",
    )
    slots, full_slots = build_slots(instance), build_slots(instance, within_horizon=False)
    operations = []
    for order in orders:
        release = _bound(
            minute_offset(origin, instance.release_at(order.release_date)), "release offset"
        )
        for stage in order.required_stages:
            compatible = [
                slot
                for slot in slots
                if eligible(instance, order, stage, slot)
                and slot.line.worker_count > 0
                and slot.profile.assumed_efficiency > 0
            ]
            alternatives = []
            for slot in compatible:
                requirement = processing_requirement(instance, order, stage, slot)
                for window in slot.working_intervals:
                    start = max(0, release, minute_offset(origin, window.start))
                    end = min(horizon, minute_offset(origin, window.end))
                    if requirement.duration_minutes <= end - start:
                        alternatives.append(
                            Alternative(
                                slot, start, end - requirement.duration_minutes, requirement
                            )
                        )
            reason = None
            if not alternatives:
                if not any(
                    c.style_id == order.style_id and c.stage == stage
                    for c in instance.planning.capabilities
                ):
                    reason = UnscheduledReason.NO_ELIGIBLE_LINE
                elif release >= horizon:
                    reason = UnscheduledReason.RELEASE_AFTER_HORIZON
                else:
                    full = [
                        slot
                        for slot in full_slots
                        if eligible(instance, order, stage, slot)
                        and slot.line.worker_count > 0
                        and slot.profile.assumed_efficiency > 0
                    ]
                    if not any(slot.working_intervals for slot in full):
                        reason = UnscheduledReason.NO_AVAILABLE_CAPACITY
                    elif not any(
                        window.minutes
                        >= processing_requirement(instance, order, stage, slot).duration_minutes
                        for slot in full
                        for window in slot.working_intervals
                    ):
                        reason = UnscheduledReason.REQUIRES_SPLITTING_OR_PREEMPTION
                    else:
                        reason = UnscheduledReason.HORIZON_EXHAUSTED
            operations.append(OperationSpec(order, stage, tuple(alternatives), reason))
    return PreparedProblem(
        horizon, tuple(operations), due, weights, tardiness_bounds, total_units, weighted_bound
    )


@dataclass(frozen=True)
class AlternativeVariables:
    specification: Alternative
    selected: cp_model.IntVar


@dataclass(frozen=True)
class OperationVariables:
    specification: OperationSpec
    present: cp_model.IntVar
    start: cp_model.IntVar
    end: cp_model.IntVar
    alternatives: tuple[AlternativeVariables, ...]


@dataclass(frozen=True)
class SchedulingModel:
    model: cp_model.CpModel
    prepared: PreparedProblem
    operations: dict[tuple[str, Stage], OperationVariables]
    objectives: tuple[cp_model.IntVar, cp_model.IntVar, cp_model.IntVar]


def build_model(instance: SchedulingInstance) -> SchedulingModel:
    prepared = prepare_problem(instance)  # All numeric preflight precedes CpModel creation.
    model = cp_model.CpModel()
    horizon = prepared.horizon_minutes
    operations = {}
    by_line: dict[str, list[cp_model.IntervalVar]] = defaultdict(list)
    for index, spec in enumerate(prepared.operations):
        present = model.new_bool_var(f"present_{index}")
        start, end = (model.new_int_var(0, horizon, f"{name}_{index}") for name in ("start", "end"))
        model.add(start == 0).only_enforce_if(~present)
        model.add(end == 0).only_enforce_if(~present)
        alternatives = []
        for number, alternative in enumerate(spec.alternatives):
            selected = model.new_bool_var(f"alternative_{index}_{number}")
            model.add(start >= alternative.earliest_start).only_enforce_if(selected)
            model.add(start <= alternative.latest_start).only_enforce_if(selected)
            interval = model.new_optional_interval_var(
                start,
                alternative.requirement.duration_minutes,
                end,
                selected,
                f"interval_{index}_{number}",
            )
            by_line[alternative.slot.line.line_id].append(interval)
            alternatives.append(AlternativeVariables(alternative, selected))
        model.add(sum(alternative.selected for alternative in alternatives) == present)
        operations[spec.key] = OperationVariables(spec, present, start, end, tuple(alternatives))
    for intervals in by_line.values():
        model.add_no_overlap(intervals)
    completion_vars, tardiness_vars = {}, {}
    for order in sorted(instance.planning.orders, key=lambda order: order.order_id):
        for previous_stage, stage in zip(
            order.required_stages[:-1], order.required_stages[1:], strict=True
        ):
            previous, current = (
                operations[order.order_id, previous_stage],
                operations[order.order_id, stage],
            )
            model.add(current.present <= previous.present)
            model.add(current.start >= previous.end).only_enforce_if(current.present)
        final = operations[order.order_id, order.required_stages[-1]]
        completion_vars[order.order_id] = final.present
        bound = prepared.tardiness_bounds[order.order_id]
        raw = model.new_int_var(0, bound, f"raw_tardiness_{order.order_id}")
        tardy = model.new_int_var(0, bound, f"completed_tardiness_{order.order_id}")
        model.add_max_equality(raw, [0, final.end - prepared.due_offsets[order.order_id]])
        model.add(tardy == raw).only_enforce_if(final.present)
        model.add(tardy == 0).only_enforce_if(~final.present)
        tardiness_vars[order.order_id] = tardy
    unfinished = model.new_int_var(0, prepared.total_units, "unfinished_units")
    model.add(
        unfinished
        == sum(
            order.quantity * (1 - completion_vars[order.order_id])
            for order in instance.planning.orders
        )
    )
    weighted = model.new_int_var(0, prepared.weighted_tardiness_bound, "weighted_tardiness")
    model.add(
        weighted
        == sum(prepared.priority_weights[key] * value for key, value in tardiness_vars.items())
    )
    makespan = model.new_int_var(0, horizon, "makespan")
    model.add_max_equality(makespan, [operation.end for operation in operations.values()])
    invalid = model.validate()
    if invalid:
        raise PlanningError("CP_MODEL_INVALID", invalid)
    return SchedulingModel(model, prepared, operations, (unfinished, weighted, makespan))
