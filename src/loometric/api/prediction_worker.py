"""Stdlib-only startup; hard memory guard established before importing ML."""

import json
import os
import sys

from loometric.execution import apply_child_memory_limit


def main() -> int:
    request = json.loads(sys.stdin.read())
    try:
        backend = apply_child_memory_limit(768 * 1024**2, request.get("windows_job_name"))
    except OSError:
        print(json.dumps({"error": {"code": "RESOURCE_GUARD_UNAVAILABLE"}}))
        return 0
    # Fixed numerical worker controls, established before native libraries import.
    for variable in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        os.environ[variable] = "1"
    from pydantic import ValidationError

    from loometric.api.codec import decode_body
    from loometric.api.errors import ApiError
    from loometric.api.prediction_schemas import SyntheticPredictionRequest
    from loometric.api.settings import default_limits
    from loometric.experimental_ml.artifacts import ArtifactError, load_trusted
    from loometric.experimental_ml.inference import predict

    try:
        parsed = decode_body(request["body"], default_limits())
        version = request.get("api_version", 1)

        if version == 1:
            contract = SyntheticPredictionRequest.model_validate(parsed)

            metadata, models = load_trusted(request["receipt"])

            prediction = predict(
                contract,
                metadata,
                models,
                request["receipt"],
            )

        elif version == 2:
            from loometric.api.prediction_schemas_v2 import (
                SyntheticPredictionRequestV2,
            )
            from loometric.experimental_ml_v2.inference import (
                predict_v2,
            )
            from loometric.experimental_ml_v2.serving import (
                load_experimental_model,
            )

            contract = SyntheticPredictionRequestV2.model_validate(parsed)

            metadata, models = load_trusted(request["receipt"])

            research_model = None

            if "rf_physics" in contract.models:
                _, research_model = load_experimental_model(contract)

            prediction = predict_v2(
                contract,
                metadata,
                models,
                request["receipt"],
                research_model,
            )

        elif version == 3:
            from loometric.api.prediction_schemas_v2 import SyntheticPredictionRequestV2
            from loometric.api.prediction_schemas_v3 import SyntheticPredictionRequestV3
            from loometric.experimental_ml_v2.serving import load_experimental_model
            from loometric.final_candidate.inference import predict_v3

            contract = SyntheticPredictionRequestV3.model_validate(parsed)
            metadata, models = load_trusted(request["receipt"])
            legacy = SyntheticPredictionRequestV2.model_construct(
                schema_version=2,
                synthetic=True,
                prediction_context=contract.prediction_context,
                inputs=contract.inputs,
                models=[m for m in contract.models if m != "history_boost"],
            )
            research_model = (
                load_experimental_model(legacy)[1] if "rf_physics" in contract.models else None
            )
            prediction = predict_v3(contract, metadata, models, request["receipt"], research_model)
        else:
            raise ValueError("Unsupported API version.")

        result = {
            "data": prediction,
            "memory_backend": backend,
        }
    except ArtifactError:
        result = {"error": {"code": "EXPERIMENTAL_ARTIFACT_UNAVAILABLE"}}
    except ApiError as exc:
        result = {"error": {"code": exc.code}}
    except (ValidationError, ValueError, TypeError, KeyError):
        result = {"error": {"code": "INVALID_ENVELOPE"}}
    except MemoryError:
        result = {"error": {"code": "MEMORY_LIMIT_EXCEEDED"}}
    except Exception:
        result = {"error": {"code": "EXECUTION_FAILED"}}
    encoded = json.dumps(result, allow_nan=False)
    if len(encoded.encode("utf-8")) > 131072:
        encoded = json.dumps({"error": {"code": "RESPONSE_LIMIT_EXCEEDED"}})
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
