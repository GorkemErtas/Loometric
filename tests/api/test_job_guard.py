import json
import threading

import pytest
from pydantic import ValidationError

import loometric.execution as execution
from loometric.api.job_settings import JobLimits, default_job_limits
from loometric.api.settings import default_limits


def request():
    return json.dumps(
        {"operation": "capacity", "body": "{}", "limits": default_limits().model_dump()}
    )


def test_cancelled_before_spawn_starts_no_process(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Pre-cancelled work spawned a child")

    monkeypatch.setattr(execution.subprocess, "Popen", forbidden)
    event = threading.Event()
    event.set()
    payload, measured = execution.guarded_child(
        request(), 256, 5, worker_module="loometric.api.worker", cancel_event=event
    )
    assert payload is None and measured["status"] == "CANCELLED"


def test_actual_startup_cancel_reaps_child_before_return(monkeypatch):
    children = []
    original = execution.subprocess.Popen

    def track(*args, **kwargs):
        child = original(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(execution.subprocess, "Popen", track)
    event = threading.Event()
    payload, measured = execution.guarded_child(
        request(),
        256,
        5,
        worker_module="loometric.api.worker",
        cancel_event=event,
        on_started=lambda pid: event.set(),
    )
    assert payload is None and measured["status"] == "CANCELLED"
    assert children and all(child.poll() is not None for child in children)
    assert measured["whole_child_wall_seconds"] > 0


def test_polling_watchdog_retains_hard_termination():
    payload, measured = execution.guarded_child(
        request(), 256, 0.001, worker_module="loometric.api.worker", cancel_event=threading.Event()
    )
    assert payload is None and measured["status"] == "TERMINATED_RESOURCE_LIMIT"


def test_cancellable_guard_delivers_ordinary_result_without_polling_loss():
    payload, measured = execution.guarded_child(
        request(), 256, 5, worker_module="loometric.api.worker", cancel_event=threading.Event()
    )
    assert payload["error"]["code"] == "INVALID_ENVELOPE"
    assert measured["returncode"] == 0


def test_job_defaults_and_hard_configuration_ceilings():
    defaults = default_job_limits().model_dump()
    assert defaults["max_active_jobs"] == 1 and defaults["max_waiting_jobs"] == 2
    for name, value in defaults.items():
        with pytest.raises(ValidationError):
            JobLimits(**{**defaults, name: value * 10000})
    with pytest.raises(ValidationError):
        JobLimits(**{**defaults, "max_retained_result_bytes": 1024})
    assert default_limits().max_concurrent_requests == 2
    assert default_limits().execution_timeout_seconds == 5
    assert default_limits().process_memory_mib == 256
