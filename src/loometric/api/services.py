"""Bounded admission and off-loop calls to the shared hard process watchdog."""

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import anyio

from loometric.api.errors import ApiError
from loometric.api.settings import Limits
from loometric.execution import guarded_child

WORKER_ERRORS = {
    "INVALID_JSON": (400, "Expected strict UTF-8 JSON with unique keys."),
    "INVALID_ENVELOPE": (422, "Request must match the closed endpoint envelope."),
    "INPUT_LIMIT_EXCEEDED": (422, "Input exceeds the synchronous API envelope."),
    "SYNTHETIC_REQUIRED": (422, "Only explicitly synthetic inputs are supported."),
    "UNSUPPORTED_OPERATION": (422, "Operation is not supported by this API."),
    "UNSUPPORTED_METHOD": (422, "M05A supports greedy scheduling only."),
    "DOMAIN_VALIDATION_FAILED": (422, "Input failed domain validation."),
    "INVALID_VALUE": (422, "Input contains an unsupported value."),
    "RESOURCE_GUARD_UNAVAILABLE": (503, "Hard process isolation is unavailable."),
    "MEMORY_LIMIT_EXCEEDED": (503, "The bounded worker exceeded its memory envelope."),
    "EXECUTION_FAILED": (500, "The bounded operation failed."),
}


class OperationService:
    def __init__(self, limits: Limits) -> None:
        self.limits = limits
        self._admission = anyio.CapacityLimiter(limits.max_concurrent_requests)

    @asynccontextmanager
    async def admit(self) -> AsyncIterator[None]:
        try:
            self._admission.acquire_nowait()
        except anyio.WouldBlock:
            raise ApiError(429, "SERVER_BUSY", "The local execution slots are occupied.") from None
        try:
            yield
        finally:
            self._admission.release()

    async def execute(self, operation: str, body: str) -> dict[str, Any]:
        # Client disconnect does not cancel a process. Keep the admission slot until
        # normal completion or the shared watchdog kills/reaps the actual child.
        with anyio.CancelScope(shield=True):
            return await anyio.to_thread.run_sync(self._execute, operation, body)

    def _execute(self, operation: str, body: str) -> dict[str, Any]:
        request = json.dumps(
            {"operation": operation, "body": body, "limits": self.limits.model_dump()}
        )
        try:
            payload, measurements = guarded_child(
                request,
                self.limits.process_memory_mib,
                self.limits.execution_timeout_seconds,
                worker_module="loometric.api.worker",
            )
        except OSError:
            raise ApiError(
                503, "RESOURCE_GUARD_UNAVAILABLE", "Hard process isolation is unavailable."
            ) from None
        if payload is None:
            status = measurements.get("status")
            if status == "TERMINATED_RESOURCE_LIMIT":
                raise ApiError(
                    504, "EXECUTION_TIMEOUT", "The worker was terminated at its deadline."
                )
            if status == "SKIPPED_RESOURCE_LIMIT":
                raise ApiError(
                    503, "RESOURCE_GUARD_UNAVAILABLE", "Hard process isolation is unavailable."
                )
            raise ApiError(500, "EXECUTION_FAILED", "The bounded operation failed.")
        if "error" in payload:
            error = payload["error"]
            status, message = WORKER_ERRORS.get(
                error.get("code"), WORKER_ERRORS["EXECUTION_FAILED"]
            )
            details = error.get("details", [])
            domain_code = error.get("domain_code")
            if isinstance(domain_code, str) and domain_code.isupper() and len(domain_code) < 80:
                details = [{"domain_code": domain_code}]
            raise ApiError(status, error.get("code", "EXECUTION_FAILED"), message, details)
        if not isinstance(payload.get("data"), dict):
            raise ApiError(500, "EXECUTION_FAILED", "The bounded operation failed.")
        return payload["data"]
