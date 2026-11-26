"""Isolated new-world history projection and closed create-only source receipts."""

from collections import defaultdict
from contextvars import ContextVar
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path

from loometric.final_candidate.history import HISTORY_COLUMNS, MatureObservation, history_snapshot
from loometric.prospective_evaluation.protocol import ROOT
from loometric.prospective_evaluation.source import require
from loometric.prospective_evaluation.storage import (
    decode_rows,
    encode,
    identity,
    opaque_identity,
    read_checked,
    sha256,
    write_new,
)
from loometric.synthetic_ml.configuration import GenerationConfig
from loometric.synthetic_ml.features import FEATURE_COLUMNS, References, feature_row, label_row
from loometric.synthetic_ml.generation import generate
from loometric.synthetic_ml.splitting import date_partitions
from loometric.synthetic_ml.validation import validate_dataset
from loometric.synthetic_training.data import CATEGORICAL, exact_float

DIRECTORY = ROOT / "data/processed/final_candidate/exp-010"
CONFIG_PATH = ROOT / "configs/final_candidate_v1.json"
PARTITIONS = ("fit", "development", "evaluation", "context", "embargo")
FILES = {"features.jsonl", *(f"labels.{p}.jsonl" for p in PARTITIONS)}
ROW_FIELDS = {
    "id",
    "local_id",
    "world_id",
    "split",
    "date",
    "cutoff",
    "label_available_at",
    "inputs",
    "history",
    "history_sources",
    "history_latest_available_at",
    "defined_target",
    "context",
}
_label_path: ContextVar[Path | None] = ContextVar("final_label_path", default=None)
evaluation_labels_enabled: ContextVar[bool] = ContextVar("final_evaluation_unsealed", default=False)


def config() -> dict:
    from loometric.prediction.contracts import read_json

    return read_json(CONFIG_PATH.read_text(encoding="utf-8"))


def core_identity() -> dict:
    return {
        name: sha256(Path(__file__).with_name(name).read_bytes())
        for name in ("history.py", "model.py", "data.py", "study.py")
    }


def design(seed: int, condition: str, heldout: bool) -> GenerationConfig:
    c = config()
    require(
        seed in c["heldout_seeds" if heldout else "development_seeds"]
        and condition in c["conditions"],
        "DECLARED_NEW_WORLD_REQUIRED",
    )
    return GenerationConfig(
        seed=seed,
        scenario=condition,
        start_date=date.fromisoformat(c["heldout_start" if heldout else "development_start"]),
        calendar_days=c["calendar_days"],
        **c["source_parameters"],
    )


def project(data, parameters: GenerationConfig, heldout: bool) -> dict[str, bytes]:
    """History is computed before adding the current observation; only mature reports qualify."""
    settings = config()
    refs = References.from_dataset(data)
    outcomes = {o.observation_id: o for o in data.outcomes}
    memberships = {m.observation_id: m.partition for m in data.membership}
    validation_dates = [d for d, p in date_partitions(parameters).items() if p == "validation"]
    snapshots, labels, history = [], defaultdict(list), []
    world = f"exp-010-world-{parameters.seed}"
    for plan in sorted(data.plans, key=lambda p: (p.cutoff, p.observation_id)):
        partition = memberships[plan.observation_id]
        if partition not in ("train", "validation"):
            continue  # No source gap/test target is materialized or used in history.
        feature = feature_row(plan, refs)
        label = label_row(plan, outcomes[plan.observation_id], refs)
        shift = refs.shifts[plan.shift_id]
        if partition == "train":
            split = "context" if heldout or parameters.scenario != "baseline" else "fit"
        elif heldout:
            split = "evaluation"
        else:
            position = validation_dates.index(shift.start.date())
            fit_dates = settings["development_validation_fit_dates"]
            embargo_end = fit_dates + settings["development_validation_embargo_dates"]
            split = (
                "fit"
                if position < fit_dates
                else "embargo"
                if position < embargo_end
                else "development"
            )
        past = history_snapshot(
            history,
            crew_id=plan.crew_id,
            line_id=plan.line_id,
            observation_id=plan.observation_id,
            shift_start=shift.start,
            cutoff=plan.cutoff,
        )
        inputs = {
            name: str(value) if name in CATEGORICAL else exact_float(value)
            for name, value in feature["inputs"].items()
        }
        row = {
            "id": f"{world}::{plan.observation_id}",
            "local_id": plan.observation_id,
            "world_id": world,
            "split": split,
            "date": shift.start.date().isoformat(),
            "cutoff": plan.cutoff.isoformat(),
            "label_available_at": label["available_at"].isoformat(),
            "inputs": inputs,
            "history": {k: past[k] for k in HISTORY_COLUMNS},
            "history_sources": past["source_observation_ids"],
            "history_latest_available_at": past["latest_available_at"],
            "defined_target": label["standard_capacity_attainment"] is not None,
            "context": {k: f"{world}::{v}" for k, v in feature["context"].items()},
        }
        snapshots.append(row)
        target = label["standard_capacity_attainment"]
        labels[split].append(
            {
                "id": row["id"],
                "actual": exact_float(target) if target is not None else None,
                "available_at": label["available_at"].isoformat(),
            }
        )
        if target is not None:
            history.append(
                MatureObservation(
                    plan.observation_id,
                    plan.crew_id,
                    plan.line_id,
                    shift.start,
                    label["available_at"],
                    exact_float(target),
                    outcomes[plan.observation_id].completed_good_pieces
                    == refs.orders[plan.order_id].quantity,
                )
            )
    return {
        "features.jsonl": b"".join(encode(r) for r in snapshots),
        **{f"labels.{p}.jsonl": b"".join(encode(r) for r in labels[p]) for p in PARTITIONS},
    }


def prepare(heldout: bool, root: Path | None = None) -> dict:
    root = root if root is not None else DIRECTORY
    c = config()
    group = "heldout" if heldout else "development"
    require(not (root / group).exists(), "CREATE_ONLY_NEW_SOURCES_REQUIRED")
    receipts = {}
    for seed in c["heldout_seeds" if heldout else "development_seeds"]:
        baseline_inputs = None
        for condition in c["conditions"]:
            parameters = design(seed, condition, heldout)
            first, second = generate(parameters), generate(parameters)
            validate_dataset(first, parameters)
            validate_dataset(second, parameters)
            buffers = project(first, parameters, heldout)
            require(buffers == project(second, parameters, heldout), "SOURCE_REPLAY_FAILED")
            projected = decode_rows("features.jsonl", buffers["features.jsonl"])
            input_identity = sha256(
                encode(
                    [{k: r[k] for k in ("id", "inputs", "cutoff", "context")} for r in projected]
                )
            )
            if baseline_inputs is None:
                baseline_inputs = input_identity
            else:
                require(input_identity == baseline_inputs, "MATCHED_RAW_INPUT_DRIFT")
            case = f"{seed}-{condition}"
            manifest = {
                "dataset_version": c["dataset_version"],
                "seed": seed,
                "condition": condition,
                "heldout": heldout,
                "configuration": asdict(parameters),
                "configuration_sha256": sha256(encode(c)),
                "code": core_identity(),
                "source_rows": len(first.plans),
                "generations": 2,
                "files": {k: identity(v) for k, v in buffers.items()},
                "promotion_decision": "NO_ML_PROMOTION",
            }
            for name, value in buffers.items():
                write_new(root, f"{group}/{case}/{name}", value)
            content = encode(manifest)
            write_new(root, f"{group}/{case}/manifest.json", content)
            receipts[case] = sha256(content)
    return receipts


def read_case(root: Path, group: str, case: str, expected: str) -> tuple[list[dict], dict]:
    from loometric.prediction.contracts import read_json

    directory = root / group / case
    require(directory.resolve() == directory.absolute(), "SOURCE_PATH_ESCAPE")
    require(
        {p.name for p in directory.iterdir()} == FILES | {"manifest.json"}, "CLOSED_SOURCE_REQUIRED"
    )
    raw = read_checked(directory / "manifest.json", 65536)
    require(sha256(raw) == expected, "INDEPENDENT_SOURCE_RECEIPT_DRIFT")
    manifest = read_json(raw.decode())
    require(
        manifest["code"] == core_identity()
        and manifest["configuration_sha256"] == sha256(encode(config())),
        "SOURCE_CODE_OR_CONFIG_DRIFT",
    )
    require(set(manifest["files"]) == FILES, "CLOSED_SOURCE_REQUIRED")
    for name, expected_file in manifest["files"].items():
        require(opaque_identity(directory / name) == expected_file, "SOURCE_FILE_RECEIPT_DRIFT")
    rows = decode_rows("features.jsonl", read_checked(directory / "features.jsonl", 32 * 1024**2))
    require(len({r["id"] for r in rows}) == len(rows), "UNIQUE_OBSERVATIONS_REQUIRED")
    indexed = {r["local_id"]: r for r in rows}
    for row in rows:
        require(
            set(row) == ROW_FIELDS and type(row["defined_target"]) is bool,
            "CLOSED_OUTCOME_FREE_ROW_REQUIRED",
        )
        require(
            tuple(sorted(row["inputs"])) == tuple(sorted(FEATURE_COLUMNS))
            and set(row["history"]) == set(HISTORY_COLUMNS),
            "CLOSED_HISTORY_FEATURES_REQUIRED",
        )
        if row["history_latest_available_at"] is not None:
            require(
                datetime.fromisoformat(row["history_latest_available_at"])
                <= datetime.fromisoformat(row["cutoff"]),
                "FUTURE_HISTORY_PROHIBITED",
            )
        require(
            row["local_id"] not in row["history_sources"] and len(row["history_sources"]) <= 7,
            "CURRENT_OR_EXCESS_HISTORY_PROHIBITED",
        )
        cutoff = datetime.fromisoformat(row["cutoff"])
        require(
            cutoff.tzinfo is not None
            and datetime.fromisoformat(row["label_available_at"])
            == cutoff + timedelta(minutes=630),
            "TARGET_AVAILABILITY_DRIFT",
        )
        for parent_id in row["history_sources"]:
            require(parent_id in indexed, "UNKNOWN_HISTORY_SOURCE")
            parent = indexed[parent_id]
            require(
                all(parent["context"][key] == row["context"][key] for key in ("crew_id", "line_id"))
                and datetime.fromisoformat(parent["label_available_at"]) <= cutoff
                and datetime.fromisoformat(parent["cutoff"]) < cutoff,
                "FUTURE_OR_OTHER_ENTITY_HISTORY_PROHIBITED",
            )
    return rows, manifest


def read_labels(
    root: Path, group: str, case: str, partition: str, *, expected_manifest_sha: str | None = None
) -> dict:
    from loometric.prediction.contracts import read_json

    require(
        (group == "development" and partition in ("fit", "development"))
        or (group == "heldout" and partition == "evaluation"),
        "RESERVED_LABEL_ACCESS_PROHIBITED",
    )
    path = root / group / case / f"labels.{partition}.jsonl"
    manifest_bytes = read_checked(path.parent / "manifest.json", 65536)
    require(sha256(manifest_bytes) == expected_manifest_sha, "INDEPENDENT_LABEL_MANIFEST_REQUIRED")
    manifest = read_json(manifest_bytes.decode())
    token = _label_path.set(path.resolve())
    try:
        raw = read_checked(path, 32 * 1024**2)
    finally:
        _label_path.reset(token)
    require(identity(raw) == manifest["files"][path.name], "LABEL_BYTES_DRIFT_BEFORE_DECODE")
    result = [read_json(line) for line in raw.decode().splitlines()]
    require(len(result) == len({r["id"] for r in result}), "UNIQUE_LABELS_REQUIRED")
    return {r["id"]: r for r in result}
