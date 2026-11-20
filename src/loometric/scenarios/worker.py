"""Private native optimizer worker; establish the hard guard before solver imports."""

import gc
import json
import sys
from dataclasses import asdict
from time import perf_counter
from typing import Any

from loometric.execution import ResourceLimits, apply_child_memory_limit, peak_working_set_bytes


def run(request: dict[str, Any]) -> dict[str, Any]:
    from loometric.optimization.configuration import SolverConfiguration
    from loometric.scheduling.loading import parse_instance

    instance = parse_instance(request["instance_json"])
    limits = ResourceLimits(**request["resource_limits"])
    dimensions = {
        "operations": sum(len(order.required_stages) for order in instance.planning.orders)
    }
    reason = limits.rejection(dimensions)
    if reason:
        return {"status": "SKIPPED_RESOURCE_LIMIT", "reason": reason, "dimensions": dimensions}
    try:
        from loometric.optimization.model import build_model
        from loometric.optimization.solver import optimize
    except ImportError:
        return {
            "status": "OPTIMIZATION_DEPENDENCY_MISSING",
            "reason": "Install the optimization extra or requirements/m03b.txt for CP-SAT.",
            "dimensions": dimensions,
        }
    started = perf_counter()
    built = build_model(instance)
    dimensions.update(
        eligible_alternatives=sum(len(op.alternatives) for op in built.operations.values()),
        model_variables=len(built.model.proto.variables),
        model_constraints=len(built.model.proto.constraints),
    )
    del built
    gc.collect()
    sizing_seconds = perf_counter() - started
    reason = limits.rejection(dimensions)
    if reason:
        return {
            "status": "SKIPPED_RESOURCE_LIMIT",
            "reason": reason,
            "dimensions": dimensions,
            "runtime": {"sizing_seconds": sizing_seconds},
        }
    result = asdict(optimize(instance, SolverConfiguration(**request["solver_configuration"])))
    native_runtime = result.pop("runtime")
    from loometric.planning.reporting import json_value

    return json_value(
        {
            "status": result["status"],
            "optimization": result,
            "dimensions": dimensions,
            "runtime": {"sizing_seconds": sizing_seconds, "optimizer": native_runtime},
        }
    )


def main() -> int:
    request = json.loads(sys.stdin.read())
    try:
        backend = apply_child_memory_limit(
            request["resource_limits"]["process_memory_mib"] * 1024**2,
            request.get("windows_job_name"),
        )
    except OSError as exc:
        print(json.dumps({"status": "SKIPPED_RESOURCE_LIMIT", "reason": str(exc)}))
        return 0
    try:
        payload = run(request)
    except MemoryError:
        payload = {
            "status": "TERMINATED_RESOURCE_LIMIT",
            "reason": "Allocation failed under the hard memory cap.",
        }
    except (ValueError, OSError, OverflowError) as exc:
        payload = {"status": "WORKER_FAILED", "reason": str(exc)}
    runtime = payload.setdefault("runtime", {})
    runtime.update(memory_backend=backend, peak_working_set_bytes=peak_working_set_bytes())
    print(json.dumps(payload, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
