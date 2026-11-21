import ctypes
import json
import os
import time
from ctypes import wintypes
from pathlib import Path

import pytest

import loometric.execution as execution
from loometric.api.codec import input_json
from loometric.api.errors import ApiError
from loometric.api.job_settings import default_job_limits
from loometric.api.jobs import JobRegistry
from loometric.api.settings import default_limits
from loometric.benchmarks.design import load_design
from loometric.benchmarks.generation import generate_instance
from loometric.scheduling.loading import instance_json

ROOT = Path(__file__).resolve().parents[2]


def native_hook(tmp_path, monkeypatch, *, memory_failure=False):
    marker = tmp_path / "native-phase.json"
    (tmp_path / "sitecustomize.py").write_text(
        r"""
import builtins,json,os,pathlib,sys
original_import=builtins.__import__
patched=False
def observe(name,*args,**kwargs):
    global patched
    result=original_import(name,*args,**kwargs)
    module=sys.modules.get('loometric.optimization.solver')
    if not patched and module is not None and hasattr(module,'_solve_phase'):
        patched=True
        solve=module._solve_phase
        def phase(*values,**options):
            path=pathlib.Path(os.environ['LOOMETRIC_TEST_PHASE_MARKER'])
            data={'pid':os.getpid(),'phase':'RUNNING'}
            path.write_text(json.dumps(data),encoding='utf-8')
            if os.environ.get('LOOMETRIC_TEST_MEMORY_FAILURE')=='1':
                bytearray(2*1024**3)  # Intentionally impossible under the real hard cap.
            outcome=solve(*values,**options)
            path.write_text(json.dumps({'pid':os.getpid(),'phase':'FINISHED'}),encoding='utf-8')
            return outcome
        module._solve_phase=phase
    return result
builtins.__import__=observe
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("PYTHONPATH", str(tmp_path) + os.pathsep + str(ROOT / "src"))
    monkeypatch.setenv("LOOMETRIC_TEST_PHASE_MARKER", str(marker))
    if memory_failure:
        monkeypatch.setenv("LOOMETRIC_TEST_MEMORY_FAILURE", "1")
    return marker


def is_running(pid):
    if os.name == "nt":
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        api.OpenProcess.restype = wintypes.HANDLE
        api.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        api.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = api.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            return bool(api.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
        finally:
            api.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        status = Path(f"/proc/{pid}/stat")
        return not status.exists() or status.read_text().split()[2] != "Z"
    except ProcessLookupError:
        return False


def wait_terminal(registry, job_id):
    deadline = time.monotonic() + 20
    while True:
        status = registry.status(job_id)
        if status["status"] not in {"QUEUED", "RUNNING"}:
            return status
        assert time.monotonic() < deadline
        time.sleep(0.005)


@pytest.mark.parametrize("stop", ["cancel", "shutdown"])
def test_actual_inflight_native_work_is_dead_before_capacity_is_released(
    stop, tmp_path, monkeypatch
):
    marker = native_hook(tmp_path, monkeypatch)
    case = next(
        c
        for c in load_design(ROOT / "configs/m03c_benchmark.json").cases
        if c.name == "medium-p90-s42"
    )
    body = '{"instance":' + instance_json(generate_instance(case.generation)).strip() + "}"
    registry = JobRegistry(default_limits(), default_job_limits())
    registry.start()
    try:
        job = registry.submit("scheduling", body)
        deadline = time.monotonic() + 10
        while True:
            try:
                phase = json.loads(marker.read_text(encoding="utf-8"))
                if phase["phase"] == "RUNNING":
                    time.sleep(0.02)
                    if json.loads(marker.read_text(encoding="utf-8"))["phase"] == "RUNNING":
                        break
            except (OSError, json.JSONDecodeError):
                pass
            assert time.monotonic() < deadline, registry.status(job["job_id"])
            time.sleep(0.001)
        native_pid = phase["pid"]
        assert is_running(native_pid)
        stop_started = time.monotonic()
        if stop == "cancel":
            registry.cancel(job["job_id"])
        else:
            registry.close()
        assert wait_terminal(registry, job["job_id"])["status"] == "CANCELLED"
        assert not is_running(native_pid), "Capacity released before native termination"
        elapsed = time.monotonic() - stop_started
        evidence_path = ROOT / ".tmp/m05b-cancellation.json"
        evidence = (
            json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.exists() else {}
        )
        evidence[stop] = {
            "elapsed_seconds": elapsed,
            "native_pid_stopped_before_terminal": True,
            "reserved_result_bytes": registry._reserved_bytes,
        }
        evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        with pytest.raises(ApiError) as caught:
            registry.result(job["job_id"])
        assert caught.value.code == "JOB_CANCELLED"
        assert registry._reserved_bytes == 0
    finally:
        registry.close()


def test_actual_whole_job_watchdog_reaps_outer_process(monkeypatch, fixture_json):
    children = []
    original = execution.subprocess.Popen

    def track(*args, **kwargs):
        process = original(*args, **kwargs)
        children.append(process)
        return process

    monkeypatch.setattr(execution.subprocess, "Popen", track)
    policy = default_job_limits().model_copy(
        update={"wall_seconds": 1, "optimizer_wall_seconds": 1}
    )
    registry = JobRegistry(default_limits(), policy)
    registry.start()
    try:
        # A controlled startup delay makes watchdog expiry deterministic, without
        # adding any caller-controlled operation or delay to the production worker.
        original_resume = execution._resume_windows_child
        if os.name == "nt":

            def delayed(pid):
                original_resume(pid)
                time.sleep(1.05)

            monkeypatch.setattr(execution, "_resume_windows_child", delayed)
        else:
            pytest.skip("Controlled suspended-start test is Windows-specific")
        body = input_json({"instance": fixture_json("scheduling/competition.json")})
        job = registry.submit("scheduling", body)
        done = wait_terminal(registry, job["job_id"])
        assert done["status"] == "FAILED" and done["error_code"] == "EXECUTION_TIMEOUT"
        assert children and all(child.poll() is not None for child in children)
        assert registry._reserved_bytes == 0
    finally:
        registry.close()


def test_real_hard_memory_allocation_failure_retains_verified_greedy(
    tmp_path, monkeypatch, fixture_json
):
    native_hook(tmp_path, monkeypatch, memory_failure=True)
    registry = JobRegistry(default_limits(), default_job_limits())
    registry.start()
    try:
        job = registry.submit(
            "scheduling", input_json({"instance": fixture_json("scheduling/competition.json")})
        )
        done = wait_terminal(registry, job["job_id"])
        assert done["status"] == "SUCCEEDED", done
        result = json.loads(registry.result(job["job_id"]))
        evaluated = result["result"]["evaluation"]
        assert evaluated["selected_producer"] == "greedy" and evaluated["verification"]["feasible"]
        assert evaluated["optimizer"]["status"] == "TERMINATED_RESOURCE_LIMIT"
        assert evaluated["optimizer"]["metrics"] is None
        assert evaluated["fallback_reason"] == "TERMINATED_RESOURCE_LIMIT"
        if os.name == "nt":
            assert result["execution"]["peak_committed_bytes"] <= 768 * 1024**2
    finally:
        registry.close()
