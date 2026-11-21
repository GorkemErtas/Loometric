"""Bounded admission and off-loop calls to the shared hard process watchdog."""

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any, TypeVar

import anyio

from loometric.api.errors import ApiError
from loometric.api.job_settings import JobLimits, default_job_limits
from loometric.api.settings import Limits
from loometric.execution import guarded_child

WORKER_ERRORS = {
    "INVALID_JSON": (400, "Expected strict UTF-8 JSON with unique keys."),
    "INVALID_ENVELOPE": (422, "Request must match the closed endpoint envelope."),
    "INPUT_LIMIT_EXCEEDED": (422, "Input exceeds the synchronous API envelope."),
    "RESPONSE_LIMIT_EXCEEDED": (422, "The resulting report exceeds the synchronous API envelope."),
    "SYNTHETIC_REQUIRED": (422, "Only explicitly synthetic inputs are supported."),
    "UNSUPPORTED_OPERATION": (422, "Operation is not supported by this API."),
    "UNSUPPORTED_METHOD": (422, "M05A supports greedy scheduling only."),
    "DOMAIN_VALIDATION_FAILED": (422, "Input failed domain validation."),
    "INVALID_VALUE": (422, "Input contains an unsupported value."),
    "JOB_SOLVER_POLICY": (422, "Requested solver settings exceed the job policy."),
    "RESOURCE_GUARD_UNAVAILABLE": (503, "Hard process isolation is unavailable."),
    "MEMORY_LIMIT_EXCEEDED": (503, "The bounded worker exceeded its memory envelope."),
    "EXECUTION_FAILED": (500, "The bounded operation failed."),
}


class OperationService:
    def __init__(self, limits: Limits, job_limits: JobLimits | None = None) -> None:
        self.limits = limits
        self.job_limits = job_limits or default_job_limits()
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
        return await wait_for_cleanup(self._execute, operation, body)

    def _execute(self, operation: str, body: str) -> dict[str, Any]:
        request = json.dumps(
            {
                "operation": operation,
                "body": body,
                "limits": self.limits.model_dump(),
                "job_limits": self.job_limits.model_dump(),
            }
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
        return worker_data(payload, measurements)


def worker_data(payload: dict[str, Any] | None, measurements: dict[str, Any]) -> dict[str, Any]:
    """Map private worker receipts through the same safe whitelist for sync/jobs."""
    if payload is None:
        status = measurements.get("status")
        if status == "TERMINATED_RESOURCE_LIMIT":
            raise ApiError(504, "EXECUTION_TIMEOUT", "The worker was terminated at its deadline.")
        if status == "SKIPPED_RESOURCE_LIMIT":
            raise ApiError(
                503, "RESOURCE_GUARD_UNAVAILABLE", "Hard process isolation is unavailable."
            )
        raise ApiError(500, "EXECUTION_FAILED", "The bounded operation failed.")
    if "error" in payload:
        error = payload["error"]
        code = error.get("code")
        if code not in WORKER_ERRORS:
            code = "EXECUTION_FAILED"
        status, message = WORKER_ERRORS[code]
        details = []
        if code == "INVALID_ENVELOPE":
            details = [{"rule": "required_object_fields_only"}]
        domain_code = error.get("domain_code")
        if (
            code == "DOMAIN_VALIDATION_FAILED"
            and isinstance(domain_code, str)
            and domain_code.isascii()
            and domain_code.isupper()
            and domain_code.replace("_", "").isalpha()
            and len(domain_code) < 80
        ):
            details = [{"domain_code": domain_code}]
        raise ApiError(status, code, message, details)
    if not isinstance(payload.get("data"), dict):
        raise ApiError(500, "EXECUTION_FAILED", "The bounded operation failed.")
    return payload["data"]


T = TypeVar("T")


async def wait_for_cleanup(function: Callable[..., T], *args: Any) -> T:
    """Retain ownership of bounded blocking cleanup through AnyIO/raw task cancellation."""
    with anyio.CancelScope(shield=True):
        work = asyncio.create_task(anyio.to_thread.run_sync(function, *args))
        cancelled = False
        while True:
            try:
                result = await asyncio.shield(work)
                break
            except asyncio.CancelledError:
                if work.cancelled():
                    raise
                # Raw asyncio Task.cancel bypasses AnyIO's shield. Wait for the
                # same bounded job to finish before propagating cancellation.
                cancelled = True
        if cancelled:
            raise asyncio.CancelledError
        return result
