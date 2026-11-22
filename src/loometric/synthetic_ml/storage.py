"""Create-only ignored bundles, exact JSONL and independently retained receipts."""

import hashlib
import json
import platform
import re
from dataclasses import asdict, fields
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from loometric.planning.domain import Stage
from loometric.planning.loading import parse_json
from loometric.planning.reporting import json_value
from loometric.synthetic_ml.audit import quality_report
from loometric.synthetic_ml.configuration import GenerationConfig
from loometric.synthetic_ml.contracts import (
    DATASET_VERSION,
    GENERATOR_VERSION,
    TABLE_TYPES,
    Dataset,
)
from loometric.synthetic_ml.features import FEATURE_COLUMNS, References, build_features, label_row
from loometric.synthetic_ml.generation import generate
from loometric.synthetic_ml.validation import validate_dataset

OUTPUT_ROOT = Path(__file__).resolve().parents[3] / "data/processed/synthetic_ml"


def encode(value: object) -> bytes:
    return (
        json.dumps(json_value(value), sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(encode(value)).hexdigest()


def _rows(data: Dataset):
    for name in TABLE_TYPES:
        yield f"{name}.jsonl", (asdict(row) for row in getattr(data, name))
    yield "features.jsonl", iter(build_features(data))
    refs = References.from_dataset(data)
    plans = {p.observation_id: p for p in data.plans}
    outcomes = {o.observation_id: o for o in data.outcomes}
    for partition in ("train", "validation", "gap", "test"):
        yield (
            f"labels.{partition}.jsonl",
            (
                label_row(plans[m.observation_id], outcomes[m.observation_id], refs)
                for m in data.membership
                if m.partition == partition
            ),
        )


def _file_identity(records) -> dict:
    hasher, count = hashlib.sha256(), 0
    for record in records:
        hasher.update(encode(record))
        count += 1
    return {"sha256": hasher.hexdigest(), "rows": count}


def file_identities(data: Dataset) -> dict:
    return {name: _file_identity(rows) for name, rows in _rows(data)}


def render_audit(report: dict) -> str:
    lines = [
        "# Synthetic ML data audit",
        "",
        "SYNTHETIC assumptions, not factory measurements.",
        f"Status: {report['status']}. Observations: {report['observations']}.",
        "",
        "| Partition | Rows |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {name} | {count} |" for name, count in report["partitions"].items())
    lines.extend(["", "| Future test population | Rows |", "| --- | ---: |"])
    lines.extend(f"| {name} | {count} |" for name, count in report["test_populations"].items())
    lines.extend(
        [
            "",
            "| Development target | Valid n | Mean | Above one | Undefined |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for part, summary in report["development_target_statistics"].items():
        lines.append(
            f"| {part} | {summary['count']} | {summary['mean']} | {summary['above_one']} | "
            f"{summary['label_statuses'].get('ZERO_PLANNED_CAPACITY', 0)} |"
        )
    lines.extend(
        [
            "",
            "Reserved test: physical/integrity checks only; no target summaries or scoring.",
            f"Deterministic replay verified: {report['replay_verified']}.",
            "No model training or automatic planning conversion.",
            "",
        ]
    )
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    lines.extend(f"- Warning: {warning}" for warning in report["warnings"])
    return "\n".join(lines) + "\n"


def write_bundle(
    data: Dataset,
    config: GenerationConfig,
    output: Path,
    *,
    configuration_sha256: str,
    profile: str,
) -> dict:
    """Validate/replay before creating output; manifest is the final completion marker."""
    base, target = OUTPUT_ROOT.resolve(), output.resolve()
    if target == base or not target.is_relative_to(base):
        raise ValueError(
            "Generated bundles must be new directories under data/processed/synthetic_ml."
        )
    if target.exists():
        raise ValueError("Dataset output already exists; choose a new directory.")
    if re.fullmatch(r"[a-f0-9]{64}", configuration_sha256) is None:
        raise ValueError("Retained configuration file SHA-256 required.")
    validate_dataset(data, config)
    if data != generate(config):
        raise ValueError("Generated records differ from deterministic configuration replay.")
    report = quality_report(data, config, replay_verified=True)
    target.mkdir(parents=True, exist_ok=False)
    identities = {}
    for name, rows in _rows(data):
        hasher, count = hashlib.sha256(), 0
        with (target / name).open("xb") as destination:
            for row in rows:
                content = encode(row)
                destination.write(content)
                hasher.update(content)
                count += 1
        identities[name] = {"sha256": hasher.hexdigest(), "rows": count}
    for name, content in (
        ("quality.json", encode(report)),
        ("audit.md", render_audit(report).encode("utf-8")),
    ):
        with (target / name).open("xb") as destination:
            destination.write(content)
        identities[name] = {"sha256": hashlib.sha256(content).hexdigest(), "rows": None}
    manifest = {
        "schema_version": 1,
        "dataset_version": DATASET_VERSION,
        "generator_version": GENERATOR_VERSION,
        "synthetic": True,
        "configuration": json_value(asdict(config)),
        "profile": profile,
        "configuration_file_sha256": configuration_sha256,
        "configuration_fingerprint": digest(asdict(config)),
        "content_fingerprint": digest(
            {k: v for k, v in identities.items() if k.endswith(".jsonl")}
        ),
        "files": identities,
        "feature_columns": list(FEATURE_COLUMNS),
        "environment": {"python": platform.python_version(), "loometric": "0.1.0"},
        "reserved_test_policy": report["reserved_test_policy"],
        "model_training_performed": False,
        "planning_conversion_authorized": False,
    }
    with (target / "manifest.json").open("xb") as destination:
        destination.write(encode(manifest))
    return {
        "manifest_fingerprint": digest(manifest),
        "content_fingerprint": manifest["content_fingerprint"],
        "observations": len(data.plans),
        "status": report["status"],
    }


def read_bundle(directory: Path, *, expected_fingerprint: str) -> tuple[Dataset, GenerationConfig]:
    """Closed normalized inputs; derived files are checked against recomputed whitelist/labels."""
    if re.fullmatch(r"[a-f0-9]{64}", expected_fingerprint) is None:
        raise ValueError("Independently retained manifest fingerprint required.")
    manifest_path = directory / "manifest.json"
    if manifest_path.stat().st_size > 32768:
        raise ValueError("Manifest exceeds 32 KiB.")
    manifest = parse_json(manifest_path.read_text(encoding="utf-8"))
    if digest(manifest) != expected_fingerprint or manifest["dataset_version"] != DATASET_VERSION:
        raise ValueError("Manifest identity differs from retained receipt.")
    raw = dict(manifest["configuration"])
    raw["start_date"] = date.fromisoformat(raw["start_date"])
    config = GenerationConfig(**raw)
    expected_files = (
        {f"{name}.jsonl" for name in TABLE_TYPES}
        | {f"labels.{part}.jsonl" for part in ("train", "validation", "test", "gap")}
        | {"features.jsonl", "quality.json", "audit.md"}
    )
    if (
        set(manifest["files"]) != expected_files
        or manifest["generator_version"] != GENERATOR_VERSION
        or manifest["feature_columns"] != list(FEATURE_COLUMNS)
        or manifest["synthetic"] is not True
        or manifest["configuration_fingerprint"] != digest(asdict(config))
        or manifest["model_training_performed"] is not False
        or manifest["planning_conversion_authorized"] is not False
    ):
        raise ValueError("Unsupported dataset manifest policy or files.")
    tables = {}
    for name in sorted(expected_files):
        hasher, count = hashlib.sha256(), 0
        records = []
        with (directory / name).open("rb") as source:
            for content in iter(lambda: source.readline(2 * 1024 * 1024 + 1), b""):
                if len(content) > 2 * 1024 * 1024 or count > 150000:
                    raise ValueError("Dataset file exceeds local inspection limits.")
                hasher.update(content)
                if name.removesuffix(".jsonl") in TABLE_TYPES:
                    cls = TABLE_TYPES[name.removesuffix(".jsonl")]
                    row = parse_json(content.decode("utf-8"))
                    if set(row) != {field.name for field in fields(cls)}:
                        raise ValueError("Closed normalized table fields required.")
                    for field in fields(cls):
                        value = row[field.name]
                        if field.type is datetime:
                            value = datetime.fromisoformat(value)
                        elif field.type is Decimal:
                            if not isinstance(value, str) or not re.fullmatch(
                                r"[0-9]+(?:\.[0-9]{1,2})?", value
                            ):
                                raise ValueError("Standards require exact decimal strings.")
                            value = Decimal(value)
                        elif field.type is Stage:
                            value = Stage(value)
                        row[field.name] = value
                    records.append(cls(**row))
                count += 1
        identity = manifest["files"][name]
        if hasher.hexdigest() != identity["sha256"] or (
            name.endswith(".jsonl") and count != identity["rows"]
        ):
            raise ValueError("Dataset content digest/count differs from manifest.")
        if name.removesuffix(".jsonl") in TABLE_TYPES:
            tables[name.removesuffix(".jsonl")] = tuple(records)
    data = Dataset(**tables)
    validate_dataset(data, config)
    expected = file_identities(data)
    if any(manifest["files"][name] != identity for name, identity in expected.items()) or (
        manifest["content_fingerprint"] != digest(expected)
    ):
        raise ValueError("Derived feature/label files differ from the outcome-free contract.")
    return data, config
