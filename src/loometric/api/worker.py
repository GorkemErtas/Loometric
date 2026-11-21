"""Private bounded API worker. No FastAPI, ML, filesystem input or solver loading."""

import json
import sys

from loometric.execution import apply_child_memory_limit


def serve(*, job_mode: bool = False) -> int:
    request = json.loads(sys.stdin.read())
    try:
        memory_backend = apply_child_memory_limit(
            (
                request["job_limits"]["process_memory_mib"]
                if job_mode
                else request["limits"]["process_memory_mib"]
            )
            * 1024**2,
            request.get("windows_job_name"),
        )
    except OSError:
        print(json.dumps({"error": {"status": 503, "code": "RESOURCE_GUARD_UNAVAILABLE"}}))
        return 0
    # Establish the hard guard before optional Pydantic imports and domain parsing.
    from decimal import DecimalException

    from loometric.api.errors import ApiError
    from loometric.api.job_settings import JobLimits
    from loometric.api.operations import execute
    from loometric.api.settings import Limits
    from loometric.planning.validation import PlanningError

    try:
        limits = Limits(**request["limits"])
        jobs = JobLimits(**request["job_limits"]) if "job_limits" in request else None
        if job_mode:
            from loometric.api.job_operations import execute_job

            result = {"data": execute_job(request["job_type"], request["body"], limits, jobs)}
        else:
            result = {"data": execute(request["operation"], request["body"], limits, jobs)}
    except ApiError as exc:
        result = {"error": {"status": exc.status, "code": exc.code, "details": exc.details}}
    except PlanningError as exc:
        result = {
            "error": {"status": 422, "code": "DOMAIN_VALIDATION_FAILED", "domain_code": exc.code}
        }
    except (DecimalException, OverflowError, ValueError, TypeError, KeyError):
        result = {"error": {"status": 422, "code": "INVALID_VALUE"}}
    except MemoryError:
        result = {"error": {"status": 503, "code": "MEMORY_LIMIT_EXCEEDED"}}
    except Exception:
        result = {"error": {"status": 500, "code": "EXECUTION_FAILED"}}
    if job_mode:
        result["execution"] = {"memory_backend": memory_backend}
    encoded = json.dumps(result, allow_nan=False)
    ceiling = (
        request["job_limits"]["max_result_bytes"]
        if job_mode
        else request["limits"]["max_response_bytes"]
    )
    if len(encoded.encode("utf-8")) > ceiling:
        encoded = json.dumps({"error": {"code": "RESPONSE_LIMIT_EXCEEDED"}})
    print(encoded)
    return 0


def main() -> int:
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
