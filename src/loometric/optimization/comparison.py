"""Pure metric comparison in the declared objective hierarchy; no scheduling or validation."""

from dataclasses import dataclass
from decimal import Decimal, localcontext

from loometric.optimization.model import OBJECTIVE_NAMES
from loometric.optimization.solver import ObjectiveValues
from loometric.planning.domain import ARITHMETIC_CONTEXT
from loometric.scheduling.metrics import QualityMetrics


@dataclass(frozen=True)
class ObjectiveComparison:
    relation: str
    deciding_objective: str | None
    candidate_objectives: ObjectiveValues | None
    reference_objectives: ObjectiveValues | None
    objective_deltas: dict[str, int]
    metric_deltas: dict[str, int | Decimal | None]


def compare_quality(
    candidate: QualityMetrics | None, reference: QualityMetrics | None
) -> ObjectiveComparison:
    candidate_values = ObjectiveValues.from_metrics(candidate) if candidate else None
    reference_values = ObjectiveValues.from_metrics(reference) if reference else None
    if candidate_values is None or reference_values is None:
        return ObjectiveComparison(
            "NOT_COMPARABLE", None, candidate_values, reference_values, {}, {}
        )
    a, b = candidate_values.as_tuple(), reference_values.as_tuple()
    relation = "BETTER" if a < b else "WORSE" if a > b else "TIE"
    deciding = next(
        (name for name, left, right in zip(OBJECTIVE_NAMES, a, b, strict=True) if left != right),
        None,
    )
    fields = (
        "scheduled_orders",
        "scheduled_units",
        "unscheduled_units",
        "on_time_completed_orders",
        "late_completed_orders",
        "priority_weighted_tardiness_minutes",
        "total_tardiness_minutes",
        "makespan_minutes",
        "line_utilization",
        "standard_capacity_utilization",
        "unused_standard_minutes",
    )
    with localcontext(ARITHMETIC_CONTEXT):
        differences = {
            field: (
                getattr(candidate, field) - getattr(reference, field)
                if getattr(candidate, field) is not None and getattr(reference, field) is not None
                else None
            )
            for field in fields
        }
    return ObjectiveComparison(
        relation,
        deciding,
        candidate_values,
        reference_values,
        {name: left - right for name, left, right in zip(OBJECTIVE_NAMES, a, b, strict=True)},
        differences,
    )
