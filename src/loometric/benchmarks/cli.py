"""Offline audit CLI; existing scheduling commands are not modified."""

import argparse
import json
import sys
from pathlib import Path

from loometric.benchmarks.design import load_design
from loometric.benchmarks.runner import run_benchmark
from loometric.planning.validation import PlanningError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bounded synthetic scheduling scalability audit.")
    parser.add_argument("--config", type=Path, default=Path("configs/m03c_benchmark.json"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = run_benchmark(load_design(args.config), args.output_dir)
    except (PlanningError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "INVALID_INPUT", "error": str(exc)}), file=sys.stderr)
        return 2
    print(
        json.dumps(
            {"output": str(args.output_dir / "results.json"), "summary": report["summary"]},
            indent=2,
        )
    )
    failures = {
        "INVALID",
        "WORKER_FAILED",
        "INFEASIBLE",
        "MODEL_INVALID",
        "TERMINATED_RESOURCE_LIMIT",
    }
    return 2 if failures.intersection(report["summary"]["status_counts"]) else 0
