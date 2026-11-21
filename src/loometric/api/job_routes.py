"""Authenticated async-job HTTP boundary; lifecycle execution belongs to the registry."""

import json

from fastapi import APIRouter, Request
from starlette.responses import Response

from loometric.api.job_schemas import JOB_REQUEST_MODELS, JobResponse, JobResultResponse, JobType
from loometric.api.routes import AUTH, ERRORS, bounded_request_body
from loometric.api.schemas import ErrorResponse

JOB_ROUTER = APIRouter(prefix="/api/v1/jobs")
JOB_ERRORS = {
    **ERRORS,
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    410: {"model": ErrorResponse},
}


def _schema(kind: JobType) -> dict:
    return {
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {"schema": JOB_REQUEST_MODELS[kind].model_json_schema()}
            },
        }
    }


async def _submit(request: Request, response: Response, kind: JobType) -> JobResponse:
    async with bounded_request_body(request) as body:
        await request.app.state.operations.execute("prepare_" + kind + "_job", body)
        info = request.app.state.jobs.submit(kind, body)
    response.headers["Location"] = info["polling_url"]
    response.headers["Retry-After"] = "1"
    return JobResponse(request_id=request.state.request_id, data=info)


@JOB_ROUTER.post(
    "/scheduling",
    status_code=202,
    response_model=JobResponse,
    responses=JOB_ERRORS,
    openapi_extra=_schema("scheduling"),
)
async def submit_scheduling(request: Request, response: Response, auth: AUTH) -> JobResponse:
    return await _submit(request, response, "scheduling")


@JOB_ROUTER.post(
    "/scenarios",
    status_code=202,
    response_model=JobResponse,
    responses=JOB_ERRORS,
    openapi_extra=_schema("scenarios"),
)
async def submit_scenario(request: Request, response: Response, auth: AUTH) -> JobResponse:
    return await _submit(request, response, "scenarios")


@JOB_ROUTER.get("/{job_id}", response_model=JobResponse, responses=JOB_ERRORS)
async def status(job_id: str, request: Request, auth: AUTH) -> JobResponse:
    return JobResponse(
        request_id=request.state.request_id, data=request.app.state.jobs.status(job_id)
    )


@JOB_ROUTER.get("/{job_id}/result", response_model=JobResultResponse, responses=JOB_ERRORS)
async def result(job_id: str, request: Request, auth: AUTH) -> Response:
    # Serialize domain reports off-loop once at publication. Retrieval only wraps
    # immutable cached UTF-8 bytes with this HTTP request's own correlation ID.
    data = request.app.state.jobs.result(job_id)
    content = (
        b'{"api_version":"v1","request_id":'
        + json.dumps(request.state.request_id).encode("ascii")
        + b',"data":'
        + data
        + b"}"
    )
    return Response(content, media_type="application/json")


@JOB_ROUTER.delete(
    "/{job_id}",
    response_model=JobResponse,
    responses={**JOB_ERRORS, 200: {"model": JobResponse}},
    status_code=202,
)
async def cancel(job_id: str, request: Request, response: Response, auth: AUTH) -> JobResponse:
    info, accepted = request.app.state.jobs.cancel(job_id)
    response.status_code = 202 if accepted else 200
    return JobResponse(request_id=request.state.request_id, data=info)
