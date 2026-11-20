"""Pure atomic scenario transformation; demand and frozen policy are preserved."""

from dataclasses import asdict, dataclass, replace
from typing import Any

from loometric.planning.domain import EvidenceStatus
from loometric.planning.scenario import index_by, reference
from loometric.planning.validation import PlanningError
from loometric.scenarios.contracts import (
    AddAssignment,
    AddDowntime,
    RemoveAssignment,
    RemoveDowntime,
    ReplaceDowntime,
    ScenarioSpec,
    SetAvailability,
    SetEfficiency,
    SetWorkers,
    digest,
    transformation_fingerprint,
)
from loometric.scheduling.contracts import SchedulingInstance, instance_fingerprint


@dataclass(frozen=True)
class AppliedChange:
    index: int
    operation: str
    target_id: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    changed: bool


@dataclass(frozen=True)
class AppliedScenario:
    instance: SchedulingInstance
    audit: tuple[AppliedChange, ...]


def demand_fingerprint(instance: SchedulingInstance) -> str:
    return digest(
        {
            "orders": [asdict(order) for order in instance.planning.orders],
            "styles": [asdict(style) for style in instance.planning.styles],
        }
    )


def apply_scenario(baseline: SchedulingInstance, spec: ScenarioSpec) -> AppliedScenario:
    if (
        baseline.instance_id != spec.baseline_instance_id
        or instance_fingerprint(baseline) != spec.baseline_fingerprint
    ):
        raise PlanningError("BASELINE_MISMATCH", "Specification does not match the exact baseline.")
    if not baseline.planning.synthetic:
        raise PlanningError("SCENARIO_NOT_SYNTHETIC", "M04 requires a synthetic baseline.")
    scenario = baseline.planning
    lines = index_by(scenario.lines, "line_id")
    profiles = index_by(scenario.capacity_profiles, "profile_id")
    assignments = index_by(scenario.calendar.assignments, "assignment_id")
    downtime = index_by(scenario.calendar.planned_downtime, "downtime_id")
    touched, audit = set(), []
    for index, change in enumerate(spec.changes, 1):
        if isinstance(change, SetWorkers | SetAvailability):
            mapping, key = lines, change.line_id
            field = "worker_count" if isinstance(change, SetWorkers) else "availability"
            conflict = ("line", key, field)
            before = reference(mapping, key, "line")
            after = replace(before, **{field: getattr(change, field)})
        elif isinstance(change, SetEfficiency):
            mapping, key = profiles, change.profile_id
            conflict = ("profile", key, "assumed_efficiency")
            before = reference(mapping, key, "profile")
            after = replace(
                before,
                assumed_efficiency=change.assumed_efficiency,
                source_id=spec.provenance.source_id,
                evidence_status=EvidenceStatus.SYNTHETIC,
                evidence_reference=None,
            )
        else:
            is_assignment = isinstance(change, AddAssignment | RemoveAssignment)
            mapping = assignments if is_assignment else downtime
            payload = (
                change.assignment
                if isinstance(change, AddAssignment)
                else (
                    change.downtime if isinstance(change, AddDowntime | ReplaceDowntime) else None
                )
            )
            key = (
                (payload.assignment_id if is_assignment else payload.downtime_id)
                if payload
                else (
                    change.assignment_id
                    if isinstance(change, RemoveAssignment)
                    else change.downtime_id
                )
            )
            conflict = ("assignment" if is_assignment else "downtime", key, "lifecycle")
            before = mapping.get(key)
            after = payload
        if conflict in touched:
            raise PlanningError("SCENARIO_CONFLICT", f"More than one change targets {conflict}.")
        touched.add(conflict)
        if isinstance(change, AddAssignment | AddDowntime) and before is not None:
            raise PlanningError("ENTITY_ALREADY_EXISTS", f"Cannot add existing entity {key}.")
        if (
            isinstance(change, RemoveAssignment | RemoveDowntime | ReplaceDowntime)
            and before is None
        ):
            raise PlanningError("UNKNOWN_REFERENCE", f"Cannot change unknown entity {key}.")
        if after is None:
            del mapping[key]
        else:
            mapping[key] = after
        audit.append(
            AppliedChange(
                index,
                change.operation,
                key,
                asdict(before) if before else None,
                asdict(after) if after else None,
                before != after,
            )
        )
    identity = f"whatif:{spec.scenario_id}:{transformation_fingerprint(spec)[:20]}"
    modified = replace(
        baseline,
        instance_id=identity,
        planning=replace(
            scenario,
            scenario_id=identity,
            lines=tuple(lines.values()),
            capacity_profiles=tuple(profiles.values()),
            calendar=replace(
                scenario.calendar,
                assignments=tuple(assignments.values()),
                planned_downtime=tuple(downtime.values()),
            ),
            assumptions=(
                *scenario.assumptions,
                *spec.provenance.assumptions,
                f"Conditional scenario {spec.scenario_id}; source {spec.provenance.source_id}.",
            ),
        ),
    )
    if demand_fingerprint(baseline) != demand_fingerprint(modified):
        raise PlanningError("DEMAND_CHANGED", "Scenario transformation changed fixed demand.")
    return AppliedScenario(modified, tuple(audit))
