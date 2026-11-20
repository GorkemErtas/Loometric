"""Read-only projection of tracked synthetic inputs into one relational CSV view.

No dispatch, optimization, capacity assessment, ML data or local result discovery.
Run from the repository root: python -m loometric.synthetic_export
"""

import argparse
import csv
import hashlib
import json
import os
import subprocess
import tempfile
from collections import Counter
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from loometric.benchmarks.design import load_design
from loometric.benchmarks.generation import generate_instance
from loometric.planning.loading import parse_json, parse_scenario
from loometric.planning.reporting import json_value
from loometric.planning.validation import PlanningError
from loometric.scenarios.application import apply_scenario
from loometric.scenarios.loading import parse_specification
from loometric.scheduling.contracts import SchedulingInstance, instance_fingerprint
from loometric.scheduling.loading import instance_json, parse_instance, parse_schedule
from loometric.scheduling.verification import verify_schedule

FIXTURE_ROOTS = (
    "examples/planning",
    "examples/scheduling",
    "examples/scheduling-scalability",
    "examples/scenarios",
)
DESIGN_PATH = "configs/m03c_benchmark.json"
OUTPUT_PATH = "data/processed/synthetic-data-view.csv"
COLUMNS = (
    "view_schema_version",
    "record_id",
    "parent_record_id",
    "record_type",
    "json_pointer",
    "source_id",
    "source_path",
    "source_sha256",
    "source_kind",
    "value_origin",
    "context_source_id",
    "baseline_source_id",
    "specification_source_id",
    "validation_status",
    "validation_codes_json",
    "instance_id",
    "instance_fingerprint",
    "scenario_id",
    "baseline_instance_id",
    "baseline_fingerprint",
    "claimed_instance_fingerprint",
    "policy_version",
    "schema_version",
    "benchmark_case",
    "benchmark_tier",
    "seed",
    "target_load_percent",
    "generation_config_json",
    "benchmark_execution_config_json",
    "order_id",
    "style_id",
    "quantity",
    "priority",
    "release_date",
    "due_date",
    "required_stages_json",
    "stage",
    "sequence_index",
    "compatible_line_ids_json",
    "line_id",
    "worker_count",
    "availability",
    "capability_id",
    "workforce_basis",
    "standard_minutes_per_unit",
    "measurement_unit",
    "output_unit",
    "shift_id",
    "interval_start",
    "interval_end",
    "profile_id",
    "effective_date",
    "assumed_efficiency",
    "profile_source_id",
    "evidence_status",
    "evidence_reference",
    "calendar_id",
    "working_date",
    "assignment_id",
    "downtime_id",
    "period_id",
    "reason",
    "horizon_start",
    "horizon_end",
    "calendar_utc_offset_minutes",
    "allocation_granularity_minutes",
    "label",
    "provenance_source_id",
    "synthetic",
    "assumptions_json",
    "scheduling_request_json",
    "operation",
    "new_worker_count",
    "new_assumed_efficiency",
    "new_availability",
    "proposed_quantity",
    "proposed_required_standard_minutes",
    "proposed_consumed_worker_minutes",
    "proposed_consumed_standard_minutes",
    "attributes_json",
)
_ENTITY_FIELDS = (
    "order_id",
    "style_id",
    "priority",
    "release_date",
    "due_date",
    "stage",
    "line_id",
    "worker_count",
    "availability",
    "capability_id",
    "workforce_basis",
    "standard_minutes_per_unit",
    "measurement_unit",
    "output_unit",
    "shift_id",
    "profile_id",
    "effective_date",
    "assumed_efficiency",
    "evidence_status",
    "evidence_reference",
    "calendar_id",
    "assignment_id",
    "downtime_id",
    "period_id",
    "reason",
    "operation",
    "label",
    "schema_version",
    "calendar_utc_offset_minutes",
    "allocation_granularity_minutes",
)
_COLLECTIONS = (
    ("styles", "style"),
    ("orders", "order"),
    ("lines", "line"),
    ("shifts", "shift"),
    ("capacity_profiles", "capacity_profile"),
    ("capabilities", "capability"),
)


def _json(value: Any) -> str:
    return json.dumps(json_value(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(json_value(value))


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, encoding="utf-8", check=True
    )
    return result.stdout


@dataclass
class Source:
    source_id: str
    source_path: str
    source_sha256: str
    source_kind: str
    document: dict[str, Any]
    value_origin: str = "source_input"
    context_source_id: str = ""
    baseline_source_id: str = ""
    validation_status: str = "VALID_INPUT"
    validation_codes: tuple[str, ...] = ()
    instance: SchedulingInstance | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    input_text: str = field(default="", repr=False)


def collect_sources(root: Path) -> Iterator[Source]:
    """Read only tracked fixture paths, then generate each distinct design case once."""
    tracked = _git(root, "ls-files", "-z", "--", *FIXTURE_ROOTS, DESIGN_PATH).split("\0")
    if DESIGN_PATH not in tracked:
        raise ValueError("The predeclared benchmark design must be tracked in this repository.")
    fixtures = []
    for name in sorted(p for p in tracked if p.endswith(".json") and p != DESIGN_PATH):
        content = (root / name).read_bytes()
        document = parse_json(content.decode("utf-8"))
        if not isinstance(document, dict):
            raise ValueError(f"Unsupported fixture envelope: {name}")
        if "planning" in document:
            kind = "scheduling_fixture"
        elif "orders" in document:
            kind = "planning_fixture"
        elif "changes" in document:
            kind = "what_if_specification"
        elif "allocations" in document:
            kind = "schedule_proposal"
        else:
            raise ValueError(f"Unsupported fixture envelope: {name}")
        source = Source(
            name,
            name,
            hashlib.sha256(content).hexdigest(),
            kind,
            document,
            input_text=content.decode("utf-8"),
        )
        try:
            if kind == "scheduling_fixture":
                source.instance = parse_instance(content.decode("utf-8"))
            elif kind == "planning_fixture":
                parse_scenario(content.decode("utf-8"))
            elif kind == "what_if_specification":
                parse_specification(content.decode("utf-8"))
            else:
                parse_schedule(content.decode("utf-8"))
        except PlanningError as exc:
            source.validation_status, source.validation_codes = "INVALID_INPUT", (exc.code,)
        fixtures.append(source)
    if not fixtures:
        raise ValueError("No tracked synthetic fixtures were found.")
    instances: dict[str, list[Source]] = {}
    for source in fixtures:
        if source.instance is not None:
            instances.setdefault(source.instance.instance_id, []).append(source)
    for source in fixtures:
        raw = source.document
        derived = None
        if (
            source.source_kind in ("what_if_specification", "schedule_proposal")
            and not source.validation_codes
        ):
            is_spec = source.source_kind == "what_if_specification"
            identity = raw["baseline_instance_id" if is_spec else "instance_id"]
            fingerprint = raw["baseline_fingerprint" if is_spec else "instance_fingerprint"]
            candidates = instances.get(identity, [])
            matches = [s for s in candidates if instance_fingerprint(s.instance) == fingerprint]
            if not matches:
                source.validation_status, source.validation_codes = (
                    "INVALID_INPUT",
                    ("UNBOUND_INSTANCE",),
                )
            else:
                # Exact ID/hash required; choose the first tracked alias in sorted path order.
                baseline = matches[0]
                source.context_source_id = baseline.source_id
                source.metadata["synthetic"] = baseline.instance.planning.synthetic
                if is_spec:
                    source.baseline_source_id = baseline.source_id
                try:
                    if is_spec:
                        spec = parse_specification(source.input_text)
                        changed = apply_scenario(baseline.instance, spec).instance
                        derived = Source(
                            source.source_id + "#applied",
                            source.source_path,
                            source.source_sha256,
                            "what_if_applied",
                            parse_json(instance_json(changed)),
                            "transformed_input",
                            baseline_source_id=baseline.source_id,
                            instance=changed,
                            metadata={"specification_source_id": source.source_id},
                        )
                    else:
                        proposal = parse_schedule(source.input_text)
                        verification = verify_schedule(baseline.instance, proposal)
                        source.validation_status = verification.status
                        source.validation_codes = tuple(
                            sorted({v.code for v in verification.violations})
                        )
                except PlanningError as exc:
                    source.validation_status, source.validation_codes = "INVALID_INPUT", (exc.code,)
        yield source
        if derived is not None:
            yield derived
    design_bytes = (root / DESIGN_PATH).read_bytes()
    design = load_design(root / DESIGN_PATH)
    if (root / DESIGN_PATH).read_bytes() != design_bytes:
        raise ValueError("Benchmark design changed while it was being read.")
    execution = {
        key: value
        for key, value in parse_json(design_bytes.decode("utf-8")).items()
        if key
        in (
            "wall_budgets_seconds",
            "deterministic_budget",
            "solver_seed",
            "repetitions",
            "resource_limits",
        )
    }
    for case in design.cases:
        instance = generate_instance(case.generation)
        yield Source(
            f"{DESIGN_PATH}#{case.name}",
            DESIGN_PATH,
            hashlib.sha256(design_bytes).hexdigest(),
            "benchmark_generated",
            parse_json(instance_json(instance)),
            "generated_input",
            instance=instance,
            metadata={
                "benchmark_case": case.name,
                "benchmark_tier": case.tier,
                "seed": case.generation.seed,
                "target_load_percent": case.generation.target_load_percent,
                "generation_config_json": _json(asdict(case.generation)),
                "benchmark_execution_config_json": _json(execution),
            },
        )


def source_rows(source: Source) -> Iterator[dict[str, str]]:
    """Entity rows with explicit parent keys, without order/resource Cartesian products."""
    raw = source.document
    planning = raw.get("planning", raw if "orders" in raw else None)
    common = {
        "view_schema_version": "1",
        "source_id": source.source_id,
        "source_path": source.source_path,
        "source_sha256": source.source_sha256,
        "source_kind": source.source_kind,
        "value_origin": source.value_origin,
        "context_source_id": source.context_source_id,
        "baseline_source_id": source.baseline_source_id,
        "validation_status": source.validation_status,
        "validation_codes_json": _json(source.validation_codes),
        "instance_id": raw.get("instance_id"),
        "instance_fingerprint": instance_fingerprint(source.instance) if source.instance else None,
        "scenario_id": raw.get("scenario_id", planning.get("scenario_id") if planning else None),
        "baseline_instance_id": raw.get("baseline_instance_id"),
        "baseline_fingerprint": raw.get("baseline_fingerprint"),
        "claimed_instance_fingerprint": raw.get("instance_fingerprint"),
        "policy_version": raw.get("policy_version"),
        "synthetic": planning.get("synthetic")
        if planning
        else raw.get("provenance", {}).get("synthetic"),
        **{key: value for key, value in source.metadata.items() if not key.endswith("_json")},
    }

    def record(
        kind: str, pointer: str, data: dict, parent: str = "", **extra: Any
    ) -> dict[str, str]:
        values = {
            **common,
            "record_id": f"{source.source_id}:{kind}:{pointer}",
            "parent_record_id": parent,
            "record_type": kind,
            "json_pointer": pointer,
            **{key: data[key] for key in _ENTITY_FIELDS if key in data},
            **extra,
        }
        if "interval" in data:
            values.update(
                interval_start=data["interval"]["start"], interval_end=data["interval"]["end"]
            )
        values["attributes_json"] = _json(data)
        return {name: _cell(values.get(name)) for name in COLUMNS}

    expanded = {
        "planning",
        "changes",
        "allocations",
        "unscheduled",
        "calendar",
        *(key for key, _ in _COLLECTIONS),
    }
    root_row = record(
        "source",
        "",
        {k: v for k, v in raw.items() if k not in expanded},
        **{k: v for k, v in source.metadata.items() if k.endswith("_json")},
    )
    if "horizon" in raw:
        root_row.update(horizon_start=raw["horizon"]["start"], horizon_end=raw["horizon"]["end"])
    yield root_row
    if planning is not None:
        prefix = "/planning" if "planning" in raw else ""
        aggregate = record(
            "planning",
            prefix,
            {k: v for k, v in planning.items() if k not in expanded},
            root_row["record_id"],
            synthetic=planning["synthetic"],
            assumptions_json=_json(planning["assumptions"]),
        )
        yield aggregate
        for collection, kind in _COLLECTIONS:
            for index, item in enumerate(planning[collection]):
                pointer = f"{prefix}/{collection}/{index}"
                nested = {"style": "standards", "order": "required_stages", "shift": "breaks"}.get(
                    kind
                )
                extra = {}
                if kind == "order":
                    extra = {
                        "quantity": item["quantity"],
                        "required_stages_json": _json(item["required_stages"]),
                    }
                if kind == "capacity_profile":
                    extra["profile_source_id"] = item["source_id"]
                row = record(
                    kind,
                    pointer,
                    {k: v for k, v in item.items() if k != nested},
                    aggregate["record_id"],
                    **extra,
                )
                yield row
                if kind == "style":
                    for number, standard in enumerate(item["standards"]):
                        yield record(
                            "style_standard",
                            f"{pointer}/standards/{number}",
                            standard,
                            row["record_id"],
                            style_id=item["style_id"],
                        )
                elif kind == "order":
                    for number, stage in enumerate(item["required_stages"]):
                        compatible = sorted(
                            {
                                c["line_id"]
                                for c in planning["capabilities"]
                                if c["style_id"] == item["style_id"] and c["stage"] == stage
                            }
                        )
                        yield record(
                            "order_stage",
                            f"{pointer}/required_stages/{number}",
                            {"stage": stage},
                            row["record_id"],
                            order_id=item["order_id"],
                            style_id=item["style_id"],
                            sequence_index=number,
                            compatible_line_ids_json=_json(compatible),
                        )
                elif kind == "shift":
                    for number, interval in enumerate(item["breaks"]):
                        yield record(
                            "break",
                            f"{pointer}/breaks/{number}",
                            {"interval": interval},
                            row["record_id"],
                            shift_id=item["shift_id"],
                            sequence_index=number,
                        )
        calendar = planning["calendar"]
        calendar_row = record(
            "calendar",
            prefix + "/calendar",
            {"calendar_id": calendar["calendar_id"]},
            aggregate["record_id"],
        )
        yield calendar_row
        for name, kind in (
            ("working_dates", "working_date"),
            ("assignments", "assignment"),
            ("planned_downtime", "downtime"),
            ("unavailable_periods", "unavailability"),
        ):
            for index, item in enumerate(calendar[name]):
                yield record(
                    kind,
                    f"{prefix}/calendar/{name}/{index}",
                    {"working_date": item} if kind == "working_date" else item,
                    calendar_row["record_id"],
                    calendar_id=calendar["calendar_id"],
                    **({"working_date": item} if kind == "working_date" else {}),
                )
    elif source.source_kind == "what_if_specification":
        provenance = raw["provenance"]
        spec = record(
            "scenario_specification",
            "",
            {k: v for k, v in raw.items() if k != "changes"},
            root_row["record_id"],
            synthetic=provenance["synthetic"],
            provenance_source_id=provenance["source_id"],
            assumptions_json=_json(provenance["assumptions"]),
            scheduling_request_json=_json(raw["scheduling"]) if "scheduling" in raw else "",
        )
        yield spec
        for index, change in enumerate(raw["changes"]):
            data = {**change, **change.get("assignment", {}), **change.get("downtime", {})}
            row = record(
                "scenario_change",
                f"/changes/{index}",
                data,
                spec["record_id"],
                sequence_index=index,
            )
            row["attributes_json"] = _json(change)
            for name in ("worker_count", "assumed_efficiency", "availability"):
                row["new_" + name], row[name] = row[name], ""
            yield row
    else:
        for name, kind in (
            ("allocations", "proposed_allocation"),
            ("unscheduled", "proposed_unscheduled"),
        ):
            for index, item in enumerate(raw[name]):
                row = record(
                    kind,
                    f"/{name}/{index}",
                    item,
                    root_row["record_id"],
                    proposed_quantity=item["quantity"],
                )
                for name in (
                    "required_standard_minutes",
                    "consumed_worker_minutes",
                    "consumed_standard_minutes",
                ):
                    row["proposed_" + name] = _cell(item.get(name))
                yield row


def export_csv(root: Path) -> dict[str, Any]:
    root = root.resolve()
    if Path(_git(root, "rev-parse", "--show-toplevel").strip()).resolve() != root:
        raise ValueError("Run from the repository root, or supply --root.")
    _git(root, "check-ignore", "-q", "--", OUTPUT_PATH)
    output = root / OUTPUT_PATH
    if not output.parent.resolve().is_relative_to(root):
        raise ValueError("The output directory must remain inside the repository.")
    output.parent.mkdir(parents=True, exist_ok=True)
    counts, kinds = Counter(), Counter()
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=output.parent,
            prefix=".synthetic-data-view-",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            writer = csv.DictWriter(stream, fieldnames=COLUMNS, lineterminator="\n")
            writer.writeheader()
            for source in collect_sources(root):
                kinds[source.source_kind] += 1
                for row in source_rows(source):
                    writer.writerow(row)
                    counts[row["record_type"]] += 1
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {
        "output": str(output),
        "rows": sum(counts.values()),
        "columns": len(COLUMNS),
        "record_counts": dict(sorted(counts.items())),
        "source_counts": dict(sorted(kinds.items())),
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Git repository root")
    args = parser.parse_args(argv)
    try:
        result = export_csv(args.root)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"status": "EXPORT_FAILED", "error": str(exc)}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
