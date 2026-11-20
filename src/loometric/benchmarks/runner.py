"""Serial bounded matrix execution and explicit repeated-result comparison."""

import hashlib
import json
import os
import platform
import sys
from collections import Counter
from dataclasses import asdict
from importlib.metadata import distributions
from pathlib import Path
from time import perf_counter
from typing import Any

from loometric.benchmarks.design import BenchmarkDesign
from loometric.benchmarks.generation import GENERATOR_VERSION
from loometric.benchmarks.resources import guarded_child
from loometric.planning.reporting import json_value
from loometric.planning.validation import PlanningError


def content_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def environment_metadata() -> dict[str, Any]:
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "logical_cpus": os.cpu_count(),
        "dependencies": dict(
            sorted(
                (distribution.metadata["Name"], distribution.version)
                for distribution in distributions()
            )
        ),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    comparisons = Counter(row["deterministic"]["comparison"] for row in rows)
    statuses = Counter(row["deterministic"]["status"] for row in rows)
    proof_levels = Counter(
        str((row["deterministic"].get("optimizer") or {}).get("proven_optimal_objectives", 0))
        for row in rows
    )
    mismatches = []
    first = {}
    for row in rows:
        key = (row["case"], row["wall_budget_seconds"])
        if key not in first:
            first[key] = row
        elif first[key]["deterministic"] != row["deterministic"]:
            mismatches.append(
                {
                    "case": key[0],
                    "wall_budget_seconds": key[1],
                    "first_repetition": first[key]["repetition"],
                    "repetition": row["repetition"],
                    "first_sha256": content_hash(first[key]["deterministic"]),
                    "repeated_sha256": content_hash(row["deterministic"]),
                }
            )
    return {
        "rows": len(rows),
        "comparison_counts": dict(sorted(comparisons.items())),
        "status_counts": dict(sorted(statuses.items())),
        "proven_objective_counts": dict(sorted(proof_levels.items())),
        "repeated_result_mismatches": mismatches,
        "full_proofs": sum(
            bool((row["deterministic"].get("optimizer") or {}).get("full_lexicographic_optimal"))
            for row in rows
        ),
    }


def run_benchmark(
    design: BenchmarkDesign, output_dir: Path, *, progress: bool = True
) -> dict[str, Any]:
    root = Path.cwd().resolve()
    output_dir = output_dir.resolve()
    if not any(output_dir.is_relative_to(root / allowed) for allowed in (".tmp", "data/processed")):
        raise PlanningError(
            "INVALID_BENCHMARK_OUTPUT", "Bulk outputs must be inside .tmp/ or data/processed/."
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "results.json"
    journal_path = output_dir / "runs.jsonl"
    if results_path.exists() or journal_path.exists():
        raise PlanningError(
            "BENCHMARK_OUTPUT_EXISTS",
            "Choose a new output directory; existing evidence is not overwritten.",
        )
    instance_dir = output_dir / "instances"
    instance_dir.mkdir(exist_ok=True)
    started = perf_counter()
    rows, skips = [], {}
    total = len(design.cases) * len(design.wall_budgets_seconds) * design.repetitions
    with journal_path.open("x", encoding="utf-8") as journal:
        for repetition in range(1, design.repetitions + 1):
            for case in design.cases:
                for wall in design.wall_budgets_seconds:
                    row: dict[str, Any] = {
                        "case": case.name,
                        "tier": case.tier,
                        "pressure_percent": case.generation.target_load_percent,
                        "generator_seed": case.generation.seed,
                        "wall_budget_seconds": wall,
                        "repetition": repetition,
                    }
                    remaining = design.resource_limits.batch_wall_seconds - (
                        perf_counter() - started
                    )
                    if case.name in skips:
                        source = skips[case.name]
                        row.update(
                            deterministic=source["deterministic"],
                            measurements={
                                "reused_resource_skip_source": {
                                    "case": case.name,
                                    "repetition": source["repetition"],
                                    "wall_budget_seconds": source["wall_budget_seconds"],
                                }
                            },
                        )
                    elif remaining <= 0:
                        row.update(
                            deterministic={
                                "status": "SKIPPED_RESOURCE_LIMIT",
                                "reason": "Total batch wall budget exhausted before launch.",
                                "comparison": "NO_COMPARABLE_INCUMBENT",
                            },
                            measurements={},
                        )
                    else:
                        request = json_value(
                            {
                                "case": case.name,
                                "generation": asdict(case.generation),
                                "resource_limits": asdict(design.resource_limits),
                                "instance_dir": str(instance_dir),
                                "wall_budget_seconds": wall,
                                "deterministic_budget": design.deterministic_budget,
                                "solver_seed": design.solver_seed,
                            }
                        )
                        payload, resource = guarded_child(
                            json.dumps(request),
                            design.resource_limits.process_memory_mib,
                            min(remaining, design.resource_limits.process_wall_seconds),
                        )
                        if payload is None:
                            row.update(
                                deterministic={
                                    "status": resource["status"],
                                    "reason": resource["reason"],
                                    "comparison": "NO_COMPARABLE_INCUMBENT",
                                },
                                measurements={"resource": resource},
                            )
                        else:
                            row.update(payload)
                            row["measurements"]["resource"] = resource
                            if row["deterministic"]["status"] == "SKIPPED_RESOURCE_LIMIT":
                                skips[case.name] = row
                    rows.append(row)
                    journal.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
                    journal.flush()
                    if progress:
                        candidate = row["deterministic"].get("optimizer") or {}
                        print(
                            f"{len(rows)}/{total} {case.name} wall={wall} repeat={repetition} "
                            f"{row['deterministic']['status']} "
                            f"{row['deterministic']['comparison']} "
                            f"proof={candidate.get('proven_optimal_objectives', 0)}",
                            file=sys.stderr,
                            flush=True,
                        )
    report = {
        "schema_version": 1,
        "generator_version": GENERATOR_VERSION,
        "design": json_value(asdict(design)),
        "design_sha256": content_hash(json_value(asdict(design))),
        "rows": rows,
        "summary": summarize(rows),
        "environment": environment_metadata(),
        "measurements": {"batch_wall_seconds": perf_counter() - started},
    }
    results_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    return report
