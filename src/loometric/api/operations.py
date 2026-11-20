"""HTTP application adapters around unchanged planning/scheduling/scenario engines."""

from dataclasses import asdict
from typing import Any

from pydantic import ValidationError

from loometric.api.codec import decode_body, input_json
from loometric.api.errors import ApiError, complexity_error
from loometric.api.schemas import REQUEST_MODELS
from loometric.api.settings import Limits
from loometric.execution import ResourceLimits
from loometric.planning.capacity import assess_scenario
from loometric.planning.loading import scenario_from_dict
from loometric.planning.reporting import json_value, report_to_dict
from loometric.planning.scenario import PlanningScenario
from loometric.scenarios.engine import compare_scenario
from loometric.scenarios.loading import parse_specification
from loometric.scheduling.contracts import SchedulingInstance, instance_fingerprint
from loometric.scheduling.dispatcher import ALGORITHM, dispatch
from loometric.scheduling.loading import parse_instance, parse_schedule
from loometric.scheduling.metrics import calculate_metrics
from loometric.scheduling.verification import verify_schedule

LIMITATIONS = (
    "Synthetic conditional planning; not production authorization.",
    "Only the declared whole-stage-minute-v1 subset is verified; no optimality claim.",
    "No ML-derived capacity, materials, setups, shared crews, splitting or initial WIP.",
)


def _planning_limits(planning: PlanningScenario, limits: Limits) -> None:
    if not planning.synthetic:
        raise ApiError(422, "SYNTHETIC_REQUIRED", "Only explicitly synthetic inputs are supported.")
    if (
        len(planning.orders) > limits.max_orders
        or sum(len(order.required_stages) for order in planning.orders) > limits.max_operations
    ):
        raise complexity_error()


def _instance(raw: dict[str, Any], limits: Limits) -> SchedulingInstance:
    instance = parse_instance(input_json(raw))
    _planning_limits(instance.planning, limits)
    return instance


def execute(operation: str, source: str, limits: Limits) -> dict[str, Any]:
    """Called in the bounded child, never in an event-loop thread."""
    if operation not in REQUEST_MODELS:
        raise ApiError(422, "UNSUPPORTED_OPERATION", "Operation is not supported by this API.")
    value = decode_body(source, limits)
    try:
        request = REQUEST_MODELS[operation].model_validate(value)
    except ValidationError:
        # Pydantic error text/locations may contain arbitrary input keys or secrets.
        raise ApiError(
            422,
            "INVALID_ENVELOPE",
            "Request must match the closed endpoint envelope.",
            [{"rule": "required_object_fields_only"}],
        ) from None
    if operation == "capacity":
        planning = scenario_from_dict(request.scenario)
        _planning_limits(planning, limits)
        return report_to_dict(assess_scenario(planning))
    if operation == "compare":
        baseline = _instance(request.baseline, limits)
        spec = parse_specification(input_json(request.specification))
        if spec.scheduling.method != "greedy":
            raise ApiError(422, "UNSUPPORTED_METHOD", "M05A supports greedy scheduling only.")
        if len(spec.changes) > limits.max_changes:
            raise complexity_error()
        # M04 alone owns atomic edits, same-demand checks, verification and selection.
        return compare_scenario(
            baseline,
            spec,
            ResourceLimits(
                max_operations=limits.max_operations,
                process_memory_mib=limits.process_memory_mib,
                process_wall_seconds=limits.execution_timeout_seconds,
            ),
        )
    instance = _instance(request.instance, limits)
    schedule = (
        dispatch(instance)
        if operation == "dispatch"
        else parse_schedule(input_json(request.schedule))
    )
    verification = verify_schedule(instance, schedule)
    if operation == "dispatch" and not verification.feasible:
        raise ApiError(500, "EXECUTION_FAILED", "The reference producer failed verification.")
    metrics = calculate_metrics(instance, schedule) if verification.feasible else None
    return json_value(
        {
            "schema_version": 1,
            "policy_version": instance.policy_version,
            "instance_id": instance.instance_id,
            "instance_fingerprint": instance_fingerprint(instance),
            "synthetic": True,
            "producer": "greedy" if operation == "dispatch" else "external_proposal",
            "algorithm": ALGORITHM if operation == "dispatch" else "EXTERNAL_PROPOSAL",
            "optimality_claim": False,
            "status": verification.status,
            "assumptions": instance.planning.assumptions,
            "provenance": {"synthetic": True, "assumptions": instance.planning.assumptions},
            "horizon": asdict(instance.horizon),
            "calendar_utc_offset_minutes": instance.calendar_utc_offset_minutes,
            "allocation_granularity_minutes": instance.allocation_granularity_minutes,
            "schedule": asdict(schedule),
            "verification": {**asdict(verification), "status": verification.status},
            "metrics": asdict(metrics) if metrics is not None else None,
            "limitations": LIMITATIONS,
        }
    )
