import asyncio
import json
import os
from pathlib import Path
from secrets import token_urlsafe

import httpx
import pytest
from pydantic import SecretStr

from loometric.api.app import create_app
from loometric.api.errors import ApiError
from loometric.api.prediction_service import PredictionService
from loometric.api.settings import Settings
from loometric.execution import guarded_child


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def native_app(publication_fixture, tmp_path, monkeypatch):
    import shutil

    artifacts = tmp_path / "artifacts"
    shutil.copytree(publication_fixture["directory"], artifacts / "v1")
    # Test-only trusted startup seam. No HTTP input can modify the artifact
    # allowlist, PYTHONPATH, trusted receipt, limits or this audit guard.
    root = Path(__file__).resolve().parents[2]
    source = publication_fixture["root"] / "source"
    (tmp_path / "sitecustomize.py").write_text(
        "import pathlib,sys\n"
        "import loometric.experimental_ml.constants as constants\n"
        f"constants.ARTIFACT_ROOT=pathlib.Path({str(artifacts)!r})\n"
        f"blocked=[pathlib.Path({str(root / 'data')!r}),pathlib.Path({str(source)!r})]\n"
        "def guard(event,args):\n"
        "    if event=='open' and isinstance(args[0],(str,bytes)):\n"
        "        raw=args[0].decode() if isinstance(args[0],bytes) else args[0]\n"
        "        path=pathlib.Path(raw).resolve()\n"
        "        if any(path.is_relative_to(p) for p in blocked):\n"
        "            raise AssertionError('Inference accessed protected training/test data')\n"
        "sys.addaudithook(guard)\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PYTHONPATH", str(tmp_path) + os.pathsep + str(root / "src"))
    monkeypatch.setattr(
        "loometric.api.prediction_service.trusted_receipt", lambda: publication_fixture["receipt"]
    )
    settings = Settings(token=SecretStr(token_urlsafe(32)))
    return create_app(settings), settings, artifacts


def request_body():
    path = Path(__file__).resolve().parents[2] / "examples/api/synthetic-prediction.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.anyio
async def test_authenticated_real_native_inference_no_training_data_or_planning_mutation(
    native_app,
):
    app, settings, _ = native_app
    before = settings.model_dump_json()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1234)),
        base_url="http://127.0.0.1",
    ) as client:
        assert (
            await client.post("/api/v1/predictions/synthetic", json=request_body())
        ).status_code == 401
        client.headers["Authorization"] = "Bearer " + settings.token.get_secret_value()
        response = await client.post("/api/v1/predictions/synthetic", json=request_body())
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
        data = response.json()["data"]
        assert len(data["results"]) == 3 and all(
            r["prediction"] is not None for r in data["results"]
        )
        assert data["execution"]["memory_backend"] in (
            "windows-job-aggregate-commit",
            "linux-rlimit-as",
        )
        assert data["execution"]["whole_child_wall_seconds"] < 10
        assert data["capacity_application_authorized"] is False
        assert settings.model_dump_json() == before
        body = request_body()
        body["inputs"]["planned_workers"] = 0
        response = await client.post("/api/v1/predictions/synthetic", json=body)
        assert response.status_code == 200
        assert all(
            r["prediction"] is None and r["support"]["status"] == "ABSTAIN"
            for r in response.json()["data"]["results"]
        )
        assert (
            "data/raw" not in response.text
            and settings.token.get_secret_value() not in response.text
        )


@pytest.mark.anyio
async def test_native_integrity_failure_closed_and_invalid_envelope(native_app):
    app, settings, artifacts = native_app
    (artifacts / "v1/random_forest.joblib").write_bytes(b"untrusted pickle replacement")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1234)),
        base_url="http://127.0.0.1",
        headers={"Authorization": "Bearer " + settings.token.get_secret_value()},
    ) as client:
        response = await client.post("/api/v1/predictions/synthetic", json=request_body())
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "EXPERIMENTAL_ARTIFACT_UNAVAILABLE"
        assert str(artifacts) not in response.text
        body = request_body()
        body["inputs"]["realized_workers"] = 5
        response = await client.post("/api/v1/predictions/synthetic", json=body)
        assert response.status_code == 422
        response = await client.post(
            "/api/v1/predictions/synthetic",
            content='{"x":1,"x":2}',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400


@pytest.mark.anyio
async def test_auth_origin_and_size_limits_do_not_launch_worker(monkeypatch):
    monkeypatch.setattr(
        PredictionService, "_execute", lambda *a: pytest.fail("Rejected HTTP reached worker")
    )
    settings = Settings(token=SecretStr(token_urlsafe(32)))
    app = create_app(settings)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1)), base_url="http://127.0.0.1"
    ) as client:
        assert (await client.post("/api/v1/predictions/synthetic", json={})).status_code == 401
        client.headers["Authorization"] = "Bearer " + settings.token.get_secret_value()
        assert (
            await client.post(
                "/api/v1/predictions/synthetic", json={}, headers={"Origin": "https://evil.example"}
            )
        ).status_code == 403
        assert (
            await client.post(
                "/api/v1/predictions/synthetic",
                content=" " * 8193,
                headers={"Content-Type": "application/json"},
            )
        ).status_code == 413
        assert (
            await client.post("/api/v1/predictions/synthetic?path=x", json={})
        ).status_code == 400


@pytest.mark.anyio
async def test_single_inference_slot_is_retained_until_bounded_cleanup(monkeypatch):
    service = PredictionService()
    entered, release = asyncio.Event(), asyncio.Event()

    async def blocked(*args):
        entered.set()
        await release.wait()
        return {"done": True}

    monkeypatch.setattr("loometric.api.prediction_service.wait_for_cleanup", blocked)
    first = asyncio.create_task(service.execute("{}"))
    await entered.wait()
    with pytest.raises(ApiError) as caught:
        await service.execute("{}")
    assert caught.value.status == 429
    release.set()
    assert await first == {"done": True}
    assert await service.execute("{}") == {"done": True}


def test_prediction_worker_uses_existing_hard_watchdog():
    payload, evidence = guarded_child(
        json.dumps({"body": "{}", "receipt": "a" * 64}),
        768,
        0.001,
        worker_module="loometric.api.prediction_worker",
    )
    assert payload is None and evidence["status"] == "TERMINATED_RESOURCE_LIMIT"
    assert evidence["whole_child_wall_seconds"] < 5


@pytest.mark.anyio
async def test_task_cancellation_does_not_release_slot_before_cleanup(monkeypatch):
    from threading import Event

    service = PredictionService()
    entered, release = Event(), Event()

    def blocking(body):
        entered.set()
        assert release.wait(5)
        return {"done": True}

    monkeypatch.setattr(service, "_execute", blocking)
    first = asyncio.create_task(service.execute("{}"))
    assert await asyncio.to_thread(entered.wait, 5)
    first.cancel()
    await asyncio.sleep(0)
    try:
        with pytest.raises(ApiError) as caught:
            await service.execute("{}")
        assert caught.value.status == 429 and not first.done()
    finally:
        release.set()
    with pytest.raises(asyncio.CancelledError):
        await first
    assert await service.execute("{}") == {"done": True}


@pytest.mark.parametrize(
    "status,expected",
    [("SKIPPED_RESOURCE_LIMIT", 503), ("TERMINATED_RESOURCE_LIMIT", 504), ("WORKER_FAILED", 500)],
)
def test_native_failure_mapping_never_exposes_details(monkeypatch, status, expected):
    monkeypatch.setattr(
        "loometric.api.prediction_service.guarded_child",
        lambda *a, **k: (None, {"status": status, "reason": "private path and payload"}),
    )
    with pytest.raises(ApiError) as caught:
        PredictionService()._execute("{}")
    assert caught.value.status == expected
    assert "private" not in str(caught.value)
