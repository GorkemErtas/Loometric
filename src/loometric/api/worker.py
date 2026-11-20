"""Private bounded API worker. No FastAPI, ML, filesystem input or solver loading."""

import json
import sys

from loometric.execution import apply_child_memory_limit


def main() -> int:
    request = json.loads(sys.stdin.read())
    try:
        apply_child_memory_limit(
            request["limits"]["process_memory_mib"] * 1024**2, request.get("windows_job_name")
        )
    except OSError:
        print(json.dumps({"error": {"status": 503, "code": "RESOURCE_GUARD_UNAVAILABLE"}}))
        return 0
    # Establish the hard guard before optional Pydantic imports and domain parsing.
    from decimal import DecimalException

    from loometric.api.errors import ApiError
    from loometric.api.operations import execute
    from loometric.api.settings import Limits
    from loometric.planning.validation import PlanningError

    try:
        result = {
            "data": execute(request["operation"], request["body"], Limits(**request["limits"]))
        }
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
    encoded = json.dumps(result, allow_nan=False)
    if len(encoded.encode("utf-8")) > request["limits"]["max_response_bytes"]:
        encoded = json.dumps({"error": {"code": "RESPONSE_LIMIT_EXCEEDED"}})
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
