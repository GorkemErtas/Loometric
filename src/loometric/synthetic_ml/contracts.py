"""Normalized synthetic records and exact target semantics; no trained model imports."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, localcontext
from fractions import Fraction

from loometric.planning.domain import ARITHMETIC_CONTEXT, Stage

DATASET_VERSION = "synthetic-ml-v1"
GENERATOR_VERSION = "stage-shift-process-v1"
TARGET_NAME = "standard_capacity_attainment"


def target_value(completed: int, standard: Decimal, available: int) -> tuple[str, Decimal | None]:
    """Credit completed good pieces only; denominator is frozen planned worker-minutes."""
    if type(completed) is not int or completed < 0 or type(available) is not int or available < 0:
        raise ValueError("Piece counts and available worker-minutes must be nonnegative integers.")
    if not isinstance(standard, Decimal) or not standard.is_finite() or standard <= 0:
        raise ValueError("An explicit positive finite worker-minute standard is required.")
    if not available:
        if completed:
            raise ValueError("Zero planned capacity cannot produce credited work in this policy.")
        return "ZERO_PLANNED_CAPACITY", None
    with localcontext(ARITHMETIC_CONTEXT):
        return "VALID", Decimal(completed) * standard / Decimal(available)


def exact_floor(value: Fraction) -> int:
    return value.numerator // value.denominator


@dataclass(frozen=True)
class Factory:
    factory_id: str
    utc_offset_minutes: int
    available_at: datetime


@dataclass(frozen=True)
class Line:
    line_id: str
    factory_id: str
    stage: Stage
    available_at: datetime


@dataclass(frozen=True)
class Crew:
    crew_id: str
    line_id: str
    shift_kind: str
    qualified_stage: Stage
    roster_size: int
    skill_level: int
    available_at: datetime


@dataclass(frozen=True)
class Style:
    style_id: str
    complexity: int
    available_at: datetime


@dataclass(frozen=True)
class Standard:
    standard_id: str
    style_id: str
    stage: Stage
    worker_minutes_per_piece: Decimal
    available_at: datetime


@dataclass(frozen=True)
class Shift:
    shift_id: str
    factory_id: str
    kind: str
    start: datetime
    end: datetime
    break_start: datetime
    break_end: datetime
    available_at: datetime


@dataclass(frozen=True)
class Order:
    order_id: str
    style_id: str
    quantity: int
    available_at: datetime


@dataclass(frozen=True)
class Plan:
    observation_id: str
    line_id: str
    crew_id: str
    shift_id: str
    order_id: str
    standard_id: str
    planned_workers: int
    machine_available: bool
    downtime_start: datetime
    downtime_end: datetime
    opening_wip_pieces: int
    planned_release_pieces: int
    snapshot_at: datetime
    cutoff: datetime


@dataclass(frozen=True)
class Outcome:
    observation_id: str
    realized_workers: int
    unplanned_loss_minutes: int
    difficult_condition: bool
    completed_good_pieces: int
    closing_wip_pieces: int
    available_at: datetime


@dataclass(frozen=True)
class Membership:
    observation_id: str
    partition: str
    population: str


TABLE_TYPES = {
    "factories": Factory,
    "lines": Line,
    "crews": Crew,
    "styles": Style,
    "standards": Standard,
    "shifts": Shift,
    "orders": Order,
    "plans": Plan,
    "outcomes": Outcome,
    "membership": Membership,
}


@dataclass(frozen=True)
class Dataset:
    factories: tuple[Factory, ...]
    lines: tuple[Line, ...]
    crews: tuple[Crew, ...]
    styles: tuple[Style, ...]
    standards: tuple[Standard, ...]
    shifts: tuple[Shift, ...]
    orders: tuple[Order, ...]
    plans: tuple[Plan, ...]
    outcomes: tuple[Outcome, ...]
    membership: tuple[Membership, ...]
