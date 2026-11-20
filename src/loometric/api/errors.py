"""Safe API errors: domain exception text and process diagnostics never cross HTTP."""

from typing import Any


class ApiError(Exception):
    def __init__(
        self, status: int, code: str, message: str, details: list[dict[str, Any]] | None = None
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details or []

    def envelope(self, request_id: str) -> dict[str, Any]:
        return {
            "api_version": "v1",
            "request_id": request_id,
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def complexity_error() -> ApiError:
    return ApiError(422, "INPUT_LIMIT_EXCEEDED", "Input exceeds the synchronous API envelope.")
