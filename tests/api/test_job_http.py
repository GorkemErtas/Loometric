import threading

import anyio
import httpx
import pytest

from loometric.api.app import create_app
from loometric.api.codec import input_json
from loometric.api.job_schemas import JobResponse, JobResultResponse
from loometric.api.jobs import JobRegistry


async def poll(client, url):
    with anyio.fail_after(20):
        while True:
            response = await client.get(url)
            assert response.status_code == 200, response.text
            info = JobResponse.model_validate_json(response.content).data
            if info.status not in {"QUEUED", "RUNNING"}:
                return info
            await anyio.sleep(0.01)


async def client_for(app, settings):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1)),
        base_url="http://127.0.0.1",
        headers={
            "Authorization": "Bearer " + settings.token.get_secret_value(),
            "Content-Type": "application/json",
        },
    )


def test_all_job_endpoints_real_workflow_and_synchronous_contract(api_settings, fixture_json):
    async def run():
        app = create_app(api_settings)
        async with app.router.lifespan_context(app), await client_for(app, api_settings) as client:
            body = {"instance": fixture_json("scheduling/hand-enumerated.json")}
            submitted = await client.post("/api/v1/jobs/scheduling", content=input_json(body))
            assert submitted.status_code == 202, submitted.text
            accepted = JobResponse.model_validate_json(submitted.content).data
            assert submitted.headers["location"] == accepted.polling_url
            assert submitted.headers["x-request-id"] == submitted.json()["request_id"]
            done = await poll(client, accepted.polling_url)
            assert done.status == "SUCCEEDED"
            result = await client.get(done.result_url)
            validated = JobResultResponse.model_validate_json(result.content)
            assert validated.request_id == result.headers["x-request-id"]
            assert validated.data.result["evaluation"]["verification"]["feasible"]
            # Cancellation after completion cannot erase the verified result.
            cancelled = await client.delete(done.polling_url)
            assert (
                cancelled.status_code == 200 and cancelled.json()["data"]["status"] == "SUCCEEDED"
            )
            spec = fixture_json("scenarios/capacity-optimizer-recovery.json")
            spec["scheduling"]["solver"] = {
                "wall_time_seconds_per_phase": 1,
                "deterministic_time_per_phase": 1,
            }
            compared = await client.post(
                "/api/v1/jobs/scenarios",
                content=input_json(
                    {
                        "baseline": fixture_json("scenarios/routing-baseline.json"),
                        "specification": spec,
                    }
                ),
            )
            assert compared.status_code == 202, compared.text
            done = await poll(client, compared.json()["data"]["polling_url"])
            assert done.status == "SUCCEEDED"
            data = (await client.get(done.result_url)).json()["data"]["result"]
            assert data["same_demand_verified"] and data["synthetic"]
            after = data["scenario"]["evaluation"]
            assert (
                after["selected_producer"] == "cp_sat" and after["metrics"]["scheduled_units"] == 28
            )
            assert after["selected_full_lexicographic_optimal"]
            sync = await client.post(
                "/api/v1/scenarios/compare",
                content=input_json(
                    {
                        "baseline": fixture_json("scenarios/capacity-baseline.json"),
                        "specification": fixture_json("scenarios/additional-workers.json"),
                    }
                ),
            )
            assert sync.status_code == 200
            assert sync.json()["data"]["scenario"]["evaluation"]["metrics"]["scheduled_units"] == 55
            assert (await client.get("/api/v1/health")).status_code == 200

    anyio.run(run)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/scheduling"),
        ("POST", "/scenarios"),
        ("GET", "/unknown"),
        ("GET", "/unknown/result"),
        ("DELETE", "/unknown"),
    ],
)
def test_authentication_precedes_job_lookup_and_body(api_settings, method, path):
    async def run():
        app = create_app(api_settings)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1)),
            base_url="http://127.0.0.1",
        ) as client:
            response = await client.request(method, "/api/v1/jobs" + path, content=b"bad JSON")
            assert response.status_code == 401
            assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

    anyio.run(run)


@pytest.mark.parametrize(
    ("body", "expected", "code"),
    [
        (b"{", 400, "INVALID_JSON"),
        (b'{"instance":{},"instance":{}}', 400, "INVALID_JSON"),
        (b'{"instance":{},"executable":"secret"}', 422, "INVALID_ENVELOPE"),
        (b'{"instance":{}}', 422, "DOMAIN_VALIDATION_FAILED"),
        (b" " * 262145, 413, "BODY_TOO_LARGE"),
    ],
)
def test_invalid_submissions_create_no_record(api_settings, body, expected, code):
    async def run():
        app = create_app(api_settings)
        async with app.router.lifespan_context(app), await client_for(app, api_settings) as client:
            response = await client.post("/api/v1/jobs/scheduling", content=body)
            assert response.status_code == expected, response.text
            assert response.json()["error"]["code"] == code
            assert not app.state.jobs._entries

    anyio.run(run)


def test_http_queue_cancel_pending_result_and_sync_slots_are_separate(
    api_settings, fixture_json, monkeypatch
):
    original = JobRegistry._run_native

    def wait_job(self, kind, body, cancel, on_started):
        on_started(123)
        assert cancel.wait(15)
        return {"result": {}, "execution": {}}

    monkeypatch.setattr(JobRegistry, "_run_native", wait_job)

    async def run():
        app = create_app(api_settings)
        async with app.router.lifespan_context(app), await client_for(app, api_settings) as client:
            body = input_json({"instance": fixture_json("scheduling/competition.json")})
            admitted = []
            for _ in range(3):
                response = await client.post("/api/v1/jobs/scheduling", content=body)
                assert response.status_code == 202, response.text
                admitted.append(response.json()["data"])
            assert admitted[1]["status"] == admitted[2]["status"] == "QUEUED"
            assert (await client.get(admitted[0]["result_url"])).status_code == 409
            response = await client.post("/api/v1/jobs/scheduling", content=body)
            assert (
                response.status_code == 429 and response.json()["error"]["code"] == "JOB_QUEUE_FULL"
            )
            assert (
                await client.post("/api/v1/scheduling/dispatch", content=body)
            ).status_code == 200
            assert (await client.get("/api/v1/health")).status_code == 200
            for info in reversed(admitted):
                cancelled = await client.delete(info["polling_url"])
                assert cancelled.status_code == 202
            done = await poll(client, admitted[0]["polling_url"])
            assert done.status == "CANCELLED" and not done.result_available
            response = await client.get(done.result_url)
            assert (
                response.status_code == 409 and response.json()["error"]["code"] == "JOB_CANCELLED"
            )
            assert (await client.get("/api/v1/jobs/missing")).status_code == 404
            headers = {
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "DELETE",
                "Access-Control-Request-Headers": "Authorization",
            }
            assert (await client.options(done.polling_url, headers=headers)).status_code == 204

    try:
        anyio.run(run)
    finally:
        monkeypatch.setattr(JobRegistry, "_run_native", original)


def test_client_disconnect_does_not_cancel_an_admitted_job(api_settings, fixture_json, monkeypatch):
    finish, running = threading.Event(), threading.Event()

    def runner(self, kind, body, cancel, on_started):
        running.set()
        assert finish.wait(5)
        assert not cancel.is_set()
        return {"result": {}, "execution": {}}

    monkeypatch.setattr(JobRegistry, "_run_native", runner)

    async def run():
        app = create_app(api_settings)
        async with app.router.lifespan_context(app):
            async with await client_for(app, api_settings) as client:
                submitted = await client.post(
                    "/api/v1/jobs/scheduling",
                    content=input_json({"instance": fixture_json("scheduling/competition.json")}),
                )
                info = submitted.json()["data"]
                assert await anyio.to_thread.run_sync(running.wait, 2)
            # Disposing the submitting client/transport leaves the admitted job owned
            # by the registry. A new authenticated client can retrieve its result.
            assert app.state.jobs.status(info["job_id"])["status"] == "RUNNING"
            finish.set()
            async with await client_for(app, api_settings) as client:
                assert (await poll(client, info["polling_url"])).status == "SUCCEEDED"

    try:
        anyio.run(run)
    finally:
        finish.set()


def test_expired_http_result_and_restart_missing_ids(api_settings, fixture_json, monkeypatch):
    monkeypatch.setattr(JobRegistry, "_run_native", lambda *a: {"result": {}, "execution": {}})

    async def run():
        app = create_app(api_settings)
        tick = [0.0]
        app.state.jobs._clock = lambda: tick[0]
        async with app.router.lifespan_context(app), await client_for(app, api_settings) as client:
            response = await client.post(
                "/api/v1/jobs/scheduling",
                content=input_json({"instance": fixture_json("scheduling/competition.json")}),
            )
            info = response.json()["data"]
            assert (await poll(client, info["polling_url"])).status == "SUCCEEDED"
            tick[0] = 300
            assert (await client.get(info["result_url"])).status_code == 410
            assert (await client.get(info["polling_url"])).json()["data"]["status"] == "EXPIRED"
        restarted = create_app(api_settings)
        async with (
            restarted.router.lifespan_context(restarted),
            await client_for(restarted, api_settings) as client,
        ):
            response = await client.get(info["polling_url"])
            assert (
                response.status_code == 404 and response.json()["error"]["code"] == "JOB_NOT_FOUND"
            )

    anyio.run(run)
