"""Strict version-1 specification parsing using existing planning wire primitives."""

from pathlib import Path
from typing import Any

from loometric.optimization.configuration import SolverConfiguration
from loometric.planning.domain import AvailabilityStatus, PlannedDowntime, ShiftAssignment
from loometric.planning.loading import (
    enumeration,
    fields,
    items,
    number,
    parse_interval,
    parse_json,
)
from loometric.planning.validation import PlanningError
from loometric.scenarios.contracts import (
    AddAssignment,
    AddDowntime,
    Change,
    Provenance,
    RemoveAssignment,
    RemoveDowntime,
    ReplaceDowntime,
    ScenarioSpec,
    SchedulingRequest,
    SetAvailability,
    SetEfficiency,
    SetWorkers,
)


def _change(raw: Any) -> Change:
    if not isinstance(raw, dict) or "operation" not in raw:
        raise PlanningError("INVALID_CHANGE", "Change requires an explicit operation.")
    operation = raw["operation"]
    match operation:
        case "set_workers":
            value = fields(raw, ("operation", "line_id", "worker_count"))
            return SetWorkers(value["line_id"], value["worker_count"])
        case "set_efficiency":
            value = fields(raw, ("operation", "profile_id", "assumed_efficiency"))
            return SetEfficiency(value["profile_id"], number(value["assumed_efficiency"]))
        case "set_availability":
            value = fields(raw, ("operation", "line_id", "availability"))
            return SetAvailability(
                value["line_id"], enumeration(AvailabilityStatus, value["availability"])
            )
        case "add_assignment":
            value = fields(raw, ("operation", "assignment"))
            assignment = fields(value["assignment"], tuple(ShiftAssignment.__dataclass_fields__))
            return AddAssignment(ShiftAssignment(**assignment))
        case "remove_assignment":
            value = fields(raw, ("operation", "assignment_id"))
            return RemoveAssignment(value["assignment_id"])
        case "add_downtime" | "replace_downtime":
            value = fields(raw, ("operation", "downtime"))
            stop = fields(value["downtime"], tuple(PlannedDowntime.__dataclass_fields__))
            downtime = PlannedDowntime(**{**stop, "interval": parse_interval(stop["interval"])})
            return (
                AddDowntime(downtime) if operation == "add_downtime" else ReplaceDowntime(downtime)
            )
        case "remove_downtime":
            value = fields(raw, ("operation", "downtime_id"))
            return RemoveDowntime(value["downtime_id"])
        case _:
            raise PlanningError(
                "UNSUPPORTED_CHANGE", f"Unsupported change operation: {operation!r}"
            )


def parse_specification(source: str) -> ScenarioSpec:
    data = fields(
        parse_json(source),
        (
            "schema_version",
            "baseline_instance_id",
            "baseline_fingerprint",
            "scenario_id",
            "label",
            "changes",
            "provenance",
        ),
        ("scheduling",),
    )
    provenance = fields(data["provenance"], tuple(Provenance.__dataclass_fields__))
    scheduling = SchedulingRequest()
    if "scheduling" in data:
        request = fields(data["scheduling"], ("method",), ("solver",))
        settings = None
        if request["method"] == "greedy_with_cp_sat":
            raw = fields(
                request.get("solver", {}), (), tuple(SolverConfiguration.__dataclass_fields__)
            )
            settings = SolverConfiguration(**raw)
        elif "solver" in request:
            raise PlanningError(
                "AMBIGUOUS_CONFIGURATION", "Solver settings require explicit CP-SAT method."
            )
        scheduling = SchedulingRequest(request["method"], settings)
    return ScenarioSpec(
        data["baseline_instance_id"],
        data["baseline_fingerprint"],
        data["scenario_id"],
        data["label"],
        tuple(_change(raw) for raw in items(data["changes"])),
        Provenance(
            provenance["source_id"],
            provenance["synthetic"],
            tuple(items(provenance["assumptions"])),
        ),
        scheduling,
        data["schema_version"],
    )


def load_specification(path: Path) -> ScenarioSpec:
    return parse_specification(path.read_text(encoding="utf-8"))
