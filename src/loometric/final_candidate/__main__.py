"""Explicit offline reproduction commands; never called by application startup."""

import argparse
import hashlib
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation", choices=("verify", "develop", "evaluate", "reproduce", "publish")
    )
    operation = parser.parse_args().operation
    root = Path(__file__).resolve().parents[3]
    receipt = json.loads((root / "docs/experiments/EXP-010-candidate-receipt.json").read_bytes())
    execution = json.loads((root / "docs/experiments/EXP-010-execution.json").read_bytes())
    expected_model = receipt["receipt"]["model_sha256"]
    expected_report = execution["report_sha256"]
    if operation == "verify":
        from loometric.final_candidate.artifacts import verified_bundle
        from loometric.prospective_evaluation.protocol import load_protocol, verify_frozen_sources

        verify_frozen_sources(load_protocol())
        metadata, raw = verified_bundle()
        if (
            hashlib.sha256(raw).hexdigest() != expected_model
            or metadata["report_sha256"] != expected_report
            or hashlib.sha256(
                (root / "docs/experiments/EXP-010-results.json").read_bytes()
            ).hexdigest()
            != expected_report
        ):
            raise ValueError("INDEPENDENT_PUBLISHED_EVIDENCE_DRIFT")
        result = {"status": "VERIFIED", "promotion_decision": "NO_ML_PROMOTION"}
    elif operation == "publish":
        from loometric.final_candidate.artifacts import publish, trusted_policy

        result = publish(expected_model, expected_report)
        if result != trusted_policy():
            raise ValueError("PUBLICATION_DIFFERS_FROM_INDEPENDENT_REGISTRY")
    else:
        from loometric.final_candidate.service import execute

        arguments = {} if operation == "develop" else {"expected_model": expected_model}
        if operation == "reproduce":
            raw = (
                root / "data/processed/final_candidate/exp-010/heldout/a.report.json"
            ).read_bytes()
            if hashlib.sha256(raw).hexdigest() != expected_report:
                raise ValueError("INDEPENDENT_PUBLISHED_EVIDENCE_DRIFT")
            report = json.loads(raw)
            arguments.update(
                source_receipts=report["source_receipts"], expected_report=expected_report
            )
        result = execute(operation, **arguments)
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
