"""Dedicated-worker access guard and capability-scoped validation decoding after sealing."""

import os
import sys
from contextvars import ContextVar
from datetime import timedelta
from decimal import Decimal, localcontext
from pathlib import Path

from loometric.planning.domain import ARITHMETIC_CONTEXT
from loometric.prediction.contracts import read_json
from loometric.prospective_evaluation.protocol import ROOT
from loometric.prospective_evaluation.source import SourceDesign, require
from loometric.prospective_evaluation.storage import (
    MAX_FILE_BYTES,
    RESERVED,
    _opaque_path,
    encode,
    identity,
    read_checked,
    require_sha,
    safe_path,
    sha256,
)
from loometric.synthetic_ml.contracts import target_value
from loometric.synthetic_ml.features import References, available_minutes

_validation_path: ContextVar[Path | None] = ContextVar("sealed_validation_path", default=None)


def install_evaluation_guard(root: Path, run: Path, history: tuple[Path, ...], models: set[Path]):
    """Permanent in the isolated worker. Audit hooks are defense in depth, not a sandbox."""
    history_allowed = {
        directory.resolve() / name
        for directory in history
        for name in (
            "manifest.json",
            *(f"{t}.jsonl" for t in ("factories", "lines", "crews", "styles", "standards")),
        )
    }
    model_paths = {p.resolve() for p in models}
    data_root = ROOT / "data"

    def guard(event, args):
        if event in {"socket.connect", "socket.bind", "subprocess.Popen", "os.system"}:
            raise PermissionError("EVALUATION_EXTERNAL_IO_FORBIDDEN")
        if event in {"os.remove", "os.rename", "os.rmdir", "os.link", "os.symlink", "os.chmod"}:
            raise PermissionError("EVALUATION_EXISTING_FILE_MUTATION_FORBIDDEN")
        if event == "os.mkdir":
            path = Path(os.fsdecode(args[0])).resolve()
            if not path.is_relative_to(run) and not run.is_relative_to(path):
                raise PermissionError("EVALUATION_DIRECTORY_OUTSIDE_RUN")
        if event != "open" or not isinstance(args[0], (str, bytes)):
            return
        path = Path(os.fsdecode(args[0])).resolve()
        flags = args[2]
        writing = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if path.name in RESERVED and not writing:
            if _opaque_path.get() != path and _validation_path.get() != path:
                raise PermissionError("RESERVED_LABEL_ACCESS_FORBIDDEN")
        if writing and not path.is_relative_to(run):
            # Python bytecode writes outside the run are disabled at startup too.
            raise PermissionError("EVALUATION_WRITE_OUTSIDE_RUN")
        if writing and not flags & os.O_EXCL:
            raise PermissionError("EVALUATION_CREATE_ONLY_WRITES_REQUIRED")
        if path.suffix in {".joblib", ".pkl", ".pickle"} and path not in model_paths:
            raise PermissionError("UNPINNED_MODEL_ACCESS_FORBIDDEN")
        if path.is_relative_to(data_root) and not path.is_relative_to(root):
            if path not in history_allowed and path not in model_paths:
                raise PermissionError("HISTORICAL_DATA_ACCESS_FORBIDDEN")

    sys.addaudithook(guard)


def verify_seal(root: Path, prefix: str, receipt_sha: str, expected: dict) -> list[dict]:
    receipt_bytes = read_checked(safe_path(root, f"{prefix}/predictions.receipt.json"), 65536)
    require(sha256(receipt_bytes) == receipt_sha, "PREDICTION_RECEIPT_DRIFT")
    require(receipt_bytes == encode(expected), "PREDICTION_SEAL_BINDING_DRIFT")
    raw = read_checked(safe_path(root, f"{prefix}/predictions.jsonl"), MAX_FILE_BYTES)
    require(identity(raw) == expected["predictions"], "SEALED_PREDICTIONS_DRIFT")
    return [read_json(line) for line in raw.decode().splitlines()]


def read_validation_labels(
    root: Path, design: SourceDesign, source, seal_check, *, expected_manifest_sha: str
) -> dict:
    """No generic partition/path parameter. A freshly checked whole-pass seal is required."""
    seal_check()
    path = safe_path(root, f"datasets/{design.case.case_id}/labels.validation.jsonl")
    require_sha(expected_manifest_sha)
    raw_manifest = read_checked(path.parent / "manifest.json", 65536)
    require(sha256(raw_manifest) == expected_manifest_sha, "VALIDATION_MANIFEST_RECEIPT_DRIFT")
    manifest = read_json(raw_manifest.decode())
    token = _validation_path.set(path)
    try:
        content = read_checked(path, MAX_FILE_BYTES)
    finally:
        _validation_path.reset(token)
    require(identity(content) == manifest["files"][path.name], "VALIDATION_LABEL_RECEIPT_DRIFT")
    require(content.endswith(b"\n"), "VALIDATION_LABEL_NEWLINE_REQUIRED")
    rows = []
    for line in content.splitlines():
        require(len(line) <= 65536, "VALIDATION_LABEL_RECORD_LIMIT")
        rows.append(read_json(line.decode()))
    ids = {m.observation_id for m in source.membership if m.partition == "validation"}
    require(
        len(rows) == len(ids) == design.case.planned_rows
        and {r["observation_id"] for r in rows} == ids,
        "EXACT_VALIDATION_LABEL_IDS_REQUIRED",
    )
    refs = References.from_dataset(source)
    plans = {p.observation_id: p for p in source.plans}
    labels = {}
    for label in rows:
        require(
            set(label)
            == {
                "observation_id",
                "status",
                "standard_capacity_attainment",
                "available_at",
                "planned_available_worker_minutes",
                "earned_standard_worker_minutes",
            },
            "CLOSED_VALIDATION_LABEL_REQUIRED",
        )
        plan = plans[label["observation_id"]]
        shift = refs.shifts[plan.shift_id]
        standard = refs.standards[plan.standard_id].worker_minutes_per_piece
        denominator = available_minutes(plan, shift) * plan.planned_workers
        require(
            type(label["planned_available_worker_minutes"]) is int
            and label["planned_available_worker_minutes"] == denominator
            and label["available_at"]
            == (
                shift.end + timedelta(minutes=design.configuration.label_delay_minutes)
            ).isoformat(),
            "VALIDATION_LABEL_TEMPORAL_OR_DENOMINATOR_DRIFT",
        )
        with localcontext(ARITHMETIC_CONTEXT):
            earned = Decimal(str(label["earned_standard_worker_minutes"]))
            completed = earned / standard
            require(
                earned.is_finite()
                and completed == completed.to_integral_value()
                and 0 <= completed <= refs.orders[plan.order_id].quantity,
                "VALIDATION_LABEL_PHYSICAL_DRIFT",
            )
            status, target = target_value(int(completed), standard, denominator)
            actual = label["standard_capacity_attainment"]
            require(
                label["status"] == status
                and (actual is None if target is None else Decimal(str(actual)) == target),
                "VALIDATION_TARGET_DEFINITION_DRIFT",
            )
        labels[plan.observation_id] = target
    seal_check()
    return labels
