"""Explicit HTTPS gateway trust never relaxes the direct loopback boundary."""

import pytest
from pydantic import ValidationError
from starlette.types import Scope

from loometric.api.errors import ApiError
from loometric.api.security import LocalBoundaryMiddleware
from loometric.api.settings import Settings


@pytest.mark.parametrize(
    "origin",
    [
        "http://demo.example",
        "https://demo.example/",
        "https://user@demo.example",
        "https://demo.example:443",
        "https://demo.example:0",
        "https://*.example",
        "https://demo.example/path",
        "https://demo.example?x=1",
    ],
)
def test_invalid_public_origin_never_enables_proxy_trust(api_settings, origin):
    with pytest.raises((ValueError, ValidationError)):
        Settings(token=api_settings.token, public_origin=origin)


def test_explicit_https_gateway_accepts_only_its_host_origin_and_loopback_peer(api_settings):
    configured = Settings(token=api_settings.token, public_origin="https://demo.example")
    middleware = LocalBoundaryMiddleware(None, configured)
    scope: Scope = {
        "type": "http",
        "client": ("127.0.0.1", 1234),
        "headers": [(b"host", b"demo.example"), (b"origin", b"https://demo.example")],
        "query_string": b"",
    }
    assert middleware._guard(scope) == "https://demo.example"
    for changes in (
        {"client": ("203.0.113.1", 1234)},
        {"headers": [(b"host", b"other.example")]},
        {"headers": [(b"host", b"demo.example"), (b"origin", b"https://other.example")]},
    ):
        with pytest.raises(ApiError):
            middleware._guard({**scope, **changes})
    with pytest.raises(ApiError):
        LocalBoundaryMiddleware(None, api_settings)._guard(scope)
