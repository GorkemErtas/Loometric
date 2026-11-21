"""Loopback-only HTTP boundary, restricted CORS and configured local Bearer auth."""

import ipaddress
import json
import logging
import re
from secrets import compare_digest
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.datastructures import Headers
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from loometric.api.errors import ApiError
from loometric.api.settings import Settings

LOGGER = logging.getLogger("loometric.api")
BEARER = HTTPBearer(auto_error=False, scheme_name="LocalBearer")


async def require_auth(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(BEARER)],
) -> None:
    values = request.headers.getlist("authorization")
    expected = request.app.state.settings.token.get_secret_value()
    value = values[0] if len(values) == 1 else ""
    match = re.fullmatch(r"(?i:Bearer) ([A-Za-z0-9_-]{32,128})", value)
    supplied = match[1] if match else ""
    if not compare_digest(supplied, expected):
        raise ApiError(401, "AUTHENTICATION_REQUIRED", "A valid local Bearer token is required.")


class LocalBoundaryMiddleware:
    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        self.settings = settings

    def _guard(self, scope: Scope) -> str | None:
        peer = scope.get("client")
        try:
            local = peer is not None and ipaddress.ip_address(peer[0]).is_loopback
        except ValueError:
            local = False
        if not local:
            raise ApiError(403, "LOCAL_ACCESS_ONLY", "This API accepts loopback clients only.")
        headers = Headers(scope=scope)
        hosts = headers.getlist("host")
        match = re.fullmatch(
            r"(?:localhost|127\.0\.0\.1|\[::1\])(?::([0-9]{1,5}))?",
            hosts[0] if len(hosts) == 1 else "",
        )
        if match is None or (match[1] is not None and not 1 <= int(match[1]) <= 65535):
            raise ApiError(403, "LOCAL_HOST_REQUIRED", "A literal local Host header is required.")
        origins = headers.getlist("origin")
        origin = origins[0] if len(origins) == 1 else None
        if origins and (len(origins) != 1 or origin not in self.settings.cors_origins):
            raise ApiError(403, "ORIGIN_REJECTED", "Browser origin is not allowed.")
        lengths = headers.getlist("content-length")
        if len(lengths) > 1 or (lengths and not re.fullmatch(r"[0-9]{1,12}", lengths[0])):
            raise ApiError(400, "INVALID_HEADERS", "Invalid HTTP body headers.")
        if lengths and int(lengths[0]) > self.settings.limits.max_body_bytes:
            raise ApiError(413, "BODY_TOO_LARGE", "Request body exceeds the API byte limit.")
        if lengths and headers.get("transfer-encoding") is not None:
            raise ApiError(400, "INVALID_HEADERS", "Ambiguous HTTP body framing.")
        if scope.get("query_string"):
            raise ApiError(400, "UNSUPPORTED_QUERY", "This API does not accept query parameters.")
        return origin

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        started = False
        origin = None

        async def safe_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                extra = [
                    (b"x-request-id", request_id.encode("ascii")),
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                ]
                if origin:
                    extra.extend(
                        [
                            (b"access-control-allow-origin", origin.encode("ascii")),
                            (b"access-control-expose-headers", b"X-Request-ID"),
                            (b"vary", b"Origin"),
                        ]
                    )
                message["headers"] = list(message.get("headers", [])) + extra
            await send(message)

        try:
            origin = self._guard(scope)
            headers = Headers(scope=scope)
            if scope["method"] == "OPTIONS" and origin:
                requested = {
                    v.strip().lower()
                    for v in headers.get("access-control-request-headers", "").split(",")
                    if v.strip()
                }
                if headers.get("access-control-request-method") not in {
                    "GET",
                    "POST",
                    "DELETE",
                } or not requested <= {"authorization", "content-type"}:
                    raise ApiError(
                        403, "CORS_REJECTED", "Preflight method or headers are not allowed."
                    )
                response = Response(
                    status_code=204,
                    headers={
                        "Access-Control-Allow-Methods": "GET, POST, DELETE",
                        "Access-Control-Allow-Headers": "Authorization, Content-Type",
                        "Access-Control-Max-Age": "600",
                    },
                )
                await response(scope, receive, safe_send)
                return
            await self.app(scope, receive, safe_send)
        except ApiError as exc:
            if started:
                raise
            await error_response(exc, request_id)(scope, receive, safe_send)
        except Exception:
            if started:
                raise
            # Log only server-generated ID and a fixed code, never request/exception data.
            LOGGER.error(json.dumps({"request_id": request_id, "code": "INTERNAL_ERROR"}))
            exc = ApiError(500, "INTERNAL_ERROR", "The local API could not complete the request.")
            await error_response(exc, request_id)(scope, receive, safe_send)


def error_response(error: ApiError, request_id: str) -> JSONResponse:
    headers = {}
    if error.status == 401:
        headers["WWW-Authenticate"] = "Bearer"
    if error.status == 429:
        headers["Retry-After"] = "1"
    return JSONResponse(error.envelope(request_id), status_code=error.status, headers=headers)
