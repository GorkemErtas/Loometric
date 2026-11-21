import json
import time
from dataclasses import asdict, replace

import pytest

from loometric.api.codec import input_json
from loometric.api.errors import ApiError
from loometric.api.job_operations import execute_job, validate_job
from loometric.api.job_settings import default_job_limits
from loometric.api.jobs import JobRegistry
from loometric.api.settings import default_limits
from loometric.planning.reporting import json_value
from loometric.planning.validation import PlanningError
from loometric.scenarios.metrics import objective_values
from loometric.scheduling.loading import parse_instance, parse_schedule
from loometric.scheduling.metrics import calculate_metrics
from loometric.scheduling.verification import verify_schedule


def cp_spec(fixture_json, wall=1):
    spec = fixture_json("scenarios/capacity-optimizer-recovery.json")
    spec["scheduling"]["solver"] = {
        "wall_time_seconds_per_phase": wall,
        "deterministic_time_per_phase": 1,
    }
    return spec


def test_real_nested_scheduling_job_preserves_verification_and_objectives(fixture_json):
    body = input_json({"instance": fixture_json("scheduling/hand-enumerated.json")})
    registry = JobRegistry(default_limits(), default_job_limits())
    registry.start()
    try:
        submitted = registry.submit("scheduling", body)
        deadline = time.monotonic() + 20
        while registry.status(submitted["job_id"])["status"] not in {"SUCCEEDED", "FAILED"}:
            assert time.monotonic() < deadline
            time.sleep(0.01)
        report = json.loads(registry.result(submitted["job_id"]))
        evaluation = report["result"]["evaluation"]
        instance = parse_instance(input_json(fixture_json("scheduling/hand-enumerated.json")))
        proposal = parse_schedule(json.dumps(evaluation["selected_schedule"]))
        assert verify_schedule(instance, proposal).feasible
        assert (
            objective_values(calculate_metrics(instance, proposal))
            == report["result"]["objectives"]
        )
        assert evaluation["optimizer"]["full_lexicographic_optimal"]
        assert report["execution"]["whole_child_wall_seconds"] > 0
        assert report["execution"]["peak_committed_bytes"] > 0
    finally:
        registry.close()


def test_actual_scenario_recovery_selects_strictly_better_cp_sat(fixture_json):
    body = input_json(
        {
            "baseline": fixture_json("scenarios/routing-baseline.json"),
            "specification": cp_spec(fixture_json),
        }
    )
    result = execute_job("scenarios", body, default_limits(), default_job_limits())
    before, after = (result[key]["evaluation"] for key in ("baseline", "scenario"))
    assert (
        before["selected_producer"] == "greedy"
        and before["fallback_reason"] == "CP_SAT_NOT_STRICTLY_BETTER"
    )
    assert after["selected_producer"] == "cp_sat" and after["selected_proven_objectives"] == 3
    assert after["metrics"]["scheduled_units"] == 28
    assert after["greedy_metrics"]["scheduled_units"] == 18


def test_actual_zero_budget_unknown_preserves_verified_greedy(fixture_json):
    spec = cp_spec(fixture_json, wall=0)
    body = input_json(
        {"baseline": fixture_json("scenarios/routing-baseline.json"), "specification": spec}
    )
    result = execute_job("scenarios", body, default_limits(), default_job_limits())
    for key in ("baseline", "scenario"):
        evaluation = result[key]["evaluation"]
        assert evaluation["optimizer"]["solver_status"] == "UNKNOWN"
        assert (
            evaluation["fallback_reason"] == "UNKNOWN"
            and evaluation["selected_producer"] == "greedy"
        )
        assert evaluation["verification"]["feasible"]
        assert evaluation["optimizer"]["metrics"] is None
        assert not evaluation["selected_full_lexicographic_optimal"]


def test_pre_admission_validation_rejects_config_escalation_and_bad_references(fixture_json):
    spec = cp_spec(fixture_json, wall=2)
    body = {"baseline": fixture_json("scenarios/routing-baseline.json"), "specification": spec}
    with pytest.raises(ApiError) as caught:
        validate_job("scenarios", input_json(body), default_limits(), default_job_limits())
    assert caught.value.code == "JOB_SOLVER_POLICY"
    body = {
        "baseline": fixture_json("scenarios/capacity-baseline.json"),
        "specification": fixture_json("scenarios/invalid-reference.json"),
    }
    with pytest.raises(PlanningError) as caught:
        validate_job("scenarios", input_json(body), default_limits(), default_job_limits())
    assert caught.value.code == "UNKNOWN_REFERENCE"


def test_controlled_feasible_injection_keeps_verified_incumbent_without_full_proof(
    fixture_json, monkeypatch
):
    # Controlled status injection, not a measured native FEASIBLE occurrence.
    from ortools.sat.python import cp_model

    import loometric.optimization.solver as native
    import loometric.scenarios.selection as selection
    from loometric.optimization.configuration import SolverConfiguration
    from loometric.scenarios.application import apply_scenario
    from loometric.scenarios.loading import parse_specification
    from loometric.scheduling.loading import instance_json

    original = native._solve_phase

    def phase(built, config, number):
        run = original(built, config, number)
        return replace(run, status=cp_model.FEASIBLE) if number == 1 else run

    def controlled(request, *args, **kwargs):
        data = json.loads(request)
        instance = parse_instance(data["instance_json"])
        result = json_value(
            asdict(native.optimize(instance, SolverConfiguration(**data["solver_configuration"])))
        )
        return {"optimization": result, "status": result["status"], "dimensions": {}}, {}

    monkeypatch.setattr(native, "_solve_phase", phase)
    monkeypatch.setattr(selection, "guarded_child", controlled)
    baseline = parse_instance(input_json(fixture_json("scenarios/routing-baseline.json")))
    changed = apply_scenario(
        baseline, parse_specification(input_json(cp_spec(fixture_json)))
    ).instance
    body = '{"instance":' + instance_json(changed).strip() + "}"
    result = execute_job("scheduling", body, default_limits(), default_job_limits())
    evaluation = result["evaluation"]
    assert evaluation["selected_producer"] == "cp_sat"
    assert evaluation["optimizer"]["solver_status"] == "FEASIBLE"
    assert evaluation["selected_proven_objectives"] == 0
    assert not evaluation["selected_full_lexicographic_optimal"]
    assert evaluation["verification"]["feasible"]


def test_controlled_native_timeout_keeps_verified_greedy_and_sanitizes_diagnostics(
    fixture_json, monkeypatch
):
    import loometric.scenarios.selection as selection

    monkeypatch.setattr(
        selection,
        "guarded_child",
        lambda *a, **k: (
            None,
            {"status": "TERMINATED_RESOURCE_LIMIT", "reason": "raw secret /private/path traceback"},
        ),
    )
    result = execute_job(
        "scheduling",
        input_json({"instance": fixture_json("scheduling/competition.json")}),
        default_limits(),
        default_job_limits(),
    )
    evaluation = result["evaluation"]
    assert evaluation["selected_producer"] == "greedy" and evaluation["verification"]["feasible"]
    assert evaluation["fallback_reason"] == "TERMINATED_RESOURCE_LIMIT"
    assert "private" not in json.dumps(result) and "traceback" not in json.dumps(result)
