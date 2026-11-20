"""Versioned HTTP routes; CPU work and domain parsing belong to the bounded service."""

import re
from typing import Annotated

import anyio
from fastapi import APIRouter, Depends, Request
from starlette.requests import ClientDisconnect

from loometric.api.errors import ApiError
from loometric.api.schemas import REQUEST_MODELS, ErrorResponse, SuccessResponse
from loometric.api.security import require_auth

ROUTER = APIRouter(prefix="/api/v1")
AUTH = Annotated[None, Depends(require_auth)]
ERRORS = {
    status: {"model": ErrorResponse}
    for status in (400, 401, 403, 408, 413, 415, 422, 429, 500, 503, 504)
}


def _success(request: Request, data: dict) -> SuccessResponse:
    return SuccessResponse(request_id=request.state.request_id, data=data)


@ROUTER.get("/health", response_model=SuccessResponse, responses=ERRORS)
async def health(request: Request) -> SuccessResponse:
    return _success(request, {"status": "ok", "api_version": "v1", "service": "loometric"})


@ROUTER.get("/capabilities", response_model=SuccessResponse, responses=ERRORS)
async def capabilities(request: Request, auth: AUTH) -> SuccessResponse:
    return _success(
        request,
        {
            "policy_versions": ["whole-stage-minute-v1"],
            "operations": ["capacity", "dispatch", "verify", "compare"],
            "scenario_changes": [
                "set_workers",
                "set_efficiency",
                "set_availability",
                "add_assignment",
                "remove_assignment",
                "add_downtime",
                "remove_downtime",
                "replace_downtime",
            ],
            "scheduling_methods": ["greedy"],
            "synthetic_only": True,
            "limits": request.app.state.settings.limits.model_dump(),
            "deferred": {
                "cp_sat": "M05B job lifecycle is not implemented; no synchronous solver endpoint.",
                "prediction": "M01 offline; artifact registry and HTTP policy deferred.",
            },
            "limitations": [
                "Loopback development API with one shared secret; no public hosting.",
                "Synthetic conditional results require human review.",
                "No database, jobs, ML data/artifacts or automatic production decisions.",
            ],
        },
    )


async def _run(request: Request, operation: str) -> SuccessResponse:
    headers = request.headers
    media = headers.getlist("content-type")
    if (
        len(media) != 1
        or re.fullmatch(
            r'application/json(?:[ \t]*;[ \t]*charset=(?:utf-8|"utf-8"))?',
            media[0],
            re.IGNORECASE,
        )
        is None
    ):
        raise ApiError(415, "JSON_REQUIRED", "Use application/json with UTF-8 encoding.")
    if headers.get("content-encoding", "identity").lower() != "identity":
        raise ApiError(
            415, "CONTENT_ENCODING_UNSUPPORTED", "Compressed request bodies are unsupported."
        )
    service = request.app.state.operations
    limits = request.app.state.settings.limits
    async with service.admit():
        chunks, size = [], 0
        try:
            with anyio.fail_after(limits.body_timeout_seconds):
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > limits.max_body_bytes:
                        raise ApiError(
                            413, "BODY_TOO_LARGE", "Request body exceeds the API byte limit."
                        )
                    if chunk:
                        chunks.append(chunk)
                    await anyio.lowlevel.checkpoint()
        except TimeoutError:
            raise ApiError(
                408, "BODY_TIMEOUT", "Request body did not arrive before its deadline."
            ) from None
        except ClientDisconnect:
            raise ApiError(
                400, "CLIENT_DISCONNECTED", "Client disconnected before sending its body."
            ) from None
        if headers.get("content-length") is not None and int(headers["content-length"]) != size:
            raise ApiError(400, "INVALID_HEADERS", "Body length differs from Content-Length.")
        try:
            body = b"".join(chunks).decode("utf-8", errors="strict")
        except UnicodeError:
            raise ApiError(
                400, "INVALID_JSON", "Expected strict UTF-8 JSON with unique keys."
            ) from None
        data = await service.execute(operation, body)
    return _success(request, data)


def _request_schema(operation: str) -> dict:
    return {
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {"schema": REQUEST_MODELS[operation].model_json_schema()}
            },
        }
    }


@ROUTER.post(
    "/planning/capacity",
    response_model=SuccessResponse,
    responses=ERRORS,
    openapi_extra=_request_schema("capacity"),
)
async def capacity(request: Request, auth: AUTH) -> SuccessResponse:
    return await _run(request, "capacity")


@ROUTER.post(
    "/scheduling/dispatch",
    response_model=SuccessResponse,
    responses=ERRORS,
    openapi_extra=_request_schema("dispatch"),
)
async def dispatch(request: Request, auth: AUTH) -> SuccessResponse:
    return await _run(request, "dispatch")


@ROUTER.post(
    "/scheduling/verify",
    response_model=SuccessResponse,
    responses=ERRORS,
    openapi_extra=_request_schema("verify"),
)
async def verify(request: Request, auth: AUTH) -> SuccessResponse:
    return await _run(request, "verify")


@ROUTER.post(
    "/scenarios/compare",
    response_model=SuccessResponse,
    responses=ERRORS,
    openapi_extra=_request_schema("compare"),
)
async def compare(request: Request, auth: AUTH) -> SuccessResponse:
    return await _run(request, "compare")
