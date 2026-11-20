"""Compare an immutable baseline with one validated conditional capacity scenario."""

from dataclasses import asdict
from typing import Any

from loometric.execution import ResourceLimits
from loometric.planning.reporting import json_value
from loometric.planning.validation import PlanningError
from loometric.scenarios.application import apply_scenario, demand_fingerprint
from loometric.scenarios.contracts import ScenarioSpec, specification_fingerprint
from loometric.scenarios.metrics import compare_objectives, metric_deltas
from loometric.scenarios.selection import evaluate_instance
from loometric.scheduling.contracts import SchedulingInstance, instance_fingerprint


def compare_scenario(
    baseline: SchedulingInstance, spec: ScenarioSpec, limits: ResourceLimits | None = None
) -> dict[str, Any]:
    applied = apply_scenario(baseline, spec)
    scenario = applied.instance
    if demand_fingerprint(baseline) != demand_fingerprint(scenario):
        raise PlanningError(
            "DEMAND_CHANGED", "Comparison requires identical order demand and standards."
        )
    base, base_runtime = evaluate_instance(baseline, spec.scheduling, limits)
    changed, changed_runtime = evaluate_instance(scenario, spec.scheduling, limits)

    def identity(instance: SchedulingInstance) -> dict[str, Any]:
        return {
            "instance_id": instance.instance_id,
            "instance_fingerprint": instance_fingerprint(instance),
            "policy_version": instance.policy_version,
            "horizon": asdict(instance.horizon),
            "assumptions": instance.planning.assumptions,
        }

    deltas = metric_deltas(base.metrics, changed.metrics)
    denominators = (
        "available_line_minutes",
        "available_worker_minutes",
        "available_standard_minutes",
    )
    return json_value(
        {
            "schema_version": 1,
            "status": "VALID_COMPARISON",
            "synthetic": True,
            "scenario_id": spec.scenario_id,
            "label": spec.label,
            "provenance": asdict(spec.provenance),
            "specification_fingerprint": specification_fingerprint(spec),
            "same_demand_fingerprint": demand_fingerprint(baseline),
            "same_demand_verified": True,
            "scheduling_request": asdict(spec.scheduling),
            "resource_policy": {
                key: value
                for key, value in asdict(limits or ResourceLimits()).items()
                if key != "batch_wall_seconds"
            },
            "baseline": {"identity": identity(baseline), "evaluation": asdict(base)},
            "scenario": {"identity": identity(scenario), "evaluation": asdict(changed)},
            "applied_changes": [asdict(item) for item in applied.audit],
            "metric_deltas": {key: asdict(value) for key, value in deltas.items()},
            "selected_comparison": compare_objectives(base.metrics, changed.metrics),
            "greedy_comparison": compare_objectives(base.greedy_metrics, changed.greedy_metrics),
            "interpretation": {
                "conditional_planning_only": True,
                "causal_productivity_estimate": False,
                "standard_capacity_increased": changed.metrics.available_standard_minutes
                > base.metrics.available_standard_minutes,
                "unfinished_demand_reduced": changed.metrics.unscheduled_units
                < base.metrics.unscheduled_units,
                "utilization_denominators_changed": {
                    key: getattr(base.metrics, key) != getattr(changed.metrics, key)
                    for key in denominators
                },
                "same_instance_scheduling_gain": {
                    "baseline": base.selected_producer == "cp_sat",
                    "scenario": changed.selected_producer == "cp_sat",
                },
            },
            "limitations": (
                "Conditional synthetic planning; no causal, forecast or financial guarantee.",
                "Declared qualified labor, standards and efficiency are uncalibrated assumptions.",
                "No sharing, setups, materials, splitting, rework, WIP or ML-derived capacity.",
                "Wall-limited optimizer outcomes may differ; candidate proof remains explicit.",
                "Completed-order tardiness excludes unfinished demand; denominators can change.",
            ),
            "runtime": {"baseline": base_runtime, "scenario": changed_runtime},
        }
    )
