"""Proof-gated lexicographic solves with independent verification of every incumbent."""

from dataclasses import dataclass
from importlib.metadata import version
from math import isfinite
from time import perf_counter

from ortools.sat.python import cp_model

from loometric.optimization.adapter import adapt_solution
from loometric.optimization.configuration import SolverConfiguration
from loometric.optimization.model import OBJECTIVE_NAMES, SchedulingModel, build_model
from loometric.planning.validation import PlanningError
from loometric.scheduling.contracts import ProposedSchedule, SchedulingInstance
from loometric.scheduling.metrics import QualityMetrics, calculate_metrics
from loometric.scheduling.verification import VerificationResult, verify_schedule


@dataclass(frozen=True)
class ObjectiveValues:
    unfinished_units: int
    priority_weighted_tardiness_minutes: int
    makespan_minutes: int

    @classmethod
    def from_metrics(cls, metrics: QualityMetrics) -> "ObjectiveValues":
        # M03A reports null makespan for an empty real allocation; its objective is zero.
        return cls(
            metrics.unscheduled_units,
            metrics.priority_weighted_tardiness_minutes,
            metrics.makespan_minutes or 0,
        )

    def as_tuple(self) -> tuple[int, int, int]:
        return (
            self.unfinished_units,
            self.priority_weighted_tardiness_minutes,
            self.makespan_minutes,
        )


@dataclass(frozen=True)
class PhaseResult:
    phase: int
    objective: str
    solver_status: str
    has_solution: bool
    objective_value: int | None
    best_objective_bound: float | None
    proven_optimal: bool
    prior_objectives_proven: bool


@dataclass(frozen=True)
class PhaseRuntime:
    phase: int
    solve_call_seconds: float
    solver_wall_seconds: float
    solver_deterministic_time: float


@dataclass(frozen=True)
class OptimizationRuntime:
    model_build_seconds: float
    phases: tuple[PhaseRuntime, ...]
    total_seconds: float


@dataclass(frozen=True)
class OptimizationDiagnostic:
    code: str
    message: str


@dataclass(frozen=True)
class OptimizationResult:
    status: str
    ortools_version: str
    configuration: SolverConfiguration
    phases: tuple[PhaseResult, ...]
    schedule: ProposedSchedule | None
    verification: VerificationResult | None
    metrics: QualityMetrics | None
    objectives: ObjectiveValues | None
    proven_optimal_objectives: int
    full_lexicographic_optimal: bool
    incumbent_phase: int | None
    terminal_solver_status: str
    termination_reason: str
    used_previous_phase_incumbent: bool
    diagnostics: tuple[OptimizationDiagnostic, ...]
    runtime: OptimizationRuntime
    absolute_gap_limit: float = 0.0
    relative_gap_limit: float = 0.0


@dataclass(frozen=True)
class _PhaseRun:
    solver: cp_model.CpSolver
    status: cp_model.CpSolverStatus
    runtime: PhaseRuntime


def _solve_phase(built: SchedulingModel, config: SolverConfiguration, phase: int) -> _PhaseRun:
    solver = cp_model.CpSolver()
    solver.parameters.random_seed = config.random_seed
    solver.parameters.num_search_workers = config.workers
    solver.parameters.max_time_in_seconds = config.wall_time_seconds_per_phase
    solver.parameters.max_deterministic_time = config.deterministic_time_per_phase
    solver.parameters.absolute_gap_limit = 0.0
    solver.parameters.relative_gap_limit = 0.0
    solver.parameters.log_search_progress = False
    started = perf_counter()
    status = solver.solve(built.model)
    elapsed = perf_counter() - started
    return _PhaseRun(
        solver,
        status,
        PhaseRuntime(phase, elapsed, solver.wall_time, solver.response_proto.deterministic_time),
    )


def optimize(
    instance: SchedulingInstance, configuration: SolverConfiguration | None = None
) -> OptimizationResult:
    configuration = configuration or SolverConfiguration()
    started = perf_counter()
    built = build_model(instance)
    build_seconds = perf_counter() - started
    phases: list[PhaseResult] = []
    runtimes: list[PhaseRuntime] = []
    diagnostics: list[OptimizationDiagnostic] = []
    schedule: ProposedSchedule | None = None
    verification: VerificationResult | None = None
    metrics: QualityMetrics | None = None
    objectives: ObjectiveValues | None = None
    incumbent_phase = None
    proven = 0
    terminal_status = "NOT_RUN"
    termination = "NOT_RUN"
    fallback = False

    def result(status: str) -> OptimizationResult:
        return OptimizationResult(
            status,
            version("ortools"),
            configuration,
            tuple(phases),
            schedule,
            verification,
            metrics,
            objectives,
            proven,
            proven == 3 and status != "INVALID",
            incumbent_phase,
            terminal_status,
            termination,
            fallback,
            tuple(diagnostics),
            OptimizationRuntime(build_seconds, tuple(runtimes), perf_counter() - started),
        )

    for index, objective in enumerate(built.objectives):
        phase = index + 1
        built.model.minimize(objective)
        run = _solve_phase(built, configuration, phase)
        solver, status = run.solver, run.status
        terminal_status = solver.status_name(status)
        runtimes.append(run.runtime)
        has_solution = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        bound = float(solver.best_objective_bound) if has_solution else None
        if bound is not None and not isfinite(bound):
            bound = None
        value = int(solver.value(objective)) if has_solution else None
        phases.append(
            PhaseResult(
                phase,
                OBJECTIVE_NAMES[index],
                terminal_status,
                has_solution,
                value,
                bound,
                False,
                proven == index,
            )
        )
        if not has_solution:
            if status == cp_model.UNKNOWN and schedule is not None:
                assert verification is not None
                fallback = True
                termination = "UNKNOWN_RETAINED_PREVIOUS_VERIFIED_INCUMBENT"
                return result(verification.status)
            if schedule is not None:
                diagnostics.append(
                    OptimizationDiagnostic(
                        "CONTRADICTORY_PHASE_RESULT",
                        "A previous feasible incumbent exists, but this phase reported "
                        "no feasible solution.",
                    )
                )
            schedule = verification = metrics = objectives = None
            incumbent_phase = None
            proven = 0
            termination = "NO_FEASIBLE_INCUMBENT"
            return result(terminal_status)

        try:
            schedule = adapt_solution(instance, built, solver)
        except PlanningError as exc:
            schedule = verification = metrics = objectives = None
            incumbent_phase = None
            proven = 0
            termination = "ADAPTER_REJECTED"
            diagnostics.append(OptimizationDiagnostic(exc.code, str(exc)))
            return result("INVALID")
        verification = verify_schedule(instance, schedule)
        incumbent_phase = phase
        if not verification.feasible:
            metrics = objectives = None
            proven = 0
            termination = "INDEPENDENT_VERIFIER_REJECTED"
            diagnostics.append(
                OptimizationDiagnostic(
                    "VERIFIER_REJECTED",
                    "Solver proposal failed the unchanged independent verifier.",
                )
            )
            return result("INVALID")
        metrics = calculate_metrics(instance, schedule)
        objectives = ObjectiveValues.from_metrics(metrics)
        actual_model_values = tuple(int(solver.value(var)) for var in built.objectives)
        if objectives.as_tuple() != actual_model_values:
            metrics = objectives = None
            proven = 0
            termination = "MODEL_METRICS_OBJECTIVE_MISMATCH"
            diagnostics.append(
                OptimizationDiagnostic(
                    "OBJECTIVE_MISMATCH",
                    "CP-SAT objective vector differs from independent schedule metrics.",
                )
            )
            return result("INVALID")
        if status == cp_model.FEASIBLE:
            termination = "FEASIBLE_PHASE_NOT_PROVEN"
            return result(verification.status)
        proven += 1
        phases[-1] = PhaseResult(
            phase, OBJECTIVE_NAMES[index], terminal_status, True, value, bound, True, True
        )
        if phase < 3:
            built.model.add(objective == value)
    termination = "ALL_THREE_OBJECTIVES_PROVEN_OPTIMAL"
    assert verification is not None
    return result(verification.status)
