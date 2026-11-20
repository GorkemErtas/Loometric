"""Quality metrics for independently feasible schedules only; never an optimality gap."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, localcontext
from fractions import Fraction

from loometric.planning.availability import union_minutes
from loometric.planning.domain import ARITHMETIC_CONTEXT, Stage
from loometric.planning.validation import PlanningError, utc
from loometric.scheduling.contracts import ProposedSchedule, SchedulingInstance
from loometric.scheduling.resources import build_slots
from loometric.scheduling.verification import verify_schedule


def _decimal(value: Fraction) -> Decimal:
    with localcontext(ARITHMETIC_CONTEXT):
        return Decimal(value.numerator) / Decimal(value.denominator)


def _ratio(used: Fraction, available: Fraction) -> Decimal | None:
    return _decimal(used / available) if available else None


def _minutes(start: datetime, end: datetime) -> int:
    elapsed = utc(end) - utc(start)
    return elapsed.days * 1440 + elapsed.seconds // 60


@dataclass(frozen=True)
class OrderCompletion:
    order_id: str
    status: str
    quantity: int
    completed_units: int
    unscheduled_units: int
    allocated_stages: tuple[Stage, ...]
    completion_at: datetime | None
    tardiness_minutes: int | None
    priority_weight: int
    unscheduled_reasons: tuple[str, ...]


@dataclass(frozen=True)
class ResourceUtilization:
    assignment_id: str
    line_id: str
    shift_id: str
    stage: Stage
    available_elapsed_minutes: Decimal
    occupied_elapsed_minutes: Decimal
    line_utilization: Decimal | None
    available_worker_minutes: Decimal
    consumed_worker_minutes: Decimal
    unused_worker_minutes: Decimal
    available_standard_minutes: Decimal
    consumed_standard_minutes: Decimal
    unused_standard_minutes: Decimal
    standard_capacity_utilization: Decimal | None


@dataclass(frozen=True)
class QualityMetrics:
    scheduled_orders: int
    unscheduled_orders: int
    partial_orders: int
    scheduled_units: int
    unscheduled_units: int
    scheduled_operations: int
    unscheduled_operations: int
    allocated_stage_units: int
    on_time_completed_orders: int
    late_completed_orders: int
    total_tardiness_minutes: int
    priority_weighted_tardiness_minutes: int
    makespan_minutes: int | None
    available_line_minutes: Decimal
    occupied_line_minutes: Decimal
    line_utilization: Decimal | None
    available_worker_minutes: Decimal
    consumed_worker_minutes: Decimal
    unused_worker_minutes: Decimal
    available_standard_minutes: Decimal
    consumed_standard_minutes: Decimal
    unused_standard_minutes: Decimal
    standard_capacity_utilization: Decimal | None
    rounding_slack_standard_minutes: Decimal
    orders: tuple[OrderCompletion, ...]
    resources: tuple[ResourceUtilization, ...]
    tardiness_scope: str = "COMPLETED_ORDERS_ONLY"
    quantity_unit: str = "piece"
    elapsed_time_unit: str = "minute"
    labor_unit: str = "worker_minute"
    capacity_unit: str = "standard_worker_minute"


def calculate_metrics(instance: SchedulingInstance, schedule: ProposedSchedule) -> QualityMetrics:
    if not verify_schedule(instance, schedule).feasible:
        raise PlanningError(
            "INVALID_SCHEDULE", "Quality metrics require independent feasibility verification."
        )
    allocated = {item.key: item for item in schedule.allocations}
    un = {item.key: item for item in schedule.unscheduled}
    weight_base = max(order.priority for order in instance.planning.orders) + 1
    orders = []
    for order in sorted(instance.planning.orders, key=lambda order: order.order_id):
        stages = tuple(
            stage for stage in order.required_stages if (order.order_id, stage) in allocated
        )
        complete = len(stages) == len(order.required_stages)
        completion = (
            utc(allocated[order.order_id, order.required_stages[-1]].interval.end)
            if complete
            else None
        )
        tardiness = (
            max(0, _minutes(instance.deadline_at(order.due_date), completion))
            if completion
            else None
        )
        reasons = tuple(
            str(un[order.order_id, stage].reason)
            for stage in order.required_stages
            if (order.order_id, stage) in un
        )
        orders.append(
            OrderCompletion(
                order.order_id,
                "COMPLETED" if complete else "PARTIAL" if stages else "UNSCHEDULED",
                order.quantity,
                order.quantity if complete else 0,
                0 if complete else order.quantity,
                stages,
                completion,
                tardiness,
                weight_base - order.priority,
                reasons,
            )
        )
    resources = []
    available_time = busy_time = available_labor = used_labor = available_capacity = (
        used_capacity
    ) = Fraction(0)
    for slot in build_slots(instance):
        available = Fraction(union_minutes(slot.working_intervals))
        busy = sum(
            (
                Fraction(item.interval.minutes)
                for item in schedule.allocations
                if item.assignment_id == slot.assignment.assignment_id
            ),
            Fraction(0),
        )
        labor, consumed_labor = available * slot.line.worker_count, busy * slot.line.worker_count
        capacity, consumed_capacity = (
            labor * Fraction(slot.profile.assumed_efficiency),
            consumed_labor * Fraction(slot.profile.assumed_efficiency),
        )
        resources.append(
            ResourceUtilization(
                slot.assignment.assignment_id,
                slot.line.line_id,
                slot.shift.shift_id,
                slot.line.stage,
                _decimal(available),
                _decimal(busy),
                _ratio(busy, available),
                _decimal(labor),
                _decimal(consumed_labor),
                _decimal(labor - consumed_labor),
                _decimal(capacity),
                _decimal(consumed_capacity),
                _decimal(capacity - consumed_capacity),
                _ratio(consumed_capacity, capacity),
            )
        )
        available_time += available
        busy_time += busy
        available_labor += labor
        used_labor += consumed_labor
        available_capacity += capacity
        used_capacity += consumed_capacity
    styles = {style.style_id: style for style in instance.planning.styles}
    order_map = {order.order_id: order for order in instance.planning.orders}
    demand = sum(
        (
            Fraction(item.quantity)
            * Fraction(styles[order_map[item.order_id].style_id].standard_for(item.stage))
            for item in schedule.allocations
        ),
        Fraction(0),
    )
    makespan = (
        _minutes(
            instance.horizon.start, max(utc(item.interval.end) for item in schedule.allocations)
        )
        if schedule.allocations
        else None
    )
    return QualityMetrics(
        scheduled_orders=sum(order.status == "COMPLETED" for order in orders),
        unscheduled_orders=sum(order.status != "COMPLETED" for order in orders),
        partial_orders=sum(order.status == "PARTIAL" for order in orders),
        scheduled_units=sum(order.completed_units for order in orders),
        unscheduled_units=sum(order.unscheduled_units for order in orders),
        scheduled_operations=len(schedule.allocations),
        unscheduled_operations=len(schedule.unscheduled),
        allocated_stage_units=sum(item.quantity for item in schedule.allocations),
        on_time_completed_orders=sum(order.tardiness_minutes == 0 for order in orders),
        late_completed_orders=sum(
            order.tardiness_minutes is not None and order.tardiness_minutes > 0 for order in orders
        ),
        total_tardiness_minutes=sum(order.tardiness_minutes or 0 for order in orders),
        priority_weighted_tardiness_minutes=sum(
            (order.tardiness_minutes or 0) * order.priority_weight for order in orders
        ),
        makespan_minutes=makespan,
        available_line_minutes=_decimal(available_time),
        occupied_line_minutes=_decimal(busy_time),
        line_utilization=_ratio(busy_time, available_time),
        available_worker_minutes=_decimal(available_labor),
        consumed_worker_minutes=_decimal(used_labor),
        unused_worker_minutes=_decimal(available_labor - used_labor),
        available_standard_minutes=_decimal(available_capacity),
        consumed_standard_minutes=_decimal(used_capacity),
        unused_standard_minutes=_decimal(available_capacity - used_capacity),
        standard_capacity_utilization=_ratio(used_capacity, available_capacity),
        rounding_slack_standard_minutes=_decimal(used_capacity - demand),
        orders=tuple(orders),
        resources=tuple(resources),
    )
