"""Bounded create-only files and explicit hash-only access to reserved target bytes."""

import hashlib
import platform
import re
import sys
from contextvars import ContextVar
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

from loometric.planning.reporting import json_value
from loometric.prediction.contracts import read_json
from loometric.prospective_evaluation.protocol import PROTOCOL_SHA256, ROOT, load_protocol
from loometric.prospective_evaluation.source import SOURCE_TABLES, require

MAX_FILE_BYTES = 32 * 1024**2
MAX_BUNDLE_BYTES = 64 * 1024**2
MAX_ROOT_BYTES = 768 * 1024**2
MAX_MANIFEST_BYTES = 65536
RESERVED = frozenset(
    {"outcomes.jsonl", *(f"labels.{p}.jsonl" for p in ("train", "validation", "gap", "test"))}
)
READABLE = frozenset(
    {
        *(f"{t}.jsonl" for t in SOURCE_TABLES),
        "features.jsonl",
        "scoped_entities.jsonl",
        "score_ids.jsonl",
    }
)
FILES = READABLE | RESERVED
_opaque_path: ContextVar[Path | None] = ContextVar("prospective_hash_only_path", default=None)


def encode(value: object) -> bytes:
    import json

    return (
        json.dumps(json_value(value), sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode("utf-8")


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def require_sha(value: str) -> None:
    require(
        isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None,
        "INDEPENDENT_RECEIPT_REQUIRED",
    )


def environment() -> dict:
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "packages": {
            name: version(name)
            for name in ("loometric", "pandas", "numpy", "scikit-learn", "joblib")
        },
    }


def core_identity() -> dict:
    directory = Path(__file__).parent
    return {
        name: sha256((directory / name).read_bytes())
        for name in ("source.py", "storage.py", "generation.py", "receipts.py", "protocol.py")
    }


def output_root() -> Path:
    return ROOT / load_protocol()["storage"]["root"]


def safe_path(root: Path, relative: str) -> Path:
    require(root.resolve() == root.absolute(), "NONCANONICAL_OUTPUT_ROOT")
    parts = Path(relative).parts
    require(
        bool(parts)
        and not Path(relative).is_absolute()
        and all(p not in (".", "..") and re.fullmatch(r"[A-Za-z0-9_.-]+", p) for p in parts),
        "CLOSED_RELATIVE_PATH_REQUIRED",
    )
    path = root.joinpath(*parts)
    require(
        path.resolve() == path.absolute() and path.resolve().is_relative_to(root.resolve()),
        "OUTPUT_PATH_ESCAPE",
    )
    return path


def root_size(root: Path) -> int:
    require(root.resolve() == root.absolute(), "NONCANONICAL_OUTPUT_ROOT")
    total, count = 0, 0
    pending = [root] if root.exists() else []
    while pending:
        directory = pending.pop()
        for path in directory.iterdir():
            count += 1
            require(
                count <= 10000 and path.resolve() == path.absolute(), "OUTPUT_TREE_LIMIT_OR_LINK"
            )
            if path.is_dir():
                pending.append(path)
            else:
                require(path.is_file(), "REGULAR_OUTPUT_FILE_REQUIRED")
                total += path.stat().st_size
            require(total <= MAX_ROOT_BYTES, "OUTPUT_ROOT_BYTE_LIMIT")
    return total


def write_new(root: Path, relative: str, content: bytes) -> None:
    path = safe_path(root, relative)
    require(
        len(content) <= MAX_FILE_BYTES and root_size(root) + len(content) <= MAX_ROOT_BYTES,
        "OUTPUT_BYTE_LIMIT",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    # Recheck after mkdir; existing partial files/directories are never replaced.
    path = safe_path(root, relative)
    with path.open("xb") as destination:
        destination.write(content)


def read_checked(path: Path, ceiling: int) -> bytes:
    require(path.resolve() == path.absolute() and path.is_file(), "REGULAR_CANONICAL_FILE_REQUIRED")
    require(path.stat().st_size <= ceiling, "INPUT_FILE_BYTE_LIMIT")
    with path.open("rb") as source:
        content = source.read(ceiling + 1)
    require(len(content) <= ceiling, "INPUT_FILE_BYTE_LIMIT")
    return content


def opaque_identity(path: Path) -> dict:
    """Never expose bytes or a decoder to a label-blind caller."""
    require(path.resolve() == path.absolute() and path.is_file(), "REGULAR_CANONICAL_FILE_REQUIRED")
    require(path.stat().st_size <= MAX_FILE_BYTES, "INPUT_FILE_BYTE_LIMIT")
    token = _opaque_path.set(path.resolve())
    try:
        hasher, size, rows, last = hashlib.sha256(), 0, 0, b""
        with path.open("rb") as source:
            for block in iter(lambda: source.read(65536), b""):
                size += len(block)
                require(size <= MAX_FILE_BYTES, "INPUT_FILE_BYTE_LIMIT")
                rows += block.count(b"\n")
                last = block[-1:]
                hasher.update(block)
        require(not size or last == b"\n", "JSONL_TERMINAL_NEWLINE_REQUIRED")
        return {"sha256": hasher.hexdigest(), "bytes": size, "rows": rows}
    finally:
        _opaque_path.reset(token)


def decode_rows(name: str, content: bytes) -> list[dict]:
    require(name in READABLE, "RESERVED_LABEL_DECODE_FORBIDDEN")
    lines = content.splitlines(keepends=True)
    require(not content or content.endswith(b"\n"), "JSONL_TERMINAL_NEWLINE_REQUIRED")
    require(len(lines) <= 150000, "JSONL_ROW_LIMIT")
    result = []
    for line in lines:
        require(len(line) <= 65536, "JSONL_RECORD_BYTE_LIMIT")
        result.append(read_json(line.decode("utf-8")))
    return result


def records_bytes(records) -> bytes:
    return b"".join(encode(asdict(v) if hasattr(v, "__dataclass_fields__") else v) for v in records)


def identity(content: bytes) -> dict:
    return {"sha256": sha256(content), "bytes": len(content), "rows": content.count(b"\n")}


def install_access_guard(root: Path, historical_directories: tuple[Path, ...]) -> None:
    """Permanent in the dedicated worker only; binary hashing needs an exact-path capability."""
    data_root = (ROOT / "data").resolve()
    history_allowed = {
        p.resolve() / name
        for p in historical_directories
        for name in (
            "manifest.json",
            *(f"{t}.jsonl" for t in ("factories", "lines", "crews", "styles", "standards")),
        )
    }

    def guard(event, args):
        if event == "import" and args[0].split(".")[0] in {"pandas", "numpy", "sklearn", "joblib"}:
            raise PermissionError("MODEL_IMPORT_FORBIDDEN")
        if event != "open" or not isinstance(args[0], (str, bytes)):
            return
        raw = args[0].decode() if isinstance(args[0], bytes) else args[0]
        path = Path(raw).resolve()
        mode = args[1]
        reading = mode is None or "r" in mode or "+" in mode
        if reading and path.suffix in {".joblib", ".pkl", ".pickle"}:
            raise PermissionError("MODEL_FILE_ACCESS_FORBIDDEN")
        if reading and path.name in RESERVED and _opaque_path.get() != path:
            raise PermissionError("RESERVED_LABEL_ACCESS_FORBIDDEN")
        if path.is_relative_to(data_root):
            if not path.is_relative_to(root.resolve()) and (
                not reading or path not in history_allowed
            ):
                raise PermissionError("HISTORICAL_DATA_ACCESS_FORBIDDEN")

    sys.addaudithook(guard)


def manifest_policy() -> dict:
    return {
        "schema_version": 1,
        "experiment_id": "EXP-009",
        "protocol_sha256": PROTOCOL_SHA256,
        "dataset_version": "synthetic-prospective-exp009-v1",
        "generator_version": "stage-shift-process-v1",
        "promotion_decision": "NO_ML_PROMOTION",
        "model_training_performed": False,
        "capacity_application_authorized": False,
        "reserved_labels_decoded_by_registrar": False,
    }
