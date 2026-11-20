import json
import threading

import anyio
import httpx
import pytest

import loometric.api.services as services
import loometric.execution as execution
from loometric.api.app import create_app
from loometric.api.codec import input_json


def test_http_concurrency_rejection_and_health_remains_responsive(api_settings, monkeypatch):
    finish = threading.Event()
    entered = 0
    lock = threading.Lock()

    def busy_worker(*args, **kwargs):
        nonlocal entered
        with lock:
            entered += 1
        assert finish.wait(5)
        return {"data": {"controlled_test": True}}, {}

    monkeypatch.setattr(services, "guarded_child", busy_worker)

    async def run():
        app = create_app(api_settings)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1)),
            base_url="http://127.0.0.1",
            headers={"Authorization": "Bearer " + api_settings.token.get_secret_value()},
        ) as client:
            responses = []

            async def post():
                responses.append(
                    await client.post(
                        "/api/v1/planning/capacity",
                        content=b"{}",
                        headers={"Content-Type": "application/json"},
                    )
                )

            async with anyio.create_task_group() as group:
                group.start_soon(post)
                group.start_soon(post)
                with anyio.fail_after(3):
                    while entered < 2:
                        await anyio.sleep(0.001)
                rejected = await client.post(
                    "/api/v1/planning/capacity",
                    content=b"{}",
                    headers={"Content-Type": "application/json"},
                )
                assert rejected.status_code == 429
                assert rejected.headers["retry-after"] == "1"
                assert (await client.get("/api/v1/health")).status_code == 200
                finish.set()
            assert len(responses) == 2 and all(r.status_code == 200 for r in responses)

    anyio.run(run)


def test_actual_http_timeout_kills_and_reaps_worker(api_settings, monkeypatch):
    children = []
    real_popen, real_guard = execution.subprocess.Popen, execution.guarded_child

    def track(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        children.append(process)
        return process

    def short_guard(request, memory, timeout, **kwargs):
        return real_guard(request, memory, 0.001, **kwargs)

    monkeypatch.setattr(execution.subprocess, "Popen", track)
    monkeypatch.setattr(services, "guarded_child", short_guard)

    async def run():
        app = create_app(api_settings)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1)),
            base_url="http://127.0.0.1",
        ) as client:
            response = await client.post(
                "/api/v1/planning/capacity",
                content=b"{}",
                headers={
                    "Authorization": "Bearer " + api_settings.token.get_secret_value(),
                    "Content-Type": "application/json",
                },
            )
        assert response.status_code == 504
        assert response.json()["error"]["code"] == "EXECUTION_TIMEOUT"
        assert children and all(child.poll() is not None for child in children)

    anyio.run(run)


async def raw_request(app, api_settings, receive, *, headers=()):
    sent = []

    async def send(message):
        sent.append(message)

    await app(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/v1/planning/capacity",
            "raw_path": b"/api/v1/planning/capacity",
            "query_string": b"",
            "client": ("127.0.0.1", 1),
            "server": ("127.0.0.1", 8000),
            "headers": [
                (b"host", b"127.0.0.1"),
                (b"content-type", b"application/json"),
                (b"authorization", ("Bearer " + api_settings.token.get_secret_value()).encode()),
                *headers,
            ],
        },
        receive,
        send,
    )
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    result = json.loads(
        b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    )
    return status, result


@pytest.mark.parametrize(
    "mode", ["oversize", "slow", "disconnect", "length_mismatch", "duplicate_length"]
)
def test_stream_body_envelope_fails_before_execution(api_settings, monkeypatch, mode):
    settings = api_settings.model_copy(
        update={"limits": api_settings.limits.model_copy(update={"body_timeout_seconds": 1})}
    )
    app = create_app(settings)

    def forbidden(*args, **kwargs):
        pytest.fail("Invalid body reached the worker")

    monkeypatch.setattr(app.state.operations, "execute", forbidden)

    async def receive():
        if mode == "slow":
            await anyio.sleep(2)
        if mode == "disconnect":
            return {"type": "http.disconnect"}
        return {
            "type": "http.request",
            "body": b" " * 262145 if mode == "oversize" else b"{}",
            "more_body": False,
        }

    async def run():
        headers = [(b"content-length", b"3")] if mode == "length_mismatch" else []
        if mode == "duplicate_length":
            headers = [(b"content-length", b"2"), (b"content-length", b"2")]
        status, value = await raw_request(app, settings, receive, headers=headers)
        assert (
            status
            == {
                "oversize": 413,
                "slow": 408,
                "disconnect": 400,
                "length_mismatch": 400,
                "duplicate_length": 400,
            }[mode]
        )
        assert value["error"]["code"]

    anyio.run(run)


def test_worker_response_size_is_bounded(api_settings, fixture_json):
    limits = api_settings.limits.model_copy(update={"max_response_bytes": 1024})
    with pytest.raises(services.ApiError) as caught:
        services.OperationService(limits)._execute(
            "capacity", input_json({"scenario": fixture_json("planning/capacity-demo.json")})
        )
    assert caught.value.code == "RESPONSE_LIMIT_EXCEEDED"


def test_internal_errors_are_sanitized_and_logs_omit_exception_input(
    api_settings, caplog, monkeypatch
):
    app = create_app(api_settings)

    def fail(*args, **kwargs):
        raise RuntimeError("secret /private/path traceback")

    monkeypatch.setattr(app.state.operations, "admit", fail)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1)),
            base_url="http://127.0.0.1",
        ) as client:
            response = await client.post(
                "/api/v1/planning/capacity",
                content=b"{}",
                headers={
                    "Authorization": "Bearer " + api_settings.token.get_secret_value(),
                    "Content-Type": "application/json",
                },
            )
        assert response.status_code == 500
        assert response.json()["error"]["code"] == "INTERNAL_ERROR"
        for text in (response.text, caplog.text):
            assert "private" not in text and "traceback" not in text
            assert api_settings.token.get_secret_value() not in text

    anyio.run(run)
