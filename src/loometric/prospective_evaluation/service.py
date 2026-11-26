"""Offline bounded entry points; generation requires a deliberate separate authorization."""

import json

from loometric.execution import guarded_child
from loometric.prospective_evaluation.protocol import load_protocol, verify_frozen_sources


def _execute(request: dict) -> dict:
    config = load_protocol()
    verify_frozen_sources(config)
    payload, measurements = guarded_child(
        json.dumps(request),
        config["budget"]["memory_limit_mib"],
        config["budget"]["whole_run_deadline_seconds"],
        worker_module="loometric.prospective_evaluation.worker",
    )
    if not payload or "error" in payload:
        code = (
            payload["error"]["code"]
            if payload and "error" in payload
            else measurements.get("status", "REJECTED")
        )
        raise ValueError("PROSPECTIVE_INFRASTRUCTURE_FAILED:" + code)
    return {**payload, "execution": measurements}


def prepare_sources(*, generation_authorized: bool = False) -> dict:
    """Do not call during M10A.2; no data generation is authorized by implementation alone."""
    if generation_authorized is not True:
        raise ValueError("SEPARATE_DATASET_GENERATION_AUTHORIZATION_REQUIRED")
    return _execute({"operation": "prepare", "generation_authorized": True})


def register_sources(expected_manifest_sha256: dict[str, str]) -> dict:
    return _execute({"operation": "register", "receipts": expected_manifest_sha256})


def verify_sources(expected_ledger_sha256: str) -> dict:
    return _execute({"operation": "verify", "ledger_sha256": expected_ledger_sha256})
