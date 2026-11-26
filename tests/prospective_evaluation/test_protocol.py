"""Declaration/calendar/provenance tests only: no generated outcomes or fitted models."""

import copy
import json
import subprocess
import sys
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from loometric.prospective_evaluation import protocol
from loometric.prospective_evaluation.protocol import (
    ENTITY_KINDS,
    PROTOCOL_SHA256,
    SnapshotProvenance,
    load_protocol,
    plan_cases,
    protocol_digest,
    validate_matched_design,
    validate_snapshot,
    verify_frozen_sources,
)
from loometric.synthetic_ml.features import FEATURE_COLUMNS


def test_declaration_freezes_models_contract_sources_and_no_promotion():
    config = load_protocol()
    assert protocol_digest(config) == PROTOCOL_SHA256
    assert config["contract"]["feature_columns"] == list(FEATURE_COLUMNS)
    assert config["contract"]["target"] == "standard_capacity_attainment"
    assert {m["name"] for m in config["models"]} == {
        "grouped_mean",
        "random_forest",
        "histogram_gradient_boosting",
        "rf_physics",
    }
    assert config["execution_requires_separate_authorization"] is True
    assert config["budget"]["maximum_estimator_fits"] == 0
    assert config["budget"]["maximum_calibration_fits"] == 0
    assert config["invariants"]["promotion_decision"] == "NO_ML_PROMOTION"
    assert all(v is False for k, v in config["invariants"].items() if k != "promotion_decision")
    assert config["storage"]["prospective_receipts_state"] == "NOT_GENERATED"
    for model in config["models"]:
        bundle = config["frozen_bundles"][model["bundle"]]
        assert model["file"] in bundle["files"]
    verify_frozen_sources(config)


@pytest.mark.parametrize(
    "section,field,value",
    [
        ("worlds", "seeds", [19, 42, 73]),
        ("worlds", "source_partition_scored", "test"),
        ("worlds", "conditions", ["baseline", "workload_surge"]),
        ("contract", "feature_columns", [*FEATURE_COLUMNS, "realized_workers"]),
        ("contract", "target", "actual_productivity"),
        ("contract", "clipping_allowed", True),
        ("sample_size", "planned_rows_per_case", 10000),
        ("sample_size", "size_extension_allowed", True),
        ("storage", "root", "data/processed/experimental_ml/v2"),
        ("evaluation", "calibration_allowed", True),
        ("evaluation", "scientific_population", "SUPPORTED_ROWS_ONLY"),
        ("uncertainty", "multiple_comparisons", "PICK_BEST_PAIR"),
        ("acceptance", "maximum_stage_mae_regression_vs_group_percent", 100),
        ("budget", "maximum_estimator_fits", 1),
        ("budget", "maximum_hyperparameter_trials", 1),
        ("invariants", "promotion_decision", "PROMOTED"),
        ("invariants", "serving_changes_allowed", True),
    ],
)
def test_any_changed_scientific_or_safety_declaration_requires_new_protocol(
    tmp_path, section, field, value
):
    config = load_protocol()
    config[section][field] = value
    path = tmp_path / "changed.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="FROZEN_PROSPECTIVE_PROTOCOL_REQUIRED"):
        load_protocol(path)
    with pytest.raises(ValueError, match="FROZEN_PROSPECTIVE_PROTOCOL_REQUIRED"):
        plan_cases(config)


def test_strict_json_byte_limit_and_canonical_reproduction(tmp_path):
    config = load_protocol()
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(config, sort_keys=True), encoding="utf-8")
    assert load_protocol(path) == config
    path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
    with pytest.raises(ValueError):
        load_protocol(path)
    path.write_text('{"number":NaN}', encoding="utf-8")
    with pytest.raises(ValueError):
        load_protocol(path)
    path.write_bytes(b" " * 65537)
    with pytest.raises(ValueError, match="BYTE_LIMIT"):
        load_protocol(path)


def test_calendar_counts_and_world_separation_without_generating_a_dataset():
    config = load_protocol()
    cases = plan_cases(config)
    assert len(cases) == 8 and len({c.case_id for c in cases}) == 8
    assert len({c.directory for c in cases}) == 8
    assert {c.seed for c in cases} == {101, 211, 307, 401}
    assert all(
        len(c.score_dates) == 18 and c.planned_rows == 360 and c.source_rows == 2720 for c in cases
    )
    assert sum(c.planned_rows for c in cases) == 2880
    assert sum(c.source_rows for c in cases) == 21760
    for baseline, disruption in zip(cases[::2], cases[1::2], strict=True):
        assert baseline.condition == "baseline" and disruption.condition == "disruption"
        assert baseline.world_id == disruption.world_id
        assert baseline.score_dates == disruption.score_dates
        assert str(baseline.score_dates[0]) == "2032-03-11"
        assert str(baseline.score_dates[-1]) == "2032-03-31"
    assert config["budget"]["maximum_scored_predictions_per_run"] == 4 * 2880
    assert 4**4 == config["uncertainty"]["primary"]["ordered_resamples"]


@pytest.fixture
def snapshot():
    case = plan_cases(load_protocol())[0]
    start = datetime(2032, 3, 11, 8, tzinfo=timezone(timedelta(hours=3)))
    cutoff = start - timedelta(minutes=30)
    return case, SnapshotProvenance(
        case_id=case.case_id,
        world_id=case.world_id,
        source_seed=case.seed,
        local_observation_id="PRIVATE-PROVENANCE-ONLY",
        source_partition="validation",
        shift_start=start,
        shift_end=start + timedelta(hours=8),
        cutoff=cutoff,
        snapshot_at=cutoff - timedelta(minutes=5),
        label_available_at=start + timedelta(hours=10),
        references_available_at=tuple(
            (kind, cutoff - timedelta(days=1)) for kind in sorted(ENTITY_KINDS)
        ),
        entity_keys=tuple((kind, case.world_id, f"LOCAL-{kind}") for kind in sorted(ENTITY_KINDS)),
        feature_columns=tuple(FEATURE_COLUMNS),
    )


def test_namespace_allows_same_local_spelling_but_never_reuses_a_historical_entity(snapshot):
    case, evidence = snapshot
    old = frozenset(
        (kind, "synthetic-ml-v1-world-42", local) for kind, _, local in evidence.entity_keys
    )
    validate_snapshot(load_protocol(), case, evidence, historical_entity_keys=old)
    # Actual collision in a fully scoped key still fails; a prefix alone is no audit.
    with pytest.raises(ValueError, match="ENTITY_SEPARATION"):
        validate_snapshot(
            load_protocol(), case, evidence, historical_entity_keys=frozenset(evidence.entity_keys)
        )


@pytest.mark.parametrize(
    "change",
    [
        {"source_seed": 42},
        {"source_seed": True},
        {"world_id": "exp-009-world-211"},
        {"source_partition": "test"},
        {"source_partition": "train"},
        {"feature_columns": (*FEATURE_COLUMNS, "unplanned_loss_minutes")},
        {"feature_columns": tuple(reversed(FEATURE_COLUMNS))},
        {"references_available_at": ()},
        {"entity_keys": ()},
    ],
)
def test_source_identity_reservation_and_feature_leakage_rejected(snapshot, change):
    case, evidence = snapshot
    with pytest.raises(ValueError):
        validate_snapshot(
            load_protocol(), case, replace(evidence, **change), historical_entity_keys=frozenset()
        )


@pytest.mark.parametrize(
    "field,offset",
    [
        ("cutoff", 1),
        ("snapshot_at", 6),
        ("shift_start", -1000000),
        ("shift_end", -1),
        ("label_available_at", -1),
    ],
)
def test_temporal_provenance_drift_rejected(snapshot, field, offset):
    case, evidence = snapshot
    bad = replace(evidence, **{field: getattr(evidence, field) + timedelta(minutes=offset)})
    with pytest.raises(ValueError, match="TEMPORAL_PROVENANCE"):
        validate_snapshot(load_protocol(), case, bad, historical_entity_keys=frozenset())


def test_late_source_naive_time_and_foreign_world_rejected(snapshot):
    case, evidence = snapshot
    late = list(evidence.references_available_at)
    late[0] = (late[0][0], evidence.cutoff + timedelta(minutes=1))
    with pytest.raises(ValueError, match="UNAVAILABLE_AT_CUTOFF"):
        validate_snapshot(
            load_protocol(),
            case,
            replace(evidence, references_available_at=tuple(late)),
            historical_entity_keys=frozenset(),
        )
    with pytest.raises(ValueError, match="AWARE_MINUTE"):
        validate_snapshot(
            load_protocol(),
            case,
            replace(evidence, cutoff=evidence.cutoff.replace(tzinfo=None)),
            historical_entity_keys=frozenset(),
        )
    keys = tuple((kind, "exp-009-world-211", local) for kind, _, local in evidence.entity_keys)
    with pytest.raises(ValueError, match="ENTITY_SEPARATION"):
        validate_snapshot(
            load_protocol(),
            case,
            replace(evidence, entity_keys=keys),
            historical_entity_keys=frozenset(),
        )


def test_matched_receipt_checks_without_reading_outcomes():
    config = load_protocol()
    baseline, disruption = plan_cases(config)[:2]

    def receipt(case, manifest):
        return {
            "case_id": case.case_id,
            "world_id": case.world_id,
            "seed": case.seed,
            "planned_rows": case.planned_rows,
            "manifest_sha256": manifest * 64,
            "features_sha256": "c" * 64,
            "score_ids_sha256": "d" * 64,
            "pre_shift_entities_sha256": "e" * 64,
        }

    left, right = receipt(baseline, "a"), receipt(disruption, "b")
    validate_matched_design(config, baseline, disruption, left, right)
    for key, value in (
        ("features_sha256", "f" * 64),
        ("score_ids_sha256", "f" * 64),
        ("pre_shift_entities_sha256", "f" * 64),
        ("manifest_sha256", "a" * 64),
        ("planned_rows", 359),
        ("seed", 42),
        ("target", 0.9),
    ):
        changed = copy.deepcopy(right)
        changed[key] = value
        with pytest.raises(ValueError):
            validate_matched_design(config, baseline, disruption, left, changed)
    with pytest.raises(ValueError, match="MATCHED_WORLD_PAIR"):
        validate_matched_design(config, baseline, plan_cases(config)[3], left, right)


def test_frozen_code_drift_fails_without_changing_any_source(monkeypatch):
    class DifferentDigest:
        def hexdigest(self):
            return "0" * 64

    monkeypatch.setattr(protocol.hashlib, "file_digest", lambda *args: DifferentDigest())
    with pytest.raises(ValueError, match="FROZEN_SOURCE_CONTENT_DRIFT"):
        verify_frozen_sources(load_protocol())


def test_protocol_import_and_validation_are_ml_free_and_cannot_read_datasets():
    script = """
import pathlib, sys
root = pathlib.Path.cwd()
def audit(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes)):
        path = pathlib.Path(args[0].decode() if isinstance(args[0], bytes) else args[0]).resolve()
        if path.is_relative_to(root / 'data'):
            raise AssertionError('Protocol accessed a dataset or frozen model')
sys.addaudithook(audit)
from loometric.prospective_evaluation.protocol import (
    load_protocol, plan_cases, verify_frozen_sources,
)
config = load_protocol()
existed = (root / config['storage']['root']).exists()
assert len(plan_cases(config)) == 8
verify_frozen_sources(config)
assert not any(n.split('.')[0] in {'pandas', 'numpy', 'sklearn', 'joblib'} for n in sys.modules)
assert (root / config['storage']['root']).exists() == existed
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=protocol.ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
