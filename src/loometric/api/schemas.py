"""Closed HTTP envelopes. Nested objects retain their existing strict CLI contracts."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class ClosedModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class CapacityRequest(ClosedModel):
    scenario: dict[str, Any]


class DispatchRequest(ClosedModel):
    instance: dict[str, Any]


class VerifyRequest(DispatchRequest):
    schedule: dict[str, Any]


class CompareRequest(ClosedModel):
    baseline: dict[str, Any]
    specification: dict[str, Any]


class SuccessResponse(ClosedModel):
    api_version: str = "v1"
    request_id: str
    data: dict[str, Any]


class ErrorDetail(ClosedModel):
    code: str
    message: str
    details: list[dict[str, Any]]


class ErrorResponse(ClosedModel):
    api_version: str = "v1"
    request_id: str
    error: ErrorDetail


REQUEST_MODELS = {
    "capacity": CapacityRequest,
    "dispatch": DispatchRequest,
    "verify": VerifyRequest,
    "compare": CompareRequest,
}
