"""Explicit application construction; importing domain/CLI code never starts HTTP."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import HTMLResponse, JSONResponse

from loometric.api.errors import ApiError
from loometric.api.routes import ROUTER
from loometric.api.security import LocalBoundaryMiddleware, error_response
from loometric.api.services import OperationService
from loometric.api.settings import Settings, settings_from_environment


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or settings_from_environment()
    app = FastAPI(
        title="Loometric local planning API",
        version="1.0.0",
        description="Bounded synthetic planning only. M01 prediction and CP-SAT HTTP are deferred.",
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/v1/openapi.json",
        swagger_ui_parameters={"persistAuthorization": False},
        swagger_ui_oauth2_redirect_url=None,
    )
    app.state.settings = settings
    app.state.operations = OperationService(settings.limits)
    app.add_middleware(LocalBoundaryMiddleware, settings=settings)
    app.include_router(ROUTER)

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
<li>POST /api/v1/scenarios/compare — {"baseline": M03 object, "specification": M04 object}</li></ul>
<p>Planning decimals are JSON numbers; reported decimals are strings. Only synthetic,
bounded greedy planning is supported. No CP-SAT, prediction, jobs or file paths.</p>
<p>See docs/architecture/api-foundation.md and examples/api/workflow.py in the repository.</p>
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
