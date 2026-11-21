import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from loometric.api.errors import ApiError
from loometric.api.job_schemas import JobInfo, JobResult
from loometric.api.job_settings import default_job_limits
from loometric.api.jobs import JobRegistry
from loometric.api.settings import default_limits


def terminal(registry, job_id):
    deadline = time.monotonic() + 5
    while True:
        value = registry.status(job_id)
        if value["status"] not in {"QUEUED", "RUNNING"}:
            return value
        assert time.monotonic() < deadline
        time.sleep(0.001)


def test_atomic_admission_saturation_and_cancelled_queue_never_executes():
    release, entered = threading.Event(), threading.Event()
    executed = []

    def runner(kind, body, cancel, on_started):
        executed.append(body)
        on_started(123)
        entered.set()
        while not release.wait(0.01) and not cancel.is_set():
            pass
        return {"result": {}, "execution": {}}

    registry = JobRegistry(default_limits(), default_job_limits(), runner=runner)
    registry.start()
    try:
        first = registry.submit("scheduling", "first")
        assert entered.wait(2)

        def submit(number):
            try:
                return registry.submit("scheduling", str(number))
            except ApiError as exc:
                return exc.code

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(submit, range(8)))
        admitted = [r for r in results if isinstance(r, dict)]
        assert len(admitted) == 2 and results.count("JOB_QUEUE_FULL") == 6
        assert all(r["status"] == "QUEUED" for r in admitted)
        assert registry._reserved_bytes == 3 * registry.policy.max_result_bytes
        for queued in admitted:
            cancelled, accepted = registry.cancel(queued["job_id"])
            assert accepted and cancelled["status"] == "CANCELLED"
        registry.cancel(first["job_id"])
        assert terminal(registry, first["job_id"])["status"] == "CANCELLED"
        assert executed == ["first"]
        assert registry._reserved_bytes == registry._retained_bytes == 0
    finally:
        release.set()
        registry.close()
    assert not registry._thread.is_alive()


def test_cancellation_accepted_before_completion_wins_and_keeps_capacity():
    finishing, cleanup = threading.Event(), threading.Event()

    def runner(kind, body, cancel, on_started):
        on_started(123)
        finishing.set()
        assert cleanup.wait(3)
        return {"result": {"already_computed": True}, "execution": {}}

    policy = default_job_limits().model_copy(update={"max_waiting_jobs": 0})
    registry = JobRegistry(default_limits(), policy, runner=runner)
    registry.start()
    try:
        job = registry.submit("scheduling", "body")
        assert finishing.wait(2)
        info, accepted = registry.cancel(job["job_id"])
        assert accepted and info["status"] == "RUNNING" and info["phase"] == "CLEANING_UP"
        assert not info["cancellation_available"]
        with pytest.raises(ApiError) as caught:
            registry.submit("scheduling", "second")
        assert caught.value.code == "JOB_QUEUE_FULL"
        assert registry._reserved_bytes == policy.max_result_bytes
        cleanup.set()
        assert terminal(registry, job["job_id"])["status"] == "CANCELLED"
        with pytest.raises(ApiError) as caught:
            registry.result(job["job_id"])
        assert caught.value.code == "JOB_CANCELLED"
        assert registry._reserved_bytes == 0
    finally:
        cleanup.set()
        registry.close()


def test_completion_before_cancel_retains_success_and_safe_schema():
    registry = JobRegistry(
        default_limits(),
        default_job_limits(),
        runner=lambda *a: {"result": {"verified": True}, "execution": {}},
    )
    registry.start()
    try:
        job = registry.submit("scheduling", "body")
        info = terminal(registry, job["job_id"])
        validated = JobInfo.model_validate(info)
        assert validated.status == "SUCCEEDED" and validated.result_available
        assert validated.submitted_at <= validated.started_at <= validated.completed_at
        before = registry.result(job["job_id"])
        after, accepted = registry.cancel(job["job_id"])
        assert not accepted and after == info
        assert registry.result(job["job_id"]) == before
        assert JobResult.model_validate_json(before).result == {"verified": True}
        assert registry._retained_bytes == len(before) and registry._reserved_bytes == 0
        assert len(job["job_id"]) == 32
    finally:
        registry.close()


def test_monotonic_retention_tombstone_then_missing_and_no_unsafe_eviction():
    tick = [0.0]
    policy = default_job_limits().model_copy(
        update={"terminal_ttl_seconds": 2, "expired_ttl_seconds": 2, "max_stored_jobs": 1}
    )
    registry = JobRegistry(
        default_limits(),
        policy,
        clock=lambda: tick[0],
        runner=lambda *a: {"result": {}, "execution": {}},
    )
    registry.start()
    try:
        job = registry.submit("scheduling", "body")
        terminal(registry, job["job_id"])
        with pytest.raises(ApiError) as caught:
            registry.submit("scheduling", "second")
        assert caught.value.code == "JOB_REGISTRY_FULL"
        tick[0] = 2
        assert registry.status(job["job_id"])["status"] == "EXPIRED"
        assert registry._retained_bytes == registry._reserved_bytes == 0
        with pytest.raises(ApiError) as caught:
            registry.result(job["job_id"])
        assert caught.value.status == 410
        tick[0] = 4
        with pytest.raises(ApiError) as caught:
            registry.status(job["job_id"])
        assert caught.value.code == "JOB_NOT_FOUND"
        registry.submit("scheduling", "after expiry")
    finally:
        registry.close()


def test_queue_age_expiration_releases_reservation_without_running():
    tick = [0.0]
    release = threading.Event()
    executed = []

    def runner(kind, body, cancel, on_started):
        executed.append(body)
        assert release.wait(3)
        return {"result": {}, "execution": {}}

    policy = default_job_limits().model_copy(update={"queue_timeout_seconds": 1})
    registry = JobRegistry(default_limits(), policy, runner=runner, clock=lambda: tick[0])
    registry.start()
    try:
        registry.submit("scheduling", "first")
        queued = registry.submit("scenarios", "expired")
        tick[0] = 1
        assert registry.status(queued["job_id"])["status"] == "EXPIRED"
        assert registry._reserved_bytes == policy.max_result_bytes
        assert "expired" not in executed
    finally:
        release.set()
        registry.close()


def test_result_capacity_reserved_atomically_before_admission():
    policy = default_job_limits().model_copy(
        update={"max_result_bytes": 1024, "max_retained_result_bytes": 1024}
    )
    registry = JobRegistry(
        default_limits(), policy, runner=lambda *a: {"result": {}, "execution": {}}
    )
    registry.start()
    try:
        job = registry.submit("scheduling", "body")
        terminal(registry, job["job_id"])
        with pytest.raises(ApiError) as caught:
            registry.submit("scheduling", "second")
        assert caught.value.code == "JOB_RESULT_CAPACITY"
        assert registry._retained_bytes + registry._reserved_bytes <= 1024
    finally:
        registry.close()


@pytest.mark.parametrize(
    "mode,code",
    [
        ("oversize", "RESPONSE_LIMIT_EXCEEDED"),
        ("exception", "EXECUTION_FAILED"),
        ("timeout", "EXECUTION_TIMEOUT"),
    ],
)
def test_failure_paths_release_all_reservations_and_never_expose_raw_errors(mode, code):
    def runner(*args):
        if mode == "oversize":
            return {"result": {"too_big": "x" * 2048}, "execution": {}}
        if mode == "timeout":
            raise ApiError(504, "EXECUTION_TIMEOUT", "safe")
        raise RuntimeError("secret /private/path traceback")

    policy = default_job_limits().model_copy(update={"max_result_bytes": 1024})
    registry = JobRegistry(default_limits(), policy, runner=runner)
    registry.start()
    try:
        job = registry.submit("scheduling", "body")
        info = terminal(registry, job["job_id"])
        assert info["status"] == "FAILED" and info["error_code"] == code
        assert "private" not in json.dumps(info, default=str)
        assert registry._retained_bytes == registry._reserved_bytes == 0
    finally:
        registry.close()


def test_shutdown_cancels_active_and_queued_then_joins_and_restart_has_no_records():
    entered = threading.Event()

    def runner(kind, body, cancel, on_started):
        entered.set()
        assert cancel.wait(3)
        return {"result": {}, "execution": {}}

    registry = JobRegistry(default_limits(), default_job_limits(), runner=runner)
    registry.start()
    active = registry.submit("scheduling", "first")
    assert entered.wait(2)
    queued = registry.submit("scheduling", "second")
    registry.close()
    assert not registry._thread.is_alive()
    assert registry.status(active["job_id"])["status"] == "CANCELLED"
    assert registry.status(queued["job_id"])["status"] == "CANCELLED"
    assert registry._retained_bytes == registry._reserved_bytes == 0
    with pytest.raises(ApiError) as caught:
        registry.submit("scheduling", "new")
    assert caught.value.status == 503
    restarted = JobRegistry(default_limits(), default_job_limits())
    with pytest.raises(ApiError) as caught:
        restarted.status(active["job_id"])
    assert caught.value.code == "JOB_NOT_FOUND"
