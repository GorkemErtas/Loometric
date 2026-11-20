"""Trusted startup configuration; clients cannot supply limits, hosts or paths."""

import os
import re
from importlib.resources import files

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class Limits(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    max_body_bytes: int = Field(ge=1024, le=262144)
    max_response_bytes: int = Field(ge=1024, le=2097152)
    max_depth: int = Field(ge=2, le=24)
    max_nodes: int = Field(ge=1, le=10000)
    max_collection_items: int = Field(ge=1, le=256)
    max_string_length: int = Field(ge=1, le=4096)
    max_number_length: int = Field(ge=1, le=128)
    max_decimal_exponent: int = Field(ge=1, le=100)
    max_orders: int = Field(ge=1, le=32)
    max_operations: int = Field(ge=1, le=96)
    max_changes: int = Field(ge=1, le=64)
    max_concurrent_requests: int = Field(ge=1, le=2)
    body_timeout_seconds: int = Field(ge=1, le=3)
    execution_timeout_seconds: int = Field(ge=1, le=5)
    process_memory_mib: int = Field(ge=128, le=256)


def default_limits() -> Limits:
    return Limits.model_validate_json(
        files("loometric.api").joinpath("default_limits.json").read_text(encoding="utf-8")
    )


class Settings(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    token: SecretStr
    limits: Limits = Field(default_factory=default_limits)
    port: int = Field(default=8000, ge=1024, le=65535)
    # Explicit browser development origins; neither wildcard nor credentialed CORS.
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")

    def model_post_init(self, context: object) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", self.token.get_secret_value()):
            raise ValueError("Invalid local API configuration.")
        allowed = re.compile(r"http://(?:localhost|127\.0\.0\.1|\[::1\]):([0-9]{1,5})")
        if len(self.cors_origins) > 8 or len(set(self.cors_origins)) != len(self.cors_origins):
            raise ValueError("Invalid local API configuration.")
        for origin in self.cors_origins:
            match = allowed.fullmatch(origin)
            if match is None or not 1024 <= int(match[1]) <= 65535:
                raise ValueError("Invalid local API configuration.")


def settings_from_environment() -> Settings:
    """Never echo Pydantic's input-bearing validation errors for credential config."""
    try:
        return Settings(
            token=SecretStr(os.environ.get("LOOMETRIC_API_TOKEN", "")),
            port=int(os.environ.get("LOOMETRIC_API_PORT", "8000")),
        )
    except (ValueError, TypeError):
        raise ValueError("Invalid local API configuration; check token and port.") from None
