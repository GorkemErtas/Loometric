"""Verified greedy fallback and strict-better optional CP-SAT selection."""

import json
from dataclasses import asdict, dataclass
from typing import Any, Literal

from loometric.execution import ResourceLimits, guarded_child
from loometric.planning.validation import PlanningError
from loometric.scenarios.contracts import SchedulingRequest
from loometric.scenarios.metrics import OBJECTIVES, compare_objectives, objective_values
from loometric.scheduling.contracts import ProposedSchedule, SchedulingInstance
from loometric.scheduling.dispatcher import ALGORITHM, dispatch
from loometric.scheduling.loading import instance_json, parse_schedule
from loometric.scheduling.metrics import QualityMetrics, calculate_metrics
from loometric.scheduling.verification import VerificationResult, verify_schedule


@dataclass(frozen=True)
class OptimizerAttempt:
    status: str
    solver_status: str | None = None
    solver_version: str | None = None
    phases: tuple[dict[str, Any], ...] = ()
    proven_objectives: int = 0
    full_lexicographic_optimal: bool = False
    incumbent_phase: int | None = None
    used_previous_phase_incumbent: bool = False
    dimensions: dict[str, int] | None = None
    candidate_schedule: ProposedSchedule | None = None
    verification: VerificationResult | None = None
    metrics: QualityMetrics | None = None
    comparison_with_greedy: dict[str, object] | None = None
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScheduleEvaluation:
    selected_producer: Literal["greedy", "cp_sat"]
    selected_schedule: ProposedSchedule
    verification: VerificationResult
    metrics: QualityMetrics
    selected_proven_objectives: int
    selected_full_lexicographic_optimal: bool
    fallback_reason: str | None
    greedy_schedule: ProposedSchedule
    greedy_verification: VerificationResult
    greedy_metrics: QualityMetrics
    optimizer: OptimizerAttempt
    selected_algorithm: str = ALGORITHM


def _proof(raw: dict[str, Any], actual: QualityMetrics) -> tuple[tuple[dict[str, Any], ...], int]:
    phases = raw["phases"]
    if not isinstance(phases, list) or not 1 <= len(phases) <= 3:
        raise ValueError("Invalid optimizer phase sequence.")
    levels = 0
    values = objective_values(actual)
    for index, phase in enumerate(phases):
        if phase["phase"] != index + 1 or phase["objective"] != OBJECTIVES[index]:
            raise ValueError("Unexpected objective phase.")
        if not phase["prior_objectives_proven"] or levels != index:
            raise ValueError("A phase ran without earlier objective proof.")
        if phase["solver_status"] == "OPTIMAL":
            if (
                phase["proven_optimal"] is not True
                or phase["has_solution"] is not True
                or phase["objective_value"] != phase["best_objective_bound"]
                or phase["objective_value"] != values[OBJECTIVES[index]]
            ):
                raise ValueError("Inconsistent optimal objective evidence.")
            levels += 1
        else:
            if index != len(phases) - 1 or phase["proven_optimal"]:
                raise ValueError("Unproven phase was followed or claimed optimal.")
            if phase["solver_status"] == "FEASIBLE":
                if (
                    not phase["has_solution"]
                    or phase["objective_value"] != values[OBJECTIVES[index]]
                ):
                    raise ValueError("Feasible phase does not match its verified incumbent.")
            elif phase["solver_status"] == "UNKNOWN":
                if (
                    index == 0
                    or phase["has_solution"]
                    or phase["objective_value"] is not None
                    or not raw["used_previous_phase_incumbent"]
                ):
                    raise ValueError("Unknown phase has no valid retained incumbent source.")
            else:
                raise ValueError("A no-solution terminal status supplied an incumbent.")
    if raw["proven_optimal_objectives"] != levels or raw["full_lexicographic_optimal"] != (
        levels == 3
    ):
        raise ValueError("Proof count disagrees with phase evidence.")
    if raw["terminal_solver_status"] != phases[-1]["solver_status"]:
        raise ValueError("Terminal solver status disagrees with final phase.")
    source = max(phase["phase"] for phase in phases if phase["has_solution"])
    if raw["incumbent_phase"] != source or raw["used_previous_phase_incumbent"] != (
        source != len(phases)
    ):
        raise ValueError("Incumbent source does not match the phase history.")
    return tuple(phases), levels


def _optimizer(
    instance: SchedulingInstance,
    request: SchedulingRequest,
    limits: ResourceLimits,
    greedy_metrics: QualityMetrics,
) -> tuple[OptimizerAttempt, dict[str, Any]]:
    assert request.solver is not None
    operations = sum(len(order.required_stages) for order in instance.planning.orders)
    reason = limits.rejection({"operations": operations})
    if reason:
        return OptimizerAttempt(
            "SKIPPED_RESOURCE_LIMIT", dimensions={"operations": operations}, diagnostics=(reason,)
        ), {}
    try:
        payload, guard_runtime = guarded_child(
            json.dumps(
                {
                    "instance_json": instance_json(instance),
                    "solver_configuration": asdict(request.solver),
                    "resource_limits": asdict(limits),
                }
            ),
            limits.process_memory_mib,
            limits.process_wall_seconds,
            worker_module="loometric.scenarios.worker",
        )
    except (OSError, ValueError) as exc:
        return OptimizerAttempt("WORKER_FAILED", diagnostics=(str(exc),)), {}
    runtime = {"resource": guard_runtime}
    if payload is None:
        return OptimizerAttempt(
            guard_runtime.get("status", "WORKER_FAILED"),
            diagnostics=(guard_runtime.get("reason", "Worker returned no result."),),
        ), runtime
    if not isinstance(payload, dict):
        return OptimizerAttempt(
            "INVALID", diagnostics=("Worker result is not an object.",)
        ), runtime
    runtime["worker"] = payload.pop("runtime", {})
    raw = payload.get("optimization")
    dimensions = payload.get("dimensions")
    if raw is None:
        return OptimizerAttempt(
            payload.get("status", "INVALID"),
            dimensions=dimensions,
            diagnostics=(payload.get("reason", "No optimizer result."),),
        ), runtime
    candidate = None
    verification = None
    try:
        if (
            not isinstance(raw, dict)
            or raw["configuration"] != asdict(request.solver)
            or raw["absolute_gap_limit"] != 0
            or raw["relative_gap_limit"] != 0
        ):
            raise ValueError("Solver configuration or exact-gap settings differ from the request.")
        if raw["schedule"] is None:
            if raw["metrics"] is not None or raw["objectives"] is not None:
                raise ValueError("No incumbent but candidate metrics were reported.")
            return OptimizerAttempt(
                raw["status"],
                solver_status=raw["terminal_solver_status"],
                solver_version=raw["ortools_version"],
                phases=tuple(raw["phases"]),
                dimensions=dimensions,
                diagnostics=(raw["termination_reason"],),
            ), runtime
        candidate = parse_schedule(json.dumps(raw["schedule"]))
        verification = verify_schedule(instance, candidate)
        if not verification.feasible:
            raise ValueError("Independent candidate verification failed.")
        if raw["status"] != verification.status:
            raise ValueError("Optimizer status disagrees with independent feasibility.")
        actual = calculate_metrics(instance, candidate)
        from loometric.planning.reporting import json_value

        if (
            json_value(asdict(actual)) != raw["metrics"]
            or objective_values(actual) != raw["objectives"]
        ):
            raise ValueError(
                "Candidate metric/objective claims differ from independent recomputation."
            )
        phases, levels = _proof(raw, actual)
        attempt = OptimizerAttempt(
            status=raw["status"],
            solver_status=raw["terminal_solver_status"],
            solver_version=raw["ortools_version"],
            phases=phases,
            proven_objectives=levels,
            full_lexicographic_optimal=levels == 3,
            incumbent_phase=raw["incumbent_phase"],
            used_previous_phase_incumbent=raw["used_previous_phase_incumbent"],
            dimensions=dimensions,
            candidate_schedule=candidate,
            verification=verification,
            metrics=actual,
            comparison_with_greedy=compare_objectives(greedy_metrics, actual),
        )
        return attempt, runtime
    except (PlanningError, ValueError, KeyError, TypeError) as exc:
        return OptimizerAttempt(
            "INVALID",
            dimensions=dimensions,
            candidate_schedule=candidate,
            verification=verification,
            diagnostics=(str(exc),),
        ), runtime


def evaluate_instance(
    instance: SchedulingInstance, request: SchedulingRequest, limits: ResourceLimits | None = None
) -> tuple[ScheduleEvaluation, dict[str, Any] | None]:
    limits = limits or ResourceLimits()
    ceilings = ResourceLimits()
    for name in (
        "max_operations",
        "max_alternatives",
        "max_variables",
        "max_constraints",
        "process_memory_mib",
        "process_wall_seconds",
    ):
        if getattr(limits, name) > getattr(ceilings, name):
            raise PlanningError(
                "RESOURCE_POLICY_EXCEEDED", "M04 cannot exceed the M03C resource envelope."
            )
    greedy = dispatch(instance)
    verification = verify_schedule(instance, greedy)
    if not verification.feasible:
        raise PlanningError(
            "REFERENCE_VERIFICATION_FAILED", "Greedy proposal failed independent verification."
        )
    greedy_metrics = calculate_metrics(instance, greedy)
    attempt, runtime = (
        (OptimizerAttempt("NOT_REQUESTED"), None)
        if request.method == "greedy"
        else (_optimizer(instance, request, limits, greedy_metrics))
    )
    selected = (
        attempt.metrics is not None
        and attempt.comparison_with_greedy is not None
        and attempt.comparison_with_greedy["relation"] == "BETTER"
    )
    reason = (
        None
        if selected
        else (
            "CP_SAT_NOT_REQUESTED"
            if attempt.status == "NOT_REQUESTED"
            else ("CP_SAT_NOT_STRICTLY_BETTER" if attempt.metrics is not None else attempt.status)
        )
    )
    return ScheduleEvaluation(
        selected_producer="cp_sat" if selected else "greedy",
        selected_schedule=attempt.candidate_schedule if selected else greedy,
        verification=attempt.verification if selected else verification,
        metrics=attempt.metrics if selected else greedy_metrics,
        selected_proven_objectives=attempt.proven_objectives if selected else 0,
        selected_full_lexicographic_optimal=attempt.full_lexicographic_optimal
        if selected
        else False,
        fallback_reason=reason,
        greedy_schedule=greedy,
        greedy_verification=verification,
        greedy_metrics=greedy_metrics,
        optimizer=attempt,
        selected_algorithm="ortools-cp-sat-lexicographic-v1" if selected else ALGORITHM,
    ), runtime
