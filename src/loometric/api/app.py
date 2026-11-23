"""Explicit application construction; importing domain/CLI code never starts HTTP."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import HTMLResponse, JSONResponse

from loometric.api.errors import ApiError
from loometric.api.job_routes import JOB_ROUTER
from loometric.api.jobs import JobRegistry
from loometric.api.prediction_routes import PREDICTION_ROUTER
from loometric.api.prediction_service import PredictionService
from loometric.api.routes import ROUTER
from loometric.api.security import LocalBoundaryMiddleware, error_response
from loometric.api.services import OperationService, wait_for_cleanup
from loometric.api.settings import Settings, settings_from_environment


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or settings_from_environment()
    jobs = JobRegistry(settings.limits, settings.job_limits)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        jobs.start()
        try:
            yield
        finally:
            await wait_for_cleanup(jobs.close)

    app = FastAPI(
        title="Loometric local planning API",
        version="1.0.0",
        description="Local synthetic planning and bounded jobs; M01 prediction remains offline.",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/v1/openapi.json",
        swagger_ui_parameters={"persistAuthorization": False},
        swagger_ui_oauth2_redirect_url=None,
    )
    app.state.settings = settings
    app.state.operations = OperationService(settings.limits, settings.job_limits)
    app.state.jobs = jobs
    app.state.predictions = PredictionService()
    app.add_middleware(LocalBoundaryMiddleware, settings=settings)
    app.include_router(ROUTER)
    app.include_router(JOB_ROUTER)
    app.include_router(PREDICTION_ROUTER)

    @app.get("/api/v1/docs", include_in_schema=False, response_class=HTMLResponse)
    async def docs() -> str:
        # No remote Swagger/ReDoc CDN assets: documentation remains fully local.
        return """<!doctype html><html lang="en"><meta charset="utf-8">
<title>Loometric API v1</title><h1>Loometric local API v1</h1>
<p><a href="/api/v1/openapi.json">OpenAPI 3.1 JSON specification</a></p>
<p>Public: GET health. Bearer token required: GET capabilities and all POST operations.</p>
<ul><li>GET /api/v1/health</li><li>GET /api/v1/capabilities</li>
<li>POST /api/v1/planning/capacity — {"scenario": M02 object}</li>
<li>POST /api/v1/scheduling/dispatch — {"instance": M03 object}</li>
<li>POST /api/v1/scheduling/verify — {"instance": M03 object, "schedule": proposal}</li>
<li>POST /api/v1/scenarios/compare — {"baseline": M03 object, "specification": M04 object}</li>
<li>POST /api/v1/jobs/scheduling — {"instance": M03 object}</li>
<li>POST /api/v1/jobs/scenarios — {"baseline": M03 object, "specification": M04 object}</li>
<li>GET /api/v1/jobs/{job_id} — lifecycle status</li>
<li>GET /api/v1/jobs/{job_id}/result — verified result</li>
<li>DELETE /api/v1/jobs/{job_id} — request native cancellation</li>
<li>POST /api/v1/predictions/synthetic — experimental synthetic estimators</li></ul>
<p>Planning decimals are JSON numbers; reported decimals are strings. Only synthetic,
bounded planning is supported. CP-SAT uses jobs. Experimental synthetic prediction
is separate from planning and requires trusted local M08C artifacts. No client file paths.</p>
<p>See docs/architecture/api-foundation.md and examples/api/workflow.py in the repository.</p>
<p>Jobs: docs/architecture/optimization-jobs-api.md and examples/api/jobs_workflow.py.</p>
</html>"""

    @app.exception_handler(ApiError)
    async def known_error(request: Request, exc: ApiError) -> JSONResponse:
        return error_response(exc, request.state.request_id)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return error_response(
            ApiError(exc.status_code, "HTTP_ERROR", "The requested HTTP operation is unavailable."),
            request.state.request_id,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(
            ApiError(422, "INVALID_REQUEST", "Request does not match the API contract."),
            request.state.request_id,
        )

    return app
