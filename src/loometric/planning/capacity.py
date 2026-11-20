"""Dimensional, independent order/stage/slot assessments; no allocation or scheduling."""

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, localcontext
from fractions import Fraction

from loometric.planning.availability import ShiftAvailability, shift_availability
from loometric.planning.domain import (
    ARITHMETIC_CONTEXT,
    AvailabilityStatus,
    CapacityProfile,
    EvidenceStatus,
    ProductionLine,
    ProductionOrder,
    ProductStyle,
    Shift,
    Stage,
)
from loometric.planning.scenario import PlanningScenario, index_by
from loometric.planning.validation import PlanningError, decimal


@dataclass(frozen=True)
class SlotCapacity:
    assignment_id: str
    line_id: str
    shift_id: str
    stage: Stage
    shift_start: str
    shift_end: str
    profile_id: str
    profile_source_id: str
    profile_evidence_status: EvidenceStatus
    profile_evidence_reference: str | None
    assumed_efficiency: Decimal
    worker_count: int
    availability: ShiftAvailability
    available_worker_minutes: Decimal
    effective_capacity_standard_minutes: Decimal


@dataclass(frozen=True)
class StageAssessment:
    order_id: str
    style_id: str
    stage: Stage
    assignment_id: str
    line_id: str
    compatible: bool
    workforce_basis: str | None
    standard_minutes_per_unit: Decimal
    required_standard_minutes: Decimal
    required_worker_minutes: Decimal | None
    potential_units: int | None
    shortfall_standard_minutes: Decimal | None
    shortfall_worker_minutes: Decimal | None
    capacity_sufficient: bool | None
    independent_slot_feasible: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class StageCheck:
    stage: Stage
    independently_sufficient_assignment_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class OrderAssessment:
    order_id: str
    style_id: str
    quantity: int
    priority: int
    release_date: str
    due_date: str
    required_stages: tuple[Stage, ...]
    required_standard_minutes_total: Decimal
    stage_checks: tuple[StageCheck, ...]
    all_stages_have_independent_slot: bool


@dataclass(frozen=True)
class PlanningReport:
    scenario_id: str
    synthetic: bool
    assumptions: tuple[str, ...]
    slots: tuple[SlotCapacity, ...]
    assessments: tuple[StageAssessment, ...]
    orders: tuple[OrderAssessment, ...]
    schema_version: int = 1
    status: str = "CAPACITY_ASSESSED"
    assessment_scope: str = "INDEPENDENT_ORDER_STAGE_SLOT"
    allocation_performed: bool = False
    schedule_feasibility: str = "NOT_ASSESSED"
    quantity_unit: str = "piece"
    elapsed_time_unit: str = "minute"
    labor_unit: str = "worker_minute"
    capacity_unit: str = "standard_worker_minute"
    limitations: tuple[str, ...] = (
        "Each order is assessed independently; capacity is never reserved or summed across orders.",
        "Stage precedence is declared, but stage timing, WIP, materials and shared "
        "resources are not scheduled.",
        "Dedicated qualified line crews and stage labor standards are scenario assumptions; "
        "no cross-line interchangeability is inferred.",
        "Efficiency is a declared capacity derating fraction, not an experimental ML prediction.",
    )


def required_standard_minutes(order: ProductionOrder, style: ProductStyle, stage: Stage) -> Decimal:
    """Pieces * standard worker-minutes/piece = standard worker-minutes for this stage."""
    if order.style_id != style.style_id or stage not in order.required_stages:
        raise PlanningError(
            "ORDER_STAGE_MISMATCH", "Demand requires the order's style and a required stage."
        )
    with localcontext(ARITHMETIC_CONTEXT):
        return Decimal(order.quantity) * style.standard_for(stage)


def required_worker_minutes(standard_minutes: Decimal, profile: CapacityProfile) -> Decimal | None:
    """Raw labor required under this profile; zero efficiency has no finite requirement."""
    decimal(standard_minutes, "standard_minutes", positive=True)
    with localcontext(ARITHMETIC_CONTEXT):
        return (
            standard_minutes / profile.assumed_efficiency
            if profile.assumed_efficiency > 0
            else None
        )


def _assess_stage(
    order: ProductionOrder,
    style: ProductStyle,
    stage: Stage,
    line: ProductionLine,
    shift: Shift,
    profile: CapacityProfile,
    slot: SlotCapacity,
    workforce_basis: str | None,
) -> StageAssessment:
    reasons: list[str] = []
    if stage != line.stage:
        reasons.append("STAGE_MISMATCH")
    elif workforce_basis is None:
        reasons.append("STYLE_NOT_SUPPORTED")
    compatible = not reasons
    if line.availability == AvailabilityStatus.UNAVAILABLE:
        reasons.append("LINE_UNAVAILABLE")
    if line.worker_count == 0:
        reasons.append("NO_WORKERS")
    if slot.availability.available_elapsed_minutes == 0:
        reasons.append("NO_WORKING_TIME")
    if profile.assumed_efficiency == 0:
        reasons.append("ZERO_EFFICIENCY")
    if shift.interval.start.date() < order.release_date:
        reasons.append("BEFORE_RELEASE_DATE")
    # Due dates include the entire local day; a slot ending at next midnight is allowed.
    end_local = shift.interval.end.astimezone(shift.interval.start.tzinfo)
    if (end_local - timedelta(microseconds=1)).date() > order.due_date:
        reasons.append("AFTER_DUE_DATE")
    demand = required_standard_minutes(order, style, stage)
    with localcontext(ARITHMETIC_CONTEXT):
        labor = required_worker_minutes(demand, profile) if compatible else None
        units = (
            int(
                Fraction(slot.effective_capacity_standard_minutes)
                // Fraction(style.standard_for(stage))
            )
            if compatible
            else None
        )
        shortfall = (
            max(Decimal(0), demand - slot.effective_capacity_standard_minutes)
            if compatible
            else None
        )
        labor_shortfall = (
            max(Decimal(0), labor - slot.available_worker_minutes) if labor is not None else None
        )
        sufficient = units >= order.quantity if units is not None else None
    if sufficient is False:
        reasons.append("INSUFFICIENT_CAPACITY")
    return StageAssessment(
        order.order_id,
        style.style_id,
        stage,
        slot.assignment_id,
        line.line_id,
        compatible,
        workforce_basis if compatible else None,
        style.standard_for(stage),
        demand,
        labor,
        units,
        shortfall,
        labor_shortfall,
        sufficient,
        not reasons,
        tuple(reasons),
    )


def assess_scenario(scenario: PlanningScenario) -> PlanningReport:
    """Each physical slot appears once; each order asks a separate hypothetical question."""
    lines = index_by(scenario.lines, "line_id")
    shifts = index_by(scenario.shifts, "shift_id")
    profiles = index_by(scenario.capacity_profiles, "profile_id")
    styles = index_by(scenario.styles, "style_id")
    capabilities = {
        (c.line_id, c.style_id, c.stage): c.workforce_basis for c in scenario.capabilities
    }
    assignments = sorted(scenario.calendar.assignments, key=lambda a: a.assignment_id)
    slots: list[SlotCapacity] = []
    for assignment in assignments:
        line, shift, profile = (
            lines[assignment.line_id],
            shifts[assignment.shift_id],
            profiles[assignment.profile_id],
        )
        available = shift_availability(
            shift,
            line_available=line.availability == AvailabilityStatus.AVAILABLE,
            planned_downtime=tuple(
                d.interval
                for d in scenario.calendar.planned_downtime
                if d.assignment_id == assignment.assignment_id
            ),
            unavailable_periods=tuple(
                p.interval
                for p in scenario.calendar.unavailable_periods
                if p.line_id == line.line_id
            ),
        )
        with localcontext(ARITHMETIC_CONTEXT):
            labor = available.available_elapsed_minutes * Decimal(line.worker_count)
            effective = labor * profile.assumed_efficiency
        slots.append(
            SlotCapacity(
                assignment.assignment_id,
                line.line_id,
                shift.shift_id,
                line.stage,
                shift.interval.start.isoformat(),
                shift.interval.end.isoformat(),
                profile.profile_id,
                profile.source_id,
                profile.evidence_status,
                profile.evidence_reference,
                profile.assumed_efficiency,
                line.worker_count,
                available,
                labor,
                effective,
            )
        )
    assessments: list[StageAssessment] = []
    orders: list[OrderAssessment] = []
    for order in sorted(scenario.orders, key=lambda o: o.order_id):
        style = styles[order.style_id]
        checks: list[StageCheck] = []
        for stage in order.required_stages:
            rows: list[StageAssessment] = []
            for assignment, slot in zip(assignments, slots, strict=True):
                row = _assess_stage(
                    order,
                    style,
                    stage,
                    lines[assignment.line_id],
                    shifts[assignment.shift_id],
                    profiles[assignment.profile_id],
                    slot,
                    capabilities.get((assignment.line_id, style.style_id, stage)),
                )
                rows.append(row)
            assessments.extend(rows)
            sufficient_slots = tuple(
                row.assignment_id for row in rows if row.independent_slot_feasible
            )
            reason = (
                ()
                if sufficient_slots
                else (
                    "NO_CALENDAR_ASSIGNMENTS"
                    if not rows
                    else "NO_COMPATIBLE_SLOT"
                    if not any(row.compatible for row in rows)
                    else "NO_SUFFICIENT_INDEPENDENT_SLOT",
                )
            )
            checks.append(StageCheck(stage, sufficient_slots, reason))
        with localcontext(ARITHMETIC_CONTEXT):
            total_demand = sum(
                (required_standard_minutes(order, style, s) for s in order.required_stages),
                Decimal(0),
            )
        orders.append(
            OrderAssessment(
                order.order_id,
                order.style_id,
                order.quantity,
                order.priority,
                order.release_date.isoformat(),
                order.due_date.isoformat(),
                order.required_stages,
                total_demand,
                tuple(checks),
                all(check.independently_sufficient_assignment_ids for check in checks),
            )
        )
    return PlanningReport(
        scenario.scenario_id,
        scenario.synthetic,
        scenario.assumptions,
        tuple(slots),
        tuple(assessments),
        tuple(orders),
    )
