"""Bounded adapters calling frozen M03B/M04 engines without changing selection."""

from dataclasses import asdict
from typing import Any

from pydantic import ValidationError

from loometric.api.codec import decode_body, input_json
from loometric.api.errors import ApiError, complexity_error
from loometric.api.job_schemas import JOB_REQUEST_MODELS, JobType
from loometric.api.job_settings import JobLimits
from loometric.api.operations import _instance
from loometric.api.settings import Limits
from loometric.execution import ResourceLimits
from loometric.optimization.configuration import SolverConfiguration
from loometric.planning.reporting import json_value
from loometric.scenarios.application import apply_scenario
from loometric.scenarios.contracts import ScenarioSpec, SchedulingRequest
from loometric.scenarios.engine import compare_scenario
from loometric.scenarios.loading import parse_specification
from loometric.scenarios.metrics import objective_values
from loometric.scenarios.selection import evaluate_instance
from loometric.scheduling.contracts import SchedulingInstance, instance_fingerprint


def validate_job(
    kind: JobType, body: str, limits: Limits, jobs: JobLimits
) -> tuple[SchedulingInstance, ScenarioSpec | None]:
    try:
        parsed = JOB_REQUEST_MODELS[kind].model_validate(decode_body(body, limits))
    except ValidationError:
        raise ApiError(
            422, "INVALID_ENVELOPE", "Request must match the closed endpoint envelope."
        ) from None
    if kind == "scheduling":
        return _instance(parsed.instance, limits), None
    instance = _instance(parsed.baseline, limits)
    spec = parse_specification(input_json(parsed.specification))
    if len(spec.changes) > limits.max_changes:
        raise complexity_error()
    solver = spec.scheduling.solver
    if solver is not None and (
        solver.random_seed != 42
        or solver.workers != 1
        or not solver.benchmark_mode
        or solver.wall_time_seconds_per_phase > jobs.solver_wall_seconds_per_phase
        or solver.deterministic_time_per_phase > jobs.solver_deterministic_time_per_phase
    ):
        raise ApiError(422, "JOB_SOLVER_POLICY", "Requested solver settings exceed the job policy.")
    apply_scenario(instance, spec)  # Validate the whole atomic transaction before admission.
    return instance, spec


def _safe_diagnostics(value: Any) -> Any:
    if isinstance(value, dict):
        result = {key: _safe_diagnostics(item) for key, item in value.items()}
        if "diagnostics" in result and result["diagnostics"]:
            result["diagnostics"] = ["Optimizer result unavailable or rejected; see its status."]
        if "reason" in result and result.get("status") in {
            "WORKER_FAILED",
            "SKIPPED_RESOURCE_LIMIT",
            "TERMINATED_RESOURCE_LIMIT",
        }:
            result["reason"] = "Bounded optimizer execution stopped; see its status."
        return result
    if isinstance(value, list):
        return [_safe_diagnostics(item) for item in value]
    return value


def execute_job(kind: JobType, body: str, limits: Limits, jobs: JobLimits) -> dict[str, Any]:
    instance, spec = validate_job(kind, body, limits, jobs)
    resources = ResourceLimits(
        max_operations=limits.max_operations,
        max_alternatives=jobs.max_alternatives,
        max_variables=jobs.max_variables,
        max_constraints=jobs.max_constraints,
        process_memory_mib=jobs.optimizer_memory_mib,
        process_wall_seconds=jobs.optimizer_wall_seconds,
    )
    if spec is not None:
        return _safe_diagnostics(compare_scenario(instance, spec, resources))
    configuration = SolverConfiguration(
        random_seed=42,
        workers=1,
        wall_time_seconds_per_phase=jobs.solver_wall_seconds_per_phase,
        deterministic_time_per_phase=jobs.solver_deterministic_time_per_phase,
        benchmark_mode=True,
    )
    evaluated, runtime = evaluate_instance(
        instance, SchedulingRequest("greedy_with_cp_sat", configuration), resources
    )
    return _safe_diagnostics(
        json_value(
            {
                "schema_version": 1,
                "status": evaluated.verification.status,
                "policy_version": instance.policy_version,
                "instance_id": instance.instance_id,
                "instance_fingerprint": instance_fingerprint(instance),
                "synthetic": True,
                "horizon": asdict(instance.horizon),
                "assumptions": instance.planning.assumptions,
                "provenance": {"synthetic": True, "assumptions": instance.planning.assumptions},
                "evaluation": asdict(evaluated),
                "objectives": objective_values(evaluated.metrics),
                "runtime": runtime,
                "limitations": [
                    "Synthetic conditional planning; not production authorization.",
                    "Only whole-stage-minute-v1 is verified; proof belongs to its producer.",
                    "No ML capacity, shared crews, materials, setups, splitting or initial WIP.",
                ],
            }
        )
    )
