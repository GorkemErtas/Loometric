"""Single explicit offline operation; never dispatched by HTTP or application startup."""

import json
import os
import sys
from pathlib import Path

from loometric.execution import apply_child_memory_limit


def main() -> int:
    try:
        sys.dont_write_bytecode = True
        raw = sys.stdin.read(65537)
        if len(raw.encode()) > 65536:
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
        from loometric.prospective_evaluation.protocol import (
            ROOT,
            load_protocol,
            verify_frozen_sources,
        )
        from loometric.prospective_evaluation.storage import _opaque_path

        c = load_protocol()
        verify_frozen_sources(c)
        operation = request.get("operation")
        fields = {"operation", "authorized"} | (
            {"windows_job_name"} if "windows_job_name" in request else set()
        )
        required = (
            set()
            if operation == "develop"
            else {"expected_model"}
            if operation == "evaluate"
            else {"expected_model", "source_receipts", "expected_report"}
        )
        if (
            request.get("authorized") is not True
            or operation not in ("develop", "evaluate", "reproduce")
            or set(request) != fields | required
        ):
            raise ValueError("CLOSED_AUTHORIZED_OFFLINE_OPERATION_REQUIRED")
        from loometric.final_candidate import data

        allowed = {
            ROOT / b["directory"] / name
            for b in c["frozen_bundles"].values()
            for name in ("manifest.json", *b["files"])
        }

        def guard(event, args):
            if event in {"socket.connect", "subprocess.Popen", "os.system"}:
                raise PermissionError("EXTERNAL_IO_FORBIDDEN")
            if event != "open" or not isinstance(args[0], (str, bytes)):
                return
            path = Path(os.fsdecode(args[0])).resolve()
            writing = bool(
                args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
            )
            if writing and (not path.is_relative_to(data.DIRECTORY) or not args[2] & os.O_EXCL):
                raise PermissionError("CREATE_ONLY_EXPERIMENT_WRITES_REQUIRED")
            if (
                path.is_relative_to(ROOT / "data")
                and not path.is_relative_to(data.DIRECTORY)
                and path not in allowed
            ):
                raise PermissionError("OLD_OR_RESERVED_DATA_ACCESS_FORBIDDEN")
            if path.name.startswith("labels.") and not writing and _opaque_path.get() != path:
                permitted = (
                    path.is_relative_to(data.DIRECTORY / "development")
                    and operation == "develop"
                    and path.name in ("labels.fit.jsonl", "labels.development.jsonl")
                )
                permitted |= (
                    path.is_relative_to(data.DIRECTORY / "heldout")
                    and operation in ("evaluate", "reproduce")
                    and path.name == "labels.evaluation.jsonl"
                    and data.evaluation_labels_enabled.get()
                )
                if not permitted or data._label_path.get() != path:
                    raise PermissionError("UNSEALED_OR_RESERVED_LABEL_ACCESS_FORBIDDEN")

        sys.addaudithook(guard)
        from threadpoolctl import threadpool_limits

        from loometric.final_candidate.study import develop, evaluate

        with threadpool_limits(limits=1):
            if operation == "develop":
                result = develop()
            else:
                result = evaluate(
                    request["expected_model"],
                    reproduce=operation == "reproduce",
                    source_receipts=request.get("source_receipts"),
                    expected_report=request.get("expected_report"),
                )
            verify_frozen_sources(c)
        result["memory_backend"] = backend
        print(json.dumps(result, allow_nan=False))
    except Exception as exc:
        code = (
            str(exc)
            if isinstance(exc, ValueError) and str(exc).isupper()
            else type(exc).__name__.upper()
        )
        print(json.dumps({"error": code}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
