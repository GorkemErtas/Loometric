"""Local job submission, polling, verified retrieval and cancellation; no credential output."""

import json
import time
from pathlib import Path

import httpx

from loometric.api.codec import input_json
from loometric.api.settings import settings_from_environment
from loometric.planning.loading import parse_json


def workflow(client: httpx.Client) -> dict:
    examples = Path(__file__).resolve().parents[1]

    def load(name: str) -> dict:
        return parse_json((examples / name).read_text(encoding="utf-8"))

    def submit(kind: str, body: dict) -> dict:
        response = client.post(
            "/api/v1/jobs/" + kind,
            content=input_json(body),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        assert response.status_code == 202
        return response.json()["data"]

    def poll(info: dict) -> dict:
        deadline = time.monotonic() + 30
        while True:
            response = client.get(info["polling_url"])
            response.raise_for_status()
            current = response.json()["data"]
            if current["status"] not in {"QUEUED", "RUNNING"}:
                return current
            if time.monotonic() > deadline:
                raise ValueError("Local polling deadline exceeded.")
            time.sleep(0.05)

    def result(info: dict) -> dict:
        done = poll(info)
        if done["status"] != "SUCCEEDED":
            raise ValueError("Job ended without a retrievable result.")
        response = client.get(done["result_url"])
        response.raise_for_status()
        return response.json()["data"]

    scheduled = result(submit("scheduling", {"instance": load("scheduling/hand-enumerated.json")}))
    spec = load("scenarios/capacity-optimizer-recovery.json")
    # Preserve M04's default10s contract: explicitly request the supported1s instead.
    spec["scheduling"]["solver"] = {
        "wall_time_seconds_per_phase": 1,
        "deterministic_time_per_phase": 1,
    }
    compared = result(
        submit(
            "scenarios",
            {"baseline": load("scenarios/routing-baseline.json"), "specification": spec},
        )
    )
    candidate = submit("scheduling", {"instance": load("scheduling/competition.json")})
    cancellation = client.delete(candidate["polling_url"])
    cancellation.raise_for_status()
    cancelled = poll(candidate)
    assert cancelled["status"] in {"CANCELLED", "SUCCEEDED"}  # Completion may win the race.
    evaluation = scheduled["result"]["evaluation"]
    scenario = compared["result"]["scenario"]["evaluation"]
    assert evaluation["verification"]["feasible"] and scenario["verification"]["feasible"]
    return {
        "synthetic": True,
        "automatic_production_authorization": False,
        "scheduling": {
            "job_id": scheduled["job_id"],
            "producer": evaluation["selected_producer"],
            "objectives": scheduled["result"]["objectives"],
            "candidate_solver_status": evaluation["optimizer"]["solver_status"],
            "selected_proven_objectives": evaluation["selected_proven_objectives"],
            "execution": scheduled["execution"],
        },
        "scenario": {
            "job_id": compared["job_id"],
            "producer": scenario["selected_producer"],
            "greedy_scheduled_units": scenario["greedy_metrics"]["scheduled_units"],
            "selected_scheduled_units": scenario["metrics"]["scheduled_units"],
            "selected_proven_objectives": scenario["selected_proven_objectives"],
            "execution": compared["execution"],
        },
        "cancellation_status": cancelled["status"],
    }


def main() -> int:
    try:
        settings = settings_from_environment()
        with httpx.Client(
            base_url=f"http://127.0.0.1:{settings.port}",
            timeout=10,
            headers={"Authorization": "Bearer " + settings.token.get_secret_value()},
            trust_env=False,
            follow_redirects=False,
        ) as client:
            report = workflow(client)
    except (ValueError, OSError, httpx.HTTPError):
        print("Local job workflow failed; inspect authenticated status and server configuration.")
        return 2
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
