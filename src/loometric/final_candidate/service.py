"""Fixed offline child using shared native hard-memory primitives, without altering old workers."""

import json
import os
import subprocess
import sys
from time import perf_counter

from loometric.execution import WindowsJob, _resume_windows_child


def execute(operation: str, **receipts) -> dict:
    if operation not in ("develop", "evaluate", "reproduce"):
        raise ValueError("CLOSED_OFFLINE_OPERATION_REQUIRED")
    request = {"operation": operation, "authorized": True, **receipts}
    return _execute(request)


def _execute(request: dict) -> dict:
    start = perf_counter()
    child = subprocess.Popen(
        [sys.executable, "-m", "loometric.final_candidate.worker"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        creationflags=0x4 | 0x08000000 if os.name == "nt" else 0,
    )
    job = None
    measurements = {}
    try:
        if os.name == "nt":
            job = WindowsJob(child.pid, 2048 * 1024**2)
            request["windows_job_name"] = job.name
            _resume_windows_child(child.pid)
        stdout, stderr = child.communicate(json.dumps(request), timeout=1200)
        if child.returncode != 0:
            raise ValueError("OFFLINE_WORKER_FAILED:" + stderr[-500:])
        result = json.loads(stdout)
        if "error" in result:
            raise ValueError(result["error"])
        return {**result, "execution": measurements}
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate()
        if job:
            measurements["peak_committed_bytes"] = job.peak_committed_bytes()
            job.close()
        measurements["whole_child_wall_seconds"] = perf_counter() - start
