"""Versioned typed changes; no arbitrary entity patches or implicit defaults."""

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Literal

from loometric.optimization.configuration import SolverConfiguration
from loometric.planning.domain import AvailabilityStatus, PlannedDowntime, ShiftAssignment
from loometric.planning.reporting import json_value
from loometric.planning.validation import PlanningError, decimal, enum_value, integer, members, text


@dataclass(frozen=True)
class SetWorkers:
    line_id: str
    worker_count: int
    operation: Literal["set_workers"] = "set_workers"

    def __post_init__(self) -> None:
        text(self.line_id, "line_id")
        integer(self.worker_count, "worker_count")


@dataclass(frozen=True)
class SetEfficiency:
    profile_id: str
    assumed_efficiency: Decimal
    operation: Literal["set_efficiency"] = "set_efficiency"

    def __post_init__(self) -> None:
        text(self.profile_id, "profile_id")
        decimal(self.assumed_efficiency, "assumed_efficiency")
        if self.assumed_efficiency > 1:
            raise PlanningError("INVALID_EFFICIENCY", "Assumed efficiency must be in [0,1].")


@dataclass(frozen=True)
class SetAvailability:
    line_id: str
    availability: AvailabilityStatus
    operation: Literal["set_availability"] = "set_availability"

    def __post_init__(self) -> None:
        text(self.line_id, "line_id")
        enum_value(self.availability, AvailabilityStatus, "availability")


@dataclass(frozen=True)
class AddAssignment:
    assignment: ShiftAssignment
    operation: Literal["add_assignment"] = "add_assignment"

    def __post_init__(self) -> None:
        if not isinstance(self.assignment, ShiftAssignment):
            raise PlanningError("INVALID_CHANGE", "A typed ShiftAssignment is required.")


@dataclass(frozen=True)
class RemoveAssignment:
    assignment_id: str
    operation: Literal["remove_assignment"] = "remove_assignment"

    def __post_init__(self) -> None:
        text(self.assignment_id, "assignment_id")


@dataclass(frozen=True)
class AddDowntime:
    downtime: PlannedDowntime
    operation: Literal["add_downtime"] = "add_downtime"

    def __post_init__(self) -> None:
        if not isinstance(self.downtime, PlannedDowntime):
            raise PlanningError("INVALID_CHANGE", "A typed PlannedDowntime is required.")


@dataclass(frozen=True)
class ReplaceDowntime:
    downtime: PlannedDowntime
    operation: Literal["replace_downtime"] = "replace_downtime"

    def __post_init__(self) -> None:
        if not isinstance(self.downtime, PlannedDowntime):
            raise PlanningError("INVALID_CHANGE", "A complete typed PlannedDowntime is required.")


@dataclass(frozen=True)
class RemoveDowntime:
    downtime_id: str
    operation: Literal["remove_downtime"] = "remove_downtime"

    def __post_init__(self) -> None:
        text(self.downtime_id, "downtime_id")


Change = (
    SetWorkers
    | SetEfficiency
    | SetAvailability
    | AddAssignment
    | RemoveAssignment
    | AddDowntime
    | ReplaceDowntime
    | RemoveDowntime
)
CHANGE_TYPES = (
    SetWorkers,
    SetEfficiency,
    SetAvailability,
    AddAssignment,
    RemoveAssignment,
    AddDowntime,
    ReplaceDowntime,
    RemoveDowntime,
)


@dataclass(frozen=True)
class Provenance:
    source_id: str
    synthetic: bool
    assumptions: tuple[str, ...]

    def __post_init__(self) -> None:
        text(self.source_id, "source_id")
        if type(self.synthetic) is not bool or not self.synthetic:
            raise PlanningError(
                "SCENARIO_NOT_SYNTHETIC", "M04 accepts explicitly synthetic assumptions only."
            )
        members(self.assumptions, str, "assumptions", nonempty=True)
        for assumption in self.assumptions:
            text(assumption, "assumption")


@dataclass(frozen=True)
class SchedulingRequest:
    method: Literal["greedy", "greedy_with_cp_sat"] = "greedy"
    solver: SolverConfiguration | None = None

    def __post_init__(self) -> None:
        if self.method not in ("greedy", "greedy_with_cp_sat"):
            raise PlanningError("UNSUPPORTED_METHOD", "Use greedy or greedy_with_cp_sat.")
        if self.method == "greedy":
            if self.solver is not None:
                raise PlanningError(
                    "AMBIGUOUS_CONFIGURATION", "Greedy does not consume solver settings."
                )
        elif not isinstance(self.solver, SolverConfiguration):
            raise PlanningError(
                "INVALID_SOLVER_CONFIGURATION", "CP-SAT requires typed solver settings."
            )
        elif (
            self.solver.workers != 1
            or not self.solver.benchmark_mode
            or self.solver.wall_time_seconds_per_phase > 10
            or self.solver.deterministic_time_per_phase > 1
        ):
            raise PlanningError(
                "INVALID_SOLVER_CONFIGURATION",
                "M04 requires worker1, benchmark mode, wall<=10s and deterministic<=1 per phase.",
            )


@dataclass(frozen=True)
class ScenarioSpec:
    baseline_instance_id: str
    baseline_fingerprint: str
    scenario_id: str
    label: str
    changes: tuple[Change, ...]
    provenance: Provenance
    scheduling: SchedulingRequest = SchedulingRequest()
    schema_version: int = 1

    def __post_init__(self) -> None:
        integer(self.schema_version, "schema_version", minimum=1)
        if self.schema_version != 1:
            raise PlanningError("SCENARIO_SCHEMA_MISMATCH", "Supported scenario schema is 1.")
        for name in ("baseline_instance_id", "scenario_id", "label"):
            text(getattr(self, name), name)
        if not isinstance(self.baseline_fingerprint, str) or not re.fullmatch(
            "[0-9a-f]{64}", self.baseline_fingerprint
        ):
            raise PlanningError(
                "INVALID_FINGERPRINT", "Baseline fingerprint must be lowercase SHA-256."
            )
        if type(self.changes) is not tuple or len(self.changes) > 1000:
            raise PlanningError(
                "INVALID_CHANGE", "Changes require a tuple of at most1000 operations."
            )
        for change in self.changes:
            if type(change) not in CHANGE_TYPES:
                raise PlanningError(
                    "UNSUPPORTED_CHANGE", "Only declared capacity changes are supported."
                )
            expected = type(change).__dataclass_fields__["operation"].default
            if change.operation != expected:
                raise PlanningError("INVALID_CHANGE", "Change type and operation tag disagree.")
        if not isinstance(self.provenance, Provenance) or not isinstance(
            self.scheduling, SchedulingRequest
        ):
            raise PlanningError(
                "INVALID_SCENARIO", "Typed provenance and scheduling request are required."
            )


def digest(value: object) -> str:
    payload = json.dumps(json_value(value), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def specification_fingerprint(spec: ScenarioSpec) -> str:
    return digest(asdict(spec))


def transformation_fingerprint(spec: ScenarioSpec) -> str:
    data = asdict(spec)
    del data["scheduling"]
    return digest(data)
