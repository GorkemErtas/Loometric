"""Receipt-bound development loading; reserved outcome values are never decoded."""

import hashlib
import re
from collections import Counter
from dataclasses import dataclass, fields
from datetime import date, datetime, timedelta
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pandas as pd

from loometric.planning.domain import Stage
from loometric.planning.loading import parse_json
from loometric.synthetic_ml.configuration import GenerationConfig
from loometric.synthetic_ml.contracts import (
    DATASET_VERSION,
    GENERATOR_VERSION,
    TABLE_TYPES,
    Dataset,
    target_value,
)
from loometric.synthetic_ml.features import FEATURE_COLUMNS, References, feature_row
from loometric.synthetic_ml.splitting import date_partitions, population
from loometric.synthetic_ml.storage import digest

CATEGORICAL = ("stage", "shift_kind", "weekday")
NUMERIC = tuple(c for c in FEATURE_COLUMNS if c not in CATEGORICAL)
AUTHORIZED = ("train", "validation")
EXPECTED_FILES = (
    {f"{name}.jsonl" for name in TABLE_TYPES}
    | {f"labels.{p}.jsonl" for p in ("train", "validation", "gap", "test")}
    | {"features.jsonl", "quality.json", "audit.md"}
)


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError(code)


def fingerprint(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def _verify_files(directory: Path, manifest: dict) -> None:
    require(set(manifest["files"]) == EXPECTED_FILES, "CLOSED_BUNDLE_FILES_REQUIRED")
    total = 0
    for name in sorted(EXPECTED_FILES):
        path = directory / name
        require(path.resolve().parent == directory.resolve(), "BUNDLE_FILE_OUTSIDE_DIRECTORY")
        total += path.stat().st_size
        require(
            path.stat().st_size <= 256 * 1024 * 1024 and total <= 512 * 1024 * 1024,
            "BUNDLE_BYTE_LIMIT",
        )
        hasher, rows, last = hashlib.sha256(), 0, b""
        with path.open("rb") as source:
            for block in iter(lambda: source.read(65536), b""):
                hasher.update(block)
                rows += block.count(b"\n")
                last = block[-1:]
        identity = manifest["files"][name]
        require(hasher.hexdigest() == identity["sha256"], "BUNDLE_DIGEST_DRIFT")
        if name.endswith(".jsonl"):
            require(
                last in (b"", b"\n")
                and type(identity["rows"]) is int
                and rows == identity["rows"]
                and rows <= 150000,
                "BUNDLE_ROW_COUNT_DRIFT",
            )
    content = {
        name: manifest["files"][name] for name in sorted(EXPECTED_FILES) if name.endswith(".jsonl")
    }
    require(digest(content) == manifest["content_fingerprint"], "BUNDLE_CONTENT_FINGERPRINT_DRIFT")


def _json_rows(path: Path):
    # This decoder is never called for outcomes, gap/test labels, audit or quality reports.
    require(
        path.name not in {"outcomes.jsonl", "labels.gap.jsonl", "labels.test.jsonl"},
        "RESERVED_VALUE_DECODE_PROHIBITED",
    )
    with path.open("rb") as source:
        for line in iter(lambda: source.readline(32769), b""):
            require(len(line) <= 32768, "DEVELOPMENT_RECORD_BYTE_LIMIT")
            row = parse_json(line.decode("utf-8"))
            require(isinstance(row, dict), "DEVELOPMENT_RECORD_OBJECT_REQUIRED")
            yield row


def _typed_table(directory: Path, name: str) -> tuple:
    require(name != "outcomes", "RESERVED_VALUE_DECODE_PROHIBITED")
    cls = TABLE_TYPES[name]
    records, identities = [], set()
    for raw in _json_rows(directory / f"{name}.jsonl"):
        require(set(raw) == {f.name for f in fields(cls)}, "CLOSED_SOURCE_SCHEMA_REQUIRED")
        converted = {}
        for field in fields(cls):
            value = raw[field.name]
            if field.type is datetime:
                require(isinstance(value, str), "TIMESTAMP_STRING_REQUIRED")
                value = datetime.fromisoformat(value)
                require(
                    value.tzinfo is not None
                    and value.utcoffset() is not None
                    and value.second == value.microsecond == 0,
                    "AWARE_MINUTE_TIMESTAMP_REQUIRED",
                )
            elif field.type is Decimal:
                require(
                    isinstance(value, str)
                    and re.fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", value) is not None,
                    "EXACT_STANDARD_STRING_REQUIRED",
                )
                value = Decimal(value)
                require(value.is_finite() and value > 0, "POSITIVE_STANDARD_REQUIRED")
            elif field.type is Stage:
                value = Stage(value)
            else:
                require(type(value) is field.type, "STRICT_SOURCE_TYPE_REQUIRED")
                if field.type is int:
                    require(value >= 0, "NONNEGATIVE_SOURCE_COUNT_REQUIRED")
                if field.type is str:
                    require(
                        bool(value) and value == value.strip() and len(value) <= 200,
                        "CANONICAL_SOURCE_TEXT_REQUIRED",
                    )
            converted[field.name] = value
        key = next(iter(converted.values()))
        require(key not in identities, "DUPLICATE_SOURCE_ID")
        identities.add(key)
        records.append(cls(**converted))
    return tuple(records)


def exact_float(value: Decimal | int | bool) -> float:
    require(type(value) in (Decimal, int, bool), "VALIDATED_NUMERIC_SOURCE_REQUIRED")
    number = Decimal(int(value)) if type(value) in (int, bool) else value
    require(number.is_finite(), "FINITE_SOURCE_NUMBER_REQUIRED")
    converted = float(number)
    require(
        abs(Fraction.from_float(converted) - Fraction(number)) <= Fraction(1, 10**12),
        "FLOAT_CONVERSION_TOLERANCE_EXCEEDED",
    )
    return converted


@dataclass(frozen=True)
class Population:
    X: pd.DataFrame
    y: pd.Series
    metadata: pd.DataFrame
    excluded: tuple[dict, ...]
    source_fingerprint: str


@dataclass(frozen=True)
class DevelopmentData:
    train: Population
    validation: Population
    provenance: dict
    audit: dict


def _population(
    directory: Path, partition: str, plans: dict, refs: References, stored: dict, label_delay: int
) -> Population:
    require(partition in AUTHORIZED, "PARTITION_NOT_AUTHORIZED_FOR_DEVELOPMENT")
    features, labels, metadata, ids, excluded, source_rows = [], [], [], [], [], []
    observed = set()
    for label in _json_rows(directory / f"labels.{partition}.jsonl"):
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
            "CLOSED_LABEL_SCHEMA_REQUIRED",
        )
        oid = label["observation_id"]
        require(oid in plans and oid not in observed, "LABEL_PARTITION_OR_ID_MISMATCH")
        observed.add(oid)
        plan = plans[oid]
        expected = feature_row(plan, refs)
        require(oid in stored and digest(expected) == digest(stored[oid]), "FEATURE_VIEW_DRIFT")
        inputs = expected["inputs"]
        available = inputs["available_minutes"] * plan.planned_workers
        require(
            type(label["planned_available_worker_minutes"]) is int
            and label["planned_available_worker_minutes"] == available,
            "PLANNED_DENOMINATOR_DRIFT",
        )
        require(
            isinstance(label["earned_standard_worker_minutes"], str), "EXACT_LABEL_STRING_REQUIRED"
        )
        earned = Decimal(label["earned_standard_worker_minutes"])
        standard = refs.standards[plan.standard_id].worker_minutes_per_piece
        require(earned.is_finite() and earned >= 0, "INVALID_EARNED_LABOR")
        completed = Fraction(earned) / Fraction(standard)
        require(
            completed.denominator == 1
            and completed <= inputs["order_quantity"]
            and earned <= available * 3,
            "COMPLETED_PIECE_OR_LABOR_INCONSISTENCY",
        )
        status, target = target_value(int(completed), standard, available)
        require(label["status"] == status, "LABEL_STATUS_DRIFT")
        require(
            (target is None and label["standard_capacity_attainment"] is None)
            or (
                target is not None
                and isinstance(label["standard_capacity_attainment"], str)
                and Decimal(label["standard_capacity_attainment"]) == target
            ),
            "LABEL_FORMULA_DRIFT",
        )
        shift = refs.shifts[plan.shift_id]
        available_at = datetime.fromisoformat(label["available_at"])
        require(
            available_at.tzinfo is not None
            and available_at == shift.end + timedelta(minutes=label_delay),
            "LABEL_MATURITY_REQUIRED",
        )
        source_rows.append({"feature": expected, "label": label})
        if target is None:
            excluded.append(
                {
                    "observation_id": oid,
                    "reason": "ZERO_PLANNED_CAPACITY_UNDEFINED_TARGET",
                    "inputs": inputs,
                    "prediction_attempted": False,
                }
            )
            continue
        features.append(
            {
                c: str(inputs[c]) if c in CATEGORICAL else exact_float(inputs[c])
                for c in FEATURE_COLUMNS
            }
        )
        labels.append(exact_float(target))
        load = Fraction(inputs["order_quantity"]) * Fraction(standard) / available
        metadata.append(
            {
                "start_date": shift.start.date(),
                "cutoff": plan.cutoff,
                "label_available_at": available_at,
                "stage": inputs["stage"],
                "shift_kind": inputs["shift_kind"],
                "staffing_band": "1-5"
                if plan.planned_workers <= 5
                else "6-10"
                if plan.planned_workers <= 10
                else "11+",
                "workload_band": "low"
                if load <= Fraction(3, 5)
                else "nominal"
                if load <= 1
                else "high",
                "planned_load_ratio": float(load),
                "low_demand": load <= Fraction(3, 5),
                "demand_censored": completed == inputs["order_quantity"],
                "interruption_band": "none"
                if inputs["planned_downtime_minutes"] == 0
                else "1-30"
                if inputs["planned_downtime_minutes"] <= 30
                else "31+",
            }
        )
        ids.append(oid)
    require(observed == set(plans) and bool(labels), "AUTHORIZED_LABEL_COVERAGE_REQUIRED")
    index = pd.Index(ids, name="observation_id")
    return Population(
        pd.DataFrame(features, index=index, columns=FEATURE_COLUMNS),
        pd.Series(labels, index=index, name="standard_capacity_attainment", dtype="float64"),
        pd.DataFrame(metadata, index=index),
        tuple(excluded),
        digest(source_rows),
    )


def load_development(directory: Path, *, expected_fingerprint: str) -> DevelopmentData:
    """Hash every byte first; decode only pre-shift tables and authorized labels."""
    require(
        isinstance(expected_fingerprint, str)
        and re.fullmatch(r"[a-f0-9]{64}", expected_fingerprint) is not None,
        "INDEPENDENT_MANIFEST_RECEIPT_REQUIRED",
    )
    path = directory / "manifest.json"
    require(path.stat().st_size <= 32768, "MANIFEST_BYTE_LIMIT")
    manifest = parse_json(path.read_text(encoding="utf-8"))
    require(digest(manifest) == expected_fingerprint, "MANIFEST_RECEIPT_MISMATCH")
    require(
        type(manifest["schema_version"]) is int
        and manifest["schema_version"] == 1
        and manifest["dataset_version"] == DATASET_VERSION
        and manifest["generator_version"] == GENERATOR_VERSION
        and manifest["synthetic"] is True
        and manifest["feature_columns"] == list(FEATURE_COLUMNS)
        and manifest["model_training_performed"] is False
        and manifest["planning_conversion_authorized"] is False,
        "UNSUPPORTED_SOURCE_CONTRACT",
    )
    _verify_files(directory, manifest)
    raw = dict(manifest["configuration"])
    raw["start_date"] = date.fromisoformat(raw["start_date"])
    config = GenerationConfig(**raw)
    require(
        digest(manifest["configuration"]) == manifest["configuration_fingerprint"],
        "CONFIGURATION_DRIFT",
    )
    tables = {name: _typed_table(directory, name) for name in TABLE_TYPES if name != "outcomes"}
    data = Dataset(**tables, outcomes=())
    refs = References.from_dataset(data)
    members = {m.observation_id: m for m in data.membership}
    require(set(members) == {p.observation_id for p in data.plans}, "MEMBERSHIP_COVERAGE_DRIFT")
    days = date_partitions(config)
    selected = {p: {} for p in AUTHORIZED}
    for plan in data.plans:
        shift, line, crew = (
            refs.shifts[plan.shift_id],
            refs.lines[plan.line_id],
            refs.crews[plan.crew_id],
        )
        order, standard = refs.orders[plan.order_id], refs.standards[plan.standard_id]
        member = members[plan.observation_id]
        require(member.partition == days[shift.start.date()], "CHRONOLOGICAL_PARTITION_DRIFT")
        require(
            line.factory_id == shift.factory_id
            and crew.line_id == line.line_id
            and crew.shift_kind == shift.kind
            and crew.qualified_stage == line.stage == standard.stage
            and standard.style_id == order.style_id
            and plan.planned_workers <= crew.roster_size
            and plan.opening_wip_pieces + plan.planned_release_pieces == order.quantity
            and plan.cutoff == shift.start - timedelta(minutes=30),
            "SOURCE_PLAN_REFERENCE_DRIFT",
        )
        if member.partition in AUTHORIZED:
            require(
                member.population == "familiar"
                and population(line.factory_id, line.line_id, crew.crew_id, order.style_id, config)
                == "future_familiar",
                "DEVELOPMENT_ENTITY_HOLDOUT_DRIFT",
            )
            selected[member.partition][plan.observation_id] = plan
    ids = set(selected["train"]) | set(selected["validation"])
    stored = {}
    for row in _json_rows(directory / "features.jsonl"):
        require(
            set(row) == {"observation_id", "cutoff", "context", "inputs"}
            and set(row["inputs"]) == set(FEATURE_COLUMNS),
            "CLOSED_FEATURE_WHITELIST_REQUIRED",
        )
        if row["observation_id"] in ids:
            require(row["observation_id"] not in stored, "DUPLICATE_FEATURE_ID")
            stored[row["observation_id"]] = row
    train, validation = (
        _population(directory, p, selected[p], refs, stored, config.label_delay_minutes)
        for p in AUTHORIZED
    )
    require(
        max(train.metadata["label_available_at"]) < min(validation.metadata["cutoff"]),
        "TRAIN_LABELS_NOT_MATURE_BEFORE_VALIDATION",
    )
    _verify_files(directory, manifest)
    return DevelopmentData(
        train,
        validation,
        {
            "manifest_fingerprint": expected_fingerprint,
            "content_fingerprint": manifest["content_fingerprint"],
            "configuration_fingerprint": manifest["configuration_fingerprint"],
            "profile": manifest["profile"],
            "seed": config.seed,
            "scenario": config.scenario,
            "split_fingerprint": digest([vars(m) for m in data.membership]),
            "train_fingerprint": train.source_fingerprint,
            "validation_fingerprint": validation.source_fingerprint,
        },
        {
            "valid_train_rows": len(train.X),
            "valid_validation_rows": len(validation.X),
            "undefined_train_rows": len(train.excluded),
            "undefined_validation_rows": len(validation.excluded),
            "partition_rows": dict(Counter(m.partition for m in data.membership)),
            "label_files_decoded": ["labels.train.jsonl", "labels.validation.jsonl"],
            "reserved_labels_decoded": False,
            "reserved_bytes_hashed_for_integrity": True,
            "float_absolute_conversion_tolerance": "0.000000000001",
        },
    )
