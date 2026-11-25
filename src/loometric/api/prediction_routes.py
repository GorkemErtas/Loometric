"""Authenticated research inference, separately isolated from planning algorithms."""

from fastapi import APIRouter, Request

from loometric.api.errors import ApiError
from loometric.api.prediction_schemas import SyntheticPredictionRequest
from loometric.api.prediction_schemas_v2 import (
    SyntheticPredictionRequestV2,
)
from loometric.api.prediction_service import MAX_BODY_BYTES
from loometric.api.routes import AUTH, ERRORS, _success, bounded_request_body
from loometric.api.schemas import SuccessResponse

PREDICTION_ROUTER = APIRouter(prefix="/api/v1/predictions")


@PREDICTION_ROUTER.post(
    "/synthetic",
    response_model=SuccessResponse,
    responses=ERRORS,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {"schema": SyntheticPredictionRequest.model_json_schema()}
            },
        }
    },
)
async def synthetic_prediction(request: Request, auth: AUTH) -> SuccessResponse:
    # Reuse strict body media/framing/deadline and global admission. The much
    # smaller prediction limit is checked before ML execution; middleware also
    # enforces the global byte ceiling while streaming.
    async with bounded_request_body(request) as body:
        if len(body.encode("utf-8")) > MAX_BODY_BYTES:
            raise ApiError(413, "BODY_TOO_LARGE", "Prediction request exceeds its byte limit.")
        result = await request.app.state.predictions.execute(body)
    return _success(request, result)


@PREDICTION_ROUTER.post(
    "/synthetic/v2",
    response_model=SuccessResponse,
    responses=ERRORS,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {"schema": (SyntheticPredictionRequestV2.model_json_schema())}
            },
        }
    },
)
async def synthetic_prediction_v2(
    request: Request,
    auth: AUTH,
) -> SuccessResponse:
    async with bounded_request_body(request) as body:
        if len(body.encode("utf-8")) > MAX_BODY_BYTES:
            raise ApiError(
                413,
                "BODY_TOO_LARGE",
                "Prediction request exceeds its byte limit.",
            )

        result = await request.app.state.predictions.execute(
            body,
            api_version=2,
        )

    return _success(request, result)
