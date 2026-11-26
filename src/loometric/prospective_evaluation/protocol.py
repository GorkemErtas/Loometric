"""Frozen declaration and metadata-only design checks; never read labels or execute models."""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from loometric.prediction.contracts import read_json
from loometric.synthetic_ml.configuration import GenerationConfig
from loometric.synthetic_ml.splitting import date_partitions

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = ROOT / "configs/prospective_evaluation_v1.json"
PROTOCOL_SHA256 = "2c64f2eccbf310ba2079d8c47fc11ab78e076cd8081937ebc56468975443b0e5"
ENTITY_KINDS = frozenset({"factory", "line", "crew", "style", "standard", "order", "shift"})


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError(code)


def protocol_digest(config: dict) -> str:
    content = json.dumps(config, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def load_protocol(path: Path = PROTOCOL_PATH) -> dict:
    _require(path.stat().st_size <= 65536, "PROSPECTIVE_CONFIGURATION_BYTE_LIMIT")
    config = read_json(path.read_text(encoding="utf-8"))
    _require(protocol_digest(config) == PROTOCOL_SHA256, "FROZEN_PROSPECTIVE_PROTOCOL_REQUIRED")
    return config


def verify_frozen_sources(config: dict) -> None:
    """Check declared source/config/pin files only; no generated artifact is opened."""
    _require(protocol_digest(config) == PROTOCOL_SHA256, "FROZEN_PROSPECTIVE_PROTOCOL_REQUIRED")
    for name, expected in config["frozen_files_sha256"].items():
        path = ROOT / name
        _require(path.resolve() == path.absolute(), "FROZEN_SOURCE_PATH_DRIFT")
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        _require(actual == expected, "FROZEN_SOURCE_CONTENT_DRIFT")


@dataclass(frozen=True)
class CasePlan:
    case_id: str
    world_id: str
    seed: int
    condition: str
    score_dates: tuple[date, ...]
    planned_rows: int
    source_rows: int
    directory: str


def plan_cases(config: dict) -> tuple[CasePlan, ...]:
    """Calendar arithmetic only; do not call generate, read a dataset or sample an RNG."""
    _require(protocol_digest(config) == PROTOCOL_SHA256, "FROZEN_PROSPECTIVE_PROTOCOL_REQUIRED")
    worlds = config["worlds"]
    parameters = {
        **worlds["parameters"],
        "start_date": date.fromisoformat(worlds["parameters"]["start_date"]),
    }
    result = []
    for seed in worlds["seeds"]:
        for condition in worlds["conditions"]:
            generation = GenerationConfig(**parameters, seed=seed, scenario=condition)
            dates = date_partitions(generation)
            score_dates = tuple(day for day, part in dates.items() if part == "validation")
            # V1 reserves the last factory/line before its new world's test period.
            familiar_rows = (generation.factories - 1) * 5 * (generation.lines_per_stage - 1) * 2
            test_rows = generation.factories * 5 * generation.lines_per_stage * 2
            planned = len(score_dates) * familiar_rows
            source = sum(test_rows if part == "test" else familiar_rows for part in dates.values())
            _require(
                len(score_dates) == config["sample_size"]["score_dates_per_case"]
                and planned == config["sample_size"]["planned_rows_per_case"]
                and source == config["sample_size"]["source_rows_per_case"],
                "PROSPECTIVE_SAMPLE_DESIGN_DRIFT",
            )
            case_id = worlds["case_id_template"].format(seed=seed, condition=condition)
            result.append(
                CasePlan(
                    case_id,
                    worlds["world_id_template"].format(seed=seed),
                    seed,
                    condition,
                    score_dates,
                    planned,
                    source,
                    f"{config['storage']['root']}/{config['storage']['datasets_subdirectory']}/{case_id}",
                )
            )
    return tuple(result)


@dataclass(frozen=True)
class SnapshotProvenance:
    case_id: str
    world_id: str
    source_seed: int
    local_observation_id: str
    source_partition: str
    shift_start: datetime
    shift_end: datetime
    cutoff: datetime
    snapshot_at: datetime
    label_available_at: datetime
    references_available_at: tuple[tuple[str, datetime], ...]
    # (entity kind, world_id, local entity ID); raw IDs alone are not global keys.
    entity_keys: tuple[tuple[str, str, str], ...]
    feature_columns: tuple[str, ...]


def validate_snapshot(
    config: dict,
    case: CasePlan,
    evidence: SnapshotProvenance,
    *,
    historical_entity_keys: frozenset[tuple[str, str, str]],
) -> None:
    """Reject metadata leakage; actual source joins/bytes need a later verified reader."""
    _require(case in plan_cases(config), "UNDECLARED_PROSPECTIVE_CASE")
    _require(
        evidence.case_id == case.case_id
        and evidence.world_id == case.world_id
        and type(evidence.source_seed) is int
        and evidence.source_seed == case.seed
        and evidence.source_partition == config["worlds"]["source_partition_scored"]
        and isinstance(evidence.local_observation_id, str)
        and bool(evidence.local_observation_id.strip()),
        "PROSPECTIVE_SOURCE_IDENTITY_DRIFT",
    )
    times = (
        evidence.shift_start,
        evidence.shift_end,
        evidence.cutoff,
        evidence.snapshot_at,
        evidence.label_available_at,
        *(v for _, v in evidence.references_available_at),
    )
    _require(
        all(
            isinstance(v, datetime)
            and v.tzinfo is not None
            and v.utcoffset() is not None
            and v.second == v.microsecond == 0
            for v in times
        ),
        "AWARE_MINUTE_PROVENANCE_REQUIRED",
    )
    contract = config["contract"]
    _require(
        evidence.shift_start.date() in case.score_dates
        and evidence.shift_end
        == evidence.shift_start + timedelta(minutes=contract["shift_minutes"])
        and evidence.cutoff
        == evidence.shift_start - timedelta(minutes=contract["prediction_minutes_before_shift"])
        and evidence.snapshot_at
        == evidence.cutoff - timedelta(minutes=contract["snapshot_minutes_before_cutoff"])
        and evidence.label_available_at
        == evidence.shift_end
        + timedelta(minutes=config["worlds"]["parameters"]["label_delay_minutes"])
        and evidence.cutoff
        > datetime.fromisoformat(config["worlds"]["historical_calendar_label_upper_bound"]),
        "PROSPECTIVE_TEMPORAL_PROVENANCE_DRIFT",
    )
    _require(
        len(evidence.references_available_at) == len(ENTITY_KINDS)
        and {kind for kind, _ in evidence.references_available_at} == ENTITY_KINDS
        and all(v <= evidence.cutoff for _, v in evidence.references_available_at),
        "FEATURE_SOURCE_UNAVAILABLE_AT_CUTOFF",
    )
    _require(
        evidence.feature_columns == tuple(contract["feature_columns"]),
        "EXACT_FROZEN_FEATURE_ORDER_REQUIRED",
    )
    _require(
        len(evidence.entity_keys) == len(ENTITY_KINDS)
        and {kind for kind, _, _ in evidence.entity_keys} == ENTITY_KINDS
        and all(
            world == case.world_id and isinstance(local, str) and bool(local.strip())
            for _, world, local in evidence.entity_keys
        )
        and not historical_entity_keys.intersection(evidence.entity_keys),
        "PROSPECTIVE_ENTITY_SEPARATION_FAILURE",
    )


def validate_matched_design(
    config: dict, baseline: CasePlan, disruption: CasePlan, left: dict, right: dict
) -> None:
    """Validate paired receipt metadata only, without decoding features or outcomes."""
    cases = plan_cases(config)
    _require(
        baseline in cases
        and disruption in cases
        and baseline.condition == "baseline"
        and disruption.condition == "disruption"
        and baseline.seed == disruption.seed
        and baseline.world_id == disruption.world_id,
        "MATCHED_WORLD_PAIR_REQUIRED",
    )
    digests = (
        "manifest_sha256",
        "features_sha256",
        "score_ids_sha256",
        "pre_shift_entities_sha256",
    )
    for case, receipt in ((baseline, left), (disruption, right)):
        _require(
            set(receipt) == {*digests, "case_id", "world_id", "seed", "planned_rows"}
            and receipt["case_id"] == case.case_id
            and receipt["world_id"] == case.world_id
            and type(receipt["seed"]) is int
            and receipt["seed"] == case.seed
            and type(receipt["planned_rows"]) is int
            and receipt["planned_rows"] == case.planned_rows
            and all(
                isinstance(receipt[k], str) and re.fullmatch(r"[a-f0-9]{64}", receipt[k])
                for k in digests
            ),
            "CLOSED_PROSPECTIVE_RECEIPT_REQUIRED",
        )
    _require(
        all(left[k] == right[k] for k in digests if k != "manifest_sha256")
        and left["manifest_sha256"] != right["manifest_sha256"],
        "MATCHED_DESIGN_FINGERPRINT_DRIFT",
    )
