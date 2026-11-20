"""Frozen synthetic HTTP workflow; start python -m loometric.api in another terminal."""

import json
from pathlib import Path

import httpx

from loometric.api.codec import input_json
from loometric.api.settings import settings_from_environment
from loometric.planning.loading import parse_json


def workflow(client: httpx.Client) -> dict:
    examples = Path(__file__).resolve().parents[1]

    def load(name: str) -> dict:
        return parse_json((examples / name).read_text(encoding="utf-8"))

    def post(path: str, body: dict) -> dict:
        response = client.post(
            "/api/v1/" + path,
            content=input_json(body),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()["data"]

    health = client.get("/api/v1/health")
    health.raise_for_status()
    capabilities = client.get("/api/v1/capabilities")
    capabilities.raise_for_status()
    assert capabilities.json()["data"]["scheduling_methods"] == ["greedy"]
    capacity = post("planning/capacity", {"scenario": load("planning/capacity-demo.json")})
    baseline = load("scenarios/capacity-baseline.json")
    dispatched = post("scheduling/dispatch", {"instance": baseline})
    verified = post("scheduling/verify", {"instance": baseline, "schedule": dispatched["schedule"]})
    assert verified["metrics"] == dispatched["metrics"]
    assert verified["verification"]["feasible"]
    comparison = post(
        "scenarios/compare",
        {"baseline": baseline, "specification": load("scenarios/additional-workers.json")},
    )
    before = comparison["baseline"]["evaluation"]["metrics"]["scheduled_units"]
    after = comparison["scenario"]["evaluation"]["metrics"]["scheduled_units"]
    assert (before, after) == (45, 55)
    return {
        "api_version": "v1",
        "synthetic": True,
        "capacity_status": capacity["status"],
        "dispatch_status": dispatched["status"],
        "verification_status": verified["status"],
        "baseline_scheduled_units": before,
        "scenario_scheduled_units": after,
        "baseline_fingerprint": dispatched["instance_fingerprint"],
        "scenario_fingerprint": comparison["scenario"]["identity"]["instance_fingerprint"],
        "automatic_production_authorization": False,
    }


def main() -> int:
    try:
        settings = settings_from_environment()
        with httpx.Client(
            base_url=f"http://127.0.0.1:{settings.port}",
            timeout=12,
            headers={"Authorization": "Bearer " + settings.token.get_secret_value()},
            trust_env=False,
            follow_redirects=False,
        ) as client:
            result = workflow(client)
    except (ValueError, OSError, httpx.HTTPError):
        print("Local workflow failed; check the server and its configured environment.")
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
