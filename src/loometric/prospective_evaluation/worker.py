"""Dedicated stdlib-only startup; hard resource and data-access guards before generation."""

import json
import os
import re
import sys

from loometric.execution import apply_child_memory_limit


def main() -> int:
    try:
        raw = sys.stdin.read(65537)
        if len(raw.encode("utf-8")) > 65536:
            raise ValueError("REQUEST_BYTE_LIMIT")
        request = json.loads(raw)
        backend = apply_child_memory_limit(2048 * 1024**2, request.get("windows_job_name"))
        for name in (
            "OMP_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
        ):
            os.environ[name] = "1"
        from loometric.prospective_evaluation.protocol import load_protocol, verify_frozen_sources
        from loometric.prospective_evaluation.receipts import (
            _register_batch,
            _verify_ledger,
            historical_bindings,
            historical_inventory,
        )
        from loometric.prospective_evaluation.source import declared_designs, require
        from loometric.prospective_evaluation.storage import ROOT, install_access_guard, output_root

        config = load_protocol()
        verify_frozen_sources(config)
        root, designs = output_root(), declared_designs()
        install_access_guard(root, tuple(ROOT / b["directory"] for b in historical_bindings()))
        operation = request.get("operation")
        fields = (
            {"operation", "windows_job_name"} if "windows_job_name" in request else {"operation"}
        )
        if operation == "prepare":
            from loometric.prospective_evaluation.generation import _prepare_batch

            require(
                set(request) == fields | {"generation_authorized"}
                and request["generation_authorized"] is True,
                "GENERATION_NOT_AUTHORIZED",
            )
            result = _prepare_batch(root, designs, historical_inventory())
        elif operation == "register":
            require(set(request) == fields | {"receipts"}, "CLOSED_WORKER_REQUEST_REQUIRED")
            result = _register_batch(root, designs, request["receipts"], historical_inventory())
        elif operation == "verify":
            require(set(request) == fields | {"ledger_sha256"}, "CLOSED_WORKER_REQUEST_REQUIRED")
            result = _verify_ledger(root, designs, request["ledger_sha256"], historical_inventory())
        else:
            raise ValueError("UNSUPPORTED_OFFLINE_OPERATION")
        result["memory_backend"] = backend
        result["numeric_threads"] = 1
        print(json.dumps(result, allow_nan=False))
    except Exception as exc:
        code = (
            str(exc)
            if isinstance(exc, ValueError) and re.fullmatch(r"[A-Z0-9_]+", str(exc))
            else type(exc).__name__.upper()
        )
        print(json.dumps({"error": {"code": code}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
