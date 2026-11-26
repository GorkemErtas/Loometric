"""Explicitly authorized offline execution only; no API/CLI/serving wiring."""

import json

from loometric.execution import guarded_child
from loometric.prospective_evaluation.protocol import load_protocol
from loometric.prospective_evaluation.storage import require_sha


def _execute(request: dict) -> dict:
    config = load_protocol()
    # All source/model/dataset verification runs inside the one supervised child.
    result, measurements = guarded_child(
        json.dumps(request),
        config["budget"]["memory_limit_mib"],
        config["budget"]["whole_run_deadline_seconds"],
        worker_module="loometric.prospective_evaluation.evaluation_worker",
    )
    if not result or "error" in result:
        code = (
            result["error"]["code"]
            if result and "error" in result
            else measurements.get("status", "REJECTED")
        )
        raise ValueError("INVALID_EVALUATION:" + code)
    return {**result, "execution": measurements}


def evaluate_frozen_models(
    expected_ledger_sha256: str,
    *,
    run: str = "a",
    expected_original_manifest_sha256: str | None = None,
    evaluation_authorized: bool = False,
) -> dict:
    """Implementation is not authorization. Do not invoke for actual EXP-009 in M10A.3."""
    if evaluation_authorized is not True:
        raise ValueError("SEPARATE_PROSPECTIVE_EVALUATION_AUTHORIZATION_REQUIRED")
    require_sha(expected_ledger_sha256)
    if run not in ("a", "b") or (run == "a" and expected_original_manifest_sha256 is not None):
        raise ValueError("TWO_DECLARED_RUNS_ONLY")
    if run == "b":
        require_sha(expected_original_manifest_sha256)
    return _execute(
        {
            "operation": "evaluate",
            "ledger_sha256": expected_ledger_sha256,
            "run": run,
            "original_manifest_sha256": expected_original_manifest_sha256,
            "evaluation_authorized": True,
        }
    )


def verify_frozen_reproduction(
    expected_ledger_sha256: str, expected_a: str, expected_b: str
) -> dict:
    for receipt in (expected_ledger_sha256, expected_a, expected_b):
        require_sha(receipt)
    return _execute(
        {
            "operation": "verify_reproduction",
            "ledger_sha256": expected_ledger_sha256,
            "original_manifest_sha256": expected_a,
            "reproduction_manifest_sha256": expected_b,
        }
    )
