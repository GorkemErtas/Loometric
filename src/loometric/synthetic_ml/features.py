"""Stateless pre-shift whitelist; features cannot read outcomes or memberships."""

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, localcontext

from loometric.planning.availability import shift_availability
from loometric.planning.domain import ARITHMETIC_CONTEXT, TimeInterval
from loometric.planning.domain import Shift as PlanningShift
from loometric.synthetic_ml.contracts import (
    Crew,
    Dataset,
    Line,
    Order,
    Outcome,
    Plan,
    Shift,
    Standard,
    Style,
    target_value,
)

FEATURE_COLUMNS = (
    "stage",
    "shift_kind",
    "weekday",
    "planned_workers",
    "skill_level",
    "style_complexity",
    "standard_worker_minutes_per_piece",
    "planned_machine_available",
    "available_minutes",
    "planned_downtime_minutes",
    "opening_wip_pieces",
    "planned_release_pieces",
    "order_quantity",
)


def available_minutes(plan: Plan, shift: Shift) -> int:
    result = shift_availability(
        PlanningShift(
            shift.shift_id,
            TimeInterval(shift.start, shift.end),
            (TimeInterval(shift.break_start, shift.break_end),),
        ),
        line_available=plan.machine_available,
        planned_downtime=(TimeInterval(plan.downtime_start, plan.downtime_end),),
    ).available_elapsed_minutes
    if result != result.to_integral_value():
        raise ValueError("Synthetic v1 uses whole elapsed minutes.")
    return int(result)


@dataclass(frozen=True)
class References:
    """One explicit set of outcome-free foreign-key indexes per materialization."""

    lines: dict[str, Line]
    crews: dict[str, Crew]
    shifts: dict[str, Shift]
    orders: dict[str, Order]
    standards: dict[str, Standard]
    styles: dict[str, Style]

    @classmethod
    def from_dataset(cls, data: Dataset) -> "References":
        return cls(
            **{
                name: {getattr(row, key): row for row in getattr(data, name)}
                for name, key in (
                    ("lines", "line_id"),
                    ("crews", "crew_id"),
                    ("shifts", "shift_id"),
                    ("orders", "order_id"),
                    ("standards", "standard_id"),
                    ("styles", "style_id"),
                )
            }
        )


def feature_row(plan: Plan, refs: References) -> dict:
    line, crew = refs.lines[plan.line_id], refs.crews[plan.crew_id]
    shift, order = refs.shifts[plan.shift_id], refs.orders[plan.order_id]
    standard, style = refs.standards[plan.standard_id], refs.styles[order.style_id]
    if any(item.available_at > plan.cutoff for item in (line, crew, shift, order, standard, style)):
        raise ValueError("Feature reference was unavailable at prediction cutoff.")
    if plan.snapshot_at > plan.cutoff or plan.cutoff >= shift.start:
        raise ValueError("Plan snapshot/cutoff must precede shift start.")
    inputs = {
        "stage": line.stage.value,
        "shift_kind": shift.kind,
        "weekday": shift.start.weekday(),
        "planned_workers": plan.planned_workers,
        "skill_level": crew.skill_level,
        "style_complexity": style.complexity,
        "standard_worker_minutes_per_piece": standard.worker_minutes_per_piece,
        "planned_machine_available": plan.machine_available,
        "available_minutes": available_minutes(plan, shift),
        "planned_downtime_minutes": (plan.downtime_end - plan.downtime_start)
        // timedelta(minutes=1),
        "opening_wip_pieces": plan.opening_wip_pieces,
        "planned_release_pieces": plan.planned_release_pieces,
        "order_quantity": order.quantity,
    }
    return {
        "observation_id": plan.observation_id,
        "cutoff": plan.cutoff,
        "context": {
            "factory_id": line.factory_id,
            "line_id": line.line_id,
            "crew_id": crew.crew_id,
            "style_id": style.style_id,
        },
        "inputs": inputs,
    }


def build_features(data: Dataset) -> tuple[dict, ...]:
    refs = References.from_dataset(data)
    return tuple(feature_row(plan, refs) for plan in data.plans)


def label_row(plan: Plan, outcome: Outcome, refs: References) -> dict:
    standard = refs.standards[plan.standard_id].worker_minutes_per_piece
    denominator = available_minutes(plan, refs.shifts[plan.shift_id]) * plan.planned_workers
    status, target = target_value(outcome.completed_good_pieces, standard, denominator)
    with localcontext(ARITHMETIC_CONTEXT):
        earned = Decimal(outcome.completed_good_pieces) * standard
    return {
        "observation_id": plan.observation_id,
        "status": status,
        "standard_capacity_attainment": target,
        "available_at": outcome.available_at,
        "planned_available_worker_minutes": denominator,
        "earned_standard_worker_minutes": earned,
    }


def training_examples(data: Dataset) -> tuple[dict, ...]:
    """Explicit train-only join. Reserved/gap/validation outcomes cannot enter it."""
    ids = {m.observation_id for m in data.membership if m.partition == "train"}
    refs = References.from_dataset(data)
    outcomes = {o.observation_id: o for o in data.outcomes if o.observation_id in ids}
    return tuple(
        {**feature_row(p, refs), "label": label_row(p, outcomes[p.observation_id], refs)}
        for p in data.plans
        if p.observation_id in ids
    )
