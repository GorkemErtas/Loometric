import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx


def test_real_loopback_server_and_example_workflow_twice(api_settings):
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
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=0x08000000 if os.name == "nt" else 0,
    )
    results = []
    try:
        with httpx.Client(
            base_url=f"http://127.0.0.1:{port}", timeout=1, trust_env=False
        ) as client:
            deadline = time.monotonic() + 10
            while True:
                assert process.poll() is None, "Local API exited before readiness"
                try:
                    if client.get("/api/v1/health").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                assert time.monotonic() < deadline, "Local API did not become ready"
                time.sleep(0.05)
        for _ in range(2):
            result = subprocess.run(
                [sys.executable, "examples/api/workflow.py"],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert result.returncode == 0, result.stderr + result.stdout
            results.append(json.loads(result.stdout))
        assert results[0] == results[1]
        assert results[0]["baseline_scheduled_units"] == 45
        assert results[0]["scenario_scheduled_units"] == 55
    finally:
        process.terminate()
        stdout, stderr = process.communicate(timeout=10)
    assert api_settings.token.get_secret_value() not in stdout + stderr
    assert "Authorization" not in stdout + stderr and "Traceback" not in stderr


def test_supported_startup_fails_closed_without_token():
    env = {key: value for key, value in os.environ.items() if key != "LOOMETRIC_API_TOKEN"}
    result = subprocess.run(
        [sys.executable, "-m", "loometric.api"], env=env, capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 2
    assert "Invalid local API configuration" in result.stderr
    assert "Traceback" not in result.stderr
