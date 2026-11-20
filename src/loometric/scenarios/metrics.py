"""Same-demand scalar differences and the frozen three-objective ordering."""

from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Literal

from loometric.planning.domain import ARITHMETIC_CONTEXT
from loometric.scheduling.metrics import QualityMetrics

OBJECTIVES = ("unfinished_units", "priority_weighted_tardiness_minutes", "makespan_minutes")
METRIC_UNITS = {
    "scheduled_orders": "order",
    "unscheduled_orders": "order",
    "partial_orders": "order",
    "scheduled_units": "piece",
    "unscheduled_units": "piece",
    "scheduled_operations": "operation",
    "unscheduled_operations": "operation",
    "allocated_stage_units": "stage_piece",
    "on_time_completed_orders": "order",
    "late_completed_orders": "order",
    "total_tardiness_minutes": "minute",
    "priority_weighted_tardiness_minutes": "priority_weighted_minute",
    "makespan_minutes": "minute",
    "available_line_minutes": "line_minute",
    "occupied_line_minutes": "line_minute",
    "line_utilization": "ratio",
    "available_worker_minutes": "worker_minute",
    "consumed_worker_minutes": "worker_minute",
    "unused_worker_minutes": "worker_minute",
    "available_standard_minutes": "standard_worker_minute",
    "consumed_standard_minutes": "standard_worker_minute",
    "unused_standard_minutes": "standard_worker_minute",
    "standard_capacity_utilization": "ratio",
    "rounding_slack_standard_minutes": "standard_worker_minute",
}


@dataclass(frozen=True)
class MetricDelta:
    baseline: int | Decimal | None
    scenario: int | Decimal | None
    absolute_change: int | Decimal | None
    percentage_change: Decimal | None
    percentage_status: Literal["DEFINED", "BASELINE_ZERO", "NULL_VALUE"]
    percentage_point_change: Decimal | None
    unit: str


def scalar_delta(
    baseline: int | Decimal | None, scenario: int | Decimal | None, unit: str
) -> MetricDelta:
    if baseline is None or scenario is None:
        return MetricDelta(baseline, scenario, None, None, "NULL_VALUE", None, unit)
    with localcontext(ARITHMETIC_CONTEXT):
        absolute = scenario - baseline
        percentage = Decimal(absolute) / Decimal(baseline) * 100 if baseline else None
        points = Decimal(absolute) * 100 if unit == "ratio" else None
    return MetricDelta(
        baseline,
        scenario,
        absolute,
        percentage,
        "DEFINED" if baseline else "BASELINE_ZERO",
        points,
        unit,
    )


def metric_deltas(baseline: QualityMetrics, scenario: QualityMetrics) -> dict[str, MetricDelta]:
    return {
        name: scalar_delta(getattr(baseline, name), getattr(scenario, name), unit)
        for name, unit in METRIC_UNITS.items()
    }


def objective_values(metrics: QualityMetrics) -> dict[str, int]:
    # Frozen M03A metrics: empty makespan remains null; objective comparison uses zero.
    return {
        "unfinished_units": metrics.unscheduled_units,
        "priority_weighted_tardiness_minutes": metrics.priority_weighted_tardiness_minutes,
        "makespan_minutes": metrics.makespan_minutes or 0,
    }


def compare_objectives(baseline: QualityMetrics, scenario: QualityMetrics) -> dict[str, object]:
    before, after = objective_values(baseline), objective_values(scenario)
    left, right = tuple(before.values()), tuple(after.values())
    return {
        "relation": "BETTER" if right < left else "WORSE" if right > left else "TIE",
        "baseline_objectives": before,
        "scenario_objectives": after,
        "deciding_objective": next((key for key in OBJECTIVES if before[key] != after[key]), None),
        "absolute_changes": {key: after[key] - before[key] for key in OBJECTIVES},
    }
