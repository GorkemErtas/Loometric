"""Closed job metadata and result contracts; input envelopes reuse M05A schemas."""

from datetime import datetime
from typing import Any, Literal

from loometric.api.schemas import ClosedModel, CompareRequest, DispatchRequest

JobType = Literal["scheduling", "scenarios"]
JobStatus = Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", "EXPIRED"]
JobPhase = Literal[
    "QUEUED", "STARTING_WORKER", "WORKER_RUNNING", "CLEANING_UP", "TERMINAL", "EXPIRED"
]


class JobInfo(ClosedModel):
    job_id: str
    job_type: JobType
    status: JobStatus
    phase: JobPhase
    submitted_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    expires_at: datetime | None
    cancellation_requested: bool
    cancellation_available: bool
    result_available: bool
    error_code: str | None
    polling_url: str
    result_url: str


class JobResponse(ClosedModel):
    api_version: Literal["v1"] = "v1"
    request_id: str
    data: JobInfo


class JobResult(ClosedModel):
    job_id: str
    job_type: JobType
    result: dict[str, Any]
    execution: dict[str, Any]


class JobResultResponse(ClosedModel):
    api_version: Literal["v1"] = "v1"
    request_id: str
    data: JobResult


JOB_REQUEST_MODELS = {"scheduling": DispatchRequest, "scenarios": CompareRequest}
