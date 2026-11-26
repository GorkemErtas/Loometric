"""One bounded process for the entire evaluation, including verification and reporting."""

import json
import os
import re
import sys

from loometric.execution import apply_child_memory_limit


def main() -> int:
    try:
        sys.dont_write_bytecode = True
        raw = sys.stdin.read(65537)
        if len(raw.encode()) > 65536:
            raise ValueError("REQUEST_BYTE_LIMIT")
        from loometric.prediction.contracts import read_json

        request = read_json(raw)
        backend = apply_child_memory_limit(2048 * 1024**2, request.get("windows_job_name"))
        for name in (
            "OMP_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
        ):
            os.environ[name] = "1"
        from loometric.prospective_evaluation.protocol import (
            ROOT,
            load_protocol,
            verify_frozen_sources,
        )
        from loometric.prospective_evaluation.source import declared_designs, require
        from loometric.prospective_evaluation.storage import output_root, safe_path

        config = load_protocol()
        verify_frozen_sources(config)
        root = output_root()
        operation = request.get("operation")
        fields = {"operation", "ledger_sha256", "original_manifest_sha256"}
        if "windows_job_name" in request:
            fields.add("windows_job_name")
        if operation == "evaluate":
            require(
                set(request) == fields | {"run", "evaluation_authorized"}
                and request["evaluation_authorized"] is True,
                "CLOSED_AUTHORIZED_EVALUATION_REQUEST_REQUIRED",
            )
            require(request["run"] in ("a", "b"), "TWO_DECLARED_RUNS_ONLY")
            prefix = f"runs/{request['run']}"
        elif operation == "verify_reproduction":
            require(
                set(request) == fields | {"reproduction_manifest_sha256"},
                "CLOSED_REPRODUCTION_REQUEST_REQUIRED",
            )
            prefix = "runs/b"
        else:
            raise ValueError("UNSUPPORTED_EVALUATION_OPERATION")
        from loometric.prospective_evaluation.evaluation_access import install_evaluation_guard
        from loometric.prospective_evaluation.receipts import (
            historical_bindings,
            historical_inventory,
        )

        model_paths = {
            ROOT / b["directory"] / n
            for b in config["frozen_bundles"].values()
            for n in ("manifest.json", *b["files"])
        }
        install_evaluation_guard(
            root,
            safe_path(root, prefix),
            tuple(ROOT / b["directory"] for b in historical_bindings()),
            model_paths,
        )
        from loometric.prospective_evaluation.evaluator import _evaluate, verify_reproduction
        from loometric.prospective_evaluation.frozen_models import (
            load_frozen_models,
            verify_model_receipts,
        )
        from loometric.prospective_evaluation.receipts import _verify_ledger

        designs, history = declared_designs(), historical_inventory()
        # Threadpool limits also cover libraries that initialize native pools late.
        from threadpoolctl import threadpool_limits

        with threadpool_limits(limits=1):
            if operation == "evaluate":
                result = _evaluate(
                    root,
                    designs,
                    history,
                    request["ledger_sha256"],
                    load_frozen_models,
                    run=request["run"],
                    expected_a=request["original_manifest_sha256"],
                    final_integrity_check=lambda: verify_model_receipts(config),
                )
            else:
                _verify_ledger(root, designs, request["ledger_sha256"], history)
                verify_model_receipts(config)
                result = verify_reproduction(
                    root,
                    request["original_manifest_sha256"],
                    request["reproduction_manifest_sha256"],
                    request["ledger_sha256"],
                )
            verify_frozen_sources(config)
        result["memory_backend"], result["numeric_threads"] = backend, 1
        print(json.dumps(result, allow_nan=False))
    except Exception as exc:
        code = (
            str(exc)
            if isinstance(exc, ValueError) and re.fullmatch(r"[A-Z0-9_]+", str(exc))
            else type(exc).__name__.upper()
        )
        print(
            json.dumps(
                {
                    "error": {"code": code},
                    "status": "INVALID_EVALUATION",
                    "promotion_decision": "NO_ML_PROMOTION",
                }
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
