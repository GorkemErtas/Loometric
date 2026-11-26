"""Two-pass frozen-generator adapter; no quality statistics, fitting or prediction."""

from collections import Counter
from dataclasses import asdict
from pathlib import Path

from loometric.prospective_evaluation.source import (
    SOURCE_TABLES,
    SourceDesign,
    audit_source,
    require,
    scoped_entities,
)
from loometric.prospective_evaluation.storage import (
    FILES,
    MAX_BUNDLE_BYTES,
    core_identity,
    encode,
    environment,
    identity,
    manifest_policy,
    records_bytes,
    root_size,
    safe_path,
    sha256,
    write_new,
)
from loometric.synthetic_ml.contracts import Dataset
from loometric.synthetic_ml.features import FEATURE_COLUMNS, References, label_row
from loometric.synthetic_ml.generation import generate
from loometric.synthetic_ml.validation import validate_dataset


def projection_files(data: Dataset, design: SourceDesign) -> dict[str, bytes]:
    features = audit_source(data, design)
    buffers = {f"{table}.jsonl": records_bytes(getattr(data, table)) for table in SOURCE_TABLES}
    buffers["features.jsonl"] = records_bytes(features)
    buffers["scoped_entities.jsonl"] = records_bytes(scoped_entities(data, design.case.world_id))
    buffers["score_ids.jsonl"] = records_bytes(
        {"world_id": design.case.world_id, "local_observation_id": row.observation_id}
        for row in data.membership
        if row.partition == "validation"
    )
    return buffers


def source_audit(data: Dataset, design: SourceDesign) -> dict:
    refs = References.from_dataset(data)
    score_ids = {m.observation_id for m in data.membership if m.partition == "validation"}
    score = [p for p in data.plans if p.observation_id in score_ids]
    return {
        "source_rows": len(data.plans),
        "planned_score_rows": len(score),
        "score_dates": [d.isoformat() for d in design.case.score_dates],
        "partition_rows": dict(Counter(m.partition for m in data.membership)),
        "stage_score_rows": dict(Counter(refs.lines[p.line_id].stage.value for p in score)),
        "score_factories": len({refs.lines[p.line_id].factory_id for p in score}),
        "score_lines": len({p.line_id for p in score}),
        "score_crews": len({p.crew_id for p in score}),
        "score_styles": len({refs.orders[p.order_id].style_id for p in score}),
    }


def expected_manifest(design: SourceDesign, data: Dataset, files: dict, history: dict) -> dict:
    return {
        **manifest_policy(),
        "case_id": design.case.case_id,
        "world_id": design.case.world_id,
        "seed": design.case.seed,
        "condition": design.case.condition,
        "source_configuration": asdict(design.configuration),
        "feature_columns": list(FEATURE_COLUMNS),
        "target": "standard_capacity_attainment",
        "units": "dimensionless_standard_worker_minutes_per_planned_worker_minute",
        "environment": environment(),
        "infrastructure_code": core_identity(),
        "historical_inventory": history,
        "audit": source_audit(data, design),
        "files": files,
        "replay": {"generations": 2, "files": files},
    }


def _publication_buffers(design: SourceDesign) -> tuple[Dataset, dict[str, bytes]]:
    """Exactly two full generation calls, including all physical integrity checks."""
    first = generate(design.configuration)
    second = generate(design.configuration)
    validate_dataset(first, design.configuration)
    validate_dataset(second, design.configuration)

    def buffers(data):
        result = projection_files(data, design)
        result["outcomes.jsonl"] = records_bytes(data.outcomes)
        refs = References.from_dataset(data)
        plans = {p.observation_id: p for p in data.plans}
        outcomes = {o.observation_id: o for o in data.outcomes}
        for partition in ("train", "validation", "gap", "test"):
            result[f"labels.{partition}.jsonl"] = records_bytes(
                label_row(plans[m.observation_id], outcomes[m.observation_id], refs)
                for m in data.membership
                if m.partition == partition
            )
        return result

    left, right = buffers(first), buffers(second)
    require(set(left) == FILES and left == right, "DETERMINISTIC_SOURCE_REPLAY_FAILED")
    require(sum(len(v) for v in left.values()) <= MAX_BUNDLE_BYTES, "DATASET_BUNDLE_BYTE_LIMIT")
    return first, left


def case_relative(design: SourceDesign) -> str:
    return f"datasets/{design.case.case_id}"


def pair_check(left: dict, right: dict) -> None:
    require(
        left["seed"] == right["seed"]
        and left["world_id"] == right["world_id"]
        and left["condition"] == "baseline"
        and right["condition"] == "disruption",
        "MATCHED_CASE_PAIR_REQUIRED",
    )
    # All pre-cutoff tables, not just the thirteen estimator fields, must match.
    from loometric.prospective_evaluation.storage import READABLE

    require(
        all(left["files"][name] == right["files"][name] for name in READABLE),
        "MATCHED_BASELINE_DISRUPTION_INPUT_DRIFT",
    )


def _prepare_batch(root: Path, designs: tuple[SourceDesign, ...], history) -> dict:
    """Internal mechanical-test seam; production obtains designs only from the pinned protocol."""
    require(
        len(designs) == 8 and len({d.case.case_id for d in designs}) == 8,
        "EXACT_EIGHT_CASES_REQUIRED",
    )
    require(not safe_path(root, "receipts/datasets.json").exists(), "EXISTING_RECEIPT_LEDGER")
    datasets = safe_path(root, "datasets")
    require(
        not datasets.exists() or (datasets.is_dir() and not any(datasets.iterdir())),
        "CREATE_ONLY_DATASET_REQUIRED",
    )
    for design in designs:
        require(not safe_path(root, case_relative(design)).exists(), "CREATE_ONLY_DATASET_REQUIRED")
    root_size(root)
    receipts = {}
    for offset in range(0, 8, 2):
        pending = []
        for design in designs[offset : offset + 2]:
            data, buffers = _publication_buffers(design)
            keys = {
                (r["kind"], r["world_id"], r["local_id"])
                for r in scoped_entities(data, design.case.world_id)
            }
            require(not keys.intersection(history.keys), "HISTORICAL_ENTITY_ALIAS")
            manifest = expected_manifest(
                design, data, {n: identity(v) for n, v in sorted(buffers.items())}, history.receipt
            )
            manifest_bytes = encode(manifest)
            require(
                sum(map(len, buffers.values())) + len(manifest_bytes) <= MAX_BUNDLE_BYTES,
                "DATASET_BUNDLE_BYTE_LIMIT",
            )
            pending.append((design, buffers, manifest, manifest_bytes))
        pair_check(pending[0][2], pending[1][2])
        for design, buffers, _manifest, content in pending:
            prefix = case_relative(design)
            safe_path(root, prefix).mkdir(parents=True, exist_ok=False)
            for name, value in sorted(buffers.items()):
                write_new(root, f"{prefix}/{name}", value)
            write_new(root, f"{prefix}/manifest.json", content)  # Completion marker, last.
            receipts[design.case.case_id] = sha256(content)
    return {
        "status": "SOURCE_GENERATION_REPLAY_VERIFIED",
        "datasets": receipts,
        "promotion_decision": "NO_ML_PROMOTION",
    }
