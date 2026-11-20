"""Native resource boundary tests, distinct from measured matrix outcomes."""

import json
import os
import subprocess
import sys
from dataclasses import asdict

import pytest

import loometric.execution as resources
from loometric.benchmarks.design import ResourceLimits
from loometric.benchmarks.generation import GenerationConfig
from loometric.planning.reporting import json_value


def _request():
    return json.dumps(
        json_value(
            {
                "case": "resource-test",
                "generation": asdict(GenerationConfig(orders=2, target_load_percent=20)),
                "resource_limits": asdict(ResourceLimits()),
                "wall_budget_seconds": 1,
                "deterministic_budget": 1,
                "solver_seed": 42,
            }
        )
    )


def test_actual_native_child_has_enforced_memory_guard_and_measured_peak():
    payload, measurements = resources.guarded_child(_request(), 768, 30)
    assert payload is not None, measurements
    assert payload["deterministic"]["audit_verification"]["feasible"]
    assert payload["measurements"]["peak_working_set_bytes"] > 0
    if os.name == "nt":
        assert 0 < measurements["peak_committed_bytes"] <= 768 * 1024**2
        assert payload["measurements"]["memory_backend"] == "windows-job-aggregate-commit"


def test_actual_whole_child_watchdog_reports_resource_stop_not_infeasibility():
    payload, measurements = resources.guarded_child(_request(), 768, 0.001)
    assert payload is None
    assert measurements["status"] == "TERMINATED_RESOURCE_LIMIT"
    assert "watchdog" in measurements["reason"]


@pytest.mark.skipif(os.name != "nt", reason="Windows-specific Job Object failure path")
def test_unavailable_hard_memory_guard_fails_closed(monkeypatch):
    def denied(*args):
        raise OSError("injected job assignment failure")

    monkeypatch.setattr(resources, "WindowsJob", denied)
    payload, measurements = resources.guarded_child(_request(), 768, 5)
    assert payload is None and measurements["status"] == "SKIPPED_RESOURCE_LIMIT"
    assert "injected job assignment failure" in measurements["reason"]


@pytest.mark.skipif(os.name != "nt", reason="Windows-specific guard assertion")
def test_worker_refuses_native_work_outside_requested_job():
    code = """
from loometric.benchmarks.resources import apply_child_memory_limit
try:
    apply_child_memory_limit(768*1024**2)
except OSError:
    print('guard rejected')
else:
    raise AssertionError('Unguarded worker was accepted')
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0 and "guard rejected" in result.stdout
