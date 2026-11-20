import json
import threading

import anyio
import pytest

import loometric.api.services as services
from loometric.api.codec import input_json
from loometric.api.errors import ApiError
from loometric.api.services import OperationService
from loometric.api.settings import default_limits
from loometric.execution import guarded_child


@pytest.mark.parametrize(
    ("worker_status", "http_status"),
    [("TERMINATED_RESOURCE_LIMIT", 504), ("WORKER_FAILED", 500), ("SKIPPED_RESOURCE_LIMIT", 503)],
)
def test_safe_process_error_mapping(monkeypatch, worker_status, http_status):
    monkeypatch.setattr(
        services,
        "guarded_child",
        lambda *a, **kw: (
            None,
            {"status": worker_status, "reason": "secret /private/path traceback"},
        ),
    )
    with pytest.raises(ApiError) as caught:
        OperationService(default_limits())._execute("capacity", "{}")
    assert caught.value.status == http_status
    assert "private" not in json.dumps(caught.value.envelope("request"))


def test_actual_guarded_worker_and_domain_validation(fixture_json):
    service = OperationService(default_limits())
    report = service._execute(
        "dispatch", input_json({"instance": fixture_json("scheduling/competition.json")})
    )
    assert report["verification"]["feasible"] and report["synthetic"]
    with pytest.raises(ApiError) as caught:
        service._execute("dispatch", '{"instance":{}}')
    assert caught.value.status == 422
    assert caught.value.details == [{"domain_code": "INVALID_FIELDS"}]


def test_actual_api_worker_watchdog_terminates_child():
    request = json.dumps(
        {"operation": "capacity", "body": "{}", "limits": default_limits().model_dump()}
    )
    payload, evidence = guarded_child(request, 256, 0.001, worker_module="loometric.api.worker")
    assert payload is None
    assert evidence["status"] == "TERMINATED_RESOURCE_LIMIT"


def test_admission_off_loop_and_cancel_keeps_slot_until_work_stops(monkeypatch):
    entered, finish, done = threading.Event(), threading.Event(), threading.Event()

    def fake_worker(*args, **kwargs):
        entered.set()
        assert finish.wait(3)
        done.set()
        return {"data": {"ok": True}}, {}

    monkeypatch.setattr(services, "guarded_child", fake_worker)

    async def run():
        service = OperationService(
            default_limits().model_copy(update={"max_concurrent_requests": 1})
        )
        scope = None

        async def first():
            nonlocal scope
            with anyio.CancelScope() as scope:
                async with service.admit():
                    await service.execute("capacity", "{}")

        async with anyio.create_task_group() as group:
            group.start_soon(first)
            with anyio.fail_after(3):
                while not entered.is_set():
                    await anyio.sleep(0.001)
            # Reaching here while the thread waits proves the loop remains responsive.
            scope.cancel()
            await anyio.sleep(0)
            assert not done.is_set()
            with pytest.raises(ApiError) as caught:
                async with service.admit():
                    pytest.fail("Cancelled request released a live worker's slot")
            assert caught.value.status == 429
            finish.set()
        assert done.is_set()
        async with service.admit():
            pass

    anyio.run(run)
