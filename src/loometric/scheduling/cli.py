"""Local dispatch/verification and optional optimization; no production services."""

import argparse
import json
from dataclasses import asdict
from decimal import DecimalException
from pathlib import Path
from time import perf_counter

from loometric.planning.reporting import json_value
from loometric.planning.validation import PlanningError
from loometric.scheduling.contracts import SchedulingInstance, instance_fingerprint
from loometric.scheduling.dispatcher import ALGORITHM, dispatch
from loometric.scheduling.loading import load_instance, load_schedule
from loometric.scheduling.metrics import calculate_metrics
from loometric.scheduling.verification import verify_schedule


def _optimize_command(instance: SchedulingInstance, args: argparse.Namespace) -> int:
    # Keep the existing dispatch/verify commands usable without optional solver imports.
    try:
        from loometric.optimization.comparison import compare_quality
        from loometric.optimization.configuration import SolverConfiguration
        from loometric.optimization.solver import optimize
    except ImportError as exc:
        raise PlanningError(
            "OPTIMIZATION_DEPENDENCY_MISSING",
            "Install the optimization extra or requirements/m03b.txt to run CP-SAT.",
        ) from exc
    config = SolverConfiguration(
        args.seed,
        args.workers,
        args.time_limit_seconds,
        args.deterministic_time_limit,
        args.benchmark_mode,
    )
    optimized = optimize(instance, config)
    started = perf_counter()
    reference = dispatch(instance)
    reference_verification = verify_schedule(instance, reference)
    reference_metrics = (
        calculate_metrics(instance, reference) if reference_verification.feasible else None
    )
    reference_seconds = perf_counter() - started
    comparison = compare_quality(optimized.metrics, reference_metrics)
    result = asdict(optimized)
    result["solver_configuration"] = result.pop("configuration")
    optimizer_runtime = result.pop("runtime")
    result.update(
        {
            "schema_version": 1,
            "algorithm": "ortools-cp-sat-lexicographic-v1",
            "synthetic": True,
            "instance_id": instance.instance_id,
            "instance_fingerprint": instance_fingerprint(instance),
            "policy_version": instance.policy_version,
            "horizon": asdict(instance.horizon),
            "assumptions": instance.planning.assumptions,
            "baseline_comparison": {
                "reference_algorithm": ALGORITHM,
                "reference_schedule": asdict(reference),
                "reference_verification": asdict(reference_verification),
                "reference_metrics": asdict(reference_metrics) if reference_metrics else None,
                "comparison": asdict(comparison),
            },
            "runtime": {
                "optimizer": optimizer_runtime,
                "reference_total_seconds": reference_seconds,
            },
        }
    )
    print(json.dumps(json_value(result), indent=2, sort_keys=True, allow_nan=False))
    return (
        0
        if optimized.verification is not None
        and optimized.verification.feasible
        and optimized.status != "INVALID"
        else 2
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Synthetic whole-stage scheduling and independent verification."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("dispatch", "verify"):
        sub = commands.add_parser(command)
        sub.add_argument("--instance", type=Path, required=True)
        if command == "verify":
            sub.add_argument("--schedule", type=Path, required=True)
    optimizer = commands.add_parser("optimize")
    optimizer.add_argument("--instance", type=Path, required=True)
    optimizer.add_argument("--seed", type=int, default=42)
    optimizer.add_argument("--workers", type=int, default=1)
    optimizer.add_argument("--time-limit-seconds", type=float, default=10.0)
    optimizer.add_argument("--deterministic-time-limit", type=float, default=1.0)
    optimizer.add_argument("--benchmark-mode", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args(argv)
    try:
        instance = load_instance(args.instance)
        if not instance.planning.synthetic:
            raise PlanningError(
                "INSTANCE_NOT_SYNTHETIC", "M03A CLI accepts explicitly synthetic instances only."
            )
        if args.command == "optimize":
            return _optimize_command(instance, args)
        schedule = (
            dispatch(instance) if args.command == "dispatch" else load_schedule(args.schedule)
        )
        verification = verify_schedule(instance, schedule)
        metrics = calculate_metrics(instance, schedule) if verification.feasible else None
        result = {
            "schema_version": 1,
            "policy_version": instance.policy_version,
            "instance_id": instance.instance_id,
            "instance_fingerprint": instance_fingerprint(instance),
            "synthetic": True,
            "algorithm": ALGORITHM if args.command == "dispatch" else "EXTERNAL_PROPOSAL",
            "optimality_claim": False,
            "status": verification.status,
            "assumptions": instance.planning.assumptions,
            "horizon": asdict(instance.horizon),
            "calendar_utc_offset_minutes": instance.calendar_utc_offset_minutes,
            "allocation_granularity_minutes": instance.allocation_granularity_minutes,
            "schedule": asdict(schedule),
            "verification": asdict(verification),
            "metrics": asdict(metrics) if metrics is not None else None,
        }
        print(json.dumps(json_value(result), indent=2, sort_keys=True, allow_nan=False))
        return 0 if verification.feasible else 2
    except (PlanningError, OSError, UnicodeError, DecimalException, OverflowError) as exc:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "INVALID_INPUT",
                    "metrics": None,
                    "error": {
                        "code": getattr(
                            exc,
                            "code",
                            "INPUT_UNREADABLE" if isinstance(exc, OSError) else "INVALID_VALUE",
                        ),
                        "message": str(exc),
                    },
                },
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
        )
        return 2
