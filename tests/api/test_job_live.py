import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx


def test_real_http_client_submits_polls_retrieves_and_cancels_twice(api_settings):
    root = Path(__file__).resolve().parents[2]
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    env = {
        **os.environ,
        "LOOMETRIC_API_TOKEN": api_settings.token.get_secret_value(),
        "LOOMETRIC_API_PORT": str(port),
    }
    process = subprocess.Popen(
        [sys.executable, "-m", "loometric.api"],
        env=env,
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=0x08000000 if os.name == "nt" else 0,
    )
    reports = []
    try:
        with httpx.Client(
            base_url=f"http://127.0.0.1:{port}", timeout=1, trust_env=False
        ) as client:
            deadline = time.monotonic() + 10
            while True:
                assert process.poll() is None, "Local API failed startup"
                try:
                    if client.get("/api/v1/health").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                assert time.monotonic() < deadline
                time.sleep(0.05)
        for _ in range(2):
            completed = subprocess.run(
                [sys.executable, "examples/api/jobs_workflow.py"],
                env=env,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=45,
            )
            assert completed.returncode == 0, completed.stderr + completed.stdout
            report = json.loads(completed.stdout)
            assert report["scenario"]["producer"] == "cp_sat"
            assert report["scenario"]["greedy_scheduled_units"] == 18
            assert report["scenario"]["selected_scheduled_units"] == 28
            assert report["scenario"]["selected_proven_objectives"] == 3
            assert report["scheduling"]["candidate_solver_status"] == "OPTIMAL"
            assert report["cancellation_status"] == "CANCELLED"
            assert api_settings.token.get_secret_value() not in completed.stdout + completed.stderr
            reports.append(report)
    finally:
        process.terminate()
        stdout, stderr = process.communicate(timeout=10)
    assert "Traceback" not in stderr
    assert api_settings.token.get_secret_value() not in stdout + stderr
    assert reports[0]["scheduling"]["objectives"] == reports[1]["scheduling"]["objectives"]
    assert reports[0]["scheduling"]["job_id"] != reports[1]["scheduling"]["job_id"]
    # Local generated evidence; credentials and API request payloads are absent.
    (root / ".tmp/m05b-live.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")
