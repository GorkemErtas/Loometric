"""Private one-case worker. Only stdlib is imported before the resource handshake."""

import gc
import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any

from loometric.benchmarks.resources import apply_child_memory_limit, peak_working_set_bytes


def run_case(request: dict[str, Any]) -> dict[str, Any]:
    from loometric.benchmarks.design import ResourceLimits
    from loometric.benchmarks.generation import (
        GenerationConfig,
        generate_instance,
        instance_json,
        static_dimensions,
    )
    from loometric.optimization.comparison import compare_quality
    from loometric.optimization.configuration import SolverConfiguration
    from loometric.optimization.model import build_model
    from loometric.optimization.solver import ObjectiveValues, optimize
    from loometric.planning.reporting import json_value
    from loometric.scheduling.contracts import instance_fingerprint
    from loometric.scheduling.dispatcher import dispatch
    from loometric.scheduling.metrics import calculate_metrics
    from loometric.scheduling.verification import verify_schedule

    started = perf_counter()
    raw = request["generation"]
    config = GenerationConfig(
        **{
            **raw,
            "start_date": date.fromisoformat(raw["start_date"]),
            "priorities": tuple(raw["priorities"]),
        }
    )
    limits = ResourceLimits(**request["resource_limits"])
    instance = generate_instance(config)
    dimensions = static_dimensions(instance)
    fingerprint = instance_fingerprint(instance)
    if request.get("instance_dir"):
        # The parent validated this directory. Names originate from strict matrix IDs.
        path = Path(request["instance_dir"]) / f"{request['case']}.json"
        content = instance_json(instance)
        if path.exists() and path.read_text(encoding="utf-8") != content:
            raise ValueError("Previously generated instance content differs.")
        path.write_text(content, encoding="utf-8")
    measurements: dict[str, Any] = {
        "generation_and_static_dimensions_seconds": perf_counter() - started
    }

    started = perf_counter()
    reference = dispatch(instance)
    measurements["reference_dispatch_seconds"] = perf_counter() - started
    started = perf_counter()
    reference_verification = verify_schedule(instance, reference)
    measurements["reference_verification_seconds"] = perf_counter() - started
    started = perf_counter()
    reference_metrics = (
        calculate_metrics(instance, reference) if reference_verification.feasible else None
    )
    measurements["reference_metrics_seconds"] = perf_counter() - started
    deterministic: dict[str, Any] = {
        "instance_id": instance.instance_id,
        "instance_fingerprint": fingerprint,
        "policy_version": instance.policy_version,
        "dimensions": dimensions,
        "reference": {
            "schedule": asdict(reference),
            "verification": asdict(reference_verification),
            "metrics": asdict(reference_metrics) if reference_metrics else None,
        },
        "optimizer": None,
        "comparison": "NO_COMPARABLE_INCUMBENT",
        "comparison_details": None,
    }
    reason = limits.rejection(dimensions)
    if reason:
        deterministic.update(status="SKIPPED_RESOURCE_LIMIT", reason=reason)
        return {"deterministic": json_value(deterministic), "measurements": measurements}

    started = perf_counter()
    built = build_model(instance)
    dimensions.update(
        eligible_alternatives=sum(
            len(operation.alternatives) for operation in built.operations.values()
        ),
        model_variables=len(built.model.proto.variables),
        model_constraints=len(built.model.proto.constraints),
        optional_intervals=sum(
            constraint.has_interval() for constraint in built.model.proto.constraints
        ),
    )
    del built  # Do not hold a second native model while optimizing.
    gc.collect()
    measurements["model_sizing_seconds"] = perf_counter() - started
    reason = limits.rejection(dimensions)
    if reason:
        deterministic.update(status="SKIPPED_RESOURCE_LIMIT", reason=reason)
        return {"deterministic": json_value(deterministic), "measurements": measurements}

    result = optimize(
        instance,
        SolverConfiguration(
            request["solver_seed"],
            1,
            request["wall_budget_seconds"],
            request["deterministic_budget"],
            True,
        ),
    )
    optimized = asdict(result)
    measurements["optimizer_runtime"] = optimized.pop("runtime")
    deterministic["optimizer"] = optimized
    measurements["audit_verification_seconds"] = None
    if result.schedule is None and (result.metrics is not None or result.objectives is not None):
        deterministic.update(
            status="INVALID", reason="Metrics/objectives exist without an incumbent."
        )
        optimized.update(
            status="INVALID", metrics=None, objectives=None, full_lexicographic_optimal=False
        )
        return {"deterministic": json_value(deterministic), "measurements": measurements}
    if result.schedule is not None:
        started = perf_counter()
        audit = verify_schedule(instance, result.schedule)
        measurements["audit_verification_seconds"] = perf_counter() - started
        deterministic["audit_verification"] = asdict(audit)
        started = perf_counter()
        audited_metrics = calculate_metrics(instance, result.schedule) if audit.feasible else None
        measurements["audit_metrics_seconds"] = perf_counter() - started
        accepted = (
            result.status != "INVALID"
            and audit.feasible
            and audited_metrics is not None
            and result.metrics == audited_metrics
            and result.objectives == ObjectiveValues.from_metrics(audited_metrics)
        )
        if not accepted:
            deterministic.update(
                status="INVALID", reason="Audit rejected candidate or metric/objective consistency."
            )
            optimized.update(
                status="INVALID", metrics=None, objectives=None, full_lexicographic_optimal=False
            )
            return {"deterministic": json_value(deterministic), "measurements": measurements}
    comparison = compare_quality(result.metrics, reference_metrics)
    deterministic.update(
        status=result.status,
        comparison="NO_COMPARABLE_INCUMBENT"
        if comparison.relation == "NOT_COMPARABLE"
        else comparison.relation,
        comparison_details=asdict(comparison),
    )
    if not reference_verification.feasible:
        deterministic.update(status="INVALID", reason="Reference failed unchanged verifier.")
    return {"deterministic": json_value(deterministic), "measurements": measurements}


def main() -> int:
    request = json.loads(sys.stdin.read())  # Parent releases work only after the hard guard.
    try:
        backend = apply_child_memory_limit(
            request["resource_limits"]["process_memory_mib"] * 1024**2
        )
    except OSError as exc:
        print(
            json.dumps(
                {
                    "deterministic": {
                        "status": "SKIPPED_RESOURCE_LIMIT",
                        "reason": f"Hard child memory limit unavailable: {exc}",
                        "comparison": "NO_COMPARABLE_INCUMBENT",
                    },
                    "measurements": {},
                }
            )
        )
        return 0
    try:
        result = run_case(request)
        result["measurements"].update(
            memory_backend=backend, peak_working_set_bytes=peak_working_set_bytes()
        )
    except MemoryError:
        result = {
            "deterministic": {
                "status": "TERMINATED_RESOURCE_LIMIT",
                "reason": "Python allocation failed under the configured hard memory limit.",
                "comparison": "NO_COMPARABLE_INCUMBENT",
            },
            "measurements": {},
        }
    except OSError as exc:
        result = {
            "deterministic": {
                "status": "WORKER_FAILED",
                "reason": str(exc),
                "comparison": "NO_COMPARABLE_INCUMBENT",
            },
            "measurements": {},
        }
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
