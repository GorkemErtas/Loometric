"""One bounded supervisor and registry, owned exclusively by an application lifespan."""

import json
import secrets
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import Condition, Event, Thread
from time import monotonic
from typing import Any

from loometric.api.errors import ApiError
from loometric.api.job_schemas import JobPhase, JobStatus, JobType
from loometric.api.job_settings import JobLimits
from loometric.api.services import worker_data
from loometric.api.settings import Limits
from loometric.execution import guarded_child

TERMINAL = {"SUCCEEDED", "FAILED", "CANCELLED", "EXPIRED"}
Runner = Callable[[JobType, str, Event, Callable[[int], None]], dict[str, Any]]


@dataclass
class _Job:
    job_id: str
    job_type: JobType
    body: str
    submitted_at: datetime
    submitted_tick: float
    status: JobStatus = "QUEUED"
    phase: JobPhase = "QUEUED"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    expires_at: datetime | None = None
    completed_tick: float | None = None
    expired_tick: float | None = None
    result: bytes | None = None
    error_code: str | None = None
    cancel: Event = field(default_factory=Event)


class JobRegistry:
    def __init__(
        self,
        limits: Limits,
        jobs: JobLimits,
        *,
        runner: Runner | None = None,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.limits, self.policy = limits, jobs
        self._runner = runner or self._run_native
        self._clock = clock
        self._condition = Condition()
        self._entries: dict[str, _Job] = {}
        self._waiting: deque[_Job] = deque()
        self._active: _Job | None = None
        self._retained_bytes = 0
        self._reserved_bytes = 0
        self._thread: Thread | None = None
        self._closing = False

    def start(self) -> None:
        with self._condition:
            if self._thread is not None or self._closing:
                raise RuntimeError("Job registry is single-use.")
            self._thread = Thread(target=self._work, name="LoometricOptimizationJobs", daemon=False)
            self._thread.start()

    def close(self) -> None:
        with self._condition:
            self._closing = True
            for queued in self._waiting:
                queued.cancel.set()
                self._finish(queued, "CANCELLED")
            self._waiting.clear()
            if self._active is not None:
                self._active.cancel.set()
                self._active.phase = "CLEANING_UP"
            self._condition.notify_all()
            thread = self._thread
        if thread is not None:
            thread.join()  # Never abandon a managed native child to satisfy HTTP shutdown.

    def submit(self, kind: JobType, body: str) -> dict[str, Any]:
        if kind not in ("scheduling", "scenarios"):
            raise ApiError(422, "UNSUPPORTED_OPERATION", "Unknown job type.")
        if len(body.encode("utf-8")) > self.limits.max_body_bytes:
            raise ApiError(413, "BODY_TOO_LARGE", "Request body exceeds the API byte limit.")
        with self._condition:
            self._prune()
            if self._thread is None or self._closing or not self._thread.is_alive():
                raise ApiError(
                    503, "JOB_SERVICE_UNAVAILABLE", "The local job service is unavailable."
                )
            if self._active is not None and len(self._waiting) >= self.policy.max_waiting_jobs:
                raise ApiError(429, "JOB_QUEUE_FULL", "The bounded job queue is full.")
            if len(self._entries) >= self.policy.max_stored_jobs:
                raise ApiError(429, "JOB_REGISTRY_FULL", "The bounded job registry is full.")
            if (
                self._retained_bytes + self._reserved_bytes + self.policy.max_result_bytes
                > self.policy.max_retained_result_bytes
            ):
                raise ApiError(
                    429, "JOB_RESULT_CAPACITY", "Retained results occupy the job memory budget."
                )
            job_id = secrets.token_hex(16)
            while job_id in self._entries:
                job_id = secrets.token_hex(16)
            job = _Job(job_id, kind, body, datetime.now(UTC), self._clock())
            self._entries[job_id] = job
            self._reserved_bytes += self.policy.max_result_bytes
            if self._active is None:
                self._activate(job)
            else:
                self._waiting.append(job)
            self._condition.notify_all()
            return self._info(job)

    def status(self, job_id: str) -> dict[str, Any]:
        with self._condition:
            self._prune()
            return self._info(self._get(job_id))

    def cancel(self, job_id: str) -> tuple[dict[str, Any], bool]:
        with self._condition:
            self._prune()
            job = self._get(job_id)
            requested = job.status not in TERMINAL
            if requested:
                job.cancel.set()
                if job.status == "QUEUED":
                    self._waiting.remove(job)
                    self._finish(job, "CANCELLED")
                else:
                    job.phase = "CLEANING_UP"
            self._condition.notify_all()
            return self._info(job), requested

    def result(self, job_id: str) -> bytes:
        with self._condition:
            self._prune()
            job = self._get(job_id)
            if job.status == "EXPIRED":
                raise ApiError(410, "JOB_EXPIRED", "The retained result has expired.")
            if job.status != "SUCCEEDED" or job.result is None:
                code = (
                    "JOB_NOT_READY" if job.status in {"QUEUED", "RUNNING"} else "JOB_" + job.status
                )
                raise ApiError(
                    409,
                    code,
                    "No completed result is available for this job.",
                    [{"error_code": job.error_code}] if job.error_code else [],
                )
            return job.result

    def _get(self, job_id: str) -> _Job:
        job = self._entries.get(job_id)
        if job is None:
            raise ApiError(
                404, "JOB_NOT_FOUND", "No job exists with this ID in this server lifetime."
            )
        return job

    def _activate(self, job: _Job) -> None:
        job.status, job.phase = "RUNNING", "STARTING_WORKER"
        job.started_at = datetime.now(UTC)
        self._active = job

    def _finish(
        self, job: _Job, status: JobStatus, *, code: str | None = None, result: bytes | None = None
    ) -> None:
        job.status, job.phase = status, "EXPIRED" if status == "EXPIRED" else "TERMINAL"
        job.completed_at, job.completed_tick = datetime.now(UTC), self._clock()
        job.expires_at = job.completed_at + timedelta(seconds=self.policy.terminal_ttl_seconds)
        if status == "EXPIRED":
            job.expired_tick = job.completed_tick
            job.expires_at = job.completed_at + timedelta(seconds=self.policy.expired_ttl_seconds)
        job.error_code, job.result, job.body = code, result, ""
        self._reserved_bytes -= self.policy.max_result_bytes
        self._retained_bytes += len(result) if result is not None else 0

    def _prune(self) -> None:
        tick = self._clock()
        for job in list(self._waiting):
            if tick - job.submitted_tick >= self.policy.queue_timeout_seconds:
                self._waiting.remove(job)
                self._finish(job, "EXPIRED", code="JOB_QUEUE_EXPIRED")
        for job in list(self._entries.values()):
            if job.completed_tick is None:
                continue
            age = tick - job.completed_tick
            if job.status != "EXPIRED" and age >= self.policy.terminal_ttl_seconds:
                if job.result is not None:
                    self._retained_bytes -= len(job.result)
                    job.result = None
                job.status, job.phase = "EXPIRED", "EXPIRED"
                job.expired_tick = job.completed_tick + self.policy.terminal_ttl_seconds
                job.error_code = None
                job.expires_at = job.completed_at + timedelta(
                    seconds=self.policy.terminal_ttl_seconds + self.policy.expired_ttl_seconds
                )
            if (
                job.expired_tick is not None
                and tick - job.expired_tick >= self.policy.expired_ttl_seconds
            ):
                del self._entries[job.job_id]

    def _info(self, job: _Job) -> dict[str, Any]:
        return {
            "job_id": job.job_id,
            "job_type": job.job_type,
            "status": job.status,
            "phase": job.phase,
            "submitted_at": job.submitted_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "expires_at": job.expires_at,
            "cancellation_requested": job.cancel.is_set(),
            "cancellation_available": job.status not in TERMINAL and not job.cancel.is_set(),
            "result_available": job.status == "SUCCEEDED" and job.result is not None,
            "error_code": job.error_code,
            "polling_url": f"/api/v1/jobs/{job.job_id}",
            "result_url": f"/api/v1/jobs/{job.job_id}/result",
        }

    def _work(self) -> None:
        while True:
            with self._condition:
                self._prune()
                while self._active is None:
                    if self._closing:
                        return
                    self._condition.wait(timeout=0.5)
                    self._prune()
                job = self._active

            def started(pid: int, current: _Job = job) -> None:
                with self._condition:
                    if current.status == "RUNNING" and not current.cancel.is_set():
                        current.phase = "WORKER_RUNNING"

            encoded, error = None, None
            try:
                report = self._runner(job.job_type, job.body, job.cancel, started)
                encoded = json.dumps(
                    {"job_id": job.job_id, "job_type": job.job_type, **report},
                    allow_nan=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                if len(encoded) > self.policy.max_result_bytes:
                    encoded, error = None, "RESPONSE_LIMIT_EXCEEDED"
            except ApiError as exc:
                error = exc.code
            except Exception:
                error = "EXECUTION_FAILED"
            with self._condition:
                # This lock defines race precedence. A cancellation accepted before
                # publication wins even when the native result is already buffered.
                if job.cancel.is_set():
                    self._finish(job, "CANCELLED")
                elif error is not None:
                    self._finish(job, "FAILED", code=error)
                else:
                    self._finish(job, "SUCCEEDED", result=encoded)
                self._active = None
                self._prune()
                if self._waiting and not self._closing:
                    self._activate(self._waiting.popleft())
                self._condition.notify_all()

    def _run_native(
        self, kind: JobType, body: str, cancel: Event, on_started: Callable[[int], None]
    ) -> dict[str, Any]:
        request = json.dumps(
            {
                "job_type": kind,
                "body": body,
                "limits": self.limits.model_dump(),
                "job_limits": self.policy.model_dump(),
            }
        )
        try:
            payload, measured = guarded_child(
                request,
                self.policy.process_memory_mib,
                self.policy.wall_seconds,
                worker_module="loometric.api.job_worker",
                cancel_event=cancel,
                on_started=on_started,
            )
        except OSError:
            raise ApiError(
                503, "RESOURCE_GUARD_UNAVAILABLE", "Hard process isolation is unavailable."
            ) from None
        data = worker_data(payload, measured)
        execution = {
            key: measured[key]
            for key in ("whole_child_wall_seconds", "peak_committed_bytes")
            if key in measured
        }
        execution.update(payload.get("execution", {}))
        return {"result": data, "execution": execution}
