"""Label-blind join inspection, historical reference inventory and independent receipt ledgers."""

from collections import Counter
from dataclasses import dataclass, fields
from pathlib import Path

from loometric.prediction.contracts import read_json
from loometric.prospective_evaluation.generation import (
    case_relative,
    expected_manifest,
    pair_check,
    projection_files,
)
from loometric.prospective_evaluation.protocol import ROOT
from loometric.prospective_evaluation.source import (
    ENTITY_FIELDS,
    SourceDesign,
    expected_source,
    require,
    scoped_entities,
)
from loometric.prospective_evaluation.storage import (
    FILES,
    MAX_BUNDLE_BYTES,
    MAX_FILE_BYTES,
    MAX_MANIFEST_BYTES,
    READABLE,
    RESERVED,
    core_identity,
    decode_rows,
    encode,
    environment,
    identity,
    manifest_policy,
    opaque_identity,
    read_checked,
    records_bytes,
    require_sha,
    root_size,
    safe_path,
    sha256,
    write_new,
)
from loometric.synthetic_ml.contracts import TABLE_TYPES

REFERENCE_TABLES = ("factories", "lines", "crews", "styles", "standards")


@dataclass(frozen=True)
class HistoricalInventory:
    keys: frozenset[tuple[str, str, str]]
    receipt: dict


def historical_bindings() -> tuple[dict, ...]:
    config = read_json((ROOT / "configs/synthetic_training_v1.json").read_text(encoding="utf-8"))
    return tuple(config["datasets"])


def _historical_inventory(bindings: tuple[dict, ...], repository: Path) -> HistoricalInventory:
    """Only old reference tables/manifest; never old features, labels or outcomes."""
    keys, evidence = set(), {}
    for binding in bindings:
        directory = safe_path(repository, binding["directory"])
        raw = read_checked(directory / "manifest.json", MAX_MANIFEST_BYTES)
        require(sha256(raw) == binding["expected_manifest_fingerprint"], "HISTORICAL_RECEIPT_DRIFT")
        manifest = read_json(raw.decode("utf-8"))
        require(
            manifest["dataset_version"] == "synthetic-ml-v1"
            and manifest["generator_version"] == "stage-shift-process-v1"
            and manifest["configuration"]["seed"] == binding["seed"]
            and manifest["configuration"]["scenario"] == binding["scenario"],
            "HISTORICAL_SOURCE_IDENTITY_DRIFT",
        )
        world = f"historical-{binding['profile']}-{binding['seed']}"
        reference_ids = {}
        for name in REFERENCE_TABLES:
            content = read_checked(directory / f"{name}.jsonl", MAX_FILE_BYTES)
            receipt = manifest["files"][f"{name}.jsonl"]
            require(sha256(content) == receipt["sha256"], "HISTORICAL_REFERENCE_DRIFT")
            rows = decode_rows(f"{name}.jsonl", content)
            require(len(rows) == receipt["rows"], "HISTORICAL_REFERENCE_COUNT_DRIFT")
            kind, key = ENTITY_FIELDS[name]
            require(
                all(set(row) == {f.name for f in fields(TABLE_TYPES[name])} for row in rows),
                "CLOSED_HISTORICAL_REFERENCE_REQUIRED",
            )
            ids = [row[key] for row in rows]
            require(
                len(ids) == len(set(ids)) and all(isinstance(v, str) and v for v in ids),
                "HISTORICAL_REFERENCE_ID_DRIFT",
            )
            keys.update((kind, world, local) for local in ids)
            reference_ids[name] = identity(content)
        evidence[binding["case_id"]] = {
            "manifest_sha256": binding["expected_manifest_fingerprint"],
            "world_id": world,
            "references": reference_ids,
        }
    receipt = {
        "bindings": evidence,
        "entities_sha256": sha256(encode(sorted(keys))),
        "reserved_labels_decoded": False,
    }
    return HistoricalInventory(frozenset(keys), receipt)


def historical_inventory() -> HistoricalInventory:
    return _historical_inventory(historical_bindings(), ROOT)


def _inspect_dataset(
    root: Path, design: SourceDesign, expected_sha: str, history: HistoricalInventory
) -> dict:
    require_sha(expected_sha)
    root_size(root)
    directory = safe_path(root, case_relative(design))
    require(directory.is_dir(), "COMPLETE_DATASET_REQUIRED")
    require(
        {p.name for p in directory.iterdir()} == FILES | {"manifest.json"},
        "CLOSED_DATASET_FILE_SET_REQUIRED",
    )
    raw = read_checked(directory / "manifest.json", MAX_MANIFEST_BYTES)
    require(sha256(raw) == expected_sha, "DATASET_MANIFEST_RECEIPT_DRIFT")
    manifest = read_json(raw.decode("utf-8"))
    require(
        isinstance(manifest.get("files"), dict) and set(manifest["files"]) == FILES,
        "CLOSED_DATASET_MANIFEST_REQUIRED",
    )
    # All size bounds are checked from stat before any content/JSON decoding.
    sizes = [safe_path(directory, name).stat().st_size for name in FILES | {"manifest.json"}]
    require(
        max(sizes) <= MAX_FILE_BYTES and sum(sizes) <= MAX_BUNDLE_BYTES, "DATASET_BUNDLE_BYTE_LIMIT"
    )
    buffers, identities = {}, {}
    for name in sorted(FILES):
        path = safe_path(directory, name)
        if name in RESERVED:
            observed = opaque_identity(path)
        else:
            content = read_checked(path, MAX_FILE_BYTES)
            observed = identity(content)
            buffers[name] = content
        require(encode(observed) == encode(manifest["files"][name]), "DATASET_CONTENT_DRIFT")
        identities[name] = observed
    # No generation/outcome stream is called here. Rebuild only pre-cutoff source
    # records, then check the actual verified tables and every materialized join.
    source = expected_source(design.configuration)
    counts = Counter(m.partition for m in source.membership)
    require(
        identities["outcomes.jsonl"]["rows"] == design.case.source_rows
        and all(
            identities[f"labels.{part}.jsonl"]["rows"] == counts[part]
            for part in ("train", "validation", "gap", "test")
        ),
        "OPAQUE_LABEL_OR_OUTCOME_ROW_COUNT_DRIFT",
    )
    expected = projection_files(source, design)
    for name in READABLE:
        rows = decode_rows(name, buffers[name])
        require(
            buffers[name] == records_bytes(rows) == expected[name],
            "SOURCE_JOIN_FEATURE_OR_ENTITY_DRIFT",
        )
    keys = {
        (row["kind"], row["world_id"], row["local_id"])
        for row in scoped_entities(source, design.case.world_id)
    }
    require(not keys.intersection(history.keys), "HISTORICAL_ENTITY_ALIAS")
    canonical = expected_manifest(design, source, identities, history.receipt)
    require(encode(manifest) == encode(canonical), "DATASET_POLICY_OR_PROVENANCE_DRIFT")
    # Rehash all files after the audit; a racing modification cannot be registered.
    require(
        all(
            encode(opaque_identity(safe_path(directory, name))) == encode(identities[name])
            for name in FILES
        ),
        "DATASET_CHANGED_DURING_INSPECTION",
    )
    require(
        read_checked(directory / "manifest.json", MAX_MANIFEST_BYTES) == raw,
        "DATASET_CHANGED_DURING_INSPECTION",
    )
    return manifest


def _ledger(
    designs: tuple[SourceDesign, ...], manifests: dict, receipts: dict, history: HistoricalInventory
) -> dict:
    require(
        len(designs) == 8 and len({d.case.case_id for d in designs}) == 8,
        "EXACT_EIGHT_CASES_REQUIRED",
    )
    keys = set()
    for offset in range(0, 8, 2):
        left, right = (manifests[d.case.case_id] for d in designs[offset : offset + 2])
        pair_check(left, right)
        require(left["world_id"] not in keys, "DUPLICATE_WORLD_OR_ENTITY_ALIAS")
        keys.add(left["world_id"])
    return {
        **manifest_policy(),
        "environment": environment(),
        "infrastructure_code": core_identity(),
        "historical_inventory": history.receipt,
        "datasets": {
            design.case.case_id: {
                "world_id": design.case.world_id,
                "seed": design.case.seed,
                "condition": design.case.condition,
                "manifest_sha256": receipts[design.case.case_id],
                "audit": manifests[design.case.case_id]["audit"],
            }
            for design in designs
        },
        "state": "REGISTERED_LABEL_BLIND_REPLAY_VERIFIED",
    }


def _inspect_batch(
    root: Path, designs: tuple[SourceDesign, ...], receipts: dict, history: HistoricalInventory
) -> dict:
    datasets = safe_path(root, "datasets")
    require(
        datasets.is_dir()
        and {p.name for p in datasets.iterdir()} == {d.case.case_id for d in designs},
        "CLOSED_EIGHT_DATASET_DIRECTORIES_REQUIRED",
    )
    require(
        isinstance(receipts, dict)
        and set(receipts) == {d.case.case_id for d in designs}
        and len(receipts) == 8,
        "EXACT_EIGHT_INDEPENDENT_RECEIPTS_REQUIRED",
    )
    for value in receipts.values():
        require_sha(value)
    manifests = {
        d.case.case_id: _inspect_dataset(root, d, receipts[d.case.case_id], history)
        for d in designs
    }
    return _ledger(designs, manifests, receipts, history)


def _register_batch(
    root: Path, designs: tuple[SourceDesign, ...], receipts: dict, history: HistoricalInventory
) -> dict:
    require(not safe_path(root, "receipts/datasets.json").exists(), "CREATE_ONLY_LEDGER_REQUIRED")
    ledger = _inspect_batch(root, designs, receipts, history)
    content = encode(ledger)
    require(len(content) <= MAX_MANIFEST_BYTES, "LEDGER_BYTE_LIMIT")
    write_new(root, "receipts/datasets.json", content)
    return {
        "status": ledger["state"],
        "ledger_sha256": sha256(content),
        "cases": len(designs),
        "promotion_decision": "NO_ML_PROMOTION",
    }


def _verify_ledger(
    root: Path, designs: tuple[SourceDesign, ...], expected_sha: str, history: HistoricalInventory
) -> dict:
    require_sha(expected_sha)
    raw = read_checked(safe_path(root, "receipts/datasets.json"), MAX_MANIFEST_BYTES)
    require(sha256(raw) == expected_sha, "INDEPENDENT_LEDGER_RECEIPT_DRIFT")
    ledger = read_json(raw.decode("utf-8"))
    require(
        isinstance(ledger.get("datasets"), dict)
        and set(ledger["datasets"]) == {d.case.case_id for d in designs},
        "CLOSED_LEDGER_REQUIRED",
    )
    receipts = {key: value["manifest_sha256"] for key, value in ledger["datasets"].items()}
    observed = _inspect_batch(root, designs, receipts, history)
    require(encode(observed) == raw, "LEDGER_POLICY_OR_SOURCE_DRIFT")
    return {
        "status": "INDEPENDENT_LEDGER_AND_SOURCES_VERIFIED",
        "cases": len(designs),
        "ledger_sha256": expected_sha,
        "promotion_decision": "NO_ML_PROMOTION",
    }
