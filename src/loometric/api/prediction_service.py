"""ML-free HTTP process adapter to a separate, hard-limited prediction worker."""

import json
from importlib.resources import files

import anyio

from loometric.api.errors import ApiError
from loometric.api.services import wait_for_cleanup, worker_data
from loometric.execution import guarded_child

MEMORY_MIB = 768
TIMEOUT_SECONDS = 10
MAX_BODY_BYTES = 8192
MAX_RESPONSE_BYTES = 131072


def trusted_receipt() -> str:
    # Package configuration is independent of artifact publication and never read
    # from the generated manifest as an implicit trust root.
    config = json.loads(
        files("loometric.experimental_ml").joinpath("trusted_v1.json").read_text(encoding="utf-8")
    )
    if (
        config["directory"] != "data/processed/experimental_ml/v1"
        or config["model_version"] != "synthetic-experimental-v1"
    ):
        raise ValueError("Unsupported experimental registry")
    return config["manifest_sha256"]


class PredictionService:
    def __init__(self):
        self._admission = anyio.CapacityLimiter(1)

    async def execute(self, body: str, api_version: int = 1) -> dict:
        try:
            self._admission.acquire_nowait()
        except anyio.WouldBlock:
            raise ApiError(
                429, "SERVER_BUSY", "The experimental inference slot is occupied."
            ) from None
        try:
            return await wait_for_cleanup(self._execute, body, api_version)
        finally:
            self._admission.release()

    def _execute(self, body: str, api_version: int = 1) -> dict:
        if len(body.encode("utf-8")) > MAX_BODY_BYTES:
            raise ApiError(413, "BODY_TOO_LARGE", "Prediction request exceeds its byte limit.")
        try:
            request = json.dumps(
                {
                    "body": body,
                    "receipt": trusted_receipt(),
                    **({"api_version": api_version} if api_version in (2, 3) else {}),
                }
            )
            payload, measurements = guarded_child(
                request,
                MEMORY_MIB,
                TIMEOUT_SECONDS,
                worker_module="loometric.api.prediction_worker",
            )
        except (OSError, ValueError, KeyError):
            raise ApiError(
                503,
                "EXPERIMENTAL_ARTIFACT_UNAVAILABLE",
                "Trusted experimental models are unavailable; check local setup.",
            ) from None
        if payload and payload.get("error", {}).get("code") == "EXPERIMENTAL_ARTIFACT_UNAVAILABLE":
            raise ApiError(
                503,
                "EXPERIMENTAL_ARTIFACT_UNAVAILABLE",
                "Trusted experimental models are unavailable; check local setup.",
            )
        result = worker_data(payload, measurements)
        result["execution"] = {
            "whole_child_wall_seconds": measurements["whole_child_wall_seconds"],
            "peak_committed_bytes": measurements["peak_committed_bytes"],
            "memory_limit_mib": MEMORY_MIB,
            "deadline_seconds": TIMEOUT_SECONDS,
            "thread_limit": 1,
            "max_concurrent_inference": 1,
            "memory_backend": payload["memory_backend"],
        }
        return result
